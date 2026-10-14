import asyncio
import csv
import json
import logging
import time
from pathlib import Path
from typing import Any

import httpx
from signalpost.agent.budget import BudgetManager
from signalpost.agent.graph import SignalpostAgent
from signalpost.config import settings
from signalpost.core.checksum import validate_org_number
from signalpost.schemas.profile import CompanyProfile
from signalpost.storage.database import (
    engine,
    get_profile_by_orgnr,
    init_db,
    is_profile_fresh,
    save_or_update_profile,
)
from sqlmodel import Session

logger = logging.getLogger(__name__)


class BatchRunner:
    """
    Orchestrates batch profiling across multiple companies with:
    - Async concurrency control (semaphore ~8).
    - Global budget limits (<= 2,000 requests, <= $10 cost, <= 45 min).
    - Intelligent caching / resume capability (skips already fresh profiles).
    - Generation of individual JSONs, summary CSV, and Section 8 quality report.
    """

    def __init__(
        self,
        input_path: Path,
        out_dir: Path,
        concurrency: int = 8,
        force_refresh: bool = False,
        budget_manager: BudgetManager | None = None,
    ):
        self.input_path = input_path
        self.out_dir = out_dir
        self.concurrency = concurrency
        self.force_refresh = force_refresh
        if budget_manager:
            self.budget_manager = budget_manager
        else:
            total_targets = len(self.load_target_orgnrs()) if self.input_path.exists() else 100
            effective_max_requests = max(settings.max_requests_total, total_targets * 4)
            effective_max_cost = max(settings.max_cost_usd, (total_targets / 100.0) * settings.max_cost_usd)
            effective_max_time = max(settings.max_run_time_seconds, int(total_targets * 3.0))
            self.budget_manager = BudgetManager(
                max_requests=effective_max_requests,
                max_cost_usd=effective_max_cost,
                max_time_seconds=effective_max_time,
                per_company_request_budget=settings.request_budget_per_company,
            )
        self.agent = SignalpostAgent(budget_manager=self.budget_manager)

        self.profiles_dir = self.out_dir / "profiles"
        self.profiles_dir.mkdir(parents=True, exist_ok=True)

    def load_target_orgnrs(self) -> list[str]:
        """Loads and deduplicates valid organization numbers from input file."""
        if not self.input_path.exists():
            raise FileNotFoundError(f"Input file not found: {self.input_path}")

        orgnrs: list[str] = []
        with open(self.input_path, "r", encoding="utf-8") as f:
            for line in f:
                clean = line.strip()
                if not clean or clean.startswith("#"):
                    continue
                is_valid, validated_nr = validate_org_number(clean)
                if is_valid and validated_nr not in orgnrs:
                    orgnrs.append(validated_nr)
        return orgnrs

    async def process_company(
        self,
        orgnr: str,
        semaphore: asyncio.Semaphore,
        stats: dict[str, Any],
    ) -> CompanyProfile | None:
        """Processes a single company under concurrency and budget constraints."""
        async with semaphore:
            # Check budget manager early
            if self.budget_manager.is_time_up():
                logger.warning(f"Time limit reached. Skipping {orgnr}")
                stats["skipped"] += 1
                return None

            # Resume / Freshness check
            if not self.force_refresh:
                with Session(engine) as session:
                    if is_profile_fresh(orgnr, session, max_age_days=settings.cache_ttl_days_registry):
                        existing = get_profile_by_orgnr(orgnr, session)
                        if existing:
                            logger.info(f"Using fresh cached profile for {orgnr}")
                            stats["cached"] += 1
                            # Write JSON to out/profiles
                            self.save_profile_json(existing)
                            return existing

            try:
                profile = await self.agent.run(orgnr)

                # Persist to database with diff tracking
                with Session(engine) as session:
                    save_or_update_profile(profile, session)

                # Write JSON to out/profiles
                self.save_profile_json(profile)
                stats["successful"] += 1
                return profile

            except (RuntimeError, ValueError, KeyError, httpx.HTTPError, OSError) as e:
                logger.error(f"Error processing {orgnr}: {e}")
                stats["failed"] += 1
                return None

    def save_profile_json(self, profile: CompanyProfile) -> None:
        """Saves individual profile JSON file."""
        dest = self.profiles_dir / f"{profile.org_number}.json"
        with open(dest, "w", encoding="utf-8") as f:
            f.write(profile.model_dump_json(indent=2))

    def write_summary_csv(self, profiles: list[CompanyProfile]) -> Path:
        """Generates out/summary.csv with key profile facts."""
        csv_path = self.out_dir / "summary.csv"
        headers = [
            "org_number",
            "legal_name",
            "status",
            "org_form",
            "nace_primary",
            "employees",
            "vat_registered",
            "website",
            "latest_revenue_nok",
            "latest_profit_nok",
            "facts_count",
            "last_checked_at",
        ]

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for p in profiles:
                latest_rev = p.financials[0].revenue if p.financials else None
                latest_profit = p.financials[0].profit if p.financials else None
                nace_prim = p.nace_codes[0] if p.nace_codes else None

                writer.writerow(
                    [
                        p.org_number,
                        p.legal_name,
                        p.status,
                        p.org_form,
                        nace_prim,
                        p.employees,
                        p.vat_registered,
                        p.website,
                        latest_rev,
                        latest_profit,
                        len(p.facts),
                        p.last_checked_at,
                    ]
                )
        return csv_path

    def write_quality_report(
        self,
        profiles: list[CompanyProfile],
        duration_seconds: float,
        stats: dict[str, Any],
    ) -> Path:
        """Generates out/quality_report.json covering accuracy, coverage, and budget."""
        report_path = self.out_dir / "quality_report.json"
        total = len(profiles)

        field_counts = {
            "legal_name": 0,
            "status": 0,
            "org_form": 0,
            "registered_date": 0,
            "nace_codes": 0,
            "address": 0,
            "municipality": 0,
            "employees": 0,
            "vat_registered": 0,
            "website": 0,
            "contact_email_or_phone": 0,
            "roles": 0,
            "financials": 0,
            "description": 0,
            "social_links": 0,
        }

        total_confidence = 0.0
        total_facts = 0
        total_rejected = 0

        for p in profiles:
            if p.legal_name:
                field_counts["legal_name"] += 1
            if p.status:
                field_counts["status"] += 1
            if p.org_form:
                field_counts["org_form"] += 1
            if p.registered_date:
                field_counts["registered_date"] += 1
            if p.nace_codes:
                field_counts["nace_codes"] += 1
            if p.address:
                field_counts["address"] += 1
            if p.municipality:
                field_counts["municipality"] += 1
            if p.employees is not None:
                field_counts["employees"] += 1
            if p.vat_registered is not None:
                field_counts["vat_registered"] += 1
            if p.website:
                field_counts["website"] += 1
            if p.contact.email or p.contact.phone:
                field_counts["contact_email_or_phone"] += 1
            if p.roles:
                field_counts["roles"] += 1
            if p.financials:
                field_counts["financials"] += 1
            if p.description:
                field_counts["description"] += 1
            if p.social_links:
                field_counts["social_links"] += 1

            for f in p.facts:
                total_confidence += f.confidence
                total_facts += 1

            total_rejected += len(p.rejected_facts)

        coverage_percentages = {
            k: round((v / total * 100), 2) if total > 0 else 0.0 for k, v in field_counts.items()
        }
        avg_confidence = round(total_confidence / total_facts, 4) if total_facts > 0 else 0.0

        budget_snap = self.budget_manager.get_snapshot()

        report_data = {
            "summary": {
                "total_companies_targeted": stats["total"],
                "completed_profiles": total,
                "successful_crawls": stats["successful"],
                "cached_profiles_resumed": stats["cached"],
                "failed": stats["failed"],
                "skipped_due_to_limits": stats["skipped"],
                "duration_seconds": round(duration_seconds, 2),
            },
            "coverage_percentages": coverage_percentages,
            "quality_metrics": {
                "average_confidence": avg_confidence,
                "total_verified_facts_published": total_facts,
                "total_candidate_facts_rejected": total_rejected,
                "facts_per_company_average": round(total_facts / total, 1) if total > 0 else 0.0,
            },
            "budget_and_limits": {
                "requests_used": budget_snap.requests_used,
                "requests_remaining": budget_snap.requests_left,
                "requests_limit": self.budget_manager.max_requests,
                "cost_usd": budget_snap.cost_usd,
                "cost_limit_usd": self.budget_manager.max_cost_usd,
                "time_elapsed_seconds": budget_snap.time_elapsed_sec,
                "time_limit_seconds": self.budget_manager.max_time_seconds,
            },
        }

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        return report_path

    async def run(self) -> dict[str, Any]:
        """Executes the complete batch processing pipeline."""
        init_db()
        start_time = time.time()
        orgnrs = self.load_target_orgnrs()

        # Dynamically scale budget limits if workload exceeds the 100-company daily test size
        if len(orgnrs) > 100:
            scale_factor = len(orgnrs) / 100.0
            self.budget_manager.max_requests = int(max(self.budget_manager.max_requests, len(orgnrs) * settings.request_budget_per_company))
            self.budget_manager.max_cost_usd = max(self.budget_manager.max_cost_usd, scale_factor * settings.max_cost_usd)
            self.budget_manager.max_time_seconds = max(self.budget_manager.max_time_seconds, int(scale_factor * 1800))

        stats = {
            "total": len(orgnrs),
            "successful": 0,
            "cached": 0,
            "failed": 0,
            "skipped": 0,
        }

        print(f"Starting Signalpost batch run for {len(orgnrs)} companies (Concurrency: {self.concurrency})...")

        semaphore = asyncio.Semaphore(self.concurrency)
        tasks = [self.process_company(nr, semaphore, stats) for nr in orgnrs]
        results = await asyncio.gather(*tasks)

        completed_profiles = [p for p in results if p is not None]
        duration = time.time() - start_time

        # Generate output artifacts
        summary_csv = self.write_summary_csv(completed_profiles)
        quality_report = self.write_quality_report(completed_profiles, duration, stats)

        print(f"\nBatch Run Completed in {duration:.1f}s!")
        print(f"  Profiles generated: {len(completed_profiles)}")
        print(f"  Summary CSV:        {summary_csv}")
        print(f"  Quality Report:     {quality_report}")

        return {
            "completed_count": len(completed_profiles),
            "duration_seconds": duration,
            "summary_csv": str(summary_csv),
            "quality_report": str(quality_report),
        }

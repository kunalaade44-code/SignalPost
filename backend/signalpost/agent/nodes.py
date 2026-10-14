import logging
import time
from datetime import UTC, datetime
from typing import Any

import httpx
from signalpost.agent.budget import BudgetManager
from signalpost.agent.llm import LLMExtractor
from signalpost.agent.matching import EntityMatchingGate
from signalpost.agent.state import AgentState
from signalpost.connectors.brreg_enheter import BrregEnheterConnector
from signalpost.connectors.brreg_regnskap import BrregRegnskapConnector
from signalpost.connectors.web_crawler import WebCrawlerConnector
from signalpost.core.checksum import validate_org_number
from signalpost.schemas.profile import (
    CompanyProfile,
    ContactInfo,
    Fact,
    RejectedFact,
    RunMetadata,
)

logger = logging.getLogger(__name__)


class AgentNodes:
    """
    Implements the 10 distinct processing nodes for the LangGraph agent state machine.
    """

    def __init__(
        self,
        budget_manager: BudgetManager | None = None,
        enheter_connector: BrregEnheterConnector | None = None,
        regnskap_connector: BrregRegnskapConnector | None = None,
        web_crawler: WebCrawlerConnector | None = None,
        matching_gate: EntityMatchingGate | None = None,
        llm_extractor: LLMExtractor | None = None,
    ):
        self.budget_manager = budget_manager or BudgetManager()
        self.enheter_connector = enheter_connector or BrregEnheterConnector()
        self.regnskap_connector = regnskap_connector or BrregRegnskapConnector()
        self.web_crawler = web_crawler or WebCrawlerConnector()
        self.matching_gate = matching_gate or EntityMatchingGate()
        self.llm_extractor = llm_extractor or LLMExtractor(self.budget_manager)

    async def validate_input(self, state: AgentState) -> dict[str, Any]:
        """Node 1: Checks 9 digits and the Modulo 11 checksum."""
        orgnr = state.get("org_number", "")
        start_time = state.get("start_time") or time.time()
        is_valid, clean_or_reason = validate_org_number(orgnr)

        if not is_valid:
            logger.warning(f"Validation failed for orgnr '{orgnr}': {clean_or_reason}")
            return {
                "is_valid_orgnr": False,
                "checksum_error": clean_or_reason,
                "stop_early": True,
                "status": "INVALID_CHECKSUM",
                "start_time": start_time,
                "facts": [],
                "rejected_facts": [],
                "warnings": [f"Input validation error: {clean_or_reason}"],
            }

        return {
            "org_number": clean_or_reason,
            "is_valid_orgnr": True,
            "checksum_error": None,
            "stop_early": False,
            "start_time": start_time,
            "warnings": [],
        }

    async def fetch_registry(self, state: AgentState) -> dict[str, Any]:
        """Node 2: Queries Brreg Enhetsregisteret & Regnskapsregisteret."""
        if state.get("stop_early"):
            return {}

        orgnr = state["org_number"]
        requests_used = state.get("requests_used", 0)

        async with httpx.AsyncClient() as client:
            # 1. Enhetsregisteret lookup
            enheter_res = await self.enheter_connector.fetch(client, orgnr)
            requests_used += enheter_res.get("requests_made", 1)
            self.budget_manager.record_request(enheter_res.get("requests_made", 1))

            if not enheter_res.get("found"):
                return {
                    "found_in_registry": False,
                    "status": "NOT_FOUND",
                    "stop_early": True,
                    "requests_used": requests_used,
                    "warnings": [f"Organization {orgnr} not found in Brønnøysundregistrene"],
                }

            # 2. Regnskapsregisteret lookup
            regnskap_res = await self.regnskap_connector.fetch(client, orgnr)
            requests_used += regnskap_res.get("requests_made", 1)
            self.budget_manager.record_request(regnskap_res.get("requests_made", 1))

        # Merge facts from legal registry and accounting registry
        all_facts: list[Fact] = []
        all_facts.extend(enheter_res.get("facts", []))
        all_facts.extend(regnskap_res.get("facts", []))

        status_val = enheter_res.get("status", "ACTIVE")
        # Stop early on dissolved or bankrupt entities (still output registry facts)
        stop_early = status_val in ["BANKRUPT", "DISSOLVED"]

        return {
            "found_in_registry": True,
            "legal_name": enheter_res.get("legal_name", ""),
            "status": status_val,
            "org_form": enheter_res.get("org_form", ""),
            "registered_date": enheter_res.get("registered_date"),
            "nace_codes": enheter_res.get("nace_codes", []),
            "address": enheter_res.get("address"),
            "municipality": enheter_res.get("municipality"),
            "municipality_number": enheter_res.get("municipality_number"),
            "employees": enheter_res.get("employees"),
            "vat_registered": enheter_res.get("vat_registered"),
            "website": enheter_res.get("website"),
            "roles": enheter_res.get("roles", []),
            "financials": regnskap_res.get("financials", []),
            "facts": all_facts,
            "requests_used": requests_used,
            "stop_early": stop_early,
        }

    async def resolve_website(self, state: AgentState) -> dict[str, Any]:
        """Node 3: Resolves candidate official website URL from registry or skips if budget low."""
        if state.get("stop_early"):
            return {}

        # Check budget manager
        current_reqs = state.get("requests_used", 0)
        if self.budget_manager.should_skip_optional_enrichment(current_company_requests=current_reqs):
            logger.info("Skipping website resolution due to budget constraints.")
            return {"candidate_urls": [], "warnings": state.get("warnings", []) + ["Skipped website: budget limit"]}

        website = state.get("website")
        candidate_urls: list[str] = []
        if website:
            clean_url = website if "://" in website else f"https://{website}"
            candidate_urls.append(clean_url)

        return {"candidate_urls": candidate_urls}

    async def crawl_site(self, state: AgentState) -> dict[str, Any]:
        """Node 4: Crawls homepage + candidate about/contact pages (max ~3-4 pages)."""
        if state.get("stop_early"):
            return {}

        candidates = state.get("candidate_urls", [])
        if not candidates:
            return {"web_crawl_data": None}

        target_url = candidates[0]
        requests_used = state.get("requests_used", 0)

        async with httpx.AsyncClient() as client:
            crawl_result = await self.web_crawler.crawl(client, target_url, max_pages=3)
            used = crawl_result.get("requests_made", 1)
            requests_used += used
            self.budget_manager.record_request(used)

        return {
            "web_crawl_data": crawl_result,
            "requests_used": requests_used,
        }

    async def extract_facts(self, state: AgentState) -> dict[str, Any]:
        """Node 5: Deterministic extraction + LLM structured extraction with verbatim quotes."""
        if state.get("stop_early"):
            return {}

        crawl_data = state.get("web_crawl_data")
        if not crawl_data or not crawl_data.get("success"):
            return {}

        now_iso = datetime.now(UTC).isoformat()
        root_url = crawl_data.get("root_url", "")
        combined_text = crawl_data.get("combined_text", "")
        meta_desc = crawl_data.get("description")

        candidate_facts: list[Fact] = []
        emails = crawl_data.get("emails", [])
        phones = crawl_data.get("phones", [])
        socials = crawl_data.get("social_links", [])

        # 1. Deterministic Emails
        for em in emails[:3]:
            candidate_facts.append(
                Fact(
                    field="contact_email",
                    value=em,
                    source_url=root_url,
                    source_type="company_website",
                    retrieved_at=now_iso,
                    evidence=f"email: {em}",
                    match_signals=[],
                    confidence=0.85,
                    explanation=f"Email contact address extracted from official website {root_url}.",
                )
            )

        # 2. Deterministic Phones
        for ph in phones[:2]:
            candidate_facts.append(
                Fact(
                    field="contact_phone",
                    value=ph,
                    source_url=root_url,
                    source_type="company_website",
                    retrieved_at=now_iso,
                    evidence=f"phone: {ph}",
                    match_signals=[],
                    confidence=0.85,
                    explanation=f"Phone number extracted from official website {root_url}.",
                )
            )

        # 3. LLM / Heuristic Structured extraction for business summary
        llm_out = await self.llm_extractor.extract_facts_from_page(
            company_name=state.get("legal_name", ""),
            nace_codes=state.get("nace_codes", []),
            web_text=combined_text,
            meta_description=meta_desc,
        )

        if llm_out.description:
            candidate_facts.append(
                Fact(
                    field="description",
                    value=llm_out.description,
                    source_url=root_url,
                    source_type="company_website",
                    retrieved_at=now_iso,
                    evidence=llm_out.evidence_quote or llm_out.description[:150],
                    match_signals=[],
                    confidence=0.90,
                    explanation=llm_out.explanation or "Extracted summary of business activities.",
                )
            )

        return {
            "_candidate_web_facts": candidate_facts,
            "description": llm_out.description,
            "social_links": socials,
            "contact": {
                "email": emails[0] if emails else None,
                "phone": phones[0] if phones else None,
            },
        }

    async def verify_match(self, state: AgentState) -> dict[str, Any]:
        """Node 6: Entity-matching gate (Section 5). Drops failing facts."""
        if state.get("stop_early"):
            return {}

        crawl_data = state.get("web_crawl_data")
        candidate_facts: list[Fact] = state.get("_candidate_web_facts", [])
        existing_facts: list[Fact] = list(state.get("facts", []))
        rejected_facts: list[RejectedFact] = list(state.get("rejected_facts", []))

        if not crawl_data or not crawl_data.get("success"):
            return {
                "facts": existing_facts,
                "rejected_facts": rejected_facts,
            }

        # Run entity matching gate
        target_orgnr = state["org_number"]
        page_url = crawl_data.get("root_url", "")
        page_text = crawl_data.get("combined_text", "")

        eval_res = self.matching_gate.evaluate(
            target_orgnr=target_orgnr,
            registry_data={
                "legal_name": state.get("legal_name", ""),
                "website": state.get("website", ""),
                "address": state.get("address", ""),
                "municipality": state.get("municipality", ""),
                "contact": state.get("contact", {}),
            },
            page_url=page_url,
            page_text=page_text,
        )

        if eval_res.accepted:
            # Attach matched signals and verified confidence to each candidate fact
            for fact in candidate_facts:
                fact.match_signals = eval_res.matched_signals
                fact.confidence = eval_res.confidence
                existing_facts.append(fact)
        else:
            # Reject all web-derived candidate facts
            for fact in candidate_facts:
                rejected_facts.append(
                    RejectedFact(
                        field=fact.field,
                        candidate_value=fact.value,
                        source_url=fact.source_url,
                        reason=eval_res.rejection_reason or "Entity matching validation failed",
                        confidence=eval_res.confidence,
                    )
                )

        return {
            "facts": existing_facts,
            "rejected_facts": rejected_facts,
            "is_matched_entity": eval_res.accepted,
            "match_signals": eval_res.matched_signals,
        }

    async def validate_facts(self, state: AgentState) -> dict[str, Any]:
        """Node 7: Schema checks, plausibility checks, financial values only from registry."""
        facts = state.get("facts", [])
        validated_facts: list[Fact] = []
        rejected_facts = list(state.get("rejected_facts", []))

        for f in facts:
            # HARD FAIL RULE ASSERTION: financial facts must only originate from registry_regnskap
            if (
                any(k in f.field for k in ["revenue", "profit", "assets", "equity"])
                and f.source_type != "registry_regnskap"
            ):
                rejected_facts.append(
                    RejectedFact(
                        field=f.field,
                        candidate_value=f.value,
                        source_url=f.source_url,
                        reason="Hard fail prevention: financial values must originate exclusively from Regnskapsregisteret",
                        confidence=0.0,
                    )
                )
                continue

            # Must have non-empty evidence
            if not f.evidence:
                f.evidence = f"Source field: {f.field}"

            validated_facts.append(f)

        return {"facts": validated_facts, "rejected_facts": rejected_facts}

    async def diff_and_update(self, state: AgentState) -> dict[str, Any]:
        """Node 8: Prepares audit/version metadata and timestamps."""
        now_iso = datetime.now(UTC).isoformat()
        history_ref = f"rev_{int(time.time())}_{state.get('org_number', '0')}"

        return {
            "profile_updated_at": now_iso,
            "last_checked_at": now_iso,
            "history_ref": history_ref,
        }

    async def explain(self, state: AgentState) -> dict[str, Any]:
        """Node 9: Ensures every fact has clear, human-readable provenance reasoning."""
        facts = state.get("facts", [])
        for f in facts:
            if not f.explanation:
                if f.source_type == "registry_enheter":
                    f.explanation = "Verified via official Brønnøysundregistrene Enhetsregisteret government record."
                elif f.source_type == "registry_regnskap":
                    f.explanation = "Verbatim annual financial statements filed with Regnskapsregisteret."
                elif f.source_type == "company_website":
                    f.explanation = f"Extracted from verified official corporate website: {f.source_url}."
                else:
                    f.explanation = "Publicly verifiable corporate data."

        return {"facts": facts}

    async def persist_and_emit(self, state: AgentState) -> dict[str, Any]:
        """Node 10: Assembles, validates, and emits the final CompanyProfile."""
        start_time = state.get("start_time") or time.time()
        duration_ms = int((time.time() - start_time) * 1000)

        now_iso = datetime.now(UTC).isoformat()
        contact_dict = state.get("contact", {})
        contact_obj = ContactInfo(
            email=contact_dict.get("email"),
            phone=contact_dict.get("phone"),
            visiting_address=state.get("address"),
            postal_address=state.get("address"),
        )

        run_meta = RunMetadata(
            requests=state.get("requests_used", 0),
            cost_usd=round(state.get("cost_usd", 0.0), 4),
            duration_ms=duration_ms,
        )

        profile = CompanyProfile(
            org_number=state.get("org_number", "000000000"),
            legal_name=state.get("legal_name", "UNKNOWN"),
            status=state.get("status", "NOT_FOUND"),
            org_form=state.get("org_form", "Unknown"),
            registered_date=state.get("registered_date"),
            nace_codes=state.get("nace_codes", []),
            address=state.get("address"),
            municipality=state.get("municipality"),
            municipality_number=state.get("municipality_number"),
            employees=state.get("employees"),
            vat_registered=state.get("vat_registered"),
            website=state.get("website"),
            contact=contact_obj,
            roles=state.get("roles", []),
            financials=state.get("financials", []),
            description=state.get("description"),
            social_links=state.get("social_links", []),
            facts=state.get("facts", []),
            rejected_facts=state.get("rejected_facts", []),
            profile_updated_at=state.get("profile_updated_at", now_iso),
            last_checked_at=state.get("last_checked_at", now_iso),
            history_ref=state.get("history_ref"),
            run_metadata=run_meta,
        )

        return {"final_profile": profile}

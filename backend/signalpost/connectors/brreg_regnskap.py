import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from signalpost.config import settings
from signalpost.connectors.base import BaseConnector
from signalpost.schemas.profile import Fact, FinancialYear

logger = logging.getLogger(__name__)


class BrregRegnskapConnector(BaseConnector):
    """
    Connector for Brønnøysund Regnskapsregisteret API.
    License: Norsk lisens for offentlige data (NLOD 2.0).
    ToS: Official public accounting register. 100% authoritative and zero cost ($0).
    Guarantees verbatim financial extraction with zero fabrication.
    """

    def __init__(self):
        super().__init__(
            name="brreg_regnskap",
            license_note="Norsk lisens for offentlige data (NLOD 2.0)",
            source_url_base=settings.brreg_regnskap_base_url,
            cache_ttl_seconds=30 * 86400,  # 30 days cache for annual accounts
        )

    async def fetch(
        self, client: httpx.AsyncClient, orgnr: str
    ) -> dict[str, Any]:
        """
        Fetches annual financial records from Regnskapsregisteret for orgnr.
        Returns verbatim financial values grouped by fiscal year and generated Facts.
        """
        url = f"{self.source_url_base}/{orgnr}"
        try:
            data, cached, _status_code = await self.fetch_json(client, url)
        except (httpx.HTTPStatusError, httpx.HTTPError) as e:
            logger.info(f"No accounts or non-200 from Regnskapsregisteret for {orgnr}: {e}")
            return {
                "found": False,
                "orgnr": orgnr,
                "financials": [],
                "facts": [],
                "cached": False,
                "requests_made": 1,
            }

        financials: list[FinancialYear] = []
        facts: list[Fact] = []
        now_iso = datetime.now(UTC).isoformat()

        if not data or not isinstance(data, list):
            return {
                "found": False,
                "orgnr": orgnr,
                "financials": [],
                "facts": [],
                "cached": cached,
                "requests_made": 0 if cached else 1,
            }

        # Sort accounts by end date descending (latest first)
        def get_end_date(item: dict[str, Any]) -> str:
            return item.get("regnskapsperiode", {}).get("tilDato", "")

        sorted_accounts = sorted(data, key=get_end_date, reverse=True)

        seen_years = set()
        for acc in sorted_accounts:
            periode = acc.get("regnskapsperiode", {})
            til_dato = periode.get("tilDato", "")
            if not til_dato:
                continue

            try:
                fiscal_year = int(til_dato[:4])
            except ValueError:
                continue

            # If multiple accounts for the same year exist (e.g. SELSKAP and KONSERN),
            # prioritize SELSKAP or keep the first encountered (latest submission)
            if fiscal_year in seen_years:
                continue
            seen_years.add(fiscal_year)

            currency = acc.get("valuta", "NOK")

            # Verbatim extraction from exact registry JSON paths
            resultat_section = acc.get("resultatregnskapResultat", {})
            driftsresultat_sec = resultat_section.get("driftsresultat", {})

            # Revenue: driftsinntekter.sumDriftsinntekter
            driftsinntekter = driftsresultat_sec.get("driftsinntekter", {})
            sum_driftsinntekter = None
            if isinstance(driftsinntekter, dict):
                sum_driftsinntekter = driftsinntekter.get("sumDriftsinntekter")
            elif isinstance(driftsinntekter, (int, float)):
                sum_driftsinntekter = driftsinntekter

            # Operating Profit: driftsresultat.driftsresultat
            driftsresultat_val = driftsresultat_sec.get("driftsresultat")
            if isinstance(driftsresultat_val, dict):
                driftsresultat_val = driftsresultat_val.get("driftsresultat")

            # Net Profit: aarsresultat
            aarsresultat_val = resultat_section.get("aarsresultat")
            if isinstance(aarsresultat_val, dict):
                aarsresultat_val = aarsresultat_val.get("aarsresultat")

            # Balance sheet: Assets (eiendeler.sumEiendeler)
            eiendeler_sec = acc.get("eiendeler", {})
            sum_eiendeler = eiendeler_sec.get("sumEiendeler")
            if isinstance(sum_eiendeler, dict):
                sum_eiendeler = sum_eiendeler.get("sumEiendeler")

            # Balance sheet: Equity (egenkapitalGjeld.egenkapital.sumEgenkapital)
            egenkapital_sec = acc.get("egenkapitalGjeld", {}).get("egenkapital", {})
            sum_egenkapital = egenkapital_sec.get("sumEgenkapital")
            if isinstance(sum_egenkapital, dict):
                sum_egenkapital = sum_egenkapital.get("sumEgenkapital")

            fin_year = FinancialYear(
                year=fiscal_year,
                revenue=float(sum_driftsinntekter) if sum_driftsinntekter is not None else None,
                profit=float(driftsresultat_val) if driftsresultat_val is not None else None,
                operating_profit=float(driftsresultat_val) if driftsresultat_val is not None else None,
                net_profit=float(aarsresultat_val) if aarsresultat_val is not None else None,
                assets=float(sum_eiendeler) if sum_eiendeler is not None else None,
                equity=float(sum_egenkapital) if sum_egenkapital is not None else None,
                currency=currency,
                source_url=url,
            )
            financials.append(fin_year)

            # Produce immutable, verifiable facts for the latest reporting years
            if sum_driftsinntekter is not None:
                facts.append(
                    Fact(
                        field=f"revenue_{fiscal_year}",
                        value=float(sum_driftsinntekter),
                        source_url=url,
                        source_type="registry_regnskap",
                        retrieved_at=now_iso,
                        evidence=f"driftsresultat.driftsinntekter.sumDriftsinntekter: {sum_driftsinntekter} {currency}",
                        match_signals=["exact_orgnr_in_official_registry"],
                        confidence=1.0,
                        explanation=(
                            f"Verbatim operating revenue (driftsinntekter) for fiscal year {fiscal_year} "
                            f"filed with Regnskapsregisteret."
                        ),
                    )
                )

            if driftsresultat_val is not None:
                facts.append(
                    Fact(
                        field=f"operating_profit_{fiscal_year}",
                        value=float(driftsresultat_val),
                        source_url=url,
                        source_type="registry_regnskap",
                        retrieved_at=now_iso,
                        evidence=f"driftsresultat.driftsresultat: {driftsresultat_val} {currency}",
                        match_signals=["exact_orgnr_in_official_registry"],
                        confidence=1.0,
                        explanation=(
                            f"Verbatim operating profit (driftsresultat) for fiscal year {fiscal_year} "
                            f"filed with Regnskapsregisteret."
                        ),
                    )
                )

            if sum_egenkapital is not None:
                facts.append(
                    Fact(
                        field=f"equity_{fiscal_year}",
                        value=float(sum_egenkapital),
                        source_url=url,
                        source_type="registry_regnskap",
                        retrieved_at=now_iso,
                        evidence=f"egenkapitalGjeld.egenkapital.sumEgenkapital: {sum_egenkapital} {currency}",
                        match_signals=["exact_orgnr_in_official_registry"],
                        confidence=1.0,
                        explanation=(
                            f"Verbatim equity (egenkapital) as of year-end {fiscal_year} "
                            f"filed with Regnskapsregisteret."
                        ),
                    )
                )

            if sum_eiendeler is not None:
                facts.append(
                    Fact(
                        field=f"assets_{fiscal_year}",
                        value=float(sum_eiendeler),
                        source_url=url,
                        source_type="registry_regnskap",
                        retrieved_at=now_iso,
                        evidence=f"eiendeler.sumEiendeler: {sum_eiendeler} {currency}",
                        match_signals=["exact_orgnr_in_official_registry"],
                        confidence=1.0,
                        explanation=(
                            f"Verbatim total assets (sum eiendeler) for fiscal year {fiscal_year} "
                            f"filed with Regnskapsregisteret."
                        ),
                    )
                )

        return {
            "found": len(financials) > 0,
            "orgnr": orgnr,
            "financials": financials,
            "facts": facts,
            "cached": cached,
            "requests_made": 0 if cached else 1,
        }

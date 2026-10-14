import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from signalpost.config import settings
from signalpost.connectors.base import BaseConnector
from signalpost.schemas.profile import Fact, Role

logger = logging.getLogger(__name__)


class BrregEnheterConnector(BaseConnector):
    """
    Connector for Brønnøysundregistrene Enhetsregisteret API.
    License: Norsk lisens for offentlige data (NLOD 2.0) - Open Government Data.
    ToS: Free, public, authoritative government registry. Rate limits ~10-20 req/s.
    """

    def __init__(self):
        super().__init__(
            name="brreg_enheter",
            license_note="Norsk lisens for offentlige data (NLOD 2.0)",
            source_url_base=settings.brreg_enheter_base_url,
            cache_ttl_seconds=settings.cache_ttl_days_registry * 86400,
        )

    async def fetch_entity(
        self, client: httpx.AsyncClient, orgnr: str
    ) -> tuple[dict[str, Any] | None, bool]:
        """Fetches the primary entity record from /enheter/{orgnr}."""
        url = f"{self.source_url_base}/enheter/{orgnr}"
        data, cached, _status = await self.fetch_json(client, url)
        return data, cached

    async def fetch_roles(
        self, client: httpx.AsyncClient, orgnr: str
    ) -> tuple[dict[str, Any] | None, bool]:
        """Fetches board, executive and auditor roles from /enheter/{orgnr}/roller."""
        url = f"{self.source_url_base}/enheter/{orgnr}/roller"
        data, cached, _status = await self.fetch_json(client, url)
        return data, cached

    async def fetch(
        self, client: httpx.AsyncClient, orgnr: str
    ) -> dict[str, Any]:
        """
        Coordinates full registry lookup: main entity + roles.
        Returns a dictionary with raw data and structured facts/roles.
        """
        entity_data, entity_cached = await self.fetch_entity(client, orgnr)
        if not entity_data:
            return {"found": False, "orgnr": orgnr, "cached": entity_cached}

        roles_data, roles_cached = await self.fetch_roles(client, orgnr)

        now_iso = datetime.now(UTC).isoformat()
        facts: list[Fact] = []
        roles: list[Role] = []

        entity_url = f"{self.source_url_base}/enheter/{orgnr}"

        # 1. Legal Name
        raw_name = entity_data.get("navn", "")
        legal_name = " ".join(raw_name) if isinstance(raw_name, list) else str(raw_name or "").strip()
        if legal_name:
            facts.append(
                Fact(
                    field="legal_name",
                    value=legal_name,
                    source_url=entity_url,
                    source_type="registry_enheter",
                    retrieved_at=now_iso,
                    evidence=f"enhet.navn: {legal_name}",
                    match_signals=["exact_orgnr_in_official_registry"],
                    confidence=1.0,
                    explanation="Official registered legal company name from Brønnøysundregistrene.",
                )
            )

        # 2. Status (Bankrupt, Dissolved, Active)
        is_bankrupt = bool(entity_data.get("konkurs", False))
        is_liquidating = bool(entity_data.get("underAvvikling", False))
        is_forced_liquidation = bool(
            entity_data.get("underTvangsavviklingEllerTvangsopplosning", False)
        )
        slettedato = entity_data.get("slettedato")

        if is_bankrupt:
            status_val = "BANKRUPT"
        elif is_forced_liquidation or is_liquidating:
            status_val = "IN_LIQUIDATION"
        elif slettedato:
            status_val = "DISSOLVED"
        else:
            status_val = "ACTIVE"

        facts.append(
            Fact(
                field="status",
                value=status_val,
                source_url=entity_url,
                source_type="registry_enheter",
                retrieved_at=now_iso,
                evidence=f"konkurs={is_bankrupt}, underAvvikling={is_liquidating}, slettedato={slettedato}",
                match_signals=["exact_orgnr_in_official_registry"],
                confidence=1.0,
                explanation="Entity operating status determined from official legal registers.",
            )
        )

        # 3. Organization form
        org_form_dict = entity_data.get("organisasjonsform", {})
        org_form_code = org_form_dict.get("kode", "")
        org_form_desc = org_form_dict.get("beskrivelse", "")
        org_form_str = f"{org_form_desc} ({org_form_code})" if org_form_code else org_form_desc
        if org_form_str:
            facts.append(
                Fact(
                    field="org_form",
                    value=org_form_str,
                    source_url=entity_url,
                    source_type="registry_enheter",
                    retrieved_at=now_iso,
                    evidence=f"organisasjonsform: {org_form_dict}",
                    match_signals=["exact_orgnr_in_official_registry"],
                    confidence=1.0,
                    explanation="Official organizational structure registered with Foretaksregisteret/Enhetsregisteret.",
                )
            )

        # 4. Registration Date
        reg_date = entity_data.get("registreringsdatoEnhetsregisteret")
        if reg_date:
            facts.append(
                Fact(
                    field="registered_date",
                    value=reg_date,
                    source_url=entity_url,
                    source_type="registry_enheter",
                    retrieved_at=now_iso,
                    evidence=f"registreringsdatoEnhetsregisteret: {reg_date}",
                    match_signals=["exact_orgnr_in_official_registry"],
                    confidence=1.0,
                    explanation="Date the entity was first registered in Enhetsregisteret.",
                )
            )

        # 5. NACE Codes
        nace_list: list[str] = []
        for i in range(1, 4):
            key = f"naeringskode{i}"
            if entity_data.get(key):
                nk = entity_data[key]
                code_str = f"{nk.get('kode')} - {nk.get('beskrivelse')}"
                nace_list.append(code_str)

        if nace_list:
            facts.append(
                Fact(
                    field="nace_codes",
                    value=nace_list,
                    source_url=entity_url,
                    source_type="registry_enheter",
                    retrieved_at=now_iso,
                    evidence=f"naeringskoder: {nace_list}",
                    match_signals=["exact_orgnr_in_official_registry"],
                    confidence=1.0,
                    explanation="Standard Industrial Classification (NACE) registered with Statistics Norway (SSB).",
                )
            )

        # 6. Address
        business_addr = entity_data.get("forretningsadresse") or entity_data.get("postadresse") or {}
        address_lines = business_addr.get("adresse", [])
        post_nr = business_addr.get("postnummer", "")
        post_sted = business_addr.get("poststed", "")
        kommune = business_addr.get("kommune", "")
        kommunenummer = business_addr.get("kommunenummer", "")

        addr_parts = list(address_lines)
        if post_nr or post_sted:
            addr_parts.append(f"{post_nr} {post_sted}".strip())
        full_address = ", ".join(p for p in addr_parts if p)

        if full_address:
            facts.append(
                Fact(
                    field="address",
                    value=full_address,
                    source_url=entity_url,
                    source_type="registry_enheter",
                    retrieved_at=now_iso,
                    evidence=f"forretningsadresse: {business_addr}",
                    match_signals=["exact_orgnr_in_official_registry"],
                    confidence=1.0,
                    explanation="Official registered office address from Enhetsregisteret.",
                )
            )

        # 7. Employees
        employees = entity_data.get("antallAnsatte")
        if employees is not None:
            facts.append(
                Fact(
                    field="employees",
                    value=employees,
                    source_url=entity_url,
                    source_type="registry_enheter",
                    retrieved_at=now_iso,
                    evidence=f"antallAnsatte: {employees}",
                    match_signals=["exact_orgnr_in_official_registry"],
                    confidence=1.0,
                    explanation="Registered employee headcount reported to the Aa-register (NAV/SSB).",
                )
            )

        # 8. VAT / MVA Registered
        vat_reg = entity_data.get("registrertIMvaregisteret")
        if vat_reg is not None:
            facts.append(
                Fact(
                    field="vat_registered",
                    value=bool(vat_reg),
                    source_url=entity_url,
                    source_type="registry_enheter",
                    retrieved_at=now_iso,
                    evidence=f"registrertIMvaregisteret: {vat_reg}",
                    match_signals=["exact_orgnr_in_official_registry"],
                    confidence=1.0,
                    explanation="Registration status in Merverdiavgiftsregisteret (Norwegian VAT Register).",
                )
            )

        # 9. Registered Website
        hjemmeside = entity_data.get("hjemmeside")
        if hjemmeside:
            # Clean protocol if missing
            web_val = hjemmeside if "://" in hjemmeside else f"https://{hjemmeside}"
            facts.append(
                Fact(
                    field="website",
                    value=web_val,
                    source_url=entity_url,
                    source_type="registry_enheter",
                    retrieved_at=now_iso,
                    evidence=f"hjemmeside: {hjemmeside}",
                    match_signals=["exact_orgnr_in_official_registry"],
                    confidence=1.0,
                    explanation="Official corporate homepage URL explicitly declared in Enhetsregisteret.",
                )
            )

        # 10. Process Roles
        if roles_data and "rollegrupper" in roles_data:
            roles_url = f"{self.source_url_base}/enheter/{orgnr}/roller"
            for rgroup in roles_data.get("rollegrupper", []):
                for r_item in rgroup.get("roller", []):
                    r_type = r_item.get("type", {}).get("beskrivelse", "Rolle")
                    person = r_item.get("person", {})
                    name_dict = person.get("navn", {})
                    if name_dict:
                        f_name = name_dict.get("fornavn", "")
                        m_name = name_dict.get("mellomnavn", "")
                        l_name = name_dict.get("etternavn", "")
                        full_name = " ".join(p for p in [f_name, m_name, l_name] if p).strip()
                    else:
                        raw_navn = r_item.get("enhet", {}).get("navn", "")
                        if isinstance(raw_navn, list):
                            full_name = " ".join(str(p) for p in raw_navn).strip()
                        else:
                            full_name = str(raw_navn or "").strip()

                    if full_name:
                        role_obj = Role(
                            role=r_type,
                            name=full_name,
                            from_date=r_item.get("valgtAv", {}).get("valgtDato"),
                            resigned=bool(r_item.get("fratraadt", False)),
                        )
                        roles.append(role_obj)

                        # Add key roles (CEO / Board Chair) to verified facts
                        if any(k in r_type.lower() for k in ["daglig leder", "styrets leder", "leder"]):
                            facts.append(
                                Fact(
                                    field=f"role_{r_type.lower().replace(' ', '_')}",
                                    value=full_name,
                                    source_url=roles_url,
                                    source_type="registry_enheter",
                                    retrieved_at=now_iso,
                                    evidence=f"rolle: {r_type} -> {full_name}",
                                    match_signals=["exact_orgnr_in_official_registry"],
                                    confidence=1.0,
                                    explanation=f"Registered corporate appointment ({r_type}) from Brønnøysundregistrene.",
                                )
                            )

        return {
            "found": True,
            "orgnr": orgnr,
            "raw_entity": entity_data,
            "raw_roles": roles_data,
            "legal_name": legal_name,
            "status": status_val,
            "org_form": org_form_str,
            "registered_date": reg_date,
            "nace_codes": nace_list,
            "address": full_address,
            "municipality": kommune,
            "municipality_number": kommunenummer,
            "employees": employees,
            "vat_registered": vat_reg,
            "website": hjemmeside if not hjemmeside or "://" in hjemmeside else f"https://{hjemmeside}",
            "roles": roles,
            "facts": facts,
            "requests_made": (0 if entity_cached else 1) + (0 if roles_cached else 1),
            "cached": entity_cached and roles_cached,
        }

    async def search_entities(
        self, client: httpx.AsyncClient, query: str, size: int = 10
    ) -> list[dict[str, Any]]:
        """Searches Brønnøysundregistrene Enhetsregisteret by company name."""
        clean_q = query.strip()
        if not clean_q or len(clean_q) < 2:
            return []

        url = f"{self.source_url_base}/enheter"
        params = {"navn": clean_q, "size": min(size, 25)}

        headers = {
            "User-Agent": settings.user_agent,
            "Accept": "application/json",
        }
        try:
            resp = await client.get(url, params=params, headers=headers, timeout=6.0)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("_embedded", {}).get("enheter", [])
                results: list[dict[str, Any]] = []
                for item in items:
                    nr = item.get("organisasjonsnummer", "")
                    raw_name = item.get("navn", "")
                    name = " ".join(raw_name) if isinstance(raw_name, list) else str(raw_name).strip()
                    org_form = item.get("organisasjonsform", {}).get("kode", "")
                    addr_obj = item.get("forretningsadresse") or item.get("postadresse") or {}
                    kommune = addr_obj.get("kommune", "")
                    poststed = addr_obj.get("poststed", "")
                    is_bankrupt = bool(item.get("konkurs", False))
                    status = "BANKRUPT" if is_bankrupt else "ACTIVE"

                    results.append({
                        "org_number": nr,
                        "legal_name": name,
                        "org_form": org_form,
                        "status": status,
                        "municipality": kommune or poststed,
                        "nace_code": item.get("naeringskode1", {}).get("kode"),
                        "nace_description": item.get("naeringskode1", {}).get("beskrivelse"),
                    })
                return results
            return []
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Error querying Brreg entity search for '{query}': {e}")
            return []

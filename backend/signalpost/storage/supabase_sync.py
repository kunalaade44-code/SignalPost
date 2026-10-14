import logging
from typing import Any

import httpx
from signalpost.config import settings
from signalpost.schemas.profile import CompanyProfile

logger = logging.getLogger(__name__)


class SupabaseSync:
    """
    Syncs verified profiles and history records to Supabase PostgreSQL database via REST.
    """

    def __init__(self):
        raw_url = settings.supabase_url.strip() if settings.supabase_url else ""
        if raw_url.endswith("/rest/v1/"):
            self.base_url = raw_url[:-1]
        elif raw_url.endswith("/rest/v1"):
            self.base_url = raw_url
        elif raw_url:
            self.base_url = f"{raw_url.rstrip('/')}/rest/v1"
        else:
            self.base_url = ""

        self.api_key = settings.supabase_key.strip() if settings.supabase_key else ""

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url and self.api_key)

    async def sync_profile(self, profile: CompanyProfile) -> bool:
        """Upserts a company profile to Supabase."""
        if not self.is_configured:
            return False

        headers = {
            "apikey": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates",
        }

        payload: dict[str, Any] = {
            "org_number": profile.org_number,
            "legal_name": profile.legal_name,
            "status": profile.status,
            "org_form": profile.org_form,
            "registered_date": profile.registered_date,
            "nace_codes": profile.nace_codes,
            "address": profile.address,
            "municipality": profile.municipality,
            "municipality_number": profile.municipality_number,
            "employees": profile.employees,
            "vat_registered": profile.vat_registered,
            "website": profile.website,
            "contact": profile.contact.model_dump(),
            "roles": [r.model_dump() for r in profile.roles],
            "financials": [f.model_dump() for f in profile.financials],
            "description": profile.description,
            "social_links": profile.social_links,
            "facts_count": len(profile.facts),
            "profile_updated_at": profile.profile_updated_at,
            "last_checked_at": profile.last_checked_at,
            "history_ref": profile.history_ref,
            "raw_json": profile.model_dump(),
        }

        endpoint = f"{self.base_url}/company_profiles"

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(endpoint, headers=headers, json=payload)
                if resp.status_code in [200, 201]:
                    logger.info(f"Successfully synced profile {profile.org_number} to Supabase.")
                    return True
                else:
                    logger.warning(
                        f"Supabase sync returned status {resp.status_code}: {resp.text}"
                    )
                    return False
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Failed to sync profile to Supabase: {e}")
            return False


supabase_sync = SupabaseSync()

import logging
from typing import Any

import httpx
from signalpost.config import settings
from signalpost.connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class BrregUpdatesConnector(BaseConnector):
    """
    Connector for Brønnøysundregistrene Oppdaterte Enheter API.
    License: Norsk lisens for offentlige data (NLOD 2.0).
    Provides a real-time event feed of updated, new, or dissolved organizations.
    Used for intelligent cache invalidation and targeted profile refreshes.
    """

    def __init__(self):
        super().__init__(
            name="brreg_updates",
            license_note="Norsk lisens for offentlige data (NLOD 2.0)",
            source_url_base=f"{settings.brreg_enheter_base_url}/oppdateringer/enheter",
            cache_ttl_seconds=300,  # 5 minutes for dynamic event stream
        )

    async def fetch_updates(
        self,
        client: httpx.AsyncClient,
        since_date: str | None = None,
        page: int = 0,
        size: int = 100,
    ) -> dict[str, Any]:
        """
        Fetches a page of entity updates.
        Parameters:
        - since_date: ISO date string (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ)
        - page: page number
        - size: page size (max 100)
        """
        params: dict[str, Any] = {"page": page, "size": size}
        if since_date:
            params["dato"] = since_date

        data, cached, _status = await self.fetch_json(client, self.source_url_base, params=params)

        updates: list[dict[str, Any]] = []
        if data and "_embedded" in data and "oppdaterteEnheter" in data["_embedded"]:
            for item in data["_embedded"]["oppdaterteEnheter"]:
                updates.append(
                    {
                        "update_id": item.get("oppdateringsid"),
                        "date": item.get("dato"),
                        "orgnr": item.get("organisasjonsnummer"),
                        "change_type": item.get("endringstype"),
                    }
                )

        page_info = data.get("page", {}) if data else {}
        return {
            "updates": updates,
            "total_elements": page_info.get("totalElements", 0),
            "total_pages": page_info.get("totalPages", 0),
            "current_page": page_info.get("number", page),
            "cached": cached,
        }

    async def fetch(self, client: httpx.AsyncClient, *args: Any, **kwargs: Any) -> Any:
        return await self.fetch_updates(client, *args, **kwargs)

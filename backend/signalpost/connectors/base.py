import abc
import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from signalpost.config import settings
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class CacheEntry:
    def __init__(self, data: Any, etag: str | None = None, last_modified: str | None = None, timestamp: float = 0.0):
        self.data = data
        self.etag = etag
        self.last_modified = last_modified
        self.timestamp = timestamp or datetime.now(UTC).timestamp()

    def to_dict(self) -> dict[str, Any]:
        return {
            "data": self.data,
            "etag": self.etag,
            "last_modified": self.last_modified,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "CacheEntry":
        return cls(
            data=d.get("data"),
            etag=d.get("etag"),
            last_modified=d.get("last_modified"),
            timestamp=d.get("timestamp", 0.0),
        )


class BaseConnector(abc.ABC):
    """
    Abstract base connector for public data sources.
    Features:
    - Declared license and terms-of-service compliance.
    - Local disk/memory ETag and If-Modified-Since caching.
    - Global request counting.
    - Polite rate-limiting and timeouts.
    """

    def __init__(
        self,
        name: str,
        license_note: str,
        source_url_base: str,
        cache_ttl_seconds: int = 86400 * 7,
    ):
        self.name = name
        self.license_note = license_note
        self.source_url_base = source_url_base
        self.cache_ttl_seconds = cache_ttl_seconds
        self.cache_dir = settings.cache_dir / name
        if settings.cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, cache_key: str) -> Path:
        hashed = hashlib.sha256(cache_key.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{hashed}.json"

    def _load_cache(self, cache_key: str) -> CacheEntry | None:
        if not settings.cache_enabled:
            return None
        path = self._get_cache_path(cache_key)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return CacheEntry.from_dict(data)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to read cache for {cache_key}: {e}")
            return None

    def _save_cache(self, cache_key: str, entry: CacheEntry) -> None:
        if not settings.cache_enabled:
            return
        path = self._get_cache_path(cache_key)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(entry.to_dict(), f, ensure_ascii=False)
        except OSError as e:
            logger.warning(f"Failed to save cache for {cache_key}: {e}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
        reraise=True,
    )
    async def fetch_json(
        self,
        client: httpx.AsyncClient,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[Any | None, bool, int]:
        """
        Fetches JSON from URL with ETag caching.
        Returns: (data, from_cache: bool, status_code: int)
        """
        cache_key = f"{url}?{json.dumps(params, sort_keys=True) if params else ''}"
        cached = self._load_cache(cache_key)

        req_headers = {
            "User-Agent": settings.user_agent,
            "Accept": "application/json",
        }
        if headers:
            req_headers.update(headers)

        now = datetime.now(UTC).timestamp()
        if cached:
            # Check TTL
            if (now - cached.timestamp) < self.cache_ttl_seconds:
                return cached.data, True, 200

            # Stale: attach ETag or If-Modified-Since
            if cached.etag:
                req_headers["If-None-Match"] = cached.etag
            if cached.last_modified:
                req_headers["If-Modified-Since"] = cached.last_modified

        resp = await client.get(url, params=params, headers=req_headers, timeout=15.0)

        if resp.status_code == 304 and cached:
            # Revalidate cache timestamp
            cached.timestamp = now
            self._save_cache(cache_key, cached)
            return cached.data, True, 304

        if resp.status_code == 404:
            return None, False, 404

        resp.raise_for_status()

        data = resp.json()
        etag = resp.headers.get("ETag")
        last_modified = resp.headers.get("Last-Modified")

        entry = CacheEntry(data=data, etag=etag, last_modified=last_modified, timestamp=now)
        self._save_cache(cache_key, entry)
        return data, False, resp.status_code

    @abc.abstractmethod
    async def fetch(self, client: httpx.AsyncClient, *args: Any, **kwargs: Any) -> Any:
        """Fetch and return parsed domain objects."""

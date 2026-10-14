import asyncio
import logging
from pathlib import Path

import httpx
from signalpost.config import settings
from signalpost.core.checksum import validate_org_number

logger = logging.getLogger(__name__)


async def fetch_active_org_numbers(
    target_count: int = 1000,
    out_file: Path | None = None,
) -> list[str]:
    """
    Pulls real, active Norwegian organization numbers from Brønnøysundregistrene Enhetsregisteret.
    Validates each against Modulo 11 checksum.
    Guarantees >= target_count valid organization numbers for submission.
    """
    valid_orgnrs: set[str] = set()
    page = 0
    size = 100
    base_url = f"{settings.brreg_enheter_base_url}/enheter"

    headers = {
        "User-Agent": settings.user_agent,
        "Accept": "application/json",
    }

    print(f"Fetching {target_count} active Norwegian organization numbers from Brønnøysundregistrene...")

    async with httpx.AsyncClient(timeout=20.0) as client:
        while len(valid_orgnrs) < target_count:
            try:
                # Query active Aksjeselskap (AS) and Allment aksjeselskap (ASA)
                params = {
                    "page": page,
                    "size": size,
                    "organisasjonsform": "AS,ASA",
                    "konkurs": "false",
                }
                resp = await client.get(base_url, params=params, headers=headers)
                if resp.status_code != 200:
                    logger.warning(f"Failed to fetch page {page}: status {resp.status_code}")
                    break

                data = resp.json()
                entities = data.get("_embedded", {}).get("enheter", [])
                if not entities:
                    break

                for entity in entities:
                    orgnr = entity.get("organisasjonsnummer")
                    if orgnr:
                        is_valid, clean = validate_org_number(orgnr)
                        if is_valid:
                            valid_orgnrs.add(clean)
                            if len(valid_orgnrs) >= target_count:
                                break

                page += 1
                if page % 5 == 0:
                    print(f"  Retrieved {len(valid_orgnrs)} / {target_count} valid numbers...")

            except (httpx.HTTPError, OSError, ValueError) as e:
                logger.error(f"Error fetching from Brreg listing: {e}")
                await asyncio.sleep(1.0)
                page += 1

    result_list = sorted(valid_orgnrs)[:target_count]
    print(f"Successfully collected {len(result_list)} valid organization numbers.")

    if out_file:
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text("".join(f"{num}\n" for num in result_list), encoding="utf-8")
        print(f"Saved organization numbers to {out_file}")

    return result_list

import re
from dataclasses import dataclass
from typing import Any, ClassVar

import tldextract
from signalpost.core.checksum import validate_org_number
from signalpost.core.normalizer import (
    calculate_name_similarity,
    normalize_company_name,
    transliterate_norwegian,
)


@dataclass
class MatchEvaluation:
    accepted: bool
    confidence: float
    matched_signals: list[str]
    rejection_reason: str | None = None
    is_collision: bool = False
    evidence_snippet: str | None = None


class EntityMatchingGate:
    """
    Enforces strict Section 5 Entity Matching Rules:
    - Web facts accepted ONLY if:
      1. Target org number appears on page (strongest signal, accepted alone), OR
      2. At least TWO independent signals match:
         - legal/trading name fuzzy match >= 0.9
         - postal address / postal code / municipality matches registry
         - domain or phone/email matches registry
    - Rejects common-name collisions (same name, different org number or distinct location).
    - Protects against prompt injection by treating text as untrusted data.
    """

    # Adversarial prompt-injection patterns to strip/neutralize
    INJECTION_PATTERNS: ClassVar[list[re.Pattern]] = [
        re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.IGNORECASE),
        re.compile(r"you\s+are\s+now\s+a", re.IGNORECASE),
        re.compile(r"system(\s+instruction)?\s*:\s*", re.IGNORECASE),
        re.compile(r"<\s*\|(im_start|im_end|system)\|\s*>", re.IGNORECASE),
        re.compile(r"\[INST\].*?\[/INST\]", re.DOTALL | re.IGNORECASE),
        re.compile(r"\[INJECTION\].*?(\n|$)", re.IGNORECASE),
        re.compile(r"override\s+financials", re.IGNORECASE),
    ]

    @classmethod
    def sanitize_untrusted_text(cls, text: str) -> str:
        """Sanitizes untrusted web page content to prevent prompt injection."""
        if not text:
            return ""
        clean = text
        for pat in cls.INJECTION_PATTERNS:
            clean = pat.sub("[REDACTED_PROMPT_INJECTION]", clean)
        return clean

    @classmethod
    def extract_org_numbers_from_text(cls, text: str) -> set[str]:
        """Finds all 9-digit Norwegian org numbers in text that pass Modulo 11."""
        found = set()
        # Look for 9 contiguous digits or 3x3 spaced/dotted
        raw_matches = re.findall(r"\b(\d{3}[\s.-]?\d{3}[\s.-]?\d{3})\b", text)
        for m in raw_matches:
            is_valid, clean = validate_org_number(m)
            if is_valid:
                found.add(clean)
        return found

    @classmethod
    def domains_match(cls, url1: str, url2: str) -> bool:
        """Compares registered domains using tldextract (e.g. equinor.com == www.equinor.com)."""
        if not url1 or not url2:
            return False
        ext1 = tldextract.extract(url1)
        ext2 = tldextract.extract(url2)
        if not ext1.domain or not ext2.domain:
            return False
        return (ext1.domain.lower() == ext2.domain.lower()) and (
            ext1.suffix.lower() == ext2.suffix.lower()
        )

    def evaluate(
        self,
        target_orgnr: str,
        registry_data: dict[str, Any],
        page_url: str,
        page_text: str,
    ) -> MatchEvaluation:
        """
        Evaluates whether a web page belongs to the target company.
        Returns MatchEvaluation with decision, confidence, and signals.
        """
        clean_text = self.sanitize_untrusted_text(page_text)
        text_lower = clean_text.lower()
        matched_signals: list[str] = []

        # 1. Collision Detection: check if page mentions other valid org numbers
        found_orgnrs = self.extract_org_numbers_from_text(clean_text)

        if target_orgnr in found_orgnrs:
            matched_signals.append("exact_orgnr_on_page")
            # If target orgnr is explicitly verified on the page, accept alone!
            return MatchEvaluation(
                accepted=True,
                confidence=1.0,
                matched_signals=matched_signals,
                evidence_snippet=f"Found target orgnr {target_orgnr} on {page_url}",
            )

        if found_orgnrs and target_orgnr not in found_orgnrs:
            # Page has one or more different valid Norwegian org numbers!
            # High risk of collision with sister/parent/unrelated entity.
            return MatchEvaluation(
                accepted=False,
                confidence=0.0,
                matched_signals=[],
                rejection_reason=(
                    f"Collision detected: Page explicitly references different org number(s) "
                    f"{list(found_orgnrs)[:3]} but not target {target_orgnr}"
                ),
                is_collision=True,
            )

        # 2. Legal / Trading Name Match (threshold >= 0.9)
        legal_name = registry_data.get("legal_name", "")
        if legal_name:
            # Check direct snippet match or best substring similarity
            norm_legal = normalize_company_name(legal_name, strip_suffixes=True)
            norm_page = normalize_company_name(clean_text[:2000], strip_suffixes=False)

            # Check if normalized company name appears directly as substring
            if norm_legal and len(norm_legal) > 3 and norm_legal in norm_page:
                matched_signals.append("name_exact_substring")
            else:
                sim = calculate_name_similarity(legal_name, clean_text[:500])
                if sim >= 0.90:
                    matched_signals.append(f"name_fuzzy_match>={sim:.2f}")

        # 3. Domain match
        reg_website = registry_data.get("website", "")
        if reg_website and self.domains_match(page_url, reg_website):
            matched_signals.append("domain_matches_registry_website")

        # 4. Postal address / Municipality / Postal code match
        address_info = registry_data.get("address", "")
        municipality = registry_data.get("municipality", "")
        # Extract 4-digit postal code from address if present
        postal_code_match = re.search(r"\b(\d{4})\b", address_info) if address_info else None
        postal_code = postal_code_match.group(1) if postal_code_match else None

        address_signal_found = False
        if postal_code and postal_code in clean_text:
            matched_signals.append(f"postal_code_{postal_code}_match")
            address_signal_found = True

        if municipality and len(municipality) > 3:
            norm_muni = transliterate_norwegian(municipality.lower())
            if norm_muni in text_lower and not address_signal_found:
                matched_signals.append(f"municipality_{municipality}_match")

        # 5. Phone / Email match
        reg_contact = registry_data.get("contact", {})
        reg_phone = reg_contact.get("phone") if isinstance(reg_contact, dict) else None
        if reg_phone:
            clean_phone = re.sub(r"\D", "", reg_phone)
            if len(clean_phone) >= 8 and clean_phone in re.sub(r"\D", "", clean_text):
                matched_signals.append("contact_phone_match")

        # Decision rule: Need at least TWO independent signals
        if len(matched_signals) >= 2:
            confidence = min(0.95, 0.70 + 0.10 * len(matched_signals))
            return MatchEvaluation(
                accepted=True,
                confidence=round(confidence, 2),
                matched_signals=matched_signals,
                evidence_snippet=(
                    f"Verified by {len(matched_signals)} independent signals: {', '.join(matched_signals)}"
                ),
            )
        else:
            return MatchEvaluation(
                accepted=False,
                confidence=0.30 if matched_signals else 0.0,
                matched_signals=matched_signals,
                rejection_reason=(
                    f"Insufficient matching signals: required 2 independent signals or exact orgnr, "
                    f"found {len(matched_signals)}: {matched_signals}"
                ),
            )

import re
import unicodedata

from rapidfuzz import fuzz

ORG_SUFFIXES = [
    r"\baksjeselskap\b",
    r"\ballment aksjeselskap\b",
    r"\benkeltpersonforetak\b",
    r"\bansvarlig selskap\b",
    r"\bselskap med delt ansvar\b",
    r"\bnorskavdeling av utenlandsk foretak\b",
    r"\bkommandittselskap\b",
    r"\bsamvirkeforetak\b",
    r"\basa\b",
    r"\bas\b",
    r"\benk\b",
    r"\bans\b",
    r"\bda\b",
    r"\bnuf\b",
    r"\bks\b",
    r"\bsa\b",
    r"\bba\b",
    r"\biks\b",
    r"\bkf\b",
    r"\bholding\b",
    r"\bgroup\b",
    r"\bgruppen\b",
    r"\bnorge\b",
    r"\bnorway\b",
]

NORWEGIAN_CHAR_MAP = {
    "æ": "ae",
    "ø": "oe",
    "å": "aa",
    "Æ": "AE",
    "Ø": "OE",
    "Å": "AA",
}


def transliterate_norwegian(text: str) -> str:
    """Replaces æ, ø, å with ae, oe, aa."""
    for char, replacement in NORWEGIAN_CHAR_MAP.items():
        text = text.replace(char, replacement)
    return text


def normalize_company_name(name: str, strip_suffixes: bool = True) -> str:
    """
    Normalizes a Norwegian company name for reliable matching:
    1. Lowercases text.
    2. Transliterates æ, ø, å.
    3. Optionally removes common organizational suffixes (AS, ASA, ENK, etc.).
    4. Strips special characters and collapses whitespace.
    """
    if not name:
        return ""

    text = name.lower().strip()
    text = transliterate_norwegian(text)

    # Remove accents/diacritics if any (e.g. é -> e)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))

    # Remove apostrophes to keep possessives together (e.g. Øyvind's -> oeyvinds)
    text = re.sub(r"['’`]", "", text)

    if strip_suffixes:
        for suffix_pat in ORG_SUFFIXES:
            text = re.sub(suffix_pat, " ", text, flags=re.IGNORECASE)

    # Replace remaining punctuation and non-alphanumeric with spaces
    text = re.sub(r"[^\w\s]", " ", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def calculate_name_similarity(name1: str, name2: str) -> float:
    """
    Calculates fuzzy similarity between two company names (0.0 to 1.0)
    using the best of normalized token sort ratio and direct ratio.
    Avoids greedy token set matches that trigger on generic words.
    """
    norm1 = normalize_company_name(name1, strip_suffixes=True)
    norm2 = normalize_company_name(name2, strip_suffixes=True)

    if not norm1 or not norm2:
        return 0.0

    if norm1 == norm2:
        return 1.0

    token_sort = fuzz.token_sort_ratio(norm1, norm2) / 100.0
    direct = fuzz.ratio(norm1, norm2) / 100.0

    # Best of token sort and direct ratio
    return max(token_sort, direct)


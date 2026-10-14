import re

MOD11_WEIGHTS = [3, 2, 7, 6, 5, 4, 3, 2]


def validate_org_number(orgnr: str) -> tuple[bool, str]:
    """
    Validates a 9-digit Norwegian organization number using Modulo 11 checksum.
    Returns: (is_valid: bool, reason_or_clean_number: str)
    """
    if not isinstance(orgnr, str):
        return False, "Organization number must be a string"

    clean = re.sub(r"[\s.-]", "", orgnr.strip())

    if len(clean) != 9:
        return False, f"Organization number must be exactly 9 digits, got {len(clean)}"

    if not clean.isdigit():
        return False, "Organization number must contain digits only"

    digits = [int(d) for d in clean]
    weighted_sum = sum(d * w for d, w in zip(digits[:8], MOD11_WEIGHTS))
    remainder = weighted_sum % 11

    if remainder == 0:
        expected_control = 0
    elif remainder == 1:
        # Modulo 11 does not permit a control digit of 10
        return False, "Checksum remainder 1 cannot produce a single valid control digit"
    else:
        expected_control = 11 - remainder

    actual_control = digits[8]
    if actual_control != expected_control:
        return (
            False,
            f"Checksum mismatch: control digit is {actual_control}, expected {expected_control}"
        )

    return True, clean


def calculate_control_digit(first_8_digits: str) -> int:
    """
    Computes the 9th checksum digit for 8 base digits.
    Raises ValueError if remainder is 1 (unusable sequence).
    """
    if len(first_8_digits) != 8 or not first_8_digits.isdigit():
        raise ValueError("Must provide exactly 8 digits")

    digits = [int(d) for d in first_8_digits]
    weighted_sum = sum(d * w for d, w in zip(digits, MOD11_WEIGHTS))
    remainder = weighted_sum % 11

    if remainder == 0:
        return 0
    elif remainder == 1:
        raise ValueError("Invalid number sequence (produces remainder 1)")
    else:
        return 11 - remainder

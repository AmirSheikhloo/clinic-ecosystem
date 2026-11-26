"""Iranian National ID (کد ملی) syntactic validation — not official identity verification."""

from __future__ import annotations

_PERSIAN = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def normalize_ascii_digits(value: str) -> str:
    return value.translate(_PERSIAN).strip()


def normalize_national_id(value: str) -> str:
    """Return 10 ASCII digits with leading zeros preserved; raise ValueError if impossible."""
    digits = "".join(ch for ch in normalize_ascii_digits(value) if ch.isdigit())
    if len(digits) > 10:
        raise ValueError("national_id_too_long")
    if not digits:
        raise ValueError("national_id_empty")
    return digits.zfill(10)


def is_valid_national_id_checksum(value: str) -> bool:
    """Official check-digit algorithm over 10 ASCII digits."""
    try:
        digits = normalize_national_id(value)
    except ValueError:
        return False
    if len(digits) != 10 or digits == digits[0] * 10:
        return False
    total = sum(int(digits[i]) * (10 - i) for i in range(9))
    rem = total % 11
    check = int(digits[9])
    return check == rem if rem < 2 else check == 11 - rem

import pytest
from clinic_ecosystem.domain.identity.national_id import (
    is_valid_national_id_checksum,
    normalize_national_id,
)


def test_normalize_preserves_leading_zeros_and_persian_digits():
    assert normalize_national_id("۰۰۱۳۵۴۲۴۱۹") == "0013542419"


@pytest.mark.parametrize(
    "value,ok",
    [
        ("0013542419", True),
        ("0000000000", False),
        ("123", False),
        ("abcdefghij", False),
    ],
)
def test_checksum(value, ok):
    assert is_valid_national_id_checksum(value) is ok

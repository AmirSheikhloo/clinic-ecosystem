"""Pure v3.0.1 PII contract tests; no KMS/DB execution or Gate A claims."""
from __future__ import annotations

import hashlib
import hmac
import uuid
from dataclasses import FrozenInstanceError

import pytest

from clinic_ecosystem.shared_kernel.pii_contracts import (
    HmacKey,
    aad_v1,
    dual_identifier_lookup_hmac,
    identifier_input,
    identifier_lookup_hmac,
    require_e164,
    map_identifier_digits,
    normalized_iran_national_id,
)

TENANT = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
PERSON = uuid.UUID("11111111-1111-1111-1111-111111111111")
RECORD = uuid.UUID("b1000000-0000-0000-0000-000000000001")
KEY_ONE = HmacKey(1, b"x" * 32)
KEY_TWO = HmacKey(2, b"y" * 32)


def _input(value: str = "0012345678") -> bytes:
    return identifier_input(
        tenant_id=TENANT,
        id_type= "IR_NATIONAL_ID" ,
        issuing_country_or_authority=" ir ",
        normalized_identifier_value=value,
    )


def test_clause767_exact_input_preserves_leading_zeroes():
    assert _input() == (
        b"aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa|IR_NATIONAL_ID|IR|0012345678"
    )
    assert _input("0012") != _input("12")


def test_lookup_is_real_versioned_hmac_sha256_not_unkeyed_hash():
    canonical = _input()
    value = identifier_lookup_hmac(key=KEY_ONE, canonical_input=canonical)
    assert value.key_version == 1
    assert len(value.digest) == 32
    assert value.digest == hmac.new(b"x" * 32, canonical, hashlib.sha256).digest()
    assert value.digest != hashlib.sha256(canonical).digest()


def test_dual_write_hashes_share_exact_input_but_have_distinct_versions():
    active, nxt = dual_identifier_lookup_hmac(
        active_key=KEY_ONE, next_key=KEY_TWO, canonical_input=_input()
    )
    assert active.key_version == 1 and nxt.key_version == 2
    assert active.digest != nxt.digest


@pytest.mark.parametrize(
    "keys",
    [(KEY_ONE, KEY_ONE), (KEY_ONE, HmacKey(2, b"x" * 32))],
)
def test_rotation_rejects_same_version_or_reused_secret(keys):
    with pytest.raises(ValueError):
        dual_identifier_lookup_hmac(
            active_key=keys[0], next_key=keys[1], canonical_input=_input()
        )


@pytest.mark.parametrize("version,secret", [(0, b"x" * 32), (32768, b"x" * 32), (True, b"x" * 32), (1, b"x" * 16)])
def test_key_version_and_entropy_length_fail_closed(version, secret):
    with pytest.raises(ValueError):
        HmacKey(version, secret)


def test_secret_is_hidden_from_repr_and_key_is_immutable():
    assert "xxxx" not in repr(KEY_ONE)
    with pytest.raises(FrozenInstanceError):
        KEY_ONE.version = 7


@pytest.mark.parametrize("invalid", ["", " 001234 ", "foo|bar", "x\nvalue"])
def test_identifier_input_rejects_ambiguous_or_unvalidated_values(invalid):
    with pytest.raises(ValueError):
        _input(invalid)


def test_identifier_input_rejects_untyped_tenant():
    with pytest.raises(TypeError):
        identifier_input(
            tenant_id=str(TENANT), id_type="NATIONAL",  # type: ignore[arg-type]
            issuing_country_or_authority="IR",
            normalized_identifier_value="0001",
        )


def test_aad_v1_matches_129_byte_source_pinned_candidate_kat():
    value = aad_v1(
        tenant_id=TENANT, original_person_id=PERSON, record_id=RECORD,
        id_type_or_field_type="PHONE_E164", issuing_country_or_authority="E164",
    )
    expected = (
        "v1|aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa|"
        "11111111-1111-1111-1111-111111111111|"
        "b1000000-0000-0000-0000-000000000001|PHONE_E164|E164"
    )
    assert value == expected.encode("utf-8")
    assert len(value) == 129
    assert value.hex() == (
        "76317c61616161616161612d616161612d616161612d616161612d6161616161616161616161617c"
        "31313131313131312d313131312d313131312d313131312d3131313131313131313131317c"
        "62313030303030302d303030302d303030302d303030302d3030303030303030303030317c"
        "50484f4e455f453136347c45313634"
    )


@pytest.mark.parametrize(
    "changed",
    [
        {"tenant_id": uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")},
        {"original_person_id": uuid.UUID("22222222-2222-2222-2222-222222222222")},
        {"record_id": uuid.UUID("b2000000-0000-0000-0000-000000000002")},
        {"id_type_or_field_type": "EMAIL"},
        {"issuing_country_or_authority": "LOCAL"},
    ],
)
def test_aad_context_transplant_changes_bytes(changed):
    base = dict(
        tenant_id=TENANT, original_person_id=PERSON, record_id=RECORD,
        id_type_or_field_type="PHONE_E164", issuing_country_or_authority="E164",
    )
    actual = aad_v1(**base)
    assert aad_v1(**{**base, **changed}) != actual


@pytest.mark.parametrize("invalid", ["+0123", "1234", "+1 234", "+1234567890123456", "+1\n", "＋123", "+١٢٣"])
def test_strict_e164_rejects_unverified_format(invalid):
    with pytest.raises(ValueError):
        require_e164(invalid)


@pytest.mark.parametrize("valid", ["+123", "+123456789012345", "+989121234567"])
def test_strict_e164_accepts_prespecified_format_not_verification(valid):
    assert require_e164(valid) == valid



def test_identifier_rejects_persian_and_arabic_digits_until_type_normalized():
    for value in ("۰۰۱۲", "٠٠١٢"):
        with pytest.raises(ValueError):
            _input(value)


def test_aad_rejects_whitespace_in_signed_token_contract():
    with pytest.raises(ValueError):
        aad_v1(
            tenant_id=TENANT, original_person_id=PERSON, record_id=RECORD,
            id_type_or_field_type=" PHONE_E164 ", issuing_country_or_authority="E164",
        )



def test_clause765_digit_mapping_preserves_leading_zeroes():
    assert map_identifier_digits("۰۰۱۲-٣٤") == "0012-34"
    assert map_identifier_digits("0012") == "0012"
    assert _input(map_identifier_digits("۰۰۱۲")) == _input("0012")


def test_digit_mapping_is_not_identifier_type_verification():
    # Check-digit, visual separators, authority and length remain separate.
    assert map_identifier_digits("۱۲-۳") == "12-3"
    with pytest.raises(TypeError):
        map_identifier_digits(None)  # type: ignore[arg-type]



@pytest.mark.parametrize("valid", ["0084575948", "۰۰۸۴۵۷۵۹۴۸", "٠٠٨٤٥٧٥٩٤٨"])
def test_iran_national_id_syntactic_mod11_preserves_leading_zeroes(valid):
    assert normalized_iran_national_id(valid) == "0084575948"


@pytest.mark.parametrize("bad", ["0084575949", "0000000000", "1111111111", "008457594", "00845759481", "008 4575948", "008-4575948", "abc84575948"])
def test_iran_national_id_rejects_invalid_checksum_or_unapproved_separators(bad):
    with pytest.raises(ValueError):
        normalized_iran_national_id(bad)


def test_iran_national_id_validation_does_not_assert_official_verification():
    normalized = normalized_iran_national_id("۰۰۸۴۵۷۵۹۴۸")
    assert _input(normalized).endswith(b"|0084575948")
    # No verification timestamp, official source, or identity ownership follows.



@pytest.mark.parametrize("bad_type", ["IRAN_NATIONAL_ID", "OTHER", ""])
def test_identifier_type_must_match_frozen_tp0002_enum(bad_type):
    with pytest.raises(ValueError):
        identifier_input(
            tenant_id=TENANT,
            id_type=bad_type,
            issuing_country_or_authority="IR",
            normalized_identifier_value="0012345678",
        )


@pytest.mark.parametrize("invalid_version", [0, -1, True, 32768])
def test_lookup_digest_version_fails_closed(invalid_version):
    from clinic_ecosystem.shared_kernel.pii_contracts import LookupDigest
    with pytest.raises(ValueError):
        LookupDigest(invalid_version, b"x" * 32)


@pytest.mark.parametrize("phone, expected_mask", [
    ("+12", "****"),
    ("+123", "****"),
    ("+1234", "****"),
    ("+1234567", "****4567"),
    ("+989121234567", "****4567"),
])
def test_masked_e164_never_exposes_all_digits(phone, expected_mask):
    from clinic_ecosystem.shared_kernel.pii_contracts import mask_phone_e164
    assert mask_phone_e164(phone) == expected_mask

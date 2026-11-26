"""Unit tests for AES-GCM PII seal/open and domain-separated HMAC (spec §52)."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from cryptography.exceptions import InvalidTag

from clinic_ecosystem.infrastructure.crypto.pii_box import (
    CryptoUnavailable,
    load_pii_keys,
    mask_national_id,
    normalize_phone_e164,
    open_identifier,
    open_phone,
    phone_lookup_digest,
    seal_identifier,
    seal_phone,
)

AES = "00" * 32
HMAC = "11" * 32
TENANT = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
PERSON = UUID("11111111-1111-1111-1111-111111111111")
RECORD = UUID("b1000000-0000-0000-0000-000000000001")


@pytest.fixture()
def keys(monkeypatch):
    monkeypatch.setenv("CLINIC_ENV", "test")
    monkeypatch.setenv("CLINIC_PII_AES_KEY_HEX", AES)
    monkeypatch.setenv("CLINIC_PII_HMAC_KEY_HEX", HMAC)
    return load_pii_keys()


def test_load_keys_refuses_when_missing(monkeypatch):
    monkeypatch.setenv("CLINIC_ENV", "test")
    monkeypatch.delenv("CLINIC_PII_AES_KEY_HEX", raising=False)
    monkeypatch.delenv("CLINIC_PII_AES_KEY", raising=False)
    monkeypatch.delenv("CLINIC_PII_HMAC_KEY_HEX", raising=False)
    monkeypatch.delenv("CLINIC_PII_HMAC_KEY", raising=False)
    with pytest.raises(CryptoUnavailable):
        load_pii_keys()


def test_load_keys_refuses_production(monkeypatch):
    monkeypatch.setenv("CLINIC_ENV", "production")
    monkeypatch.setenv("CLINIC_PII_AES_KEY_HEX", AES)
    monkeypatch.setenv("CLINIC_PII_HMAC_KEY_HEX", HMAC)
    with pytest.raises(CryptoUnavailable):
        load_pii_keys()


def test_hmac_key_allows_longer_than_32(monkeypatch):
    monkeypatch.setenv("CLINIC_ENV", "test")
    monkeypatch.setenv("CLINIC_PII_AES_KEY_HEX", AES)
    monkeypatch.setenv("CLINIC_PII_HMAC_KEY_HEX", "22" * 48)
    loaded = load_pii_keys()
    assert len(loaded.hmac_key) == 48


def test_national_id_roundtrip(keys):
    sealed = seal_identifier(
        tenant_id=TENANT,
        person_id=PERSON,
        record_id=RECORD,
        id_type="IR_NATIONAL_ID",
        issuing_country_or_authority="IR",
        normalized_value="0013542419",
        keys=keys,
    )
    assert sealed.masked_display == "******2419"
    assert len(sealed.nonce_96bit) == 12
    assert len(sealed.auth_tag_128bit) == 16
    assert sealed.aad_version == 1
    assert sealed.encryption_key_version == 1
    assert b"0013542419" not in sealed.ciphertext
    assert (
        open_identifier(
            tenant_id=TENANT,
            person_id=PERSON,
            record_id=RECORD,
            id_type="IR_NATIONAL_ID",
            issuing_country_or_authority="IR",
            ciphertext=sealed.ciphertext,
            nonce_96bit=sealed.nonce_96bit,
            auth_tag_128bit=sealed.auth_tag_128bit,
            keys=keys,
        )
        == "0013542419"
    )


def test_aad_transplant_fails(keys):
    sealed = seal_identifier(
        tenant_id=TENANT,
        person_id=PERSON,
        record_id=RECORD,
        id_type="IR_NATIONAL_ID",
        issuing_country_or_authority="IR",
        normalized_value="0013542419",
        keys=keys,
    )
    with pytest.raises(InvalidTag):
        open_identifier(
            tenant_id=uuid4(),
            person_id=PERSON,
            record_id=RECORD,
            id_type="IR_NATIONAL_ID",
            issuing_country_or_authority="IR",
            ciphertext=sealed.ciphertext,
            nonce_96bit=sealed.nonce_96bit,
            auth_tag_128bit=sealed.auth_tag_128bit,
            keys=keys,
        )


def test_shared_phone_multi_match_digest(keys):
    e164 = normalize_phone_e164("09121234567")
    assert e164 == "+989121234567"
    person_b = UUID("22222222-2222-2222-2222-222222222222")
    record_b = UUID("b2000000-0000-0000-0000-000000000002")
    sealed_a = seal_phone(
        tenant_id=TENANT, person_id=PERSON, record_id=RECORD, e164=e164, keys=keys
    )
    sealed_b = seal_phone(
        tenant_id=TENANT, person_id=person_b, record_id=record_b, e164=e164, keys=keys
    )
    assert sealed_a.lookup_hmac == sealed_b.lookup_hmac
    assert sealed_a.ciphertext != sealed_b.ciphertext
    assert sealed_a.masked_display == "****4567"
    assert phone_lookup_digest(tenant_id=TENANT, e164=e164, keys=keys) == sealed_a.lookup_hmac
    assert (
        open_phone(
            tenant_id=TENANT,
            person_id=PERSON,
            record_id=RECORD,
            ciphertext=sealed_a.ciphertext,
            nonce_96bit=sealed_a.nonce_96bit,
            auth_tag_128bit=sealed_a.auth_tag_128bit,
            keys=keys,
        )
        == e164
    )


def test_phone_aad_mismatch(keys):
    sealed = seal_phone(
        tenant_id=TENANT, person_id=PERSON, record_id=RECORD, e164="+989121234567", keys=keys
    )
    with pytest.raises(InvalidTag):
        open_phone(
            tenant_id=TENANT,
            person_id=uuid4(),
            record_id=RECORD,
            ciphertext=sealed.ciphertext,
            nonce_96bit=sealed.nonce_96bit,
            auth_tag_128bit=sealed.auth_tag_128bit,
            keys=keys,
        )


def test_mask_national_id():
    assert mask_national_id("0013542419") == "******2419"

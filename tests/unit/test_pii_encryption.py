"""AES-GCM synthetic-only contract tests, not production key-provider proof."""
from __future__ import annotations

from dataclasses import replace
import uuid

import pytest
from cryptography.exceptions import InvalidTag

from clinic_ecosystem.shared_kernel.pii_encryption import (
    EncryptionKey,
    EncryptedPhone,
    FieldContext,
    encrypt_phone,
    decrypt_phone,
    rotate_phone_encryption,
)


class TestNonceLedger:
    """Test double ONLY: production must use durable cross-worker reservation."""
    __test__ = False

    def __init__(self):
        self.seen: set[tuple[uuid.UUID, bytes]] = set()

    def reserve(self, *, aes_key_identity: uuid.UUID, nonce_96bit: bytes) -> None:
        record = (aes_key_identity, nonce_96bit)
        if record in self.seen:
            raise ValueError("nonce reuse rejected")
        self.seen.add(record)


TENANT = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
OWNER = uuid.UUID("11111111-1111-1111-1111-111111111111")
RECORD = uuid.UUID("b1000000-0000-0000-0000-000000000001")
KEY_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
KEY_ID_TWO = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
CTX = FieldContext(TENANT, OWNER, RECORD, "PHONE_E164", "E164")
KEY_ONE = EncryptionKey(1, b"a" * 32)
KEY_TWO = EncryptionKey(2, b"b" * 32)


def test_phone_encrypted_roundtrip_and_persistence_field_sizes():
    ledger = TestNonceLedger()
    sealed = encrypt_phone(
        phone_e164="+989121234567", context=CTX, key=KEY_ONE,
        aes_key_identity=KEY_ID, nonce_reservation=ledger,
    )
    assert isinstance(sealed, EncryptedPhone)
    assert len(sealed.nonce_96bit) == 12
    assert len(sealed.auth_tag_128bit) == 16
    assert sealed.encryption_key_version == 1
    assert sealed.aad_version == 1
    assert b"+989121234567" not in sealed.phone_ciphertext
    assert decrypt_phone(encrypted=sealed, context=CTX, key=KEY_ONE) == "+989121234567"
    assert "+989121234567" not in repr(sealed)


@pytest.mark.parametrize("swap", [
    {"tenant_id": uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")},
    {"original_person_id": uuid.UUID("22222222-2222-2222-2222-222222222222")},
    {"record_id": uuid.UUID("b2000000-0000-0000-0000-000000000002")},
    {"field_type": "EMAIL"},
    {"issuing_authority": "OTHER"},
])
def test_phone_ciphertext_transplant_fails_aad_binding(swap):
    sealed = encrypt_phone(
        phone_e164="+989121234567", context=CTX, key=KEY_ONE,
        aes_key_identity=KEY_ID, nonce_reservation=TestNonceLedger(),
    )
    with pytest.raises(InvalidTag):
        decrypt_phone(encrypted=sealed, context=replace(CTX, **swap), key=KEY_ONE)


def test_phone_tag_and_ciphertext_tampering_rejected():
    sealed = encrypt_phone(
        phone_e164="+989121234567", context=CTX, key=KEY_ONE,
        aes_key_identity=KEY_ID, nonce_reservation=TestNonceLedger(),
    )
    tampered_tag = bytes([sealed.auth_tag_128bit[0] ^ 1]) + sealed.auth_tag_128bit[1:]
    tampered_data = bytes([sealed.phone_ciphertext[0] ^ 1]) + sealed.phone_ciphertext[1:]
    with pytest.raises(InvalidTag):
        decrypt_phone(encrypted=replace(sealed, auth_tag_128bit=tampered_tag), context=CTX, key=KEY_ONE)
    with pytest.raises(InvalidTag):
        decrypt_phone(encrypted=replace(sealed, phone_ciphertext=tampered_data), context=CTX, key=KEY_ONE)


def test_phone_wrong_key_version_fails_before_crypto():
    sealed = encrypt_phone(
        phone_e164="+123456789", context=CTX, key=KEY_ONE,
        aes_key_identity=KEY_ID, nonce_reservation=TestNonceLedger(),
    )
    with pytest.raises(ValueError, match="version mismatch"):
        decrypt_phone(encrypted=sealed, context=CTX, key=KEY_TWO)


def test_aes_rotation_rewraps_and_keeps_immutable_owner():
    ledger = TestNonceLedger()
    old = encrypt_phone(
        phone_e164="+123456789", context=CTX, key=KEY_ONE,
        aes_key_identity=KEY_ID, nonce_reservation=ledger,
    )
    rotated = rotate_phone_encryption(
        encrypted=old, context=CTX, old_key=KEY_ONE,
        new_key=KEY_TWO, aes_key_identity=KEY_ID_TWO, nonce_reservation=ledger,
    )
    assert rotated.encryption_key_version == 2
    assert rotated.auth_tag_128bit != old.auth_tag_128bit
    assert decrypt_phone(encrypted=rotated, context=CTX, key=KEY_TWO) == "+123456789"
    assert decrypt_phone(encrypted=old, context=CTX, key=KEY_ONE) == "+123456789"


def test_rotation_rejects_reused_aes_key_or_version():
    old = encrypt_phone(
        phone_e164="+123456789", context=CTX, key=KEY_ONE,
        aes_key_identity=KEY_ID, nonce_reservation=TestNonceLedger(),
    )
    for bad_key in (KEY_ONE, EncryptionKey(2, KEY_ONE.material)):
        with pytest.raises(ValueError):
            rotate_phone_encryption(
                encrypted=old, context=CTX, old_key=KEY_ONE,
                new_key=bad_key, aes_key_identity=KEY_ID_TWO,
                nonce_reservation=TestNonceLedger(),
            )


def test_nonce_reservation_is_mandatory_and_duplicate_nonce_is_denied(monkeypatch):
    fixed_nonce = b"0123456789ab"
    monkeypatch.setattr("clinic_ecosystem.shared_kernel.pii_encryption.secrets.token_bytes", lambda n: fixed_nonce)
    ledger = TestNonceLedger()
    first = encrypt_phone(
        phone_e164="+123456789", context=CTX, key=KEY_ONE,
        aes_key_identity=KEY_ID, nonce_reservation=ledger,
    )
    assert first.nonce_96bit == fixed_nonce
    with pytest.raises(ValueError, match="nonce reuse"):
        encrypt_phone(
            phone_e164="+123456789", context=CTX, key=KEY_ONE,
            aes_key_identity=KEY_ID, nonce_reservation=ledger,
        )
    with pytest.raises(TypeError, match="nonce reservation"):
        encrypt_phone(
            phone_e164="+123456789", context=CTX, key=KEY_ONE,
            aes_key_identity=KEY_ID, nonce_reservation=None,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("version,material", [(0, b"a" * 32), (32768, b"a" * 32), (1, b"a" * 16), (True, b"a" * 32)])
def test_encryption_key_fails_closed(version, material):
    with pytest.raises(ValueError):
        EncryptionKey(version, material)


def test_encrypted_envelope_and_unauthorized_aad_input_fail_closed():
    with pytest.raises(ValueError):
        EncryptedPhone(b"x", b"wrong", b"t" * 16, 1)
    with pytest.raises(ValueError):
        EncryptedPhone(b"x", b"0" * 12, b"t" * 15, 1)
    with pytest.raises(ValueError):
        EncryptedPhone(b"x", b"0" * 12, b"t" * 16, 1, aad_version=2)
    with pytest.raises(ValueError):
        FieldContext(TENANT, OWNER, RECORD, " PHONE_E164 ", "E164")
    with pytest.raises(ValueError):
        encrypt_phone(
            phone_e164="09121234567", context=CTX, key=KEY_ONE,
            aes_key_identity=KEY_ID, nonce_reservation=TestNonceLedger(),
        )

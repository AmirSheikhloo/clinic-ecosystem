"""Permission separated PII read, KMS and AAD negative unit contracts."""
from __future__ import annotations

from dataclasses import replace
from uuid import UUID

import pytest
from cryptography.exceptions import InvalidTag

from clinic_ecosystem.infrastructure.persistence.authenticated_uow import (
    VerifiedTenantDbSession,
)
from clinic_ecosystem.infrastructure.persistence.phone_reveal import (
    PhoneRevealRejected, SqlPhoneReader,
)
from clinic_ecosystem.infrastructure.persistence.phone_vault import TenantPhoneEncryptionKey
from clinic_ecosystem.shared_kernel.pii_encryption import (
    EncryptionKey, FieldContext, encrypt_phone,
)
from clinic_ecosystem.shared_kernel.tenant_auth import VerifiedHumanPrincipal

TENANT = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
OTHER = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
OWNER = UUID("11111111-1111-1111-1111-111111111111")
ACCOUNT = UUID("22222222-2222-2222-2222-222222222222")
PHONE_ID = UUID("33333333-3333-3333-3333-333333333333")
KEY_ID = UUID("44444444-4444-4444-4444-444444444444")
KEY = EncryptionKey(1, b"q" * 32)


class _Nonce:
    def reserve(self, *, key_version, nonce_96bit):
        assert key_version == 1 and len(nonce_96bit) == 12


class _Result:
    def __init__(self, value):
        self.value = value

    def first(self):
        return (1,) if self.value is True else None

    def mappings(self):
        return self

    def one_or_none(self):
        return self.value


class _Db:
    def __init__(self, *, allowed=True, found=True, tag_tamper=False):
        ctx = FieldContext(TENANT, OWNER, PHONE_ID, "PHONE_E164", "E164")
        sealed = encrypt_phone(
            phone_e164="+989121234567",
            context=ctx, key=KEY, nonce_reservation=_Nonce(),
        )
        if tag_tamper:
            sealed = replace(
                sealed,
                auth_tag_128bit=bytes([sealed.auth_tag_128bit[0] ^ 1])
                + sealed.auth_tag_128bit[1:],
            )
        self.record = {
            "id": PHONE_ID, "person_id": OWNER,
            "phone_ciphertext": sealed.phone_ciphertext,
            "nonce_96bit": sealed.nonce_96bit,
            "auth_tag_128bit": sealed.auth_tag_128bit,
            "encryption_key_version": 1,
            "aad_version": 1,
        }
        self.allowed = allowed
        self.found = found
        self.executed = []

    async def execute(self, stmt, params=None):
        sql = str(stmt)
        self.executed.append((sql, params or {}))
        if "FROM user_role_assignments" in sql:
            return _Result(self.allowed)
        if "FROM person_phones" in sql:
            assert params == {"tenant": TENANT, "phone_id": PHONE_ID}
            return _Result(self.record if self.found else None)
        return _Result(None)


class _Keys:
    def __init__(self, *, tenant=TENANT, version=1):
        self.tenant = tenant
        self.version = version
        self.calls = 0

    async def phone_aes_key_for_version(self, *, tenant_id, encryption_key_version):
        self.calls += 1
        assert tenant_id == TENANT and encryption_key_version == 1
        return TenantPhoneEncryptionKey(self.tenant, KEY_ID, EncryptionKey(self.version, b"q" * 32))


def _reader(db, keys):
    scope = VerifiedTenantDbSession(
        session=db,
        principal=VerifiedHumanPrincipal(
            tenant_id=TENANT, principal_id=ACCOUNT,
            jti="synthetic", issued_at_unix=1, expires_at_unix=9999999999,
        ),
    )
    return SqlPhoneReader(
        scope=scope, key_provider=keys,
        phone_field_type="PHONE_E164",
        phone_issuing_authority="E164",
        reveal_permission_code="TEST_ONLY_REVEAL_PHONE",
    )


@pytest.mark.asyncio
async def test_authorized_reveal_decrypts_and_audits_without_plaintext_in_logs():
    db = _Db()
    assert await _reader(db, _Keys()).reveal(phone_record_id=PHONE_ID) == "+989121234567"
    logs = [(s, p) for s, p in db.executed if "INSERT INTO audit_entries" in s]
    assert len(logs) == 1
    assert logs[0][1]["operation"] == "person_phone.plaintext_revealed"
    assert "+989121234567" not in repr(logs)


@pytest.mark.asyncio
async def test_reveal_rbac_denied_before_any_select_or_key_fetch():
    db, keys = _Db(allowed=False), _Keys()
    with pytest.raises(PhoneRevealRejected):
        await _reader(db, keys).reveal(phone_record_id=PHONE_ID)
    assert keys.calls == 0
    assert not any("FROM person_phones" in sql for sql, _ in db.executed)


@pytest.mark.asyncio
async def test_reveal_missing_row_does_not_fetch_key():
    db, keys = _Db(found=False), _Keys()
    with pytest.raises(PhoneRevealRejected):
        await _reader(db, keys).reveal(phone_record_id=PHONE_ID)
    assert keys.calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("tenant,version", [(OTHER, 1), (TENANT, 2)])
async def test_reveal_rejects_wrong_tenant_or_wrong_key_version(tenant, version):
    db = _Db()
    with pytest.raises(PhoneRevealRejected):
        await _reader(db, _Keys(tenant=tenant, version=version)).reveal(
            phone_record_id=PHONE_ID
        )
    assert not any("INSERT INTO audit_entries" in sql for sql, _ in db.executed)


@pytest.mark.asyncio
async def test_ciphertext_auth_tag_corruption_fails_with_invalid_tag():
    db = _Db(tag_tamper=True)
    with pytest.raises(InvalidTag):
        await _reader(db, _Keys()).reveal(phone_record_id=PHONE_ID)
    assert not any("INSERT INTO audit_entries" in sql for sql, _ in db.executed)


def test_reveal_requires_separate_configured_permission_and_key_provider():
    db = _Db()
    scope = VerifiedTenantDbSession(
        session=db,
        principal=VerifiedHumanPrincipal(TENANT, ACCOUNT, "jti", 1, 999999999),
    )
    with pytest.raises(ValueError):
        SqlPhoneReader(
            scope=scope, key_provider=_Keys(), phone_field_type="PHONE_E164",
            phone_issuing_authority="E164", reveal_permission_code="",
        )
    with pytest.raises(TypeError):
        SqlPhoneReader(
            scope=scope, key_provider=None, phone_field_type="PHONE_E164",
            phone_issuing_authority="E164", reveal_permission_code="TEST_ONLY_REVEAL_PHONE",
        )

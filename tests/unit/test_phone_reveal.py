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
from tests.verified_scope_helpers import mint_verified_scope_for_tests

TENANT = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
OTHER = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
OWNER = UUID("11111111-1111-1111-1111-111111111111")
ACCOUNT = UUID("22222222-2222-2222-2222-222222222222")
PHONE_ID = UUID("33333333-3333-3333-3333-333333333333")
KEY_ID = UUID("44444444-4444-4444-4444-444444444444")
KEY = EncryptionKey(1, b"q" * 32)


class _Nonce:
    def reserve(self, *, aes_key_identity, nonce_96bit):
        assert aes_key_identity == KEY_ID and len(nonce_96bit) == 12


class _Scalar:
    def __init__(self, value):
        self._value = value

    def scalar_one(self):
        return self._value

    def first(self):
        return (1,) if self._value is True else None

    def mappings(self):
        return self

    def one_or_none(self):
        return self._value


class _Db:
    def __init__(self, *, allowed=True, found=True, tag_tamper=False, guc=None):
        ctx = FieldContext(TENANT, OWNER, PHONE_ID, "PHONE_E164", "E164")
        sealed = encrypt_phone(
            phone_e164="+989121234567",
            context=ctx, key=KEY, aes_key_identity=KEY_ID,
            nonce_reservation=_Nonce(),
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
        self.guc = str(TENANT) if guc is None else guc
        self.executed = []
        self.commits = 0
        self.begins = 0

    async def execute(self, stmt, params=None):
        sql = str(stmt)
        self.executed.append((sql, params or {}))
        if "pg_current_xact_id_if_assigned()" in sql:
            return _Scalar(True)
        if "current_setting('app.current_tenant_id'" in sql:
            return _Scalar(self.guc)
        if "FROM user_role_assignments" in sql:
            return _Scalar(self.allowed)
        if "FROM person_phones" in sql:
            assert params == {"tenant": TENANT, "phone_id": PHONE_ID}
            return _Scalar(self.record if self.found else None)
        return _Scalar(None)

    async def commit(self):
        self.commits += 1

    async def begin(self):
        self.begins += 1


class _Keys:
    def __init__(self, *, tenant=TENANT, version=1):
        self.tenant = tenant
        self.version = version
        self.calls = 0

    async def phone_aes_key_for_version(self, *, tenant_id, encryption_key_version):
        self.calls += 1
        assert tenant_id == TENANT and encryption_key_version == 1
        return TenantPhoneEncryptionKey(self.tenant, KEY_ID, EncryptionKey(self.version, b"q" * 32))


def _principal():
    return VerifiedHumanPrincipal(
        tenant_id=TENANT, principal_id=ACCOUNT,
        jti="synthetic", issued_at_unix=1, expires_at_unix=9999999999,
    )


def _reader(db, keys):
    scope = mint_verified_scope_for_tests(session=db, principal=_principal())
    return SqlPhoneReader(
        scope=scope, key_provider=keys,
        phone_field_type="PHONE_E164",
        phone_issuing_authority="E164",
        reveal_permission_code="TEST_ONLY_REVEAL_PHONE",
    )


@pytest.mark.asyncio
async def test_authorized_reveal_commits_audit_before_returning_plaintext():
    db = _Db()
    assert await _reader(db, _Keys()).reveal(phone_record_id=PHONE_ID) == "+989121234567"
    logs = [(s, p) for s, p in db.executed if "INSERT INTO audit_entries" in s]
    assert len(logs) == 1
    assert logs[0][1]["operation"] == "person_phone.plaintext_revealed"
    assert "+989121234567" not in repr(logs)
    assert db.commits >= 1
    assert db.begins == 0  # no post-reveal transaction restart


@pytest.mark.asyncio
async def test_reveal_rbac_denied_before_any_select_or_key_fetch():
    db, keys = _Db(allowed=False), _Keys()
    with pytest.raises(PhoneRevealRejected):
        await _reader(db, keys).reveal(phone_record_id=PHONE_ID)
    assert keys.calls == 0
    assert not any("FROM person_phones" in sql for sql, _ in db.executed)
    assert db.commits == 0


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
    assert db.commits == 0


@pytest.mark.asyncio
async def test_ciphertext_auth_tag_corruption_fails_with_invalid_tag():
    db = _Db(tag_tamper=True)
    with pytest.raises(InvalidTag):
        await _reader(db, _Keys()).reveal(phone_record_id=PHONE_ID)
    assert not any("INSERT INTO audit_entries" in sql for sql, _ in db.executed)
    assert db.commits == 0


@pytest.mark.asyncio
async def test_reveal_rejects_spoofed_tenant_guc():
    db = _Db(guc=str(OTHER))
    with pytest.raises(PermissionError):
        await _reader(db, _Keys()).reveal(phone_record_id=PHONE_ID)
    assert db.commits == 0


def test_forged_verified_scope_cannot_be_constructed_or_accepted():
    db = _Db()
    with pytest.raises(TypeError, match="minted"):
        VerifiedTenantDbSession(session=db, principal=_principal())
    scope = mint_verified_scope_for_tests(session=db, principal=_principal())
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



@pytest.mark.parametrize("invalid_type,invalid_authority", [
    (" PHONE_E164 ", "E164"),
    ("PHONE_E164", " E164 "),
    ("PHONE|E164", "E164"),
])
def test_reveal_rejects_noncanonical_aad_tokens_before_sql(invalid_type, invalid_authority):
    db = _Db()
    scope = mint_verified_scope_for_tests(session=db, principal=_principal())
    with pytest.raises(ValueError):
        SqlPhoneReader(
            scope=scope, key_provider=_Keys(),
            phone_field_type=invalid_type,
            phone_issuing_authority=invalid_authority,
            reveal_permission_code="TEST_ONLY_REVEAL_PHONE",
        )
    assert db.executed == []


def test_reveal_rejects_object_new_scope_with_arbitrary_auth_marker():
    db = _Db()
    forged = object.__new__(VerifiedTenantDbSession)
    object.__setattr__(forged, "session", db)
    object.__setattr__(forged, "principal", _principal())
    object.__setattr__(forged, "_auth", object())
    with pytest.raises(TypeError):
        SqlPhoneReader(
            scope=forged, key_provider=_Keys(),
            phone_field_type="PHONE_E164",
            phone_issuing_authority="E164",
            reveal_permission_code="TEST_ONLY_REVEAL_PHONE",
        )

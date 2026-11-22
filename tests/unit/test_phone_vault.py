"""No production schemas needed: unit-test protected SQL phone create boundaries."""
from __future__ import annotations

import hashlib
import hmac
from uuid import UUID

import pytest

from clinic_ecosystem.infrastructure.persistence.authenticated_uow import (
    VerifiedTenantDbSession,
)
from clinic_ecosystem.infrastructure.persistence.phone_vault import (
    NonceReuseRejected, PhoneWriteRejected, SqlNonceRegistry, SqlPhoneVault,
    TenantPhoneEncryptionKey,
)
from clinic_ecosystem.shared_kernel.pii_contracts import LookupDigest
from clinic_ecosystem.shared_kernel.pii_encryption import EncryptionKey
from clinic_ecosystem.shared_kernel.tenant_auth import VerifiedHumanPrincipal
from tests.verified_scope_helpers import mint_verified_scope_for_tests

TENANT = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
OTHER = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
OWNER = UUID("11111111-1111-1111-1111-111111111111")
ACTOR = UUID("22222222-2222-2222-2222-222222222222")
KEY_ID = UUID("33333333-3333-3333-3333-333333333333")
PHONE = "+989121234567"


class _Result:
    def __init__(self, value=None):
        self._value = value

    def first(self):
        return (1,) if self._value else None

    def scalar_one(self):
        return self._value

    def scalar_one_or_none(self):
        return self._value


class _Session:
    def __init__(self, *, allowed=True, owner=True, nonce_available=True, guc=None):
        self.allowed = allowed
        self.owner = owner
        self.nonce_available = nonce_available
        self.guc = str(TENANT) if guc is None else guc
        self.executed: list[tuple[str, dict]] = []

    async def scalar(self, statement, parameters=None):
        assert "tenant_persons" in str(statement)
        assert parameters == {"tenant": TENANT, "owner": OWNER}
        return OWNER if self.owner else None

    async def execute(self, statement, parameters=None):
        sql = str(statement)
        params = parameters or {}
        self.executed.append((sql, params))
        if "current_setting('app.current_tenant_id'" in sql:
            return _Result(self.guc)
        if "FROM user_role_assignments" in sql:
            return _Result(self.allowed)
        if "INSERT INTO pii_nonce_reservations" in sql:
            return _Result(params["nonce"] if self.nonce_available else None)
        return _Result()


class _Kms:
    def __init__(self, tenant=TENANT):
        self.tenant = tenant
        self.calls = 0

    async def phone_aes_key(self, *, tenant_id):
        self.calls += 1
        assert tenant_id == TENANT
        return TenantPhoneEncryptionKey(self.tenant, KEY_ID, EncryptionKey(1, b"a" * 32))


class _Hmac:
    def __init__(self):
        self.calls = 0

    async def derive(self, *, tenant_id, phone_e164):
        self.calls += 1
        assert tenant_id == TENANT and phone_e164 == PHONE
        # TEST-ONLY derivation; normative phone domain is NOT approved.
        digest = hmac.new(b"x" * 32, b"synthetic-phone|" + PHONE.encode(), hashlib.sha256).digest()
        return LookupDigest(1, digest)


def _principal():
    return VerifiedHumanPrincipal(
        tenant_id=TENANT,
        principal_id=ACTOR,
        jti="synthetic-verified",
        issued_at_unix=1,
        expires_at_unix=100000000000,
    )


def _scope(session):
    return mint_verified_scope_for_tests(session=session, principal=_principal())


def _vault(session, kms=None, indexer=None):
    return SqlPhoneVault(
        scope=_scope(session),
        key_provider=kms or _Kms(),
        hmac_provider=indexer or _Hmac(),
        nonce_registry=SqlNonceRegistry(session),
        phone_field_type="PHONE_E164",
        phone_issuing_authority="E164",
        create_permission_code="PROPOSED_PHONE_WRITE",
    )


@pytest.mark.asyncio
async def test_phone_create_binds_db_fields_and_writes_audit_without_plaintext():
    session = _Session()
    result_id = await _vault(session).create(
        original_owner_person_id=OWNER, phone_e164=PHONE, is_shared_phone=True
    )
    sql_rows = [(sql, values) for sql, values in session.executed if "INSERT INTO person_phones" in sql]
    assert len(sql_rows) == 1
    sql, row = sql_rows[0]
    assert row["record_id"] == result_id
    assert row["tenant"] == TENANT and row["owner"] == OWNER
    assert row["masked"] == "****4567"
    assert row["is_shared"] is True and row["is_primary"] is False
    assert len(row["nonce"]) == 12 and len(row["tag"]) == 16
    assert len(row["digest"]) == 32 and row["digest_version"] == 1
    assert b"+989121234567" not in row["ciphertext"]
    assert row["key_version"] == 1 and row["aad_version"] == 1
    assert row["created_at"].tzinfo is not None
    assert any("INSERT INTO pii_nonce_reservations" in x[0] for x in session.executed)
    audit = [(s, p) for s, p in session.executed if "INSERT INTO audit_entries" in s]
    assert len(audit) == 1
    assert PHONE not in audit[0][1]["details"]
    assert PHONE not in repr(audit[0][1])


@pytest.mark.asyncio
async def test_phone_create_rejects_missing_rbac_before_kms_or_write():
    session = _Session(allowed=False)
    kms = _Kms()
    with pytest.raises(PhoneWriteRejected):
        await _vault(session, kms=kms).create(original_owner_person_id=OWNER, phone_e164=PHONE)
    assert kms.calls == 0
    assert not any("INSERT INTO" in sql for sql, _ in session.executed)


@pytest.mark.asyncio
async def test_phone_create_rejects_cross_tenant_owner_before_kms():
    session = _Session(owner=False)
    kms = _Kms()
    with pytest.raises(PhoneWriteRejected):
        await _vault(session, kms=kms).create(original_owner_person_id=OWNER, phone_e164=PHONE)
    assert kms.calls == 0


@pytest.mark.asyncio
async def test_phone_create_rejects_key_from_other_tenant_before_encryption():
    session = _Session()
    with pytest.raises(PhoneWriteRejected):
        await _vault(session, kms=_Kms(OTHER)).create(
            original_owner_person_id=OWNER, phone_e164=PHONE
        )
    assert not any("INSERT INTO person_phones" in x[0] for x in session.executed)


@pytest.mark.asyncio
async def test_nonce_collision_prevents_phone_persistence_and_audit():
    session = _Session(nonce_available=False)
    with pytest.raises(NonceReuseRejected):
        await _vault(session).create(original_owner_person_id=OWNER, phone_e164=PHONE)
    assert not any("INSERT INTO person_phones" in x[0] for x in session.executed)
    assert not any("INSERT INTO audit_entries" in x[0] for x in session.executed)


@pytest.mark.asyncio
async def test_phone_create_rejects_invalid_number_without_database_actions():
    session = _Session()
    with pytest.raises(ValueError):
        await _vault(session).create(original_owner_person_id=OWNER, phone_e164="09121234567")
    assert session.executed == []


@pytest.mark.asyncio
async def test_phone_create_rejects_spoofed_tenant_guc():
    session = _Session(guc=str(OTHER))
    with pytest.raises(PermissionError):
        await _vault(session).create(original_owner_person_id=OWNER, phone_e164=PHONE)
    assert not any("INSERT INTO person_phones" in sql for sql, _ in session.executed)


def test_phone_vault_requires_all_external_security_ports():
    session = _Session()
    with pytest.raises(TypeError):
        SqlPhoneVault(
            scope=_scope(session), key_provider=None, hmac_provider=_Hmac(),
            nonce_registry=SqlNonceRegistry(session), phone_field_type="PHONE_E164",
            phone_issuing_authority="E164", create_permission_code="PROPOSED_PHONE_WRITE",
        )


@pytest.mark.asyncio
async def test_pg_nonce_registration_checks_shape_before_sql():
    session = _Session()
    registry = SqlNonceRegistry(session)
    with pytest.raises(ValueError):
        await registry.reserve(tenant_id=TENANT, aes_key_identity=KEY_ID, nonce_96bit=b"bad")
    assert session.executed == []


def test_phone_vault_rejects_nonce_ledger_on_unrelated_session():
    trusted_session = _Session()
    unrelated_session = _Session()
    with pytest.raises(TypeError, match="same SQL transaction"):
        SqlPhoneVault(
            scope=_scope(trusted_session),
            key_provider=_Kms(),
            hmac_provider=_Hmac(),
            nonce_registry=SqlNonceRegistry(unrelated_session),
            phone_field_type="PHONE_E164",
            phone_issuing_authority="E164",
            create_permission_code="TEST_ONLY_PHONE_WRITE",
        )


def test_forged_verified_scope_is_rejected():
    session = _Session()
    with pytest.raises(TypeError, match="minted"):
        VerifiedTenantDbSession(session=session, principal=_principal())



@pytest.mark.parametrize("bad_tenant,bad_key_id,bad_key", [
    (None, KEY_ID, EncryptionKey(1, b"a" * 32)),
    (TENANT, None, EncryptionKey(1, b"a" * 32)),
    (TENANT, KEY_ID, b"not-key"),
    (UUID(int=0), KEY_ID, EncryptionKey(1, b"a" * 32)),
])
def test_tenant_kms_key_identity_fail_closed(bad_tenant, bad_key_id, bad_key):
    with pytest.raises((TypeError, ValueError)):
        TenantPhoneEncryptionKey(bad_tenant, bad_key_id, bad_key)


@pytest.mark.parametrize("bad_type,bad_auth", [
    (" PHONE_E164 ", "E164"),
    ("PHONE_E164", " E164 "),
    ("PHONE|E164", "E164"),
])
def test_phone_vault_validates_aad_before_database_actions(bad_type, bad_auth):
    session = _Session()
    with pytest.raises(ValueError):
        SqlPhoneVault(
            scope=_scope(session),
            key_provider=_Kms(),
            hmac_provider=_Hmac(),
            nonce_registry=SqlNonceRegistry(session),
            phone_field_type=bad_type,
            phone_issuing_authority=bad_auth,
            create_permission_code="TEST_ONLY_PHONE_WRITE",
        )
    assert session.executed == []


def test_no_public_production_scope_test_mint():
    import clinic_ecosystem.infrastructure.persistence.authenticated_uow as auth
    assert not hasattr(auth, "mint_verified_scope_for_tests")

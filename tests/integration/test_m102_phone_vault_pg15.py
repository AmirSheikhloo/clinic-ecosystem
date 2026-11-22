"""Real PG15 disposable schema: encrypted-phone insert, forced RLS, nonce SQL UNIQUE.

pii_nonce_reservations is created ONLY IN THIS TEST on a disposable database.
No official migration or production schema is created or accepted here.
The phone-HMAC message/field tokens are TEST-ONLY pending signed ADR.
"""
from __future__ import annotations

import hashlib
import hmac
import time
from datetime import datetime, timezone
from urllib.parse import quote_plus

import asyncpg
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from clinic_ecosystem.infrastructure.persistence.authenticated_uow import (
    verified_jwt_transaction,
)
from clinic_ecosystem.infrastructure.persistence.phone_vault import (
    NonceReuseRejected, SqlNonceRegistry, SqlPhoneVault,
    TenantPhoneEncryptionKey,
)
from clinic_ecosystem.shared_kernel.pii_contracts import LookupDigest
from clinic_ecosystem.shared_kernel.pii_encryption import (
    EncryptionKey, EncryptedPhone, FieldContext, decrypt_phone,
)
from clinic_ecosystem.shared_kernel.tenant_auth import (
    HumanJwtVerifier, TrustedJwtPublicKey,
)
from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7
from tests.integration.alembic_runner import upgrade_tenant_plane_async
from tests.integration.docker_probe import DOCKER_AVAILABLE, SKIP_REASON
from tests.integration.m1_seed import seed_scheduling_graph

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not DOCKER_AVAILABLE, reason=SKIP_REASON),
]
AES_KEY = EncryptionKey(1, b"S" * 32)
KEY_ID = new_uuid7()


class _SyntheticKeySource:
    def __init__(self, tenant):
        self.tenant = tenant

    async def phone_aes_key(self, *, tenant_id):
        assert tenant_id == self.tenant
        return TenantPhoneEncryptionKey(tenant_id, KEY_ID, AES_KEY)


class _SyntheticPhoneHmac:
    async def derive(self, *, tenant_id, phone_e164):
        # NOT production normative; phone input bytes are unsigned.
        msg = b"test-only|" + tenant_id.bytes + phone_e164.encode("ascii")
        return LookupDigest(
            key_version=1,
            digest=hmac.new(b"H" * 32, msg, hashlib.sha256).digest(),
        )


class _SyntheticJtiGuard:
    async def ensure_active(self, *, tenant_id, token_jti):
        assert token_jti == "signed-test-only-jti"


def _runtime_url(topology):
    ep = topology.cloud_tenant
    return (
        f"postgresql+asyncpg://tp_app_login:"
        f"{quote_plus(topology.passwords['tp_app_login'])}"
        f"@{ep.host}:{ep.port}/tenant_app"
    )


async def _make_test_registry(conn):
    # Test-only DDL, not a tp0008+ migration.
    await conn.execute(
        """
        CREATE TABLE pii_nonce_reservations (
            tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
            aes_key_identity UUID NOT NULL,
            nonce_96bit BYTEA NOT NULL CHECK (octet_length(nonce_96bit) = 12),
            created_at_utc TIMESTAMPTZ NOT NULL,
            CONSTRAINT uq_test_nonce_key_bytes UNIQUE(aes_key_identity, nonce_96bit)
        )
        """
    )
    await conn.execute("ALTER TABLE pii_nonce_reservations ENABLE ROW LEVEL SECURITY")
    await conn.execute("ALTER TABLE pii_nonce_reservations FORCE ROW LEVEL SECURITY")
    await conn.execute(
        """
        CREATE POLICY test_nonce_runtime_base ON pii_nonce_reservations
        AS PERMISSIVE FOR ALL TO db_app_runtime
        USING (true) WITH CHECK (true)
        """
    )
    await conn.execute(
        """
        CREATE POLICY test_nonce_runtime_guard ON pii_nonce_reservations
        AS RESTRICTIVE FOR ALL TO db_app_runtime
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id',true),'')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id',true),'')::uuid)
        """
    )
    await conn.execute(
        """
        CREATE POLICY test_nonce_migrator_maintenance ON pii_nonce_reservations
        AS PERMISSIVE FOR ALL TO db_migrator USING (true) WITH CHECK (true)
        """
    )
    await conn.execute(
        "GRANT SELECT, INSERT ON pii_nonce_reservations TO db_app_runtime"
    )


@pytest.mark.asyncio
async def test_real_pg15_phone_storage_nonce_and_rls(plane_topology, monkeypatch):
    await upgrade_tenant_plane_async(plane_topology.cloud_tenant.sqlalchemy_async_url())
    mig = await asyncpg.connect(plane_topology.cloud_tenant.asyncpg_dsn())
    registry_created = False
    engine = None
    try:
        await mig.execute("SET ROLE db_migrator")
        ids_a = await seed_scheduling_graph(mig)
        ids_b = await seed_scheduling_graph(mig)
        # Test-only permission, not a frozen production permission code.
        await mig.execute(
            """
            INSERT INTO role_permission_assignments(
                id, tenant_id, role_id, permission_code, granted_at_utc
            ) VALUES ($1,$2,$3,'TEST_ONLY_PHONE_WRITE',$4)
            """,
            new_uuid7(), ids_a.tenant_id, ids_a.role_id, datetime.now(timezone.utc)
        )
        # Second PERSON in same tenant (shared family phone must remain non-unique).
        owner_b = new_uuid7()
        await mig.execute(
            """
            INSERT INTO tenant_persons(
                id,tenant_id,first_name,last_name,aggregate_version,
                created_at_utc,updated_at_utc
            ) VALUES ($1,$2,'Test','Family',1,$3,$3)
            """,
            owner_b, ids_a.tenant_id, datetime.now(timezone.utc)
        )
        await _make_test_registry(mig)
        registry_created = True
        await mig.execute("RESET ROLE")

        rsa_secret = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        key_pem = rsa_secret.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        verifier = HumanJwtVerifier(
            issuer="https://synthetic-issuer.invalid/",
            audience="clinic",
            trusted_keys=(TrustedJwtPublicKey("test-rsa", "RS256", key_pem),),
            jti_validator=_SyntheticJtiGuard(),
            max_lifetime_seconds=300,
        )

        def auth_token(tenant, actor):
            clock = int(time.time())
            return jwt.encode(
                {
                    "iss": "https://synthetic-issuer.invalid/",
                    "aud": "clinic", "sub": str(actor),
                    "tenant_id": str(tenant), "jti": "signed-test-only-jti",
                    "iat": clock - 1, "nbf": clock - 1, "exp": clock + 120,
                },
                rsa_secret, algorithm="RS256", headers={"kid": "test-rsa"},
            )

        engine = create_async_engine(_runtime_url(plane_topology), pool_size=2)
        token_a = auth_token(ids_a.tenant_id, ids_a.user_account_id)
        token_b = auth_token(ids_b.tenant_id, ids_b.user_account_id)

        async def _store(owner):
            async with verified_jwt_transaction(
                engine=engine, bearer_token=token_a, verifier=verifier
            ) as scope:
                vault = SqlPhoneVault(
                    scope=scope,
                    key_provider=_SyntheticKeySource(ids_a.tenant_id),
                    hmac_provider=_SyntheticPhoneHmac(),
                    nonce_registry=SqlNonceRegistry(scope.session),
                    phone_field_type="PHONE_E164",
                    phone_issuing_authority="E164",
                    create_permission_code="TEST_ONLY_PHONE_WRITE",
                )
                return await vault.create(
                    original_owner_person_id=owner,
                    phone_e164="+989121234567", is_shared_phone=True
                )

        first = await _store(ids_a.person_id)
        second = await _store(owner_b)
        assert first != second

        async with verified_jwt_transaction(
            engine=engine, bearer_token=token_a, verifier=verifier
        ) as scope:
            results = (
                await scope.session.execute(
                    text(
                        """
                        SELECT id,person_id,phone_ciphertext,nonce_96bit,
                          auth_tag_128bit,encryption_key_version,aad_version,
                          phone_lookup_hmac,hmac_key_version,masked_phone
                        FROM person_phones
                        WHERE tenant_id=:tenant ORDER BY created_at_utc,id
                        """
                    ),
                    {"tenant": ids_a.tenant_id},
                )
            ).mappings().all()
            assert {r["id"] for r in results} == {first, second}
            assert len({r["phone_lookup_hmac"] for r in results}) == 1
            assert all(r["masked_phone"] == "****4567" for r in results)
            for row in results:
                sealed = EncryptedPhone(
                    bytes(row["phone_ciphertext"]), bytes(row["nonce_96bit"]),
                    bytes(row["auth_tag_128bit"]), row["encryption_key_version"],
                    row["aad_version"],
                )
                context = FieldContext(
                    ids_a.tenant_id, row["person_id"], row["id"],
                    "PHONE_E164", "E164",
                )
                assert decrypt_phone(
                    encrypted=sealed, context=context, key=AES_KEY
                ) == "+989121234567"
            audit_count = await scope.session.scalar(
                text(
                    "SELECT count(*) FROM audit_entries "
                    "WHERE tenant_id=:tenant AND operation='person_phone.created'"
                ),
                {"tenant": ids_a.tenant_id},
            )
            assert audit_count == 2

        async with verified_jwt_transaction(
            engine=engine, bearer_token=token_b, verifier=verifier
        ) as scope:
            assert await scope.session.scalar(
                text("SELECT count(*) FROM person_phones WHERE tenant_id=:a"),
                {"a": ids_a.tenant_id},
            ) == 0

        # Duplicate (key, nonce) rejected by a REAL PostgreSQL UNIQUE
        # across separate DB transactions and cannot create a phone row.
        fixed_nonce = b"test-nonce-12"
        assert len(fixed_nonce) == 13 or len(fixed_nonce) == 12
        fixed_nonce = b"0123456789ab"
        monkeypatch.setattr(
            "clinic_ecosystem.infrastructure.persistence.phone_vault.secrets.token_bytes",
            lambda n: fixed_nonce,
        )
        _ = await _store(ids_a.person_id)
        with pytest.raises(NonceReuseRejected):
            await _store(ids_a.person_id)

        async with verified_jwt_transaction(
            engine=engine, bearer_token=token_a, verifier=verifier
        ) as scope:
            assert await scope.session.scalar(
                text("SELECT count(*) FROM person_phones WHERE tenant_id=:a"),
                {"a": ids_a.tenant_id},
            ) == 3
            assert await scope.session.scalar(
                text("SELECT count(*) FROM pii_nonce_reservations WHERE tenant_id=:a"),
                {"a": ids_a.tenant_id},
            ) == 3
    finally:
        if engine is not None:
            await engine.dispose()
        try:
            await mig.execute("SET ROLE db_migrator")
            if registry_created:
                await mig.execute("DROP TABLE pii_nonce_reservations")
            await mig.execute("RESET ROLE")
        finally:
            await mig.close()

"""PG15 Testcontainers: verified RS256 JWT -> runtime role -> tenant-local RLS.

This proves only a real signed-human-JWT entrypoint with synthetic keys/data.
It does not prove a connected live identity provider or production jti store.
"""
from __future__ import annotations

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
    RuntimeRoleRejected,
    verified_jwt_transaction,
)
from clinic_ecosystem.shared_kernel.tenant_auth import (
    AuthenticationRejected,
    HumanJwtVerifier,
    TrustedJwtPublicKey,
)
from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7
from tests.integration.alembic_runner import upgrade_tenant_plane_async
from tests.integration.docker_probe import DOCKER_AVAILABLE, SKIP_REASON

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not DOCKER_AVAILABLE, reason=SKIP_REASON),
]


class _SyntheticJtiGuard:
    def __init__(self, permitted: set[str]):
        self.permitted = permitted

    async def ensure_active(self, *, tenant_id, token_jti):
        if token_jti not in self.permitted:
            raise AuthenticationRejected("revoked")


def _login_url(plane_topology, login: str, password: str) -> str:
    ep = plane_topology.cloud_tenant
    return (
        f"postgresql+asyncpg://{quote_plus(login)}:{quote_plus(password)}"
        f"@{ep.host}:{ep.port}/tenant_app"
    )


@pytest.mark.asyncio
async def test_jwt_provenance_and_runtime_rls_cross_tenant_real_pg15(plane_topology):
    await upgrade_tenant_plane_async(plane_topology.cloud_tenant.sqlalchemy_async_url())
    tenant_a, tenant_b = new_uuid7(), new_uuid7()
    now = datetime.now(timezone.utc)

    mig = await asyncpg.connect(plane_topology.cloud_tenant.asyncpg_dsn())
    try:
        await mig.execute("SET ROLE db_migrator")
        for tenant in (tenant_a, tenant_b):
            await mig.execute(
                """
                INSERT INTO tenant_registry(
                  tenant_id, tenant_status, timezone_name, created_at_utc, updated_at_utc
                ) VALUES ($1, 'ACTIVE', 'UTC', $2, $2)
                """,
                tenant, now,
            )
        await mig.execute("RESET ROLE")
    finally:
        await mig.close()

    rsa_private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_pem = rsa_private.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    verifier = HumanJwtVerifier(
        issuer="https://synthetic-idp.example.invalid/",
        audience="clinic-tenant",
        trusted_keys=(TrustedJwtPublicKey("key-1", "RS256", public_pem),),
        jti_validator=_SyntheticJtiGuard({"allowed-A", "allowed-B"}),
        max_lifetime_seconds=300,
    )

    def token(tenant, jti):
        ts = int(time.time())
        return jwt.encode(
            {
                "iss": "https://synthetic-idp.example.invalid/",
                "aud": "clinic-tenant",
                "sub": str(new_uuid7()),
                "tenant_id": str(tenant),
                "jti": jti,
                "iat": ts - 1, "nbf": ts - 1, "exp": ts + 120,
            },
            rsa_private, algorithm="RS256", headers={"kid": "key-1"},
        )

    engine = create_async_engine(
        _login_url(
            plane_topology, "tp_app_login", plane_topology.passwords["tp_app_login"]
        ),
        pool_size=1,
        max_overflow=0,
    )
    try:
        async with verified_jwt_transaction(
            engine=engine, bearer_token=token(tenant_a, "allowed-A"),
            verifier=verifier,
        ) as scope_a:
            assert scope_a.principal.tenant_id == tenant_a
            rows = (
                await scope_a.session.execute(text("SELECT tenant_id FROM tenant_registry"))
            ).scalars().all()
            assert rows == [tenant_a]
            invisible = await scope_a.session.scalar(
                text("SELECT count(*) FROM tenant_registry WHERE tenant_id = :other"),
                {"other": tenant_b},
            )
            assert invisible == 0

        async with verified_jwt_transaction(
            engine=engine, bearer_token=token(tenant_b, "allowed-B"),
            verifier=verifier,
        ) as scope_b:
            assert (
                await scope_b.session.execute(
                    text("SELECT tenant_id FROM tenant_registry")
                )
            ).scalars().all() == [tenant_b]
            assert await scope_b.session.scalar(
                text("SELECT count(*) FROM tenant_registry WHERE tenant_id = :other"),
                {"other": tenant_a},
            ) == 0

        async with engine.connect() as conn:
            # New unit of work, without verified tenant context, cannot see rows.
            assert await conn.scalar(text("SELECT count(*) FROM tenant_registry")) == 0

        with pytest.raises(AuthenticationRejected):
            async with verified_jwt_transaction(
                engine=engine, bearer_token=token(tenant_a, "revoked"),
                verifier=verifier,
            ):
                pytest.fail("revoked human JWT opened a transaction")

        # A migration-capable login is NEVER an allowed runtime principal.
        migrator_engine = create_async_engine(
            plane_topology.cloud_tenant.sqlalchemy_async_url(), pool_size=1
        )
        try:
            with pytest.raises(RuntimeRoleRejected):
                async with verified_jwt_transaction(
                    engine=migrator_engine, bearer_token=token(tenant_a, "allowed-A"),
                    verifier=verifier,
                ):
                    pytest.fail("migrator was accepted as application runtime")
        finally:
            await migrator_engine.dispose()
    finally:
        await engine.dispose()

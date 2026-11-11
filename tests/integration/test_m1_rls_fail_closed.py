"""TP0007 RLS fail-closed integration evidence using real runtime login."""

from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import quote_plus

import asyncpg
import pytest

from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7
from tests.integration.alembic_runner import upgrade_tenant_plane_async
from tests.integration.docker_probe import DOCKER_AVAILABLE, SKIP_REASON

pytestmark = pytest.mark.integration


def _runtime_dsn(plane_topology) -> str:
    pwd = plane_topology.passwords["tp_app_login"]
    ep = plane_topology.cloud_tenant
    return (
        f"postgresql://{quote_plus('tp_app_login')}:{quote_plus(pwd)}"
        f"@{ep.host}:{ep.port}/tenant_app"
    )


@pytest.mark.asyncio
async def test_runtime_rls_fail_closed_without_tenant_guc_and_cross_tenant(
    plane_topology,
) -> None:
    if not DOCKER_AVAILABLE:
        pytest.skip(SKIP_REASON)
    await upgrade_tenant_plane_async(plane_topology.cloud_tenant.sqlalchemy_async_url())

    tenant_a = new_uuid7()
    tenant_b = new_uuid7()
    now = datetime.now(timezone.utc)

    # Seed two tenants as migrator (bypass runtime RLS for fixture setup).
    mig = await asyncpg.connect(plane_topology.cloud_tenant.asyncpg_dsn())
    try:
        await mig.execute("SET ROLE db_migrator")
        for tid in (tenant_a, tenant_b):
            await mig.execute(
                """
                INSERT INTO tenant_registry (
                  tenant_id, tenant_status, timezone_name, created_at_utc, updated_at_utc
                ) VALUES ($1, 'ACTIVE', 'UTC', $2, $2)
                """,
                tid,
                now,
            )
        await mig.execute("RESET ROLE")
    finally:
        await mig.close()

    conn = await asyncpg.connect(_runtime_dsn(plane_topology))
    try:
        # No GUC: SELECT must not expose tenant-owned rows.
        visible = await conn.fetchval("SELECT count(*) FROM tenant_registry")
        assert visible == 0

        # No GUC: INSERT rejected by restrictive RLS policy.
        with pytest.raises(asyncpg.InsufficientPrivilegeError):
            await conn.execute(
                """
                INSERT INTO tenant_registry (
                  tenant_id, tenant_status, timezone_name, created_at_utc, updated_at_utc
                ) VALUES ($1, 'ACTIVE', 'UTC', NOW(), NOW())
                """,
                new_uuid7(),
            )

        # Matching tenant GUC allows permitted DML inside the transaction.
        tx = conn.transaction()
        await tx.start()
        try:
            await conn.execute(
                "SELECT set_config('app.current_tenant_id', $1, true)", str(tenant_a)
            )
            row = await conn.fetchval(
                "SELECT tenant_id FROM tenant_registry WHERE tenant_id = $1", tenant_a
            )
            assert row == tenant_a
            # Cross-tenant read remains closed under Tenant A GUC.
            other = await conn.fetchval(
                "SELECT tenant_id FROM tenant_registry WHERE tenant_id = $1", tenant_b
            )
            assert other is None
            with pytest.raises(asyncpg.InsufficientPrivilegeError):
                await conn.execute(
                    """
                    INSERT INTO tenant_registry (
                      tenant_id, tenant_status, timezone_name, created_at_utc, updated_at_utc
                    ) VALUES ($1, 'ACTIVE', 'UTC', NOW(), NOW())
                    """,
                    tenant_b,
                )
        finally:
            await tx.rollback()
    finally:
        await conn.close()

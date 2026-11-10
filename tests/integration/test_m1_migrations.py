"""TP0002–TP0007 migration contract tests."""

from __future__ import annotations

import asyncpg
import pytest

from tests.integration.alembic_runner import upgrade_tenant_plane_async
from tests.integration.docker_probe import DOCKER_AVAILABLE, SKIP_REASON

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_tenant_plane_upgrades_to_tp0007(plane_topology) -> None:
    if not DOCKER_AVAILABLE:
        pytest.skip(SKIP_REASON)
    await upgrade_tenant_plane_async(plane_topology.cloud_tenant.sqlalchemy_async_url())
    conn = await asyncpg.connect(plane_topology.cloud_tenant.asyncpg_dsn())
    try:
        version = await conn.fetchval(
            "SELECT version_num FROM alembic_meta.alembic_version_tp"
        )
        assert version == "tp0007"
        for table in (
            "tenant_persons",
            "appointments",
            "appointment_resource_allocations",
            "hold_expiry_work_items",
            "idempotency_records",
            "outbox_messages",
            "audit_entries",
            "tenant_roles",
        ):
            exists = await conn.fetchval(
                "SELECT to_regclass($1) IS NOT NULL", f"public.{table}"
            )
            assert exists, table
        # ONLINE-only EXCLUDE present
        exclude = await conn.fetchval(
            """
            SELECT 1 FROM pg_constraint
            WHERE conname = 'ex_online_resource_time'
            """
        )
        assert exclude == 1
        # RLS forced on appointments
        row = await conn.fetchrow(
            """
            SELECT relrowsecurity, relforcerowsecurity
            FROM pg_class WHERE relname = 'appointments'
            """
        )
        assert row["relrowsecurity"] is True
        assert row["relforcerowsecurity"] is True
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_local_hub_also_reaches_tp0007(plane_topology) -> None:
    if not DOCKER_AVAILABLE:
        pytest.skip(SKIP_REASON)
    await upgrade_tenant_plane_async(plane_topology.local_hub.sqlalchemy_async_url())
    conn = await asyncpg.connect(plane_topology.local_hub.asyncpg_dsn())
    try:
        version = await conn.fetchval(
            "SELECT version_num FROM alembic_meta.alembic_version_tp"
        )
        assert version == "tp0007"
    finally:
        await conn.close()

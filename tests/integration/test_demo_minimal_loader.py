"""PG15 smoke: load minimal demo profile and validate target counts."""

from __future__ import annotations

import os
from datetime import datetime, timezone

import asyncpg
import pytest

from clinic_ecosystem.infrastructure.demo.crypto_hooks import preview_demo_pii_env
from clinic_ecosystem.infrastructure.demo.loader import load_demo_dataset
from clinic_ecosystem.infrastructure.demo.profiles import resolve_profile
from clinic_ecosystem.infrastructure.demo.validate import validate_demo_counts
from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7
from tests.integration.alembic_runner import upgrade_tenant_plane_async
from tests.integration.docker_probe import DOCKER_AVAILABLE, SKIP_REASON

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_minimal_demo_loader_on_pg(plane_topology) -> None:
    if not DOCKER_AVAILABLE:
        pytest.skip(SKIP_REASON)
    os.environ.update(preview_demo_pii_env())
    os.environ["CLINIC_ENV"] = "test"

    await upgrade_tenant_plane_async(plane_topology.cloud_tenant.sqlalchemy_async_url())
    tenant_id = new_uuid7()
    person_id = new_uuid7()
    account_id = new_uuid7()
    now = datetime.now(timezone.utc)
    conn = await asyncpg.connect(plane_topology.cloud_tenant.asyncpg_dsn())
    try:
        await conn.execute("SET ROLE db_migrator")
        await conn.execute(
            """
            INSERT INTO tenant_registry (tenant_id, tenant_status, timezone_name, created_at_utc, updated_at_utc)
            VALUES ($1, 'ACTIVE', 'Asia/Tehran', $2, $2)
            """,
            tenant_id,
            now,
        )
        await conn.execute(
            "SELECT set_config('app.current_tenant_id', $1, false)", str(tenant_id)
        )
        await conn.execute(
            """
            INSERT INTO tenant_persons (
                id, tenant_id, first_name, last_name, birth_date, gender,
                aggregate_version, created_at_utc, updated_at_utc
            ) VALUES ($1, $2, 'Recv', 'Demo', NULL, NULL, 1, $3, $3)
            """,
            person_id,
            tenant_id,
            now,
        )
        await conn.execute(
            """
            INSERT INTO user_accounts (
                id, tenant_id, person_id, login_identifier, normalized_login_identifier,
                password_hash_argon2id, is_active, failed_login_attempts, locked_until_utc,
                password_changed_at_utc, aggregate_version, created_at_utc, updated_at_utc
            ) VALUES (
                $1, $2, $3, 'demo.recv', 'demo.recv', 'x', TRUE, 0, NULL, NULL, 1, $4, $4
            )
            """,
            account_id,
            tenant_id,
            person_id,
            now,
        )
        result = await load_demo_dataset(
            conn,
            tenant_id=tenant_id,
            receptionist_person_id=person_id,
            receptionist_account_id=account_id,
            profile="minimal",
        )
        assert result.crypto_seeded, result.crypto_skip_reason
        await conn.execute("SET ROLE db_migrator")
        report = await validate_demo_counts(
            conn,
            tenant_id=tenant_id,
            profile="minimal",
            crypto_expected=True,
        )
    finally:
        await conn.close()

    _, targets = resolve_profile("minimal")
    assert report.ok, report.failures
    assert int(result.counts["patients"]) >= targets.patients
    assert int(result.counts["appointments"]) >= targets.appointments
    assert int(report.counts["patients"]) >= targets.patients
    assert int(report.counts["appointments"]) >= targets.appointments

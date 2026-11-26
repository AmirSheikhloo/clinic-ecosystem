"""PG15: load full `demo` profile and validate live database counts (not in-memory)."""

from __future__ import annotations

import os
from datetime import datetime, timezone

import asyncpg
import pytest

from clinic_ecosystem.infrastructure.demo.crypto_hooks import preview_demo_pii_env
from clinic_ecosystem.infrastructure.demo.loader import load_demo_dataset
from clinic_ecosystem.infrastructure.demo.profiles import resolve_profile
from clinic_ecosystem.infrastructure.demo.validate import format_report, validate_demo_counts
from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7
from tests.integration.alembic_runner import upgrade_tenant_plane_async
from tests.integration.docker_probe import DOCKER_AVAILABLE, SKIP_REASON

pytestmark = pytest.mark.integration


async def _seed_tenant(conn: asyncpg.Connection) -> tuple:
    tenant_id = new_uuid7()
    person_id = new_uuid7()
    account_id = new_uuid7()
    now = datetime.now(timezone.utc)
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
    return tenant_id, person_id, account_id


@pytest.mark.asyncio
async def test_full_demo_profile_live_counts_on_pg(plane_topology) -> None:
    if not DOCKER_AVAILABLE:
        pytest.skip(SKIP_REASON)
    os.environ.update(preview_demo_pii_env())
    os.environ["CLINIC_ENV"] = "test"

    await upgrade_tenant_plane_async(plane_topology.cloud_tenant.sqlalchemy_async_url())
    conn = await asyncpg.connect(plane_topology.cloud_tenant.asyncpg_dsn())
    try:
        tenant_id, person_id, account_id = await _seed_tenant(conn)
        result = await load_demo_dataset(
            conn,
            tenant_id=tenant_id,
            receptionist_person_id=person_id,
            receptionist_account_id=account_id,
            profile="demo",
        )
        assert result.crypto_seeded, result.crypto_skip_reason
        await conn.execute("SET ROLE db_migrator")
        report = await validate_demo_counts(
            conn,
            tenant_id=tenant_id,
            profile="demo",
            crypto_expected=True,
        )
    finally:
        await conn.close()

    _, targets = resolve_profile("demo")
    assert report.ok, format_report(report)
    # Live DB thresholds from Task 30 / D0.5
    assert report.counts["patients"] >= 520
    assert report.counts["staff"] >= 42
    assert report.counts["services"] >= 32
    assert report.counts["appointments"] >= 10_500
    assert report.counts["appointments_today"] >= 220
    assert report.counts["appointments_tomorrow"] >= 110
    assert report.counts["shared_phone_families"] >= 32
    assert report.counts["exceptional_identity_patients"] >= 32
    assert report.counts["multi_service_groups"] >= 110
    assert report.counts["manual_overlap_pairs"] >= 32
    assert report.counts["audit_entries"] >= 5_200
    assert report.counts["national_id_rows"] >= targets.national_id_patients
    # Generator manifest must not exceed live DB (live is source of truth)
    assert int(result.counts["appointments"]) == report.counts["appointments"]

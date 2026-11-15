"""Fresh-install vs upgrade rehearsal and Package-2 / Phase-9 impact guards.

EXPERIMENTAL ONLY. Confirms experimental DDL never becomes official TP0008+
and that Package-2 TP0011 path is not rewritten by this branch.
"""

from __future__ import annotations

from pathlib import Path

import asyncpg
import pytest

from experiments.m102_hmac_physical.concurrent_ops import (
    create_unique_index_concurrently_via_alembic,
)
from experiments.m102_hmac_physical.fixtures import insert_identifier, seed_tenant_person
from experiments.m102_hmac_physical.p1_staged_columns import (
    P1_GEN2_INDEX_DDL,
    apply_p1_expand,
)
from experiments.m102_hmac_physical.p2_generation_sidecar import apply_p2_expand
from experiments.m102_hmac_physical.phase_gate import (
    PhaseGateError,
    advance_to,
    experimental_upgrade_head,
    get_state,
    init_model,
)
from experiments.m102_hmac_physical.rotation import p1_backfill_gen2_batch
from tests.integration.alembic_runner import upgrade_tenant_plane_async
from tests.integration.docker_probe import DOCKER_AVAILABLE, SKIP_REASON

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not DOCKER_AVAILABLE, reason=SKIP_REASON),
]

REPO = Path(__file__).resolve().parents[2]
TP_VERSIONS = REPO / "migrations" / "tenant_plane" / "versions"


async def _mig(ep):
    conn = await asyncpg.connect(ep.asyncpg_dsn())
    await conn.execute("SET ROLE db_migrator")
    return conn


@pytest.mark.asyncio
async def test_fresh_install_then_experimental_expand(plane_topology) -> None:
    """Empty TP0007 database: expand → dual-write path without legacy rows."""
    ep = plane_topology.cloud_tenant
    await upgrade_tenant_plane_async(ep.sqlalchemy_async_url(), revision="tp0007")
    conn = await _mig(ep)
    try:
        assert await conn.fetchval(
            "SELECT count(*) FROM person_identifiers"
        ) == 0
        await apply_p1_expand(conn)
        await apply_p2_expand(conn)
        await init_model(conn, model="P1")
        await init_model(conn, model="P2")
        tenant, person = await seed_tenant_person(conn)
        # Fresh writes can populate gen2 in the same transaction as active.
        await insert_identifier(
            conn,
            tenant_id=tenant,
            person_id=person,
            normalized="7770000001",
            next_version=2,
        )
        await p1_backfill_gen2_batch(conn, tenant_id=tenant, batch_size=10)
        filled = await conn.fetchval(
            """
            SELECT count(*) FROM person_identifiers
            WHERE tenant_id=$1 AND exp_lookup_hmac_gen2 IS NOT NULL
            """,
            tenant,
        )
        assert filled == 1
        assert await conn.fetchval(
            "SELECT version_num FROM alembic_meta.alembic_version_tp"
        ) == "tp0007"
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_upgrade_path_populated_then_expand_and_backfill(plane_topology) -> None:
    """Legacy populated TP0007 rows, then experimental expand + resumable backfill."""
    ep = plane_topology.local_hub
    await upgrade_tenant_plane_async(ep.sqlalchemy_async_url(), revision="tp0007")
    conn = await _mig(ep)
    try:
        tenant, person = await seed_tenant_person(conn)
        for i in range(6):
            await insert_identifier(
                conn,
                tenant_id=tenant,
                person_id=person,
                normalized=f"888{i:07d}",
                next_version=None,
            )
        # Simulate upgrade expand after data exists.
        await apply_p1_expand(conn)
        await init_model(conn, model="P1")
        for phase in (1, 2, 3):
            await advance_to(conn, model="P1", phase=phase)
        n1, cur = await p1_backfill_gen2_batch(
            conn, tenant_id=tenant, batch_size=2
        )
        assert n1 == 2
        n2, _ = await p1_backfill_gen2_batch(
            conn, tenant_id=tenant, batch_size=20, after_id=cur
        )
        assert n2 == 4
        assert (
            await conn.fetchval(
                """
                SELECT count(*) FROM person_identifiers
                WHERE tenant_id=$1 AND exp_lookup_hmac_gen2 IS NULL
                """,
                tenant,
            )
            == 0
        )
        for phase in (4, 5):
            await advance_to(conn, model="P1", phase=phase)
    finally:
        await conn.close()

    await create_unique_index_concurrently_via_alembic(
        ep.sqlalchemy_async_url(), P1_GEN2_INDEX_DDL
    )
    conn = await _mig(ep)
    try:
        await advance_to(conn, model="P1", phase=6)
        state = await get_state(conn, "P1")
        assert state.phase == 6
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_phase_gate_blocks_skip_to_index_and_phase9_not_operational(
    plane_topology,
) -> None:
    ep = plane_topology.cloud_tenant
    await upgrade_tenant_plane_async(ep.sqlalchemy_async_url(), revision="tp0007")
    conn = await _mig(ep)
    try:
        await init_model(conn, model="P1")
        with pytest.raises(PhaseGateError, match="unsafe phase jump"):
            await advance_to(conn, model="P1", phase=6)
        await advance_to(conn, model="P1", phase=1)
        with pytest.raises(PhaseGateError, match="refusing experimental upgrade head"):
            await experimental_upgrade_head(conn, model="P1", target_phase=9)
        # Legitimate one-step advances to dry-run phase 9 keep operational flag false.
        for phase in range(2, 10):
            await advance_to(conn, model="P1", phase=phase)
        state = await get_state(conn, "P1")
        assert state.phase == 9
        assert state.phase9_operational_executed is False
    finally:
        await conn.close()


def test_no_official_tp0008_plus_committed_on_this_branch() -> None:
    files = sorted(p.name for p in TP_VERSIONS.glob("tp*.py"))
    assert files == [
        "tp0001_extensions_and_tenant_root.py",
        "tp0002_identity_and_person_model.py",
        "tp0003_rbac_governance_minimum.py",
        "tp0004_catalog_resources_requirements.py",
        "tp0005_appointments_allocations_holds.py",
        "tp0006_idempotency_outbox_inbox_audit.py",
        "tp0007_rls_and_role_policies.py",
    ]
    # Package-2 TP0011 is NOT present and must not be invented here.
    assert not (TP_VERSIONS / "tp0011_catalog.py").exists()
    assert not list(TP_VERSIONS.glob("tp0008*.py"))
    assert not list(TP_VERSIONS.glob("tp0009*.py"))
    assert not list(TP_VERSIONS.glob("tp0010*.py"))

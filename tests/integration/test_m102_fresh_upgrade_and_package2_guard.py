"""Fresh-install vs upgrade rehearsal and Package-2 / Phase-9 impact guards."""

from __future__ import annotations

from pathlib import Path

import asyncpg
import pytest

from experiments.m102_hmac_physical.concurrent_ops import create_and_assert_unique_index
from experiments.m102_hmac_physical.fixtures import insert_identifier, seed_tenant_person
from experiments.m102_hmac_physical.lifecycle import (
    advance_phase_chain,
    advance_to_validate_after_backfill,
    advance_to_verify_after_index,
)
from experiments.m102_hmac_physical.p1_staged_columns import (
    P1_GEN2_INDEX,
    P1_GEN2_INDEX_DDL,
    apply_p1_expand,
)
from experiments.m102_hmac_physical.p2_generation_sidecar import apply_p2_expand
from experiments.m102_hmac_physical.phase_gate import (
    PhaseGateError,
    advance_to,
    cutover_generation,
    experimental_upgrade_head,
    get_state,
    init_model,
    record_evidence,
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
    """Prove expand+backfill on a newly seeded tenant at tp0007 (no TP0008+).

    Shared session fixtures may retain rows from earlier tests; this node binds
    assertions to a fresh tenant UUID rather than a global empty table.
    """
    ep = plane_topology.cloud_tenant
    await upgrade_tenant_plane_async(ep.sqlalchemy_async_url(), revision="tp0007")
    conn = await _mig(ep)
    try:
        await apply_p1_expand(conn)
        await apply_p2_expand(conn)
        await init_model(conn, model="P1")
        await init_model(conn, model="P2")
        tenant, person = await seed_tenant_person(conn)
        assert (
            await conn.fetchval(
                "SELECT count(*) FROM person_identifiers WHERE tenant_id=$1", tenant
            )
            == 0
        )
        await insert_identifier(
            conn,
            tenant_id=tenant,
            person_id=person,
            normalized="7770000001",
            next_version=2,
        )
        await p1_backfill_gen2_batch(conn, tenant_id=tenant, batch_size=10)
        assert (
            await conn.fetchval(
                """
                SELECT count(*) FROM person_identifiers
                WHERE tenant_id=$1 AND exp_lookup_hmac_gen2 IS NOT NULL
                """,
                tenant,
            )
            == 1
        )
        assert await conn.fetchval(
            "SELECT version_num FROM alembic_meta.alembic_version_tp"
        ) == "tp0007"
        assert not list(
            (REPO / "migrations" / "tenant_plane" / "versions").glob("tp0008*.py")
        )
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_upgrade_path_populated_then_expand_and_backfill(plane_topology) -> None:
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
        await apply_p1_expand(conn)
        await init_model(conn, model="P1")
        await advance_phase_chain(conn, model="P1", to_phase=3)
        n1, cur = await p1_backfill_gen2_batch(conn, tenant_id=tenant, batch_size=2)
        assert n1 == 2
        n2, _ = await p1_backfill_gen2_batch(
            conn, tenant_id=tenant, batch_size=20, after_id=cur
        )
        assert n2 == 4
        from experiments.m102_hmac_physical.lifecycle import prove_drain_and_backfill
        await prove_drain_and_backfill(
            conn, model="P1", tenant_id=tenant, generation=2
        )
        await advance_phase_chain(conn, model="P1", to_phase=5)
        assert (await get_state(conn, "P1")).phase == 5
        await conn.execute(f"DROP INDEX CONCURRENTLY IF EXISTS public.{P1_GEN2_INDEX}")
    finally:
        await conn.close()

    await create_and_assert_unique_index(
        sqlalchemy_async_url=ep.sqlalchemy_async_url(),
        inspect_dsn=ep.asyncpg_dsn(),
        ddl=P1_GEN2_INDEX_DDL,
        index_name=P1_GEN2_INDEX,
        table_name="person_identifiers",
        required_fragments=["exp_lookup_hmac_gen2"],
    )
    conn = await _mig(ep)
    try:
        await advance_to_verify_after_index(
            conn,
            model="P1",
            index_name=P1_GEN2_INDEX,
            table_name="person_identifiers",
            generation=2,
        )
        assert (await get_state(conn, "P1")).phase == 7
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
        await advance_phase_chain(conn, model="P1", to_phase=1)
        with pytest.raises(PhaseGateError, match="refusing experimental upgrade head"):
            await experimental_upgrade_head(conn, model="P1", target_phase=9)

        # Forged evidence path is disabled.
        with pytest.raises(PhaseGateError, match="record_evidence"):
            await record_evidence(
                conn,
                model="P1",
                phase=3,
                evidence_kind="drain",
                evidence={"fenced": True},
            )

        # Cannot leave DRAIN / enter CUTOVER without live proofs.
        await advance_phase_chain(conn, model="P1", to_phase=3)
        with pytest.raises(PhaseGateError, match="drain"):
            await advance_to(conn, model="P1", phase=4)
        with pytest.raises(PhaseGateError, match="cutover"):
            await cutover_generation(conn, model="P1", new_active=99)

        # Phase-9 operational flag remains impossible.
        await conn.execute(
            """
            UPDATE m102_exp_rotation_phase_meta
            SET phase = 9, phase9_operational_executed = FALSE
            WHERE model = 'P1'
            """
        )
        state = await get_state(conn, "P1")
        assert state.phase == 9
        assert state.phase9_operational_executed is False
        with pytest.raises(asyncpg.CheckViolationError):
            await conn.execute(
                """
                UPDATE m102_exp_rotation_phase_meta
                SET phase9_operational_executed=TRUE WHERE model='P1'
                """
            )
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
    assert not (TP_VERSIONS / "tp0011_catalog.py").exists()
    assert not list(TP_VERSIONS.glob("tp0008*.py"))

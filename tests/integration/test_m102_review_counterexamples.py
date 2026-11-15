"""Independent negative evidence: model-global gate vs tenant-scoped backfill.

These tests show experimental safety gaps, NOT approval of operational migration
or any production data/crypto access. Fresh disposable PostgreSQL 15 only.
"""
from uuid import uuid4

import asyncpg
import pytest

from experiments.m102_hmac_physical.concurrent_ops import create_and_assert_unique_index
from experiments.m102_hmac_physical.fixtures import insert_identifier, seed_tenant_person
from experiments.m102_hmac_physical.p1_staged_columns import (
    P1_GEN2_INDEX, P1_GEN2_INDEX_DDL, apply_p1_expand,
)
from experiments.m102_hmac_physical.phase_gate import (
    attest_backfill, attest_cutover_ready, attest_drain, attest_index_valid,
    advance_to, collect_backfill_proof, collect_drain_proof, collect_index_proof,
    cutover_generation, get_state, init_model, set_candidate_generation,
)
from experiments.m102_hmac_physical.synthetic_hmac import synthetic_lookup_hmac
from tests.integration.alembic_runner import upgrade_tenant_plane_async
from tests.integration.docker_probe import DOCKER_AVAILABLE, SKIP_REASON

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not DOCKER_AVAILABLE, reason=SKIP_REASON),
]


async def _migrator(ep):
    conn = await asyncpg.connect(ep.asyncpg_dsn())
    await conn.execute("SET ROLE db_migrator")
    assert await conn.fetchval("SELECT current_user") == "db_migrator"
    return conn


@pytest.mark.asyncio
async def test_negative_global_cutover_passes_after_only_one_of_two_tenants_backfilled(
    plane_topology,
):
    """Counterexample: one tenant's zero-null proof flips model-global completeness."""
    ep = plane_topology.cloud_tenant
    await upgrade_tenant_plane_async(ep.sqlalchemy_async_url(), revision="tp0007")
    conn = await _migrator(ep)
    try:
        await apply_p1_expand(conn)
        await init_model(conn, model="P1", active_generation=1)

        ta, pa = await seed_tenant_person(conn)
        tb, pb = await seed_tenant_person(conn)
        assert ta != tb
        a = await insert_identifier(
            conn, tenant_id=ta, person_id=pa,
            normalized="1122334455", next_version=None
        )
        await insert_identifier(
            conn, tenant_id=tb, person_id=pb,
            normalized="6677889900", next_version=None
        )
        digest = synthetic_lookup_hmac(
            tenant_id=ta, id_type=a.id_type,
            issuing_country_or_authority=a.authority,
            normalized_identifier=a.normalized, hmac_key_version=2,
        )
        await conn.execute(
            "UPDATE person_identifiers "
            "SET exp_lookup_hmac_gen2=$2, exp_hmac_key_version_gen2=2 "
            "WHERE id=$1", a.identifier_id, digest,
        )
        assert await conn.fetchval(
            "SELECT count(*) FROM person_identifiers "
            "WHERE tenant_id=$1 AND exp_lookup_hmac_gen2 IS NULL", tb
        ) == 1

        for phase in (1, 2, 3):
            await advance_to(conn, model="P1", phase=phase)
        drain = await collect_drain_proof(conn, model="P1")
        await attest_drain(conn, model="P1", proof=drain)
        await advance_to(conn, model="P1", phase=4)
        proof = await collect_backfill_proof(
            conn, model="P1", tenant_id=ta, generation=2
        )
        assert proof.remaining_null_rows == 0
        await attest_backfill(conn, model="P1", proof=proof)
        state = await get_state(conn, "P1")
        assert state.backfill_complete is True
        assert await conn.fetchval(
            "SELECT count(*) FROM person_identifiers "
            "WHERE tenant_id=$1 AND exp_lookup_hmac_gen2 IS NULL", tb
        ) == 1
        for phase in (5, 6):
            await advance_to(conn, model="P1", phase=phase)
    finally:
        await conn.close()

    # Partial unique index succeeds because tenant B has NULL candidate values.
    await create_and_assert_unique_index(
        sqlalchemy_async_url=ep.sqlalchemy_async_url(),
        inspect_dsn=ep.asyncpg_dsn(),
        ddl=P1_GEN2_INDEX_DDL,
        index_name=P1_GEN2_INDEX,
        table_name="person_identifiers",
        required_fragments=["exp_lookup_hmac_gen2"],
    )
    conn = await _migrator(ep)
    try:
        idx = await collect_index_proof(
            conn, model="P1",
            index_name=P1_GEN2_INDEX, table_name="person_identifiers",
        )
        await attest_index_valid(conn, model="P1", proof=idx, generation=2)
        await advance_to(conn, model="P1", phase=7)
        await set_candidate_generation(conn, model="P1", candidate=2)
        await attest_cutover_ready(
            conn, model="P1", candidate=2,
            index_name=P1_GEN2_INDEX, table_name="person_identifiers",
        )
        await advance_to(conn, model="P1", phase=8)
        await cutover_generation(conn, model="P1", new_active=2)
        state = await get_state(conn, "P1")
        assert state.active_generation == 2
        assert await conn.fetchval(
            "SELECT count(*) FROM person_identifiers "
            "WHERE tenant_id=$1 AND exp_lookup_hmac_gen2 IS NULL", tb
        ) == 1
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_negative_evidence_log_is_mutable_and_erasable_by_experiment_migrator(
    plane_topology,
):
    """Counterexample: INSERT-only writer does not provide DB-enforced immutability."""
    ep = plane_topology.local_hub
    await upgrade_tenant_plane_async(ep.sqlalchemy_async_url(), revision="tp0007")
    conn = await _migrator(ep)
    try:
        await init_model(conn, model="P1")
        drain = await collect_drain_proof(conn, model="P1")
        await attest_drain(conn, model="P1", proof=drain)
        assert await conn.fetchval(
            "SELECT count(*) FROM public.m102_exp_phase_evidence "
            "WHERE model='P1' AND evidence_kind='drain'"
        ) == 1
        # Metadata storage has no prevention for direct UPDATE/DELETE by the
        # same db_migrator that creates and uses the experimental evidence table.
        await conn.execute(
            "UPDATE public.m102_exp_phase_evidence "
            "SET proof_source='TAMPERED' "
            "WHERE model='P1' AND evidence_kind='drain'"
        )
        assert await conn.fetchval(
            "SELECT proof_source FROM public.m102_exp_phase_evidence "
            "WHERE model='P1' AND evidence_kind='drain'"
        ) == "TAMPERED"
        await conn.execute(
            "DELETE FROM public.m102_exp_phase_evidence WHERE model='P1'"
        )
        assert await conn.fetchval(
            "SELECT count(*) FROM public.m102_exp_phase_evidence WHERE model='P1'"
        ) == 0
        # The implementation's init_model() also resets/deletes evidence.
    finally:
        await conn.close()

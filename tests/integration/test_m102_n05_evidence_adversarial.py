"""Adversarial negative proofs of N05 evidence semantics, disposable PG15 only.

Passing these tests confirms a *gap in an experimental simulation*, NOT
approval of the design or failure of any deployed Clinic Ecosystem security.
No official migration, patient data, or production key is accessed.
"""
from __future__ import annotations

import asyncpg
import pytest

from experiments.m102_hmac_physical.lifecycle import progress_with_evidence
from experiments.m102_hmac_physical.phase_gate import (
    cutover_generation,
    get_state,
    init_model,
    record_evidence,
    rollback_to_previous_active,
    set_candidate_generation,
)
from tests.integration.alembic_runner import upgrade_tenant_plane_async
from tests.integration.docker_probe import DOCKER_AVAILABLE, SKIP_REASON

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not DOCKER_AVAILABLE, reason=SKIP_REASON),
]


@pytest.mark.asyncio
async def test_negative_n05_can_cutover_without_real_drain_backfill_or_generation_index(
    plane_topology,
) -> None:
    """The lifecycle helper self-attests all gates without checking real operations."""
    ep = plane_topology.cloud_tenant
    await upgrade_tenant_plane_async(ep.sqlalchemy_async_url(), revision="tp0007")
    conn = await asyncpg.connect(ep.asyncpg_dsn())
    try:
        await conn.execute("SET ROLE db_migrator")
        await init_model(conn, model="P1", active_generation=1)
        await set_candidate_generation(conn, model="P1", candidate=77)
        # Never expand schema, drain a writer, backfill a row, or build an index.
        assert await conn.fetchval(
            "SELECT to_regclass('public.uq_exp_p1_identifier_gen77_lookup')"
        ) is None
        await progress_with_evidence(conn, model="P1", to_phase=8)
        await cutover_generation(conn, model="P1", new_active=77)
        state = await get_state(conn, "P1")
        assert state.phase == 8
        assert state.active_generation == 77
        assert state.drain_attested and state.backfill_complete
        assert state.index_valid_attested

        # Even 'rollback_to_previous_active' can select an absent generation.
        await rollback_to_previous_active(
            conn, model="P1", previous_active=99
        )
        state = await get_state(conn, "P1")
        assert state.active_generation == 99
        assert await conn.fetchval(
            "SELECT to_regclass('public.uq_exp_p1_identifier_gen99_lookup')"
        ) is None
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_negative_n05_evidence_false_attested_and_history_mutable(
    plane_topology,
) -> None:
    """Writing a false payload sets TRUE; another write replaces the alleged record."""
    ep = plane_topology.local_hub
    await upgrade_tenant_plane_async(ep.sqlalchemy_async_url(), revision="tp0007")
    conn = await asyncpg.connect(ep.asyncpg_dsn())
    try:
        await conn.execute("SET ROLE db_migrator")
        await init_model(conn, model="P1", active_generation=1)
        await record_evidence(
            conn,
            model="P1",
            phase=3,
            evidence_kind="drain",
            evidence={"fenced": False, "proof": "NEGATIVE_CASE"},
        )
        state = await get_state(conn, "P1")
        assert state.drain_attested is True
        before = await conn.fetchval(
            "SELECT evidence_json->>'proof' FROM public.m102_exp_phase_evidence "
            "WHERE model='P1' AND phase=3 AND evidence_kind='drain'"
        )
        assert before == "NEGATIVE_CASE"
        await record_evidence(
            conn,
            model="P1",
            phase=3,
            evidence_kind="drain",
            evidence={"fenced": True, "proof": "OVERWRITTEN"},
        )
        after = await conn.fetchval(
            "SELECT evidence_json->>'proof' FROM public.m102_exp_phase_evidence "
            "WHERE model='P1' AND phase=3 AND evidence_kind='drain'"
        )
        assert after == "OVERWRITTEN"
    finally:
        await conn.close()

"""Proof-bound phase progression helpers (no self-forged attestations)."""

from __future__ import annotations

from uuid import UUID

import asyncpg

from experiments.m102_hmac_physical.p1_staged_columns import P1_GEN2_INDEX, P1_GEN3_INDEX
from experiments.m102_hmac_physical.p2_generation_sidecar import P2_ACTIVE_INDEX, P2_TABLE
from experiments.m102_hmac_physical.phase_gate import (
    PhaseGateError,
    advance_to,
    attest_backfill,
    attest_cutover_ready,
    attest_drain,
    attest_index_valid,
    begin_next_candidate_cycle,
    collect_backfill_proof,
    collect_drain_proof,
    collect_index_proof,
    generation_index_name,
    set_candidate_generation,
)


async def advance_phase_chain(
    conn: asyncpg.Connection, *, model: str, to_phase: int
) -> None:
    """Advance one phase at a time; fails closed if required attestations are missing."""
    state_phase = await conn.fetchval(
        "SELECT phase FROM m102_exp_rotation_phase_meta WHERE model=$1", model
    )
    current = int(state_phase)
    for phase in range(current + 1, to_phase + 1):
        await advance_to(conn, model=model, phase=phase)


# Backward-compatible name — no longer forges evidence.
async def progress_with_evidence(
    conn: asyncpg.Connection,
    *,
    model: str,
    to_phase: int,
    evidence: dict | None = None,
) -> None:
    if evidence:
        raise PhaseGateError(
            "progress_with_evidence no longer accepts forged evidence payloads; "
            "call attest_* with live proofs first"
        )
    await advance_phase_chain(conn, model=model, to_phase=to_phase)


async def prove_drain_and_backfill(
    conn: asyncpg.Connection,
    *,
    model: str,
    tenant_id: UUID,
    generation: int,
) -> None:
    drain = await collect_drain_proof(conn, model=model)
    await attest_drain(conn, model=model, proof=drain)
    backfill = await collect_backfill_proof(
        conn, model=model, tenant_id=tenant_id, generation=generation
    )
    await attest_backfill(conn, model=model, proof=backfill)


async def prove_index(
    conn: asyncpg.Connection,
    *,
    model: str,
    index_name: str,
    table_name: str,
    generation: int,
) -> None:
    idx = await collect_index_proof(
        conn, model=model, index_name=index_name, table_name=table_name
    )
    await attest_index_valid(conn, model=model, proof=idx, generation=generation)


async def advance_to_validate_after_backfill(
    conn: asyncpg.Connection,
    *,
    model: str,
    tenant_id: UUID,
    generation: int,
) -> None:
    """Reach VALIDATE (5) only after live drain+backfill proofs."""
    await advance_phase_chain(conn, model=model, to_phase=3)
    await prove_drain_and_backfill(
        conn, model=model, tenant_id=tenant_id, generation=generation
    )
    await advance_phase_chain(conn, model=model, to_phase=5)


async def advance_to_verify_after_index(
    conn: asyncpg.Connection,
    *,
    model: str,
    index_name: str,
    table_name: str,
    generation: int,
) -> None:
    """Reach VERIFY (7) only after live index catalog proof."""
    await advance_phase_chain(conn, model=model, to_phase=6)
    await prove_index(
        conn,
        model=model,
        index_name=index_name,
        table_name=table_name,
        generation=generation,
    )
    await advance_phase_chain(conn, model=model, to_phase=7)


async def prepare_cutover_candidate(
    conn: asyncpg.Connection,
    *,
    model: str,
    candidate: int,
    index_name: str | None = None,
    table_name: str | None = None,
) -> None:
    """Set candidate and attest cutover_ready only after live index re-check."""
    await set_candidate_generation(conn, model=model, candidate=candidate)
    if index_name is None:
        index_name = generation_index_name(model, candidate)
    if table_name is None:
        table_name = "person_identifiers" if model == "P1" else P2_TABLE
    await attest_cutover_ready(
        conn,
        model=model,
        candidate=candidate,
        index_name=index_name,
        table_name=table_name,
    )


def p1_index_for_generation(generation: int) -> str:
    if generation == 2:
        return P1_GEN2_INDEX
    if generation == 3:
        return P1_GEN3_INDEX
    raise PhaseGateError(f"unsupported P1 candidate generation {generation}")

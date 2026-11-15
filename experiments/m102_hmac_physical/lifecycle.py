"""Helpers to advance experimental phases with required evidence attestations."""

from __future__ import annotations

from typing import Any

import asyncpg

from experiments.m102_hmac_physical.phase_gate import (
    advance_to,
    record_evidence,
    set_candidate_generation,
)


async def progress_with_evidence(
    conn: asyncpg.Connection,
    *,
    model: str,
    to_phase: int,
    evidence: dict[int, list[tuple[str, dict[str, Any]]]] | None = None,
) -> None:
    """Advance one phase at a time, recording evidence before gated transitions."""
    evidence = evidence or {}
    state_phase = await conn.fetchval(
        "SELECT phase FROM m102_exp_rotation_phase_meta WHERE model=$1", model
    )
    current = int(state_phase)
    for phase in range(current + 1, to_phase + 1):
        # Record evidence required to leave the previous phase / enter the target.
        if phase == 4:
            await record_evidence(
                conn, model=model, phase=3, evidence_kind="drain", evidence={"fenced": True}
            )
        if phase == 5:
            await record_evidence(
                conn,
                model=model,
                phase=4,
                evidence_kind="backfill",
                evidence={"complete": True},
            )
        if phase == 7:
            await record_evidence(
                conn,
                model=model,
                phase=6,
                evidence_kind="index_valid",
                evidence={"valid": True},
            )
        if phase == 8:
            await record_evidence(
                conn,
                model=model,
                phase=8,
                evidence_kind="cutover_ready",
                evidence={"ready": True},
            )
        for kind, payload in evidence.get(phase, []):
            await record_evidence(
                conn, model=model, phase=phase, evidence_kind=kind, evidence=payload
            )
        await advance_to(conn, model=model, phase=phase)


async def prepare_cutover_candidate(
    conn: asyncpg.Connection, *, model: str, candidate: int
) -> None:
    await set_candidate_generation(conn, model=model, candidate=candidate)
    await record_evidence(
        conn,
        model=model,
        phase=8,
        evidence_kind="cutover_ready",
        evidence={"candidate": candidate},
    )

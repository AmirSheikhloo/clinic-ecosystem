"""Evidence-bound experimental phase metadata (clause-771 simulation only).

Not a real Alembic revision gate. Transitions fail closed unless immutable
evidence flags for drain/backfill/index/cutover are set. Phase-9 operational
retirement cannot be marked executed in this experiment.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import asyncpg

META_TABLE = "m102_exp_rotation_phase_meta"
EVIDENCE_TABLE = "m102_exp_phase_evidence"

PHASE_NAMES = {
    0: "BASELINE",
    1: "EXPAND",
    2: "DUAL_WRITE",
    3: "DRAIN",
    4: "BACKFILL",
    5: "VALIDATE",
    6: "INDEX",
    7: "VERIFY",
    8: "CUTOVER",
    9: "CONTRACT_DRY_RUN_ONLY",
}


@dataclass(frozen=True)
class PhaseState:
    model: str
    phase: int
    active_generation: int
    candidate_generation: int | None
    phase9_operational_executed: bool
    drain_attested: bool
    backfill_complete: bool
    index_valid_attested: bool
    cutover_ready: bool


CREATE_META = f"""
CREATE TABLE IF NOT EXISTS public.{META_TABLE} (
    model VARCHAR(8) PRIMARY KEY CHECK (model IN ('P1', 'P2')),
    phase SMALLINT NOT NULL CHECK (phase BETWEEN 0 AND 9),
    active_generation SMALLINT NOT NULL,
    candidate_generation SMALLINT NULL,
    phase9_operational_executed BOOLEAN NOT NULL DEFAULT FALSE,
    drain_attested BOOLEAN NOT NULL DEFAULT FALSE,
    backfill_complete BOOLEAN NOT NULL DEFAULT FALSE,
    index_valid_attested BOOLEAN NOT NULL DEFAULT FALSE,
    cutover_ready BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_exp_phase9_never_operational CHECK (
      phase9_operational_executed = FALSE
    )
)
"""

CREATE_EVIDENCE = f"""
CREATE TABLE IF NOT EXISTS public.{EVIDENCE_TABLE} (
    model VARCHAR(8) NOT NULL CHECK (model IN ('P1', 'P2')),
    phase SMALLINT NOT NULL CHECK (phase BETWEEN 0 AND 9),
    evidence_kind VARCHAR(64) NOT NULL,
    evidence_json JSONB NOT NULL DEFAULT '{{}}'::jsonb,
    created_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (model, phase, evidence_kind)
)
"""


class PhaseGateError(RuntimeError):
    """Raised when an experimental runner attempts an unsafe phase jump."""


async def ensure_meta(conn: asyncpg.Connection) -> None:
    await conn.execute(CREATE_META)
    await conn.execute(CREATE_EVIDENCE)
    # Repair older experimental schemas that lack evidence columns / weak CHECKs.
    await conn.execute(
        f"""
        ALTER TABLE public.{META_TABLE}
          ADD COLUMN IF NOT EXISTS drain_attested BOOLEAN NOT NULL DEFAULT FALSE,
          ADD COLUMN IF NOT EXISTS backfill_complete BOOLEAN NOT NULL DEFAULT FALSE,
          ADD COLUMN IF NOT EXISTS index_valid_attested BOOLEAN NOT NULL DEFAULT FALSE,
          ADD COLUMN IF NOT EXISTS cutover_ready BOOLEAN NOT NULL DEFAULT FALSE
        """
    )
    await conn.execute(
        f"""
        ALTER TABLE public.{META_TABLE}
          DROP CONSTRAINT IF EXISTS ck_exp_phase9_not_silent_closed
        """
    )
    await conn.execute(
        f"""
        DO $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conname = 'ck_exp_phase9_never_operational'
              AND conrelid = 'public.{META_TABLE}'::regclass
          ) THEN
            ALTER TABLE public.{META_TABLE}
              ADD CONSTRAINT ck_exp_phase9_never_operational
              CHECK (phase9_operational_executed = FALSE);
          END IF;
        END $$
        """
    )


async def init_model(
    conn: asyncpg.Connection, *, model: str, active_generation: int = 1
) -> None:
    await ensure_meta(conn)
    await conn.execute(
        f"DELETE FROM public.{EVIDENCE_TABLE} WHERE model = $1", model
    )
    await conn.execute(
        f"""
        INSERT INTO public.{META_TABLE} (
          model, phase, active_generation, candidate_generation,
          phase9_operational_executed, drain_attested, backfill_complete,
          index_valid_attested, cutover_ready, updated_at_utc
        ) VALUES ($1, 0, $2, NULL, FALSE, FALSE, FALSE, FALSE, FALSE, NOW())
        ON CONFLICT (model) DO UPDATE SET
          phase = 0,
          active_generation = EXCLUDED.active_generation,
          candidate_generation = NULL,
          phase9_operational_executed = FALSE,
          drain_attested = FALSE,
          backfill_complete = FALSE,
          index_valid_attested = FALSE,
          cutover_ready = FALSE,
          updated_at_utc = NOW()
        """,
        model,
        active_generation,
    )


async def get_state(conn: asyncpg.Connection, model: str) -> PhaseState:
    row = await conn.fetchrow(
        f"SELECT * FROM public.{META_TABLE} WHERE model = $1", model
    )
    if row is None:
        raise PhaseGateError(f"no experimental phase metadata for {model}")
    return PhaseState(
        model=row["model"],
        phase=int(row["phase"]),
        active_generation=int(row["active_generation"]),
        candidate_generation=(
            None
            if row["candidate_generation"] is None
            else int(row["candidate_generation"])
        ),
        phase9_operational_executed=bool(row["phase9_operational_executed"]),
        drain_attested=bool(row["drain_attested"]),
        backfill_complete=bool(row["backfill_complete"]),
        index_valid_attested=bool(row["index_valid_attested"]),
        cutover_ready=bool(row["cutover_ready"]),
    )


async def record_evidence(
    conn: asyncpg.Connection,
    *,
    model: str,
    phase: int,
    evidence_kind: str,
    evidence: dict[str, Any],
) -> None:
    await ensure_meta(conn)
    await conn.execute(
        f"""
        INSERT INTO public.{EVIDENCE_TABLE} (
          model, phase, evidence_kind, evidence_json, created_at_utc
        ) VALUES ($1, $2, $3, CAST($4 AS jsonb), NOW())
        ON CONFLICT (model, phase, evidence_kind) DO UPDATE SET
          evidence_json = EXCLUDED.evidence_json,
          created_at_utc = NOW()
        """,
        model,
        phase,
        evidence_kind,
        json.dumps(evidence, default=str),
    )
    if evidence_kind == "drain":
        await conn.execute(
            f"UPDATE public.{META_TABLE} SET drain_attested=TRUE, updated_at_utc=NOW() WHERE model=$1",
            model,
        )
    elif evidence_kind == "backfill":
        await conn.execute(
            f"UPDATE public.{META_TABLE} SET backfill_complete=TRUE, updated_at_utc=NOW() WHERE model=$1",
            model,
        )
    elif evidence_kind == "index_valid":
        await conn.execute(
            f"UPDATE public.{META_TABLE} SET index_valid_attested=TRUE, updated_at_utc=NOW() WHERE model=$1",
            model,
        )
    elif evidence_kind == "cutover_ready":
        await conn.execute(
            f"UPDATE public.{META_TABLE} SET cutover_ready=TRUE, updated_at_utc=NOW() WHERE model=$1",
            model,
        )


def _require_evidence_for_phase(state: PhaseState, phase: int) -> None:
    # Entering these phases requires prior evidence.
    if phase >= 3 and not state.drain_attested and phase != 3:
        # Advancing INTO phase 3 is allowed to record drain; leaving 3 requires drain.
        pass
    if phase > 3 and not state.drain_attested:
        raise PhaseGateError(f"{state.model}: drain evidence required before phase {phase}")
    if phase > 4 and not state.backfill_complete:
        raise PhaseGateError(
            f"{state.model}: backfill evidence required before phase {phase}"
        )
    if phase > 6 and not state.index_valid_attested:
        raise PhaseGateError(
            f"{state.model}: valid-index evidence required before phase {phase}"
        )
    if phase == 8 and not state.cutover_ready:
        raise PhaseGateError(
            f"{state.model}: cutover_ready evidence required before phase {phase}"
        )


async def advance_to(conn: asyncpg.Connection, *, model: str, phase: int) -> None:
    state = await get_state(conn, model)
    if phase < state.phase:
        raise PhaseGateError(
            f"{model}: cannot rewind phase {state.phase} -> {phase} without rollback API"
        )
    if phase > state.phase + 1:
        raise PhaseGateError(
            f"{model}: unsafe phase jump {state.phase} -> {phase}; "
            "use advance one phase at a time"
        )
    if phase == state.phase:
        return
    # Validate evidence needed to leave current phase / enter target.
    if phase >= 4 and state.phase == 3 and not state.drain_attested:
        raise PhaseGateError(f"{model}: cannot leave DRAIN without drain evidence")
    if phase >= 5 and state.phase == 4 and not state.backfill_complete:
        raise PhaseGateError(f"{model}: cannot leave BACKFILL without backfill evidence")
    if phase >= 7 and state.phase == 6 and not state.index_valid_attested:
        raise PhaseGateError(f"{model}: cannot leave INDEX without index_valid evidence")
    if phase == 8 and not state.cutover_ready:
        raise PhaseGateError(f"{model}: cannot enter CUTOVER without cutover_ready evidence")
    _require_evidence_for_phase(state, phase)

    if phase == 9:
        await conn.execute(
            f"""
            UPDATE public.{META_TABLE}
            SET phase = 9,
                phase9_operational_executed = FALSE,
                updated_at_utc = NOW()
            WHERE model = $1
            """,
            model,
        )
        return
    await conn.execute(
        f"""
        UPDATE public.{META_TABLE}
        SET phase = $2, updated_at_utc = NOW()
        WHERE model = $1
        """,
        model,
        phase,
    )


async def set_candidate_generation(
    conn: asyncpg.Connection, *, model: str, candidate: int
) -> None:
    await conn.execute(
        f"""
        UPDATE public.{META_TABLE}
        SET candidate_generation = $2, updated_at_utc = NOW()
        WHERE model = $1
        """,
        model,
        candidate,
    )


async def cutover_generation(
    conn: asyncpg.Connection, *, model: str, new_active: int
) -> None:
    state = await get_state(conn, model)
    if state.phase < 8:
        raise PhaseGateError(f"{model}: cutover requires phase>=8, have {state.phase}")
    if not state.drain_attested:
        raise PhaseGateError(f"{model}: cutover blocked — drain not attested")
    if not state.backfill_complete:
        raise PhaseGateError(f"{model}: cutover blocked — backfill incomplete")
    if not state.index_valid_attested:
        raise PhaseGateError(f"{model}: cutover blocked — index not validated")
    if not state.cutover_ready:
        raise PhaseGateError(f"{model}: cutover blocked — cutover_ready missing")
    if state.candidate_generation != new_active:
        raise PhaseGateError(
            f"{model}: cutover new_active={new_active} must equal "
            f"candidate_generation={state.candidate_generation}"
        )
    await conn.execute(
        f"""
        UPDATE public.{META_TABLE}
        SET active_generation = $2,
            candidate_generation = NULL,
            cutover_ready = FALSE,
            updated_at_utc = NOW()
        WHERE model = $1
        """,
        model,
        new_active,
    )
    await record_evidence(
        conn,
        model=model,
        phase=8,
        evidence_kind="cutover_committed",
        evidence={
            "previous_active": state.active_generation,
            "new_active": new_active,
        },
    )


async def rollback_to_previous_active(
    conn: asyncpg.Connection, *, model: str, previous_active: int
) -> None:
    """Authority-preserving metadata rollback (keeps indexes/values intact)."""
    state = await get_state(conn, model)
    if state.phase < 8:
        raise PhaseGateError(f"{model}: rollback-to-old requires phase>=8")
    await conn.execute(
        f"""
        UPDATE public.{META_TABLE}
        SET active_generation = $2,
            candidate_generation = $3,
            cutover_ready = FALSE,
            updated_at_utc = NOW()
        WHERE model = $1
        """,
        model,
        previous_active,
        state.active_generation,
    )
    await record_evidence(
        conn,
        model=model,
        phase=8,
        evidence_kind="rollback_to_old",
        evidence={
            "restored_active": previous_active,
            "demoted_generation": state.active_generation,
        },
    )


async def experimental_upgrade_head(
    conn: asyncpg.Connection, *, model: str, target_phase: int = 9
) -> None:
    state = await get_state(conn, model)
    if target_phase > state.phase + 1:
        raise PhaseGateError(
            f"refusing experimental upgrade head to phase {target_phase}: "
            f"current={state.phase} ({PHASE_NAMES[state.phase]}); "
            "backfill/drain/validate gates incomplete"
        )
    await advance_to(conn, model=model, phase=target_phase)

"""Experimental phase metadata and fail-closed upgrade-head guard.

Simulates clause-771 phase boundaries without official Alembic revisions.
An unsafe 'upgrade to experimental head' that skips incomplete phases must
raise rather than silently building Phase-6 indexes.
"""

from __future__ import annotations

from dataclasses import dataclass

import asyncpg

META_TABLE = "m102_exp_rotation_phase_meta"

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


CREATE_META = f"""
CREATE TABLE IF NOT EXISTS public.{META_TABLE} (
    model VARCHAR(8) PRIMARY KEY CHECK (model IN ('P1', 'P2')),
    phase SMALLINT NOT NULL CHECK (phase BETWEEN 0 AND 9),
    active_generation SMALLINT NOT NULL,
    candidate_generation SMALLINT NULL,
    phase9_operational_executed BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_exp_phase9_not_silent_closed CHECK (
      phase < 9 OR phase9_operational_executed = FALSE
      OR phase = 9
    )
)
"""


class PhaseGateError(RuntimeError):
    """Raised when an experimental runner attempts an unsafe phase jump."""


async def ensure_meta(conn: asyncpg.Connection) -> None:
    await conn.execute(CREATE_META)


async def init_model(
    conn: asyncpg.Connection, *, model: str, active_generation: int = 1
) -> None:
    await ensure_meta(conn)
    await conn.execute(
        f"""
        INSERT INTO public.{META_TABLE} (
          model, phase, active_generation, candidate_generation,
          phase9_operational_executed, updated_at_utc
        ) VALUES ($1, 0, $2, NULL, FALSE, NOW())
        ON CONFLICT (model) DO UPDATE SET
          phase = EXCLUDED.phase,
          active_generation = EXCLUDED.active_generation,
          candidate_generation = NULL,
          phase9_operational_executed = FALSE,
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
    if phase == 9:
        # Package-1 dry-run only: never mark operational retirement executed here.
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
    await conn.execute(
        f"""
        UPDATE public.{META_TABLE}
        SET active_generation = $2,
            candidate_generation = NULL,
            updated_at_utc = NOW()
        WHERE model = $1
        """,
        model,
        new_active,
    )


async def experimental_upgrade_head(
    conn: asyncpg.Connection, *, model: str, target_phase: int = 9
) -> None:
    """Fail-closed stand-in for unsafe alembic upgrade head across phase gates."""
    state = await get_state(conn, model)
    if target_phase > state.phase + 1:
        raise PhaseGateError(
            f"refusing experimental upgrade head to phase {target_phase}: "
            f"current={state.phase} ({PHASE_NAMES[state.phase]}); "
            "backfill/drain/validate gates incomplete"
        )
    await advance_to(conn, model=model, phase=target_phase)


async def assert_phase_at_least(
    conn: asyncpg.Connection, *, model: str, minimum: int
) -> None:
    state = await get_state(conn, model)
    if state.phase < minimum:
        raise PhaseGateError(
            f"{model}: required phase>={minimum}, have {state.phase}"
        )

"""Proof-bound experimental phase metadata (clause-771 simulation only).

Not a real Alembic revision gate and not a deployable migration controller.
Attestations require live catalog/lease/backfill proofs; forged boolean payloads
are rejected. Evidence rows are append-only (no overwrite). Phase-9 operational
retirement cannot be marked executed in this experiment.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import asyncpg

from experiments.m102_hmac_physical.p1_staged_columns import P1_GEN2_INDEX, P1_GEN3_INDEX
from experiments.m102_hmac_physical.p2_generation_sidecar import P2_ACTIVE_INDEX, P2_TABLE

META_TABLE = "m102_exp_rotation_phase_meta"
EVIDENCE_TABLE = "m102_exp_phase_evidence"
LEASE_TABLE = "m102_exp_writer_leases"

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

# Experimental generation → unique index that must exist for authority/rollback.
P1_GENERATION_INDEX = {
    1: "uq_person_identifier_active_lookup",
    2: P1_GEN2_INDEX,
    3: P1_GEN3_INDEX,
}
P1_GENERATION_COLUMN = {
    2: "exp_lookup_hmac_gen2",
    3: "exp_lookup_hmac_gen3",
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


@dataclass(frozen=True)
class DrainProof:
    model: str
    active_writer_leases: int
    collected_at_utc: datetime

    def validate(self) -> None:
        if self.active_writer_leases != 0:
            raise PhaseGateError(
                f"drain proof rejected: {self.active_writer_leases} active writer leases"
            )


@dataclass(frozen=True)
class BackfillProof:
    """Full-population backfill proof (all tenants currently holding identifiers)."""

    model: str
    generation: int
    scope_tenant_ids: tuple[UUID, ...]
    remaining_null_rows: int
    collected_at_utc: datetime

    def validate(self) -> None:
        if self.remaining_null_rows != 0:
            raise PhaseGateError(
                f"backfill proof rejected: {self.remaining_null_rows} rows still null "
                f"across {len(self.scope_tenant_ids)} tenant(s) in deployment scope"
            )


@dataclass(frozen=True)
class IndexProof:
    model: str
    index_name: str
    table_name: str
    unique_index: bool
    valid: bool
    ready: bool
    collected_at_utc: datetime

    def validate(self) -> None:
        if not (self.unique_index and self.valid and self.ready):
            raise PhaseGateError(
                f"index proof rejected for {self.index_name}: "
                f"unique={self.unique_index} valid={self.valid} ready={self.ready}"
            )


@dataclass(frozen=True)
class CutoverProof:
    model: str
    candidate_generation: int
    index_name: str
    index_valid: bool
    drain_attested: bool
    backfill_complete: bool
    collected_at_utc: datetime

    def validate(self) -> None:
        if not self.drain_attested:
            raise PhaseGateError("cutover proof rejected: drain not attested")
        if not self.backfill_complete:
            raise PhaseGateError("cutover proof rejected: backfill incomplete")
        if not self.index_valid:
            raise PhaseGateError(
                f"cutover proof rejected: index {self.index_name} not valid"
            )


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
    evidence_id BIGSERIAL PRIMARY KEY,
    model VARCHAR(8) NOT NULL CHECK (model IN ('P1', 'P2')),
    phase SMALLINT NOT NULL CHECK (phase BETWEEN 0 AND 9),
    evidence_kind VARCHAR(64) NOT NULL,
    evidence_json JSONB NOT NULL DEFAULT '{{}}'::jsonb,
    proof_source VARCHAR(64) NOT NULL,
    created_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
"""

EVIDENCE_IMMUTABILITY_SQL = f"""
CREATE OR REPLACE FUNCTION public.m102_exp_forbid_evidence_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  RAISE EXCEPTION 'm102_exp_phase_evidence is append-only (UPDATE/DELETE forbidden)';
END;
$$;

DROP TRIGGER IF EXISTS trg_exp_evidence_no_update ON public.{EVIDENCE_TABLE};
CREATE TRIGGER trg_exp_evidence_no_update
  BEFORE UPDATE ON public.{EVIDENCE_TABLE}
  FOR EACH ROW EXECUTE FUNCTION public.m102_exp_forbid_evidence_mutation();

DROP TRIGGER IF EXISTS trg_exp_evidence_no_delete ON public.{EVIDENCE_TABLE};
CREATE TRIGGER trg_exp_evidence_no_delete
  BEFORE DELETE ON public.{EVIDENCE_TABLE}
  FOR EACH ROW EXECUTE FUNCTION public.m102_exp_forbid_evidence_mutation();

REVOKE UPDATE, DELETE ON public.{EVIDENCE_TABLE} FROM PUBLIC;
GRANT SELECT, INSERT ON public.{EVIDENCE_TABLE} TO db_migrator;
"""

CREATE_LEASES = f"""
CREATE TABLE IF NOT EXISTS public.{LEASE_TABLE} (
    lease_id BIGSERIAL PRIMARY KEY,
    model VARCHAR(8) NOT NULL CHECK (model IN ('P1', 'P2')),
    writer_name TEXT NOT NULL,
    acquired_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    released_at_utc TIMESTAMPTZ NULL
)
"""


class PhaseGateError(RuntimeError):
    """Raised when an experimental runner attempts an unsafe phase jump."""


async def ensure_meta(conn: asyncpg.Connection) -> None:
    await conn.execute(CREATE_META)
    await conn.execute(CREATE_LEASES)
    # Prefer append-only evidence schema; rebuild if an older mutable table exists.
    exists = await conn.fetchval(
        """
        SELECT EXISTS (
          SELECT 1 FROM information_schema.tables
          WHERE table_schema='public' AND table_name=$1
        )
        """,
        EVIDENCE_TABLE,
    )
    if exists:
        has_id = await conn.fetchval(
            """
            SELECT EXISTS (
              SELECT 1 FROM information_schema.columns
              WHERE table_schema='public' AND table_name=$1 AND column_name='evidence_id'
            )
            """,
            EVIDENCE_TABLE,
        )
        if not has_id:
            await conn.execute(f"DROP TABLE public.{EVIDENCE_TABLE}")
    await conn.execute(CREATE_EVIDENCE)
    await conn.execute(EVIDENCE_IMMUTABILITY_SQL)
    seq = await conn.fetchval(
        "SELECT pg_get_serial_sequence($1, 'evidence_id')", f"public.{EVIDENCE_TABLE}"
    )
    if seq:
        await conn.execute(f"GRANT USAGE, SELECT ON SEQUENCE {seq} TO db_migrator")
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
    """Reset phase metadata for a disposable run.

    Does **not** DELETE append-only evidence rows (DB triggers forbid it).
    Prior evidence remains for audit; gate decisions use refreshed meta flags.
    """
    await ensure_meta(conn)
    await conn.execute(
        f"""
        UPDATE public.{LEASE_TABLE}
        SET released_at_utc = NOW()
        WHERE model = $1 AND released_at_utc IS NULL
        """,
        model,
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


async def acquire_writer_lease(
    conn: asyncpg.Connection, *, model: str, writer_name: str
) -> int:
    await ensure_meta(conn)
    return int(
        await conn.fetchval(
            f"""
            INSERT INTO public.{LEASE_TABLE} (model, writer_name)
            VALUES ($1, $2) RETURNING lease_id
            """,
            model,
            writer_name,
        )
    )


async def release_writer_lease(conn: asyncpg.Connection, *, lease_id: int) -> None:
    await conn.execute(
        f"""
        UPDATE public.{LEASE_TABLE}
        SET released_at_utc = NOW()
        WHERE lease_id = $1 AND released_at_utc IS NULL
        """,
        lease_id,
    )


async def collect_drain_proof(conn: asyncpg.Connection, *, model: str) -> DrainProof:
    await ensure_meta(conn)
    active = int(
        await conn.fetchval(
            f"""
            SELECT count(*) FROM public.{LEASE_TABLE}
            WHERE model = $1 AND released_at_utc IS NULL
            """,
            model,
        )
    )
    return DrainProof(
        model=model,
        active_writer_leases=active,
        collected_at_utc=datetime.now(timezone.utc),
    )


async def collect_backfill_proof(
    conn: asyncpg.Connection,
    *,
    model: str,
    generation: int,
) -> BackfillProof:
    """Count incomplete generation rows across the full identifier population.

    Tenant-scoped proofs are rejected: a single-tenant zero-null result must not
    flip the model-global backfill_complete gate while other tenants remain open.
    """
    await ensure_meta(conn)
    scope_rows = await conn.fetch(
        "SELECT DISTINCT tenant_id FROM person_identifiers ORDER BY tenant_id"
    )
    scope = tuple(UUID(str(r["tenant_id"])) for r in scope_rows)
    if model == "P1":
        column = P1_GENERATION_COLUMN.get(generation)
        if column is None:
            raise PhaseGateError(f"P1 backfill proof unsupported for generation {generation}")
        remaining = int(
            await conn.fetchval(
                f"""
                SELECT count(*) FROM person_identifiers
                WHERE {column} IS NULL
                """
            )
        )
    elif model == "P2":
        remaining = int(
            await conn.fetchval(
                f"""
                SELECT count(*) FROM person_identifiers pi
                WHERE NOT EXISTS (
                  SELECT 1 FROM {P2_TABLE} g
                  WHERE g.tenant_id = pi.tenant_id
                    AND g.identifier_id = pi.id
                    AND g.hmac_key_version = $1
                )
                """,
                generation,
            )
        )
    else:
        raise PhaseGateError(f"unknown model {model}")
    return BackfillProof(
        model=model,
        generation=generation,
        scope_tenant_ids=scope,
        remaining_null_rows=remaining,
        collected_at_utc=datetime.now(timezone.utc),
    )


async def collect_index_proof(
    conn: asyncpg.Connection, *, model: str, index_name: str, table_name: str
) -> IndexProof:
    row = await conn.fetchrow(
        """
        SELECT i.indisunique AS unique_index,
               i.indisvalid AS valid,
               i.indisready AS ready,
               t.relname AS table_name
        FROM pg_index i
        JOIN pg_class c ON c.oid = i.indexrelid
        JOIN pg_class t ON t.oid = i.indrelid
        WHERE c.relname = $1
        """,
        index_name,
    )
    if row is None:
        raise PhaseGateError(f"index proof: missing index {index_name}")
    if row["table_name"] != table_name:
        raise PhaseGateError(
            f"index proof: {index_name} on {row['table_name']}, expected {table_name}"
        )
    return IndexProof(
        model=model,
        index_name=index_name,
        table_name=table_name,
        unique_index=bool(row["unique_index"]),
        valid=bool(row["valid"]),
        ready=bool(row["ready"]),
        collected_at_utc=datetime.now(timezone.utc),
    )


def generation_index_name(model: str, generation: int) -> str:
    if model == "P1":
        name = P1_GENERATION_INDEX.get(generation)
        if name is None:
            raise PhaseGateError(f"no P1 index mapping for generation {generation}")
        return name
    if model == "P2":
        # P2 active authority is the status-scoped ACTIVE unique index.
        return P2_ACTIVE_INDEX
    raise PhaseGateError(f"unknown model {model}")


async def _append_evidence(
    conn: asyncpg.Connection,
    *,
    model: str,
    phase: int,
    evidence_kind: str,
    evidence: dict[str, Any],
    proof_source: str,
) -> None:
    """Append-only insert. Never UPDATE existing evidence rows."""
    await ensure_meta(conn)
    await conn.execute(
        f"""
        INSERT INTO public.{EVIDENCE_TABLE} (
          model, phase, evidence_kind, evidence_json, proof_source, created_at_utc
        ) VALUES ($1, $2, $3, CAST($4 AS jsonb), $5, NOW())
        """,
        model,
        phase,
        evidence_kind,
        json.dumps(evidence, default=str),
        proof_source,
    )


async def attest_drain(conn: asyncpg.Connection, *, model: str, proof: DrainProof) -> None:
    if proof.model != model:
        raise PhaseGateError("drain proof model mismatch")
    proof.validate()
    # Re-check live lease table; do not trust a stale proof object alone.
    live = await collect_drain_proof(conn, model=model)
    live.validate()
    state = await get_state(conn, model)
    if state.drain_attested:
        # Idempotent if already proven with zero leases; still refuse forged path.
        live.validate()
        return
    await _append_evidence(
        conn,
        model=model,
        phase=3,
        evidence_kind="drain",
        evidence={
            "active_writer_leases": live.active_writer_leases,
            "collected_at_utc": live.collected_at_utc.isoformat(),
        },
        proof_source="collect_drain_proof",
    )
    await conn.execute(
        f"UPDATE public.{META_TABLE} SET drain_attested=TRUE, updated_at_utc=NOW() WHERE model=$1",
        model,
    )


async def attest_backfill(
    conn: asyncpg.Connection, *, model: str, proof: BackfillProof
) -> None:
    if proof.model != model:
        raise PhaseGateError("backfill proof model mismatch")
    proof.validate()
    # Always re-scan the full live population (tenants may appear after a snapshot).
    live = await collect_backfill_proof(
        conn, model=model, generation=proof.generation
    )
    live.validate()
    await _append_evidence(
        conn,
        model=model,
        phase=4,
        evidence_kind=f"backfill_g{live.generation}",
        evidence={
            "generation": live.generation,
            "scope_tenant_ids": [str(t) for t in live.scope_tenant_ids],
            "scope_tenant_count": len(live.scope_tenant_ids),
            "remaining_null_rows": live.remaining_null_rows,
            "collected_at_utc": live.collected_at_utc.isoformat(),
        },
        proof_source="collect_backfill_proof",
    )
    await conn.execute(
        f"UPDATE public.{META_TABLE} SET backfill_complete=TRUE, updated_at_utc=NOW() WHERE model=$1",
        model,
    )


async def attest_index_valid(
    conn: asyncpg.Connection,
    *,
    model: str,
    proof: IndexProof,
    generation: int | None = None,
) -> None:
    if proof.model != model:
        raise PhaseGateError("index proof model mismatch")
    proof.validate()
    live = await collect_index_proof(
        conn, model=model, index_name=proof.index_name, table_name=proof.table_name
    )
    live.validate()
    kind = f"index_valid_g{generation}" if generation is not None else f"index_valid_{live.index_name}"
    await _append_evidence(
        conn,
        model=model,
        phase=6,
        evidence_kind=kind,
        evidence={
            "index_name": live.index_name,
            "table_name": live.table_name,
            "unique": live.unique_index,
            "valid": live.valid,
            "ready": live.ready,
            "collected_at_utc": live.collected_at_utc.isoformat(),
        },
        proof_source="collect_index_proof",
    )
    await conn.execute(
        f"""
        UPDATE public.{META_TABLE}
        SET index_valid_attested=TRUE, updated_at_utc=NOW()
        WHERE model=$1
        """,
        model,
    )


async def attest_cutover_ready(
    conn: asyncpg.Connection,
    *,
    model: str,
    candidate: int,
    index_name: str,
    table_name: str,
) -> None:
    state = await get_state(conn, model)
    if not state.drain_attested or not state.backfill_complete or not state.index_valid_attested:
        raise PhaseGateError(
            f"{model}: cutover_ready requires drain+backfill+index attestations first"
        )
    if state.candidate_generation != candidate:
        raise PhaseGateError(
            f"{model}: cutover_ready candidate {candidate} != metadata "
            f"{state.candidate_generation}"
        )
    # Re-verify full-population backfill at cutover-ready time (new tenants may appear).
    bf = await collect_backfill_proof(conn, model=model, generation=candidate)
    bf.validate()
    idx = await collect_index_proof(
        conn, model=model, index_name=index_name, table_name=table_name
    )
    idx.validate()
    proof = CutoverProof(
        model=model,
        candidate_generation=candidate,
        index_name=index_name,
        index_valid=True,
        drain_attested=True,
        backfill_complete=True,
        collected_at_utc=datetime.now(timezone.utc),
    )
    proof.validate()
    await _append_evidence(
        conn,
        model=model,
        phase=8,
        evidence_kind=f"cutover_ready_g{candidate}",
        evidence={
            "candidate": candidate,
            "index_name": index_name,
            "scope_tenant_count": len(bf.scope_tenant_ids),
            "collected_at_utc": proof.collected_at_utc.isoformat(),
        },
        proof_source="attest_cutover_ready",
    )
    await conn.execute(
        f"UPDATE public.{META_TABLE} SET cutover_ready=TRUE, updated_at_utc=NOW() WHERE model=$1",
        model,
    )


async def record_evidence(
    conn: asyncpg.Connection,
    *,
    model: str,
    phase: int,
    evidence_kind: str,
    evidence: dict[str, Any],
) -> None:
    """Deprecated forge path — always fail closed.

    Callers must use attest_drain / attest_backfill / attest_index_valid /
    attest_cutover_ready with live proofs.
    """
    raise PhaseGateError(
        f"{model}: record_evidence({evidence_kind}) is disabled; "
        "use proof-bound attest_* APIs (forged payloads are rejected)"
    )


def _require_evidence_for_phase(state: PhaseState, phase: int) -> None:
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
    # Live re-check: full-population backfill still complete + generation index valid.
    bf = await collect_backfill_proof(conn, model=model, generation=new_active)
    bf.validate()
    index_name = generation_index_name(model, new_active)
    table = "person_identifiers" if model == "P1" else P2_TABLE
    idx = await collect_index_proof(
        conn, model=model, index_name=index_name, table_name=table
    )
    idx.validate()
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
    await _append_evidence(
        conn,
        model=model,
        phase=8,
        evidence_kind=f"cutover_committed_gen{new_active}",
        evidence={
            "previous_active": state.active_generation,
            "new_active": new_active,
            "index_name": index_name,
        },
        proof_source="cutover_generation",
    )


async def rollback_to_previous_active(
    conn: asyncpg.Connection, *, model: str, previous_active: int
) -> None:
    """Authority-preserving rollback; requires the restored generation index."""
    state = await get_state(conn, model)
    if state.phase < 8:
        raise PhaseGateError(f"{model}: rollback-to-old requires phase>=8")
    index_name = generation_index_name(model, previous_active)
    table = "person_identifiers" if model == "P1" else P2_TABLE
    idx = await collect_index_proof(
        conn, model=model, index_name=index_name, table_name=table
    )
    idx.validate()
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
    await _append_evidence(
        conn,
        model=model,
        phase=8,
        evidence_kind=f"rollback_to_gen{previous_active}",
        evidence={
            "restored_active": previous_active,
            "demoted_generation": state.active_generation,
            "index_name": index_name,
        },
        proof_source="rollback_to_previous_active",
    )


async def begin_next_candidate_cycle(conn: asyncpg.Connection, *, model: str) -> None:
    """Clear backfill/index/cutover flags so the next generation must be re-proven.

    Call explicitly before starting the next rotation's backfill/index work.
    Cutover itself does not forge a clean slate — that would break phase-9 dry-run
    after a completed cutover.
    """
    state = await get_state(conn, model)
    if state.phase < 8:
        raise PhaseGateError(f"{model}: begin_next_candidate_cycle requires phase>=8")
    await conn.execute(
        f"""
        UPDATE public.{META_TABLE}
        SET backfill_complete = FALSE,
            index_valid_attested = FALSE,
            cutover_ready = FALSE,
            candidate_generation = NULL,
            updated_at_utc = NOW()
        WHERE model = $1
        """,
        model,
    )
    await _append_evidence(
        conn,
        model=model,
        phase=state.phase,
        evidence_kind="next_candidate_cycle_opened",
        evidence={"prior_active": state.active_generation},
        proof_source="begin_next_candidate_cycle",
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

"""Experimental dual-write, resumable backfill, and authority-preserving rotation."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import asyncpg

from experiments.m102_hmac_physical.phase_gate import PhaseGateError, get_state
from experiments.m102_hmac_physical.synthetic_hmac import synthetic_lookup_hmac


class RotationError(RuntimeError):
    """Raised for unsafe experimental rotation operations."""


def _normalized_from_cipher(cipher: bytes) -> str:
    if cipher.startswith(b"cipher:"):
        return cipher[len(b"cipher:") :].decode("utf-8")
    return cipher.hex()


async def p1_atomic_dual_write_gen(
    conn: asyncpg.Connection,
    *,
    identifier_id: UUID,
    tenant_id: UUID,
    normalized: str,
    active_version: int,
    candidate_version: int,
    candidate_column: str,
    candidate_version_column: str,
) -> bytes:
    """Atomically verify active HMAC and write candidate from the same canonical source.

    Must be called inside a transaction. Asserts exactly one owned row is updated.
    """
    if candidate_column not in {
        "exp_lookup_hmac_gen2",
        "exp_lookup_hmac_gen3",
    } or candidate_version_column not in {
        "exp_hmac_key_version_gen2",
        "exp_hmac_key_version_gen3",
    }:
        raise RotationError("unsupported candidate column pair")

    expected_active = synthetic_lookup_hmac(
        tenant_id=tenant_id,
        id_type="IR_NATIONAL_ID",  # overwritten from row below
        issuing_country_or_authority="IR",
        normalized_identifier=normalized,
        hmac_key_version=active_version,
    )
    row = await conn.fetchrow(
        """
        SELECT id_type, issuing_country_or_authority, lookup_hmac_active,
               hmac_key_version_active, id_ciphertext
        FROM person_identifiers
        WHERE id = $1 AND tenant_id = $2
        FOR UPDATE
        """,
        identifier_id,
        tenant_id,
    )
    if row is None:
        raise RotationError("identifier not found for dual-write")
    # Recompute with actual type/authority from the locked row.
    expected_active = synthetic_lookup_hmac(
        tenant_id=tenant_id,
        id_type=row["id_type"],
        issuing_country_or_authority=row["issuing_country_or_authority"],
        normalized_identifier=normalized,
        hmac_key_version=active_version,
    )
    if bytes(row["lookup_hmac_active"]) != expected_active:
        raise RotationError("active HMAC does not match canonical source for dual-write")
    if int(row["hmac_key_version_active"]) != active_version:
        raise RotationError("active key version mismatch for dual-write")

    candidate = synthetic_lookup_hmac(
        tenant_id=tenant_id,
        id_type=row["id_type"],
        issuing_country_or_authority=row["issuing_country_or_authority"],
        normalized_identifier=normalized,
        hmac_key_version=candidate_version,
    )
    result = await conn.execute(
        f"""
        UPDATE person_identifiers
        SET {candidate_column} = $2,
            {candidate_version_column} = $3
        WHERE id = $1 AND tenant_id = $4
          AND lookup_hmac_active = $5
        """,
        identifier_id,
        candidate,
        candidate_version,
        tenant_id,
        expected_active,
    )
    if result != "UPDATE 1":
        raise RotationError(f"dual-write updated unexpected rowcount: {result}")
    return candidate


async def p1_dual_write_gen2(
    conn: asyncpg.Connection,
    *,
    identifier_id: UUID,
    tenant_id: UUID,
    id_type: str,
    authority: str,
    normalized: str,
    gen2_version: int = 2,
) -> bytes:
    """Backward-compatible wrapper; prefers transactional atomic helper semantics."""
    _ = id_type, authority
    tx = conn.transaction()
    await tx.start()
    try:
        digest = await p1_atomic_dual_write_gen(
            conn,
            identifier_id=identifier_id,
            tenant_id=tenant_id,
            normalized=normalized,
            active_version=1,
            candidate_version=gen2_version,
            candidate_column="exp_lookup_hmac_gen2",
            candidate_version_column="exp_hmac_key_version_gen2",
        )
        await tx.commit()
        return digest
    except Exception:
        await tx.rollback()
        raise


async def p1_backfill_gen2_batch(
    conn: asyncpg.Connection,
    *,
    tenant_id: UUID,
    gen2_version: int = 2,
    batch_size: int = 50,
    after_id: UUID | None = None,
) -> tuple[int, UUID | None]:
    """Idempotent resumable backfill of gen2 using FOR UPDATE row locks."""
    tx = conn.transaction()
    await tx.start()
    try:
        rows = await conn.fetch(
            """
            SELECT id, id_ciphertext, hmac_key_version_active
            FROM person_identifiers
            WHERE tenant_id = $1
              AND exp_lookup_hmac_gen2 IS NULL
              AND ($2::uuid IS NULL OR id > $2)
            ORDER BY id
            LIMIT $3
            FOR UPDATE
            """,
            tenant_id,
            after_id,
            batch_size,
        )
        last: UUID | None = after_id
        for row in rows:
            normalized = _normalized_from_cipher(bytes(row["id_ciphertext"]))
            await p1_atomic_dual_write_gen(
                conn,
                identifier_id=row["id"],
                tenant_id=tenant_id,
                normalized=normalized,
                active_version=int(row["hmac_key_version_active"]),
                candidate_version=gen2_version,
                candidate_column="exp_lookup_hmac_gen2",
                candidate_version_column="exp_hmac_key_version_gen2",
            )
            last = row["id"]
        await tx.commit()
        return len(rows), last
    except Exception:
        await tx.rollback()
        raise


async def p1_backfill_gen3_batch(
    conn: asyncpg.Connection,
    *,
    tenant_id: UUID,
    gen3_version: int = 3,
    batch_size: int = 50,
    after_id: UUID | None = None,
) -> tuple[int, UUID | None]:
    tx = conn.transaction()
    await tx.start()
    try:
        rows = await conn.fetch(
            """
            SELECT id, id_ciphertext, hmac_key_version_active
            FROM person_identifiers
            WHERE tenant_id = $1
              AND exp_lookup_hmac_gen3 IS NULL
              AND ($2::uuid IS NULL OR id > $2)
            ORDER BY id
            LIMIT $3
            FOR UPDATE
            """,
            tenant_id,
            after_id,
            batch_size,
        )
        last = after_id
        for row in rows:
            normalized = _normalized_from_cipher(bytes(row["id_ciphertext"]))
            await p1_atomic_dual_write_gen(
                conn,
                identifier_id=row["id"],
                tenant_id=tenant_id,
                normalized=normalized,
                active_version=int(row["hmac_key_version_active"]),
                candidate_version=gen3_version,
                candidate_column="exp_lookup_hmac_gen3",
                candidate_version_column="exp_hmac_key_version_gen3",
            )
            last = row["id"]
        await tx.commit()
        return len(rows), last
    except Exception:
        await tx.rollback()
        raise


async def p1_assert_generation_authority(
    conn: asyncpg.Connection,
    *,
    model: str = "P1",
    generation: int,
    index_name: str,
) -> None:
    state = await get_state(conn, model)
    if state.active_generation != generation:
        raise RotationError(
            f"active_generation={state.active_generation}, expected {generation}"
        )
    exists = await conn.fetchval(
        "SELECT to_regclass($1)::text", f"public.{index_name}"
    )
    if exists is None:
        raise RotationError(
            f"active generation {generation} unique index {index_name} is missing"
        )
    valid = await conn.fetchval(
        """
        SELECT i.indisvalid AND i.indisready AND i.indisunique
        FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid
        WHERE c.relname = $1
        """,
        index_name,
    )
    if not valid:
        raise RotationError(f"active generation index {index_name} is not valid/ready")


async def p1_rollback_gen2(conn: asyncpg.Connection, *, tenant_id: UUID) -> int:
    """Refuse to wipe gen2 while metadata says generation 2 is active authority."""
    try:
        state = await get_state(conn, "P1")
    except PhaseGateError:
        state = None
    if state is not None and state.active_generation == 2:
        raise RotationError(
            "refusing to clear gen2 values while active_generation=2; "
            "use rollback_to_previous_active first and keep the gen2 index"
        )
    # Also refuse if gen2 index still names the active unique authority in catalog
    # while metadata claims gen2 — covered above. When gen2 is only a candidate,
    # clearing is allowed for rollback rehearsal.
    result = await conn.execute(
        """
        UPDATE person_identifiers
        SET exp_lookup_hmac_gen2 = NULL,
            exp_hmac_key_version_gen2 = NULL
        WHERE tenant_id = $1 AND exp_lookup_hmac_gen2 IS NOT NULL
        """,
        tenant_id,
    )
    return int(result.split()[-1])


async def p1_drop_generation_index_if_safe(
    conn: asyncpg.Connection, *, model: str, generation: int, index_name: str
) -> None:
    state = await get_state(conn, model)
    if state.active_generation == generation:
        raise RotationError(
            f"refusing DROP INDEX {index_name} while it is the active generation"
        )
    await conn.execute(f"DROP INDEX CONCURRENTLY IF EXISTS public.{index_name}")


async def p2_upsert_generation(
    conn: asyncpg.Connection,
    *,
    tenant_id: UUID,
    identifier_id: UUID,
    person_id: UUID,
    id_type: str,
    authority: str,
    normalized: str,
    hmac_key_version: int,
    status: str,
) -> UUID:
    # Parent consistency is enforced by FK/trigger; still read parent for digest.
    parent = await conn.fetchrow(
        """
        SELECT person_id, id_type, issuing_country_or_authority
        FROM person_identifiers
        WHERE tenant_id=$1 AND id=$2
        FOR UPDATE
        """,
        tenant_id,
        identifier_id,
    )
    if parent is None:
        raise RotationError("parent identifier missing for sidecar upsert")
    if parent["person_id"] != person_id:
        raise RotationError("sidecar person_id does not match parent identifier")
    if parent["id_type"] != id_type or parent["issuing_country_or_authority"] != authority:
        raise RotationError("sidecar type/authority does not match parent identifier")

    digest = synthetic_lookup_hmac(
        tenant_id=tenant_id,
        id_type=id_type,
        issuing_country_or_authority=authority,
        normalized_identifier=normalized,
        hmac_key_version=hmac_key_version,
    )
    row_id = uuid4()
    now = datetime.now(timezone.utc)
    await conn.execute(
        """
        INSERT INTO person_identifier_hmac_generations_exp (
          id, tenant_id, identifier_id, person_id, id_type,
          issuing_country_or_authority, hmac_key_version, lookup_hmac,
          generation_status, created_at_utc, retired_at_utc
        ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,NULL)
        ON CONFLICT (tenant_id, identifier_id, hmac_key_version) DO UPDATE SET
          lookup_hmac = EXCLUDED.lookup_hmac,
          generation_status = EXCLUDED.generation_status,
          person_id = EXCLUDED.person_id,
          id_type = EXCLUDED.id_type,
          issuing_country_or_authority = EXCLUDED.issuing_country_or_authority,
          retired_at_utc = CASE
            WHEN EXCLUDED.generation_status = 'RETIRED' THEN NOW()
            ELSE person_identifier_hmac_generations_exp.retired_at_utc
          END
        """,
        row_id,
        tenant_id,
        identifier_id,
        person_id,
        id_type,
        authority,
        hmac_key_version,
        digest,
        status,
        now,
    )
    return row_id


async def p2_backfill_candidate_batch(
    conn: asyncpg.Connection,
    *,
    tenant_id: UUID,
    candidate_version: int,
    batch_size: int = 50,
    after_identifier_id: UUID | None = None,
) -> tuple[int, UUID | None]:
    tx = conn.transaction()
    await tx.start()
    try:
        rows = await conn.fetch(
            """
            SELECT pi.id, pi.person_id, pi.id_type, pi.issuing_country_or_authority,
                   pi.id_ciphertext
            FROM person_identifiers pi
            WHERE pi.tenant_id = $1
              AND ($2::uuid IS NULL OR pi.id > $2)
              AND NOT EXISTS (
                SELECT 1 FROM person_identifier_hmac_generations_exp g
                WHERE g.tenant_id = pi.tenant_id
                  AND g.identifier_id = pi.id
                  AND g.hmac_key_version = $3
              )
            ORDER BY pi.id
            LIMIT $4
            FOR UPDATE OF pi
            """,
            tenant_id,
            after_identifier_id,
            candidate_version,
            batch_size,
        )
        last = after_identifier_id
        for row in rows:
            normalized = _normalized_from_cipher(bytes(row["id_ciphertext"]))
            await p2_upsert_generation(
                conn,
                tenant_id=tenant_id,
                identifier_id=row["id"],
                person_id=row["person_id"],
                id_type=row["id_type"],
                authority=row["issuing_country_or_authority"],
                normalized=normalized,
                hmac_key_version=candidate_version,
                status="CANDIDATE",
            )
            last = row["id"]
        await tx.commit()
        return len(rows), last
    except Exception:
        await tx.rollback()
        raise


async def p2_promote_candidate_to_active(
    conn: asyncpg.Connection,
    *,
    tenant_id: UUID,
    from_version: int,
    to_version: int,
) -> None:
    """Promote under an already-built ACTIVE unique index; retire previous ACTIVE."""
    await conn.execute(
        """
        UPDATE person_identifier_hmac_generations_exp
        SET generation_status='RETIRED', retired_at_utc=NOW()
        WHERE tenant_id=$1 AND hmac_key_version=$2 AND generation_status='ACTIVE'
        """,
        tenant_id,
        from_version,
    )
    await conn.execute(
        """
        UPDATE person_identifier_hmac_generations_exp
        SET generation_status='ACTIVE', retired_at_utc=NULL
        WHERE tenant_id=$1 AND hmac_key_version=$2 AND generation_status='CANDIDATE'
        """,
        tenant_id,
        to_version,
    )

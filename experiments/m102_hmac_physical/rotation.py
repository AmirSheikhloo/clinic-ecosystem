"""Experimental dual-write, resumable backfill, and two-cycle rotation helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import asyncpg

from experiments.m102_hmac_physical.synthetic_hmac import synthetic_lookup_hmac


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
    digest = synthetic_lookup_hmac(
        tenant_id=tenant_id,
        id_type=id_type,
        issuing_country_or_authority=authority,
        normalized_identifier=normalized,
        hmac_key_version=gen2_version,
    )
    await conn.execute(
        """
        UPDATE person_identifiers
        SET exp_lookup_hmac_gen2 = $2,
            exp_hmac_key_version_gen2 = $3
        WHERE id = $1
        """,
        identifier_id,
        digest,
        gen2_version,
    )
    return digest


async def p1_backfill_gen2_batch(
    conn: asyncpg.Connection,
    *,
    tenant_id: UUID,
    gen2_version: int = 2,
    batch_size: int = 50,
    after_id: UUID | None = None,
) -> tuple[int, UUID | None]:
    """Idempotent resumable backfill of gen2 from synthetic canonical source marker.

    Uses masked_display suffix after 'cipher:' is unavailable; instead re-derives
    from a synthetic mapping stored in id_ciphertext prefix 'cipher:'.
    """
    rows = await conn.fetch(
        """
        SELECT id, id_type, issuing_country_or_authority, id_ciphertext
        FROM person_identifiers
        WHERE tenant_id = $1
          AND exp_lookup_hmac_gen2 IS NULL
          AND ($2::uuid IS NULL OR id > $2)
        ORDER BY id
        LIMIT $3
        """,
        tenant_id,
        after_id,
        batch_size,
    )
    last: UUID | None = after_id
    for row in rows:
        cipher = bytes(row["id_ciphertext"])
        if cipher.startswith(b"cipher:"):
            normalized = cipher[len(b"cipher:") :].decode("utf-8")
        else:
            normalized = cipher.hex()
        digest = synthetic_lookup_hmac(
            tenant_id=tenant_id,
            id_type=row["id_type"],
            issuing_country_or_authority=row["issuing_country_or_authority"],
            normalized_identifier=normalized,
            hmac_key_version=gen2_version,
        )
        await conn.execute(
            """
            UPDATE person_identifiers
            SET exp_lookup_hmac_gen2 = $2,
                exp_hmac_key_version_gen2 = $3
            WHERE id = $1 AND exp_lookup_hmac_gen2 IS NULL
            """,
            row["id"],
            digest,
            gen2_version,
        )
        last = row["id"]
    return len(rows), last


async def p1_rollback_gen2(conn: asyncpg.Connection, *, tenant_id: UUID) -> int:
    result = await conn.execute(
        """
        UPDATE person_identifiers
        SET exp_lookup_hmac_gen2 = NULL,
            exp_hmac_key_version_gen2 = NULL
        WHERE tenant_id = $1 AND exp_lookup_hmac_gen2 IS NOT NULL
        """,
        tenant_id,
    )
    # asyncpg returns status like 'UPDATE N'
    return int(result.split()[-1])


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
        """,
        tenant_id,
        after_identifier_id,
        candidate_version,
        batch_size,
    )
    last = after_identifier_id
    for row in rows:
        cipher = bytes(row["id_ciphertext"])
        normalized = (
            cipher[len(b"cipher:") :].decode("utf-8")
            if cipher.startswith(b"cipher:")
            else cipher.hex()
        )
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
    return len(rows), last

"""Synthetic tenant/person/identifier fixtures for disposable PG15 experiments."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

import asyncpg

from experiments.m102_hmac_physical.synthetic_hmac import synthetic_lookup_hmac


@dataclass(frozen=True)
class IdentifierFixture:
    tenant_id: UUID
    person_id: UUID
    identifier_id: UUID
    id_type: str
    authority: str
    normalized: str
    active_hmac: bytes
    next_hmac: bytes | None
    active_version: int
    next_version: int | None


async def seed_tenant_person(
    conn: asyncpg.Connection,
    *,
    tenant_id: UUID | None = None,
    person_id: UUID | None = None,
) -> tuple[UUID, UUID]:
    tenant_id = tenant_id or uuid4()
    person_id = person_id or uuid4()
    now = datetime.now(timezone.utc)
    await conn.execute(
        """
        INSERT INTO tenant_registry (
          tenant_id, tenant_status, timezone_name, created_at_utc, updated_at_utc
        ) VALUES ($1, 'ACTIVE', 'UTC', $2, $2)
        ON CONFLICT (tenant_id) DO NOTHING
        """,
        tenant_id,
        now,
    )
    await conn.execute(
        """
        INSERT INTO tenant_persons (
          id, tenant_id, first_name, last_name, aggregate_version,
          created_at_utc, updated_at_utc
        ) VALUES ($1, $2, 'Synthetic', 'Patient', 1, $3, $3)
        ON CONFLICT (id) DO NOTHING
        """,
        person_id,
        tenant_id,
        now,
    )
    return tenant_id, person_id


async def insert_identifier(
    conn: asyncpg.Connection,
    *,
    tenant_id: UUID,
    person_id: UUID,
    normalized: str,
    active_version: int = 1,
    next_version: int | None = 2,
    id_type: str = "IR_NATIONAL_ID",
    authority: str = "IR",
    identifier_id: UUID | None = None,
) -> IdentifierFixture:
    identifier_id = identifier_id or uuid4()
    now = datetime.now(timezone.utc)
    active = synthetic_lookup_hmac(
        tenant_id=tenant_id,
        id_type=id_type,
        issuing_country_or_authority=authority,
        normalized_identifier=normalized,
        hmac_key_version=active_version,
    )
    nxt = None
    if next_version is not None:
        nxt = synthetic_lookup_hmac(
            tenant_id=tenant_id,
            id_type=id_type,
            issuing_country_or_authority=authority,
            normalized_identifier=normalized,
            hmac_key_version=next_version,
        )
    await conn.execute(
        """
        INSERT INTO person_identifiers (
          id, tenant_id, person_id, id_type, issuing_country_or_authority,
          id_ciphertext, nonce_96bit, auth_tag_128bit,
          encryption_key_version, aad_version, masked_display,
          verification_status, lookup_hmac_active, hmac_key_version_active,
          lookup_hmac_next, hmac_key_version_next, created_at_utc
        ) VALUES (
          $1,$2,$3,$4,$5,
          $6,$7,$8,
          1,1,'****-synth',
          'SYNTACTICALLY_VALID_UNVERIFIED',$9,$10,$11,$12,$13
        )
        """,
        identifier_id,
        tenant_id,
        person_id,
        id_type,
        authority,
        f"cipher:{normalized}".encode(),
        b"\x01" * 12,
        b"\x02" * 16,
        active,
        active_version,
        nxt,
        next_version,
        now,
    )
    return IdentifierFixture(
        tenant_id=tenant_id,
        person_id=person_id,
        identifier_id=identifier_id,
        id_type=id_type,
        authority=authority,
        normalized=normalized,
        active_hmac=active,
        next_hmac=nxt,
        active_version=active_version,
        next_version=next_version,
    )


async def fetch_index_catalog(conn: asyncpg.Connection, names: list[str]):
    return await conn.fetch(
        """
        SELECT c.relname AS name,
               i.indisunique AS unique_index,
               i.indisvalid AS valid,
               i.indisready AS ready,
               i.indislive AS live,
               i.indexrelid AS oid,
               pg_get_indexdef(i.indexrelid) AS definition
        FROM pg_index i
        JOIN pg_class c ON c.oid = i.indexrelid
        WHERE c.relname = ANY($1::text[])
        ORDER BY c.relname
        """,
        names,
    )


async def tp0002_indexes_intact(conn: asyncpg.Connection) -> bool:
    rows = await fetch_index_catalog(
        conn,
        ["uq_person_identifier_active_lookup", "uq_person_identifier_next_lookup"],
    )
    if len(rows) != 2:
        return False
    return all(r["unique_index"] and r["valid"] and r["ready"] for r in rows)

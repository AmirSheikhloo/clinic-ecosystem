"""P1 experimental DDL: additive generation columns on person_identifiers.

PROPOSED physical model only. Preserves TP0002 active/next indexes untouched.
Phase-6 candidate indexes target gen2/gen3 columns — nonredundant vs next.
"""

from __future__ import annotations

import asyncpg

P1_GEN2_INDEX = "uq_exp_p1_identifier_gen2_lookup"
P1_GEN3_INDEX = "uq_exp_p1_identifier_gen3_lookup"

P1_EXPAND_STATEMENTS = [
    """
    ALTER TABLE public.person_identifiers
      ADD COLUMN IF NOT EXISTS exp_lookup_hmac_gen2 BYTEA
        CHECK (
          exp_lookup_hmac_gen2 IS NULL
          OR octet_length(exp_lookup_hmac_gen2) = 32
        )
    """,
    """
    ALTER TABLE public.person_identifiers
      ADD COLUMN IF NOT EXISTS exp_hmac_key_version_gen2 SMALLINT
    """,
    """
    ALTER TABLE public.person_identifiers
      ADD COLUMN IF NOT EXISTS exp_lookup_hmac_gen3 BYTEA
        CHECK (
          exp_lookup_hmac_gen3 IS NULL
          OR octet_length(exp_lookup_hmac_gen3) = 32
        )
    """,
    """
    ALTER TABLE public.person_identifiers
      ADD COLUMN IF NOT EXISTS exp_hmac_key_version_gen3 SMALLINT
    """,
    """
    DO $$
    BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_exp_p1_gen2_pair'
          AND conrelid = 'public.person_identifiers'::regclass
      ) THEN
        ALTER TABLE public.person_identifiers
          ADD CONSTRAINT ck_exp_p1_gen2_pair CHECK (
            (exp_lookup_hmac_gen2 IS NULL AND exp_hmac_key_version_gen2 IS NULL)
            OR (exp_lookup_hmac_gen2 IS NOT NULL AND exp_hmac_key_version_gen2 IS NOT NULL)
          );
      END IF;
    END $$
    """,
    """
    DO $$
    BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_exp_p1_gen3_pair'
          AND conrelid = 'public.person_identifiers'::regclass
      ) THEN
        ALTER TABLE public.person_identifiers
          ADD CONSTRAINT ck_exp_p1_gen3_pair CHECK (
            (exp_lookup_hmac_gen3 IS NULL AND exp_hmac_key_version_gen3 IS NULL)
            OR (exp_lookup_hmac_gen3 IS NOT NULL AND exp_hmac_key_version_gen3 IS NOT NULL)
          );
      END IF;
    END $$
    """,
]

# No IF NOT EXISTS: callers must DROP invalid leftovers or assert catalog first.
P1_GEN2_INDEX_DDL = f"""
CREATE UNIQUE INDEX CONCURRENTLY {P1_GEN2_INDEX}
ON public.person_identifiers (
  tenant_id, id_type, issuing_country_or_authority, exp_lookup_hmac_gen2
)
WHERE exp_lookup_hmac_gen2 IS NOT NULL
"""

P1_GEN3_INDEX_DDL = f"""
CREATE UNIQUE INDEX CONCURRENTLY {P1_GEN3_INDEX}
ON public.person_identifiers (
  tenant_id, id_type, issuing_country_or_authority, exp_lookup_hmac_gen3
)
WHERE exp_lookup_hmac_gen3 IS NOT NULL
"""


async def apply_p1_expand(conn: asyncpg.Connection) -> None:
    for stmt in P1_EXPAND_STATEMENTS:
        await conn.execute(stmt)


async def drop_p1_indexes(conn: asyncpg.Connection) -> None:
    for name in (P1_GEN2_INDEX, P1_GEN3_INDEX):
        await conn.execute(f"DROP INDEX CONCURRENTLY IF EXISTS public.{name}")


async def rollback_p1_expand(conn: asyncpg.Connection) -> None:
    await drop_p1_indexes(conn)
    await conn.execute(
        """
        ALTER TABLE public.person_identifiers
          DROP CONSTRAINT IF EXISTS ck_exp_p1_gen2_pair,
          DROP CONSTRAINT IF EXISTS ck_exp_p1_gen3_pair,
          DROP COLUMN IF EXISTS exp_lookup_hmac_gen2,
          DROP COLUMN IF EXISTS exp_hmac_key_version_gen2,
          DROP COLUMN IF EXISTS exp_lookup_hmac_gen3,
          DROP COLUMN IF EXISTS exp_hmac_key_version_gen3
        """
    )

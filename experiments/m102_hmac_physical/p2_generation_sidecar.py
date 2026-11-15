"""P2 experimental DDL: generation-aware sidecar for identifier HMACs.

PROPOSED physical model only. Higher frozen-spec compatibility review burden
than P1 because storage shape extends beyond Appendix F.2 core columns.
Existing person_identifiers active/next indexes remain authoritative until an
approved cutover; sidecar indexes are separate physical authorities.
"""

from __future__ import annotations

import asyncpg

P2_TABLE = "person_identifier_hmac_generations_exp"
P2_ACTIVE_INDEX = "uq_exp_p2_hmac_active_lookup"
P2_NEXT_INDEX = "uq_exp_p2_hmac_next_lookup"
P2_CANDIDATE_INDEX = "uq_exp_p2_hmac_candidate_lookup"

P2_CREATE_TABLE = f"""
CREATE TABLE IF NOT EXISTS public.{P2_TABLE} (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES public.tenant_registry(tenant_id),
    identifier_id UUID NOT NULL,
    person_id UUID NOT NULL,
    id_type VARCHAR(32) NOT NULL
        CHECK (id_type IN ('IR_NATIONAL_ID', 'FOREIGN_FIDA_CODE', 'FOREIGN_PASSPORT')),
    issuing_country_or_authority VARCHAR(64) NOT NULL,
    hmac_key_version SMALLINT NOT NULL,
    lookup_hmac BYTEA NOT NULL CHECK (octet_length(lookup_hmac) = 32),
    generation_status VARCHAR(16) NOT NULL
        CHECK (generation_status IN ('ACTIVE', 'NEXT', 'CANDIDATE', 'RETIRED')),
    created_at_utc TIMESTAMPTZ NOT NULL,
    retired_at_utc TIMESTAMPTZ NULL,
    CONSTRAINT uq_exp_p2_identifier_version
        UNIQUE (tenant_id, identifier_id, hmac_key_version),
    CONSTRAINT uq_exp_p2_row_tenant_id UNIQUE (tenant_id, id),
    CONSTRAINT fk_exp_p2_identifier_tenant
        FOREIGN KEY (tenant_id, identifier_id)
        REFERENCES public.person_identifiers (tenant_id, id) MATCH FULL
)
"""

P2_RLS = [
    f"ALTER TABLE public.{P2_TABLE} ENABLE ROW LEVEL SECURITY",
    f"ALTER TABLE public.{P2_TABLE} FORCE ROW LEVEL SECURITY",
    f"""
    DO $$
    BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname='public' AND tablename='{P2_TABLE}'
          AND policyname='tenant_runtime_base'
      ) THEN
        CREATE POLICY tenant_runtime_base ON public.{P2_TABLE}
        AS PERMISSIVE FOR ALL TO db_app_runtime
        USING (true) WITH CHECK (true);
      END IF;
    END $$
    """,
    f"""
    DO $$
    BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname='public' AND tablename='{P2_TABLE}'
          AND policyname='tenant_runtime_guard'
      ) THEN
        CREATE POLICY tenant_runtime_guard ON public.{P2_TABLE}
        AS RESTRICTIVE FOR ALL TO db_app_runtime
        USING (
          tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
        )
        WITH CHECK (
          tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
        );
      END IF;
    END $$
    """,
    f"""
    DO $$
    BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE schemaname='public' AND tablename='{P2_TABLE}'
          AND policyname='tenant_migrator_maintenance'
      ) THEN
        CREATE POLICY tenant_migrator_maintenance ON public.{P2_TABLE}
        AS PERMISSIVE FOR ALL TO db_migrator
        USING (true) WITH CHECK (true);
      END IF;
    END $$
    """,
    f"GRANT SELECT, INSERT, UPDATE, DELETE ON public.{P2_TABLE} TO db_app_runtime",
]

P2_ACTIVE_INDEX_DDL = f"""
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS {P2_ACTIVE_INDEX}
ON public.{P2_TABLE} (
  tenant_id, id_type, issuing_country_or_authority, lookup_hmac
)
WHERE generation_status = 'ACTIVE'
"""

P2_NEXT_INDEX_DDL = f"""
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS {P2_NEXT_INDEX}
ON public.{P2_TABLE} (
  tenant_id, id_type, issuing_country_or_authority, lookup_hmac
)
WHERE generation_status = 'NEXT'
"""

P2_CANDIDATE_INDEX_DDL = f"""
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS {P2_CANDIDATE_INDEX}
ON public.{P2_TABLE} (
  tenant_id, id_type, issuing_country_or_authority, lookup_hmac
)
WHERE generation_status = 'CANDIDATE'
"""


async def apply_p2_expand(conn: asyncpg.Connection) -> None:
    await conn.execute(P2_CREATE_TABLE)
    for stmt in P2_RLS:
        await conn.execute(stmt)


async def drop_p2_indexes(conn: asyncpg.Connection) -> None:
    for name in (P2_ACTIVE_INDEX, P2_NEXT_INDEX, P2_CANDIDATE_INDEX):
        await conn.execute(f"DROP INDEX CONCURRENTLY IF EXISTS public.{name}")


async def rollback_p2_expand(conn: asyncpg.Connection) -> None:
    await drop_p2_indexes(conn)
    await conn.execute(f"DROP TABLE IF EXISTS public.{P2_TABLE} CASCADE")

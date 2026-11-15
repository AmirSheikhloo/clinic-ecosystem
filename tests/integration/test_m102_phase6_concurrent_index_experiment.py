"""Disposable PG15 experiment: Phase-6 concurrent index, invalid-index recovery.

These are experiment-only tests. No official TP0008+ migration or Package-1
implementation is created, authorized, or tested by these cases.
Both database endpoints are spawned by tests.integration.conftest Testcontainers.
"""
from __future__ import annotations

import asyncpg
import pytest
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from tests.integration.alembic_runner import upgrade_tenant_plane_async

pytestmark = pytest.mark.integration

PHASE6_NAME = "uq_m102_spike_identifier_next_phase6"
INVALID_NAME = "uq_m102_spike_invalid_scope"
PROBE_TABLE = "m102_spike_synthetic_keys"

PHASE6_DDL = f"""
CREATE UNIQUE INDEX CONCURRENTLY {PHASE6_NAME}
ON public.person_identifiers (
    tenant_id, id_type, issuing_country_or_authority, lookup_hmac_next
) WHERE lookup_hmac_next IS NOT NULL
"""


async def _migrator_connection(ep):
    conn = await asyncpg.connect(ep.asyncpg_dsn())
    assert await conn.fetchval("SELECT current_database()") in {"tenant_app", "local_hub"}
    assert 150000 <= int(await conn.fetchval("SHOW server_version_num")) < 160000
    await conn.execute("SET ROLE db_migrator")
    assert await conn.fetchval("SELECT current_user") == "db_migrator"
    return conn


@pytest.mark.asyncio
@pytest.mark.parametrize("plane", ["cloud_tenant", "local_hub"])
async def test_m102_spike_phase6_alembic_autocommit_keeps_old_index(
    plane_topology, plane: str
) -> None:
    ep = getattr(plane_topology, plane)
    await upgrade_tenant_plane_async(ep.sqlalchemy_async_url(), revision="tp0007")

    # Real Alembic Operations autocommit_block, not a text-only mock.
    engine = create_async_engine(ep.sqlalchemy_async_url(), poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SET ROLE db_migrator"))
            await connection.commit()

            def run_spike_in_alembic_context(sync_connection):
                context = MigrationContext.configure(
                    sync_connection, opts={"transactional_ddl": True}
                )
                operations = Operations(context)
                with context.begin_transaction():
                    with operations.get_context().autocommit_block():
                        operations.execute(PHASE6_DDL)

            await connection.run_sync(run_spike_in_alembic_context)
            await connection.commit()

        verifier = await _migrator_connection(ep)
        try:
            rows = await verifier.fetch(
                """
                SELECT c.relname AS name, i.indisunique AS unique_index,
                       i.indisvalid AS valid, i.indisready AS ready,
                       i.indexrelid AS oid,
                       pg_get_indexdef(i.indexrelid) AS definition
                FROM pg_index i JOIN pg_class c ON c.oid=i.indexrelid
                WHERE c.relname = ANY($1::text[])
                ORDER BY c.relname
                """,
                ["uq_person_identifier_next_lookup", PHASE6_NAME],
            )
            indexes = {row["name"]: row for row in rows}
            assert len(indexes) == 2, indexes
            assert indexes[PHASE6_NAME]["oid"] != indexes[
                "uq_person_identifier_next_lookup"]["oid"]
            assert all(row["unique_index"] and row["valid"] and row["ready"]
                       for row in indexes.values())
            assert "lookup_hmac_next IS NOT NULL" in indexes[
                PHASE6_NAME]["definition"]
            assert await verifier.fetchval(
                "SELECT version_num FROM alembic_meta.alembic_version_tp"
            ) == "tp0007"
        finally:
            await verifier.close()
    finally:
        # Explicitly decommission the synthetic duplicate index. Existing
        # uq_person_identifier_next_lookup is NEVER dropped or replaced.
        cleaner = await _migrator_connection(ep)
        try:
            await cleaner.execute(f"DROP INDEX CONCURRENTLY IF EXISTS public.{PHASE6_NAME}")
        finally:
            await cleaner.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_m102_spike_failed_concurrent_unique_index_and_retry(plane_topology) -> None:
    ep = plane_topology.cloud_tenant
    await upgrade_tenant_plane_async(ep.sqlalchemy_async_url(), revision="tp0007")
    conn = await _migrator_connection(ep)
    try:
        await conn.execute(
            f"CREATE TABLE public.{PROBE_TABLE} "
            "(marker integer PRIMARY KEY, tenant_id uuid NOT NULL, "
            "blind_key bytea NOT NULL)"
        )
        await conn.execute(
            f"""
            INSERT INTO public.{PROBE_TABLE}(marker, tenant_id, blind_key)
            VALUES (1, '01900000-0000-7000-8000-000000000001', decode(repeat('42',32),'hex')),
                   (2, '01900000-0000-7000-8000-000000000001', decode(repeat('42',32),'hex'))
            """
        )
        with pytest.raises(asyncpg.UniqueViolationError):
            await conn.execute(
                f"CREATE UNIQUE INDEX CONCURRENTLY {INVALID_NAME} "
                f"ON public.{PROBE_TABLE}(tenant_id, blind_key)"
            )
        invalid = await conn.fetchrow(
            """
            SELECT i.indisvalid AS valid, i.indisunique AS unique_index,
                   i.indisready AS ready
            FROM pg_index i JOIN pg_class c ON c.oid=i.indexrelid
            WHERE c.relname=$1
            """, INVALID_NAME
        )
        assert invalid is not None and invalid["valid"] is False
        assert invalid["unique_index"] is True

        # Invalid indexes may continue enforcing uniqueness. Do not pretend
        # IF NOT EXISTS repairs them. Recover via explicit concurrent drop.
        await conn.execute(f"DROP INDEX CONCURRENTLY public.{INVALID_NAME}")
        assert await conn.fetchval(
            "SELECT to_regclass($1)::text", f"public.{INVALID_NAME}"
        ) is None
        await conn.execute(f"DELETE FROM public.{PROBE_TABLE} WHERE marker=2")
        await conn.execute(
            f"CREATE UNIQUE INDEX CONCURRENTLY {INVALID_NAME} "
            f"ON public.{PROBE_TABLE}(tenant_id, blind_key)"
        )
        assert await conn.fetchval(
            """
            SELECT i.indisvalid AND i.indisready FROM pg_index i
            JOIN pg_class c ON c.oid=i.indexrelid WHERE c.relname=$1
            """, INVALID_NAME
        ) is True
        with pytest.raises(asyncpg.UniqueViolationError):
            await conn.execute(
                f"INSERT INTO public.{PROBE_TABLE}(marker,tenant_id,blind_key) "
                "VALUES (3,'01900000-0000-7000-8000-000000000001',"
                "decode(repeat('42',32),'hex'))"
            )
    finally:
        await conn.execute(f"DROP INDEX CONCURRENTLY IF EXISTS public.{INVALID_NAME}")
        await conn.execute(f"DROP TABLE IF EXISTS public.{PROBE_TABLE}")
        await conn.close()

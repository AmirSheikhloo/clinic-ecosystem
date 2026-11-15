"""Concurrent index build, invalid-index repair, and mandatory two-session barriers."""

from __future__ import annotations

import asyncio
from typing import Awaitable, Callable

import asyncpg
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from experiments.m102_hmac_physical.index_catalog import assert_index_catalog


class BarrierError(RuntimeError):
    """Raised when the overlapping-writer lock wait is not observed."""


async def create_unique_index_concurrently_via_alembic(
    sqlalchemy_async_url: str, ddl: str
) -> None:
    """Execute CREATE UNIQUE INDEX CONCURRENTLY inside Alembic autocommit_block."""
    engine = create_async_engine(sqlalchemy_async_url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SET ROLE db_migrator"))
            await connection.commit()

            def _run(sync_connection):
                context = MigrationContext.configure(
                    sync_connection, opts={"transactional_ddl": True}
                )
                operations = Operations(context)
                with context.begin_transaction():
                    with operations.get_context().autocommit_block():
                        operations.execute(ddl)

            await connection.run_sync(_run)
            await connection.commit()
    finally:
        await engine.dispose()


async def create_and_assert_unique_index(
    *,
    sqlalchemy_async_url: str,
    inspect_dsn: str,
    ddl: str,
    index_name: str,
    table_name: str,
    required_fragments: list[str],
    forbidden_fragments: list[str] | None = None,
) -> None:
    """Build concurrently, then fail closed unless catalog matches exactly."""
    await create_unique_index_concurrently_via_alembic(sqlalchemy_async_url, ddl)
    conn = await asyncpg.connect(inspect_dsn)
    try:
        await conn.execute("SET ROLE db_migrator")
        await assert_index_catalog(
            conn,
            index_name=index_name,
            table_name=table_name,
            required_fragments=required_fragments,
            forbidden_fragments=forbidden_fragments,
            unique=True,
            valid=True,
            ready=True,
        )
    finally:
        await conn.close()


async def wait_until_waiting_on_lock(
    inspector: asyncpg.Connection, *, backend_pid: int, timeout_s: float = 5.0
) -> bool:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_s
    while loop.time() < deadline:
        state = await inspector.fetchval(
            "SELECT wait_event_type FROM pg_stat_activity WHERE pid = $1",
            backend_pid,
        )
        if state in {"Lock", "LWLock"}:
            return True
        await asyncio.sleep(0.05)
    return False


async def two_session_unique_conflict(
    *,
    dsn: str,
    setup_role: str = "db_migrator",
    first_insert: Callable[[asyncpg.Connection], Awaitable[None]],
    second_insert: Callable[[asyncpg.Connection], Awaitable[None]],
    require_observed_lock_wait: bool = True,
    first_commits: bool = True,
) -> tuple[str, str, bool]:
    """Prove overlapping uncommitted writers with a mandatory lock-wait assertion.

    Returns (first_outcome, second_outcome, lock_wait_observed).
    """
    conn1 = await asyncpg.connect(dsn)
    conn2 = await asyncpg.connect(dsn)
    inspector = await asyncpg.connect(dsn)
    try:
        await conn1.execute(f"SET ROLE {setup_role}")
        await conn2.execute(f"SET ROLE {setup_role}")
        await inspector.execute(f"SET ROLE {setup_role}")

        tx1 = conn1.transaction()
        await tx1.start()
        await first_insert(conn1)
        pid2_holder: dict[str, int] = {}

        async def second() -> str:
            tx2 = conn2.transaction()
            await tx2.start()
            pid2_holder["pid"] = await conn2.fetchval("SELECT pg_backend_pid()")
            try:
                await second_insert(conn2)
                await tx2.commit()
                return "inserted"
            except asyncpg.UniqueViolationError:
                await tx2.rollback()
                return "unique_violation"
            except Exception:
                await tx2.rollback()
                raise

        task = asyncio.create_task(second())
        # Wait until session-2 has a backend pid, then require lock wait.
        loop = asyncio.get_running_loop()
        deadline = loop.time() + 5.0
        while "pid" not in pid2_holder and loop.time() < deadline:
            await asyncio.sleep(0.02)
        if "pid" not in pid2_holder:
            task.cancel()
            await tx1.rollback()
            raise BarrierError("session-2 never started INSERT before timeout")

        lock_wait_observed = await wait_until_waiting_on_lock(
            inspector, backend_pid=pid2_holder["pid"], timeout_s=5.0
        )
        if require_observed_lock_wait and not lock_wait_observed:
            task.cancel()
            await tx1.rollback()
            raise BarrierError(
                "session-2 was not observed waiting on Lock/LWLock before session-1 resolved"
            )

        if first_commits:
            await tx1.commit()
            first_outcome = "committed"
        else:
            await tx1.rollback()
            first_outcome = "rolled_back"
        second_result = await asyncio.wait_for(task, timeout=10.0)
        return first_outcome, second_result, lock_wait_observed
    finally:
        await conn1.close()
        await conn2.close()
        await inspector.close()


async def force_invalid_unique_index(
    conn: asyncpg.Connection, *, table: str, index_name: str, column: str
) -> None:
    """Create a unique index that fails validation, leaving an INVALID catalog entry."""
    await conn.execute(f"DROP INDEX CONCURRENTLY IF EXISTS public.{index_name}")
    await conn.execute(f"DROP TABLE IF EXISTS public.{table}")
    await conn.execute(
        f"""
        CREATE TABLE public.{table} (
          id int PRIMARY KEY,
          tenant_id uuid NOT NULL,
          {column} bytea NOT NULL
        )
        """
    )
    dup = b"\xab" * 32
    tid = "01900000-0000-7000-8000-0000000000aa"
    await conn.execute(
        f"INSERT INTO public.{table}(id, tenant_id, {column}) "
        "VALUES (1, $1::uuid, $2), (2, $1::uuid, $2)",
        tid,
        dup,
    )
    try:
        await conn.execute(
            f"""
            CREATE UNIQUE INDEX CONCURRENTLY {index_name}
            ON public.{table} (tenant_id, {column})
            """
        )
    except (asyncpg.UniqueViolationError, asyncpg.PostgresError):
        pass
    row = await conn.fetchrow(
        """
        SELECT i.indisvalid, i.indisready, c.relname
        FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid
        WHERE c.relname = $1
        """,
        index_name,
    )
    if row is None:
        raise RuntimeError(f"expected invalid index catalog row for {index_name}")
    if row["indisvalid"]:
        await conn.execute(f"DROP INDEX CONCURRENTLY IF EXISTS public.{index_name}")
        raise RuntimeError("index unexpectedly valid after duplicate concurrent build")


async def drop_invalid_and_retry(
    conn: asyncpg.Connection,
    *,
    table: str,
    index_name: str,
    column: str,
) -> dict:
    """Detect INVALID index, drop concurrently, dedupe rows, rebuild, verify valid."""
    before = await conn.fetchrow(
        """
        SELECT i.indisvalid AS valid, i.indisready AS ready
        FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid
        WHERE c.relname = $1
        """,
        index_name,
    )
    assert before is not None
    assert before["valid"] is False
    await conn.execute(f"DROP INDEX CONCURRENTLY IF EXISTS public.{index_name}")
    await conn.execute(f"DELETE FROM public.{table} WHERE id = 2")
    await conn.execute(
        f"""
        CREATE UNIQUE INDEX CONCURRENTLY {index_name}
        ON public.{table} (tenant_id, {column})
        """
    )
    after = await conn.fetchrow(
        """
        SELECT i.indisvalid AS valid, i.indisready AS ready, i.indisunique AS unique_index
        FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid
        WHERE c.relname = $1
        """,
        index_name,
    )
    assert after is not None
    return dict(after)


async def recover_invalid_generation_index(
    conn: asyncpg.Connection,
    *,
    index_name: str,
    rebuild_ddl: str,
    resolve_duplicates: Callable[[asyncpg.Connection], Awaitable[None]],
) -> None:
    """Fail-closed recovery for a real experimental generation index."""
    row = await conn.fetchrow(
        """
        SELECT i.indisvalid AS valid
        FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid
        WHERE c.relname = $1
        """,
        index_name,
    )
    if row is None:
        raise IndexError(f"no catalog row for {index_name}")
    if row["valid"]:
        raise RuntimeError(f"{index_name} is unexpectedly valid; nothing to recover")
    await conn.execute(f"DROP INDEX CONCURRENTLY IF EXISTS public.{index_name}")
    await resolve_duplicates(conn)
    await conn.execute(rebuild_ddl)
    after = await conn.fetchrow(
        """
        SELECT i.indisvalid AS valid, i.indisready AS ready, i.indisunique AS unique_index
        FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid
        WHERE c.relname = $1
        """,
        index_name,
    )
    if after is None or not after["valid"] or not after["ready"] or not after["unique_index"]:
        raise RuntimeError(f"recovery failed for {index_name}: {after}")

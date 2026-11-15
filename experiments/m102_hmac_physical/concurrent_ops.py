"""Concurrent index build, invalid-index repair, and two-session barriers."""

from __future__ import annotations

import asyncio
from typing import Awaitable, Callable

import asyncpg
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool


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
) -> tuple[str, str]:
    """Prove overlapping uncommitted writers with deterministic barrier.

    Session-1 inserts and holds the transaction open.
    Session-2 starts after session-1 insert and blocks on uniqueness.
    Session-1 then commits; session-2 must observe UniqueViolation.
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
        # Allow session-2 to reach the blocking INSERT.
        await asyncio.sleep(0.15)
        pid2 = pid2_holder.get("pid")
        if pid2 is not None:
            await wait_until_waiting_on_lock(inspector, backend_pid=pid2, timeout_s=3.0)
        await tx1.commit()
        second_result = await asyncio.wait_for(task, timeout=10.0)
        return "committed", second_result
    finally:
        await conn1.close()
        await conn2.close()
        await inspector.close()


async def force_invalid_unique_index(
    conn: asyncpg.Connection, *, table: str, index_name: str, column: str
) -> None:
    """Create a unique index that fails validation, leaving an INVALID catalog entry.

    Technique: insert duplicate keys, attempt concurrent unique index, catch failure.
    """
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
    # Resolve cause: keep one row only.
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

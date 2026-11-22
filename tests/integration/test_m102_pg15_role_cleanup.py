"""Actual PostgreSQL 15 SQLSTATE 25P02 cleanup ordering, both migration planes.

This verifies the real SQLAlchemy+asyncpg same-connection sequence.
It is NOT evidence of Alembic autocommit_block/TP0011 or Gate A completion.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine
from tests.integration.docker_probe import DOCKER_AVAILABLE, SKIP_REASON

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not DOCKER_AVAILABLE, reason=SKIP_REASON),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "endpoint_name,role_name",
    [
        ("cloud_tenant", "db_migrator"),
        ("cloud_control", "cp_db_migrator"),
    ],
)
async def test_real_pg15_aborted_transaction_requires_rollback_before_reset_role(
    plane_topology, endpoint_name, role_name,
):
    endpoint = getattr(plane_topology, endpoint_name)
    engine = create_async_engine(endpoint.sqlalchemy_async_url())
    try:
        async with engine.connect() as conn:
            await conn.execute(text(f'SET ROLE "{role_name}"'))
            assert await conn.scalar(text("SELECT current_user")) == role_name
            with pytest.raises(DBAPIError):
                await conn.execute(text("SELECT 1/0"))
            # PostgreSQL 25P02: RESET ROLE is forbidden while txn is aborted.
            with pytest.raises(DBAPIError) as still_aborted:
                await conn.execute(text("RESET ROLE"))
            assert "25P02" in str(still_aborted.value) or "aborted" in str(still_aborted.value).lower()
            await conn.rollback()
            await conn.execute(text("RESET ROLE"))
            await conn.commit()
            user = await conn.scalar(text("SELECT current_user"))
            session_user = await conn.scalar(text("SELECT session_user"))
            assert user == session_user == endpoint.user
    finally:
        await engine.dispose()



@pytest.mark.asyncio
@pytest.mark.parametrize(
    "plane,role_name",
    [
        ("tenant_plane", "db_migrator"),
        ("control_plane", "cp_db_migrator"),
    ],
)
async def test_real_env_py_propagates_pg15_division_by_zero_after_reset(
    plane_topology, plane, role_name,
):
    """Run the actual env.py coroutine AST against real PG15 asyncpg engine.

    This covers SQLSTATE 22012 + the subsequent 25P02 rollback prerequisite,
    not Alembic's autocommit_block or later TP0008+ migrations.
    """
    import ast
    from pathlib import Path
    from types import SimpleNamespace
    endpoint = (
        plane_topology.cloud_tenant if plane == "tenant_plane"
        else plane_topology.cloud_control
    )
    engine = create_async_engine(endpoint.sqlalchemy_async_url())
    source_path = (
        Path(__file__).resolve().parents[2] / "migrations" / plane / "env.py"
    )
    source = source_path.read_text(encoding="utf-8")
    fn_node = next(
        n for n in ast.parse(source).body
        if isinstance(n, ast.AsyncFunctionDef) and n.name == "run_async_migrations"
    )

    def failing_live_migration(connection):
        assert connection.execute(text("SELECT current_user")).scalar() == role_name
        connection.execute(text("SELECT 1/0"))

    namespace = {
        "config": SimpleNamespace(
            config_ini_section="alembic", get_section=lambda _: {},
        ),
        "get_url": endpoint.sqlalchemy_async_url,
        "async_engine_from_config": lambda *_a, **_kw: engine,
        "pool": SimpleNamespace(NullPool=object()),
        "text": text,
        "MIGRATOR_ROLE": role_name,
        "do_run_migrations": failing_live_migration,
    }
    exec(
        compile(ast.Module(body=[fn_node], type_ignores=[]), str(source_path), "exec"),
        namespace,
    )
    with pytest.raises(DBAPIError) as exc:
        await namespace["run_async_migrations"]()
    assert "division by zero" in str(exc.value).lower()

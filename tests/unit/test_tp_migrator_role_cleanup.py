"""M1-02 narrow regression: TP Alembic resets role only after rollback.

Execute the actual async function body with a fake same-connection adapter.
This is unit evidence, NOT a PostgreSQL integration or Gate A claim.
"""
from __future__ import annotations

import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

ENV_PATH = Path(__file__).resolve().parents[2] / "migrations/tenant_plane/env.py"


class _FakeConnection:
    def __init__(self, events: list[str], *, abort: bool = False):
        self.events = events
        self.abort = abort
        self.failed_transaction = False

    async def execute(self, stmt: str) -> None:
        if self.failed_transaction:
            raise AssertionError("RESET ROLE attempted inside aborted transaction")
        self.events.append(stmt)

    async def run_sync(self, _fn):
        self.events.append("MIGRATE")
        if self.abort:
            self.failed_transaction = True
            raise RuntimeError("representative SQL transaction abort")

    async def rollback(self) -> None:
        self.events.append("ROLLBACK")
        self.failed_transaction = False

    async def commit(self) -> None:
        self.events.append("COMMIT")


class _FakeConnectable:
    def __init__(self, events: list[str], *, abort: bool):
        self.events = events
        self.connection = _FakeConnection(events, abort=abort)

    def connect(self):
        parent = self

        class _Context:
            async def __aenter__(self):
                return parent.connection

            async def __aexit__(self, *_args):
                parent.events.append("CLOSE")

        return _Context()

    async def dispose(self) -> None:
        self.events.append("DISPOSE")


def _load_actual_run_async_migrations(events: list[str], *, abort: bool):
    source = ENV_PATH.read_text(encoding="utf-8")
    function = next(
        n for n in ast.parse(source).body
        if isinstance(n, ast.AsyncFunctionDef) and n.name == "run_async_migrations"
    )
    engine = _FakeConnectable(events, abort=abort)
    namespace = {
        "config": SimpleNamespace(config_ini_section="alembic", get_section=lambda _: {}),
        "get_url": lambda: "postgresql+asyncpg://test-host/test",
        "async_engine_from_config": lambda *_a, **_k: engine,
        "pool": SimpleNamespace(NullPool=object()),
        "text": lambda sql: sql,
        "MIGRATOR_ROLE": "db_migrator",
        "do_run_migrations": lambda *_: None,
    }
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(ENV_PATH), "exec"), namespace)
    return namespace["run_async_migrations"]


def test_sql_abort_rolls_back_before_reset_role():
    events: list[str] = []
    fn = _load_actual_run_async_migrations(events, abort=True)
    with pytest.raises(RuntimeError, match="representative SQL transaction abort"):
        asyncio.run(fn())
    assert events == [
        'SET ROLE "db_migrator"', "MIGRATE", "ROLLBACK", "RESET ROLE",
        "COMMIT", "CLOSE", "DISPOSE",
    ]


def test_success_resets_role_and_disposes_engine():
    events: list[str] = []
    fn = _load_actual_run_async_migrations(events, abort=False)
    asyncio.run(fn())
    assert events == [
        'SET ROLE "db_migrator"', "MIGRATE", "COMMIT", "ROLLBACK",
        "RESET ROLE", "COMMIT", "CLOSE", "DISPOSE",
    ]

"""M1-02 narrow regression: CP Alembic resets role only after rollback."""
from __future__ import annotations

import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

ENV_PATH = Path(__file__).resolve().parents[2] / "migrations/control_plane/env.py"


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
        "MIGRATOR_ROLE": "cp_db_migrator",
        "do_run_migrations": lambda *_: None,
    }
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(ENV_PATH), "exec"), namespace)
    return namespace["run_async_migrations"]


def test_cp_sql_abort_rolls_back_before_reset_role():
    events: list[str] = []
    fn = _load_actual_run_async_migrations(events, abort=True)
    with pytest.raises(RuntimeError, match="representative SQL transaction abort"):
        asyncio.run(fn())
    assert events == [
        'SET ROLE "cp_db_migrator"', "MIGRATE", "ROLLBACK", "RESET ROLE",
        "COMMIT", "CLOSE", "DISPOSE",
    ]


def test_cp_success_resets_role_and_disposes_engine():
    events: list[str] = []
    fn = _load_actual_run_async_migrations(events, abort=False)
    asyncio.run(fn())
    assert events == [
        'SET ROLE "cp_db_migrator"', "MIGRATE", "COMMIT", "ROLLBACK",
        "RESET ROLE", "COMMIT", "CLOSE", "DISPOSE",
    ]



def test_primary_migration_error_survives_secondary_rollback_failure(monkeypatch):
    async def connection_lost(self):
        self.events.append("ROLLBACK-FAILED")
        raise ConnectionError("disconnected during rollback")
    monkeypatch.setattr(_FakeConnection, "rollback", connection_lost)
    events: list[str] = []
    fn = _load_actual_run_async_migrations(events, abort=True)
    with pytest.raises(RuntimeError, match="representative SQL transaction abort"):
        asyncio.run(fn())
    assert events[-2:] == ["CLOSE", "DISPOSE"]


def test_set_role_permission_error_is_not_replaced_by_cleanup(monkeypatch):
    async def role_denied(self, statement):
        if statement.startswith("SET ROLE"):
            self.events.append("SET-ROLE-DENIED")
            raise PermissionError("SQLSTATE 42501")
        self.events.append(statement)
    monkeypatch.setattr(_FakeConnection, "execute", role_denied)
    events: list[str] = []
    fn = _load_actual_run_async_migrations(events, abort=False)
    with pytest.raises(PermissionError, match="42501"):
        asyncio.run(fn())
    assert "RESET ROLE" not in events
    assert events[-2:] == ["CLOSE", "DISPOSE"]

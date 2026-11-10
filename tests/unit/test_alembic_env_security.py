"""Static/unit checks for Alembic env URL precedence and fixed SET ROLE."""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TP_ENV = REPO_ROOT / "migrations" / "tenant_plane" / "env.py"
CP_ENV = REPO_ROOT / "migrations" / "control_plane" / "env.py"
RUNNER = REPO_ROOT / "tests" / "integration" / "alembic_runner.py"


def test_env_files_use_alembic_meta_schema_online_and_offline() -> None:
    for path in (TP_ENV, CP_ENV):
        text = path.read_text(encoding="utf-8")
        assert 'VERSION_TABLE_SCHEMA = "alembic_meta"' in text
        assert text.count("version_table_schema=VERSION_TABLE_SCHEMA") >= 2


def test_set_role_is_fixed_plane_constant_not_env_override() -> None:
    tp = TP_ENV.read_text(encoding="utf-8")
    cp = CP_ENV.read_text(encoding="utf-8")
    assert 'MIGRATOR_ROLE = "db_migrator"' in tp
    assert 'MIGRATOR_ROLE = "cp_db_migrator"' in cp
    assert "TENANT_PLANE_SET_ROLE" not in tp
    assert "CONTROL_PLANE_SET_ROLE" not in cp
    assert 'SET ROLE "{MIGRATOR_ROLE}"' in tp
    assert 'SET ROLE "{MIGRATOR_ROLE}"' in cp


def test_get_url_prefers_non_placeholder_sqlalchemy_url() -> None:
    for path in (TP_ENV, CP_ENV):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        fn = next(
            n
            for n in tree.body
            if isinstance(n, ast.FunctionDef) and n.name == "get_url"
        )
        src = ast.get_source_segment(source, fn)
        assert src is not None
        assert "_is_placeholder_url" in src
        assert "get_main_option" in src
        assert src.index("get_main_option") < src.index("environ.get")


def test_alembic_runner_does_not_mutate_os_environ() -> None:
    text = RUNNER.read_text(encoding="utf-8")
    assert "os.environ[" not in text
    assert "os.environ.update" not in text
    assert 'set_main_option("sqlalchemy.url"' in text

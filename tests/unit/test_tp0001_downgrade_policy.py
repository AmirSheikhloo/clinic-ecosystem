"""Static check: TP0001 downgrade refuses destructive rollback (Appendix E.4)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATION = (
    REPO_ROOT
    / "migrations"
    / "tenant_plane"
    / "versions"
    / "tp0001_extensions_and_tenant_root.py"
)


def _load_tp0001():
    spec = importlib.util.spec_from_file_location("tp0001_mod", MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_tp0001_downgrade_is_explicitly_irreversible() -> None:
    module = _load_tp0001()
    with pytest.raises(NotImplementedError, match="E\\.4|irreversible|restore"):
        module.downgrade()


def test_cp0000_revision_file_absent() -> None:
    versions = REPO_ROOT / "migrations" / "control_plane" / "versions"
    py_files = list(versions.glob("*.py"))
    assert py_files == [], f"unexpected CP revision files: {py_files}"

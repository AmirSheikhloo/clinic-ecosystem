"""Fail-closed upgrade wrapper — refuses ambiguous Alembic targets."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

EXP_ROOT = Path(__file__).resolve().parents[1]

ALLOWED_TARGETS = frozenset(
    {
        "exp_e03_base",
        "exp_e03_h6",
        "exp_e03_h8",
        "exp_e03_cat1",
        "exp_e03_cat2",
        "hmac_rotation@head",
        "tenant_catalog@head",
        "hmac_rotation@exp_e03_h6",
        "hmac_rotation@exp_e03_h8",
        "tenant_catalog@exp_e03_cat1",
        "tenant_catalog@exp_e03_cat2",
    }
)
FORBIDDEN_TARGETS = frozenset({"head", "heads", ""})


class UpgradeTargetError(ValueError):
    """Raised before any schema mutation when the target is unsafe."""


def make_config(database_url: str) -> Config:
    cfg = Config(str(EXP_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(EXP_ROOT))
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


def assert_safe_target(target: str) -> None:
    t = (target or "").strip()
    if t in FORBIDDEN_TARGETS or t.lower() in FORBIDDEN_TARGETS:
        raise UpgradeTargetError(
            f"refusing dangerous Alembic target {target!r} before schema mutation"
        )
    if t not in ALLOWED_TARGETS:
        raise UpgradeTargetError(
            f"refusing unknown/unallowlisted Alembic target {target!r} before schema mutation"
        )


def safe_upgrade(database_url: str, target: str) -> None:
    assert_safe_target(target)
    cfg = make_config(database_url)
    command.upgrade(cfg, target)


def list_heads(database_url: str) -> list[str]:
    cfg = make_config(database_url)
    script = ScriptDirectory.from_config(cfg)
    return sorted(script.get_heads())

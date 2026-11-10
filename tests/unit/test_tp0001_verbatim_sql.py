"""Static checks that TP0001 embeds verbatim F.2 tenant_registry SQL."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATION = (
    REPO_ROOT
    / "migrations"
    / "tenant_plane"
    / "versions"
    / "tp0001_extensions_and_tenant_root.py"
)
SPEC = REPO_ROOT / "docs" / "FINAL_MASTER_SPECIFICATION_v3.0.1_FINAL.txt"

VERBATIM_FRAGMENT = """CREATE TABLE tenant_registry (
    tenant_id UUID PRIMARY KEY,
    tenant_status VARCHAR(24) NOT NULL
        CHECK (tenant_status IN ('ACTIVE', 'SUSPENDED', 'DELETING', 'DELETED')),
    timezone_name TEXT NOT NULL,
    created_at_utc TIMESTAMPTZ NOT NULL,
    updated_at_utc TIMESTAMPTZ NOT NULL
);"""


def test_tp0001_contains_verbatim_f2_tenant_registry() -> None:
    text = MIGRATION.read_text(encoding="utf-8")
    assert "CREATE EXTENSION IF NOT EXISTS btree_gist;" in text
    assert VERBATIM_FRAGMENT in text
    assert "uuid_generate" not in text.lower()
    assert "gen_random_uuid" not in text.lower()
    assert "DEFAULT" not in VERBATIM_FRAGMENT
    # Ensure other F.2 tables were not pulled into TP0001
    assert "tenant_persons" not in text
    assert "ENABLE ROW LEVEL SECURITY" not in text.upper()


def test_spec_still_contains_same_f2_contract() -> None:
    spec = SPEC.read_text(encoding="utf-8")
    assert VERBATIM_FRAGMENT in spec

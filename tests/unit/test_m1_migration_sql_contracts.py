"""Static checks that M1 migrations preserve verbatim F.3/F.4/F.5 fragments."""

from __future__ import annotations

from pathlib import Path

VERSIONS = Path(__file__).resolve().parents[2] / "migrations" / "tenant_plane" / "versions"


def test_tp0005_contains_online_exclude_predicate() -> None:
    text = (VERSIONS / "tp0005_appointments_allocations_holds.py").read_text(encoding="utf-8")
    assert "CONSTRAINT ex_online_resource_time" in text
    assert "EXCLUDE USING gist" in text
    assert "capacity_pool = 'ONLINE'" in text
    assert "'PENDING_PAYMENT_HOLD', 'CONFIRMED', 'CHECKED_IN'" in text
    assert "CREATE TABLE hold_expiry_work_items" in text


def test_tp0004_contains_f3_match_simple_note_target() -> None:
    text = (VERSIONS / "tp0004_catalog_resources_requirements.py").read_text(encoding="utf-8")
    assert "MATCH SIMPLE" in text
    assert "DEFAULT_ONLINE_SLOT_STREAM" in text


def test_tp0007_forces_rls_on_appointments() -> None:
    text = (VERSIONS / "tp0007_rls_and_role_policies.py").read_text(encoding="utf-8")
    assert "ALTER TABLE appointments ENABLE ROW LEVEL SECURITY" in text
    assert "ALTER TABLE appointments FORCE ROW LEVEL SECURITY" in text
    assert "tenant_runtime_guard ON appointments" in text
    assert "REVOKE UPDATE, DELETE ON TABLE audit_entries FROM db_app_runtime" in text

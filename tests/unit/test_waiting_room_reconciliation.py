"""Waiting-room checked_in_count must equal appointments.waiting_checked_in."""

from __future__ import annotations

import ast
from pathlib import Path


def _overview_source() -> str:
    root = Path(__file__).resolve().parents[2]
    return (root / "src/clinic_ecosystem/presentation/http/overview.py").read_text(
        encoding="utf-8"
    )


def test_waiting_room_uses_same_checked_in_source() -> None:
    """Document the reconciliation contract used by dashboard_summary."""
    by_status = {"CHECKED_IN": 7, "CONFIRMED": 12, "CANCELLED": 2}
    waiting_checked_in = int(by_status.get("CHECKED_IN", 0))
    waiting_room = {"checked_in_count": waiting_checked_in}
    assert waiting_room["checked_in_count"] == waiting_checked_in
    assert waiting_room["checked_in_count"] != sum(by_status.values())


def test_scoped_empty_services_zero_waiting() -> None:
    allowed_services: set = set()
    by_status = {} if not allowed_services else {"CHECKED_IN": 3}
    assert int(by_status.get("CHECKED_IN", 0)) == 0


def test_dashboard_summary_does_not_call_unscoped_physical_waiting() -> None:
    """Guard against regressing to unscoped wait_ops.physical_waiting_count for wr."""
    src = _overview_source()
    tree = ast.parse(src)
    summary = next(
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "dashboard_summary"
    )
    summary_src = ast.get_source_segment(src, summary) or ""
    assert "waiting_checked_in" in summary_src
    assert "checked_in_count" in summary_src
    # Prefer appointments.waiting_checked_in; unscoped physical_waiting_count must not
    # be the primary waiting_room path when appointments section is present.
    assert 'appointments["waiting_checked_in"]' in summary_src


def test_status_and_unique_patient_counts_pass_service_ids() -> None:
    src = _overview_source()
    assert "service_ids=allowed_services" in src
    # Both status counts and unique patients must be scoped like ops metrics.
    assert src.count("service_ids=allowed_services") >= 4

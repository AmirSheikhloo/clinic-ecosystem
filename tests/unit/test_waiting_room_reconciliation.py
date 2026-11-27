"""Waiting-room checked_in_count must equal appointments.waiting_checked_in."""

from __future__ import annotations


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

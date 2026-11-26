"""Unit tests for appointment lifecycle transition rules."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from clinic_ecosystem.domain.scheduling.transitions import (
    ALLOWED_TRANSITIONS,
    InvalidStatusTransition,
    validate_transition,
)


def test_allowed_transition_matrix() -> None:
    assert ALLOWED_TRANSITIONS[("CONFIRMED", "CHECKED_IN")] == "check_in"
    assert ALLOWED_TRANSITIONS[("CONFIRMED", "NO_SHOW")] == "no_show"
    assert ALLOWED_TRANSITIONS[("CONFIRMED", "CANCELLED")] == "cancel"
    assert ALLOWED_TRANSITIONS[("CHECKED_IN", "COMPLETED")] == "complete"
    assert ALLOWED_TRANSITIONS[("CHECKED_IN", "CANCELLED")] == "cancel"
    assert ("CHECKED_IN", "NO_SHOW") not in ALLOWED_TRANSITIONS
    assert ("CONFIRMED", "COMPLETED") not in ALLOWED_TRANSITIONS
    assert ("COMPLETED", "CANCELLED") not in ALLOWED_TRANSITIONS


def test_validate_happy_paths() -> None:
    start = datetime(2030, 1, 1, 10, 0, tzinfo=timezone.utc)
    now = start + timedelta(minutes=5)
    assert validate_transition(
        from_status="CONFIRMED", to_status="CHECKED_IN", now=now, scheduled_start_at_utc=start
    ) == "check_in"
    assert validate_transition(
        from_status="CHECKED_IN", to_status="COMPLETED", now=now, scheduled_start_at_utc=start
    ) == "complete"
    assert validate_transition(
        from_status="CONFIRMED", to_status="NO_SHOW", now=now, scheduled_start_at_utc=start
    ) == "no_show"
    assert validate_transition(
        from_status="CHECKED_IN", to_status="CANCELLED", now=now, scheduled_start_at_utc=start
    ) == "cancel"


def test_reject_illegal_and_premature_no_show() -> None:
    start = datetime(2030, 6, 1, 12, 0, tzinfo=timezone.utc)
    before = start - timedelta(seconds=1)
    with pytest.raises(InvalidStatusTransition) as illegal:
        validate_transition(
            from_status="CONFIRMED",
            to_status="COMPLETED",
            now=start,
            scheduled_start_at_utc=start,
        )
    assert illegal.value.code == "invalid_status_transition"
    assert illegal.value.extra["current_status"] == "CONFIRMED"

    with pytest.raises(InvalidStatusTransition) as premature:
        validate_transition(
            from_status="CONFIRMED",
            to_status="NO_SHOW",
            now=before,
            scheduled_start_at_utc=start,
        )
    assert premature.value.code == "no_show_before_start"

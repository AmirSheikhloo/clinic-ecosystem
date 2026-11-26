"""Unit coverage for group conflict serialization and waiting-room day bounds."""

from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import uuid4

from clinic_ecosystem.application.scheduling.exceptions import (
    ConflictDisplayItem,
    GroupManualOverlapAcknowledgementRequired,
)
from clinic_ecosystem.presentation.http.appointments import _tehran_day_bounds
from clinic_ecosystem.presentation.scheduling import (
    serialize_group_manual_conflict_response,
)


def test_serialize_group_conflicts_keyed_by_client_line_id() -> None:
    appt_id = uuid4()
    start = datetime(2026, 11, 26, 10, 0, tzinfo=timezone.utc)
    end = datetime(2026, 11, 26, 10, 30, tzinfo=timezone.utc)
    exc = GroupManualOverlapAcknowledgementRequired(
        {
            "line-b": [
                ConflictDisplayItem(
                    appointment_id=appt_id,
                    display_safe_patient_name="Ada",
                    booking_channel="MANUAL_STAFF",
                    scheduled_start_at_utc=start,
                    scheduled_end_at_utc=end,
                )
            ],
            "line-a": [],
        }
    )
    body = serialize_group_manual_conflict_response(exc)
    assert body["error"] == "manual_overlap_acknowledgement_required"
    assert list(body["line_conflicts"]) == ["line-a", "line-b"]
    assert body["line_conflicts"]["line-b"][0]["appointment_id"] == str(appt_id)
    assert body["line_conflicts"]["line-b"][0]["display_safe_patient_name"] == "Ada"


def test_tehran_day_bounds_are_half_open_utc() -> None:
    start, end = _tehran_day_bounds(date(2026, 11, 26))
    assert start.tzinfo is not None and end.tzinfo is not None
    assert start.astimezone(timezone.utc).isoformat() == "2026-11-25T20:30:00+00:00"
    assert end.astimezone(timezone.utc).isoformat() == "2026-11-26T20:30:00+00:00"
    assert end > start

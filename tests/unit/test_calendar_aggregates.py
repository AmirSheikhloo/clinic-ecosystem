"""Calendar period aggregates — scope-aware totals including terminal statuses."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from clinic_ecosystem.presentation.http.appointment_admin import _calendar_aggregates


def test_calendar_aggregates_include_cancelled_and_tehran_days() -> None:
    day_a = datetime(2026, 11, 27, 8, 0, tzinfo=timezone.utc)  # Tehran afternoon
    day_b = datetime(2026, 11, 28, 8, 0, tzinfo=timezone.utc)
    rows = [
        {
            "appointment_id": uuid4(),
            "status": "CONFIRMED",
            "scheduled_start_at_utc": day_a,
            "service_id": uuid4(),
        },
        {
            "appointment_id": uuid4(),
            "status": "CANCELLED",
            "scheduled_start_at_utc": day_a,
            "service_id": uuid4(),
        },
        {
            "appointment_id": uuid4(),
            "status": "COMPLETED",
            "scheduled_start_at_utc": day_b,
            "service_id": uuid4(),
        },
        {
            "appointment_id": uuid4(),
            "status": "NO_SHOW",
            "scheduled_start_at_utc": day_b,
            "service_id": uuid4(),
        },
    ]
    agg = _calendar_aggregates(rows)
    assert agg["total"] == 4
    assert agg["cancelled_count"] == 1
    assert agg["completed_count"] == 1
    assert agg["no_show_count"] == 1
    assert agg["by_status"]["CONFIRMED"] == 1
    assert len(agg["by_day"]) == 2
    assert sum(d["count"] for d in agg["by_day"]) == 4


def test_calendar_aggregates_empty() -> None:
    agg = _calendar_aggregates([])
    assert agg["total"] == 0
    assert agg["by_day"] == []
    assert agg["cancelled_count"] == 0

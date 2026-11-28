"""Calendar period aggregates — scope-aware totals including terminal statuses."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from clinic_ecosystem.presentation.http.appointment_admin import (
    build_calendar_aggregates,
    infer_calendar_period,
)
from clinic_ecosystem.presentation.http.scope_access import filter_rows_by_scope
from clinic_ecosystem.infrastructure.persistence.permissions import PermissionScope


def _row(*, status: str, start: datetime, service_id):
    return {
        "appointment_id": uuid4(),
        "status": status,
        "scheduled_start_at_utc": start,
        "service_id": service_id,
    }


def test_infer_calendar_period_buckets() -> None:
    start = datetime(2026, 11, 27, 0, 30, tzinfo=timezone.utc)
    assert infer_calendar_period(start, start + timedelta(hours=24)) == "day"
    assert infer_calendar_period(start, start + timedelta(days=7)) == "week"
    assert infer_calendar_period(start, start + timedelta(days=31)) == "month"
    assert infer_calendar_period(start, start + timedelta(days=60)) == "custom"


def test_calendar_aggregates_include_cancelled_and_tehran_days() -> None:
    day_a = datetime(2026, 11, 27, 8, 0, tzinfo=timezone.utc)
    day_b = datetime(2026, 11, 28, 8, 0, tzinfo=timezone.utc)
    svc = uuid4()
    rows = [
        _row(status="CONFIRMED", start=day_a, service_id=svc),
        _row(status="CANCELLED", start=day_a, service_id=svc),
        _row(status="COMPLETED", start=day_b, service_id=svc),
        _row(status="NO_SHOW", start=day_b, service_id=svc),
    ]
    agg = build_calendar_aggregates(rows, period="week")
    assert agg["period"] == "week"
    assert agg["total"] == 4
    assert agg["cancelled_count"] == 1
    assert agg["completed_count"] == 1
    assert agg["no_show_count"] == 1
    assert agg["by_status"]["CONFIRMED"] == 1
    assert len(agg["by_day"]) == 2
    assert sum(d["count"] for d in agg["by_day"]) == 4


def test_aggregates_match_filtered_items_under_service_scope() -> None:
    svc_a, svc_b = uuid4(), uuid4()
    start = datetime(2026, 11, 27, 9, 0, tzinfo=timezone.utc)
    rows = [
        _row(status="CONFIRMED", start=start, service_id=svc_a),
        _row(status="CANCELLED", start=start, service_id=svc_a),
        _row(status="CHECKED_IN", start=start, service_id=svc_b),
        _row(status="COMPLETED", start=start, service_id=svc_b),
    ]
    scopes = [
        PermissionScope(
            permission_code="BETA01B_APPOINTMENTS_LIST",
            scope_mode="FILTER",
            department_id=None,
            service_id=svc_a,
            provider_resource_id=None,
        )
    ]
    scoped = filter_rows_by_scope(scopes, rows)
    assert len(scoped) == 2
    assert {r["service_id"] for r in scoped} == {svc_a}
    agg = build_calendar_aggregates(scoped, period="day")
    assert agg["total"] == len(scoped)
    assert agg["total"] == sum(agg["by_status"].values())
    assert agg["by_status"].get("CHECKED_IN", 0) == 0
    assert agg["cancelled_count"] == 1
    assert sum(d["count"] for d in agg["by_day"]) == agg["total"]


def test_calendar_aggregates_empty() -> None:
    agg = build_calendar_aggregates([], period="day")
    assert agg["total"] == 0
    assert agg["by_day"] == []
    assert agg["cancelled_count"] == 0
    assert agg["period"] == "day"

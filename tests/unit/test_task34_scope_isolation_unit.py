"""Unit-level adversarial scope isolation for Task 34 R2 SEC-01.

Full HTTP PG15 coverage lives in scripts/validate_task34_scope_isolation.py.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from clinic_ecosystem.infrastructure.persistence.permissions import (
    PermissionScope,
    SqlPermissionService,
)
from clinic_ecosystem.presentation.http.appointment_admin import build_calendar_aggregates
from clinic_ecosystem.presentation.http.scope_access import (
    filter_rows_by_scope,
    require_object_scope,
    scope_service_ids,
)
import pytest
from fastapi import HTTPException


def _filter_service(service_id) -> PermissionScope:
    return PermissionScope(
        permission_code="BETA01B_APPOINTMENTS_LIST",
        scope_mode="FILTER",
        department_id=None,
        service_id=service_id,
        provider_resource_id=None,
    )


def test_disjoint_filter_scopes_isolate_rows_and_counts() -> None:
    svc_a, svc_b = uuid4(), uuid4()
    start = datetime(2026, 11, 27, 10, 0, tzinfo=timezone.utc)
    rows = [
        {
            "appointment_id": uuid4(),
            "service_id": svc_a,
            "status": "CONFIRMED",
            "scheduled_start_at_utc": start,
        },
        {
            "appointment_id": uuid4(),
            "service_id": svc_a,
            "status": "CANCELLED",
            "scheduled_start_at_utc": start + timedelta(hours=1),
        },
        {
            "appointment_id": uuid4(),
            "service_id": svc_b,
            "status": "CHECKED_IN",
            "scheduled_start_at_utc": start,
        },
        {
            "appointment_id": uuid4(),
            "service_id": svc_b,
            "status": "COMPLETED",
            "scheduled_start_at_utc": start + timedelta(hours=2),
        },
    ]
    scopes_a = [_filter_service(svc_a)]
    scopes_b = [_filter_service(svc_b)]
    a_rows = filter_rows_by_scope(scopes_a, rows)
    b_rows = filter_rows_by_scope(scopes_b, rows)
    assert {r["service_id"] for r in a_rows} == {svc_a}
    assert {r["service_id"] for r in b_rows} == {svc_b}
    assert not set(r["appointment_id"] for r in a_rows) & set(
        r["appointment_id"] for r in b_rows
    )
    agg_a = build_calendar_aggregates(a_rows, period="day")
    agg_b = build_calendar_aggregates(b_rows, period="day")
    assert agg_a["total"] == 2 and agg_b["total"] == 2
    assert agg_a["total"] == len(a_rows)
    assert agg_b["by_status"].get("CHECKED_IN") == 1
    assert agg_a["by_status"].get("CHECKED_IN", 0) == 0
    # Pagination after scope: page of 1 from scoped A never leaks B.
    page = a_rows[0:1]
    assert page[0]["service_id"] == svc_a
    assert scope_service_ids(scopes_a) == {svc_a}
    assert scope_service_ids(scopes_b) == {svc_b}


def test_direct_id_access_fail_closed_for_other_scope() -> None:
    svc_a, svc_b = uuid4(), uuid4()
    scopes_a = [_filter_service(svc_a)]
    with pytest.raises(HTTPException) as exc:
        require_object_scope(scopes_a, service_id=svc_b)
    assert exc.value.status_code == 403
    require_object_scope(scopes_a, service_id=svc_a)  # does not raise


def test_empty_scopes_deny_list_and_object() -> None:
    svc = SqlPermissionService(session=None)  # type: ignore[arg-type]
    assert svc.allows([], service_id=uuid4()) is False
    assert filter_rows_by_scope([], [{"service_id": uuid4()}]) == []
    assert scope_service_ids([]) == set()

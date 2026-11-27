"""Appointment calendar, list, upcoming and lifecycle HTTP routes (Workstream D)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response, status
from pydantic import BaseModel, Field

from clinic_ecosystem.application.appointment_admin.service import AppointmentLifecycleService
from clinic_ecosystem.application.shared.errors import NotFound, ValidationFailed
from clinic_ecosystem.application.shared.idempotent import run_idempotent, validate_key
from clinic_ecosystem.application.shared.preconditions import parse_if_match
from clinic_ecosystem.domain.access import permissions as perm
from clinic_ecosystem.infrastructure.persistence.appointment_admin import SqlAppointmentAdmin
from clinic_ecosystem.infrastructure.persistence.uow import SqlAlchemyUnitOfWork
from clinic_ecosystem.presentation.http.common import actor_of, load_granted, require, set_etag
from clinic_ecosystem.presentation.http.dependencies import (
    AuthenticatedPrincipal,
    get_authenticated_principal,
    get_uow,
)
from clinic_ecosystem.presentation.http.scope_access import (
    filter_rows_by_scope,
    load_scopes,
    require_object_scope,
    scope_service_ids,
)

router = APIRouter(prefix="/api/v1/appointments", tags=["appointment-admin"])
Principal = Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)]
Uow = Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)]

MAX_CALENDAR_DAYS = 42
CALENDAR_STATUSES = (
    "PENDING_PAYMENT_HOLD", "CONFIRMED", "CHECKED_IN", "COMPLETED",
    "CANCELLED", "EXPIRED_HOLD", "NO_SHOW",
)
SORT_OPTIONS = ("time", "patient", "service")


class CancelBody(BaseModel):
    reason: str | None = Field(default=None, max_length=200)


class RescheduleBody(BaseModel):
    start_at_utc: datetime
    end_at_utc: datetime
    acknowledge_overlap: bool = False
    acknowledged_conflict_ids: list[UUID] = Field(default_factory=list, max_length=50)


def _aware_utc(value: datetime, field: str) -> datetime:
    if value.tzinfo is None:
        raise ValidationFailed(f"{field} must include a timezone offset", code="invalid_datetime")
    return value.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _item(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "appointment_id": str(r["appointment_id"]),
        "patient_profile_id": str(r["patient_profile_id"]),
        "patient_first_name": r["patient_first_name"],
        "patient_last_name": r["patient_last_name"],
        "service_id": str(r["service_id"]),
        "service_name": r["service_name"],
        "status": r["status"],
        "booking_channel": r["booking_channel"],
        "capacity_pool": r["capacity_pool"],
        "scheduled_start_at_utc": _iso(r["scheduled_start_at_utc"]),
        "scheduled_end_at_utc": _iso(r["scheduled_end_at_utc"]),
        "resource_names": list(r["resource_names"]),
        "aggregate_version": int(r["aggregate_version"]),
    }


def _parse_range(start_at_utc: datetime, end_at_utc: datetime) -> tuple[datetime, datetime]:
    start = _aware_utc(start_at_utc, "start_at_utc")
    end = _aware_utc(end_at_utc, "end_at_utc")
    if end <= start:
        raise ValidationFailed("end_at_utc must be after start_at_utc", code="invalid_time_range")
    if (end - start).days > MAX_CALENDAR_DAYS:
        raise ValidationFailed(
            f"Calendar range must be at most {MAX_CALENDAR_DAYS} days", code="range_too_large"
        )
    return start, end


@router.get("/calendar")
async def calendar(
    principal: Principal,
    uow: Uow,
    start_at_utc: Annotated[datetime, Query()],
    end_at_utc: Annotated[datetime, Query()],
    service_id: UUID | None = None,
    resource_id: UUID | None = None,
    patient_profile_id: UUID | None = None,
    status_filter: Annotated[str | None, Query(alias="status", max_length=32)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 300,
) -> dict:
    require(await load_granted(principal, uow), perm.APPOINTMENTS_LIST)
    scopes = await load_scopes(principal, uow, perm.APPOINTMENTS_LIST)
    if not scopes:
        return {"items": [], "truncated": False, "limit": limit}
    allowed_services = scope_service_ids(scopes)
    if allowed_services is not None and len(allowed_services) == 0:
        return {"items": [], "truncated": False, "limit": limit}
    if service_id is not None and allowed_services is not None and service_id not in allowed_services:
        return {"items": [], "truncated": False, "limit": limit}
    start, end = _parse_range(start_at_utc, end_at_utc)
    if status_filter and status_filter not in CALENDAR_STATUSES:
        raise ValidationFailed("Unknown status filter", code="invalid_status")
    rows = await SqlAppointmentAdmin(uow.session).list_calendar(
        tenant_id=principal.claims.tenant_id,
        start_at_utc=start, end_at_utc=end,
        service_id=service_id, resource_id=resource_id,
        status=status_filter, patient_profile_id=patient_profile_id,
        limit=min(2000, (limit + 1) * 4),
    )
    scoped = filter_rows_by_scope(scopes, [dict(r) for r in rows])
    truncated = len(scoped) > limit
    return {"items": [_item(r) for r in scoped[:limit]], "truncated": truncated, "limit": limit}


@router.get("/management")
async def management_list(
    principal: Principal,
    uow: Uow,
    start_at_utc: Annotated[datetime, Query()],
    end_at_utc: Annotated[datetime, Query()],
    service_id: UUID | None = None,
    resource_id: UUID | None = None,
    patient_profile_id: UUID | None = None,
    status_filter: Annotated[str | None, Query(alias="status", max_length=32)] = None,
    q: Annotated[str | None, Query(max_length=120)] = None,
    sort: Annotated[str, Query(max_length=16)] = "time",
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
) -> dict:
    require(await load_granted(principal, uow), perm.APPOINTMENTS_LIST)
    scopes = await load_scopes(principal, uow, perm.APPOINTMENTS_LIST)
    if not scopes:
        return {"items": [], "total": 0, "limit": limit, "offset": offset, "truncated": False}
    start, end = _parse_range(start_at_utc, end_at_utc)
    if status_filter and status_filter not in CALENDAR_STATUSES:
        raise ValidationFailed("Unknown status filter", code="invalid_status")
    if sort not in SORT_OPTIONS:
        raise ValidationFailed("Unknown sort", code="invalid_sort")
    term = (q or "").strip() or None
    admin = SqlAppointmentAdmin(uow.session)
    tenant_id = principal.claims.tenant_id
    # Scope before pagination: fetch bounded window, filter, then slice.
    fetch_limit = min(2000, max(limit + offset, limit) * 4)
    rows = await admin.list_calendar(
        tenant_id=tenant_id, start_at_utc=start, end_at_utc=end,
        service_id=service_id, resource_id=resource_id, status=status_filter,
        patient_profile_id=patient_profile_id, q=term, sort=sort,
        limit=fetch_limit, offset=0,
    )
    scoped = filter_rows_by_scope(scopes, [dict(r) for r in rows])
    total = len(scoped)
    page = scoped[offset : offset + limit]
    return {
        "items": [_item(r) for r in page],
        "total": total,
        "limit": limit,
        "offset": offset,
        "truncated": (offset + len(page)) < total,
    }


@router.get("/upcoming")
async def upcoming(
    principal: Principal,
    uow: Uow,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    start_at_utc: Annotated[datetime | None, Query()] = None,
    end_at_utc: Annotated[datetime | None, Query()] = None,
) -> dict:
    require(await load_granted(principal, uow), perm.APPOINTMENTS_LIST)
    scopes = await load_scopes(principal, uow, perm.APPOINTMENTS_LIST)
    if not scopes:
        return {"items": [], "limit": limit}
    day_start = day_end = None
    if start_at_utc is not None or end_at_utc is not None:
        if start_at_utc is None or end_at_utc is None:
            raise ValidationFailed(
                "Both start_at_utc and end_at_utc are required for day bounds",
                code="invalid_time_range",
            )
        day_start, day_end = _parse_range(start_at_utc, end_at_utc)
    rows = await SqlAppointmentAdmin(uow.session).list_upcoming(
        tenant_id=principal.claims.tenant_id,
        now=datetime.now(timezone.utc),
        limit=min(500, limit * 4),
        day_start_at_utc=day_start,
        day_end_at_utc=day_end,
    )
    scoped = filter_rows_by_scope(scopes, [dict(r) for r in rows])
    return {"items": [_item(r) for r in scoped[:limit]], "limit": limit}


@router.get("/waiting-room")
async def waiting_room(
    principal: Principal,
    uow: Uow,
    start_at_utc: Annotated[datetime, Query()],
    end_at_utc: Annotated[datetime, Query()],
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
) -> dict:
    """Physical waiting room: CHECKED_IN appointments in the Tehran-day window (read model)."""
    require(await load_granted(principal, uow), perm.APPOINTMENTS_LIST)
    scopes = await load_scopes(principal, uow, perm.APPOINTMENTS_LIST)
    if not scopes:
        return {"items": [], "total": 0, "limit": limit, "offset": offset}
    start, end = _parse_range(start_at_utc, end_at_utc)
    admin = SqlAppointmentAdmin(uow.session)
    tenant_id = principal.claims.tenant_id
    fetch_limit = min(2000, max(limit + offset, limit) * 4)
    rows = await admin.list_calendar(
        tenant_id=tenant_id,
        start_at_utc=start,
        end_at_utc=end,
        status="CHECKED_IN",
        sort="time",
        limit=fetch_limit,
        offset=0,
    )
    scoped = filter_rows_by_scope(scopes, [dict(r) for r in rows])
    total = len(scoped)
    page = scoped[offset : offset + limit]
    return {
        "items": [_item(r) for r in page],
        "total": total,
        "limit": limit,
        "offset": offset,
        "truncated": (offset + len(page)) < total,
    }


@router.get("/{appointment_id}")
async def appointment_details(
    appointment_id: UUID, principal: Principal, uow: Uow, response: Response
) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.APPOINTMENTS_VIEW_DETAILS)
    scopes = await load_scopes(principal, uow, perm.APPOINTMENTS_VIEW_DETAILS)
    admin = SqlAppointmentAdmin(uow.session)
    tenant_id = principal.claims.tenant_id
    row = await admin.get_appointment(tenant_id=tenant_id, appointment_id=appointment_id)
    if row is None:
        raise NotFound("Appointment not found", code="appointment_not_found")
    require_object_scope(scopes, service_id=row.get("service_id"))
    allocations = await admin.get_allocations(tenant_id=tenant_id, appointment_id=appointment_id)
    set_etag(response, int(row["aggregate_version"]))
    manual = row["capacity_pool"] == "MANUAL"
    status_now = row["status"]
    return {
        "appointment_id": str(row["appointment_id"]),
        "patient_profile_id": str(row["patient_profile_id"]),
        "patient_first_name": row["patient_first_name"],
        "patient_last_name": row["patient_last_name"],
        "service_id": str(row["service_id"]),
        "service_name": row["service_name"],
        "status": status_now,
        "booking_channel": row["booking_channel"],
        "capacity_pool": row["capacity_pool"],
        "scheduled_start_at_utc": _iso(row["scheduled_start_at_utc"]),
        "scheduled_end_at_utc": _iso(row["scheduled_end_at_utc"]),
        "aggregate_version": int(row["aggregate_version"]),
        "created_at_utc": _iso(row["created_at_utc"]),
        "updated_at_utc": _iso(row["updated_at_utc"]),
        "allocations": [
            {
                "resource_id": str(a["resource_id"]),
                "resource_name": a["resource_name"],
                "resource_type": a["resource_type"],
                "allocation_status": a["allocation_status"],
            }
            for a in allocations
        ],
        "can_cancel": manual and status_now in {"CONFIRMED", "CHECKED_IN"}
            and perm.APPOINTMENTS_CANCEL in granted,
        "can_reschedule": manual and status_now == "CONFIRMED"
            and perm.APPOINTMENTS_RESCHEDULE in granted,
        "can_check_in": manual and status_now == "CONFIRMED"
            and perm.APPOINTMENTS_CHECK_IN in granted,
        "can_complete": manual and status_now == "CHECKED_IN"
            and perm.APPOINTMENTS_COMPLETE in granted,
        "can_mark_no_show": manual and status_now == "CONFIRMED"
            and perm.APPOINTMENTS_MARK_NO_SHOW in granted,
    }


async def _idempotent_lifecycle(
    *,
    uow: Uow,
    principal: Principal,
    response: Response,
    appointment_id: UUID,
    if_match: str | None,
    idempotency_key: str | None,
    permission: str,
    scope: str,
    action,
) -> dict:
    require(await load_granted(principal, uow), permission)
    expected = parse_if_match(if_match)
    key = validate_key(idempotency_key)
    actor = actor_of(principal)
    result, replayed = await run_idempotent(
        uow,
        tenant_id=actor.tenant_id,
        principal_id=actor.account_id,
        scope=scope,
        key=key,
        request_payload={"expected_version": expected},
        action=lambda: action(actor, expected),
    )
    if replayed:
        response.headers["Idempotent-Replay"] = "true"
    set_etag(response, int(result["aggregate_version"]))
    return result


@router.post("/{appointment_id}/cancel")
async def cancel_appointment(
    appointment_id: UUID,
    body: CancelBody,
    principal: Principal,
    uow: Uow,
    response: Response,
    if_match: Annotated[str | None, Header()] = None,
    idempotency_key: Annotated[str | None, Header()] = None,
) -> dict:
    require(await load_granted(principal, uow), perm.APPOINTMENTS_CANCEL)
    expected = parse_if_match(if_match)
    key = validate_key(idempotency_key)
    actor = actor_of(principal)
    service = AppointmentLifecycleService(uow)
    result, replayed = await run_idempotent(
        uow,
        tenant_id=actor.tenant_id,
        principal_id=actor.account_id,
        scope=f"appointment.cancel:{appointment_id}",
        key=key,
        request_payload={"expected_version": expected, "reason": (body.reason or "").strip()},
        action=lambda: service.cancel(actor, appointment_id, expected, body.reason),
    )
    if replayed:
        response.headers["Idempotent-Replay"] = "true"
    set_etag(response, int(result["aggregate_version"]))
    return result


@router.post("/{appointment_id}/check-in")
async def check_in_appointment(
    appointment_id: UUID,
    principal: Principal,
    uow: Uow,
    response: Response,
    if_match: Annotated[str | None, Header()] = None,
    idempotency_key: Annotated[str | None, Header()] = None,
) -> dict:
    service = AppointmentLifecycleService(uow)
    return await _idempotent_lifecycle(
        uow=uow, principal=principal, response=response,
        appointment_id=appointment_id, if_match=if_match,
        idempotency_key=idempotency_key, permission=perm.APPOINTMENTS_CHECK_IN,
        scope=f"appointment.check_in:{appointment_id}",
        action=lambda actor, expected: service.check_in(actor, appointment_id, expected),
    )


@router.post("/{appointment_id}/complete")
async def complete_appointment(
    appointment_id: UUID,
    principal: Principal,
    uow: Uow,
    response: Response,
    if_match: Annotated[str | None, Header()] = None,
    idempotency_key: Annotated[str | None, Header()] = None,
) -> dict:
    service = AppointmentLifecycleService(uow)
    return await _idempotent_lifecycle(
        uow=uow, principal=principal, response=response,
        appointment_id=appointment_id, if_match=if_match,
        idempotency_key=idempotency_key, permission=perm.APPOINTMENTS_COMPLETE,
        scope=f"appointment.complete:{appointment_id}",
        action=lambda actor, expected: service.complete(actor, appointment_id, expected),
    )


@router.post("/{appointment_id}/no-show")
async def no_show_appointment(
    appointment_id: UUID,
    principal: Principal,
    uow: Uow,
    response: Response,
    if_match: Annotated[str | None, Header()] = None,
    idempotency_key: Annotated[str | None, Header()] = None,
) -> dict:
    service = AppointmentLifecycleService(uow)
    return await _idempotent_lifecycle(
        uow=uow, principal=principal, response=response,
        appointment_id=appointment_id, if_match=if_match,
        idempotency_key=idempotency_key, permission=perm.APPOINTMENTS_MARK_NO_SHOW,
        scope=f"appointment.no_show:{appointment_id}",
        action=lambda actor, expected: service.mark_no_show(actor, appointment_id, expected),
    )


@router.post("/{appointment_id}/reschedule", status_code=status.HTTP_200_OK)
async def reschedule_appointment(
    appointment_id: UUID,
    body: RescheduleBody,
    principal: Principal,
    uow: Uow,
    response: Response,
    if_match: Annotated[str | None, Header()] = None,
    idempotency_key: Annotated[str | None, Header()] = None,
) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.APPOINTMENTS_RESCHEDULE)
    expected = parse_if_match(if_match)
    key = validate_key(idempotency_key)
    start = _aware_utc(body.start_at_utc, "start_at_utc")
    end = _aware_utc(body.end_at_utc, "end_at_utc")
    actor = actor_of(principal)
    service = AppointmentLifecycleService(uow)
    result, replayed = await run_idempotent(
        uow,
        tenant_id=actor.tenant_id,
        principal_id=actor.account_id,
        scope=f"appointment.reschedule:{appointment_id}",
        key=key,
        request_payload={
            "expected_version": expected,
            "start_at_utc": _iso(start),
            "end_at_utc": _iso(end),
            "acknowledge_overlap": body.acknowledge_overlap,
            "acknowledged_conflict_ids": sorted(str(i) for i in body.acknowledged_conflict_ids),
        },
        action=lambda: service.reschedule(
            actor, granted, appointment_id, expected, start, end,
            body.acknowledge_overlap, body.acknowledged_conflict_ids,
        ),
    )
    if replayed:
        response.headers["Idempotent-Replay"] = "true"
    set_etag(response, int(result["aggregate_version"]))
    return result

"""Appointment calendar, details and lifecycle HTTP routes (Workstream D)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
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

router = APIRouter(prefix="/api/v1/appointments", tags=["appointment-admin"])
Principal = Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)]
Uow = Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)]

MAX_CALENDAR_DAYS = 42
CALENDAR_STATUSES = (
    "PENDING_PAYMENT_HOLD", "CONFIRMED", "CHECKED_IN", "COMPLETED",
    "CANCELLED", "EXPIRED_HOLD", "NO_SHOW",
)


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
    start = _aware_utc(start_at_utc, "start_at_utc")
    end = _aware_utc(end_at_utc, "end_at_utc")
    if end <= start:
        raise ValidationFailed("end_at_utc must be after start_at_utc", code="invalid_time_range")
    if (end - start).days > MAX_CALENDAR_DAYS:
        raise ValidationFailed(
            f"Calendar range must be at most {MAX_CALENDAR_DAYS} days", code="range_too_large"
        )
    if status_filter and status_filter not in CALENDAR_STATUSES:
        raise ValidationFailed("Unknown status filter", code="invalid_status")
    rows = await SqlAppointmentAdmin(uow.session).list_calendar(
        tenant_id=principal.claims.tenant_id,
        start_at_utc=start,
        end_at_utc=end,
        service_id=service_id,
        resource_id=resource_id,
        status=status_filter,
        patient_profile_id=patient_profile_id,
        limit=limit + 1,
    )
    truncated = len(rows) > limit
    return {
        "items": [
            {
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
            for r in rows[:limit]
        ],
        "truncated": truncated,
        "limit": limit,
    }


@router.get("/{appointment_id}")
async def appointment_details(
    appointment_id: UUID, principal: Principal, uow: Uow, response: Response
) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.APPOINTMENTS_VIEW_DETAILS)
    admin = SqlAppointmentAdmin(uow.session)
    tenant_id = principal.claims.tenant_id
    row = await admin.get_appointment(tenant_id=tenant_id, appointment_id=appointment_id)
    if row is None:
        raise NotFound("Appointment not found", code="appointment_not_found")
    allocations = await admin.get_allocations(tenant_id=tenant_id, appointment_id=appointment_id)
    set_etag(response, int(row["aggregate_version"]))
    can_mutate = row["capacity_pool"] == "MANUAL" and row["status"] == "CONFIRMED"
    return {
        "appointment_id": str(row["appointment_id"]),
        "patient_profile_id": str(row["patient_profile_id"]),
        "patient_first_name": row["patient_first_name"],
        "patient_last_name": row["patient_last_name"],
        "service_id": str(row["service_id"]),
        "service_name": row["service_name"],
        "status": row["status"],
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
        "can_cancel": can_mutate and perm.APPOINTMENTS_CANCEL in granted,
        "can_reschedule": can_mutate and perm.APPOINTMENTS_RESCHEDULE in granted,
    }


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

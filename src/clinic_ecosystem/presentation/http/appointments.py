"""Manual appointment scheduling, group booking, day listing, waiting room."""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Annotated, Any
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from clinic_ecosystem.application.scheduling.exceptions import (
    GroupManualOverlapAcknowledgementRequired,
    IdempotencyConflict,
    IdempotencyInProgress,
    ManualOverlapAcknowledgementRequired,
    ServiceRequirementsNotMet,
    UnauthorizedScheduling,
)
from clinic_ecosystem.domain.scheduling.exceptions import (
    CapacityConflictException,
    InvalidAppointmentSchedule,
)
from clinic_ecosystem.infrastructure.auth.settings import (
    APPOINTMENTS_LIST,
    APPOINTMENTS_SCHEDULE_MANUAL,
)
from clinic_ecosystem.infrastructure.persistence.appointment_queries import (
    SqlAppointmentQueryRepository,
)
from clinic_ecosystem.infrastructure.persistence.compose import build_handler_for_session
from clinic_ecosystem.infrastructure.persistence.patients import SqlPatientRepository
from clinic_ecosystem.infrastructure.persistence.uow import SqlAlchemyUnitOfWork
from clinic_ecosystem.presentation.http.dependencies import (
    AuthenticatedPrincipal,
    get_authenticated_principal,
    get_engine,
    get_uow,
    require_permission,
)
from clinic_ecosystem.presentation.http.schedule_validation import (
    validate_schedule_catalog,
)
from clinic_ecosystem.presentation.scheduling import (
    command_from_api_payload,
    group_command_from_api_payload,
    serialize_group_manual_conflict_response,
    serialize_manual_conflict_response,
)
from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7

router = APIRouter(prefix="/api/v1/appointments", tags=["appointments"])
TEHRAN_TZ = ZoneInfo("Asia/Tehran")


class ScheduleAppointmentRequest(BaseModel):
    beneficiary_patient_id: UUID
    service_id: UUID
    resource_ids: list[UUID] = Field(min_length=1, max_length=20)
    start_at_utc: datetime
    end_at_utc: datetime
    patient_booking_note: str | None = Field(default=None, max_length=2000)
    acknowledge_overlap: bool = False
    acknowledged_conflict_ids: list[UUID] = Field(default_factory=list)
    # Reception workflow is fixed to MANUAL_STAFF / MANUAL — not client-overridable.
    booking_channel: str = "MANUAL_STAFF"
    capacity_pool: str = "MANUAL"
    immediate_check_in: bool = False


class ScheduleAppointmentResponse(BaseModel):
    appointment_id: str
    replayed: bool
    status: str | None = None


class GroupScheduleLineRequest(BaseModel):
    client_line_id: str = Field(min_length=1, max_length=128)
    service_id: UUID
    resource_ids: list[UUID] = Field(min_length=1, max_length=20)
    start_at_utc: datetime
    end_at_utc: datetime
    patient_booking_note: str | None = Field(default=None, max_length=2000)
    acknowledge_overlap: bool = False
    acknowledged_conflict_ids: list[UUID] = Field(default_factory=list)


class GroupScheduleRequest(BaseModel):
    beneficiary_patient_id: UUID
    lines: list[GroupScheduleLineRequest] = Field(min_length=1, max_length=20)
    immediate_check_in: bool = False
    booking_channel: str = "MANUAL_STAFF"
    capacity_pool: str = "MANUAL"


class GroupScheduleLineResponse(BaseModel):
    client_line_id: str
    appointment_id: str
    status: str


class GroupScheduleResponse(BaseModel):
    lines: list[GroupScheduleLineResponse]
    replayed: bool


class AppointmentListItemResponse(BaseModel):
    appointment_id: str
    patient_profile_id: str
    patient_first_name: str
    patient_last_name: str
    service_id: str
    service_name: str
    status: str
    booking_channel: str
    capacity_pool: str
    scheduled_start_at_utc: datetime
    scheduled_end_at_utc: datetime


class AppointmentListResponse(BaseModel):
    items: list[AppointmentListItemResponse]


def _ensure_aware_utc(value: datetime, *, field: str) -> datetime:
    if value.tzinfo is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_datetime",
                "message": f"{field} must include a timezone offset (prefer UTC)",
            },
        )
    return value.astimezone(timezone.utc)


def _tehran_day_bounds(day: date) -> tuple[datetime, datetime]:
    start_local = datetime.combine(day, time.min, tzinfo=TEHRAN_TZ)
    end_local = datetime.combine(day, time.min, tzinfo=TEHRAN_TZ)
    # Exclusive end = next calendar day 00:00 Tehran.
    from datetime import timedelta

    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def _raise_schedule_http(exc: BaseException) -> None:
    if isinstance(exc, ManualOverlapAcknowledgementRequired):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=serialize_manual_conflict_response(exc),
        ) from None
    if isinstance(exc, GroupManualOverlapAcknowledgementRequired):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=serialize_group_manual_conflict_response(exc),
        ) from None
    if isinstance(exc, UnauthorizedScheduling):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "permission_denied",
                "message": "Required scheduling permission is missing for this principal",
            },
        ) from None
    if isinstance(exc, IdempotencyConflict):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "idempotency_conflict",
                "message": "Idempotency key reused with a different request fingerprint",
            },
        ) from None
    if isinstance(exc, IdempotencyInProgress):
        raise HTTPException(
            status_code=status.HTTP_425_TOO_EARLY,
            detail={
                "error": "idempotency_in_progress",
                "message": "A matching request is still in progress",
            },
        ) from None
    if isinstance(exc, CapacityConflictException):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "capacity_conflict", "message": str(exc)},
        ) from None
    if isinstance(exc, ServiceRequirementsNotMet):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_resources", "message": str(exc)},
        ) from None
    if isinstance(exc, InvalidAppointmentSchedule):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_appointment", "message": str(exc)},
        ) from None
    raise exc


def _validate_idempotency_key(idempotency_key: str) -> str:
    key = idempotency_key.strip()
    if not key or len(key) > 128:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_idempotency_key",
                "message": "Idempotency-Key is required (1..128 characters)",
            },
        )
    return key


def _list_item_response(item: Any) -> AppointmentListItemResponse:
    return AppointmentListItemResponse(
        appointment_id=str(item.appointment_id),
        patient_profile_id=str(item.patient_profile_id),
        patient_first_name=item.patient_first_name,
        patient_last_name=item.patient_last_name,
        service_id=str(item.service_id),
        service_name=item.service_name,
        status=item.status,
        booking_channel=item.booking_channel,
        capacity_pool=item.capacity_pool,
        scheduled_start_at_utc=item.scheduled_start_at_utc,
        scheduled_end_at_utc=item.scheduled_end_at_utc,
    )


@router.post("/group", response_model=GroupScheduleResponse)
async def schedule_appointment_group(
    body: GroupScheduleRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    engine: Annotated[AsyncEngine, Depends(get_engine)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> GroupScheduleResponse:
    """Atomically schedule multiple MANUAL lines under one group Idempotency-Key."""
    await require_permission(
        APPOINTMENTS_SCHEDULE_MANUAL, principal=principal, uow=uow
    )
    if body.booking_channel != "MANUAL_STAFF" or body.capacity_pool != "MANUAL":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_booking_mode",
                "message": "Reception group scheduling requires MANUAL_STAFF / MANUAL",
            },
        )
    key = _validate_idempotency_key(idempotency_key)
    seen_line_ids: set[str] = set()
    for line in body.lines:
        if line.client_line_id in seen_line_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "duplicate_client_line_id",
                    "message": f"Duplicate client_line_id: {line.client_line_id}",
                },
            )
        seen_line_ids.add(line.client_line_id)
        start = _ensure_aware_utc(line.start_at_utc, field="start_at_utc")
        end = _ensure_aware_utc(line.end_at_utc, field="end_at_utc")
        if end <= start:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "invalid_time_range",
                    "message": "end_at_utc must be after start_at_utc",
                },
            )
        line.start_at_utc = start
        line.end_at_utc = end

    patients = SqlPatientRepository(uow.session)
    patient = await patients.get_by_profile_id(
        tenant_id=principal.claims.tenant_id,
        patient_profile_id=body.beneficiary_patient_id,
    )
    if patient is None or not patient.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "patient_not_found", "message": "Patient not found"},
        )

    for line in body.lines:
        await validate_schedule_catalog(
            uow=uow,
            tenant_id=principal.claims.tenant_id,
            service_id=line.service_id,
            resource_ids=list(line.resource_ids),
        )

    payload = {
        "beneficiary_patient_id": str(body.beneficiary_patient_id),
        "booker_person_id": str(principal.account.person_id),
        "booking_channel": "MANUAL_STAFF",
        "capacity_pool": "MANUAL",
        "immediate_check_in": body.immediate_check_in,
        "lines": [
            {
                "client_line_id": line.client_line_id,
                "service_id": str(line.service_id),
                "resource_ids": [str(rid) for rid in line.resource_ids],
                "start_at_utc": line.start_at_utc.isoformat(),
                "end_at_utc": line.end_at_utc.isoformat(),
                "acknowledge_overlap": line.acknowledge_overlap,
                "acknowledged_conflict_ids": [
                    str(cid) for cid in line.acknowledged_conflict_ids
                ],
                "patient_booking_note": line.patient_booking_note,
            }
            for line in body.lines
        ],
    }
    command = group_command_from_api_payload(
        verified_tenant_id=principal.claims.tenant_id,
        verified_principal_id=principal.claims.principal_id,
        actor_type="USER",
        payload=payload,
        idempotency_key=key,
        correlation_id=new_uuid7(),
    )

    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    session = factory()
    try:
        handler = build_handler_for_session(session)
        result = await handler.handle_group(command)
    except Exception as exc:  # noqa: BLE001
        _raise_schedule_http(exc)
        raise  # pragma: no cover
    finally:
        await session.close()

    return GroupScheduleResponse(
        lines=[
            GroupScheduleLineResponse(
                client_line_id=line.client_line_id,
                appointment_id=str(line.appointment_id),
                status=line.status,
            )
            for line in result.lines
        ],
        replayed=result.replayed,
    )


@router.get("/waiting-room", response_model=AppointmentListResponse)
async def list_waiting_room(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    date_ymd: Annotated[str, Query(alias="date", pattern=r"^\d{4}-\d{2}-\d{2}$")],
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
) -> AppointmentListResponse:
    """CHECKED_IN appointments for a Tehran calendar day (physical waiting room)."""
    await require_permission(APPOINTMENTS_LIST, principal=principal, uow=uow)
    try:
        day = date.fromisoformat(date_ymd)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_date", "message": "date must be YYYY-MM-DD"},
        ) from exc
    start, end = _tehran_day_bounds(day)
    repo = SqlAppointmentQueryRepository(uow.session)
    rows = await repo.list_waiting_room(
        tenant_id=principal.claims.tenant_id,
        start_at_utc=start,
        end_at_utc=end,
        limit=limit,
    )
    return AppointmentListResponse(items=[_list_item_response(item) for item in rows])


@router.post("", response_model=ScheduleAppointmentResponse)
async def schedule_appointment(
    body: ScheduleAppointmentRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    engine: Annotated[AsyncEngine, Depends(get_engine)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> ScheduleAppointmentResponse:
    """Schedule a MANUAL_STAFF appointment via the existing ScheduleAppointmentHandler.

    Uses a request-scoped session (build_handler_for_session) so concurrent requests
    never share mutable holder/proxy scheduling state.
    """
    await require_permission(
        APPOINTMENTS_SCHEDULE_MANUAL, principal=principal, uow=uow
    )

    if body.booking_channel != "MANUAL_STAFF" or body.capacity_pool != "MANUAL":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_booking_mode",
                "message": "Reception scheduling requires MANUAL_STAFF / MANUAL",
            },
        )

    key = _validate_idempotency_key(idempotency_key)

    start = _ensure_aware_utc(body.start_at_utc, field="start_at_utc")
    end = _ensure_aware_utc(body.end_at_utc, field="end_at_utc")
    if end <= start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_time_range",
                "message": "end_at_utc must be after start_at_utc",
            },
        )

    patients = SqlPatientRepository(uow.session)
    patient = await patients.get_by_profile_id(
        tenant_id=principal.claims.tenant_id,
        patient_profile_id=body.beneficiary_patient_id,
    )
    if patient is None or not patient.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "patient_not_found", "message": "Patient not found"},
        )

    await validate_schedule_catalog(
        uow=uow,
        tenant_id=principal.claims.tenant_id,
        service_id=body.service_id,
        resource_ids=list(body.resource_ids),
    )

    payload = {
        "beneficiary_patient_id": str(body.beneficiary_patient_id),
        "service_id": str(body.service_id),
        "resource_ids": [str(rid) for rid in body.resource_ids],
        "booking_channel": "MANUAL_STAFF",
        "capacity_pool": "MANUAL",
        "start_at_utc": start.isoformat(),
        "end_at_utc": end.isoformat(),
        "acknowledge_overlap": body.acknowledge_overlap,
        "acknowledged_conflict_ids": [
            str(cid) for cid in body.acknowledged_conflict_ids
        ],
        "patient_booking_note": body.patient_booking_note,
        "booker_person_id": str(principal.account.person_id),
        "immediate_check_in": body.immediate_check_in,
    }
    command = command_from_api_payload(
        verified_tenant_id=principal.claims.tenant_id,
        verified_principal_id=principal.claims.principal_id,
        actor_type="USER",
        payload=payload,
        idempotency_key=key,
        correlation_id=new_uuid7(),
    )

    # Separate transactional unit owned by the scheduling handler (existing design).
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    session = factory()
    try:
        handler = build_handler_for_session(session)
        result = await handler.handle(command)
    except Exception as exc:  # noqa: BLE001
        _raise_schedule_http(exc)
        raise  # pragma: no cover
    finally:
        await session.close()

    return ScheduleAppointmentResponse(
        appointment_id=str(result.appointment_id),
        replayed=result.replayed,
        status=result.status,
    )


@router.get("", response_model=AppointmentListResponse)
async def list_appointments(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    start_at_utc: Annotated[datetime, Query()],
    end_at_utc: Annotated[datetime, Query()],
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
) -> AppointmentListResponse:
    await require_permission(APPOINTMENTS_LIST, principal=principal, uow=uow)
    start = _ensure_aware_utc(start_at_utc, field="start_at_utc")
    end = _ensure_aware_utc(end_at_utc, field="end_at_utc")
    if end <= start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_time_range",
                "message": "end_at_utc must be after start_at_utc",
            },
        )
    # Bound day-range queries (max 7 days) for reception listing.
    if (end - start).total_seconds() > 7 * 24 * 3600:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "range_too_large",
                "message": "Appointment listing range must be at most 7 days",
            },
        )
    repo = SqlAppointmentQueryRepository(uow.session)
    rows = await repo.list_in_range(
        tenant_id=principal.claims.tenant_id,
        start_at_utc=start,
        end_at_utc=end,
        limit=limit,
    )
    return AppointmentListResponse(items=[_list_item_response(item) for item in rows])

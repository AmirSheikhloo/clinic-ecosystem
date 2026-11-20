"""Manual appointment scheduling and day listing (BETA-01B)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from clinic_ecosystem.application.scheduling.exceptions import (
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
    serialize_manual_conflict_response,
)
from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7

router = APIRouter(prefix="/api/v1/appointments", tags=["appointments"])


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


class ScheduleAppointmentResponse(BaseModel):
    appointment_id: str
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

    key = idempotency_key.strip()
    if not key or len(key) > 128:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_idempotency_key",
                "message": "Idempotency-Key is required (1..128 characters)",
            },
        )

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
    except ManualOverlapAcknowledgementRequired as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=serialize_manual_conflict_response(exc),
        ) from None
    except UnauthorizedScheduling:
        # Unauthorized staff must never obtain conflict patient names.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "permission_denied",
                "message": "Manual overlap is not authorized for this principal",
            },
        ) from None
    except IdempotencyConflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "idempotency_conflict",
                "message": "Idempotency key reused with a different request fingerprint",
            },
        ) from None
    except IdempotencyInProgress:
        raise HTTPException(
            status_code=status.HTTP_425_TOO_EARLY,
            detail={
                "error": "idempotency_in_progress",
                "message": "A matching request is still in progress",
            },
        ) from None
    except CapacityConflictException as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "capacity_conflict", "message": str(exc)},
        ) from None
    except ServiceRequirementsNotMet as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_resources", "message": str(exc)},
        ) from None
    except InvalidAppointmentSchedule as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_appointment", "message": str(exc)},
        ) from None
    finally:
        await session.close()

    return ScheduleAppointmentResponse(
        appointment_id=str(result.appointment_id),
        replayed=result.replayed,
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
    return AppointmentListResponse(
        items=[
            AppointmentListItemResponse(
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
            for item in rows
        ]
    )

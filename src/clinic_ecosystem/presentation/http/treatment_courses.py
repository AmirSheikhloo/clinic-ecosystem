"""HTTP stubs for treatment courses / rolling recall (Task 34 R2 §9)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field
from sqlalchemy import text

from clinic_ecosystem.application.shared.errors import Conflict, ValidationFailed
from clinic_ecosystem.application.treatment_courses.service import TreatmentCourseService
from clinic_ecosystem.domain.access import permissions as perm
from clinic_ecosystem.infrastructure.persistence.treatment_courses import (
    SqlTreatmentCourseStore,
)
from clinic_ecosystem.infrastructure.persistence.uow import SqlAlchemyUnitOfWork
from clinic_ecosystem.presentation.http.common import load_granted, require
from clinic_ecosystem.presentation.http.dependencies import (
    AuthenticatedPrincipal,
    get_authenticated_principal,
    get_uow,
)

router = APIRouter(prefix="/api/v1/courses", tags=["treatment-courses"])
Principal = Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)]
Uow = Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)]


class EnrollIn(BaseModel):
    patient_id: UUID
    service_id: UUID
    planned_sessions: int = Field(ge=1, le=100)
    interval_kind: Literal["JALALI_CALENDAR_MONTH", "FIXED_DAYS", "CALENDAR_MONTH"] = (
        "JALALI_CALENDAR_MONTH"
    )
    interval_value: int = Field(default=1, ge=1, le=366)
    reminder_lead_days: int = Field(default=2, ge=0, le=30)
    template_version_id: UUID | None = None
    # Explicitly rejected if true — prepaid remains disabled.
    prepaid_entitlement_enabled: bool = False


class CompleteSessionIn(BaseModel):
    service_record_id: UUID
    appointment_id: UUID | None = None
    idempotency_key: str = Field(min_length=8, max_length=200)


class LifecycleIn(BaseModel):
    status: Literal["ACTIVE", "PAUSED", "TERMINATED", "REASSESSMENT_REQUIRED", "COMPLETED"]


async def _require_courses_schema(uow: Uow) -> None:
    store = SqlTreatmentCourseStore(uow.session)
    if not await store.schema_present():
        raise Conflict(
            "Treatment courses schema unavailable",
            code="ops_schema_unavailable",
        )


@router.get("/patients/{patient_id}")
async def list_patient_courses(
    patient_id: UUID, principal: Principal, uow: Uow
) -> dict[str, Any]:
    granted = await load_granted(principal, uow)
    require(granted, perm.COURSES_VIEW)
    await _require_courses_schema(uow)
    store = SqlTreatmentCourseStore(uow.session)
    rows = await store.list_courses_for_patient(
        tenant_id=principal.claims.tenant_id, patient_id=patient_id
    )
    return {
        "items": [
            {
                "id": str(r["id"]),
                "service_id": str(r["service_id"]),
                "planned_sessions": r["planned_sessions"],
                "completed_session_count": r["completed_session_count"],
                "status": r["status"],
                "billing_mode": r["billing_mode"],
                "next_suggested_date_tehran": (
                    r["next_suggested_date_tehran"].isoformat()
                    if r["next_suggested_date_tehran"]
                    else None
                ),
                "last_completion_date_tehran": (
                    r["last_completion_date_tehran"].isoformat()
                    if r["last_completion_date_tehran"]
                    else None
                ),
                "interval_kind": r["interval_kind"],
                "interval_value": r["interval_value"],
                "reminder_lead_days": r["reminder_lead_days"],
                "aggregate_version": r["aggregate_version"],
                "pay_per_session": True,
                "prepaid_enabled": False,
            }
            for r in rows
        ],
        "prepaid_entitlement_enabled": False,
        "shared_settlement_enabled": False,
    }


@router.post("/enroll")
async def enroll_course(body: EnrollIn, principal: Principal, uow: Uow) -> dict[str, Any]:
    granted = await load_granted(principal, uow)
    require(granted, perm.COURSES_MANAGE)
    await _require_courses_schema(uow)
    if body.prepaid_entitlement_enabled:
        raise ValidationFailed(
            "prepaid entitlement is disabled pending ratification",
            code="prepaid_disabled",
        )
    svc = TreatmentCourseService(uow.session)
    row = await svc.enroll_pay_per_session(
        tenant_id=principal.claims.tenant_id,
        patient_id=body.patient_id,
        service_id=body.service_id,
        template_version_id=body.template_version_id,
        planned_sessions=body.planned_sessions,
        interval_kind=body.interval_kind,
        interval_value=body.interval_value,
        reminder_lead_days=body.reminder_lead_days,
        actor_user_id=principal.claims.user_id,
    )
    await uow.commit()
    return row


@router.post("/{course_id}/sessions/complete")
async def complete_session(
    course_id: UUID,
    body: CompleteSessionIn,
    principal: Principal,
    uow: Uow,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> dict[str, Any]:
    granted = await load_granted(principal, uow)
    require(granted, perm.COURSES_MANAGE)
    await _require_courses_schema(uow)
    expected = int(if_match) if if_match and if_match.isdigit() else None
    svc = TreatmentCourseService(uow.session)
    result = await svc.record_session_completion(
        tenant_id=principal.claims.tenant_id,
        course_id=course_id,
        service_record_id=body.service_record_id,
        appointment_id=body.appointment_id,
        idempotency_key=body.idempotency_key,
        expected_version=expected,
    )
    await uow.commit()
    return {
        "course_id": str(result.course_id),
        "session_id": str(result.session_id),
        "session_no": result.session_no,
        "suggested_date_tehran": result.suggested_date_tehran.isoformat(),
        "reminder_date_tehran": result.reminder_date_tehran.isoformat(),
        "schedule_version": result.schedule_version,
        "replayed": result.replayed,
        "billing_mode": "PAY_PER_SESSION",
        "prepaid_enabled": False,
    }


@router.post("/{course_id}/lifecycle")
async def course_lifecycle(
    course_id: UUID,
    body: LifecycleIn,
    principal: Principal,
    uow: Uow,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> dict[str, Any]:
    granted = await load_granted(principal, uow)
    require(granted, perm.COURSES_MANAGE)
    await _require_courses_schema(uow)
    expected = int(if_match) if if_match and if_match.isdigit() else None
    svc = TreatmentCourseService(uow.session)
    row = await svc.set_lifecycle(
        tenant_id=principal.claims.tenant_id,
        course_id=course_id,
        status=body.status,
        expected_version=expected,
    )
    await uow.commit()
    return row


@router.get("/templates")
async def list_templates(principal: Principal, uow: Uow) -> dict[str, Any]:
    """Course template catalog stub (pay-per-session only)."""
    granted = await load_granted(principal, uow)
    require(granted, perm.COURSES_VIEW)
    await _require_courses_schema(uow)
    result = await uow.session.execute(
        __import__("sqlalchemy", fromlist=["text"]).text(
            """
            SELECT t.id, t.service_id, t.template_code, t.template_name,
                   t.current_version_no, t.is_active,
                   v.planned_sessions, v.interval_kind, v.interval_value,
                   v.reminder_lead_days, v.billing_mode, v.scheduling_mode
            FROM service_course_templates t
            LEFT JOIN service_course_template_versions v
              ON v.tenant_id = t.tenant_id
             AND v.template_id = t.id
             AND v.version_no = t.current_version_no
            WHERE t.tenant_id = :tenant_id
            ORDER BY t.template_code
            """
        ),
        {"tenant_id": principal.claims.tenant_id},
    )
    items = []
    for r in result.mappings().all():
        items.append(
            {
                "id": str(r["id"]),
                "service_id": str(r["service_id"]),
                "template_code": r["template_code"],
                "template_name": r["template_name"],
                "version_no": r["current_version_no"],
                "is_active": r["is_active"],
                "planned_sessions": r["planned_sessions"],
                "interval_kind": r["interval_kind"],
                "interval_value": r["interval_value"],
                "reminder_lead_days": r["reminder_lead_days"],
                "billing_mode": r["billing_mode"] or "PAY_PER_SESSION",
                "scheduling_mode": r["scheduling_mode"] or "ROLLING",
                "prepaid_enabled": False,
            }
        )
    return {"items": items, "prepaid_entitlement_enabled": False}


@router.get("/health/synthetic-reminders")
async def synthetic_reminder_health(principal: Principal, uow: Uow) -> dict[str, Any]:
    """Ops visibility for synthetic sink — never claims live SMS."""
    granted = await load_granted(principal, uow)
    require(granted, perm.COURSES_VIEW)
    await _require_courses_schema(uow)
    text = __import__("sqlalchemy", fromlist=["text"]).text
    pending = await uow.session.execute(
        text(
            """
            SELECT COUNT(*)::INT AS n
            FROM notification_outbox_synthetic
            WHERE tenant_id = :tenant_id
              AND work_state IN ('PENDING', 'RETRYABLE', 'CLAIMED')
            """
        ),
        {"tenant_id": principal.claims.tenant_id},
    )
    delivered = await uow.session.execute(
        text(
            """
            SELECT COUNT(*)::INT AS n
            FROM synthetic_notification_deliveries
            WHERE tenant_id = :tenant_id
            """
        ),
        {"tenant_id": principal.claims.tenant_id},
    )
    return {
        "pending_jobs": pending.mappings().one()["n"],
        "synthetic_deliveries": delivered.mappings().one()["n"],
        "real_sms_enabled": False,
        "real_bot_enabled": False,
        "as_of_utc": datetime.utcnow().isoformat() + "Z",
    }

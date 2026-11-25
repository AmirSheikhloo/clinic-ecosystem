"""Patient registration and search HTTP routes (BETA-01B)."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from clinic_ecosystem.infrastructure.auth.settings import PATIENTS_REGISTER, PATIENTS_SEARCH
from clinic_ecosystem.infrastructure.persistence.audit import SqlAuditStore
from clinic_ecosystem.infrastructure.persistence.patients import SqlPatientRepository
from clinic_ecosystem.infrastructure.persistence.uow import SqlAlchemyUnitOfWork
from clinic_ecosystem.presentation.http.dependencies import (
    AuthenticatedPrincipal,
    get_authenticated_principal,
    get_uow,
    require_permission,
)

router = APIRouter(prefix="/api/v1/patients", tags=["patients"])


class RegisterPatientRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=120)
    last_name: str = Field(min_length=1, max_length=120)
    birth_date: date | None = None


class PatientResponse(BaseModel):
    patient_profile_id: str
    person_id: str
    first_name: str
    last_name: str
    birth_date: date | None
    is_active: bool


class PatientListResponse(BaseModel):
    items: list[PatientResponse]


@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def register_patient(
    body: RegisterPatientRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
) -> PatientResponse:
    await require_permission(PATIENTS_REGISTER, principal=principal, uow=uow)
    first = body.first_name.strip()
    last = body.last_name.strip()
    if not first or not last:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "patient_validation_error",
                "message": "First name and last name are required",
            },
        )
    repo = SqlPatientRepository(uow.session)
    try:
        record = await repo.register(
            tenant_id=principal.claims.tenant_id,
            first_name=first,
            last_name=last,
            birth_date=body.birth_date,
        )
        await SqlAuditStore(uow.session).append(
            tenant_id=principal.claims.tenant_id,
            actor_type="USER_ACCOUNT",
            actor_id=principal.account.id,
            operation="patient.registered",
            target_type="patient_profile",
            target_id=record.patient_profile_id,
            details={},
        )
        await uow.commit()
    except Exception:
        await uow.rollback()
        raise
    return PatientResponse(
        patient_profile_id=str(record.patient_profile_id),
        person_id=str(record.person_id),
        first_name=record.first_name,
        last_name=record.last_name,
        birth_date=record.birth_date,
        is_active=record.is_active,
    )


@router.get("", response_model=PatientListResponse)
async def search_patients(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    q: Annotated[str, Query(min_length=1, max_length=120)],
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
) -> PatientListResponse:
    await require_permission(PATIENTS_SEARCH, principal=principal, uow=uow)
    repo = SqlPatientRepository(uow.session)
    rows = await repo.search_by_name(
        tenant_id=principal.claims.tenant_id,
        query=q,
        limit=limit,
        offset=offset,
    )
    return PatientListResponse(
        items=[
            PatientResponse(
                patient_profile_id=str(item.patient_profile_id),
                person_id=str(item.person_id),
                first_name=item.first_name,
                last_name=item.last_name,
                birth_date=item.birth_date,
                is_active=item.is_active,
            )
            for item in rows
        ]
    )

"""Patient registry HTTP routes (Workstream A)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response
from pydantic import BaseModel

from clinic_ecosystem.application.patient_registry.service import (
    PatientChanges,
    PatientRegistryService,
)
from clinic_ecosystem.application.shared.preconditions import parse_if_match
from clinic_ecosystem.domain.access import permissions as perm
from clinic_ecosystem.infrastructure.persistence.patient_registry import (
    PatientProfileRow,
    SqlPatientRegistry,
)
from clinic_ecosystem.infrastructure.persistence.uow import SqlAlchemyUnitOfWork
from clinic_ecosystem.presentation.http.common import (
    actor_of,
    load_granted,
    require,
    set_etag,
)
from clinic_ecosystem.presentation.http.dependencies import (
    AuthenticatedPrincipal,
    get_authenticated_principal,
    get_uow,
)

router = APIRouter(prefix="/api/v1/patients", tags=["patient-registry"])
Principal = Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)]
Uow = Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)]


class PatientProfile(BaseModel):
    patient_profile_id: str
    person_id: str
    first_name: str
    last_name: str
    birth_date: date | None
    dossier_number: str | None
    is_active: bool
    aggregate_version: int
    created_at_utc: datetime
    masked_identifier: str | None = None
    identifier_type: str | None = None
    masked_phone: str | None = None


class PatientPage(BaseModel):
    items: list[PatientProfile]
    total: int
    limit: int
    offset: int


class PatientPatch(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    birth_date: date | None = None
    dossier_number: str | None = None
    is_active: bool | None = None


class HistoryItem(BaseModel):
    appointment_id: str
    status: str
    booking_channel: str
    scheduled_start_at_utc: datetime
    scheduled_end_at_utc: datetime
    service_id: str
    service_name: str


class HistoryPage(BaseModel):
    items: list[HistoryItem]
    total: int
    limit: int
    offset: int


def to_profile(
    row: PatientProfileRow,
    *,
    masked_identifier: str | None = None,
    identifier_type: str | None = None,
    masked_phone: str | None = None,
) -> PatientProfile:
    return PatientProfile(
        patient_profile_id=str(row.patient_profile_id),
        person_id=str(row.person_id),
        first_name=row.first_name,
        last_name=row.last_name,
        birth_date=row.birth_date,
        dossier_number=row.dossier_number,
        is_active=row.is_active,
        aggregate_version=row.aggregate_version,
        created_at_utc=row.created_at_utc,
        masked_identifier=masked_identifier,
        identifier_type=identifier_type,
        masked_phone=masked_phone,
    )


async def to_profile_with_masks(
    registry: SqlPatientRegistry, *, tenant_id: UUID, row: PatientProfileRow
) -> PatientProfile:
    masks = await registry.masked_identity(tenant_id=tenant_id, person_id=row.person_id)
    return to_profile(
        row,
        masked_identifier=masks.masked_identifier,
        identifier_type=masks.identifier_type,
        masked_phone=masks.masked_phone,
    )


@router.get("/directory", response_model=PatientPage)
async def list_directory(
    principal: Principal,
    uow: Uow,
    q: Annotated[str | None, Query(max_length=120)] = None,
    status: Annotated[str, Query(pattern="^(active|inactive|all)$")] = "active",
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
) -> PatientPage:
    granted = await load_granted(principal, uow)
    require(granted, perm.PATIENTS_SEARCH)
    if status != "active":
        require(granted, perm.PATIENTS_VIEW_PROFILE)
    rows, total = await SqlPatientRegistry(uow.session).list_page(
        tenant_id=principal.claims.tenant_id,
        q=(q or "").strip() or None,
        is_active={"active": True, "inactive": False, "all": None}[status],
        limit=limit,
        offset=offset,
    )
    return PatientPage(
        items=[to_profile(r) for r in rows], total=total, limit=limit, offset=offset
    )


@router.get("/{patient_profile_id}", response_model=PatientProfile)
async def get_patient(
    patient_profile_id: UUID, principal: Principal, uow: Uow, response: Response
) -> PatientProfile:
    require(await load_granted(principal, uow), perm.PATIENTS_VIEW_PROFILE)
    row = await PatientRegistryService(uow).require(actor_of(principal), patient_profile_id)
    set_etag(response, row.aggregate_version)
    return await to_profile_with_masks(
        SqlPatientRegistry(uow.session),
        tenant_id=principal.claims.tenant_id,
        row=row,
    )


@router.patch("/{patient_profile_id}", response_model=PatientProfile)
async def patch_patient(
    patient_profile_id: UUID,
    body: PatientPatch,
    principal: Principal,
    uow: Uow,
    response: Response,
    if_match: Annotated[str | None, Header()] = None,
) -> PatientProfile:
    granted = await load_granted(principal, uow)
    require(granted, perm.PATIENTS_VIEW_PROFILE)
    expected = parse_if_match(if_match)
    changes = PatientChanges(
        fields_set=frozenset(body.model_fields_set),
        first_name=body.first_name,
        last_name=body.last_name,
        birth_date=body.birth_date,
        dossier_number=body.dossier_number,
        is_active=body.is_active,
    )
    service = PatientRegistryService(uow)
    try:
        row = await service.update(
            actor_of(principal), granted, patient_profile_id, expected, changes
        )
        await uow.commit()
    except BaseException:
        await uow.rollback()
        raise
    set_etag(response, row.aggregate_version)
    return await to_profile_with_masks(
        SqlPatientRegistry(uow.session),
        tenant_id=principal.claims.tenant_id,
        row=row,
    )


@router.get("/{patient_profile_id}/appointments", response_model=HistoryPage)
async def patient_history(
    patient_profile_id: UUID,
    principal: Principal,
    uow: Uow,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
) -> HistoryPage:
    require(await load_granted(principal, uow), perm.PATIENTS_VIEW_HISTORY)
    actor = actor_of(principal)
    await PatientRegistryService(uow).require(actor, patient_profile_id)
    rows, total = await SqlPatientRegistry(uow.session).appointment_history(
        tenant_id=actor.tenant_id,
        patient_profile_id=patient_profile_id,
        limit=limit,
        offset=offset,
    )
    return HistoryPage(
        items=[
            HistoryItem(
                appointment_id=str(r["appointment_id"]),
                status=r["status"],
                booking_channel=r["booking_channel"],
                scheduled_start_at_utc=r["scheduled_start_at_utc"],
                scheduled_end_at_utc=r["scheduled_end_at_utc"],
                service_id=str(r["service_id"]),
                service_name=r["service_name"],
            )
            for r in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )

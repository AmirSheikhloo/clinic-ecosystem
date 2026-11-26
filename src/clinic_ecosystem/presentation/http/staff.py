"""Staff directory HTTP routes (Workstream B)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response, status
from pydantic import BaseModel, Field

from clinic_ecosystem.application.shared.errors import ValidationFailed
from clinic_ecosystem.application.shared.idempotent import run_idempotent, validate_key
from clinic_ecosystem.application.shared.preconditions import parse_if_match
from clinic_ecosystem.application.staff.service import (
    STAFF_KINDS,
    LoginSpec,
    NewStaff,
    StaffService,
)
from clinic_ecosystem.domain.access import permissions as perm
from clinic_ecosystem.infrastructure.persistence.staff_registry import SqlStaffRegistry, StaffRow
from clinic_ecosystem.infrastructure.persistence.uow import SqlAlchemyUnitOfWork
from clinic_ecosystem.presentation.http.common import actor_of, load_granted, require, set_etag
from clinic_ecosystem.presentation.http.dependencies import (
    AuthenticatedPrincipal,
    get_authenticated_principal,
    get_uow,
)

router = APIRouter(prefix="/api/v1/staff", tags=["staff"])
Principal = Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)]
Uow = Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)]


class StaffAccountView(BaseModel):
    account_id: str
    is_active: bool
    login_identifier: str | None = None


class StaffView(BaseModel):
    staff_profile_id: str
    person_id: str
    first_name: str
    last_name: str
    staff_kind: str
    medical_council_code: str | None
    is_active: bool
    aggregate_version: int
    created_at_utc: datetime
    account: StaffAccountView | None


class StaffPage(BaseModel):
    items: list[StaffView]
    total: int
    limit: int
    offset: int


class LoginBody(BaseModel):
    login_identifier: str = Field(max_length=254)
    password: str = Field(max_length=256, repr=False)


class CreateStaffBody(BaseModel):
    first_name: str = Field(max_length=120)
    last_name: str = Field(max_length=120)
    staff_kind: str = Field(max_length=32)
    medical_council_code: str | None = Field(default=None, max_length=64)
    birth_date: date | None = None
    create_login_account: bool = False
    login: LoginBody | None = None


class PatchStaffBody(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    staff_kind: str | None = None
    medical_council_code: str | None = None
    is_active: bool | None = None


def to_view(row: StaffRow, *, show_login: bool) -> StaffView:
    account = None
    if row.account_id is not None:
        account = StaffAccountView(
            account_id=str(row.account_id),
            is_active=bool(row.account_is_active),
            login_identifier=row.login_identifier if show_login else None,
        )
    return StaffView(
        staff_profile_id=str(row.staff_profile_id),
        person_id=str(row.person_id),
        first_name=row.first_name,
        last_name=row.last_name,
        staff_kind=row.staff_kind,
        medical_council_code=row.medical_council_code,
        is_active=row.is_active,
        aggregate_version=row.aggregate_version,
        created_at_utc=row.created_at_utc,
        account=account,
    )


@router.get("/kinds")
async def staff_kinds(principal: Principal, uow: Uow) -> dict[str, list[str]]:
    require(await load_granted(principal, uow), perm.STAFF_VIEW)
    return {"items": list(STAFF_KINDS)}


@router.get("", response_model=StaffPage)
async def list_staff(
    principal: Principal,
    uow: Uow,
    q: Annotated[str | None, Query(max_length=120)] = None,
    kind: Annotated[str | None, Query(max_length=32)] = None,
    status_filter: Annotated[str, Query(alias="status", pattern="^(active|inactive|all)$")] = "all",
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
) -> StaffPage:
    granted = await load_granted(principal, uow)
    require(granted, perm.STAFF_VIEW)
    rows, total = await SqlStaffRegistry(uow.session).list_page(
        tenant_id=principal.claims.tenant_id,
        q=(q or "").strip() or None,
        kind=kind,
        is_active={"active": True, "inactive": False, "all": None}[status_filter],
        limit=limit,
        offset=offset,
    )
    show = perm.ACCOUNTS_VIEW in granted
    return StaffPage(
        items=[to_view(r, show_login=show) for r in rows],
        total=total, limit=limit, offset=offset,
    )


@router.get("/{staff_profile_id}", response_model=StaffView)
async def get_staff(
    staff_profile_id: UUID, principal: Principal, uow: Uow, response: Response
) -> StaffView:
    granted = await load_granted(principal, uow)
    require(granted, perm.STAFF_VIEW)
    row = await StaffService(uow).require(actor_of(principal), staff_profile_id)
    set_etag(response, row.aggregate_version)
    return to_view(row, show_login=perm.ACCOUNTS_VIEW in granted)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_staff(
    body: CreateStaffBody,
    principal: Principal,
    uow: Uow,
    response: Response,
    idempotency_key: Annotated[str | None, Header()] = None,
) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.STAFF_MANAGE)
    key = validate_key(idempotency_key)
    if body.create_login_account and body.login is None:
        raise ValidationFailed("Login details are required", code="login_required")
    login = (
        LoginSpec(body.login.login_identifier, body.login.password)
        if body.create_login_account and body.login
        else None
    )
    data = NewStaff(
        first_name=body.first_name,
        last_name=body.last_name,
        staff_kind=body.staff_kind,
        medical_council_code=body.medical_council_code,
        birth_date=body.birth_date,
        login=login,
    )
    actor = actor_of(principal)
    service = StaffService(uow)
    fingerprint_payload = {
        "first_name": body.first_name.strip(),
        "last_name": body.last_name.strip(),
        "staff_kind": body.staff_kind,
        "medical_council_code": (body.medical_council_code or "").strip() or None,
        "birth_date": body.birth_date.isoformat() if body.birth_date else None,
        "login_identifier": body.login.login_identifier.strip().lower() if login and body.login else None,
        "has_password": bool(login),
    }
    result, replayed = await run_idempotent(
        uow,
        tenant_id=actor.tenant_id,
        principal_id=actor.account_id,
        scope="staff.create",
        key=key,
        request_payload=fingerprint_payload,
        action=lambda: service.create(actor, granted, data),
    )
    if replayed:
        response.status_code = status.HTTP_200_OK
        response.headers["Idempotent-Replay"] = "true"
    return result


@router.patch("/{staff_profile_id}", response_model=StaffView)
async def patch_staff(
    staff_profile_id: UUID,
    body: PatchStaffBody,
    principal: Principal,
    uow: Uow,
    response: Response,
    if_match: Annotated[str | None, Header()] = None,
) -> StaffView:
    granted = await load_granted(principal, uow)
    require(granted, perm.STAFF_MANAGE)
    expected = parse_if_match(if_match)
    service = StaffService(uow)
    try:
        row = await service.update(
            actor_of(principal),
            staff_profile_id,
            expected,
            {k: getattr(body, k) for k in body.model_fields_set},
        )
        await uow.commit()
    except BaseException:
        await uow.rollback()
        raise
    set_etag(response, row.aggregate_version)
    return to_view(row, show_login=perm.ACCOUNTS_VIEW in granted)


@router.post("/{staff_profile_id}/login-account", status_code=status.HTTP_201_CREATED)
async def provision_login(
    staff_profile_id: UUID,
    body: LoginBody,
    principal: Principal,
    uow: Uow,
    response: Response,
    idempotency_key: Annotated[str | None, Header()] = None,
) -> dict:
    granted = await load_granted(principal, uow)
    require(granted, perm.STAFF_PROVISION_LOGIN)
    key = validate_key(idempotency_key)
    actor = actor_of(principal)
    service = StaffService(uow)
    spec = LoginSpec(body.login_identifier, body.password)
    result, replayed = await run_idempotent(
        uow,
        tenant_id=actor.tenant_id,
        principal_id=actor.account_id,
        scope=f"staff.provision_login:{staff_profile_id}",
        key=key,
        request_payload={
            "login_identifier": body.login_identifier.strip().lower(),
            "has_password": True,
        },
        action=lambda: service.provision_login(actor, staff_profile_id, spec),
    )
    if replayed:
        response.status_code = status.HTTP_200_OK
        response.headers["Idempotent-Replay"] = "true"
    return result

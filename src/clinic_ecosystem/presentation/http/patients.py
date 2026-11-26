"""Patient registration, search, and encrypted-identifier lookup (spec §52)."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from clinic_ecosystem.domain.identity.national_id import (
    is_valid_national_id_checksum,
    normalize_national_id,
)
from clinic_ecosystem.infrastructure.auth.settings import PATIENTS_REGISTER, PATIENTS_SEARCH
from clinic_ecosystem.infrastructure.crypto.pii_box import (
    CryptoUnavailable,
    load_pii_keys,
    mask_national_id,
    mask_phone,
    normalize_phone_e164,
)
from clinic_ecosystem.infrastructure.persistence.audit import SqlAuditStore
from clinic_ecosystem.infrastructure.persistence.patients import SqlPatientRepository
from clinic_ecosystem.infrastructure.persistence.person_identifiers import (
    DuplicateOfficialIdentifier,
    SqlPersonIdentifierStore,
)
from clinic_ecosystem.infrastructure.persistence.person_phones import SqlPersonPhoneStore
from clinic_ecosystem.infrastructure.persistence.uow import SqlAlchemyUnitOfWork
from clinic_ecosystem.presentation.http.dependencies import (
    AuthenticatedPrincipal,
    get_authenticated_principal,
    get_uow,
    require_permission,
)

router = APIRouter(prefix="/api/v1/patients", tags=["patients"])

IdentityType = Literal["IR_NATIONAL_ID", "FOREIGN_FIDA_CODE", "FOREIGN_PASSPORT", "EXCEPTION"]
_DEFAULT_AUTHORITY = {
    "IR_NATIONAL_ID": "IR",
    "FOREIGN_FIDA_CODE": "FOREIGN",
    "FOREIGN_PASSPORT": "FOREIGN",
}


class RegisterPatientRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=120)
    last_name: str = Field(min_length=1, max_length=120)
    birth_date: date | None = None
    national_id: str | None = Field(default=None, max_length=40)
    phone: str | None = Field(default=None, max_length=32)
    identity_type: IdentityType | None = None
    issuing_country_or_authority: str | None = Field(default=None, max_length=64)
    identity_exception_reason: str | None = Field(default=None, max_length=200)
    is_shared_phone: bool = False


class PatientResponse(BaseModel):
    patient_profile_id: str
    person_id: str
    first_name: str
    last_name: str
    birth_date: date | None
    is_active: bool
    masked_identifier: str | None = None
    masked_phone: str | None = None


class PatientListResponse(BaseModel):
    items: list[PatientResponse]


class IdentifierLookupResponse(BaseModel):
    found: bool
    patient_profile_id: str | None = None
    person_id: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    id_type: str | None = None
    masked_display: str | None = None
    verification_status: str | None = None


def _crypto_unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={
            "error": "identifier_crypto_unavailable",
            "message": "Identifier encryption keys are not configured",
        },
    )


def _normalize_official(*, identity_type: str, raw_value: str | None) -> str:
    value = (raw_value or "").strip()
    if not value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "identifier_required", "message": "Official identifier value is required"},
        )
    if identity_type == "IR_NATIONAL_ID":
        try:
            national = normalize_national_id(value)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "national_id_invalid", "message": "National ID must be at most 10 digits"},
            )
        if not is_valid_national_id_checksum(national):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "national_id_checksum_invalid", "message": "National ID check digit is invalid"},
            )
        return national
    if "|" in value or len(value) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "identifier_invalid", "message": "Foreign identifier is invalid"},
        )
    return value


@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def register_patient(
    body: RegisterPatientRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
) -> PatientResponse:
    await require_permission(PATIENTS_REGISTER, principal=principal, uow=uow)
    first, last = body.first_name.strip(), body.last_name.strip()
    if not first or not last:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "patient_validation_error", "message": "First name and last name are required"},
        )

    has_id = bool((body.national_id or "").strip())
    identity_type = (body.identity_type or ("IR_NATIONAL_ID" if has_id else "EXCEPTION")).upper()
    if identity_type not in _DEFAULT_AUTHORITY and identity_type != "EXCEPTION":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "identity_type_invalid", "message": "Unsupported identity type"},
        )

    # Clause 755: missing official ID must not block profile creation. Exception
    # reason is encouraged and audited when present; it is not a hard gate.
    exception_reason = (body.identity_exception_reason or "").strip() or None
    official_value: str | None = None
    authority: str | None = None
    if identity_type != "EXCEPTION":
        official_value = _normalize_official(identity_type=identity_type, raw_value=body.national_id)
        authority = (body.issuing_country_or_authority or _DEFAULT_AUTHORITY[identity_type]).strip().upper()

    phone_raw = (body.phone or "").strip() or None
    phone_e164: str | None = None
    if phone_raw:
        try:
            phone_e164 = normalize_phone_e164(phone_raw)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "phone_invalid", "message": "Phone must normalize to E.164"},
            )

    keys = None
    if official_value is not None or phone_e164 is not None:
        try:
            keys = load_pii_keys()
        except CryptoUnavailable:
            raise _crypto_unavailable() from None

    repo = SqlPatientRepository(uow.session)
    id_store = SqlPersonIdentifierStore(uow.session)
    phone_store = SqlPersonPhoneStore(uow.session)
    masked_identifier = masked_phone = None
    try:
        if official_value and keys and authority:
            if await id_store.exists_duplicate(
                tenant_id=principal.claims.tenant_id,
                id_type=identity_type,
                issuing_country_or_authority=authority,
                normalized_value=official_value,
                keys=keys,
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "error": "duplicate_official_identifier",
                        "message": "An existing person already uses this official identifier",
                    },
                )

        record = await repo.register(
            tenant_id=principal.claims.tenant_id,
            first_name=first,
            last_name=last,
            birth_date=body.birth_date,
        )

        if official_value and keys and authority:
            try:
                await id_store.insert(
                    tenant_id=principal.claims.tenant_id,
                    person_id=record.person_id,
                    id_type=identity_type,
                    issuing_country_or_authority=authority,
                    normalized_value=official_value,
                    keys=keys,
                )
            except DuplicateOfficialIdentifier as exc:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "error": "duplicate_official_identifier",
                        "message": "An existing person already uses this official identifier",
                    },
                ) from exc
            masked_identifier = (
                mask_national_id(official_value)
                if identity_type == "IR_NATIONAL_ID"
                else ("****" + official_value[-4:] if len(official_value) >= 4 else "****")
            )

        if phone_e164 and keys:
            await phone_store.insert(
                tenant_id=principal.claims.tenant_id,
                person_id=record.person_id,
                phone=phone_e164,
                keys=keys,
                is_shared_phone=body.is_shared_phone,
            )
            masked_phone = mask_phone(phone_e164)

        await SqlAuditStore(uow.session).append(
            tenant_id=principal.claims.tenant_id,
            actor_type="USER_ACCOUNT",
            actor_id=principal.account.id,
            operation="patient.registered",
            target_type="patient_profile",
            target_id=record.patient_profile_id,
            details={
                "identity_type": identity_type,
                "national_id_stored": official_value is not None,
                "phone_stored": phone_e164 is not None,
                "identity_exception_reason": exception_reason,
                "is_shared_phone": body.is_shared_phone if phone_e164 else None,
            },
        )
        await uow.commit()
    except HTTPException:
        await uow.rollback()
        raise
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
        masked_identifier=masked_identifier,
        masked_phone=masked_phone,
    )


OfficialLookupType = Literal["IR_NATIONAL_ID", "FOREIGN_FIDA_CODE", "FOREIGN_PASSPORT"]


class IdentifierLookupRequest(BaseModel):
    value: str = Field(min_length=1, max_length=40)
    id_type: OfficialLookupType = "IR_NATIONAL_ID"
    issuing_country_or_authority: str | None = Field(default=None, max_length=64)


class PhoneLookupRequest(BaseModel):
    phone: str = Field(min_length=3, max_length=32)
    limit: int = Field(default=20, ge=1, le=50)


@router.post("/lookup/identifier", response_model=IdentifierLookupResponse)
async def lookup_by_identifier(
    body: IdentifierLookupRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
) -> IdentifierLookupResponse:
    """Exact official-identifier lookup. Body-only — never put raw IDs in URLs."""
    await require_permission(PATIENTS_SEARCH, principal=principal, uow=uow)
    kind = body.id_type.strip().upper()
    if kind not in _DEFAULT_AUTHORITY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "identity_type_invalid", "message": "Unsupported identity type"},
        )
    try:
        keys = load_pii_keys()
    except CryptoUnavailable:
        raise _crypto_unavailable() from None
    normalized = _normalize_official(identity_type=kind, raw_value=body.value)
    authority = (body.issuing_country_or_authority or _DEFAULT_AUTHORITY[kind]).strip().upper()
    hit = await SqlPersonIdentifierStore(uow.session).lookup_exact(
        tenant_id=principal.claims.tenant_id,
        id_type=kind,
        issuing_country_or_authority=authority,
        normalized_value=normalized,
        keys=keys,
    )
    if hit is None:
        return IdentifierLookupResponse(found=False)
    return IdentifierLookupResponse(
        found=True,
        patient_profile_id=str(hit.patient_profile_id) if hit.patient_profile_id else None,
        person_id=str(hit.person_id),
        first_name=hit.first_name,
        last_name=hit.last_name,
        id_type=hit.id_type,
        masked_display=hit.masked_display,
        verification_status=hit.verification_status,
    )


@router.post("/lookup/phone", response_model=PatientListResponse)
async def lookup_by_phone(
    body: PhoneLookupRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
) -> PatientListResponse:
    """Shared-phone search. Body-only — never put raw phones in query strings."""
    await require_permission(PATIENTS_SEARCH, principal=principal, uow=uow)
    try:
        keys = load_pii_keys()
    except CryptoUnavailable:
        raise _crypto_unavailable() from None
    try:
        normalize_phone_e164(body.phone)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "phone_invalid", "message": "Phone must normalize to E.164"},
        )
    hits = await SqlPersonPhoneStore(uow.session).search_by_phone(
        tenant_id=principal.claims.tenant_id,
        phone=body.phone,
        keys=keys,
        limit=body.limit,
    )
    return PatientListResponse(
        items=[
            PatientResponse(
                patient_profile_id=str(h.patient_profile_id),
                person_id=str(h.person_id),
                first_name=h.first_name,
                last_name=h.last_name,
                birth_date=None,
                is_active=True if h.is_active is None else h.is_active,
                masked_phone=h.masked_phone,
            )
            for h in hits
            if h.patient_profile_id is not None
        ]
    )


@router.get("", response_model=PatientListResponse)
async def search_patients(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
    q: Annotated[str | None, Query(max_length=120)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
) -> PatientListResponse:
    """Name/dossier text search only. Official IDs and phones use POST lookup routes."""
    await require_permission(PATIENTS_SEARCH, principal=principal, uow=uow)
    name_q = (q or "").strip()
    if not name_q:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "query_required", "message": "Provide q"},
        )
    rows = await SqlPatientRepository(uow.session).search_by_name(
        tenant_id=principal.claims.tenant_id,
        query=name_q,
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

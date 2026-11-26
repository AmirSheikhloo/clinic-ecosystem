"""Patient registry use cases: guarded updates and bounded reads."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from clinic_ecosystem.application.shared.actor import Actor
from clinic_ecosystem.application.shared.errors import (
    Conflict,
    Forbidden,
    NotFound,
    PreconditionFailed,
    ValidationFailed,
)
from clinic_ecosystem.domain.access import permissions as perm
from clinic_ecosystem.infrastructure.persistence.audit import SqlAuditStore
from clinic_ecosystem.infrastructure.persistence.patient_registry import (
    PatientProfileRow,
    SqlPatientRegistry,
)
from clinic_ecosystem.infrastructure.persistence.uow import SqlAlchemyUnitOfWork

_MAX_DOSSIER = 64


@dataclass(frozen=True, slots=True)
class PatientChanges:
    fields_set: frozenset[str]
    first_name: str | None = None
    last_name: str | None = None
    birth_date: date | None = None
    dossier_number: str | None = None
    is_active: bool | None = None


def validate_changes(changes: PatientChanges) -> dict[str, Any]:
    """Normalize requested changes; raise ValidationFailed for invalid input."""
    out: dict[str, Any] = {}
    for name in ("first_name", "last_name"):
        if name in changes.fields_set:
            value = (getattr(changes, name) or "").strip()
            if not value or len(value) > 120:
                raise ValidationFailed(f"{name} must be 1-120 characters")
            out[name] = value
    if "birth_date" in changes.fields_set:
        value = changes.birth_date
        if value is not None and value > datetime.now(timezone.utc).date():
            raise ValidationFailed("birth_date cannot be in the future")
        out["birth_date"] = value
    if "dossier_number" in changes.fields_set:
        raw = (changes.dossier_number or "").strip()
        if len(raw) > _MAX_DOSSIER:
            raise ValidationFailed("dossier_number is too long")
        out["dossier_number"] = raw or None
    if "is_active" in changes.fields_set:
        if changes.is_active is None:
            raise ValidationFailed("is_active must be true or false")
        out["is_active"] = changes.is_active
    return out


class PatientRegistryService:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow
        self._registry = SqlPatientRegistry(uow.session)
        self._audit = SqlAuditStore(uow.session)

    async def require(self, actor: Actor, patient_profile_id: UUID) -> PatientProfileRow:
        row = await self._registry.get(
            tenant_id=actor.tenant_id, patient_profile_id=patient_profile_id
        )
        if row is None:
            raise NotFound("Patient not found", code="patient_not_found")
        return row

    async def update(
        self,
        actor: Actor,
        granted: set[str],
        patient_profile_id: UUID,
        expected_version: int,
        changes: PatientChanges,
    ) -> PatientProfileRow:
        normalized = validate_changes(changes)
        profile_fields = {"first_name", "last_name", "birth_date", "dossier_number"}
        if profile_fields & normalized.keys() and perm.PATIENTS_UPDATE not in granted:
            raise Forbidden("Permission denied", code="permission_denied")
        if "is_active" in normalized and perm.PATIENTS_SET_ACTIVE not in granted:
            raise Forbidden("Permission denied", code="permission_denied")

        current = await self.require(actor, patient_profile_id)
        await self._registry.lock_person(tenant_id=actor.tenant_id, person_id=current.person_id)
        current = await self.require(actor, patient_profile_id)
        if current.aggregate_version != expected_version:
            raise PreconditionFailed(
                "Patient was modified by someone else",
                extra={"current_version": current.aggregate_version},
            )

        changed = [
            name
            for name, value in normalized.items()
            if getattr(current, name) != value
        ]
        if not changed:
            return current

        if "dossier_number" in changed and normalized["dossier_number"]:
            await self._registry.lock_dossier_namespace(actor.tenant_id)
            if await self._registry.dossier_in_use(
                tenant_id=actor.tenant_id,
                dossier_number=normalized["dossier_number"],
                exclude_profile_id=patient_profile_id,
            ):
                raise Conflict("Dossier number is already in use", code="dossier_in_use")

        now = datetime.now(timezone.utc)
        new_version = await self._registry.bump_person(
            tenant_id=actor.tenant_id,
            person_id=current.person_id,
            expected_version=expected_version,
            fields={k: v for k, v in normalized.items() if k in {"first_name", "last_name", "birth_date"}},
            now=now,
        )
        if new_version is None:
            raise PreconditionFailed("Patient was modified by someone else")
        await self._registry.update_profile(
            tenant_id=actor.tenant_id,
            patient_profile_id=patient_profile_id,
            dossier_number=normalized.get("dossier_number"),
            set_dossier="dossier_number" in changed,
            is_active=normalized.get("is_active") if "is_active" in changed else None,
        )
        operation = "patient.updated"
        if changed == ["is_active"]:
            operation = "patient.activated" if normalized["is_active"] else "patient.deactivated"
        await self._audit.append(
            tenant_id=actor.tenant_id,
            actor_type="USER_ACCOUNT",
            actor_id=actor.account_id,
            operation=operation,
            target_type="patient_profile",
            target_id=patient_profile_id,
            details={
                "changed_fields": sorted(changed),
                "from_version": expected_version,
                "to_version": new_version,
            },
        )
        return await self.require(actor, patient_profile_id)

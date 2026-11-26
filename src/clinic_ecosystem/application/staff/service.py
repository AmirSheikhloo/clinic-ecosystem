"""Staff directory use cases (Workstream B)."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from clinic_ecosystem.application.auth.service import normalize_login_identifier
from clinic_ecosystem.application.shared.actor import Actor
from clinic_ecosystem.application.shared.errors import (
    Conflict,
    Forbidden,
    NotFound,
    PreconditionFailed,
    ValidationFailed,
)
from clinic_ecosystem.domain.access import permissions as perm
from clinic_ecosystem.infrastructure.auth.passwords import hash_password
from clinic_ecosystem.infrastructure.persistence.audit import SqlAuditStore
from clinic_ecosystem.infrastructure.persistence.staff_registry import SqlStaffRegistry, StaffRow
from clinic_ecosystem.infrastructure.persistence.uow import SqlAlchemyUnitOfWork
from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7

STAFF_KINDS = ("DOCTOR", "SPECIALIST", "RECEPTIONIST", "NURSE", "TECHNICIAN", "OTHER")
_LOGIN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._@+-]{2,253}$")
MIN_PASSWORD = 12
MAX_PASSWORD = 128


@dataclass(frozen=True, slots=True)
class LoginSpec:
    login_identifier: str
    password: str = ""


@dataclass(frozen=True, slots=True)
class NewStaff:
    first_name: str
    last_name: str
    staff_kind: str
    medical_council_code: str | None = None
    birth_date: date | None = None
    login: LoginSpec | None = None


def _name(value: str | None, field: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned or len(cleaned) > 120:
        raise ValidationFailed(f"{field} must be 1-120 characters")
    return cleaned


def _kind(value: str) -> str:
    if value not in STAFF_KINDS:
        raise ValidationFailed("Unsupported staff kind", code="staff_kind_invalid")
    return value


def _council(value: str | None) -> str | None:
    cleaned = (value or "").strip()
    if len(cleaned) > 64:
        raise ValidationFailed("medical_council_code is too long")
    return cleaned or None


def validate_login(spec: LoginSpec) -> tuple[str, str]:
    login = spec.login_identifier.strip()
    if not _LOGIN.match(login):
        raise ValidationFailed("Login identifier format is invalid", code="login_invalid")
    if not (MIN_PASSWORD <= len(spec.password) <= MAX_PASSWORD):
        raise ValidationFailed(
            f"Password must be {MIN_PASSWORD}-{MAX_PASSWORD} characters",
            code="password_policy",
        )
    if spec.password.lower() == login.lower():
        raise ValidationFailed("Password must differ from the login", code="password_policy")
    return login, normalize_login_identifier(login)


class StaffService:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow
        self._staff = SqlStaffRegistry(uow.session)
        self._audit = SqlAuditStore(uow.session)

    async def require(self, actor: Actor, staff_profile_id: UUID) -> StaffRow:
        row = await self._staff.get(tenant_id=actor.tenant_id, staff_profile_id=staff_profile_id)
        if row is None:
            raise NotFound("Staff profile not found", code="staff_not_found")
        return row

    async def _provision(
        self, actor: Actor, person_id: UUID, spec: LoginSpec, now: datetime
    ) -> UUID:
        login, normalized = validate_login(spec)
        if await self._staff.login_exists(tenant_id=actor.tenant_id, normalized=normalized):
            raise Conflict("Login identifier is already taken", code="login_identifier_taken")
        password_hash = await asyncio.to_thread(hash_password, spec.password)
        account_id = new_uuid7()
        try:
            await self._staff.insert_account(
                tenant_id=actor.tenant_id,
                account_id=account_id,
                person_id=person_id,
                login_identifier=login,
                normalized_login=normalized,
                password_hash=password_hash,
                now=now,
            )
        except IntegrityError as exc:
            raise Conflict(
                "Login identifier is already taken", code="login_identifier_taken"
            ) from exc
        await self._audit.append(
            tenant_id=actor.tenant_id,
            actor_type="USER_ACCOUNT",
            actor_id=actor.account_id,
            operation="account.provisioned",
            target_type="user_account",
            target_id=account_id,
            details={"person_id": str(person_id), "roles_granted": []},
        )
        return account_id

    async def create(self, actor: Actor, granted: set[str], data: NewStaff) -> dict[str, Any]:
        if data.login is not None and perm.STAFF_PROVISION_LOGIN not in granted:
            raise Forbidden("Permission denied", code="permission_denied")
        first = _name(data.first_name, "first_name")
        last = _name(data.last_name, "last_name")
        kind = _kind(data.staff_kind)
        council = _council(data.medical_council_code)
        if data.login is not None:
            validate_login(data.login)
        now = datetime.now(timezone.utc)
        person_id, staff_id = new_uuid7(), new_uuid7()
        await self._staff.insert_person(
            tenant_id=actor.tenant_id,
            person_id=person_id,
            first_name=first,
            last_name=last,
            birth_date=data.birth_date,
            now=now,
        )
        await self._staff.insert_profile(
            tenant_id=actor.tenant_id,
            staff_profile_id=staff_id,
            person_id=person_id,
            staff_kind=kind,
            medical_council_code=council,
            now=now,
        )
        await self._audit.append(
            tenant_id=actor.tenant_id,
            actor_type="USER_ACCOUNT",
            actor_id=actor.account_id,
            operation="staff.created",
            target_type="staff_profile",
            target_id=staff_id,
            details={"staff_kind": kind, "login_requested": data.login is not None},
        )
        account_id = None
        if data.login is not None:
            account_id = await self._provision(actor, person_id, data.login, now)
        return {
            "staff_profile_id": str(staff_id),
            "person_id": str(person_id),
            "account_id": str(account_id) if account_id else None,
        }

    async def provision_login(
        self, actor: Actor, staff_profile_id: UUID, spec: LoginSpec
    ) -> dict[str, Any]:
        row = await self.require(actor, staff_profile_id)
        if row.account_id is not None:
            raise Conflict("Staff member already has a login account", code="account_exists")
        account_id = await self._provision(
            actor, row.person_id, spec, datetime.now(timezone.utc)
        )
        return {"staff_profile_id": str(staff_profile_id), "account_id": str(account_id)}

    async def update(
        self,
        actor: Actor,
        staff_profile_id: UUID,
        expected_version: int,
        fields: dict[str, Any],
    ) -> StaffRow:
        clean: dict[str, Any] = {}
        if "first_name" in fields:
            clean["first_name"] = _name(fields["first_name"], "first_name")
        if "last_name" in fields:
            clean["last_name"] = _name(fields["last_name"], "last_name")
        if "staff_kind" in fields:
            clean["staff_kind"] = _kind(fields["staff_kind"])
        if "medical_council_code" in fields:
            clean["medical_council_code"] = _council(fields["medical_council_code"])
        if "is_active" in fields:
            if not isinstance(fields["is_active"], bool):
                raise ValidationFailed("is_active must be true or false")
            clean["is_active"] = fields["is_active"]

        current = await self.require(actor, staff_profile_id)
        await self._staff.lock_person(tenant_id=actor.tenant_id, person_id=current.person_id)
        current = await self.require(actor, staff_profile_id)
        if current.aggregate_version != expected_version:
            raise PreconditionFailed(
                "Staff profile was modified by someone else",
                extra={"current_version": current.aggregate_version},
            )
        changed = sorted(k for k, v in clean.items() if getattr(current, k) != v)
        if not changed:
            return current
        new_version = await self._staff.update_person_cas(
            tenant_id=actor.tenant_id,
            person_id=current.person_id,
            expected_version=expected_version,
            first_name=clean.get("first_name"),
            last_name=clean.get("last_name"),
            now=datetime.now(timezone.utc),
        )
        if new_version is None:
            raise PreconditionFailed("Staff profile was modified by someone else")
        await self._staff.update_profile(
            tenant_id=actor.tenant_id,
            staff_profile_id=staff_profile_id,
            staff_kind=clean.get("staff_kind") if "staff_kind" in changed else None,
            medical_council_code=clean.get("medical_council_code"),
            set_council="medical_council_code" in changed,
            is_active=clean.get("is_active") if "is_active" in changed else None,
        )
        operation = "staff.updated"
        if changed == ["is_active"]:
            operation = "staff.activated" if clean["is_active"] else "staff.deactivated"
        await self._audit.append(
            tenant_id=actor.tenant_id,
            actor_type="USER_ACCOUNT",
            actor_id=actor.account_id,
            operation=operation,
            target_type="staff_profile",
            target_id=staff_profile_id,
            details={"changed_fields": changed, "from_version": expected_version,
                     "to_version": new_version},
        )
        return await self.require(actor, staff_profile_id)

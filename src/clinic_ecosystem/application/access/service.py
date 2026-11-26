"""Role, account-status and governance administration (Workstream C).

Anti-escalation invariants, enforced server-side for every mutation:
* an actor can only grant/revoke permissions it holds itself,
* an actor cannot change its own roles, governance or account status,
* system-defined roles are immutable through this API,
* owner-level governance is assignable only by an owner.
"""

from __future__ import annotations

from datetime import datetime, timezone
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
from clinic_ecosystem.domain.access import rules
from clinic_ecosystem.domain.access.permissions import PERMISSION_CATALOG
from clinic_ecosystem.infrastructure.persistence.access_admin import SqlAccessAdmin
from clinic_ecosystem.infrastructure.persistence.audit import SqlAuditStore
from clinic_ecosystem.infrastructure.persistence.permissions import SqlPermissionService
from clinic_ecosystem.infrastructure.persistence.uow import SqlAlchemyUnitOfWork
from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7


def _escalation(missing: set[str]) -> Forbidden:
    return Forbidden(
        "Actor cannot grant or revoke permissions it does not hold",
        code="privilege_escalation_denied",
        extra={"permissions": sorted(missing)},
    )


class AccessService:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._uow = uow
        self._admin = SqlAccessAdmin(uow.session)
        self._audit = SqlAuditStore(uow.session)
        self._perms = SqlPermissionService(uow.session)

    async def _audit_entry(
        self, actor: Actor, operation: str, target_type: str, target_id: UUID, details: dict[str, Any]
    ) -> None:
        await self._audit.append(
            tenant_id=actor.tenant_id,
            actor_type="USER_ACCOUNT",
            actor_id=actor.account_id,
            operation=operation,
            target_type=target_type,
            target_id=target_id,
            details=details,
        )

    async def _actor_governance(self, actor: Actor) -> set[str]:
        return await self._perms.governance_roles(
            tenant_id=actor.tenant_id, person_id=actor.person_id
        )

    async def _guard_target_account(
        self, actor: Actor, granted: set[str], account: dict[str, Any]
    ) -> None:
        """Common protection for operations on another account."""
        if account["account_id"] == actor.account_id:
            raise Forbidden("Self-service change is not allowed", code="self_change_denied")
        target_gov = await self._admin.person_governance(
            tenant_id=actor.tenant_id, person_id=account["person_id"]
        )
        if "CLINIC_OWNER" in target_gov and "CLINIC_OWNER" not in await self._actor_governance(actor):
            raise Forbidden("Owner accounts are protected", code="owner_protected")
        target_perms = await self._perms.effective_permissions(
            tenant_id=actor.tenant_id, principal_id=account["account_id"]
        )
        missing = rules.ungrantable(granted, target_perms)
        if missing:
            raise _escalation(missing)

    # -- roles ---------------------------------------------------------------

    async def create_role(
        self, actor: Actor, granted: set[str], code: str, name: str, permissions: list[str]
    ) -> UUID:
        problem = rules.validate_role_code(code)
        if problem:
            raise ValidationFailed(problem, code="role_code_invalid")
        name = name.strip()
        if not name or len(name) > 120:
            raise ValidationFailed("Role name must be 1-120 characters")
        wanted = self._validate_codes(permissions)
        missing = rules.ungrantable(granted, wanted)
        if missing:
            raise _escalation(missing)
        existing = {r["role_code"] for r in await self._admin.list_roles(tenant_id=actor.tenant_id)}
        if code in existing:
            raise Conflict("Role code already exists", code="role_code_taken")
        now = datetime.now(timezone.utc)
        role_id = new_uuid7()
        await self._admin.insert_role(
            tenant_id=actor.tenant_id, role_id=role_id, code=code, name=name, now=now
        )
        await self._admin.replace_role_permissions(
            tenant_id=actor.tenant_id, role_id=role_id, add=wanted, remove=set(), now=now
        )
        await self._audit_entry(
            actor, "role.created", "tenant_role", role_id,
            {"role_code": code, "permissions": sorted(wanted)},
        )
        return role_id

    @staticmethod
    def _validate_codes(codes: list[str]) -> set[str]:
        unknown = {c for c in codes if c not in PERMISSION_CATALOG}
        if unknown:
            raise ValidationFailed(
                "Unknown permission code", code="permission_unknown",
                extra={"permissions": sorted(unknown)},
            )
        return set(codes)

    async def _mutable_role(self, actor: Actor, role_id: UUID) -> dict[str, Any]:
        role = await self._admin.get_role(
            tenant_id=actor.tenant_id, role_id=role_id, for_update=True
        )
        if role is None:
            raise NotFound("Role not found", code="role_not_found")
        if role["is_system_defined"]:
            raise Forbidden("System-defined roles are immutable", code="system_role_immutable")
        return role

    async def set_role_permissions(
        self, actor: Actor, granted: set[str], role_id: UUID, permissions: list[str]
    ) -> dict[str, Any]:
        wanted = self._validate_codes(permissions)
        role = await self._mutable_role(actor, role_id)
        current = (
            await self._admin.role_permission_codes(tenant_id=actor.tenant_id, role_ids=[role_id])
        )[role_id]
        add, remove = wanted - current, current - wanted
        missing = rules.ungrantable(granted, add | remove)
        if missing:
            raise _escalation(missing)
        if add or remove:
            await self._admin.replace_role_permissions(
                tenant_id=actor.tenant_id, role_id=role_id, add=add, remove=remove,
                now=datetime.now(timezone.utc),
            )
            await self._audit_entry(
                actor, "role.permissions_changed", "tenant_role", role_id,
                {"role_code": role["role_code"], "added": sorted(add), "removed": sorted(remove)},
            )
        return {"role_id": str(role_id), "permissions": sorted(wanted)}

    async def delete_role(self, actor: Actor, role_id: UUID) -> None:
        role = await self._mutable_role(actor, role_id)
        if await self._admin.role_member_count(tenant_id=actor.tenant_id, role_id=role_id):
            raise Conflict("Role is still assigned to accounts", code="role_in_use")
        await self._admin.delete_role(tenant_id=actor.tenant_id, role_id=role_id)
        await self._audit_entry(
            actor, "role.deleted", "tenant_role", role_id, {"role_code": role["role_code"]}
        )

    # -- accounts ------------------------------------------------------------

    async def set_account_roles(
        self, actor: Actor, granted: set[str], account_id: UUID, role_ids: list[UUID]
    ) -> dict[str, Any]:
        account = await self._admin.get_account(
            tenant_id=actor.tenant_id, account_id=account_id, for_update=True
        )
        if account is None:
            raise NotFound("Account not found", code="account_not_found")
        await self._guard_target_account(actor, granted, account)
        wanted = set(role_ids)
        if wanted != await self._admin.existing_roles(
            tenant_id=actor.tenant_id, role_ids=sorted(wanted)
        ):
            raise ValidationFailed("Unknown role", code="role_unknown")
        current = await self._admin.account_role_ids(tenant_id=actor.tenant_id, account_id=account_id)
        add, remove = wanted - current, current - wanted
        if add or remove:
            perms = await self._admin.role_permission_codes(
                tenant_id=actor.tenant_id, role_ids=sorted(add | remove)
            )
            touched = set().union(*perms.values()) if perms else set()
            missing = rules.ungrantable(granted, touched)
            if missing:
                raise _escalation(missing)
            await self._admin.replace_account_roles(
                tenant_id=actor.tenant_id, account_id=account_id, add=add, remove=remove,
                now=datetime.now(timezone.utc),
            )
            await self._audit_entry(
                actor, "account.roles_changed", "user_account", account_id,
                {"added": sorted(map(str, add)), "removed": sorted(map(str, remove))},
            )
        return {"account_id": str(account_id), "role_ids": sorted(map(str, wanted))}

    async def set_account_active(
        self, actor: Actor, granted: set[str], account_id: UUID, expected_version: int, active: bool
    ) -> dict[str, Any]:
        account = await self._admin.get_account(
            tenant_id=actor.tenant_id, account_id=account_id, for_update=True
        )
        if account is None:
            raise NotFound("Account not found", code="account_not_found")
        await self._guard_target_account(actor, granted, account)
        if account["aggregate_version"] != expected_version:
            raise PreconditionFailed(
                "Account was modified by someone else",
                extra={"current_version": account["aggregate_version"]},
            )
        if account["is_active"] == active:
            return {"account_id": str(account_id), "is_active": active,
                    "aggregate_version": expected_version}
        version = await self._admin.set_account_active_cas(
            tenant_id=actor.tenant_id, account_id=account_id,
            expected_version=expected_version, active=active, now=datetime.now(timezone.utc),
        )
        if version is None:
            raise PreconditionFailed("Account was modified by someone else")
        await self._audit_entry(
            actor, "account.reactivated" if active else "account.suspended",
            "user_account", account_id,
            {"from_version": expected_version, "to_version": version},
        )
        return {"account_id": str(account_id), "is_active": active, "aggregate_version": version}

    # -- governance ----------------------------------------------------------

    async def set_governance(
        self, actor: Actor, person_id: UUID, roles: list[str]
    ) -> dict[str, Any]:
        wanted = set(roles)
        unknown = wanted - set(rules.GOVERNANCE_ROLES)
        if unknown:
            raise ValidationFailed("Unknown governance role", code="governance_role_unknown")
        if person_id == actor.person_id:
            raise Forbidden("Self-service change is not allowed", code="self_change_denied")
        if not await self._admin.person_exists(tenant_id=actor.tenant_id, person_id=person_id):
            raise NotFound("Person not found", code="person_not_found")
        await self._admin.lock_governance_namespace(actor.tenant_id)
        current = await self._admin.person_governance(
            tenant_id=actor.tenant_id, person_id=person_id
        )
        add, remove = wanted - current, current - wanted
        actor_gov = await self._actor_governance(actor)
        for role in add | remove:
            if not rules.governance_change_allowed(actor_gov, role):
                raise Forbidden(
                    "Governance role change requires a higher authority",
                    code="governance_authority_insufficient",
                )
        if "CLINIC_OWNER" in remove and await self._admin.count_governance_holders(
            tenant_id=actor.tenant_id, role="CLINIC_OWNER"
        ) <= 1:
            raise Conflict("The last clinic owner cannot be removed", code="last_owner")
        if add or remove:
            await self._admin.replace_governance(
                tenant_id=actor.tenant_id, person_id=person_id, add=add, remove=remove,
                now=datetime.now(timezone.utc),
            )
            await self._audit_entry(
                actor, "governance.changed", "tenant_person", person_id,
                {"added": sorted(add), "removed": sorted(remove)},
            )
        return {"person_id": str(person_id), "roles": sorted(wanted)}

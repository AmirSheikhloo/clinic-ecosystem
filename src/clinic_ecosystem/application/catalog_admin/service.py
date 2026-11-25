"""Services and resources administration (Workstream E, manager-only)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from clinic_ecosystem.application.shared.actor import Actor
from clinic_ecosystem.application.shared.errors import (
    Conflict,
    NotFound,
    PreconditionFailed,
    ValidationFailed,
)
from clinic_ecosystem.infrastructure.persistence.audit import SqlAuditStore
from clinic_ecosystem.infrastructure.persistence.catalog_admin import SqlCatalogAdmin
from clinic_ecosystem.infrastructure.persistence.uow import SqlAlchemyUnitOfWork
from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7

RESOURCE_TYPES = ("PRACTITIONER", "ROOM", "DEVICE")
MAX_DURATION_MINUTES = 720
MAX_PRICE_IRR = 10**12
MAX_REQUIREMENTS = 20


def _text(value: str | None, field: str, limit: int, *, required: bool) -> str | None:
    cleaned = (value or "").strip()
    if not cleaned:
        if required:
            raise ValidationFailed(f"{field} is required")
        return None
    if len(cleaned) > limit:
        raise ValidationFailed(f"{field} is too long")
    return cleaned


def _int(value: Any, field: str, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not (low <= value <= high):
        raise ValidationFailed(f"{field} must be an integer between {low} and {high}")
    return value


def clean_service_fields(fields: dict[str, Any], *, creating: bool) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if creating or "service_name" in fields:
        out["service_name"] = _text(fields.get("service_name"), "service_name", 200, required=True)
    if "service_code" in fields:
        out["service_code"] = _text(fields["service_code"], "service_code", 64, required=False)
    if creating or "default_duration_minutes" in fields:
        out["default_duration_minutes"] = _int(
            fields.get("default_duration_minutes"), "default_duration_minutes", 1, MAX_DURATION_MINUTES
        )
    if creating or "default_price_irr" in fields:
        out["default_price_irr"] = _int(
            fields.get("default_price_irr"), "default_price_irr", 0, MAX_PRICE_IRR
        )
    if "is_active" in fields:
        if not isinstance(fields["is_active"], bool):
            raise ValidationFailed("is_active must be true or false")
        out["is_active"] = fields["is_active"]
    return out


class CatalogAdminService:
    def __init__(self, uow: SqlAlchemyUnitOfWork) -> None:
        self._catalog = SqlCatalogAdmin(uow.session)
        self._audit = SqlAuditStore(uow.session)

    async def _audit_entry(self, actor: Actor, op: str, target: str, target_id: UUID, details: dict) -> None:
        await self._audit.append(
            tenant_id=actor.tenant_id, actor_type="USER_ACCOUNT", actor_id=actor.account_id,
            operation=op, target_type=target, target_id=target_id, details=details,
        )

    async def create_service(self, actor: Actor, fields: dict[str, Any]) -> dict[str, Any]:
        clean = clean_service_fields(fields, creating=True)
        await self._catalog.lock_namespace(actor.tenant_id)
        code = clean.get("service_code")
        if code and await self._catalog.code_in_use(tenant_id=actor.tenant_id, code=code, exclude_id=None):
            raise Conflict("Service code is already in use", code="service_code_taken")
        service_id = new_uuid7()
        await self._catalog.insert_service(
            tenant_id=actor.tenant_id, service_id=service_id, code=code,
            name=clean["service_name"], duration=clean["default_duration_minutes"],
            price=clean["default_price_irr"], now=datetime.now(timezone.utc),
        )
        await self._audit_entry(actor, "service.created", "service", service_id,
                                {"duration": clean["default_duration_minutes"],
                                 "price_irr": clean["default_price_irr"]})
        return {"service_id": str(service_id), "aggregate_version": 1}

    async def update_service(
        self, actor: Actor, service_id: UUID, expected_version: int, fields: dict[str, Any]
    ) -> dict[str, Any]:
        clean = clean_service_fields(fields, creating=False)
        await self._catalog.lock_namespace(actor.tenant_id)
        current = await self._catalog.get_service(
            tenant_id=actor.tenant_id, service_id=service_id, for_update=True
        )
        if current is None:
            raise NotFound("Service not found", code="service_not_found")
        if current["aggregate_version"] != expected_version:
            raise PreconditionFailed("Service was modified by someone else",
                                     extra={"current_version": current["aggregate_version"]})
        changed = sorted(k for k, v in clean.items() if current[k] != v)
        if not changed:
            return {"service_id": str(service_id), "aggregate_version": expected_version}
        code = clean.get("service_code")
        if "service_code" in changed and code and await self._catalog.code_in_use(
            tenant_id=actor.tenant_id, code=code, exclude_id=service_id
        ):
            raise Conflict("Service code is already in use", code="service_code_taken")
        version = await self._catalog.update_service_cas(
            tenant_id=actor.tenant_id, service_id=service_id, expected_version=expected_version,
            fields=clean, now=datetime.now(timezone.utc),
        )
        if version is None:
            raise PreconditionFailed("Service was modified by someone else")
        op = "service.updated"
        if changed == ["is_active"]:
            op = "service.activated" if clean["is_active"] else "service.deactivated"
        await self._audit_entry(actor, op, "service", service_id,
                                {"changed_fields": changed, "from_version": expected_version,
                                 "to_version": version})
        return {"service_id": str(service_id), "aggregate_version": version}

    async def replace_requirements(
        self, actor: Actor, service_id: UUID, expected_version: int, items: list[dict[str, Any]]
    ) -> dict[str, Any]:
        if len(items) > MAX_REQUIREMENTS:
            raise ValidationFailed("Too many requirements")
        cleaned: list[dict[str, Any]] = []
        for item in items:
            rtype = item.get("required_resource_type")
            if rtype not in RESOURCE_TYPES:
                raise ValidationFailed("Unsupported resource type", code="resource_type_invalid")
            cleaned.append({
                "requirement_group": _text(item.get("requirement_group"), "requirement_group", 64, required=True),
                "required_resource_type": rtype,
                "specific_resource_id": item.get("specific_resource_id"),
                "quantity_required": _int(item.get("quantity_required"), "quantity_required", 1, 20),
            })
        for item in cleaned:
            specific = item["specific_resource_id"]
            if specific is None:
                continue
            resource = await self._catalog.get_resource(tenant_id=actor.tenant_id, resource_id=specific)
            if resource is None:
                raise ValidationFailed("Specific resource not found", code="resource_not_found")
            if resource["resource_type"] != item["required_resource_type"]:
                raise ValidationFailed("Specific resource type mismatch", code="resource_type_mismatch")
            if item["quantity_required"] != 1:
                raise ValidationFailed("A specific resource requires quantity 1", code="quantity_invalid")
        current = await self._catalog.get_service(
            tenant_id=actor.tenant_id, service_id=service_id, for_update=True
        )
        if current is None:
            raise NotFound("Service not found", code="service_not_found")
        if current["aggregate_version"] != expected_version:
            raise PreconditionFailed("Service was modified by someone else",
                                     extra={"current_version": current["aggregate_version"]})
        now = datetime.now(timezone.utc)
        await self._catalog.replace_requirements(
            tenant_id=actor.tenant_id, service_id=service_id, items=cleaned,
            ids=[new_uuid7() for _ in cleaned], now=now,
        )
        version = await self._catalog.update_service_cas(
            tenant_id=actor.tenant_id, service_id=service_id, expected_version=expected_version,
            fields={}, now=now,
        )
        if version is None:
            raise PreconditionFailed("Service was modified by someone else")
        await self._audit_entry(actor, "service.requirements_replaced", "service", service_id,
                                {"requirement_count": len(cleaned), "to_version": version})
        return {"service_id": str(service_id), "aggregate_version": version}

    async def create_resource(self, actor: Actor, resource_type: str, name: str) -> dict[str, Any]:
        if resource_type not in RESOURCE_TYPES:
            raise ValidationFailed("Unsupported resource type", code="resource_type_invalid")
        cleaned = _text(name, "resource_name", 200, required=True)
        resource_id = new_uuid7()
        await self._catalog.insert_resource(
            tenant_id=actor.tenant_id, resource_id=resource_id, resource_type=resource_type,
            name=cleaned, now=datetime.now(timezone.utc),
        )
        await self._audit_entry(actor, "resource.created", "bookable_resource", resource_id,
                                {"resource_type": resource_type})
        return {"resource_id": str(resource_id)}

    async def update_resource(
        self, actor: Actor, resource_id: UUID, fields: dict[str, Any]
    ) -> dict[str, Any]:
        name = _text(fields["resource_name"], "resource_name", 200, required=True) if "resource_name" in fields else None
        active = fields.get("is_active") if "is_active" in fields else None
        if "is_active" in fields and not isinstance(active, bool):
            raise ValidationFailed("is_active must be true or false")
        current = await self._catalog.get_resource(
            tenant_id=actor.tenant_id, resource_id=resource_id, for_update=True
        )
        if current is None:
            raise NotFound("Resource not found", code="resource_not_found")
        changed = []
        if name is not None and name != current["resource_name"]:
            changed.append("resource_name")
        if active is not None and active != current["is_active"]:
            changed.append("is_active")
        if changed:
            await self._catalog.update_resource(
                tenant_id=actor.tenant_id, resource_id=resource_id,
                name=name if "resource_name" in changed else None,
                is_active=active if "is_active" in changed else None,
            )
            future = 0
            if active is False:
                future = await self._catalog.future_allocation_count(
                    tenant_id=actor.tenant_id, resource_id=resource_id,
                    now=datetime.now(timezone.utc),
                )
            await self._audit_entry(
                actor, "resource.updated", "bookable_resource", resource_id,
                {"changed_fields": changed, "future_allocations": future},
            )
        return {"resource_id": str(resource_id)}

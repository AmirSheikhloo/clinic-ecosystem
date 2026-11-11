"""Ports used by ScheduleAppointmentHandler (implemented in infrastructure)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from clinic_ecosystem.domain.scheduling.conflicts import OverlapConflictFact
from clinic_ecosystem.domain.scheduling.model import Appointment, ResourceAllocationRequest


class UnitOfWork(Protocol):
    async def __aenter__(self) -> UnitOfWork: ...

    async def __aexit__(self, exc_type, exc, tb) -> None: ...

    async def bind_tenant(self, tenant_id: UUID) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...

    async def flush(self) -> None: ...


class IdempotencyStore(Protocol):
    async def claim(
        self,
        *,
        tenant_id: UUID,
        principal_id: UUID,
        operation_scope: str,
        idempotency_key: str,
        request_fingerprint: str,
        owner_token: UUID,
    ) -> dict[str, Any]: ...

    async def complete(
        self,
        *,
        tenant_id: UUID,
        principal_id: UUID,
        operation_scope: str,
        idempotency_key: str,
        owner_token: UUID,
        response_payload: dict[str, Any],
    ) -> None: ...


class AppointmentRepository(Protocol):
    async def lock_resources(self, tenant_id: UUID, resource_ids: list[UUID]) -> None: ...

    async def get_service_requirements(
        self, tenant_id: UUID, service_id: UUID
    ) -> list[dict[str, Any]]: ...

    async def get_resource_types(
        self, tenant_id: UUID, resource_ids: list[UUID]
    ) -> dict[UUID, str]: ...

    async def discover_overlapping_appointment_ids(
        self,
        *,
        tenant_id: UUID,
        resource_ids: list[UUID],
        start_at_utc: datetime,
        end_at_utc: datetime,
    ) -> list[UUID]: ...

    async def lock_appointments(
        self, tenant_id: UUID, appointment_ids: list[UUID]
    ) -> None: ...

    async def lock_allocations_for_appointments(
        self, tenant_id: UUID, appointment_ids: list[UUID]
    ) -> None: ...

    async def find_overlap_facts(
        self,
        *,
        tenant_id: UUID,
        resource_ids: list[UUID],
        start_at_utc: datetime,
        end_at_utc: datetime,
    ) -> list[OverlapConflictFact]: ...

    async def expire_conflicting_holds(
        self,
        *,
        tenant_id: UUID,
        resource_ids: list[UUID],
        start_at_utc: datetime,
        end_at_utc: datetime,
        now_utc: datetime,
    ) -> list[UUID]: ...

    async def add(self, appointment: Appointment) -> None: ...

    async def enqueue_hold_expiry(
        self,
        *,
        tenant_id: UUID,
        appointment_id: UUID,
        due_at_utc: datetime,
    ) -> None: ...


class PatientDisplayDirectory(Protocol):
    """Authorized display-safe patient names from tenant_persons operational name fields."""

    async def display_safe_names(
        self, *, tenant_id: UUID, patient_ids: list[UUID]
    ) -> dict[UUID, str]: ...


class OutboxStore(Protocol):
    async def stage(self, *, tenant_id: UUID, message_type: str, payload: dict[str, Any]) -> None: ...


class AuditStore(Protocol):
    async def append(
        self,
        *,
        tenant_id: UUID,
        actor_type: str,
        actor_id: UUID | None,
        operation: str,
        target_type: str,
        target_id: UUID | None,
        details: dict[str, Any],
    ) -> None: ...


class PermissionService(Protocol):
    async def principal_has(
        self, *, tenant_id: UUID, principal_id: UUID, permission_code: str
    ) -> bool: ...


def validate_resource_set(
    requirements: list[dict[str, Any]],
    resource_types: dict[UUID, str],
    resource_ids: list[UUID],
) -> list[ResourceAllocationRequest]:
    from clinic_ecosystem.application.scheduling.exceptions import ServiceRequirementsNotMet

    if not requirements:
        return [
            ResourceAllocationRequest(resource_id=rid, resource_type=resource_types[rid])
            for rid in resource_ids
        ]

    remaining = list(resource_ids)
    for req in requirements:
        qty = int(req["quantity_required"])
        rtype = req["required_resource_type"]
        specific = req.get("specific_resource_id")
        matched: list[UUID] = []
        for rid in list(remaining):
            if specific is not None and rid != specific:
                continue
            if resource_types.get(rid) != rtype:
                continue
            matched.append(rid)
            remaining.remove(rid)
            if len(matched) == qty:
                break
        if len(matched) < qty:
            raise ServiceRequirementsNotMet(
                f"requirement group {req.get('requirement_group')} unmet for type {rtype}"
            )
    if remaining:
        raise ServiceRequirementsNotMet("extra resources not mapped to requirements")
    return [
        ResourceAllocationRequest(resource_id=rid, resource_type=resource_types[rid])
        for rid in resource_ids
    ]

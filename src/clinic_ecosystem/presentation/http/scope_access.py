"""Object-level scope authorization helpers for HTTP handlers."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status

from clinic_ecosystem.infrastructure.persistence.permissions import (
    PermissionScope,
    SqlPermissionService,
)
from clinic_ecosystem.infrastructure.persistence.uow import SqlAlchemyUnitOfWork
from clinic_ecosystem.presentation.http.dependencies import AuthenticatedPrincipal


async def load_scopes(
    principal: AuthenticatedPrincipal,
    uow: SqlAlchemyUnitOfWork,
    permission_code: str,
) -> list[PermissionScope]:
    return await SqlPermissionService(uow.session).permission_scopes(
        tenant_id=principal.claims.tenant_id,
        principal_id=principal.claims.principal_id,
        permission_code=permission_code,
    )


def deny() -> None:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"error": "permission_denied", "message": "Permission denied"},
    )


def require_object_scope(
    scopes: list[PermissionScope],
    *,
    department_id: UUID | None = None,
    service_id: UUID | None = None,
    provider_resource_id: UUID | None = None,
) -> None:
    """Fail closed when scopes empty or object dimensions do not match FILTER/ALL."""
    svc = SqlPermissionService(session=None)  # type: ignore[arg-type]
    if not svc.allows(
        scopes,
        department_id=department_id,
        service_id=service_id,
        provider_resource_id=provider_resource_id,
    ):
        deny()


def filter_rows_by_scope(
    scopes: list[PermissionScope],
    rows: list[dict],
    *,
    department_key: str = "department_id",
    service_key: str = "service_id",
    provider_key: str = "provider_resource_id",
) -> list[dict]:
    """Post-filter rows after a tenant query when SQL pushdown is not available."""
    svc = SqlPermissionService(session=None)  # type: ignore[arg-type]
    if not scopes:
        return []
    if svc.is_unrestricted(scopes):
        return rows
    out: list[dict] = []
    for row in rows:
        if svc.allows(
            scopes,
            department_id=row.get(department_key),
            service_id=row.get(service_key),
            provider_resource_id=row.get(provider_key),
        ):
            out.append(row)
    return out


def scope_department_ids(scopes: list[PermissionScope]) -> set[UUID] | None:
    """None ⇒ unrestricted; empty set ⇒ deny; else allowed department IDs.

    FILTER rows that do not constrain department imply all departments for that
    dimension — represented as None (unrestricted) when any such FILTER exists
    without an ALL grant already covering everything.
    """
    svc = SqlPermissionService(session=None)  # type: ignore[arg-type]
    if not scopes:
        return set()
    if svc.is_unrestricted(scopes):
        return None
    filters = svc.filter_scopes(scopes)
    if any(s.department_id is None for s in filters):
        return None
    return {s.department_id for s in filters if s.department_id is not None}


def scope_service_ids(scopes: list[PermissionScope]) -> set[UUID] | None:
    svc = SqlPermissionService(session=None)  # type: ignore[arg-type]
    if not scopes:
        return set()
    if svc.is_unrestricted(scopes):
        return None
    filters = svc.filter_scopes(scopes)
    if any(s.service_id is None for s in filters):
        return None
    return {s.service_id for s in filters if s.service_id is not None}

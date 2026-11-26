"""Shared HTTP helpers: actor resolution, permission loading and problem responses."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse

from clinic_ecosystem.application.shared.actor import Actor
from clinic_ecosystem.application.shared.errors import AppError
from clinic_ecosystem.application.shared.preconditions import etag
from clinic_ecosystem.infrastructure.persistence.permissions import SqlPermissionService
from clinic_ecosystem.infrastructure.persistence.uow import SqlAlchemyUnitOfWork
from clinic_ecosystem.presentation.http.dependencies import AuthenticatedPrincipal


def actor_of(principal: AuthenticatedPrincipal) -> Actor:
    return Actor(
        tenant_id=principal.claims.tenant_id,
        account_id=principal.account.id,
        person_id=principal.account.person_id,
    )


async def load_granted(
    principal: AuthenticatedPrincipal, uow: SqlAlchemyUnitOfWork
) -> set[str]:
    """Effective permission codes for the authenticated principal (server-side)."""
    return await SqlPermissionService(uow.session).effective_permissions(
        tenant_id=principal.claims.tenant_id,
        principal_id=principal.claims.principal_id,
    )


def require(granted: set[str], code: str) -> None:
    if code not in granted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "permission_denied", "message": "Permission denied"},
        )


def set_etag(response: Response, version: int) -> None:
    response.headers["ETag"] = etag(version)


def problem_body(exc: AppError) -> dict:
    return {
        "type": f"urn:clinic-ecosystem:problem:{exc.code}",
        "title": exc.code,
        "status": exc.status,
        "detail": exc.message,
        "error": exc.code,
        "message": exc.message,
        **exc.extra,
    }


def install_problem_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _handle(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            problem_body(exc),
            status_code=exc.status,
            media_type="application/problem+json",
        )

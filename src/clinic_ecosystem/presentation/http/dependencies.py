"""FastAPI dependencies: settings, DB session/UoW, authenticated principal."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from clinic_ecosystem.application.auth.exceptions import InvalidCredentials
from clinic_ecosystem.application.auth.service import AuthService
from clinic_ecosystem.infrastructure.auth.access_tokens import (
    AccessTokenClaims,
    AccessTokenError,
    validate_access_token,
)
from clinic_ecosystem.infrastructure.auth.settings import AuthSettings
from clinic_ecosystem.infrastructure.persistence.permissions import SqlPermissionService
from clinic_ecosystem.infrastructure.persistence.uow import SqlAlchemyUnitOfWork
from clinic_ecosystem.infrastructure.persistence.user_accounts import UserAccountRecord

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class AuthenticatedPrincipal:
    claims: AccessTokenClaims
    account: UserAccountRecord


def get_settings(request: Request) -> AuthSettings:
    settings = getattr(request.app.state, "auth_settings", None)
    if settings is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="auth settings are not configured",
        )
    return settings


def get_engine(request: Request) -> AsyncEngine:
    engine = getattr(request.app.state, "engine", None)
    if engine is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="database engine is not configured",
        )
    return engine


async def get_uow(
    engine: Annotated[AsyncEngine, Depends(get_engine)],
) -> AsyncIterator[SqlAlchemyUnitOfWork]:
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    session = factory()
    uow = SqlAlchemyUnitOfWork(session, owns_session=True)
    try:
        async with uow:
            yield uow
    finally:
        pass


def get_auth_service(
    settings: Annotated[AuthSettings, Depends(get_settings)],
) -> AuthService:
    return AuthService(settings=settings)


async def get_authenticated_principal(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    settings: Annotated[AuthSettings, Depends(get_settings)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
) -> AuthenticatedPrincipal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "authentication_required", "message": "Authentication required"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        claims = validate_access_token(credentials.credentials, settings=settings)
    except AccessTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_token", "message": "Invalid or expired token"},
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    # Never bind a client-forged tenant: only token claims after signature validation.
    try:
        account = await auth_service.load_active_account(
            uow=uow,
            tenant_id=claims.tenant_id,
            principal_id=claims.principal_id,
        )
    except InvalidCredentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_token", "message": "Invalid or expired token"},
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    # Stash for handlers that need the already-bound UoW / tenant.
    request.state.authenticated_tenant_id = claims.tenant_id
    return AuthenticatedPrincipal(claims=claims, account=account)


async def require_permission(
    permission_code: str,
    *,
    principal: AuthenticatedPrincipal,
    uow: SqlAlchemyUnitOfWork,
) -> None:
    # Tenant GUC must already be bound by get_authenticated_principal / load_active_account.
    permissions = SqlPermissionService(uow.session)
    allowed = await permissions.principal_has(
        tenant_id=principal.claims.tenant_id,
        principal_id=principal.claims.principal_id,
        permission_code=permission_code,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "permission_denied", "message": "Permission denied"},
        )


def verified_tenant_id(principal: AuthenticatedPrincipal) -> UUID:
    return principal.claims.tenant_id

"""Authentication HTTP routes for BETA-01A."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from clinic_ecosystem.application.auth.exceptions import (
    AccountUnavailable,
    AuthApplicationError,
    AuthRealmUnavailable,
    InvalidCredentials,
)
from clinic_ecosystem.application.auth.service import AuthService
from clinic_ecosystem.infrastructure.persistence.uow import SqlAlchemyUnitOfWork
from clinic_ecosystem.presentation.http.dependencies import (
    AuthenticatedPrincipal,
    get_auth_service,
    get_authenticated_principal,
    get_uow,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    login_identifier: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=1024)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    account_id: str
    tenant_id: str


class MeResponse(BaseModel):
    account_id: str
    tenant_id: str
    login_identifier: str
    is_active: bool


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)],
) -> LoginResponse:
    try:
        result = await auth_service.login(
            uow=uow,
            login_identifier=body.login_identifier,
            password=body.password,
        )
    except (InvalidCredentials, AccountUnavailable):
        # Generic response — do not distinguish unknown user / bad password / locked.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_credentials", "message": "Invalid credentials"},
        ) from None
    except AuthRealmUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": exc.code, "message": exc.message},
        ) from None
    except AuthApplicationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": exc.code, "message": exc.message},
        ) from None

    return LoginResponse(
        access_token=result.access_token,
        token_type=result.token_type,
        expires_in=result.expires_in,
        account_id=str(result.account.id),
        tenant_id=str(result.account.tenant_id),
    )


@router.get("/me", response_model=MeResponse)
async def me(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
) -> MeResponse:
    return MeResponse(
        account_id=str(principal.account.id),
        tenant_id=str(principal.account.tenant_id),
        login_identifier=principal.account.login_identifier,
        is_active=principal.account.is_active,
    )

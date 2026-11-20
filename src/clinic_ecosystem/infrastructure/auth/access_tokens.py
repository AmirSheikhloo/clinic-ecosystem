"""Short-lived signed access tokens for BETA-01A staff API.

Uses HS256 with an environment secret for the synthetic demo only.
Production deployments must migrate to RS256/ES256 per specification §246;
this module does not claim production cryptographic readiness.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import jwt

from clinic_ecosystem.infrastructure.auth.settings import AuthSettings, require_token_signing_secret
from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7


class AccessTokenError(ValueError):
    """Token missing, malformed, expired, or otherwise invalid."""


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    token_id: UUID
    principal_id: UUID
    tenant_id: UUID
    issued_at: datetime
    expires_at: datetime
    issuer: str
    audience: str


def issue_access_token(
    *,
    settings: AuthSettings,
    principal_id: UUID,
    tenant_id: UUID,
    now: datetime | None = None,
) -> tuple[str, AccessTokenClaims]:
    secret = require_token_signing_secret(settings)
    issued = now or datetime.now(timezone.utc)
    if issued.tzinfo is None:
        raise ValueError("now must be timezone-aware UTC")
    expires = issued + timedelta(seconds=settings.access_token_ttl_seconds)
    token_id = new_uuid7()
    payload: dict[str, Any] = {
        "jti": str(token_id),
        "sub": str(principal_id),
        "tid": str(tenant_id),
        "iss": settings.access_token_issuer,
        "aud": settings.access_token_audience,
        "iat": int(issued.timestamp()),
        "exp": int(expires.timestamp()),
    }
    token = jwt.encode(payload, secret, algorithm="HS256")
    claims = AccessTokenClaims(
        token_id=token_id,
        principal_id=principal_id,
        tenant_id=tenant_id,
        issued_at=issued,
        expires_at=expires,
        issuer=settings.access_token_issuer,
        audience=settings.access_token_audience,
    )
    return token, claims


def validate_access_token(token: str, *, settings: AuthSettings) -> AccessTokenClaims:
    secret = require_token_signing_secret(settings)
    if not token or not token.strip():
        raise AccessTokenError("missing token")
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience=settings.access_token_audience,
            issuer=settings.access_token_issuer,
            options={
                "require": ["exp", "iat", "iss", "aud", "sub", "jti", "tid"],
            },
        )
    except jwt.PyJWTError as exc:
        raise AccessTokenError("invalid token") from exc

    try:
        return AccessTokenClaims(
            token_id=UUID(str(payload["jti"])),
            principal_id=UUID(str(payload["sub"])),
            tenant_id=UUID(str(payload["tid"])),
            issued_at=datetime.fromtimestamp(int(payload["iat"]), tz=timezone.utc),
            expires_at=datetime.fromtimestamp(int(payload["exp"]), tz=timezone.utc),
            issuer=str(payload["iss"]),
            audience=str(payload["aud"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise AccessTokenError("invalid token claims") from exc

"""BETA-01A runtime settings for auth and the single-tenant login realm.

The pre-auth realm is a synthetic/dev-only bootstrap. It is disabled by default
and fails closed when configuration is missing, ambiguous, or multi-tenant.
It is NOT a production shared multi-tenant authentication solution.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from uuid import UUID

# Narrow permission used by GET /api/v1/catalog/services.
CATALOG_SERVICES_READ = "CATALOG_SERVICES_READ"

_DEFAULT_ISSUER = "clinic-ecosystem-beta-01a"
_DEFAULT_AUDIENCE = "clinic-ecosystem-staff-api"
_DEFAULT_TTL_SECONDS = 900
_ALLOWED_REALM_ENVS = frozenset({"test", "development"})


class AuthSettingsError(RuntimeError):
    """Raised when auth/realm configuration is unsafe or incomplete."""


@dataclass(frozen=True, slots=True)
class AuthSettings:
    clinic_env: str
    database_url: str
    access_token_signing_secret: str
    access_token_issuer: str
    access_token_audience: str
    access_token_ttl_seconds: int
    auth_realm_enabled: bool
    auth_realm_tenant_id: UUID | None
    max_failed_login_attempts: int
    lockout_minutes: int

    @property
    def is_realm_usable(self) -> bool:
        return (
            self.auth_realm_enabled
            and self.auth_realm_tenant_id is not None
            and self.clinic_env in _ALLOWED_REALM_ENVS
        )


def _truthy(raw: str | None) -> bool:
    return (raw or "").strip().lower() in {"1", "true", "yes", "on"}


def load_auth_settings(environ: dict[str, str] | None = None) -> AuthSettings:
    env = environ if environ is not None else os.environ
    clinic_env = (env.get("CLINIC_ENV") or "production").strip().lower()
    realm_enabled = _truthy(env.get("CLINIC_BETA_AUTH_REALM_ENABLED"))
    realm_raw = (env.get("CLINIC_BETA_AUTH_REALM_TENANT_ID") or "").strip()
    realm_tenant: UUID | None = None
    if realm_raw:
        try:
            realm_tenant = UUID(realm_raw)
        except ValueError as exc:
            raise AuthSettingsError(
                "CLINIC_BETA_AUTH_REALM_TENANT_ID must be a UUID"
            ) from exc

    secret = (env.get("CLINIC_ACCESS_TOKEN_SIGNING_SECRET") or "").strip()
    database_url = (env.get("CLINIC_DATABASE_URL") or "").strip()
    issuer = (env.get("CLINIC_ACCESS_TOKEN_ISSUER") or _DEFAULT_ISSUER).strip()
    audience = (env.get("CLINIC_ACCESS_TOKEN_AUDIENCE") or _DEFAULT_AUDIENCE).strip()
    ttl_raw = (env.get("CLINIC_ACCESS_TOKEN_TTL_SECONDS") or str(_DEFAULT_TTL_SECONDS)).strip()
    try:
        ttl = int(ttl_raw)
    except ValueError as exc:
        raise AuthSettingsError("CLINIC_ACCESS_TOKEN_TTL_SECONDS must be an integer") from exc
    if ttl <= 0 or ttl > 3600:
        raise AuthSettingsError("CLINIC_ACCESS_TOKEN_TTL_SECONDS must be in 1..3600")

    try:
        max_failed = int((env.get("CLINIC_MAX_FAILED_LOGIN_ATTEMPTS") or "5").strip())
    except ValueError as exc:
        raise AuthSettingsError(
            "CLINIC_MAX_FAILED_LOGIN_ATTEMPTS must be an integer"
        ) from exc
    try:
        lockout_minutes = int((env.get("CLINIC_LOCKOUT_MINUTES") or "15").strip())
    except ValueError as exc:
        raise AuthSettingsError("CLINIC_LOCKOUT_MINUTES must be an integer") from exc
    if max_failed < 1 or max_failed > 50:
        raise AuthSettingsError("CLINIC_MAX_FAILED_LOGIN_ATTEMPTS must be in 1..50")
    if lockout_minutes < 1 or lockout_minutes > 24 * 60:
        raise AuthSettingsError("CLINIC_LOCKOUT_MINUTES must be in 1..1440")

    return AuthSettings(
        clinic_env=clinic_env,
        database_url=database_url,
        access_token_signing_secret=secret,
        access_token_issuer=issuer,
        access_token_audience=audience,
        access_token_ttl_seconds=ttl,
        auth_realm_enabled=realm_enabled,
        auth_realm_tenant_id=realm_tenant,
        max_failed_login_attempts=max_failed,
        lockout_minutes=lockout_minutes,
    )


def require_token_signing_secret(settings: AuthSettings) -> str:
    if not settings.access_token_signing_secret:
        raise AuthSettingsError("CLINIC_ACCESS_TOKEN_SIGNING_SECRET is required")
    if len(settings.access_token_signing_secret) < 32:
        raise AuthSettingsError(
            "CLINIC_ACCESS_TOKEN_SIGNING_SECRET must be at least 32 characters"
        )
    return settings.access_token_signing_secret


def require_usable_auth_realm(settings: AuthSettings) -> UUID:
    """Fail closed unless the synthetic single-tenant login realm is safe to use."""
    if settings.clinic_env not in _ALLOWED_REALM_ENVS:
        raise AuthSettingsError(
            "auth realm is disabled outside test/development environments"
        )
    if not settings.auth_realm_enabled:
        raise AuthSettingsError("CLINIC_BETA_AUTH_REALM_ENABLED is not enabled")
    if settings.auth_realm_tenant_id is None:
        raise AuthSettingsError("CLINIC_BETA_AUTH_REALM_TENANT_ID is required")
    return settings.auth_realm_tenant_id


def require_token_tenant_matches_realm(
    settings: AuthSettings, token_tenant_id: UUID
) -> UUID:
    """Reject tokens whose tenant is outside the configured demo realm."""
    realm_tenant_id = require_usable_auth_realm(settings)
    if token_tenant_id != realm_tenant_id:
        raise AuthSettingsError("token tenant is outside the configured auth realm")
    return realm_tenant_id

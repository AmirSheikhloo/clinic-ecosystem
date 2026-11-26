"""Unit tests for BETA-01A settings, passwords, and access tokens (no Docker)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from clinic_ecosystem.infrastructure.auth.access_tokens import (
    AccessTokenError,
    issue_access_token,
    validate_access_token,
)
from clinic_ecosystem.infrastructure.auth.passwords import hash_password, verify_password
from clinic_ecosystem.infrastructure.auth.settings import (
    AuthSettingsError,
    load_auth_settings,
    require_usable_auth_realm,
)


def _base_env(**overrides: str) -> dict[str, str]:
    env = {
        "CLINIC_ENV": "test",
        "CLINIC_BETA_AUTH_REALM_ENABLED": "1",
        "CLINIC_BETA_AUTH_REALM_TENANT_ID": str(uuid4()),
        "CLINIC_ACCESS_TOKEN_SIGNING_SECRET": "x" * 48,
        "CLINIC_DATABASE_URL": "postgresql+asyncpg://tp_app_login:unused@127.0.0.1:5432/tenant_app",
    }
    env.update(overrides)
    return env


def test_password_hash_and_verify_roundtrip() -> None:
    hashed = hash_password("Beta01a-Unit-Test-Password!")
    assert hashed.startswith("$argon2id$")
    assert verify_password(hashed, "Beta01a-Unit-Test-Password!") is True
    assert verify_password(hashed, "wrong-password") is False


def test_realm_fails_closed_when_disabled() -> None:
    settings = load_auth_settings(
        _base_env(CLINIC_BETA_AUTH_REALM_ENABLED="0")
    )
    with pytest.raises(AuthSettingsError):
        require_usable_auth_realm(settings)


def test_realm_fails_closed_outside_test_dev() -> None:
    settings = load_auth_settings(_base_env(CLINIC_ENV="production"))
    with pytest.raises(AuthSettingsError):
        require_usable_auth_realm(settings)


def test_realm_fails_closed_without_tenant_id() -> None:
    env = _base_env()
    del env["CLINIC_BETA_AUTH_REALM_TENANT_ID"]
    settings = load_auth_settings(env)
    with pytest.raises(AuthSettingsError):
        require_usable_auth_realm(settings)


def test_invalid_realm_tenant_uuid_raises() -> None:
    with pytest.raises(AuthSettingsError):
        load_auth_settings(_base_env(CLINIC_BETA_AUTH_REALM_TENANT_ID="not-a-uuid"))


def test_access_token_roundtrip_and_claim_validation() -> None:
    settings = load_auth_settings(_base_env())
    principal = uuid4()
    tenant = uuid4()
    token, claims = issue_access_token(
        settings=settings, principal_id=principal, tenant_id=tenant
    )
    assert claims.principal_id == principal
    assert claims.tenant_id == tenant
    parsed = validate_access_token(token, settings=settings)
    assert parsed.principal_id == principal
    assert parsed.tenant_id == tenant
    assert parsed.token_id == claims.token_id
    assert parsed.issuer == settings.access_token_issuer
    assert parsed.audience == settings.access_token_audience


def test_expired_token_rejected() -> None:
    settings = load_auth_settings(_base_env(CLINIC_ACCESS_TOKEN_TTL_SECONDS="60"))
    past = datetime.now(timezone.utc) - timedelta(hours=2)
    token, _ = issue_access_token(
        settings=settings,
        principal_id=uuid4(),
        tenant_id=uuid4(),
        now=past,
    )
    with pytest.raises(AccessTokenError):
        validate_access_token(token, settings=settings)


def test_wrong_secret_rejected() -> None:
    settings = load_auth_settings(_base_env())
    token, _ = issue_access_token(
        settings=settings, principal_id=uuid4(), tenant_id=uuid4()
    )
    other = load_auth_settings(_base_env(CLINIC_ACCESS_TOKEN_SIGNING_SECRET="y" * 48))
    with pytest.raises(AccessTokenError):
        validate_access_token(token, settings=other)


def test_malformed_token_rejected() -> None:
    settings = load_auth_settings(_base_env())
    with pytest.raises(AccessTokenError):
        validate_access_token("not-a.jwt.token", settings=settings)

"""Demo alias fail-closed gating and resolution."""

from __future__ import annotations

from clinic_ecosystem.infrastructure.auth.demo_aliases import (
    DEMO_SHARED_PASSWORD,
    demo_aliases_enabled,
    load_demo_alias_catalog,
    resolve_login_identifier,
)

_VALID = {
    "CLINIC_ENV": "test",
    "CLINIC_DEMO_ALIASES_ENABLED": "1",
    "CLINIC_BETA_AUTH_REALM_ENABLED": "1",
    "CLINIC_BETA_AUTH_REALM_TENANT_ID": "00000000-0000-4000-8000-000000000001",
    "CLINIC_OPS_SCHEMA_MODE": "disposable",
    "CLINIC_DEMO_DISPOSABLE_MARKER": "clinic-ecosystem-synthetic-preview-v1",
    "CLINIC_DATABASE_URL": "postgresql+asyncpg://u:p@127.0.0.1:5432/tenant_app_preview",
    "CLINIC_DEMO_ALIAS_OWNER": "owner@beta02.test",
    "CLINIC_DEMO_ALIAS_RECEPTIONIST": "receptionist@beta01b.test",
}


def test_aliases_fail_closed_in_production() -> None:
    env = {**_VALID, "CLINIC_ENV": "production"}
    assert demo_aliases_enabled(env) is False


def test_aliases_reject_arbitrary_development_label() -> None:
    env = {**_VALID, "CLINIC_ENV": "development"}
    assert demo_aliases_enabled(env) is False
    env2 = {**_VALID, "CLINIC_ENV": "dev"}
    assert demo_aliases_enabled(env2) is False


def test_aliases_require_disposable_ops_mode() -> None:
    env = {**_VALID, "CLINIC_OPS_SCHEMA_MODE": "1"}
    assert demo_aliases_enabled(env) is False


def test_aliases_require_disposable_marker() -> None:
    env = {**_VALID, "CLINIC_DEMO_DISPOSABLE_MARKER": "wrong"}
    assert demo_aliases_enabled(env) is False


def test_aliases_disabled_without_realm() -> None:
    env = {**_VALID, "CLINIC_BETA_AUTH_REALM_ENABLED": "0"}
    assert demo_aliases_enabled(env) is False


def test_aliases_enabled_only_with_verified_synthetic_identity() -> None:
    cat = load_demo_alias_catalog(_VALID)
    assert cat.enabled is True
    assert cat.password == DEMO_SHARED_PASSWORD
    assert resolve_login_identifier("owner", cat) == "owner@beta02.test"
    assert resolve_login_identifier("OWNER", cat) == "owner@beta02.test"
    assert resolve_login_identifier("someone@else.test", cat) == "someone@else.test"


def test_no_default_alias_mappings_without_env() -> None:
    env = {k: v for k, v in _VALID.items() if not k.startswith("CLINIC_DEMO_ALIAS_")}
    cat = load_demo_alias_catalog(env)
    assert cat.enabled is False
    assert cat.aliases == {}

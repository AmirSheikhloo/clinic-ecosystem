"""Demo alias fail-closed gating and resolution."""

from __future__ import annotations

from clinic_ecosystem.infrastructure.auth.demo_aliases import (
    DEMO_SHARED_PASSWORD,
    demo_aliases_enabled,
    load_demo_alias_catalog,
    resolve_login_identifier,
)


def test_aliases_fail_closed_in_production() -> None:
    env = {
        "CLINIC_ENV": "production",
        "CLINIC_DEMO_ALIASES_ENABLED": "1",
        "CLINIC_BETA_AUTH_REALM_ENABLED": "1",
        "CLINIC_OPS_SCHEMA_MODE": "disposable",
    }
    assert demo_aliases_enabled(env) is False
    assert load_demo_alias_catalog(env).enabled is False


def test_aliases_disabled_without_realm() -> None:
    env = {
        "CLINIC_ENV": "test",
        "CLINIC_DEMO_ALIASES_ENABLED": "1",
        "CLINIC_BETA_AUTH_REALM_ENABLED": "0",
        "CLINIC_OPS_SCHEMA_MODE": "disposable",
    }
    assert demo_aliases_enabled(env) is False


def test_aliases_enabled_only_with_explicit_synthetic_flags() -> None:
    env = {
        "CLINIC_ENV": "test",
        "CLINIC_DEMO_ALIASES_ENABLED": "1",
        "CLINIC_BETA_AUTH_REALM_ENABLED": "1",
        "CLINIC_OPS_SCHEMA_MODE": "disposable",
        "CLINIC_DEMO_ALIAS_OWNER": "owner@beta02.test",
        "CLINIC_DEMO_ALIAS_RECEPTIONIST": "receptionist@beta01b.test",
    }
    cat = load_demo_alias_catalog(env)
    assert cat.enabled is True
    assert cat.password == DEMO_SHARED_PASSWORD
    assert resolve_login_identifier("owner", cat) == "owner@beta02.test"
    assert resolve_login_identifier("OWNER", cat) == "owner@beta02.test"
    assert resolve_login_identifier("someone@else.test", cat) == "someone@else.test"

"""Isolated-preview demo login aliases (Task 34 §5). Fail closed outside synthetic preview."""

from __future__ import annotations

import os
from dataclasses import dataclass

# Shared demo-only password for Product Owner one-click role login.
DEMO_SHARED_PASSWORD = "Clinic123!"

# Alias → Persian label (UI). Resolution to real login_identifier is env-configured.
DEMO_ROLE_ALIASES: tuple[str, ...] = (
    "owner",
    "manager",
    "deputy",
    "head",
    "receptionist",
    "limited",
    "doctor",
    "clerk",
)

DEMO_ROLE_LABELS_FA: dict[str, str] = {
    "owner": "مالک کلینیک",
    "manager": "مدیر",
    "deputy": "جانشین مدیر",
    "head": "سرپرست پذیرش",
    "receptionist": "پذیرشگر عمومی",
    "limited": "پذیرشگر محدود",
    "doctor": "پزشک (نمونه ورود)",
    "clerk": "منشی بدون مجوز",
}


@dataclass(frozen=True)
class DemoAliasCatalog:
    enabled: bool
    password: str
    aliases: dict[str, str]  # alias → real login_identifier
    labels_fa: dict[str, str]


def _truthy(raw: str | None) -> bool:
    return (raw or "").strip().lower() in {"1", "true", "yes", "on"}


def demo_aliases_enabled(environ: dict[str, str] | None = None) -> bool:
    """Require explicit synthetic flags — hostname alone is insufficient."""
    env = environ if environ is not None else os.environ
    clinic_env = (env.get("CLINIC_ENV") or "production").strip().lower()
    if clinic_env in {"production", "staging", "prod"}:
        return False
    if not _truthy(env.get("CLINIC_DEMO_ALIASES_ENABLED")):
        return False
    if not _truthy(env.get("CLINIC_BETA_AUTH_REALM_ENABLED")):
        return False
    # Disposable ops preview or explicit test realm.
    ops = (env.get("CLINIC_OPS_SCHEMA_MODE") or "").strip().lower()
    if ops not in {"disposable", "1", "true"} and clinic_env not in {"test", "development", "dev"}:
        return False
    return True


def load_demo_alias_catalog(environ: dict[str, str] | None = None) -> DemoAliasCatalog:
    env = environ if environ is not None else os.environ
    enabled = demo_aliases_enabled(env)
    aliases: dict[str, str] = {}
    if enabled:
        for alias in DEMO_ROLE_ALIASES:
            key = f"CLINIC_DEMO_ALIAS_{alias.upper()}"
            target = (env.get(key) or "").strip()
            if target:
                aliases[alias] = target
            elif alias in {"owner", "manager", "deputy"}:
                # Sensible preview defaults matching beta02 seed emails.
                aliases[alias] = f"{alias}@beta02.test"
    return DemoAliasCatalog(
        enabled=enabled,
        password=DEMO_SHARED_PASSWORD,
        aliases=aliases,
        labels_fa=dict(DEMO_ROLE_LABELS_FA),
    )


def resolve_login_identifier(raw: str, catalog: DemoAliasCatalog | None = None) -> str:
    """Map demo alias → real login when enabled; otherwise return trimmed input."""
    identifier = (raw or "").strip()
    cat = catalog or load_demo_alias_catalog()
    if not cat.enabled:
        return identifier
    key = identifier.lower()
    return cat.aliases.get(key, identifier)

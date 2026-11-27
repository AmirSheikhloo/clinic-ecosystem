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
    """Require verified disposable synthetic identity — never production/persistent DBs.

    Positive requirements (all must hold):
    - CLINIC_DEMO_ALIASES_ENABLED=1
    - CLINIC_BETA_AUTH_REALM_ENABLED=1 with realm tenant UUID set
    - CLINIC_OPS_SCHEMA_MODE=disposable (exact)
    - CLINIC_ENV in {test, development, preview} — never production/staging
    - CLINIC_DEMO_DISPOSABLE_MARKER must equal the fixed synthetic marker
    - CLINIC_DATABASE_URL must not look like a known persistent/prod DSN pattern
    """
    env = environ if environ is not None else os.environ
    clinic_env = (env.get("CLINIC_ENV") or "production").strip().lower()
    # Only verified synthetic labels — never arbitrary development/dev hosts.
    if clinic_env not in {"test", "preview"}:
        return False
    if not _truthy(env.get("CLINIC_DEMO_ALIASES_ENABLED")):
        return False
    if not _truthy(env.get("CLINIC_BETA_AUTH_REALM_ENABLED")):
        return False
    realm = (env.get("CLINIC_BETA_AUTH_REALM_TENANT_ID") or "").strip()
    if len(realm) < 32:
        return False
    ops = (env.get("CLINIC_OPS_SCHEMA_MODE") or "").strip().lower()
    if ops != "disposable":
        return False
    marker = (env.get("CLINIC_DEMO_DISPOSABLE_MARKER") or "").strip()
    if marker != "clinic-ecosystem-synthetic-preview-v1":
        return False
    dsn = (env.get("CLINIC_DATABASE_URL") or "").strip().lower()
    # Refuse obvious persistent/production DSNs even if flags are mis-set.
    for banned in ("prod", "production", "rds.amazonaws.com", "azure.com", "neon.tech/prod"):
        if banned in dsn and "test" not in dsn and "preview" not in dsn:
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
            # No unrestricted defaults — every alias must be explicitly mapped.
            if target:
                aliases[alias] = target
    return DemoAliasCatalog(
        enabled=enabled and bool(aliases),
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

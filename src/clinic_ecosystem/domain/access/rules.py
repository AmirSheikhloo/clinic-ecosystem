"""Pure authorization rules for role and governance administration."""

from __future__ import annotations

import re
from collections.abc import Iterable

GOVERNANCE_ROLES = ("CLINIC_OWNER", "CLINIC_MANAGER", "DEPUTY_ADMIN", "RECEPTIONIST")
_OWNER_ONLY = frozenset({"CLINIC_OWNER", "CLINIC_MANAGER"})
_ROLE_CODE = re.compile(r"^[A-Z][A-Z0-9_]{2,63}$")
_FORBIDDEN_ROLE_CODES = frozenset({"SUPER_ADMIN", *GOVERNANCE_ROLES})


def validate_role_code(code: str) -> str | None:
    """Return an error message or None when the code is acceptable."""
    if not _ROLE_CODE.match(code):
        return "Role code must be 3-64 characters: A-Z, 0-9 and underscore"
    if code in _FORBIDDEN_ROLE_CODES:
        return "Role code is reserved"
    return None


def ungrantable(actor_permissions: Iterable[str], requested: Iterable[str]) -> set[str]:
    """Permissions in ``requested`` the actor does not hold (anti-escalation)."""
    return set(requested) - set(actor_permissions)


def governance_change_allowed(actor_governance: Iterable[str], role: str) -> bool:
    """Owner-level roles are assignable only by owners; others by owner/manager."""
    actor = set(actor_governance)
    if role in _OWNER_ONLY:
        return "CLINIC_OWNER" in actor
    return bool(actor & {"CLINIC_OWNER", "CLINIC_MANAGER"})

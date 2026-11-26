from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Actor:
    """Verified server-side principal for protected operations."""

    tenant_id: UUID
    account_id: UUID
    person_id: UUID

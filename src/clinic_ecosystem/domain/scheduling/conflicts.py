"""Domain conflict facts for MANUAL overlap inspection (no display/PII projection)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class OverlapConflictFact:
    """Business facts about an occupying allocation conflict (identifiers only)."""

    appointment_id: UUID
    beneficiary_patient_id: UUID
    booking_channel: str
    capacity_pool: str
    scheduled_start_at_utc: datetime
    scheduled_end_at_utc: datetime
    resource_id: UUID
    allocation_status: str

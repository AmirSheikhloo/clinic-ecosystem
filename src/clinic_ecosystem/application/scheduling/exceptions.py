"""Application-layer exceptions for ScheduleAppointment."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


class ApplicationError(Exception):
    """Base application error."""


class IdempotencyConflict(ApplicationError):
    """Same idempotency key with different fingerprint."""


class IdempotencyInProgress(ApplicationError):
    """Competing owner holds IN_PROGRESS (HTTP 425)."""


class ServiceRequirementsNotMet(ApplicationError):
    """Requested resource set does not satisfy service_resource_requirements."""


class UnauthorizedScheduling(ApplicationError):
    """Missing ALLOW_MANUAL_OVERBOOKING or related permission."""


@dataclass(frozen=True, slots=True)
class ConflictDisplayItem:
    """Authorized staff-facing conflict projection (clause 779)."""

    appointment_id: UUID
    display_safe_patient_name: str
    booking_channel: str
    scheduled_start_at_utc: datetime
    scheduled_end_at_utc: datetime


class ManualOverlapAcknowledgementRequired(ApplicationError):
    """MANUAL booking overlaps; authorized staff must acknowledge the exact set."""

    def __init__(self, conflicts: list[ConflictDisplayItem]) -> None:
        self.conflicts = conflicts
        super().__init__("manual_overlap_acknowledgement_required")

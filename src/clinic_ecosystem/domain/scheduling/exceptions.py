"""Domain exceptions for scheduling."""


class DomainError(Exception):
    """Base domain error."""


class InvalidAppointmentSchedule(DomainError):
    """Schedule invariants failed before persistence."""


class CapacityConflictException(DomainError):
    """ONLINE capacity conflict (maps from EXCLUDE / no_overlapping_appointments)."""


class ManualOverlapAcknowledgementRequired(DomainError):
    """MANUAL booking overlaps existing allocations and needs acknowledgement."""

    def __init__(self, conflicts: list[dict]) -> None:
        self.conflicts = conflicts
        super().__init__("manual_overlap_acknowledgement_required")


class PermissionDenied(DomainError):
    """Caller lacks a required permission."""

"""Domain exceptions for scheduling."""


class DomainError(Exception):
    """Base domain error."""


class InvalidAppointmentSchedule(DomainError):
    """Schedule invariants failed before persistence."""


class CapacityConflictException(DomainError):
    """ONLINE capacity conflict (maps from EXCLUDE / no_overlapping_appointments)."""

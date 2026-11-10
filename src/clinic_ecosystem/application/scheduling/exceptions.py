"""Application-layer exceptions for ScheduleAppointment."""


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

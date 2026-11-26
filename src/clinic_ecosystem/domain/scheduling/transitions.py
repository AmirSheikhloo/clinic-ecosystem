"""Allowed appointment lifecycle transitions (clause 781 statuses).

Occupying allocation statuses remain PENDING_PAYMENT_HOLD, CONFIRMED and
CHECKED_IN. COMPLETED / NO_SHOW / CANCELLED release capacity.
"""

from __future__ import annotations

from datetime import datetime

from clinic_ecosystem.domain.scheduling.exceptions import DomainError

# (from_status, to_status) -> action name
ALLOWED_TRANSITIONS: dict[tuple[str, str], str] = {
    ("CONFIRMED", "CHECKED_IN"): "check_in",
    ("CONFIRMED", "NO_SHOW"): "no_show",
    ("CONFIRMED", "CANCELLED"): "cancel",
    ("CHECKED_IN", "COMPLETED"): "complete",
    ("CHECKED_IN", "CANCELLED"): "cancel",
}


class InvalidStatusTransition(DomainError):
    """Transition is not permitted for the current appointment state."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        current_status: str | None = None,
        target_status: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.current_status = current_status
        self.target_status = target_status

    @property
    def extra(self) -> dict:
        out: dict = {}
        if self.current_status is not None:
            out["current_status"] = self.current_status
        if self.target_status is not None:
            out["target_status"] = self.target_status
        return out


def validate_transition(
    *,
    from_status: str,
    to_status: str,
    now: datetime,
    scheduled_start_at_utc: datetime,
) -> str:
    """Return the action name if allowed; otherwise raise InvalidStatusTransition."""
    action = ALLOWED_TRANSITIONS.get((from_status, to_status))
    if action is None:
        raise InvalidStatusTransition(
            "Appointment status does not allow this operation",
            code="invalid_status_transition",
            current_status=from_status,
            target_status=to_status,
        )
    if to_status == "NO_SHOW" and now < scheduled_start_at_utc:
        raise InvalidStatusTransition(
            "NO_SHOW cannot be applied before the scheduled start",
            code="no_show_before_start",
            current_status=from_status,
            target_status=to_status,
        )
    return action

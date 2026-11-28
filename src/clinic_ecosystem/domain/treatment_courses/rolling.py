"""Rolling recall plan derivation (completion-based; Tehran local dates)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from clinic_ecosystem.domain.treatment_courses.jalali import (
    add_jalali_months,
    from_jalali,
    to_jalali,
)
from clinic_ecosystem.infrastructure.timezones import TEHRAN_TZ_KEY, require_tehran_zoneinfo

# Alias kept for callers that still say CALENDAR_MONTH in the early stub.
_MONTH_KINDS = frozenset({"JALALI_CALENDAR_MONTH", "CALENDAR_MONTH"})


@dataclass(frozen=True, slots=True)
class ReminderPlan:
    completion_tehran: date
    suggested_tehran: date
    reminder_tehran: date
    interval_kind: str
    interval_value: int
    reminder_lead_days: int
    scheduling_mode: str


def shift_tehran_days(day: date, delta_days: int) -> date:
    """Shift a Tehran calendar DATE by civil days (not UTC-instant math)."""
    return day + timedelta(days=delta_days)


def _add_jalali_calendar_months(day: date, months: int) -> date:
    j = to_jalali(day.year, day.month, day.day)
    nxt = add_jalali_months(j.year, j.month, j.day, months)
    gy, gm, gd = from_jalali(nxt.year, nxt.month, nxt.day)
    return date(gy, gm, gd)


def compute_next_suggested_date(
    *,
    completion_tehran: date,
    interval_kind: str,
    interval_value: int,
    scheduling_mode: str = "ROLLING",
) -> date:
    """Next suggested visit date from actual completion (never booking/payment)."""
    if scheduling_mode not in {"ROLLING", "FIXED"}:
        raise ValueError("unsupported scheduling_mode")
    if interval_value <= 0:
        raise ValueError("interval_value must be positive")
    # FIXED lattice still advances from the completion anchor for this tip when
    # no separate fixed-anchor table is bound; callers may override suggested date.
    if interval_kind in _MONTH_KINDS:
        return _add_jalali_calendar_months(completion_tehran, interval_value)
    if interval_kind == "FIXED_DAYS":
        return shift_tehran_days(completion_tehran, interval_value)
    raise ValueError(f"unsupported interval_kind: {interval_kind}")


def compute_rolling_reminder_plan(
    *,
    completion_tehran: date,
    interval_kind: str = "JALALI_CALENDAR_MONTH",
    interval_value: int = 1,
    reminder_lead_days: int = 2,
    scheduling_mode: str = "ROLLING",
) -> ReminderPlan:
    suggested = compute_next_suggested_date(
        completion_tehran=completion_tehran,
        interval_kind=interval_kind,
        interval_value=interval_value,
        scheduling_mode=scheduling_mode,
    )
    if reminder_lead_days < 0:
        raise ValueError("reminder_lead_days must be >= 0")
    reminder = shift_tehran_days(suggested, -reminder_lead_days)
    return ReminderPlan(
        completion_tehran=completion_tehran,
        suggested_tehran=suggested,
        reminder_tehran=reminder,
        interval_kind=interval_kind,
        interval_value=interval_value,
        reminder_lead_days=reminder_lead_days,
        scheduling_mode=scheduling_mode,
    )


def tehran_date_to_utc_noon(day: date) -> datetime:
    """Persist a Tehran calendar day as a stable UTC instant (local noon)."""
    tz = require_tehran_zoneinfo()
    local = datetime(day.year, day.month, day.day, 12, 0, 0, tzinfo=tz)
    return local.astimezone(ZoneInfo("UTC"))


def defer_for_quiet_hours(
    *,
    candidate_utc: datetime,
    quiet_start_minute: int,
    quiet_end_minute: int,
) -> datetime:
    """If candidate falls inside Tehran quiet hours, defer to quiet_end same/next day.

    Quiet window may wrap midnight (e.g. 22:00–08:00 → start=1320, end=480).
    """
    if not (0 <= quiet_start_minute < 1440 and 0 <= quiet_end_minute < 1440):
        raise ValueError("quiet hour minutes out of range")
    tz = require_tehran_zoneinfo()
    local = candidate_utc.astimezone(tz)
    minutes = local.hour * 60 + local.minute

    def _in_quiet(m: int) -> bool:
        if quiet_start_minute == quiet_end_minute:
            return False
        if quiet_start_minute < quiet_end_minute:
            return quiet_start_minute <= m < quiet_end_minute
        return m >= quiet_start_minute or m < quiet_end_minute

    if not _in_quiet(minutes):
        return candidate_utc

    end_h, end_m = divmod(quiet_end_minute, 60)
    end_local = datetime(
        local.year, local.month, local.day, end_h, end_m, 0, tzinfo=tz
    )
    if quiet_start_minute > quiet_end_minute and minutes >= quiet_start_minute:
        end_local = end_local + timedelta(days=1)
    elif quiet_start_minute < quiet_end_minute and minutes >= quiet_end_minute:
        end_local = end_local + timedelta(days=1)
    return end_local.astimezone(ZoneInfo("UTC"))


def assert_tehran_zone() -> str:
    require_tehran_zoneinfo()
    return TEHRAN_TZ_KEY

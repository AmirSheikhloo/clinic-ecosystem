"""Task 34 R2 §9 — rolling recall from actual completion (Mehr→Aban→Azar)."""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

from clinic_ecosystem.domain.treatment_courses.jalali import (
    JalaliDate,
    add_jalali_months,
    from_jalali,
    is_jalali_leap,
    jalali_month_length,
    to_jalali,
)
from clinic_ecosystem.domain.treatment_courses.rolling import (
    compute_rolling_reminder_plan,
    defer_for_quiet_hours,
    shift_tehran_days,
)


def _ymd_jalali(jy: int, jm: int, jd: int) -> date:
    gy, gm, gd = from_jalali(jy, jm, jd)
    return date(gy, gm, gd)


def test_ext_recall_01_mehr_aban_azar_rolling_from_completion() -> None:
    """Session 1 completed 5 Mehr → next 5 Aban → reminder 3 Aban;
    Session 2 completed 15 Aban → next 15 Azar → reminder 13 Azar.
    """
    s1 = _ymd_jalali(1405, 7, 5)  # 5 Mehr 1405
    plan1 = compute_rolling_reminder_plan(
        completion_tehran=s1,
        interval_kind="JALALI_CALENDAR_MONTH",
        interval_value=1,
        reminder_lead_days=2,
        scheduling_mode="ROLLING",
    )
    assert plan1.suggested_tehran == _ymd_jalali(1405, 8, 5)
    assert plan1.reminder_tehran == _ymd_jalali(1405, 8, 3)
    assert to_jalali(
        plan1.suggested_tehran.year, plan1.suggested_tehran.month, plan1.suggested_tehran.day
    ) == JalaliDate(1405, 8, 5)
    assert to_jalali(
        plan1.reminder_tehran.year, plan1.reminder_tehran.month, plan1.reminder_tehran.day
    ) == JalaliDate(1405, 8, 3)

    s2 = _ymd_jalali(1405, 8, 15)  # 15 Aban — completion date, NOT booking/payment
    plan2 = compute_rolling_reminder_plan(completion_tehran=s2)
    assert plan2.suggested_tehran == _ymd_jalali(1405, 9, 15)
    assert plan2.reminder_tehran == _ymd_jalali(1405, 9, 13)
    assert to_jalali(
        plan2.suggested_tehran.year, plan2.suggested_tehran.month, plan2.suggested_tehran.day
    ) == JalaliDate(1405, 9, 15)
    assert to_jalali(
        plan2.reminder_tehran.year, plan2.reminder_tehran.month, plan2.reminder_tehran.day
    ) == JalaliDate(1405, 9, 13)

    # Booking date must not drive rolling.
    booking = _ymd_jalali(1405, 8, 1)
    assert booking != s2
    assert compute_rolling_reminder_plan(completion_tehran=s2).suggested_tehran != (
        compute_rolling_reminder_plan(completion_tehran=booking).suggested_tehran
    )


def test_jalali_leap_and_end_of_month_clamp() -> None:
    assert is_jalali_leap(1403) is True
    assert jalali_month_length(1403, 12) == 30
    assert is_jalali_leap(1404) is False
    assert jalali_month_length(1404, 12) == 29

    # 30 Esfand 1403 + 12 months → clamp into 29 Esfand 1404
    clamped = add_jalali_months(1403, 12, 30, 12)
    assert clamped == JalaliDate(1404, 12, 29)

    # 31 Farvardin + 7 months → Aban has 30 days → clamp to 30
    assert add_jalali_months(1405, 1, 31, 7) == JalaliDate(1405, 8, 30)


def test_fixed_days_interval() -> None:
    start = date(2026, 9, 27)
    plan = compute_rolling_reminder_plan(
        completion_tehran=start,
        interval_kind="FIXED_DAYS",
        interval_value=30,
        reminder_lead_days=2,
    )
    assert plan.suggested_tehran == shift_tehran_days(start, 30)
    assert plan.reminder_tehran == shift_tehran_days(plan.suggested_tehran, -2)


def test_quiet_hours_deferral_wraps_midnight() -> None:
    # 23:30 Tehran on a known day — inside 22:00–08:00 quiet window.
    tehran_late = datetime(2026, 10, 25, 20, 0, tzinfo=timezone.utc)  # ~23:30 IRST
    deferred = defer_for_quiet_hours(
        candidate_utc=tehran_late,
        quiet_start_minute=22 * 60,
        quiet_end_minute=8 * 60,
    )
    assert deferred > tehran_late

    midday = datetime(2026, 10, 25, 9, 0, tzinfo=timezone.utc)  # ~12:30 IRST
    same = defer_for_quiet_hours(
        candidate_utc=midday,
        quiet_start_minute=22 * 60,
        quiet_end_minute=8 * 60,
    )
    assert same == midday


def test_calendar_month_alias_matches_jalali_kind() -> None:
    d = _ymd_jalali(1405, 7, 5)
    a = compute_rolling_reminder_plan(completion_tehran=d, interval_kind="CALENDAR_MONTH")
    b = compute_rolling_reminder_plan(
        completion_tehran=d, interval_kind="JALALI_CALENDAR_MONTH"
    )
    assert a.suggested_tehran == b.suggested_tehran
    assert a.reminder_tehran == b.reminder_tehran


def test_nowruz_boundaries_match_intl() -> None:
    assert to_jalali(2025, 3, 20) == JalaliDate(1403, 12, 30)
    assert from_jalali(1403, 12, 30) == (2025, 3, 20)
    assert from_jalali(1404, 1, 1) == (2025, 3, 21)


def test_pay_per_session_stub_flags() -> None:
    stub = Path("beta-panel/features/courses/payPerSession.ts").read_text(encoding="utf-8")
    assert "prepaidEntitlementEnabled: false" in stub
    assert "sharedSettlementEnabled: false" in stub


def test_architecture_doc_and_sql_present() -> None:
    arch = Path(
        "docs/validation/d010/proposed/TREATMENT_COURSES_ROLLING_RECALL_ARCHITECTURE.md"
    )
    sql = Path("docs/validation/d010/d09_extracted/proposed_treatment_courses.sql")
    assert arch.is_file()
    assert sql.is_file()
    body = sql.read_text(encoding="utf-8")
    for needle in (
        "treatment_course_sessions",
        "notification_outbox_synthetic",
        "treatment_reminder_policy_snapshots",
        "JALALI_CALENDAR_MONTH",
        "prepaid_entitlement_enabled BOOLEAN NOT NULL DEFAULT FALSE",
        "ops_treatment_session_performed_guard",
        "SYNTHETIC_SINK",
    ):
        assert needle in body

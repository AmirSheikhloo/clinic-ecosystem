"""Exact R2 rolling-recall example: Mehr → Aban → Azar (completion-based)."""

from __future__ import annotations

from datetime import date

from clinic_ecosystem.domain.treatment_courses.jalali import from_jalali
from clinic_ecosystem.domain.treatment_courses.rolling import compute_rolling_reminder_plan


def _tehran(jy: int, jm: int, jd: int) -> date:
    gy, gm, gd = from_jalali(jy, jm, jd)
    return date(gy, gm, gd)


def test_session1_mehr5_to_aban5_reminder_aban3() -> None:
    # Session 1 completed on 5 Mehr 1403 → next visit 5 Aban → reminder 3 Aban.
    completion = _tehran(1403, 7, 5)
    plan = compute_rolling_reminder_plan(
        completion_tehran=completion,
        interval_kind="JALALI_CALENDAR_MONTH",
        interval_value=1,
        reminder_lead_days=2,
        scheduling_mode="ROLLING",
    )
    assert plan.suggested_tehran == _tehran(1403, 8, 5)
    assert plan.reminder_tehran == _tehran(1403, 8, 3)


def test_session2_aban15_to_azar15_reminder_azar13() -> None:
    # Session 2 completed on 15 Aban → next 15 Azar → reminder 13 Azar.
    completion = _tehran(1403, 8, 15)
    plan = compute_rolling_reminder_plan(
        completion_tehran=completion,
        interval_kind="JALALI_CALENDAR_MONTH",
        interval_value=1,
        reminder_lead_days=2,
        scheduling_mode="ROLLING",
    )
    assert plan.suggested_tehran == _tehran(1403, 9, 15)
    assert plan.reminder_tehran == _tehran(1403, 9, 13)


def test_rolling_uses_completion_not_booking() -> None:
    booking = _tehran(1403, 7, 1)
    completion = _tehran(1403, 7, 5)
    plan = compute_rolling_reminder_plan(completion_tehran=completion)
    assert plan.suggested_tehran != _tehran(1403, 8, 1)
    assert plan.completion_tehran == completion
    assert booking != completion

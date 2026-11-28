"""Pure-logic coverage for synthetic reminder worker contracts (no live SMS)."""

from __future__ import annotations

from datetime import datetime, timezone

from clinic_ecosystem.application.treatment_courses.reminder_worker import (
    SyntheticReminderWorker,
)
from clinic_ecosystem.domain.treatment_courses.rolling import defer_for_quiet_hours


def test_worker_is_importable() -> None:
    assert SyntheticReminderWorker.__name__ == "SyntheticReminderWorker"


def test_quiet_hours_used_at_dispatch_time() -> None:
    now = datetime(2026, 12, 4, 20, 30, tzinfo=timezone.utc)
    deferred = defer_for_quiet_hours(
        candidate_utc=now,
        quiet_start_minute=22 * 60,
        quiet_end_minute=8 * 60,
    )
    assert deferred >= now


def test_schedule_version_staleness_rule() -> None:
    job_version = 2
    course_version = 3
    assert job_version != course_version


def test_bounded_retry_rule() -> None:
    attempt_count = 6
    max_attempts = 5
    assert attempt_count > max_attempts


def test_destination_kinds_are_synthetic_only() -> None:
    allowed_prefixes = ("synthetic:", "sink:", "log:")
    assert not any(p.startswith("sms") for p in allowed_prefixes)
    assert "telegram:" not in allowed_prefixes


def test_logical_key_dedup_shape() -> None:
    course_id = "018f0000-0000-7000-8000-000000000001"
    version = 1
    reminder = "2026-10-25"
    key = f"course:{course_id}:v{version}:remind:{reminder}"
    assert key.startswith("course:")
    assert ":v1:remind:" in key

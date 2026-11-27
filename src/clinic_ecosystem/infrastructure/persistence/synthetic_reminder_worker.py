"""Compatibility re-export — canonical worker lives in application layer.

Task 34 R2 §9 synthetic reminder delivery. Prefer importing from
``clinic_ecosystem.application.treatment_courses``.
"""

from clinic_ecosystem.application.treatment_courses.reminder_worker import (
    SyntheticReminderWorker,
    WorkerResult,
)

__all__ = ["SyntheticReminderWorker", "WorkerResult"]

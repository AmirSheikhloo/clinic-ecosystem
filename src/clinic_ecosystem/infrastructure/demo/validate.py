"""Count and validate demo dataset presence for a tenant."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from clinic_ecosystem.infrastructure.demo.profiles import DemoTargets

TEHRAN = ZoneInfo("Asia/Tehran")


async def count_demo_snapshot(
    session: AsyncSession, *, tenant_id: UUID, now: datetime | None = None
) -> dict[str, Any]:
    clock = now or datetime.now(timezone.utc)
    local = clock.astimezone(TEHRAN)
    today = local.date()
    tomorrow = today + timedelta(days=1)
    day0 = datetime(today.year, today.month, today.day, tzinfo=TEHRAN).astimezone(timezone.utc)
    day1 = datetime(tomorrow.year, tomorrow.month, tomorrow.day, tzinfo=TEHRAN).astimezone(
        timezone.utc
    )
    day2 = day1 + timedelta(days=1)

    async def scalar(sql: str, params: dict[str, Any]) -> int:
        result = await session.execute(text(sql), params)
        return int(result.scalar_one())

    by_status_rows = await session.execute(
        text(
            """
            SELECT status, count(*) AS n FROM appointments
            WHERE tenant_id = :t GROUP BY status
            """
        ),
        {"t": tenant_id},
    )
    by_status = {r.status: int(r.n) for r in by_status_rows}
    return {
        "patients": await scalar(
            "SELECT count(*) FROM patient_profiles WHERE tenant_id = :t", {"t": tenant_id}
        ),
        "staff": await scalar(
            "SELECT count(*) FROM staff_profiles WHERE tenant_id = :t", {"t": tenant_id}
        ),
        "services": await scalar(
            "SELECT count(*) FROM services WHERE tenant_id = :t", {"t": tenant_id}
        ),
        "resources": await scalar(
            "SELECT count(*) FROM bookable_resources WHERE tenant_id = :t", {"t": tenant_id}
        ),
        "appointments": await scalar(
            "SELECT count(*) FROM appointments WHERE tenant_id = :t", {"t": tenant_id}
        ),
        "appointments_today": await scalar(
            """
            SELECT count(*) FROM appointments
            WHERE tenant_id = :t AND scheduled_start_at_utc >= :a AND scheduled_start_at_utc < :b
            """,
            {"t": tenant_id, "a": day0, "b": day1},
        ),
        "appointments_tomorrow": await scalar(
            """
            SELECT count(*) FROM appointments
            WHERE tenant_id = :t AND scheduled_start_at_utc >= :a AND scheduled_start_at_utc < :b
            """,
            {"t": tenant_id, "a": day1, "b": day2},
        ),
        "checked_in": int(by_status.get("CHECKED_IN", 0)),
        "identifiers": await scalar(
            "SELECT count(*) FROM person_identifiers WHERE tenant_id = :t", {"t": tenant_id}
        ),
        "phones": await scalar(
            "SELECT count(*) FROM person_phones WHERE tenant_id = :t", {"t": tenant_id}
        ),
        "audit_entries": await scalar(
            "SELECT count(*) FROM audit_entries WHERE tenant_id = :t", {"t": tenant_id}
        ),
        "by_status": by_status,
    }


def validate_demo_counts(snapshot: dict[str, Any], targets: DemoTargets) -> list[str]:
    """Return human-readable deficit messages (empty = OK)."""
    checks = [
        ("patients", targets.patients),
        ("appointments", targets.appointments),
        ("appointments_today", targets.appointments_today),
        ("appointments_tomorrow", targets.appointments_tomorrow),
        ("services", targets.services),
        ("staff", targets.staff_total),
    ]
    deficits: list[str] = []
    for key, need in checks:
        have = int(snapshot.get(key, 0))
        if have < need:
            deficits.append(f"{key}: have {have}, need ≥ {need}")
    return deficits

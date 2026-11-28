"""Validate demo dataset counts against profile thresholds (asyncpg)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

import asyncpg

from clinic_ecosystem.infrastructure.demo.profiles import ProfileName, resolve_profile
from clinic_ecosystem.infrastructure.timezones import require_tehran_zoneinfo

TEHRAN = require_tehran_zoneinfo()


@dataclass(frozen=True)
class ValidationReport:
    ok: bool
    profile: ProfileName
    counts: dict[str, Any]
    failures: list[str]
    notes: list[str]


async def collect_counts(
    conn: asyncpg.Connection,
    *,
    tenant_id: UUID,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    await conn.execute(
        "SELECT set_config('app.current_tenant_id', $1, false)", str(tenant_id)
    )
    now = now_utc or datetime.now(timezone.utc)
    today = now.astimezone(TEHRAN).date()
    tomorrow = date.fromordinal(today.toordinal() + 1)

    async def scalar(sql: str, *args: object) -> int:
        return int(await conn.fetchval(sql, *args) or 0)

    by_status = {
        r["status"]: r["c"]
        for r in await conn.fetch(
            "SELECT status, count(*)::int AS c FROM appointments "
            "WHERE tenant_id = $1 GROUP BY status ORDER BY status",
            tenant_id,
        )
    }
    return {
        "patients": await scalar(
            "SELECT count(*) FROM patient_profiles WHERE tenant_id = $1", tenant_id
        ),
        "inactive_patients": await scalar(
            "SELECT count(*) FROM patient_profiles WHERE tenant_id = $1 AND is_active = FALSE",
            tenant_id,
        ),
        "exceptional_identity_patients": await scalar(
            "SELECT count(*) FROM patient_profiles WHERE tenant_id = $1 AND dossier_number LIKE 'EXC-%'",
            tenant_id,
        ),
        "staff": await scalar(
            "SELECT count(*) FROM staff_profiles WHERE tenant_id = $1", tenant_id
        ),
        "services": await scalar(
            "SELECT count(*) FROM services WHERE tenant_id = $1", tenant_id
        ),
        "rooms": await scalar(
            "SELECT count(*) FROM bookable_resources WHERE tenant_id = $1 AND resource_type = 'ROOM'",
            tenant_id,
        ),
        "appointments": await scalar(
            "SELECT count(*) FROM appointments WHERE tenant_id = $1", tenant_id
        ),
        "appointments_by_status": by_status,
        "appointments_today": await scalar(
            """
            SELECT count(*) FROM appointments WHERE tenant_id = $1
              AND (scheduled_start_at_utc AT TIME ZONE 'Asia/Tehran')::date = $2
            """,
            tenant_id,
            today,
        ),
        "appointments_tomorrow": await scalar(
            """
            SELECT count(*) FROM appointments WHERE tenant_id = $1
              AND (scheduled_start_at_utc AT TIME ZONE 'Asia/Tehran')::date = $2
            """,
            tenant_id,
            tomorrow,
        ),
        "checked_in_waiting_today": await scalar(
            """
            SELECT count(*) FROM appointments
            WHERE tenant_id = $1 AND status = 'CHECKED_IN'
              AND (scheduled_start_at_utc AT TIME ZONE 'Asia/Tehran')::date = $2
            """,
            tenant_id,
            today,
        ),
        "multi_service_groups": await scalar(
            """
            SELECT count(DISTINCT split_part(patient_booking_note, ' ', 1))
            FROM appointments
            WHERE tenant_id = $1 AND patient_booking_note LIKE 'GROUP:%'
            """,
            tenant_id,
        ),
        "manual_overlap_pairs": await scalar(
            """
            SELECT count(*) FROM appointments
            WHERE tenant_id = $1
              AND patient_booking_note LIKE 'OVERLAP pair=%'
              AND patient_booking_note LIKE '%side=0%'
            """,
            tenant_id,
        ),
        "audit_entries": await scalar(
            "SELECT count(*) FROM audit_entries WHERE tenant_id = $1", tenant_id
        ),
        "national_id_rows": await scalar(
            "SELECT count(*) FROM person_identifiers WHERE tenant_id = $1 AND id_type = 'IR_NATIONAL_ID'",
            tenant_id,
        ),
        "shared_phone_families": await scalar(
            """
            SELECT count(*) FROM (
              SELECT phone_lookup_hmac FROM person_phones
              WHERE tenant_id = $1 AND is_shared_phone = TRUE
              GROUP BY phone_lookup_hmac HAVING count(*) >= 2
            ) s
            """,
            tenant_id,
        ),
        "phone_rows": await scalar(
            "SELECT count(*) FROM person_phones WHERE tenant_id = $1", tenant_id
        ),
        "tehran_today": today.isoformat(),
    }


def _require(failures: list[str], label: str, actual: int, minimum: int) -> None:
    if actual < minimum:
        failures.append(f"{label}: {actual} < {minimum}")


async def validate_demo_counts(
    conn: asyncpg.Connection,
    *,
    tenant_id: UUID,
    profile: str = "demo",
    crypto_expected: bool | None = None,
    now_utc: datetime | None = None,
) -> ValidationReport:
    profile_name, targets = resolve_profile(profile)
    counts = await collect_counts(conn, tenant_id=tenant_id, now_utc=now_utc)
    failures: list[str] = []
    notes: list[str] = []

    checks = (
        ("patients", counts["patients"], targets.patients),
        ("staff", counts["staff"], targets.staff_total),
        ("services", counts["services"], targets.services),
        ("rooms", counts["rooms"], targets.resources_rooms),
        ("appointments", counts["appointments"], targets.appointments),
        ("appointments_today", counts["appointments_today"], targets.appointments_today),
        ("appointments_tomorrow", counts["appointments_tomorrow"], targets.appointments_tomorrow),
        ("checked_in_waiting_today", counts["checked_in_waiting_today"], targets.checked_in_waiting_today),
        ("multi_service_groups", counts["multi_service_groups"], targets.multi_service_groups),
        ("manual_overlap_pairs", counts["manual_overlap_pairs"], targets.manual_overlap_pairs),
        ("audit_entries", counts["audit_entries"], targets.audit_entries),
        (
            "exceptional_identity_patients",
            counts["exceptional_identity_patients"],
            targets.exceptional_identity_patients,
        ),
    )
    for label, actual, minimum in checks:
        _require(failures, label, actual, minimum)

    crypto_on = counts["national_id_rows"] > 0 or counts["phone_rows"] > 0
    if crypto_expected is True or (crypto_expected is None and crypto_on):
        _require(failures, "national_id_rows", counts["national_id_rows"], targets.national_id_patients)
        _require(
            failures,
            "shared_phone_families",
            counts["shared_phone_families"],
            targets.shared_phone_families,
        )
    else:
        notes.append(
            "Crypto thresholds skipped (set CLINIC_ENV=test and CLINIC_PII_* keys to seed PII)."
        )

    if profile_name != "minimal":
        for status in ("CONFIRMED", "CHECKED_IN", "COMPLETED", "CANCELLED", "NO_SHOW"):
            if counts["appointments_by_status"].get(status, 0) < 1:
                failures.append(f"missing status {status}")

    return ValidationReport(
        ok=not failures,
        profile=profile_name,
        counts=counts,
        failures=failures,
        notes=notes,
    )


def format_report(report: ValidationReport) -> str:
    lines = [
        f"profile={report.profile} ok={report.ok}",
        f"tehran_today={report.counts.get('tehran_today')}",
    ]
    for key in (
        "patients", "inactive_patients", "exceptional_identity_patients", "staff",
        "services", "rooms", "appointments", "appointments_today", "appointments_tomorrow",
        "checked_in_waiting_today", "multi_service_groups", "manual_overlap_pairs",
        "audit_entries", "national_id_rows", "shared_phone_families", "phone_rows",
    ):
        lines.append(f"  {key}={report.counts.get(key)}")
    lines.append(f"  appointments_by_status={report.counts.get('appointments_by_status')}")
    for note in report.notes:
        lines.append(f"NOTE: {note}")
    for fail in report.failures:
        lines.append(f"FAIL: {fail}")
    return "\n".join(lines)

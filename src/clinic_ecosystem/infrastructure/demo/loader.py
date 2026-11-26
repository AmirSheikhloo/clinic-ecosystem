"""Load demo fixtures into PostgreSQL under tenant GUC (db_migrator role)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

import asyncpg

from clinic_ecosystem.infrastructure.demo.builders_appointments import (
    build_appointments,
    tehran_today,
)
from clinic_ecosystem.infrastructure.demo.builders_catalog import build_catalog
from clinic_ecosystem.infrastructure.demo.builders_people import build_patients, build_staff
from clinic_ecosystem.infrastructure.demo.crypto_hooks import plan_crypto_rows
from clinic_ecosystem.infrastructure.demo.persist import (
    persist_appointments,
    persist_audit,
    persist_catalog,
    persist_crypto,
    persist_identity_graph,
)
from clinic_ecosystem.infrastructure.demo.profiles import (
    DEMO_SEED,
    DemoTargets,
    ProfileName,
    resolve_profile,
    targets_as_dict,
)

TEHRAN = ZoneInfo("Asia/Tehran")


@dataclass(frozen=True)
class DemoLoadResult:
    profile: ProfileName
    tenant_id: UUID
    counts: dict[str, Any]
    crypto_seeded: bool
    crypto_skip_reason: str | None
    manifest: dict[str, Any]


async def load_demo_dataset(
    conn: asyncpg.Connection,
    *,
    tenant_id: UUID,
    receptionist_person_id: UUID,
    receptionist_account_id: UUID | None = None,
    profile: str = "demo",
    seed: int | None = None,
    now_utc: datetime | None = None,
) -> DemoLoadResult:
    """Insert rich demo rows for an existing tenant after roles/migrations seed."""
    profile_name, targets = resolve_profile(profile)
    # Tenant-scoped seed: deterministic per (profile seed, tenant) so fixture IDs
    # never collide on PRIMARY KEY when multiple tenants share one PostgreSQL
    # (CI session-scoped Testcontainers). Preview remains stable for a given tenant.
    base_seed = seed if seed is not None else targets.seed
    tenant_salt = (tenant_id.int % 999_983) + 1
    effective_seed = base_seed + tenant_salt
    if effective_seed != targets.seed:
        targets = DemoTargets(**{**targets_as_dict(targets), "seed": effective_seed})
    now = now_utc or datetime.now(timezone.utc)
    today = tehran_today(now)

    people = build_patients(targets)
    staff_bundle = build_staff(targets)
    catalog = build_catalog(targets, now=now)
    appts = build_appointments(
        targets,
        patients=people.patients,
        catalog=catalog,
        staff=staff_bundle.staff,
        receptionist_person_id=receptionist_person_id,
        now_utc=now,
    )
    crypto = plan_crypto_rows(targets, tenant_id=tenant_id, patients=people.patients)

    await conn.execute("SET ROLE db_migrator")
    await conn.execute(
        "SELECT set_config('app.current_tenant_id', $1, false)", str(tenant_id)
    )
    await persist_identity_graph(
        conn, tenant_id=tenant_id, targets=targets, people=people, staff=staff_bundle, now=now
    )
    await persist_catalog(
        conn, tenant_id=tenant_id, catalog=catalog, staff=staff_bundle, now=now
    )
    await persist_crypto(conn, tenant_id=tenant_id, crypto=crypto, now=now)
    await persist_appointments(conn, tenant_id=tenant_id, targets=targets, appts=appts)
    audit_count = await persist_audit(
        conn,
        tenant_id=tenant_id,
        targets=targets,
        profile_name=profile_name,
        people=people,
        appts=appts,
        crypto=crypto,
        actor=receptionist_account_id,
        now=now,
    )
    await conn.execute("RESET ROLE")

    today_count = sum(
        1 for a in appts.appointments if a.start_utc.astimezone(TEHRAN).date() == today
    )
    tomorrow = today.fromordinal(today.toordinal() + 1)
    tomorrow_count = sum(
        1 for a in appts.appointments if a.start_utc.astimezone(TEHRAN).date() == tomorrow
    )
    status_counts: dict[str, int] = {}
    for a in appts.appointments:
        status_counts[a.status] = status_counts.get(a.status, 0) + 1

    counts = {
        "patients": len(people.patients),
        "inactive_patients": sum(1 for p in people.patients if not p.is_active),
        "exceptional_identity_patients": sum(
            1 for p in people.patients if p.exception_reason
        ),
        "national_id_patients_planned": sum(1 for p in people.patients if p.national_id),
        "national_id_rows_inserted": len(crypto.identifiers),
        "shared_phone_families_planned": len(
            {
                p.shared_phone_family
                for p in people.patients
                if p.shared_phone_family is not None
            }
        ),
        "phone_rows_inserted": len(crypto.phones),
        "staff": len(staff_bundle.staff),
        "services": len(catalog.services),
        "rooms": len(catalog.rooms),
        "appointments": len(appts.appointments),
        "appointments_today": today_count,
        "appointments_tomorrow": tomorrow_count,
        "appointments_by_status": status_counts,
        "manual_overlap_pairs": appts.manual_overlap_pairs,
        "checked_in_waiting_today": appts.checked_in_waiting_today,
        "multi_service_groups": appts.multi_service_group_count,
        "audit_entries": audit_count,
        "tehran_today": today.isoformat(),
    }
    manifest = {
        "profile": profile_name,
        "seed": targets.seed,
        "targets": targets_as_dict(targets),
        "counts": counts,
        "crypto_seeded": crypto.available,
        "crypto_skip_reason": crypto.skip_reason,
        "generated_at_utc": now.isoformat(),
        "tenant_id": str(tenant_id),
        "notes": [
            "Synthetic data only; National IDs/phones are not real persons.",
            "Dates anchored to Asia/Tehran calendar day at generation time.",
            "No finance/inventory rows (tp0001–tp0007 only).",
            "RLS left enabled; inserts run as db_migrator with tenant GUC.",
        ],
    }
    return DemoLoadResult(
        profile=profile_name,
        tenant_id=tenant_id,
        counts=counts,
        crypto_seeded=crypto.available,
        crypto_skip_reason=crypto.skip_reason,
        manifest=manifest,
    )


DEFAULT_SEED = DEMO_SEED

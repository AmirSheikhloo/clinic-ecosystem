"""Batch SQL persistence helpers for the demo dataset loader."""

from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID

import asyncpg

from clinic_ecosystem.infrastructure.auth.passwords import hash_password
from clinic_ecosystem.infrastructure.demo.builders_appointments import AppointmentBundle
from clinic_ecosystem.infrastructure.demo.builders_catalog import CatalogBundle
from clinic_ecosystem.infrastructure.demo.builders_people import PeopleBundle
from clinic_ecosystem.infrastructure.demo.crypto_hooks import CryptoSeedPlan
from clinic_ecosystem.infrastructure.demo.ids import demo_uuid
from clinic_ecosystem.infrastructure.demo.profiles import DemoTargets

BATCH = 500
DEMO_RECV_PASSWORD = "BetaDemo-Receptionist-Only!"


async def copy_rows(
    conn: asyncpg.Connection, table: str, columns: list[str], rows: list[tuple]
) -> None:
    if not rows:
        return
    for i in range(0, len(rows), BATCH):
        await conn.copy_records_to_table(
            table, records=rows[i : i + BATCH], columns=columns
        )


async def persist_identity_graph(
    conn: asyncpg.Connection,
    *,
    tenant_id: UUID,
    targets: DemoTargets,
    people: PeopleBundle,
    staff: PeopleBundle,
    now: datetime,
) -> None:
    person_rows = [
        (p.id, tenant_id, p.first_name, p.last_name, p.birth_date, p.gender, 1, now, now)
        for p in (*people.persons, *staff.persons)
    ]
    await copy_rows(
        conn,
        "tenant_persons",
        [
            "id", "tenant_id", "first_name", "last_name", "birth_date", "gender",
            "aggregate_version", "created_at_utc", "updated_at_utc",
        ],
        person_rows,
    )
    await copy_rows(
        conn,
        "patient_profiles",
        ["id", "tenant_id", "person_id", "dossier_number", "is_active", "created_at_utc"],
        [
            (p.id, tenant_id, p.person_id, p.dossier_number, p.is_active, now)
            for p in people.patients
        ],
    )
    await copy_rows(
        conn,
        "staff_profiles",
        [
            "id", "tenant_id", "person_id", "staff_kind", "medical_council_code",
            "is_active", "created_at_utc",
        ],
        [
            (s.id, tenant_id, s.person_id, s.staff_kind, s.medical_council_code, s.is_active, now)
            for s in staff.staff
        ],
    )
    pwd = hash_password(DEMO_RECV_PASSWORD)
    login_rows = []
    for staff_index, s in enumerate(staff.staff):
        if not s.with_login or not s.login_identifier:
            continue
        login_rows.append(
            (
                demo_uuid(targets.seed, "staff_account", staff_index),
                tenant_id,
                s.person_id,
                s.login_identifier,
                s.login_identifier.lower(),
                pwd,
                True,
                0,
                None,
                now,
                1,
                now,
                now,
            )
        )
    await copy_rows(
        conn,
        "user_accounts",
        [
            "id", "tenant_id", "person_id", "login_identifier",
            "normalized_login_identifier", "password_hash_argon2id", "is_active",
            "failed_login_attempts", "locked_until_utc", "password_changed_at_utc",
            "aggregate_version", "created_at_utc", "updated_at_utc",
        ],
        login_rows,
    )


async def persist_catalog(
    conn: asyncpg.Connection,
    *,
    tenant_id: UUID,
    catalog: CatalogBundle,
    staff: PeopleBundle,
    now: datetime,
) -> None:
    await copy_rows(
        conn,
        "services",
        [
            "id", "tenant_id", "service_code", "service_name", "default_duration_minutes",
            "default_price_irr", "is_active", "aggregate_version", "created_at_utc",
            "updated_at_utc",
        ],
        [
            (s.id, tenant_id, s.code, s.name, s.duration_minutes, s.price_irr, True, 1, now, now)
            for s in catalog.services
        ],
    )
    resource_rows = [
        (r.id, tenant_id, r.resource_type, r.name, r.is_active, now) for r in catalog.rooms
    ]
    for s in staff.staff:
        if s.resource_id and s.resource_name:
            resource_rows.append(
                (s.resource_id, tenant_id, "PRACTITIONER", s.resource_name, True, now)
            )
    await copy_rows(
        conn,
        "bookable_resources",
        ["id", "tenant_id", "resource_type", "resource_name", "is_active", "created_at_utc"],
        resource_rows,
    )
    await copy_rows(
        conn,
        "service_resource_requirements",
        [
            "id", "tenant_id", "service_id", "requirement_group", "required_resource_type",
            "specific_resource_id", "quantity_required", "created_at_utc",
        ],
        [
            (
                r.id, tenant_id, r.service_id, r.group, r.resource_type,
                r.specific_resource_id, r.quantity, now,
            )
            for r in catalog.requirements
        ],
    )


async def persist_crypto(
    conn: asyncpg.Connection,
    *,
    tenant_id: UUID,
    crypto: CryptoSeedPlan,
    now: datetime,
) -> None:
    if not crypto.available:
        return
    await copy_rows(
        conn,
        "person_identifiers",
        [
            "id", "tenant_id", "person_id", "id_type", "issuing_country_or_authority",
            "id_ciphertext", "nonce_96bit", "auth_tag_128bit", "encryption_key_version",
            "aad_version", "masked_display", "verification_status", "lookup_hmac_active",
            "hmac_key_version_active", "lookup_hmac_next", "hmac_key_version_next",
            "created_at_utc",
        ],
        [
            (
                row.id, tenant_id, row.person_id, row.id_type, row.authority,
                row.sealed.ciphertext, row.sealed.nonce_96bit, row.sealed.auth_tag_128bit,
                row.sealed.encryption_key_version, row.sealed.aad_version,
                row.sealed.masked_display, "SYNTACTICALLY_VALID_UNVERIFIED",
                row.sealed.lookup_hmac, row.sealed.hmac_key_version, None, None, now,
            )
            for row in crypto.identifiers
        ],
    )
    await copy_rows(
        conn,
        "person_phones",
        [
            "id", "tenant_id", "person_id", "phone_ciphertext", "nonce_96bit",
            "auth_tag_128bit", "encryption_key_version", "aad_version", "masked_phone",
            "phone_lookup_hmac", "hmac_key_version", "is_primary", "is_shared_phone",
            "phone_verified_at_utc", "created_at_utc",
        ],
        [
            (
                row.id, tenant_id, row.person_id, row.sealed.ciphertext, row.sealed.nonce_96bit,
                row.sealed.auth_tag_128bit, row.sealed.encryption_key_version,
                row.sealed.aad_version, row.sealed.masked_display, row.sealed.lookup_hmac,
                row.sealed.hmac_key_version, row.is_primary, row.is_shared_phone, None, now,
            )
            for row in crypto.phones
        ],
    )


async def persist_appointments(
    conn: asyncpg.Connection,
    *,
    tenant_id: UUID,
    targets: DemoTargets,
    appts: AppointmentBundle,
) -> None:
    appt_rows = []
    alloc_params = []
    for i, a in enumerate(appts.appointments):
        appt_rows.append(
            (
                a.id, tenant_id, a.patient_id, a.booker_person_id, a.note, a.service_id,
                a.status, a.booking_channel, a.capacity_pool, a.start_utc, a.end_utc,
                None, 1, a.created_at, a.created_at,
            )
        )
        alloc_params.append(
            (
                demo_uuid(targets.seed, "allocation", i),
                tenant_id,
                a.id,
                a.resource_id,
                a.booking_channel,
                a.capacity_pool,
                a.allocation_status,
                a.start_utc,
                a.end_utc,
                a.created_at,
            )
        )
    await copy_rows(
        conn,
        "appointments",
        [
            "id", "tenant_id", "beneficiary_patient_id", "booker_person_id",
            "patient_booking_note", "service_id", "status", "booking_channel",
            "capacity_pool", "scheduled_start_at_utc", "scheduled_end_at_utc",
            "hold_expires_at_utc", "aggregate_version", "created_at_utc", "updated_at_utc",
        ],
        appt_rows,
    )
    for i in range(0, len(alloc_params), BATCH):
        await conn.executemany(
            """
            INSERT INTO appointment_resource_allocations (
                id, tenant_id, appointment_id, resource_id, booking_channel,
                capacity_pool, allocation_status, time_slot, created_at_utc
            ) VALUES (
                $1,$2,$3,$4,$5,$6,$7, tstzrange($8::timestamptz, $9::timestamptz, '[)'), $10
            )
            """,
            alloc_params[i : i + BATCH],
        )


async def persist_audit(
    conn: asyncpg.Connection,
    *,
    tenant_id: UUID,
    targets: DemoTargets,
    profile_name: str,
    people: PeopleBundle,
    appts: AppointmentBundle,
    crypto: CryptoSeedPlan,
    actor: UUID | None,
    now: datetime,
) -> int:
    audit_rows: list[tuple] = []
    for i, p in enumerate(people.patients):
        audit_rows.append(
            (
                demo_uuid(targets.seed, "audit_patient", i),
                tenant_id,
                "USER_ACCOUNT",
                actor,
                "patient.registered",
                "patient_profile",
                p.id,
                json.dumps(
                    {
                        "demo": True,
                        "identity_exception_reason": p.exception_reason,
                        "national_id_stored": bool(p.national_id and crypto.available),
                    }
                ),
                now,
            )
        )
    for i, a in enumerate(appts.appointments):
        if len(audit_rows) >= targets.audit_entries:
            break
        audit_rows.append(
            (
                demo_uuid(targets.seed, "audit_appt", i),
                tenant_id,
                "USER_ACCOUNT",
                actor,
                f"appointment.demo_{a.status.lower()}",
                "appointment",
                a.id,
                json.dumps(
                    {"demo": True, "status": a.status, "capacity_pool": a.capacity_pool}
                ),
                a.created_at,
            )
        )
    pad = 0
    while len(audit_rows) < targets.audit_entries:
        audit_rows.append(
            (
                demo_uuid(targets.seed, "audit_pad", pad),
                tenant_id,
                "USER_ACCOUNT",
                actor,
                "demo.seed_marker",
                "demo_dataset",
                demo_uuid(targets.seed, "demo_marker", 0),
                json.dumps({"demo": True, "pad": pad, "profile": profile_name}),
                now,
            )
        )
        pad += 1
    for i in range(0, len(audit_rows), BATCH):
        await conn.executemany(
            """
            INSERT INTO audit_entries (
                id, tenant_id, actor_type, actor_id, operation,
                target_type, target_id, details_json, created_at_utc
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,CAST($8 AS jsonb),$9)
            """,
            audit_rows[i : i + BATCH],
        )
    return len(audit_rows)

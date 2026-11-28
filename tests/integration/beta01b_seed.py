"""Synthetic fixtures for BETA-01B reception integration tests.

All credentials and identifiers are test-only. No real patient PII.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

import asyncpg

from clinic_ecosystem.infrastructure.auth.passwords import hash_password
from clinic_ecosystem.infrastructure.auth.settings import (
    APPOINTMENTS_LIST,
    APPOINTMENTS_SCHEDULE_MANUAL,
    CATALOG_RESOURCES_READ,
    CATALOG_SERVICES_READ,
    PATIENTS_REGISTER,
    PATIENTS_SEARCH,
)
from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7

TEST_RECEPTIONIST_PASSWORD = "Beta01b-Receptionist-Test-Only!"
TEST_UNAUTHORIZED_PASSWORD = "Beta01b-Unauthorized-Test-Only!"
TEST_SCHEDULE_ONLY_PASSWORD = "Beta01b-ScheduleOnly-Test-Only!"
TEST_NO_OVERBOOK_PASSWORD = "Beta01b-NoOverbook-Test-Only!"

BETA01B_PERMISSIONS = (
    CATALOG_SERVICES_READ,
    CATALOG_RESOURCES_READ,
    PATIENTS_REGISTER,
    PATIENTS_SEARCH,
    APPOINTMENTS_SCHEDULE_MANUAL,
    APPOINTMENTS_LIST,
)


@dataclass(frozen=True)
class Beta01bSeed:
    tenant_a_id: UUID
    tenant_b_id: UUID
    receptionist_account_id: UUID
    unauthorized_account_id: UUID
    schedule_only_account_id: UUID
    no_overbook_account_id: UUID
    receptionist_login: str
    unauthorized_login: str
    schedule_only_login: str
    no_overbook_login: str
    receptionist_password: str
    unauthorized_password: str
    schedule_only_password: str
    no_overbook_password: str
    receptionist_person_id: UUID
    service_a_id: UUID
    service_b_id: UUID
    service_inactive_id: UUID
    service_no_req_id: UUID
    service_multi_id: UUID
    resource_a_id: UUID
    resource_a2_id: UUID
    resource_b_id: UUID
    resource_inactive_id: UUID
    patient_a_id: UUID
    patient_a_person_id: UUID
    patient_b_id: UUID
    patient_inactive_id: UUID
    role_recv_id: UUID


async def seed_beta01b_reception(conn: asyncpg.Connection) -> Beta01bSeed:
    """Seed two tenants with reception graph, permissions, and isolation fixtures."""
    now = datetime.now(timezone.utc)
    tenant_a = new_uuid7()
    tenant_b = new_uuid7()

    person_recv = new_uuid7()
    person_unauth = new_uuid7()
    person_sched = new_uuid7()
    person_no_over = new_uuid7()
    person_patient_a = new_uuid7()
    person_b = new_uuid7()
    person_patient_b = new_uuid7()

    recv_account = new_uuid7()
    unauth_account = new_uuid7()
    sched_account = new_uuid7()
    no_over_account = new_uuid7()

    role_recv = new_uuid7()
    role_unauth = new_uuid7()
    role_sched = new_uuid7()
    role_no_over = new_uuid7()

    service_a = new_uuid7()
    service_b = new_uuid7()
    service_inactive = new_uuid7()
    service_no_req = new_uuid7()
    service_multi = new_uuid7()
    resource_a = new_uuid7()
    resource_a2 = new_uuid7()
    resource_b = new_uuid7()
    resource_inactive = new_uuid7()
    patient_a = new_uuid7()
    patient_b = new_uuid7()
    person_patient_inactive = new_uuid7()
    patient_inactive = new_uuid7()

    recv_login = "receptionist@beta01b.test"
    unauth_login = "clerk-no-perms@beta01b.test"
    sched_login = "schedule-only@beta01b.test"
    no_over_login = "no-overbook@beta01b.test"

    recv_hash = hash_password(TEST_RECEPTIONIST_PASSWORD)
    unauth_hash = hash_password(TEST_UNAUTHORIZED_PASSWORD)
    sched_hash = hash_password(TEST_SCHEDULE_ONLY_PASSWORD)
    no_over_hash = hash_password(TEST_NO_OVERBOOK_PASSWORD)

    await conn.execute("SET ROLE db_migrator")

    for tid in (tenant_a, tenant_b):
        await conn.execute(
            """
            INSERT INTO tenant_registry
                (tenant_id, tenant_status, timezone_name, created_at_utc, updated_at_utc)
            VALUES ($1, 'ACTIVE', 'Asia/Tehran', $2, $2)
            """,
            tid,
            now,
        )

    await conn.execute(
        "SELECT set_config('app.current_tenant_id', $1, false)", str(tenant_a)
    )

    await conn.execute(
        """
        INSERT INTO tenant_persons (
            id, tenant_id, first_name, last_name, birth_date, gender,
            aggregate_version, created_at_utc, updated_at_utc
        ) VALUES
            ($1, $2, 'سارا', 'نائینی', NULL, NULL, 1, $3, $3),
            ($4, $2, 'مینا', 'بی‌مجوز', NULL, NULL, 1, $3, $3),
            ($5, $2, 'سامان', 'نوبت‌کار', NULL, NULL, 1, $3, $3),
            ($6, $2, 'پویا', 'Alpha', NULL, NULL, 1, $3, $3),
            ($7, $2, 'اینا', 'غیرفعال', NULL, NULL, 1, $3, $3),
            ($8, $2, 'نادر', 'بدون‌اوربوک', NULL, NULL, 1, $3, $3)
        """,
        person_recv,
        tenant_a,
        now,
        person_unauth,
        person_sched,
        person_patient_a,
        person_patient_inactive,
        person_no_over,
    )
    await conn.execute(
        """
        INSERT INTO patient_profiles (
            id, tenant_id, person_id, dossier_number, is_active, created_at_utc
        ) VALUES
            ($1, $2, $3, NULL, TRUE, $4),
            ($5, $2, $6, NULL, FALSE, $4)
        """,
        patient_a,
        tenant_a,
        person_patient_a,
        now,
        patient_inactive,
        person_patient_inactive,
    )
    await conn.execute(
        """
        INSERT INTO user_accounts (
            id, tenant_id, person_id, login_identifier, normalized_login_identifier,
            password_hash_argon2id, is_active, failed_login_attempts, locked_until_utc,
            password_changed_at_utc, aggregate_version, created_at_utc, updated_at_utc
        ) VALUES
            ($1, $2, $3, $4, $4, $5, TRUE, 0, NULL, $6, 1, $6, $6),
            ($7, $2, $8, $9, $9, $10, TRUE, 0, NULL, $6, 1, $6, $6),
            ($11, $2, $12, $13, $13, $14, TRUE, 0, NULL, $6, 1, $6, $6),
            ($15, $2, $16, $17, $17, $18, TRUE, 0, NULL, $6, 1, $6, $6)
        """,
        recv_account,
        tenant_a,
        person_recv,
        recv_login,
        recv_hash,
        now,
        unauth_account,
        person_unauth,
        unauth_login,
        unauth_hash,
        sched_account,
        person_sched,
        sched_login,
        sched_hash,
        no_over_account,
        person_no_over,
        no_over_login,
        no_over_hash,
    )
    await conn.execute(
        """
        INSERT INTO tenant_roles (id, tenant_id, role_code, role_name, is_system_defined, created_at_utc)
        VALUES
            ($1, $2, 'RECEPTIONIST', 'Receptionist', TRUE, $3),
            ($4, $2, 'CLERK_NO_PERMS', 'Clerk without perms', TRUE, $3),
            ($5, $2, 'OVERBOOK_ONLY', 'Overlap only', TRUE, $3),
            ($6, $2, 'SCHED_NO_OVERBOOK', 'Schedule without overbook', TRUE, $3)
        """,
        role_recv,
        tenant_a,
        now,
        role_unauth,
        role_sched,
        role_no_over,
    )
    await conn.execute(
        """
        INSERT INTO user_role_assignments (id, tenant_id, user_account_id, role_id, assigned_at_utc)
        VALUES
            ($1, $2, $3, $4, $5),
            ($6, $2, $7, $8, $5),
            ($9, $2, $10, $11, $5),
            ($12, $2, $13, $14, $5)
        """,
        new_uuid7(),
        tenant_a,
        recv_account,
        role_recv,
        now,
        new_uuid7(),
        unauth_account,
        role_unauth,
        new_uuid7(),
        sched_account,
        role_sched,
        new_uuid7(),
        no_over_account,
        role_no_over,
    )
    for code in BETA01B_PERMISSIONS:
        await conn.execute(
            """
            INSERT INTO role_permission_assignments (
                id, tenant_id, role_id, permission_code, granted_at_utc
            ) VALUES ($1, $2, $3, $4, $5)
            """,
            new_uuid7(),
            tenant_a,
            role_recv,
            code,
            now,
        )
        await conn.execute(
            """
            INSERT INTO role_permission_assignments (
                id, tenant_id, role_id, permission_code, granted_at_utc
            ) VALUES ($1, $2, $3, $4, $5)
            """,
            new_uuid7(),
            tenant_a,
            role_no_over,
            code,
            now,
        )
    # schedule-only principal: ALLOW_MANUAL_OVERBOOKING without ordinary schedule permission
    await conn.execute(
        """
        INSERT INTO role_permission_assignments (
            id, tenant_id, role_id, permission_code, granted_at_utc
        ) VALUES ($1, $2, $3, 'ALLOW_MANUAL_OVERBOOKING', $4)
        """,
        new_uuid7(),
        tenant_a,
        role_sched,
        now,
    )
    # Receptionist also gets overlap privilege for overlap-ack tests.
    await conn.execute(
        """
        INSERT INTO role_permission_assignments (
            id, tenant_id, role_id, permission_code, granted_at_utc
        ) VALUES ($1, $2, $3, 'ALLOW_MANUAL_OVERBOOKING', $4)
        """,
        new_uuid7(),
        tenant_a,
        role_recv,
        now,
    )

    await conn.execute(
        """
        INSERT INTO services (
            id, tenant_id, service_code, service_name, default_duration_minutes,
            default_price_irr, is_active, aggregate_version, created_at_utc, updated_at_utc
        ) VALUES
            ($1, $2, 'CONSULT', 'Tenant A Consultation', 30, 150000, TRUE, 1, $3, $3),
            ($4, $2, 'INACTIVE', 'Inactive Service', 30, 1000, FALSE, 1, $3, $3),
            ($5, $2, 'NOREQ', 'No Requirement Service', 15, 5000, TRUE, 1, $3, $3),
            ($6, $2, 'MULTI', 'Multi Resource Service', 45, 200000, TRUE, 1, $3, $3)
        """,
        service_a,
        tenant_a,
        now,
        service_inactive,
        service_no_req,
        service_multi,
    )
    await conn.execute(
        """
        INSERT INTO bookable_resources (
            id, tenant_id, resource_type, resource_name, is_active, created_at_utc
        ) VALUES
            ($1, $2, 'ROOM', 'Room Alpha', TRUE, $3),
            ($4, $2, 'PRACTITIONER', 'Dr Alpha', TRUE, $3),
            ($5, $2, 'ROOM', 'Room Inactive', FALSE, $3)
        """,
        resource_a,
        tenant_a,
        now,
        resource_a2,
        resource_inactive,
    )
    await conn.execute(
        """
        INSERT INTO service_resource_requirements (
            id, tenant_id, service_id, requirement_group, required_resource_type,
            specific_resource_id, quantity_required, created_at_utc
        ) VALUES
            ($1, $2, $3, 'primary', 'ROOM', NULL, 1, $4),
            ($5, $2, $6, 'room', 'ROOM', NULL, 1, $4),
            ($7, $2, $6, 'doctor', 'PRACTITIONER', $8, 1, $4)
        """,
        new_uuid7(),
        tenant_a,
        service_a,
        now,
        new_uuid7(),
        service_multi,
        new_uuid7(),
        resource_a2,
    )

    # Tenant B isolation fixtures
    await conn.execute(
        "SELECT set_config('app.current_tenant_id', $1, false)", str(tenant_b)
    )
    await conn.execute(
        """
        INSERT INTO tenant_persons (
            id, tenant_id, first_name, last_name, birth_date, gender,
            aggregate_version, created_at_utc, updated_at_utc
        ) VALUES
            ($1, $2, 'Other', 'Staff', NULL, NULL, 1, $3, $3),
            ($4, $2, 'Secret', 'Patient', NULL, NULL, 1, $3, $3)
        """,
        person_b,
        tenant_b,
        now,
        person_patient_b,
    )
    await conn.execute(
        """
        INSERT INTO patient_profiles (
            id, tenant_id, person_id, dossier_number, is_active, created_at_utc
        ) VALUES ($1, $2, $3, NULL, TRUE, $4)
        """,
        patient_b,
        tenant_b,
        person_patient_b,
        now,
    )
    await conn.execute(
        """
        INSERT INTO services (
            id, tenant_id, service_code, service_name, default_duration_minutes,
            default_price_irr, is_active, aggregate_version, created_at_utc, updated_at_utc
        ) VALUES ($1, $2, 'SECRET', 'Tenant B Hidden Service', 45, 999999, TRUE, 1, $3, $3)
        """,
        service_b,
        tenant_b,
        now,
    )
    await conn.execute(
        """
        INSERT INTO bookable_resources (
            id, tenant_id, resource_type, resource_name, is_active, created_at_utc
        ) VALUES ($1, $2, 'ROOM', 'Room Bravo', TRUE, $3)
        """,
        resource_b,
        tenant_b,
        now,
    )
    await conn.execute(
        """
        INSERT INTO service_resource_requirements (
            id, tenant_id, service_id, requirement_group, required_resource_type,
            specific_resource_id, quantity_required, created_at_utc
        ) VALUES ($1, $2, $3, 'primary', 'ROOM', NULL, 1, $4)
        """,
        new_uuid7(),
        tenant_b,
        service_b,
        now,
    )

    await conn.execute("RESET ROLE")
    return Beta01bSeed(
        tenant_a_id=tenant_a,
        tenant_b_id=tenant_b,
        receptionist_account_id=recv_account,
        unauthorized_account_id=unauth_account,
        schedule_only_account_id=sched_account,
        no_overbook_account_id=no_over_account,
        receptionist_login=recv_login,
        unauthorized_login=unauth_login,
        schedule_only_login=sched_login,
        no_overbook_login=no_over_login,
        receptionist_password=TEST_RECEPTIONIST_PASSWORD,
        unauthorized_password=TEST_UNAUTHORIZED_PASSWORD,
        schedule_only_password=TEST_SCHEDULE_ONLY_PASSWORD,
        no_overbook_password=TEST_NO_OVERBOOK_PASSWORD,
        receptionist_person_id=person_recv,
        service_a_id=service_a,
        service_b_id=service_b,
        service_inactive_id=service_inactive,
        service_no_req_id=service_no_req,
        service_multi_id=service_multi,
        resource_a_id=resource_a,
        resource_a2_id=resource_a2,
        resource_b_id=resource_b,
        resource_inactive_id=resource_inactive,
        patient_a_id=patient_a,
        patient_a_person_id=person_patient_a,
        patient_b_id=patient_b,
        patient_inactive_id=patient_inactive,
        role_recv_id=role_recv,
    )

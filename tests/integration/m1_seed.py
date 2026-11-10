"""Seed helpers for M1-01 ScheduleAppointment integration tests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

import asyncpg

from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7


@dataclass(frozen=True)
class SeedIds:
    tenant_id: UUID
    person_id: UUID
    patient_id: UUID
    user_account_id: UUID
    role_id: UUID
    service_id: UUID
    resource_id: UUID
    requirement_id: UUID


async def seed_scheduling_graph(
    conn: asyncpg.Connection,
    *,
    grant_manual_overbooking: bool = True,
) -> SeedIds:
    now = datetime.now(timezone.utc)
    ids = SeedIds(
        tenant_id=new_uuid7(),
        person_id=new_uuid7(),
        patient_id=new_uuid7(),
        user_account_id=new_uuid7(),
        role_id=new_uuid7(),
        service_id=new_uuid7(),
        resource_id=new_uuid7(),
        requirement_id=new_uuid7(),
    )
    await conn.execute(
        """
        INSERT INTO tenant_registry (tenant_id, tenant_status, timezone_name, created_at_utc, updated_at_utc)
        VALUES ($1, 'ACTIVE', 'Asia/Tehran', $2, $2)
        """,
        ids.tenant_id,
        now,
    )
    await conn.execute("SELECT set_config('app.current_tenant_id', $1, false)", str(ids.tenant_id))
    await conn.execute(
        """
        INSERT INTO tenant_persons (
            id, tenant_id, first_name, last_name, birth_date, gender,
            aggregate_version, created_at_utc, updated_at_utc
        ) VALUES ($1, $2, 'Ada', 'Clinic', NULL, NULL, 1, $3, $3)
        """,
        ids.person_id,
        ids.tenant_id,
        now,
    )
    await conn.execute(
        """
        INSERT INTO patient_profiles (
            id, tenant_id, person_id, dossier_number, is_active, created_at_utc
        ) VALUES ($1, $2, $3, 'D-1', TRUE, $4)
        """,
        ids.patient_id,
        ids.tenant_id,
        ids.person_id,
        now,
    )
    await conn.execute(
        """
        INSERT INTO user_accounts (
            id, tenant_id, person_id, login_identifier, normalized_login_identifier,
            password_hash_argon2id, is_active, failed_login_attempts, locked_until_utc,
            password_changed_at_utc, aggregate_version, created_at_utc, updated_at_utc
        ) VALUES (
            $1, $2, $3, 'receptionist@example.test', 'receptionist@example.test',
            '$argon2id$placeholder', TRUE, 0, NULL, NULL, 1, $4, $4
        )
        """,
        ids.user_account_id,
        ids.tenant_id,
        ids.person_id,
        now,
    )
    await conn.execute(
        """
        INSERT INTO tenant_roles (id, tenant_id, role_code, role_name, is_system_defined, created_at_utc)
        VALUES ($1, $2, 'RECEPTIONIST', 'Receptionist', TRUE, $3)
        """,
        ids.role_id,
        ids.tenant_id,
        now,
    )
    await conn.execute(
        """
        INSERT INTO user_role_assignments (id, tenant_id, user_account_id, role_id, assigned_at_utc)
        VALUES ($1, $2, $3, $4, $5)
        """,
        new_uuid7(),
        ids.tenant_id,
        ids.user_account_id,
        ids.role_id,
        now,
    )
    if grant_manual_overbooking:
        await conn.execute(
            """
            INSERT INTO role_permission_assignments (
                id, tenant_id, role_id, permission_code, granted_at_utc
            ) VALUES ($1, $2, $3, 'ALLOW_MANUAL_OVERBOOKING', $4)
            """,
            new_uuid7(),
            ids.tenant_id,
            ids.role_id,
            now,
        )
    await conn.execute(
        """
        INSERT INTO services (
            id, tenant_id, service_code, service_name, default_duration_minutes,
            default_price_irr, is_active, aggregate_version, created_at_utc, updated_at_utc
        ) VALUES ($1, $2, 'CONSULT', 'Consultation', 30, 100000, TRUE, 1, $3, $3)
        """,
        ids.service_id,
        ids.tenant_id,
        now,
    )
    await conn.execute(
        """
        INSERT INTO bookable_resources (
            id, tenant_id, resource_type, resource_name, is_active, created_at_utc
        ) VALUES ($1, $2, 'ROOM', 'Room A', TRUE, $3)
        """,
        ids.resource_id,
        ids.tenant_id,
        now,
    )
    await conn.execute(
        """
        INSERT INTO service_resource_requirements (
            id, tenant_id, service_id, requirement_group, required_resource_type,
            specific_resource_id, quantity_required, created_at_utc
        ) VALUES ($1, $2, $3, 'primary', 'ROOM', NULL, 1, $4)
        """,
        ids.requirement_id,
        ids.tenant_id,
        ids.service_id,
        now,
    )
    return ids

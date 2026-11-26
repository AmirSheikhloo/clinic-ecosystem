"""Synthetic fixtures for BETA-01A auth + catalog integration tests.

All credentials and identifiers are test-only. No real patient PII.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

import asyncpg

from clinic_ecosystem.infrastructure.auth.passwords import hash_password
from clinic_ecosystem.infrastructure.auth.settings import CATALOG_SERVICES_READ
from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7

# Deterministic synthetic plaintext passwords for tests only (never production).
TEST_RECEPTIONIST_PASSWORD = "Beta01a-Receptionist-Test-Only!"
TEST_UNAUTHORIZED_PASSWORD = "Beta01a-Unauthorized-Test-Only!"


@dataclass(frozen=True)
class Beta01aSeed:
    tenant_a_id: UUID
    tenant_b_id: UUID
    receptionist_account_id: UUID
    unauthorized_account_id: UUID
    receptionist_login: str
    unauthorized_login: str
    service_a_id: UUID
    service_b_id: UUID
    receptionist_password: str
    unauthorized_password: str


async def seed_beta01a_auth_catalog(conn: asyncpg.Connection) -> Beta01aSeed:
    """Seed two tenants, authorized + unauthorized users, and tenant-scoped services.

    Caller must be connected as a role that can SET ROLE db_migrator (fixture setup).
    """
    now = datetime.now(timezone.utc)
    tenant_a = new_uuid7()
    tenant_b = new_uuid7()
    person_recv = new_uuid7()
    person_unauth = new_uuid7()
    person_b = new_uuid7()
    recv_account = new_uuid7()
    unauth_account = new_uuid7()
    role_recv = new_uuid7()
    role_unauth = new_uuid7()
    service_a = new_uuid7()
    service_b = new_uuid7()

    recv_login = "receptionist@beta01a.test"
    unauth_login = "clerk-no-catalog@beta01a.test"
    recv_hash = hash_password(TEST_RECEPTIONIST_PASSWORD)
    unauth_hash = hash_password(TEST_UNAUTHORIZED_PASSWORD)

    await conn.execute("SET ROLE db_migrator")

    for tid, status in ((tenant_a, "ACTIVE"), (tenant_b, "ACTIVE")):
        await conn.execute(
            """
            INSERT INTO tenant_registry
                (tenant_id, tenant_status, timezone_name, created_at_utc, updated_at_utc)
            VALUES ($1, $2, 'Asia/Tehran', $3, $3)
            """,
            tid,
            status,
            now,
        )

    # Tenant A graph
    await conn.execute(
        "SELECT set_config('app.current_tenant_id', $1, false)", str(tenant_a)
    )
    await conn.execute(
        """
        INSERT INTO tenant_persons (
            id, tenant_id, first_name, last_name, birth_date, gender,
            aggregate_version, created_at_utc, updated_at_utc
        ) VALUES
            ($1, $2, 'Rita', 'Reception', NULL, NULL, 1, $3, $3),
            ($4, $2, 'Uma', 'Unauthorized', NULL, NULL, 1, $3, $3)
        """,
        person_recv,
        tenant_a,
        now,
        person_unauth,
    )
    await conn.execute(
        """
        INSERT INTO user_accounts (
            id, tenant_id, person_id, login_identifier, normalized_login_identifier,
            password_hash_argon2id, is_active, failed_login_attempts, locked_until_utc,
            password_changed_at_utc, aggregate_version, created_at_utc, updated_at_utc
        ) VALUES
            ($1, $2, $3, $4, $5, $6, TRUE, 0, NULL, $7, 1, $7, $7),
            ($8, $2, $9, $10, $11, $12, TRUE, 0, NULL, $7, 1, $7, $7)
        """,
        recv_account,
        tenant_a,
        person_recv,
        recv_login,
        recv_login,
        recv_hash,
        now,
        unauth_account,
        person_unauth,
        unauth_login,
        unauth_login,
        unauth_hash,
    )
    await conn.execute(
        """
        INSERT INTO tenant_roles (id, tenant_id, role_code, role_name, is_system_defined, created_at_utc)
        VALUES
            ($1, $2, 'RECEPTIONIST', 'Receptionist', TRUE, $3),
            ($4, $2, 'CLERK_NO_CATALOG', 'Clerk without catalog', TRUE, $3)
        """,
        role_recv,
        tenant_a,
        now,
        role_unauth,
    )
    await conn.execute(
        """
        INSERT INTO user_role_assignments (id, tenant_id, user_account_id, role_id, assigned_at_utc)
        VALUES
            ($1, $2, $3, $4, $5),
            ($6, $2, $7, $8, $5)
        """,
        new_uuid7(),
        tenant_a,
        recv_account,
        role_recv,
        now,
        new_uuid7(),
        unauth_account,
        role_unauth,
    )
    await conn.execute(
        """
        INSERT INTO role_permission_assignments (
            id, tenant_id, role_id, permission_code, granted_at_utc
        ) VALUES ($1, $2, $3, $4, $5)
        """,
        new_uuid7(),
        tenant_a,
        role_recv,
        CATALOG_SERVICES_READ,
        now,
    )
    await conn.execute(
        """
        INSERT INTO services (
            id, tenant_id, service_code, service_name, default_duration_minutes,
            default_price_irr, is_active, aggregate_version, created_at_utc, updated_at_utc
        ) VALUES ($1, $2, 'CONSULT', 'Tenant A Consultation', 30, 150000, TRUE, 1, $3, $3)
        """,
        service_a,
        tenant_a,
        now,
    )

    # Tenant B isolation fixture
    await conn.execute(
        "SELECT set_config('app.current_tenant_id', $1, false)", str(tenant_b)
    )
    await conn.execute(
        """
        INSERT INTO tenant_persons (
            id, tenant_id, first_name, last_name, birth_date, gender,
            aggregate_version, created_at_utc, updated_at_utc
        ) VALUES ($1, $2, 'Other', 'Tenant', NULL, NULL, 1, $3, $3)
        """,
        person_b,
        tenant_b,
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

    await conn.execute("RESET ROLE")
    return Beta01aSeed(
        tenant_a_id=tenant_a,
        tenant_b_id=tenant_b,
        receptionist_account_id=recv_account,
        unauthorized_account_id=unauth_account,
        receptionist_login=recv_login,
        unauthorized_login=unauth_login,
        service_a_id=service_a,
        service_b_id=service_b,
        receptionist_password=TEST_RECEPTIONIST_PASSWORD,
        unauthorized_password=TEST_UNAUTHORIZED_PASSWORD,
    )


async def lock_account(
    conn: asyncpg.Connection, *, tenant_id: UUID, account_id: UUID, minutes: int = 30
) -> None:
    now = datetime.now(timezone.utc)
    await conn.execute("SET ROLE db_migrator")
    await conn.execute(
        "SELECT set_config('app.current_tenant_id', $1, false)", str(tenant_id)
    )
    await conn.execute(
        """
        UPDATE user_accounts
        SET locked_until_utc = $1, failed_login_attempts = 99, updated_at_utc = $2
        WHERE tenant_id = $3 AND id = $4
        """,
        now + timedelta(minutes=minutes),
        now,
        tenant_id,
        account_id,
    )
    await conn.execute("RESET ROLE")


async def deactivate_account(
    conn: asyncpg.Connection, *, tenant_id: UUID, account_id: UUID
) -> None:
    now = datetime.now(timezone.utc)
    await conn.execute("SET ROLE db_migrator")
    await conn.execute(
        "SELECT set_config('app.current_tenant_id', $1, false)", str(tenant_id)
    )
    await conn.execute(
        """
        UPDATE user_accounts
        SET is_active = FALSE, updated_at_utc = $1
        WHERE tenant_id = $2 AND id = $3
        """,
        now,
        tenant_id,
        account_id,
    )
    await conn.execute("RESET ROLE")

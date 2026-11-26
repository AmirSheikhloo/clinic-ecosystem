"""Synthetic BETA-02 operations fixtures layered on the BETA-01B seed.

All credentials are test-only. Roles/permission bundles below are synthetic
fixtures, not a ratified production role catalog.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

import asyncpg

from clinic_ecosystem.domain.access.permissions import PERMISSION_CATALOG
from clinic_ecosystem.infrastructure.auth.passwords import hash_password
from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7
from tests.integration.beta01b_seed import Beta01bSeed, seed_beta01b_reception

OWNER_PASSWORD = "Beta02-Owner-Test-Only!!"
MANAGER_PASSWORD = "Beta02-Manager-Test-Only!"
DEPUTY_PASSWORD = "Beta02-Deputy-Test-Only!!"
TARGET_PASSWORD = "Beta02-Target-Test-Only!!"

ALL_PERMISSIONS = tuple(PERMISSION_CATALOG)
MANAGER_PERMISSIONS = tuple(
    c for c in ALL_PERMISSIONS if c != "BETA02_GOVERNANCE_MANAGE"
)
DEPUTY_PERMISSIONS = (
    "BETA02_STAFF_VIEW",
    "BETA02_ACCOUNTS_VIEW",
    "BETA02_ROLES_VIEW",
    "BETA02_ROLES_MANAGE",
    "BETA02_USER_ROLES_ASSIGN",
    "BETA02_ACCOUNTS_SET_ACTIVE",
    "BETA01B_PATIENTS_SEARCH",
    "BETA01B_APPOINTMENTS_LIST",
)
RECEPTIONIST_EXTRA = (
    "BETA02_PATIENTS_VIEW_PROFILE",
    "BETA02_PATIENTS_VIEW_HISTORY",
    "BETA02_PATIENTS_UPDATE",
    "BETA02_APPOINTMENTS_VIEW_DETAILS",
    "BETA02_APPOINTMENTS_CANCEL",
    "BETA02_APPOINTMENTS_RESCHEDULE",
    "BETA02_APPOINTMENTS_CHECK_IN",
    "BETA02_APPOINTMENTS_COMPLETE",
    "BETA02_APPOINTMENTS_MARK_NO_SHOW",
)


@dataclass(frozen=True)
class Beta02Seed:
    base: Beta01bSeed
    owner_login: str
    owner_account_id: UUID
    owner_person_id: UUID
    manager_login: str
    manager_account_id: UUID
    manager_person_id: UUID
    deputy_login: str
    deputy_account_id: UUID
    deputy_person_id: UUID
    target_login: str
    target_account_id: UUID
    target_person_id: UUID
    role_owner_id: UUID
    role_manager_id: UUID
    role_deputy_id: UUID
    role_custom_id: UUID
    tenant_b_account_id: UUID
    tenant_b_staff_id: UUID
    tenant_b_role_id: UUID


async def _grant(conn, tenant: UUID, role: UUID, codes, now) -> None:
    for code in codes:
        await conn.execute(
            "INSERT INTO role_permission_assignments "
            "(id, tenant_id, role_id, permission_code, granted_at_utc) VALUES ($1,$2,$3,$4,$5)",
            new_uuid7(), tenant, role, code, now,
        )


async def seed_beta02_operations(conn: asyncpg.Connection) -> Beta02Seed:
    base = await seed_beta01b_reception(conn)
    tenant = base.tenant_a_id
    tenant_b = base.tenant_b_id
    now = datetime.now(timezone.utc)

    people = {name: new_uuid7() for name in ("owner", "manager", "deputy", "target")}
    accounts = {name: new_uuid7() for name in people}
    logins = {name: f"{name}@beta02.test" for name in people}
    passwords = {
        "owner": OWNER_PASSWORD, "manager": MANAGER_PASSWORD,
        "deputy": DEPUTY_PASSWORD, "target": TARGET_PASSWORD,
    }
    roles = {name: new_uuid7() for name in ("owner", "manager", "deputy", "custom")}
    tenant_b_person, tenant_b_account, tenant_b_staff, tenant_b_role = (
        new_uuid7(), new_uuid7(), new_uuid7(), new_uuid7(),
    )

    await conn.execute("SET ROLE db_migrator")
    await conn.execute("SELECT set_config('app.current_tenant_id', $1, false)", str(tenant))
    for name, person in people.items():
        await conn.execute(
            "INSERT INTO tenant_persons (id, tenant_id, first_name, last_name, birth_date, gender,"
            " aggregate_version, created_at_utc, updated_at_utc)"
            " VALUES ($1,$2,$3,$4,NULL,NULL,1,$5,$5)",
            person, tenant, name.capitalize(), "Beta02", now,
        )
        await conn.execute(
            "INSERT INTO user_accounts (id, tenant_id, person_id, login_identifier,"
            " normalized_login_identifier, password_hash_argon2id, is_active,"
            " failed_login_attempts, locked_until_utc, password_changed_at_utc,"
            " aggregate_version, created_at_utc, updated_at_utc)"
            " VALUES ($1,$2,$3,$4,$4,$5,TRUE,0,NULL,$6,1,$6,$6)",
            accounts[name], tenant, person, logins[name], hash_password(passwords[name]), now,
        )
    for key, code, name_text, system in (
        ("owner", "CLINIC_OWNER_ROLE", "Owner", True),
        ("manager", "CLINIC_MANAGER_ROLE", "Manager", True),
        ("deputy", "DEPUTY_ADMIN_ROLE", "Deputy admin", True),
        ("custom", "CUSTOM_FRONTDESK", "Custom front desk", False),
    ):
        await conn.execute(
            "INSERT INTO tenant_roles (id, tenant_id, role_code, role_name, is_system_defined,"
            " created_at_utc) VALUES ($1,$2,$3,$4,$5,$6)",
            roles[key], tenant, code, name_text, system, now,
        )
    await _grant(conn, tenant, roles["owner"], ALL_PERMISSIONS, now)
    await _grant(conn, tenant, roles["manager"], MANAGER_PERMISSIONS, now)
    await _grant(conn, tenant, roles["deputy"], DEPUTY_PERMISSIONS, now)
    await _grant(conn, tenant, roles["custom"], ("BETA01B_PATIENTS_SEARCH",), now)
    await _grant(conn, tenant, base.role_recv_id, RECEPTIONIST_EXTRA, now)
    for name, role in (("owner", "owner"), ("manager", "manager"), ("deputy", "deputy")):
        await conn.execute(
            "INSERT INTO user_role_assignments (id, tenant_id, user_account_id, role_id,"
            " assigned_at_utc) VALUES ($1,$2,$3,$4,$5)",
            new_uuid7(), tenant, accounts[name], roles[role], now,
        )
    for name, gov in (("owner", "CLINIC_OWNER"), ("manager", "CLINIC_MANAGER"),
                      ("deputy", "DEPUTY_ADMIN")):
        await conn.execute(
            "INSERT INTO tenant_governance_assignments (id, tenant_id, person_id,"
            " governance_role, assigned_at_utc) VALUES ($1,$2,$3,$4,$5)",
            new_uuid7(), tenant, people[name], gov, now,
        )

    await conn.execute("SELECT set_config('app.current_tenant_id', $1, false)", str(tenant_b))
    await conn.execute(
        "INSERT INTO tenant_persons (id, tenant_id, first_name, last_name, birth_date, gender,"
        " aggregate_version, created_at_utc, updated_at_utc)"
        " VALUES ($1,$2,'Bee','Staff',NULL,NULL,1,$3,$3)",
        tenant_b_person, tenant_b, now,
    )
    await conn.execute(
        "INSERT INTO staff_profiles (id, tenant_id, person_id, staff_kind, medical_council_code,"
        " is_active, created_at_utc) VALUES ($1,$2,$3,'DOCTOR','B-12345',TRUE,$4)",
        tenant_b_staff, tenant_b, tenant_b_person, now,
    )
    await conn.execute(
        "INSERT INTO user_accounts (id, tenant_id, person_id, login_identifier,"
        " normalized_login_identifier, password_hash_argon2id, is_active, failed_login_attempts,"
        " locked_until_utc, password_changed_at_utc, aggregate_version, created_at_utc,"
        " updated_at_utc) VALUES ($1,$2,$3,'b@beta02.test','b@beta02.test','x',TRUE,0,NULL,$4,1,$4,$4)",
        tenant_b_account, tenant_b, tenant_b_person, now,
    )
    await conn.execute(
        "INSERT INTO tenant_roles (id, tenant_id, role_code, role_name, is_system_defined,"
        " created_at_utc) VALUES ($1,$2,'TENANT_B_ROLE','B role',FALSE,$3)",
        tenant_b_role, tenant_b, now,
    )
    await conn.execute("RESET ROLE")
    return Beta02Seed(
        base=base,
        owner_login=logins["owner"], owner_account_id=accounts["owner"], owner_person_id=people["owner"],
        manager_login=logins["manager"], manager_account_id=accounts["manager"],
        manager_person_id=people["manager"],
        deputy_login=logins["deputy"], deputy_account_id=accounts["deputy"],
        deputy_person_id=people["deputy"],
        target_login=logins["target"], target_account_id=accounts["target"],
        target_person_id=people["target"],
        role_owner_id=roles["owner"], role_manager_id=roles["manager"],
        role_deputy_id=roles["deputy"], role_custom_id=roles["custom"],
        tenant_b_account_id=tenant_b_account, tenant_b_staff_id=tenant_b_staff,
        tenant_b_role_id=tenant_b_role,
    )

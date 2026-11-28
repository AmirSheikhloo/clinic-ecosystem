"""Ensure Task 34 §5 demo role accounts exist with shared password Clinic123!."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import asyncpg

from clinic_ecosystem.infrastructure.auth.demo_aliases import DEMO_SHARED_PASSWORD
from clinic_ecosystem.infrastructure.auth.passwords import hash_password
from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7

# Maps alias → (persian first, last, staff_kind, login_email_fallback, role_source)
# role_source: existing account login to copy role assignments from, or None for clerk.
ALIAS_SPECS: tuple[tuple[str, str, str, str, str, str | None], ...] = (
    ("owner", "حسین", "جعفری", "RECEPTIONIST", "owner@beta02.test", "owner@beta02.test"),
    ("manager", "علی", "نادری", "RECEPTIONIST", "manager@beta02.test", "manager@beta02.test"),
    ("deputy", "نرگس", "احمدی", "RECEPTIONIST", "deputy@beta02.test", "deputy@beta02.test"),
    ("receptionist", "سارا", "نائینی", "RECEPTIONIST", "receptionist@beta01b.test", "receptionist@beta01b.test"),
    ("head", "مریم", "صادقی", "RECEPTIONIST", "head@demo.test", "receptionist@beta01b.test"),
    ("limited", "محمد", "رضایی", "RECEPTIONIST", "limited@demo.test", "clerk-no-perms@beta01b.test"),
    ("doctor", "علی", "نادری", "DOCTOR", "doctor@demo.test", None),
    ("clerk", "نرگس", "احمدی", "RECEPTIONIST", "clerk@demo.test", "clerk-no-perms@beta01b.test"),
)

_JOB_TITLES: dict[str, str] = {
    "owner": "مالک کلینیک",
    "manager": "مدیر",
    "deputy": "مدیر داخلی",
    "receptionist": "منشی",
    "head": "سرپرست پذیرش",
    "limited": "منشی",
    "doctor": "پزشک",
    "clerk": "منشی",
}


async def apply_preview_demo_aliases(
    conn: asyncpg.Connection,
    *,
    tenant_id: UUID,
    receptionist_login: str | None = None,
) -> dict[str, Any]:
    """Set shared password on known accounts and create missing alias logins."""
    now = datetime.now(timezone.utc)
    pwd = hash_password(DEMO_SHARED_PASSWORD)
    await conn.execute("SET ROLE db_migrator")
    await conn.execute(
        "SELECT set_config('app.current_tenant_id', $1, false)", str(tenant_id)
    )
    alias_map: dict[str, str] = {}
    created: list[str] = []

    # Prefer actual receptionist login from seed when present.
    specs = []
    for alias, first, last, kind, email, copy_from in ALIAS_SPECS:
        if alias == "receptionist" and receptionist_login:
            email = receptionist_login
            copy_from = receptionist_login
        specs.append((alias, first, last, kind, email, copy_from))

    for alias, first, last, kind, email, copy_from in specs:
        # Prefer updating the canonical email account password.
        row = await conn.fetchrow(
            """
            SELECT id, person_id, login_identifier FROM user_accounts
            WHERE tenant_id = $1 AND normalized_login_identifier = lower($2)
            """,
            tenant_id,
            email,
        )
        if row is None and copy_from:
            row = await conn.fetchrow(
                """
                SELECT id, person_id, login_identifier FROM user_accounts
                WHERE tenant_id = $1 AND normalized_login_identifier = lower($2)
                """,
                tenant_id,
                copy_from,
            )
        if row is not None:
            await conn.execute(
                """
                UPDATE user_accounts
                SET password_hash_argon2id = $3, password_changed_at_utc = $4, updated_at_utc = $4
                WHERE tenant_id = $1 AND id = $2
                """,
                tenant_id,
                row["id"],
                pwd,
                now,
            )
            # Correct synthetic display names + optional job_title on the existing person.
            await conn.execute(
                """
                UPDATE tenant_persons
                SET first_name = $3, last_name = $4, updated_at_utc = $5
                WHERE tenant_id = $1 AND id = $2
                """,
                tenant_id,
                row["person_id"],
                first,
                last,
                now,
            )
            job_title = _JOB_TITLES.get(alias, "کارشناس")
            has_job_title = await conn.fetchval(
                """
                SELECT EXISTS (
                  SELECT 1 FROM information_schema.columns
                  WHERE table_schema='public' AND table_name='staff_profiles'
                    AND column_name='job_title'
                )
                """
            )
            if has_job_title:
                updated = await conn.execute(
                    """
                    UPDATE staff_profiles
                    SET job_title = $3
                    WHERE tenant_id = $1 AND person_id = $2
                    """,
                    tenant_id,
                    row["person_id"],
                    job_title,
                )
                if updated == "UPDATE 0":
                    await conn.execute(
                        """
                        INSERT INTO staff_profiles (
                          id, tenant_id, person_id, staff_kind, is_active, created_at_utc, job_title
                        ) VALUES ($1,$2,$3,$4,TRUE,$5,$6)
                        ON CONFLICT DO NOTHING
                        """,
                        new_uuid7(),
                        tenant_id,
                        row["person_id"],
                        kind if kind in {"RECEPTIONIST", "DOCTOR", "ADMIN", "CLERK"} else "RECEPTIONIST",
                        now,
                        job_title,
                    )
            # Also ensure a short-alias login account exists (same person) when distinct.
            alias_row = await conn.fetchrow(
                """
                SELECT id FROM user_accounts
                WHERE tenant_id = $1 AND normalized_login_identifier = lower($2)
                """,
                tenant_id,
                alias,
            )
            if alias_row is None and alias.lower() != str(row["login_identifier"]).lower():
                # One login per person typically — create a dedicated alias person+account
                # sharing the same role assignments as the source account.
                person_id = new_uuid7()
                account_id = new_uuid7()
                await conn.execute(
                    """
                    INSERT INTO tenant_persons (
                      id, tenant_id, first_name, last_name, birth_date, gender,
                      aggregate_version, created_at_utc, updated_at_utc
                    ) VALUES ($1,$2,$3,$4,NULL,NULL,1,$5,$5)
                    """,
                    person_id,
                    tenant_id,
                    first,
                    last,
                    now,
                )
                await conn.execute(
                    """
                    INSERT INTO user_accounts (
                      id, tenant_id, person_id, login_identifier, normalized_login_identifier,
                      password_hash_argon2id, is_active, failed_login_attempts, locked_until_utc,
                      password_changed_at_utc, aggregate_version, created_at_utc, updated_at_utc
                    ) VALUES (
                      $1,$2,$3,$4,$5,$6,TRUE,0,NULL,$7,1,$7,$7
                    )
                    """,
                    account_id,
                    tenant_id,
                    person_id,
                    alias,
                    alias.lower(),
                    pwd,
                    now,
                )
                # Copy role assignments from source account.
                roles = await conn.fetch(
                    """
                    SELECT role_id FROM user_role_assignments
                    WHERE tenant_id = $1 AND user_account_id = $2
                    """,
                    tenant_id,
                    row["id"],
                )
                for r in roles:
                    await conn.execute(
                        """
                        INSERT INTO user_role_assignments (
                          id, tenant_id, user_account_id, role_id, assigned_at_utc
                        ) VALUES ($1,$2,$3,$4,$5)
                        ON CONFLICT DO NOTHING
                        """,
                        new_uuid7(),
                        tenant_id,
                        account_id,
                        r["role_id"],
                        now,
                    )
                created.append(alias)
                alias_map[alias] = alias
            else:
                alias_map[alias] = str(row["login_identifier"])
            continue

        # Create from scratch when no source exists.
        person_id = new_uuid7()
        account_id = new_uuid7()
        await conn.execute(
            """
            INSERT INTO tenant_persons (
              id, tenant_id, first_name, last_name, birth_date, gender,
              aggregate_version, created_at_utc, updated_at_utc
            ) VALUES ($1,$2,$3,$4,NULL,NULL,1,$5,$5)
            """,
            person_id,
            tenant_id,
            first,
            last,
            now,
        )
        staff_kind = (
            kind if kind in {"RECEPTIONIST", "DOCTOR", "ADMIN", "CLERK"} else "RECEPTIONIST"
        )
        job_title = _JOB_TITLES.get(alias, "کارشناس")
        has_job_title = await conn.fetchval(
            """
            SELECT EXISTS (
              SELECT 1 FROM information_schema.columns
              WHERE table_schema='public' AND table_name='staff_profiles'
                AND column_name='job_title'
            )
            """
        )
        if has_job_title:
            await conn.execute(
                """
                INSERT INTO staff_profiles (
                  id, tenant_id, person_id, staff_kind, is_active, created_at_utc, job_title
                ) VALUES ($1,$2,$3,$4,TRUE,$5,$6)
                """,
                new_uuid7(),
                tenant_id,
                person_id,
                staff_kind,
                now,
                job_title,
            )
        else:
            await conn.execute(
                """
                INSERT INTO staff_profiles (
                  id, tenant_id, person_id, staff_kind, is_active, created_at_utc
                ) VALUES ($1,$2,$3,$4,TRUE,$5)
                """,
                new_uuid7(),
                tenant_id,
                person_id,
                staff_kind,
                now,
            )
        await conn.execute(
            """
            INSERT INTO user_accounts (
              id, tenant_id, person_id, login_identifier, normalized_login_identifier,
              password_hash_argon2id, is_active, failed_login_attempts, locked_until_utc,
              password_changed_at_utc, aggregate_version, created_at_utc, updated_at_utc
            ) VALUES (
              $1,$2,$3,$4,$5,$6,TRUE,0,NULL,$7,1,$7,$7
            )
            """,
            account_id,
            tenant_id,
            person_id,
            alias,
            alias.lower(),
            pwd,
            now,
        )
        # Doctor: login enabled explicitly for demo alias only.
        created.append(alias)
        alias_map[alias] = alias

    await conn.execute("RESET ROLE")
    return {
        "password": DEMO_SHARED_PASSWORD,
        "aliases": alias_map,
        "created": created,
    }

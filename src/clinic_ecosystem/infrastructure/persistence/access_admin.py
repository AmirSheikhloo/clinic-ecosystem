"""Account, role and governance administration queries (Workstream C)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession

from clinic_ecosystem.infrastructure.persistence.sql_helpers import like_contains
from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7


class SqlAccessAdmin:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_accounts(
        self, *, tenant_id: UUID, q: str | None, limit: int, offset: int
    ) -> tuple[list[dict[str, Any]], int]:
        where = "ua.tenant_id = :tenant_id"
        params: dict[str, Any] = {"tenant_id": tenant_id, "limit": limit, "offset": offset}
        if q:
            where += (
                " AND ((p.first_name || ' ' || p.last_name) ILIKE :pat ESCAPE '\\'"
                " OR ua.login_identifier ILIKE :pat ESCAPE '\\')"
            )
            params["pat"] = like_contains(q)
        total = await self._session.execute(
            text(
                "SELECT count(*) FROM user_accounts ua JOIN tenant_persons p "
                f"ON p.tenant_id = ua.tenant_id AND p.id = ua.person_id WHERE {where}"
            ),
            params,
        )
        rows = await self._session.execute(
            text(
                f"""
                SELECT ua.id AS account_id, ua.person_id, ua.login_identifier,
                       ua.is_active, ua.locked_until_utc, ua.aggregate_version,
                       p.first_name, p.last_name, sp.staff_kind,
                       COALESCE((
                           SELECT array_agg(r.role_code ORDER BY r.role_code)
                           FROM user_role_assignments ura
                           JOIN tenant_roles r
                             ON r.tenant_id = ura.tenant_id AND r.id = ura.role_id
                           WHERE ura.tenant_id = ua.tenant_id AND ura.user_account_id = ua.id
                       ), ARRAY[]::varchar[]) AS role_codes,
                       COALESCE((
                           SELECT array_agg(g.governance_role ORDER BY g.governance_role)
                           FROM tenant_governance_assignments g
                           WHERE g.tenant_id = ua.tenant_id AND g.person_id = ua.person_id
                       ), ARRAY[]::varchar[]) AS governance_roles
                FROM user_accounts ua
                JOIN tenant_persons p ON p.tenant_id = ua.tenant_id AND p.id = ua.person_id
                LEFT JOIN staff_profiles sp
                  ON sp.tenant_id = ua.tenant_id AND sp.person_id = ua.person_id
                WHERE {where}
                ORDER BY p.last_name, p.first_name, ua.id
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        )
        return [dict(r._mapping) for r in rows], int(total.scalar_one())

    async def get_account(
        self, *, tenant_id: UUID, account_id: UUID, for_update: bool = False
    ) -> dict[str, Any] | None:
        suffix = " FOR UPDATE OF ua" if for_update else ""
        result = await self._session.execute(
            text(
                """
                SELECT ua.id AS account_id, ua.person_id, ua.login_identifier,
                       ua.is_active, ua.aggregate_version
                FROM user_accounts ua
                WHERE ua.tenant_id = :tenant_id AND ua.id = :id
                """
                + suffix
            ),
            {"tenant_id": tenant_id, "id": account_id},
        )
        row = result.first()
        return dict(row._mapping) if row else None

    async def set_account_active_cas(
        self,
        *,
        tenant_id: UUID,
        account_id: UUID,
        expected_version: int,
        active: bool,
        now: datetime,
    ) -> int | None:
        result = await self._session.execute(
            text(
                """
                UPDATE user_accounts
                SET is_active = :active,
                    failed_login_attempts = CASE WHEN :active THEN 0 ELSE failed_login_attempts END,
                    locked_until_utc = CASE WHEN :active THEN NULL ELSE locked_until_utc END,
                    aggregate_version = aggregate_version + 1,
                    updated_at_utc = :now
                WHERE tenant_id = :tenant_id AND id = :id AND aggregate_version = :expected
                RETURNING aggregate_version
                """
            ),
            {
                "tenant_id": tenant_id,
                "id": account_id,
                "expected": expected_version,
                "active": active,
                "now": now,
            },
        )
        row = result.first()
        return int(row.aggregate_version) if row else None

    async def account_permissions(
        self, *, tenant_id: UUID, account_id: UUID
    ) -> list[dict[str, Any]]:
        result = await self._session.execute(
            text(
                """
                SELECT rpa.permission_code, r.role_code
                FROM user_role_assignments ura
                JOIN tenant_roles r ON r.tenant_id = ura.tenant_id AND r.id = ura.role_id
                JOIN role_permission_assignments rpa
                  ON rpa.tenant_id = ura.tenant_id AND rpa.role_id = ura.role_id
                WHERE ura.tenant_id = :tenant_id AND ura.user_account_id = :id
                ORDER BY rpa.permission_code, r.role_code
                """
            ),
            {"tenant_id": tenant_id, "id": account_id},
        )
        return [dict(r._mapping) for r in result]

    async def list_roles(self, *, tenant_id: UUID) -> list[dict[str, Any]]:
        result = await self._session.execute(
            text(
                """
                SELECT r.id AS role_id, r.role_code, r.role_name, r.is_system_defined,
                       COALESCE((
                           SELECT array_agg(rpa.permission_code ORDER BY rpa.permission_code)
                           FROM role_permission_assignments rpa
                           WHERE rpa.tenant_id = r.tenant_id AND rpa.role_id = r.id
                       ), ARRAY[]::varchar[]) AS permission_codes,
                       (SELECT count(*) FROM user_role_assignments ura
                        WHERE ura.tenant_id = r.tenant_id AND ura.role_id = r.id) AS member_count
                FROM tenant_roles r
                WHERE r.tenant_id = :tenant_id
                ORDER BY r.role_code
                """
            ),
            {"tenant_id": tenant_id},
        )
        return [dict(r._mapping) for r in result]

    async def get_role(
        self, *, tenant_id: UUID, role_id: UUID, for_update: bool = False
    ) -> dict[str, Any] | None:
        result = await self._session.execute(
            text(
                "SELECT id AS role_id, role_code, role_name, is_system_defined "
                "FROM tenant_roles WHERE tenant_id = :tenant_id AND id = :id"
                + (" FOR UPDATE" if for_update else "")
            ),
            {"tenant_id": tenant_id, "id": role_id},
        )
        row = result.first()
        return dict(row._mapping) if row else None

    async def role_permission_codes(self, *, tenant_id: UUID, role_ids: list[UUID]) -> dict[UUID, set[str]]:
        if not role_ids:
            return {}
        stmt = text(
            "SELECT role_id, permission_code FROM role_permission_assignments "
            "WHERE tenant_id = :tenant_id AND role_id = ANY(:ids)"
        ).bindparams(bindparam("ids", type_=ARRAY(PGUUID(as_uuid=True))))
        result = await self._session.execute(stmt, {"tenant_id": tenant_id, "ids": role_ids})
        out: dict[UUID, set[str]] = {rid: set() for rid in role_ids}
        for row in result:
            out[row.role_id].add(row.permission_code)
        return out

    async def existing_roles(self, *, tenant_id: UUID, role_ids: list[UUID]) -> set[UUID]:
        if not role_ids:
            return set()
        stmt = text(
            "SELECT id FROM tenant_roles WHERE tenant_id = :tenant_id AND id = ANY(:ids)"
        ).bindparams(bindparam("ids", type_=ARRAY(PGUUID(as_uuid=True))))
        result = await self._session.execute(stmt, {"tenant_id": tenant_id, "ids": role_ids})
        return {row.id for row in result}

    async def insert_role(
        self, *, tenant_id: UUID, role_id: UUID, code: str, name: str, now: datetime
    ) -> None:
        await self._session.execute(
            text(
                """
                INSERT INTO tenant_roles (id, tenant_id, role_code, role_name,
                                          is_system_defined, created_at_utc)
                VALUES (:id, :tenant_id, :code, :name, FALSE, :now)
                """
            ),
            {"id": role_id, "tenant_id": tenant_id, "code": code, "name": name, "now": now},
        )

    async def delete_role(self, *, tenant_id: UUID, role_id: UUID) -> None:
        await self._session.execute(
            text("DELETE FROM role_permission_assignments WHERE tenant_id = :t AND role_id = :r"),
            {"t": tenant_id, "r": role_id},
        )
        await self._session.execute(
            text("DELETE FROM tenant_roles WHERE tenant_id = :t AND id = :r"),
            {"t": tenant_id, "r": role_id},
        )

    async def role_member_count(self, *, tenant_id: UUID, role_id: UUID) -> int:
        result = await self._session.execute(
            text(
                "SELECT count(*) FROM user_role_assignments "
                "WHERE tenant_id = :t AND role_id = :r"
            ),
            {"t": tenant_id, "r": role_id},
        )
        return int(result.scalar_one())

    async def replace_role_permissions(
        self, *, tenant_id: UUID, role_id: UUID, add: set[str], remove: set[str], now: datetime
    ) -> None:
        for code in sorted(remove):
            await self._session.execute(
                text(
                    "DELETE FROM role_permission_assignments "
                    "WHERE tenant_id = :t AND role_id = :r AND permission_code = :c"
                ),
                {"t": tenant_id, "r": role_id, "c": code},
            )
        for code in sorted(add):
            await self._session.execute(
                text(
                    """
                    INSERT INTO role_permission_assignments
                        (id, tenant_id, role_id, permission_code, granted_at_utc)
                    VALUES (:id, :t, :r, :c, :now)
                    """
                ),
                {"id": new_uuid7(), "t": tenant_id, "r": role_id, "c": code, "now": now},
            )

    async def account_role_ids(self, *, tenant_id: UUID, account_id: UUID) -> set[UUID]:
        result = await self._session.execute(
            text(
                "SELECT role_id FROM user_role_assignments "
                "WHERE tenant_id = :t AND user_account_id = :a"
            ),
            {"t": tenant_id, "a": account_id},
        )
        return {row.role_id for row in result}

    async def replace_account_roles(
        self,
        *,
        tenant_id: UUID,
        account_id: UUID,
        add: set[UUID],
        remove: set[UUID],
        now: datetime,
    ) -> None:
        for role_id in sorted(remove):
            await self._session.execute(
                text(
                    "DELETE FROM user_role_assignments "
                    "WHERE tenant_id = :t AND user_account_id = :a AND role_id = :r"
                ),
                {"t": tenant_id, "a": account_id, "r": role_id},
            )
        for role_id in sorted(add):
            await self._session.execute(
                text(
                    """
                    INSERT INTO user_role_assignments
                        (id, tenant_id, user_account_id, role_id, assigned_at_utc)
                    VALUES (:id, :t, :a, :r, :now)
                    """
                ),
                {"id": new_uuid7(), "t": tenant_id, "a": account_id, "r": role_id, "now": now},
            )

    async def list_governance(self, *, tenant_id: UUID) -> list[dict[str, Any]]:
        result = await self._session.execute(
            text(
                """
                SELECT p.id AS person_id, p.first_name, p.last_name,
                       array_agg(g.governance_role ORDER BY g.governance_role) AS roles
                FROM tenant_governance_assignments g
                JOIN tenant_persons p ON p.tenant_id = g.tenant_id AND p.id = g.person_id
                WHERE g.tenant_id = :tenant_id
                GROUP BY p.id, p.first_name, p.last_name
                ORDER BY p.last_name, p.first_name, p.id
                """
            ),
            {"tenant_id": tenant_id},
        )
        return [dict(r._mapping) for r in result]

    async def person_display(self, *, tenant_id: UUID, person_id: UUID) -> tuple[str, str] | None:
        result = await self._session.execute(
            text("SELECT first_name, last_name FROM tenant_persons WHERE tenant_id = :t AND id = :p"),
            {"t": tenant_id, "p": person_id},
        )
        row = result.first()
        return (row.first_name, row.last_name) if row else None

    async def staff_job_title(self, *, tenant_id: UUID, person_id: UUID) -> str | None:
        """Return staff_profiles.job_title when the disposable column exists."""
        ready = await self._session.execute(
            text(
                """
                SELECT EXISTS (
                  SELECT 1 FROM information_schema.columns
                  WHERE table_schema = 'public'
                    AND table_name = 'staff_profiles'
                    AND column_name = 'job_title'
                ) AS ok
                """
            )
        )
        if not bool(ready.mappings().one()["ok"]):
            return None
        result = await self._session.execute(
            text(
                """
                SELECT job_title FROM staff_profiles
                WHERE tenant_id = :t AND person_id = :p
                """
            ),
            {"t": tenant_id, "p": person_id},
        )
        row = result.first()
        if row is None:
            return None
        title = row.job_title
        return str(title) if title else None

    async def person_exists(self, *, tenant_id: UUID, person_id: UUID) -> bool:
        result = await self._session.execute(
            text("SELECT 1 FROM tenant_persons WHERE tenant_id = :t AND id = :p"),
            {"t": tenant_id, "p": person_id},
        )
        return result.first() is not None

    async def lock_governance_namespace(self, tenant_id: UUID) -> None:
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": f"{tenant_id}:governance"},
        )

    async def person_governance(self, *, tenant_id: UUID, person_id: UUID) -> set[str]:
        result = await self._session.execute(
            text(
                "SELECT governance_role FROM tenant_governance_assignments "
                "WHERE tenant_id = :t AND person_id = :p"
            ),
            {"t": tenant_id, "p": person_id},
        )
        return {row.governance_role for row in result}

    async def count_governance_holders(self, *, tenant_id: UUID, role: str) -> int:
        result = await self._session.execute(
            text(
                "SELECT count(*) FROM tenant_governance_assignments "
                "WHERE tenant_id = :t AND governance_role = :r"
            ),
            {"t": tenant_id, "r": role},
        )
        return int(result.scalar_one())

    async def replace_governance(
        self,
        *,
        tenant_id: UUID,
        person_id: UUID,
        add: set[str],
        remove: set[str],
        now: datetime,
    ) -> None:
        for role in sorted(remove):
            await self._session.execute(
                text(
                    "DELETE FROM tenant_governance_assignments "
                    "WHERE tenant_id = :t AND person_id = :p AND governance_role = :r"
                ),
                {"t": tenant_id, "p": person_id, "r": role},
            )
        for role in sorted(add):
            await self._session.execute(
                text(
                    """
                    INSERT INTO tenant_governance_assignments
                        (id, tenant_id, person_id, governance_role, assigned_at_utc)
                    VALUES (:id, :t, :p, :r, :now)
                    """
                ),
                {"id": new_uuid7(), "t": tenant_id, "p": person_id, "r": role, "now": now},
            )

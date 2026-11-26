"""Staff profile queries and writes (Workstream B).

Person, staff profile and login account stay in separate tables; nothing here
grants roles or permissions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from clinic_ecosystem.infrastructure.persistence.sql_helpers import like_contains

_SELECT = """
    SELECT sp.id AS staff_profile_id, sp.person_id, sp.staff_kind,
           sp.medical_council_code, sp.is_active, sp.created_at_utc,
           p.first_name, p.last_name, p.birth_date, p.aggregate_version,
           ua.id AS account_id, ua.is_active AS account_is_active,
           ua.login_identifier, ua.locked_until_utc
    FROM staff_profiles sp
    JOIN tenant_persons p ON p.tenant_id = sp.tenant_id AND p.id = sp.person_id
    LEFT JOIN user_accounts ua ON ua.tenant_id = sp.tenant_id AND ua.person_id = sp.person_id
"""


@dataclass(frozen=True, slots=True)
class StaffRow:
    staff_profile_id: UUID
    person_id: UUID
    first_name: str
    last_name: str
    birth_date: date | None
    staff_kind: str
    medical_council_code: str | None
    is_active: bool
    aggregate_version: int
    created_at_utc: datetime
    account_id: UUID | None
    account_is_active: bool | None
    login_identifier: str | None
    locked_until_utc: datetime | None


def _row(r) -> StaffRow:
    return StaffRow(
        staff_profile_id=r.staff_profile_id,
        person_id=r.person_id,
        first_name=r.first_name,
        last_name=r.last_name,
        birth_date=r.birth_date,
        staff_kind=r.staff_kind,
        medical_council_code=r.medical_council_code,
        is_active=r.is_active,
        aggregate_version=int(r.aggregate_version),
        created_at_utc=r.created_at_utc,
        account_id=r.account_id,
        account_is_active=r.account_is_active,
        login_identifier=r.login_identifier,
        locked_until_utc=r.locked_until_utc,
    )


class SqlStaffRegistry:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_page(
        self,
        *,
        tenant_id: UUID,
        q: str | None,
        kind: str | None,
        is_active: bool | None,
        limit: int,
        offset: int,
    ) -> tuple[list[StaffRow], int]:
        where = ["sp.tenant_id = :tenant_id"]
        params: dict[str, Any] = {"tenant_id": tenant_id, "limit": limit, "offset": offset}
        if q:
            where.append(
                "((p.first_name || ' ' || p.last_name) ILIKE :pat ESCAPE '\\'"
                " OR p.last_name ILIKE :pat ESCAPE '\\')"
            )
            params["pat"] = like_contains(q)
        if kind:
            where.append("sp.staff_kind = :kind")
            params["kind"] = kind
        if is_active is not None:
            where.append("sp.is_active = :is_active")
            params["is_active"] = is_active
        clause = " AND ".join(where)
        total = await self._session.execute(
            text(
                "SELECT count(*) FROM staff_profiles sp JOIN tenant_persons p "
                f"ON p.tenant_id = sp.tenant_id AND p.id = sp.person_id WHERE {clause}"
            ),
            params,
        )
        rows = await self._session.execute(
            text(
                f"{_SELECT} WHERE {clause} ORDER BY p.last_name, p.first_name, sp.id "
                "LIMIT :limit OFFSET :offset"
            ),
            params,
        )
        return [_row(r) for r in rows], int(total.scalar_one())

    async def get(self, *, tenant_id: UUID, staff_profile_id: UUID) -> StaffRow | None:
        result = await self._session.execute(
            text(f"{_SELECT} WHERE sp.tenant_id = :tenant_id AND sp.id = :id"),
            {"tenant_id": tenant_id, "id": staff_profile_id},
        )
        row = result.first()
        return _row(row) if row else None

    async def insert_person(
        self,
        *,
        tenant_id: UUID,
        person_id: UUID,
        first_name: str,
        last_name: str,
        birth_date: date | None,
        now: datetime,
    ) -> None:
        await self._session.execute(
            text(
                """
                INSERT INTO tenant_persons (
                    id, tenant_id, first_name, last_name, birth_date, gender,
                    aggregate_version, created_at_utc, updated_at_utc
                ) VALUES (:id, :tenant_id, :first, :last, :birth, NULL, 1, :now, :now)
                """
            ),
            {
                "id": person_id,
                "tenant_id": tenant_id,
                "first": first_name,
                "last": last_name,
                "birth": birth_date,
                "now": now,
            },
        )

    async def insert_profile(
        self,
        *,
        tenant_id: UUID,
        staff_profile_id: UUID,
        person_id: UUID,
        staff_kind: str,
        medical_council_code: str | None,
        now: datetime,
    ) -> None:
        await self._session.execute(
            text(
                """
                INSERT INTO staff_profiles (
                    id, tenant_id, person_id, staff_kind, medical_council_code,
                    is_active, created_at_utc
                ) VALUES (:id, :tenant_id, :person_id, :kind, :council, TRUE, :now)
                """
            ),
            {
                "id": staff_profile_id,
                "tenant_id": tenant_id,
                "person_id": person_id,
                "kind": staff_kind,
                "council": medical_council_code,
                "now": now,
            },
        )

    async def lock_person(self, *, tenant_id: UUID, person_id: UUID) -> None:
        await self._session.execute(
            text(
                "SELECT id FROM tenant_persons WHERE tenant_id = :t AND id = :p FOR UPDATE"
            ),
            {"t": tenant_id, "p": person_id},
        )

    async def update_person_cas(
        self,
        *,
        tenant_id: UUID,
        person_id: UUID,
        expected_version: int,
        first_name: str | None,
        last_name: str | None,
        now: datetime,
    ) -> int | None:
        result = await self._session.execute(
            text(
                """
                UPDATE tenant_persons
                SET first_name = COALESCE(:first, first_name),
                    last_name = COALESCE(:last, last_name),
                    aggregate_version = aggregate_version + 1,
                    updated_at_utc = :now
                WHERE tenant_id = :tenant_id AND id = :person_id
                  AND aggregate_version = :expected
                RETURNING aggregate_version
                """
            ),
            {
                "tenant_id": tenant_id,
                "person_id": person_id,
                "expected": expected_version,
                "first": first_name,
                "last": last_name,
                "now": now,
            },
        )
        row = result.first()
        return int(row.aggregate_version) if row else None

    async def update_profile(
        self,
        *,
        tenant_id: UUID,
        staff_profile_id: UUID,
        staff_kind: str | None,
        medical_council_code: str | None,
        set_council: bool,
        is_active: bool | None,
    ) -> None:
        sets: list[str] = []
        params: dict[str, Any] = {"tenant_id": tenant_id, "id": staff_profile_id}
        if staff_kind is not None:
            sets.append("staff_kind = :kind")
            params["kind"] = staff_kind
        if set_council:
            sets.append("medical_council_code = :council")
            params["council"] = medical_council_code
        if is_active is not None:
            sets.append("is_active = :is_active")
            params["is_active"] = is_active
        if sets:
            await self._session.execute(
                text(
                    f"UPDATE staff_profiles SET {', '.join(sets)} "
                    "WHERE tenant_id = :tenant_id AND id = :id"
                ),
                params,
            )

    async def login_exists(self, *, tenant_id: UUID, normalized: str) -> bool:
        result = await self._session.execute(
            text(
                "SELECT 1 FROM user_accounts WHERE tenant_id = :t "
                "AND normalized_login_identifier = :n LIMIT 1"
            ),
            {"t": tenant_id, "n": normalized},
        )
        return result.first() is not None

    async def insert_account(
        self,
        *,
        tenant_id: UUID,
        account_id: UUID,
        person_id: UUID,
        login_identifier: str,
        normalized_login: str,
        password_hash: str,
        now: datetime,
    ) -> None:
        await self._session.execute(
            text(
                """
                INSERT INTO user_accounts (
                    id, tenant_id, person_id, login_identifier, normalized_login_identifier,
                    password_hash_argon2id, is_active, failed_login_attempts,
                    locked_until_utc, password_changed_at_utc, aggregate_version,
                    created_at_utc, updated_at_utc
                ) VALUES (
                    :id, :tenant_id, :person_id, :login, :normalized, :hash, TRUE, 0,
                    NULL, :now, 1, :now, :now
                )
                """
            ),
            {
                "id": account_id,
                "tenant_id": tenant_id,
                "person_id": person_id,
                "login": login_identifier,
                "normalized": normalized_login,
                "hash": password_hash,
                "now": now,
            },
        )

"""Patient registry queries and guarded updates (Workstream A)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from clinic_ecosystem.infrastructure.persistence.sql_helpers import like_contains

_PROFILE_SELECT = """
    SELECT pp.id AS patient_profile_id, pp.person_id, pp.dossier_number, pp.is_active,
           pp.created_at_utc, p.first_name, p.last_name, p.birth_date,
           p.aggregate_version
    FROM patient_profiles pp
    JOIN tenant_persons p ON p.tenant_id = pp.tenant_id AND p.id = pp.person_id
"""


@dataclass(frozen=True, slots=True)
class PatientProfileRow:
    patient_profile_id: UUID
    person_id: UUID
    first_name: str
    last_name: str
    birth_date: date | None
    dossier_number: str | None
    is_active: bool
    aggregate_version: int
    created_at_utc: datetime


@dataclass(frozen=True, slots=True)
class PatientMaskedIdentity:
    masked_identifier: str | None
    identifier_type: str | None
    masked_phone: str | None


def _row(row) -> PatientProfileRow:
    return PatientProfileRow(
        patient_profile_id=row.patient_profile_id,
        person_id=row.person_id,
        first_name=row.first_name,
        last_name=row.last_name,
        birth_date=row.birth_date,
        dossier_number=row.dossier_number,
        is_active=row.is_active,
        aggregate_version=int(row.aggregate_version),
        created_at_utc=row.created_at_utc,
    )


class SqlPatientRegistry:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_page(
        self,
        *,
        tenant_id: UUID,
        q: str | None,
        is_active: bool | None,
        limit: int,
        offset: int,
    ) -> tuple[list[PatientProfileRow], int]:
        where = ["pp.tenant_id = :tenant_id"]
        params: dict[str, Any] = {"tenant_id": tenant_id, "limit": limit, "offset": offset}
        if q:
            where.append(
                "(p.first_name ILIKE :pat ESCAPE '\\' OR p.last_name ILIKE :pat ESCAPE '\\'"
                " OR (p.first_name || ' ' || p.last_name) ILIKE :pat ESCAPE '\\'"
                " OR pp.dossier_number ILIKE :pat ESCAPE '\\')"
            )
            params["pat"] = like_contains(q)
        if is_active is not None:
            where.append("pp.is_active = :is_active")
            params["is_active"] = is_active
        clause = " AND ".join(where)
        total = await self._session.execute(
            text(
                f"SELECT count(*) FROM patient_profiles pp JOIN tenant_persons p "
                f"ON p.tenant_id = pp.tenant_id AND p.id = pp.person_id WHERE {clause}"
            ),
            params,
        )
        rows = await self._session.execute(
            text(
                f"{_PROFILE_SELECT} WHERE {clause} "
                "ORDER BY p.last_name, p.first_name, pp.id LIMIT :limit OFFSET :offset"
            ),
            params,
        )
        return [_row(r) for r in rows], int(total.scalar_one())

    async def get(self, *, tenant_id: UUID, patient_profile_id: UUID) -> PatientProfileRow | None:
        result = await self._session.execute(
            text(f"{_PROFILE_SELECT} WHERE pp.tenant_id = :tenant_id AND pp.id = :id"),
            {"tenant_id": tenant_id, "id": patient_profile_id},
        )
        row = result.first()
        return _row(row) if row else None

    async def masked_identity(
        self, *, tenant_id: UUID, person_id: UUID
    ) -> PatientMaskedIdentity:
        """Return stored masked display values only — never ciphertext or plaintext."""
        id_row = await self._session.execute(
            text(
                """
                SELECT masked_display, id_type
                FROM person_identifiers
                WHERE tenant_id = :tenant_id AND person_id = :person_id
                ORDER BY created_at_utc ASC, id ASC
                LIMIT 1
                """
            ),
            {"tenant_id": tenant_id, "person_id": person_id},
        )
        phone_row = await self._session.execute(
            text(
                """
                SELECT masked_phone
                FROM person_phones
                WHERE tenant_id = :tenant_id AND person_id = :person_id
                ORDER BY created_at_utc ASC, id ASC
                LIMIT 1
                """
            ),
            {"tenant_id": tenant_id, "person_id": person_id},
        )
        identifier = id_row.mappings().first()
        phone = phone_row.mappings().first()
        return PatientMaskedIdentity(
            masked_identifier=identifier["masked_display"] if identifier else None,
            identifier_type=identifier["id_type"] if identifier else None,
            masked_phone=phone["masked_phone"] if phone else None,
        )

    async def lock_dossier_namespace(self, tenant_id: UUID) -> None:
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
            {"key": f"{tenant_id}:patient-dossier"},
        )

    async def dossier_in_use(
        self, *, tenant_id: UUID, dossier_number: str, exclude_profile_id: UUID
    ) -> bool:
        result = await self._session.execute(
            text(
                """
                SELECT 1 FROM patient_profiles
                WHERE tenant_id = :tenant_id AND dossier_number = :dossier
                  AND id <> :exclude
                LIMIT 1
                """
            ),
            {
                "tenant_id": tenant_id,
                "dossier": dossier_number,
                "exclude": exclude_profile_id,
            },
        )
        return result.first() is not None

    async def bump_person(
        self,
        *,
        tenant_id: UUID,
        person_id: UUID,
        expected_version: int,
        fields: dict[str, Any],
        now: datetime,
    ) -> int | None:
        """Compare-and-set on tenant_persons.aggregate_version; None when stale."""
        sets = ["aggregate_version = aggregate_version + 1", "updated_at_utc = :now"]
        params: dict[str, Any] = {
            "tenant_id": tenant_id,
            "person_id": person_id,
            "expected": expected_version,
            "now": now,
        }
        for column in ("first_name", "last_name", "birth_date"):
            if column in fields:
                sets.append(f"{column} = :{column}")
                params[column] = fields[column]
        result = await self._session.execute(
            text(
                f"UPDATE tenant_persons SET {', '.join(sets)} "
                "WHERE tenant_id = :tenant_id AND id = :person_id "
                "AND aggregate_version = :expected RETURNING aggregate_version"
            ),
            params,
        )
        row = result.first()
        return int(row.aggregate_version) if row else None

    async def update_profile(
        self,
        *,
        tenant_id: UUID,
        patient_profile_id: UUID,
        dossier_number: str | None,
        set_dossier: bool,
        is_active: bool | None,
    ) -> None:
        sets: list[str] = []
        params: dict[str, Any] = {"tenant_id": tenant_id, "id": patient_profile_id}
        if set_dossier:
            sets.append("dossier_number = :dossier")
            params["dossier"] = dossier_number
        if is_active is not None:
            sets.append("is_active = :is_active")
            params["is_active"] = is_active
        if not sets:
            return
        await self._session.execute(
            text(
                f"UPDATE patient_profiles SET {', '.join(sets)} "
                "WHERE tenant_id = :tenant_id AND id = :id"
            ),
            params,
        )

    async def lock_person(self, *, tenant_id: UUID, person_id: UUID) -> None:
        await self._session.execute(
            text(
                "SELECT id FROM tenant_persons WHERE tenant_id = :tenant_id "
                "AND id = :person_id FOR UPDATE"
            ),
            {"tenant_id": tenant_id, "person_id": person_id},
        )

    async def appointment_history(
        self, *, tenant_id: UUID, patient_profile_id: UUID, limit: int, offset: int
    ) -> tuple[list[dict[str, Any]], int]:
        params = {
            "tenant_id": tenant_id,
            "patient_id": patient_profile_id,
            "limit": limit,
            "offset": offset,
        }
        total = await self._session.execute(
            text(
                "SELECT count(*) FROM appointments "
                "WHERE tenant_id = :tenant_id AND beneficiary_patient_id = :patient_id"
            ),
            params,
        )
        rows = await self._session.execute(
            text(
                """
                SELECT a.id AS appointment_id, a.status, a.booking_channel,
                       a.scheduled_start_at_utc, a.scheduled_end_at_utc,
                       s.id AS service_id, s.service_name
                FROM appointments a
                JOIN services s ON s.tenant_id = a.tenant_id AND s.id = a.service_id
                WHERE a.tenant_id = :tenant_id AND a.beneficiary_patient_id = :patient_id
                ORDER BY a.scheduled_start_at_utc DESC, a.id
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        )
        return [dict(r._mapping) for r in rows], int(total.scalar_one())

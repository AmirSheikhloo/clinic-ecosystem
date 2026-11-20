"""Patient person/profile persistence under verified tenant GUC (BETA-01B)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7


@dataclass(frozen=True, slots=True)
class PatientRecord:
    patient_profile_id: UUID
    person_id: UUID
    tenant_id: UUID
    first_name: str
    last_name: str
    birth_date: date | None
    is_active: bool


class SqlPatientRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def register(
        self,
        *,
        tenant_id: UUID,
        first_name: str,
        last_name: str,
        birth_date: date | None = None,
        now: datetime | None = None,
    ) -> PatientRecord:
        current = now or datetime.now(timezone.utc)
        person_id = new_uuid7()
        patient_id = new_uuid7()
        await self._session.execute(
            text(
                """
                INSERT INTO tenant_persons (
                    id, tenant_id, first_name, last_name, birth_date, gender,
                    aggregate_version, created_at_utc, updated_at_utc
                ) VALUES (
                    :person_id, :tenant_id, :first_name, :last_name, :birth_date, NULL,
                    1, :now, :now
                )
                """
            ),
            {
                "person_id": person_id,
                "tenant_id": tenant_id,
                "first_name": first_name,
                "last_name": last_name,
                "birth_date": birth_date,
                "now": current,
            },
        )
        await self._session.execute(
            text(
                """
                INSERT INTO patient_profiles (
                    id, tenant_id, person_id, dossier_number, is_active, created_at_utc
                ) VALUES (
                    :patient_id, :tenant_id, :person_id, NULL, TRUE, :now
                )
                """
            ),
            {
                "patient_id": patient_id,
                "tenant_id": tenant_id,
                "person_id": person_id,
                "now": current,
            },
        )
        return PatientRecord(
            patient_profile_id=patient_id,
            person_id=person_id,
            tenant_id=tenant_id,
            first_name=first_name,
            last_name=last_name,
            birth_date=birth_date,
            is_active=True,
        )

    async def get_by_profile_id(
        self, *, tenant_id: UUID, patient_profile_id: UUID
    ) -> PatientRecord | None:
        result = await self._session.execute(
            text(
                """
                SELECT p.id AS patient_profile_id, p.person_id, p.tenant_id,
                       tp.first_name, tp.last_name, tp.birth_date, p.is_active
                FROM patient_profiles p
                JOIN tenant_persons tp
                  ON tp.tenant_id = p.tenant_id AND tp.id = p.person_id
                WHERE p.tenant_id = :tenant_id AND p.id = :patient_id
                LIMIT 1
                """
            ),
            {"tenant_id": tenant_id, "patient_id": patient_profile_id},
        )
        row = result.mappings().first()
        if row is None:
            return None
        return PatientRecord(
            patient_profile_id=row["patient_profile_id"],
            person_id=row["person_id"],
            tenant_id=row["tenant_id"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            birth_date=row["birth_date"],
            is_active=bool(row["is_active"]),
        )

    async def search_by_name(
        self,
        *,
        tenant_id: UUID,
        query: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[PatientRecord]:
        pattern = f"%{query.strip()}%"
        result = await self._session.execute(
            text(
                """
                SELECT p.id AS patient_profile_id, p.person_id, p.tenant_id,
                       tp.first_name, tp.last_name, tp.birth_date, p.is_active
                FROM patient_profiles p
                JOIN tenant_persons tp
                  ON tp.tenant_id = p.tenant_id AND tp.id = p.person_id
                WHERE p.tenant_id = :tenant_id
                  AND p.is_active = TRUE
                  AND (
                    tp.first_name ILIKE :pattern
                    OR tp.last_name ILIKE :pattern
                    OR (tp.first_name || ' ' || tp.last_name) ILIKE :pattern
                  )
                ORDER BY tp.last_name ASC, tp.first_name ASC, p.id ASC
                LIMIT :limit OFFSET :offset
                """
            ),
            {
                "tenant_id": tenant_id,
                "pattern": pattern,
                "limit": limit,
                "offset": offset,
            },
        )
        items: list[PatientRecord] = []
        for row in result.mappings().all():
            items.append(
                PatientRecord(
                    patient_profile_id=row["patient_profile_id"],
                    person_id=row["person_id"],
                    tenant_id=row["tenant_id"],
                    first_name=row["first_name"],
                    last_name=row["last_name"],
                    birth_date=row["birth_date"],
                    is_active=bool(row["is_active"]),
                )
            )
        return items

"""Display-safe patient names from tenant_persons operational name fields (clause 757/779)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession


class SqlPatientDisplayDirectory:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def display_safe_names(
        self, *, tenant_id: UUID, patient_ids: list[UUID]
    ) -> dict[UUID, str]:
        if not patient_ids:
            return {}
        result = await self._session.execute(
            text(
                """
                SELECT pp.id AS patient_id,
                       concat_ws(' ', tp.first_name, tp.last_name) AS display_name
                FROM patient_profiles pp
                JOIN tenant_persons tp
                  ON tp.tenant_id = pp.tenant_id AND tp.id = pp.person_id
                WHERE pp.tenant_id = :tenant_id
                  AND pp.id = ANY(:ids)
                """
            ).bindparams(bindparam("ids", type_=ARRAY(PGUUID(as_uuid=True)))),
            {"tenant_id": tenant_id, "ids": list(patient_ids)},
        )
        return {row.patient_id: (row.display_name or "").strip() for row in result}

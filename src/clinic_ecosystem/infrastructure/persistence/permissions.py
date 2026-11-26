"""Server-side permission checks (ALLOW_MANUAL_OVERBOOKING)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class SqlPermissionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def principal_has(
        self, *, tenant_id: UUID, principal_id: UUID, permission_code: str
    ) -> bool:
        result = await self._session.execute(
            text(
                """
                SELECT 1
                FROM user_role_assignments ura
                JOIN role_permission_assignments rpa
                  ON rpa.tenant_id = ura.tenant_id AND rpa.role_id = ura.role_id
                WHERE ura.tenant_id = :tenant_id
                  AND ura.user_account_id = :principal_id
                  AND rpa.permission_code = :permission_code
                LIMIT 1
                """
            ),
            {
                "tenant_id": tenant_id,
                "principal_id": principal_id,
                "permission_code": permission_code,
            },
        )
        return result.first() is not None

    async def effective_permissions(
        self, *, tenant_id: UUID, principal_id: UUID
    ) -> set[str]:
        result = await self._session.execute(
            text(
                """
                SELECT DISTINCT rpa.permission_code
                FROM user_role_assignments ura
                JOIN role_permission_assignments rpa
                  ON rpa.tenant_id = ura.tenant_id AND rpa.role_id = ura.role_id
                WHERE ura.tenant_id = :tenant_id
                  AND ura.user_account_id = :principal_id
                """
            ),
            {"tenant_id": tenant_id, "principal_id": principal_id},
        )
        return {row.permission_code for row in result}

    async def governance_roles(self, *, tenant_id: UUID, person_id: UUID) -> set[str]:
        result = await self._session.execute(
            text(
                """
                SELECT governance_role FROM tenant_governance_assignments
                WHERE tenant_id = :tenant_id AND person_id = :person_id
                """
            ),
            {"tenant_id": tenant_id, "person_id": person_id},
        )
        return {row.governance_role for row in result}

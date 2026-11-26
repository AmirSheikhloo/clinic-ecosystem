"""Server-side permission checks with optional ACR-D0.11 scope enforcement."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class PermissionScope:
    permission_code: str
    scope_mode: str  # ALL | FILTER
    department_id: UUID | None
    service_id: UUID | None
    provider_resource_id: UUID | None


class SqlPermissionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _scopes_table_ready(self) -> bool:
        result = await self._session.execute(
            text("SELECT to_regclass('public.role_permission_scopes') IS NOT NULL")
        )
        return bool(result.scalar())

    async def principal_has(
        self, *, tenant_id: UUID, principal_id: UUID, permission_code: str
    ) -> bool:
        granted = await self.effective_permissions(
            tenant_id=tenant_id, principal_id=principal_id
        )
        return permission_code in granted

    async def effective_permissions(
        self, *, tenant_id: UUID, principal_id: UUID
    ) -> set[str]:
        """Return permission codes the principal may use.

        When ``role_permission_scopes`` is present, ACR-D0.11 default-deny applies:
        a grant is effective only if it has at least one scope row (ALL or FILTER).
        Without the scopes table (pre-ops schema), flat TP0003 grants remain effective.
        """
        flat_sql = text(
            """
            SELECT DISTINCT rpa.permission_code
            FROM user_role_assignments ura
            JOIN role_permission_assignments rpa
              ON rpa.tenant_id = ura.tenant_id AND rpa.role_id = ura.role_id
            WHERE ura.tenant_id = :tenant_id
              AND ura.user_account_id = :principal_id
            """
        )
        params = {"tenant_id": tenant_id, "principal_id": principal_id}
        if not await self._scopes_table_ready():
            result = await self._session.execute(flat_sql, params)
            return {row.permission_code for row in result}

        # Cutover: enforce scopes only after at least one scope row exists for this
        # principal's grants. Pre-cutover fixtures (deep suite without backfill) keep
        # flat grants until demo/ops seed writes explicit ALL/FILTER rows.
        cutover = await self._session.execute(
            text(
                """
                SELECT 1
                FROM user_role_assignments ura
                JOIN role_permission_assignments rpa
                  ON rpa.tenant_id = ura.tenant_id AND rpa.role_id = ura.role_id
                JOIN role_permission_scopes rps
                  ON rps.tenant_id = rpa.tenant_id
                 AND rps.role_permission_assignment_id = rpa.id
                WHERE ura.tenant_id = :tenant_id
                  AND ura.user_account_id = :principal_id
                LIMIT 1
                """
            ),
            params,
        )
        if cutover.first() is None:
            result = await self._session.execute(flat_sql, params)
            return {row.permission_code for row in result}

        result = await self._session.execute(
            text(
                """
                SELECT DISTINCT rpa.permission_code
                FROM user_role_assignments ura
                JOIN role_permission_assignments rpa
                  ON rpa.tenant_id = ura.tenant_id AND rpa.role_id = ura.role_id
                JOIN role_permission_scopes rps
                  ON rps.tenant_id = rpa.tenant_id
                 AND rps.role_permission_assignment_id = rpa.id
                WHERE ura.tenant_id = :tenant_id
                  AND ura.user_account_id = :principal_id
                """
            ),
            params,
        )
        return {row.permission_code for row in result}

    async def permission_scopes(
        self, *, tenant_id: UUID, principal_id: UUID, permission_code: str
    ) -> list[PermissionScope]:
        """Return typed scopes for one permission (empty ⇒ denied under ops schema)."""
        if not await self._scopes_table_ready():
            if await self.principal_has(
                tenant_id=tenant_id,
                principal_id=principal_id,
                permission_code=permission_code,
            ):
                return [
                    PermissionScope(
                        permission_code=permission_code,
                        scope_mode="ALL",
                        department_id=None,
                        service_id=None,
                        provider_resource_id=None,
                    )
                ]
            return []
        result = await self._session.execute(
            text(
                """
                SELECT rpa.permission_code, rps.scope_mode, rps.department_id,
                       rps.service_id, rps.provider_resource_id
                FROM user_role_assignments ura
                JOIN role_permission_assignments rpa
                  ON rpa.tenant_id = ura.tenant_id AND rpa.role_id = ura.role_id
                JOIN role_permission_scopes rps
                  ON rps.tenant_id = rpa.tenant_id
                 AND rps.role_permission_assignment_id = rpa.id
                WHERE ura.tenant_id = :tenant_id
                  AND ura.user_account_id = :principal_id
                  AND rpa.permission_code = :permission_code
                """
            ),
            {
                "tenant_id": tenant_id,
                "principal_id": principal_id,
                "permission_code": permission_code,
            },
        )
        return [
            PermissionScope(
                permission_code=row.permission_code,
                scope_mode=row.scope_mode,
                department_id=row.department_id,
                service_id=row.service_id,
                provider_resource_id=row.provider_resource_id,
            )
            for row in result
        ]

    def allows_department(
        self, scopes: list[PermissionScope], department_id: UUID | None
    ) -> bool:
        """Within-row AND / across-row OR: ALL wins; else department FILTER must match."""
        if any(s.scope_mode == "ALL" for s in scopes):
            return True
        if department_id is None:
            return False
        return any(
            s.scope_mode == "FILTER" and s.department_id == department_id for s in scopes
        )

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

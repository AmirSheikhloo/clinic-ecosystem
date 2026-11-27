"""Server-side permission checks with ACR-D0.11 fail-closed scope enforcement."""

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

    def matches(
        self,
        *,
        department_id: UUID | None = None,
        service_id: UUID | None = None,
        provider_resource_id: UUID | None = None,
    ) -> bool:
        """Within-row AND: every non-null FILTER dimension on the row must match.

        Missing object dimensions fail closed when the FILTER row constrains that
        dimension (None on the object never satisfies a required FILTER value).
        """
        if self.scope_mode == "ALL":
            return True
        if self.scope_mode != "FILTER":
            return False
        if self.department_id is not None and self.department_id != department_id:
            return False
        if self.service_id is not None and self.service_id != service_id:
            return False
        if (
            self.provider_resource_id is not None
            and self.provider_resource_id != provider_resource_id
        ):
            return False
        # FILTER row must constrain at least one dimension (enforced by schema CHECK).
        return True


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
        Missing scopes never widen access — there is no flat-permission fallback.
        Without the scopes table (pre-ops TP0001–7 only), flat TP0003 grants apply.
        """
        params = {"tenant_id": tenant_id, "principal_id": principal_id}
        if not await self._scopes_table_ready():
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
                params,
            )
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

    def allows(
        self,
        scopes: list[PermissionScope],
        *,
        department_id: UUID | None = None,
        service_id: UUID | None = None,
        provider_resource_id: UUID | None = None,
    ) -> bool:
        """Across-row OR of within-row AND matches. Empty scopes ⇒ deny."""
        if not scopes:
            return False
        if any(s.scope_mode == "ALL" for s in scopes):
            return True
        return any(
            s.matches(
                department_id=department_id,
                service_id=service_id,
                provider_resource_id=provider_resource_id,
            )
            for s in scopes
        )

    def allows_department(
        self, scopes: list[PermissionScope], department_id: UUID | None
    ) -> bool:
        """Department-only checks still require full object dimensions when known.

        Prefer ``allows(...)`` with all object dimensions. A lone department check
        fails closed when FILTER rows constrain service/provider and those are omitted.
        """
        return self.allows(scopes, department_id=department_id)

    def allows_service(
        self, scopes: list[PermissionScope], service_id: UUID | None
    ) -> bool:
        return self.allows(scopes, service_id=service_id)

    def allows_practitioner(
        self, scopes: list[PermissionScope], provider_resource_id: UUID | None
    ) -> bool:
        """Practitioner checks must not widen via unconstrained FILTER dimensions.

        A FILTER row without a provider constraint does **not** independently grant
        all practitioners when other constrained dimensions are omitted — use
        ``allows(...)`` with department/service/provider together. This method is
        a thin alias of ``allows`` for the provider dimension only (fail-closed).
        """
        return self.allows(scopes, provider_resource_id=provider_resource_id)

    def is_unrestricted(self, scopes: list[PermissionScope]) -> bool:
        return any(s.scope_mode == "ALL" for s in scopes)

    def filter_scopes(self, scopes: list[PermissionScope]) -> list[PermissionScope]:
        """FILTER rows only (empty when ALL present or no scopes)."""
        if self.is_unrestricted(scopes):
            return []
        return [s for s in scopes if s.scope_mode == "FILTER"]

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

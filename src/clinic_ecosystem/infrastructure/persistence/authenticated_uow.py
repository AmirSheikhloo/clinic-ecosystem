"""Verified JWT to one PostgreSQL Tenant Plane transaction (clauses 747-751).

The ONLY input authority to this entrypoint is a cryptographically verified
human JWT plus an authoritative jti status check. Background/sync identities
must enter through their own separate verified trust boundaries.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from clinic_ecosystem.shared_kernel.tenant_auth import (
    HumanJwtVerifier,
    VerifiedHumanPrincipal,
)


class RuntimeRoleRejected(PermissionError):
    """A runtime caller must never operate with migration/owner/bypass powers."""


# Opaque mint token: only this module may construct VerifiedTenantDbSession.
_SCOPE_AUTH = object()

_ROLE_CHECK = text(
    """
    SELECT
      pg_has_role(current_user, 'db_app_runtime', 'member') AS is_runtime,
      pg_has_role(current_user, 'db_migrator', 'member') AS is_migrator,
      r.rolsuper AS is_superuser,
      r.rolbypassrls AS bypasses_rls
    FROM pg_roles r WHERE r.rolname = current_user
    """
)


@dataclass(frozen=True)
class VerifiedTenantDbSession:
    """Session scoped to the JWT-authenticated tenant inside one SQL transaction.

    Construction outside ``verified_jwt_transaction`` raises TypeError.
    This is an internal type guard, NOT an unforgeable Python security capability.
    """

    session: AsyncSession
    principal: VerifiedHumanPrincipal
    _auth: object = field(default=None, repr=False, compare=False)
    _reveal_finalized: bool = field(default=False, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._auth is not _SCOPE_AUTH:
            raise TypeError(
                "VerifiedTenantDbSession may only be minted by "
                "verified_jwt_transaction"
            )
        if not isinstance(self.principal, VerifiedHumanPrincipal):
            raise TypeError("verified principal required")

    def assert_provenance(self) -> None:
        """Type-level guard only; real trust comes from verified entrypoint + DB role."""
        self.__post_init__()
        if self._reveal_finalized:
            raise RuntimeRoleRejected("reveal transaction already finalized")

    async def assert_tenant_guc(self) -> None:
        """Re-read transaction-local GUC; reject spoofed or cleared tenant context."""
        self.assert_provenance()
        actual = (
            await self.session.execute(
                text("SELECT current_setting('app.current_tenant_id', true)")
            )
        ).scalar_one()
        if actual != str(self.principal.tenant_id):
            raise RuntimeRoleRejected("transaction-local tenant context mismatch")

    async def assert_reveal_transaction_clean(self) -> None:
        """Fail closed if a caller has uncommitted business DML in this UoW.

        A read+audit is only allowed when the verified session is not write-dirty.
        PostgreSQL 15's assigned XID check detects prior raw SQL DML on this
        connection; SQLAlchemy's identity maps detect pending ORM writes.
        """
        await self.assert_tenant_guc()
        if any(getattr(self.session, name, ()) for name in ("new", "dirty", "deleted")):
            raise RuntimeRoleRejected("reveal requires a clean transaction")
        clean = (
            await self.session.execute(
                text("SELECT pg_current_xact_id_if_assigned() IS NULL")
            )
        ).scalar_one()
        if clean is not True:
            raise RuntimeRoleRejected("reveal cannot commit pending business writes")

    async def finalize_reveal_audit(self) -> None:
        """Commit ONLY the isolated audit-only transaction and close this scope.

        Must follow assert_reveal_transaction_clean immediately before the
        audit append. Never re-open/rebind the same UoW after this commit.
        """
        await self.assert_tenant_guc()
        await self.session.commit()
        object.__setattr__(self, "_reveal_finalized", True)


async def _bind_tenant_guc(session: AsyncSession, tenant_id: UUID) -> None:
    await session.execute(
        text("SELECT set_config('app.current_tenant_id', :tenant, true)"),
        {"tenant": str(tenant_id)},
    )
    actual = (
        await session.execute(
            text("SELECT current_setting('app.current_tenant_id', true)")
        )
    ).scalar_one()
    if actual != str(tenant_id):
        raise RuntimeRoleRejected("transaction-local tenant context mismatch")


@asynccontextmanager
async def verified_jwt_transaction(
    *,
    engine: AsyncEngine,
    bearer_token: str,
    verifier: HumanJwtVerifier,
) -> AsyncIterator[VerifiedTenantDbSession]:
    """Verify BEFORE connection use; commit only on successful context exit.

    Tenant id is NEVER read from HTTP request parameters or arbitrary GUC.
    Use bound SQL parameters and explicit tenant scopes on all repository DML.
    No generic client-SQL execution endpoint may expose this session.
    """
    if type(verifier) is not HumanJwtVerifier:
        raise TypeError("only configured HumanJwtVerifier may authenticate a JWT")
    principal = await verifier.verify(bearer_token)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        await session.begin()
        try:
            role = (await session.execute(_ROLE_CHECK)).mappings().one_or_none()
            if (
                role is None
                or not role["is_runtime"]
                or role["is_migrator"]
                or role["is_superuser"]
                or role["bypasses_rls"]
            ):
                raise RuntimeRoleRejected("unsafe database runtime role")
            await _bind_tenant_guc(session, principal.tenant_id)
            scope = VerifiedTenantDbSession(
                session=session, principal=principal, _auth=_SCOPE_AUTH
            )
            yield scope
            if not scope._reveal_finalized:
                await scope.assert_tenant_guc()
                await session.commit()
        except Exception:
            await session.rollback()
            raise

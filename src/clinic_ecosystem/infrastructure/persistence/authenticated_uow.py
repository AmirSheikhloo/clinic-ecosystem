"""Verified JWT to one PostgreSQL Tenant Plane transaction (clauses 747-751).

The ONLY input authority to this entrypoint is a cryptographically verified
human JWT plus an authoritative jti status check. Background/sync identities
must enter through their own separate verified trust boundaries.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any
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

    Construction outside ``verified_jwt_transaction`` (or the explicit test mint)
    raises TypeError. Callers must not treat a forged dataclass as authenticated.
    """

    session: AsyncSession
    principal: VerifiedHumanPrincipal
    _auth: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._auth is not _SCOPE_AUTH:
            raise TypeError(
                "VerifiedTenantDbSession may only be minted by "
                "verified_jwt_transaction (or mint_verified_scope_for_tests)"
            )
        if not isinstance(self.principal, VerifiedHumanPrincipal):
            raise TypeError("verified principal required")

    async def assert_tenant_guc(self) -> None:
        """Re-read transaction-local GUC; reject spoofed or cleared tenant context."""
        actual = (
            await self.session.execute(
                text("SELECT current_setting('app.current_tenant_id', true)")
            )
        ).scalar_one()
        if actual != str(self.principal.tenant_id):
            raise RuntimeRoleRejected("transaction-local tenant context mismatch")

    async def commit_security_checkpoint(self) -> None:
        """Commit durable security side-effects (e.g. reveal audit) then rebind GUC.

        Used when plaintext or other irreversible disclosure must not leave the
        process unless the preceding audit row is already durable.
        """
        await self.assert_tenant_guc()
        await self.session.commit()
        await self.session.begin()
        await _bind_tenant_guc(self.session, self.principal.tenant_id)
        await self.assert_tenant_guc()


def mint_verified_scope_for_tests(
    *,
    session: Any,
    principal: VerifiedHumanPrincipal,
) -> VerifiedTenantDbSession:
    """Synthetic mint for unit/integration fixtures. Does NOT verify a JWT.

    Production composition roots must never call this.
    """
    if not isinstance(principal, VerifiedHumanPrincipal):
        raise TypeError("verified principal required")
    return VerifiedTenantDbSession(
        session=session, principal=principal, _auth=_SCOPE_AUTH
    )


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
            await scope.assert_tenant_guc()
            await session.commit()
        except Exception:
            await session.rollback()
            raise

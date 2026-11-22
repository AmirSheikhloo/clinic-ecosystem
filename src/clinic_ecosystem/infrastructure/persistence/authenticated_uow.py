"""Verified JWT to one PostgreSQL Tenant Plane transaction (clauses 747-751).

The ONLY input authority to this entrypoint is a cryptographically verified
human JWT plus an authoritative jti status check. Background/sync identities
must enter through their own separate verified trust boundaries.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from clinic_ecosystem.shared_kernel.tenant_auth import (
    HumanJwtVerifier,
    VerifiedHumanPrincipal,
)


class RuntimeRoleRejected(PermissionError):
    """A runtime caller must never operate with migration/owner/bypass powers."""


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
    """Session scoped to the JWT-authenticated tenant inside one SQL transaction."""
    session: AsyncSession
    principal: VerifiedHumanPrincipal


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
    if not isinstance(verifier, HumanJwtVerifier):
        raise TypeError("only configured HumanJwtVerifier may authenticate a JWT")
    principal = await verifier.verify(bearer_token)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        async with session.begin():
            role = (await session.execute(_ROLE_CHECK)).mappings().one_or_none()
            if (
                role is None
                or not role["is_runtime"]
                or role["is_migrator"]
                or role["is_superuser"]
                or role["bypasses_rls"]
            ):
                raise RuntimeRoleRejected("unsafe database runtime role")
            await session.execute(
                text("SELECT set_config('app.current_tenant_id', :tenant, true)"),
                {"tenant": str(principal.tenant_id)},
            )
            actual = (
                await session.execute(
                    text("SELECT current_setting('app.current_tenant_id', true)")
                )
            ).scalar_one()
            if actual != str(principal.tenant_id):
                raise RuntimeRoleRejected("transaction-local tenant context mismatch")
            yield VerifiedTenantDbSession(session=session, principal=principal)

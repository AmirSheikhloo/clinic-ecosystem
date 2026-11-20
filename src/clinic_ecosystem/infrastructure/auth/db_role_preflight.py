"""Fail-closed PostgreSQL runtime-role preflight for BETA-01A.

Verifies the live connection identity is a non-owner Tenant runtime principal
without SUPERUSER or BYPASSRLS. Rejects migrator/schema-owner style roles.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

# Authorized Tenant Plane runtime login / group role names (Appendix E / ops bootstrap).
_ALLOWED_RUNTIME_ROLES = frozenset(
    {
        "tp_app_login",
        "db_app_runtime",
        "local_app_login",
    }
)

_FORBIDDEN_ROLE_MARKERS = frozenset(
    {
        "tp_migrator_login",
        "db_migrator",
        "local_migrator_login",
        "cp_migrator_login",
        "cp_db_migrator",
        "postgres",
    }
)


class UnsafeDatabaseRoleError(RuntimeError):
    """Raised when the database connection is not a safe Tenant runtime role."""


@dataclass(frozen=True, slots=True)
class RuntimeRoleSnapshot:
    current_user: str
    session_user: str
    rolsuper: bool
    rolbypassrls: bool
    rolname: str


async def inspect_runtime_role(engine: AsyncEngine) -> RuntimeRoleSnapshot:
    async with engine.connect() as conn:
        row = (
            await conn.execute(
                text(
                    """
                    SELECT
                        current_user AS current_user,
                        session_user AS session_user,
                        r.rolname AS rolname,
                        r.rolsuper AS rolsuper,
                        r.rolbypassrls AS rolbypassrls
                    FROM pg_roles r
                    WHERE r.rolname = current_user
                    """
                )
            )
        ).mappings().one()
    return RuntimeRoleSnapshot(
        current_user=str(row["current_user"]),
        session_user=str(row["session_user"]),
        rolsuper=bool(row["rolsuper"]),
        rolbypassrls=bool(row["rolbypassrls"]),
        rolname=str(row["rolname"]),
    )


def evaluate_runtime_role(snapshot: RuntimeRoleSnapshot) -> None:
    role = snapshot.current_user
    if role in _FORBIDDEN_ROLE_MARKERS or role.endswith("_migrator") or role.endswith(
        "_migrator_login"
    ):
        raise UnsafeDatabaseRoleError(
            f"database role {role!r} is a migrator/admin identity and is not allowed"
        )
    if snapshot.rolsuper:
        raise UnsafeDatabaseRoleError(
            f"database role {role!r} has SUPERUSER privilege"
        )
    if snapshot.rolbypassrls:
        raise UnsafeDatabaseRoleError(
            f"database role {role!r} has BYPASSRLS privilege"
        )
    if role not in _ALLOWED_RUNTIME_ROLES:
        raise UnsafeDatabaseRoleError(
            f"database role {role!r} is not an authorized Tenant runtime identity"
        )


async def verify_runtime_db_role(engine: AsyncEngine) -> RuntimeRoleSnapshot:
    snapshot = await inspect_runtime_role(engine)
    evaluate_runtime_role(snapshot)
    return snapshot

"""Fail-closed PostgreSQL runtime-role preflight for BETA-01A.

Verifies BOTH session_user (login) and current_user (effective role).
An elevated login that merely ``SET ROLE db_app_runtime`` must not pass.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

# Authorized LOGIN principals for Tenant Plane / Local Hub runtime.
_ALLOWED_RUNTIME_LOGINS = frozenset(
    {
        "tp_app_login",
        "local_app_login",
    }
)

# Effective roles permitted only when the session login is an authorized runtime login.
_ALLOWED_CURRENT_ROLES_BY_LOGIN: dict[str, frozenset[str]] = {
    "tp_app_login": frozenset({"tp_app_login", "db_app_runtime"}),
    "local_app_login": frozenset({"local_app_login", "db_app_runtime"}),
}

_FORBIDDEN_ROLE_MARKERS = frozenset(
    {
        "tp_migrator_login",
        "db_migrator",
        "local_migrator_login",
        "cp_migrator_login",
        "cp_db_migrator",
        "cp_app_login",
        "cp_db_app_runtime",
        "postgres",
    }
)

_FORBIDDEN_MEMBERSHIP_ROLES = frozenset(
    {
        "db_migrator",
        "tp_migrator_login",
        "local_migrator_login",
        "cp_db_migrator",
        "cp_migrator_login",
    }
)


class UnsafeDatabaseRoleError(RuntimeError):
    """Raised when the database connection is not a safe Tenant runtime role."""


@dataclass(frozen=True, slots=True)
class RuntimeRoleSnapshot:
    current_user: str
    session_user: str
    current_rolsuper: bool
    current_rolbypassrls: bool
    session_rolsuper: bool
    session_rolbypassrls: bool
    session_member_of_forbidden: tuple[str, ...]
    # Backward-compatible aliases used by older call sites/tests.
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
                        cur.rolsuper AS current_rolsuper,
                        cur.rolbypassrls AS current_rolbypassrls,
                        sess.rolsuper AS session_rolsuper,
                        sess.rolbypassrls AS session_rolbypassrls,
                        COALESCE((
                            SELECT array_agg(r.rolname ORDER BY r.rolname)
                            FROM pg_auth_members m
                            JOIN pg_roles r ON r.oid = m.roleid
                            JOIN pg_roles u ON u.oid = m.member
                            WHERE u.rolname = session_user
                              AND r.rolname IN (
                                  'db_migrator',
                                  'tp_migrator_login',
                                  'local_migrator_login',
                                  'cp_db_migrator',
                                  'cp_migrator_login'
                              )
                        ), ARRAY[]::name[]) AS session_forbidden_memberships
                    FROM pg_roles cur
                    JOIN pg_roles sess ON sess.rolname = session_user
                    WHERE cur.rolname = current_user
                    """
                )
            )
        ).mappings().one()
    forbidden = tuple(str(x) for x in (row["session_forbidden_memberships"] or ()))
    current_user = str(row["current_user"])
    return RuntimeRoleSnapshot(
        current_user=current_user,
        session_user=str(row["session_user"]),
        current_rolsuper=bool(row["current_rolsuper"]),
        current_rolbypassrls=bool(row["current_rolbypassrls"]),
        session_rolsuper=bool(row["session_rolsuper"]),
        session_rolbypassrls=bool(row["session_rolbypassrls"]),
        session_member_of_forbidden=forbidden,
        rolsuper=bool(row["current_rolsuper"]),
        rolbypassrls=bool(row["current_rolbypassrls"]),
        rolname=current_user,
    )


def _is_forbidden_identity(role: str) -> bool:
    return (
        role in _FORBIDDEN_ROLE_MARKERS
        or role.endswith("_migrator")
        or role.endswith("_migrator_login")
    )


def evaluate_runtime_role(snapshot: RuntimeRoleSnapshot) -> None:
    session = snapshot.session_user
    current = snapshot.current_user

    if _is_forbidden_identity(session):
        raise UnsafeDatabaseRoleError(
            f"session login {session!r} is a migrator/admin identity and is not allowed"
        )
    if _is_forbidden_identity(current):
        raise UnsafeDatabaseRoleError(
            f"current role {current!r} is a migrator/admin identity and is not allowed"
        )

    if snapshot.session_rolsuper or snapshot.current_rolsuper:
        raise UnsafeDatabaseRoleError(
            f"database session/current role has SUPERUSER privilege "
            f"(session={session!r}, current={current!r})"
        )
    if snapshot.session_rolbypassrls or snapshot.current_rolbypassrls:
        raise UnsafeDatabaseRoleError(
            f"database session/current role has BYPASSRLS privilege "
            f"(session={session!r}, current={current!r})"
        )

    if snapshot.session_member_of_forbidden:
        raise UnsafeDatabaseRoleError(
            f"session login {session!r} has forbidden role membership: "
            f"{list(snapshot.session_member_of_forbidden)}"
        )

    if session not in _ALLOWED_RUNTIME_LOGINS:
        raise UnsafeDatabaseRoleError(
            f"session login {session!r} is not an authorized Tenant runtime login"
        )

    allowed_current = _ALLOWED_CURRENT_ROLES_BY_LOGIN[session]
    if current not in allowed_current:
        raise UnsafeDatabaseRoleError(
            f"current role {current!r} is not consistent with authorized "
            f"session login {session!r}"
        )


async def verify_runtime_db_role(engine: AsyncEngine) -> RuntimeRoleSnapshot:
    snapshot = await inspect_runtime_role(engine)
    evaluate_runtime_role(snapshot)
    return snapshot

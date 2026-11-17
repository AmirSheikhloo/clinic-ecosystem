"""Ephemeral role/schema bootstrap for synthetic PG15 only (E0.3)."""

from __future__ import annotations

import hashlib
import os
import secrets
from uuid import uuid4

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

MIGRATOR = "exp_e03_migrator"
APP = "exp_e03_app"
SYNTH_PW = "synth-only-not-secret"


def require_pg15(dsn: str) -> dict:
    conn = psycopg2.connect(dsn)
    try:
        cur = conn.cursor()
        cur.execute("SHOW server_version_num")
        v = int(cur.fetchone()[0])
        if not (150000 <= v <= 159999):
            raise RuntimeError(f"PostgreSQL 15 required, got server_version_num={v}")
        cur.execute(
            "SELECT inet_server_addr(), current_database(), version(), current_user, session_user"
        )
        addr, db, ver, cu, su = cur.fetchone()
        return {
            "server_version_num": v,
            "database": db,
            "addr": addr,
            "version": ver,
            "current_user": cu,
            "session_user": su,
        }
    finally:
        conn.close()


def bootstrap_roles(admin_dsn: str) -> None:
    conn = psycopg2.connect(admin_dsn)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    try:
        cur = conn.cursor()
        for role in (MIGRATOR, APP):
            cur.execute(
                f"""
                DO $$ BEGIN
                  CREATE ROLE {role} NOINHERIT LOGIN PASSWORD '{SYNTH_PW}';
                EXCEPTION WHEN duplicate_object THEN
                  ALTER ROLE {role} WITH LOGIN PASSWORD '{SYNTH_PW}';
                END $$
                """
            )
        cur.execute(f"ALTER ROLE {MIGRATOR} NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE")
        cur.execute(f"ALTER ROLE {APP} NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE")
        cur.execute(f"GRANT ALL ON SCHEMA public TO {MIGRATOR}")
        cur.execute(f"GRANT USAGE ON SCHEMA public TO {APP}")
        cur.execute(
            f"""
            ALTER DEFAULT PRIVILEGES FOR ROLE {MIGRATOR} IN SCHEMA public
              GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {APP}
            """
        )
        cur.execute("SELECT current_user")
        admin_user = cur.fetchone()[0]
        cur.execute(f"GRANT {MIGRATOR} TO {admin_user}")
        cur.execute(f"GRANT {APP} TO {admin_user}")
    finally:
        conn.close()


def ensure_databases(
    admin_dsn: str, names: tuple[str, ...] = ("exp_e03", "exp_e03_cloud", "exp_e03_local")
) -> None:
    conn = psycopg2.connect(admin_dsn)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    try:
        cur = conn.cursor()
        for name in names:
            cur.execute("SELECT 1 FROM pg_database WHERE datname=%s", (name,))
            if not cur.fetchone():
                cur.execute(f'CREATE DATABASE "{name}"')
    finally:
        conn.close()


def admin_dsn_from_env() -> str:
    url = os.environ.get("EXP_E03_ADMIN_DSN") or os.environ.get("EXP_E03_DATABASE_URL")
    if not url:
        raise RuntimeError("EXP_E03_ADMIN_DSN or EXP_E03_DATABASE_URL required")
    return url


def _rewrite_user(base: str, user: str) -> str:
    scheme, rest = base.split("://", 1)
    _, hostpart = rest.split("@", 1)
    return f"{scheme}://{user}:{SYNTH_PW}@{hostpart}"


def migrator_url(base: str | None = None) -> str:
    base = base or os.environ.get("EXP_E03_DATABASE_URL") or admin_dsn_from_env()
    return _rewrite_user(base, MIGRATOR)


def app_dsn(base: str | None = None) -> str:
    base = base or admin_dsn_from_env()
    return _rewrite_user(base, APP)


def dsn_for_db(admin_dsn: str, dbname: str) -> str:
    prefix, _old = admin_dsn.rsplit("/", 1)
    return f"{prefix}/{dbname}"


def synthetic_hmac(material: str) -> bytes:
    return hashlib.sha256(f"synth::{material}".encode()).digest()


def seed_tenant_identifier(
    dsn: str, *, with_next: bool = False, canonical: str | None = None
) -> tuple[str, str, str]:
    tenant = str(uuid4())
    ident = str(uuid4())
    canon = canonical or f"synth-{secrets.token_hex(4)}"
    active = synthetic_hmac(f"{tenant}:{canon}:1")
    conn = psycopg2.connect(dsn)
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO exp_e03_tenants(tenant_id, label) VALUES (%s::uuid, %s)",
            (tenant, "synthetic"),
        )
        if with_next:
            nxt = synthetic_hmac(f"{tenant}:{canon}:2")
            cur.execute(
                """
                INSERT INTO exp_e03_identifiers(
                  id, tenant_id, canonical_value, lookup_hmac_active,
                  hmac_key_version_active, lookup_hmac_next, hmac_key_version_next
                ) VALUES (%s::uuid, %s::uuid, %s, %s, 1, %s, 2)
                """,
                (ident, tenant, canon, psycopg2.Binary(active), psycopg2.Binary(nxt)),
            )
        else:
            cur.execute(
                """
                INSERT INTO exp_e03_identifiers(
                  id, tenant_id, canonical_value, lookup_hmac_active,
                  hmac_key_version_active
                ) VALUES (%s::uuid, %s::uuid, %s, %s, 1)
                """,
                (ident, tenant, canon, psycopg2.Binary(active)),
            )
        conn.commit()
        return tenant, ident, canon
    finally:
        conn.close()


def enable_rls_for_app(admin_dsn: str) -> None:
    conn = psycopg2.connect(admin_dsn)
    conn.autocommit = True
    try:
        cur = conn.cursor()
        cur.execute("ALTER TABLE exp_e03_identifiers ENABLE ROW LEVEL SECURITY")
        cur.execute("ALTER TABLE exp_e03_identifiers FORCE ROW LEVEL SECURITY")
        cur.execute("DROP POLICY IF EXISTS exp_e03_ident_tenant ON exp_e03_identifiers")
        cur.execute(
            """
            CREATE POLICY exp_e03_ident_tenant ON exp_e03_identifiers
              FOR ALL TO exp_e03_app
              USING (tenant_id::text = current_setting('app.tenant_id', true))
              WITH CHECK (tenant_id::text = current_setting('app.tenant_id', true))
            """
        )
        cur.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON exp_e03_identifiers TO {APP}")
        cur.execute(f"GRANT SELECT ON exp_e03_tenants TO {APP}")
        cur.execute(f"GRANT SELECT ON exp_e03_meta TO {APP}")
    finally:
        conn.close()

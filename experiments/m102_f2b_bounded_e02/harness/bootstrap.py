"""Ephemeral role/schema bootstrap for synthetic PG15 only."""

from __future__ import annotations

import hashlib
import os
import secrets
from uuid import uuid4

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


def require_pg15(dsn: str) -> str:
    conn = psycopg2.connect(dsn)
    try:
        cur = conn.cursor()
        cur.execute("SHOW server_version_num")
        v = int(cur.fetchone()[0])
        if not (150000 <= v <= 159999):
            raise RuntimeError(f"PostgreSQL 15 required, got server_version_num={v}")
        cur.execute("SELECT inet_server_addr(), current_database(), version()")
        addr, db, ver = cur.fetchone()
        return f"server_version_num={v}; db={db}; addr={addr}; version={ver}"
    finally:
        conn.close()


def bootstrap_roles_and_rls(admin_dsn: str) -> None:
    conn = psycopg2.connect(admin_dsn)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    try:
        cur = conn.cursor()
        for role in ("exp_f2b_migrator", "exp_f2b_app"):
            cur.execute(
                f"""
                DO $$ BEGIN
                  CREATE ROLE {role} NOINHERIT LOGIN PASSWORD 'synth-only-not-secret';
                EXCEPTION WHEN duplicate_object THEN
                  ALTER ROLE {role} WITH LOGIN PASSWORD 'synth-only-not-secret';
                END $$
                """
            )
        cur.execute("ALTER ROLE exp_f2b_migrator NOSUPERUSER NOBYPASSRLS")
        cur.execute("ALTER ROLE exp_f2b_app NOSUPERUSER NOBYPASSRLS")
        cur.execute("GRANT ALL ON SCHEMA public TO exp_f2b_migrator")
        cur.execute("GRANT USAGE ON SCHEMA public TO exp_f2b_app")
        # Default privileges for future tables owned by migrator
        cur.execute(
            """
            ALTER DEFAULT PRIVILEGES FOR ROLE exp_f2b_migrator IN SCHEMA public
              GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO exp_f2b_app
            """
        )
    finally:
        conn.close()


def admin_dsn_from_env() -> str:
    url = os.environ.get("EXP_F2B_ADMIN_DSN") or os.environ.get("EXP_F2B_DATABASE_URL")
    if not url:
        raise RuntimeError("EXP_F2B_ADMIN_DSN or EXP_F2B_DATABASE_URL required")
    return url


def migrator_url() -> str:
    """SQLAlchemy URL as migrator role."""
    base = os.environ.get("EXP_F2B_DATABASE_URL")
    if not base:
        raise RuntimeError("EXP_F2B_DATABASE_URL required")
    # Rewrite user if postgres://postgres:... pattern from CI service
    if "://" in base:
        scheme, rest = base.split("://", 1)
        if "@" in rest:
            creds, hostpart = rest.split("@", 1)
            return f"{scheme}://exp_f2b_migrator:synth-only-not-secret@{hostpart}"
    return base


def app_dsn() -> str:
    base = admin_dsn_from_env()
    scheme, rest = base.split("://", 1)
    _, hostpart = rest.split("@", 1)
    return f"{scheme}://exp_f2b_app:synth-only-not-secret@{hostpart}"


def synthetic_hmac(material: str) -> bytes:
    return hashlib.sha256(f"synth::{material}".encode()).digest()


def seed_tenant_identifier(dsn: str, *, with_next: bool = False) -> tuple[str, str]:
    tenant = str(uuid4())
    ident = str(uuid4())
    canon = f"synth-{secrets.token_hex(4)}"
    active = synthetic_hmac(f"{tenant}:{canon}:1")
    conn = psycopg2.connect(dsn)
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO exp_f2b_tenants(tenant_id, label) VALUES (%s::uuid, %s)",
            (tenant, "synthetic"),
        )
        if with_next:
            nxt = synthetic_hmac(f"{tenant}:{canon}:2")
            cur.execute(
                """
                INSERT INTO exp_f2b_identifiers(
                  id, tenant_id, canonical_value, lookup_hmac_active,
                  hmac_key_version_active, lookup_hmac_next, hmac_key_version_next
                ) VALUES (%s::uuid, %s::uuid, %s, %s, 1, %s, 2)
                """,
                (ident, tenant, canon, psycopg2.Binary(active), psycopg2.Binary(nxt)),
            )
        else:
            cur.execute(
                """
                INSERT INTO exp_f2b_identifiers(
                  id, tenant_id, canonical_value, lookup_hmac_active,
                  hmac_key_version_active
                ) VALUES (%s::uuid, %s::uuid, %s, %s, 1)
                """,
                (ident, tenant, canon, psycopg2.Binary(active)),
            )
        conn.commit()
        return tenant, ident
    finally:
        conn.close()

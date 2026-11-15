"""Read-only metadata assertions on disposable PostgreSQL 15 Testcontainers.
Only existing TP0001..TP0007 migrations may be applied (never TP0008+).
"""
from __future__ import annotations

import json
from pathlib import Path

import asyncpg
import pytest

from tests.integration.alembic_runner import (
    ensure_control_plane_version_table_async,
    upgrade_tenant_plane_async,
)

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
@pytest.mark.parametrize("plane", ["cloud_tenant", "local_hub"])
async def test_existing_tp0007_pg15_catalog_and_indexes(plane_topology, plane: str) -> None:
    ep = getattr(plane_topology, plane)
    await upgrade_tenant_plane_async(ep.sqlalchemy_async_url(), revision="tp0007")
    conn = await asyncpg.connect(ep.asyncpg_dsn())
    try:
        server_version = int(await conn.fetchval("SHOW server_version_num"))
        assert 150000 <= server_version < 160000
        revision = await conn.fetchval(
            "SELECT version_num FROM alembic_meta.alembic_version_tp"
        )
        assert revision == "tp0007"

        rows = await conn.fetch(
            """
            SELECT idx.relname AS name, tab.relname AS relation,
                   i.indisunique AS is_unique, i.indisvalid AS valid,
                   i.indisready AS ready, pg_get_indexdef(idx.oid) AS definition
            FROM pg_index AS i
            JOIN pg_class AS idx ON idx.oid=i.indexrelid
            JOIN pg_class AS tab ON tab.oid=i.indrelid
            JOIN pg_namespace AS ns ON ns.oid=tab.relnamespace
            WHERE ns.nspname='public' AND idx.relname=ANY($1::text[])
            ORDER BY idx.relname
            """,
            ["uq_person_identifier_active_lookup",
             "uq_person_identifier_next_lookup", "ix_person_phones_lookup"],
        )
        indexes = {row["name"]: dict(row) for row in rows}
        assert len(indexes) == 3
        assert indexes["uq_person_identifier_active_lookup"]["is_unique"]
        assert indexes["uq_person_identifier_next_lookup"]["is_unique"]
        assert "lookup_hmac_next IS NOT NULL" in indexes[
            "uq_person_identifier_next_lookup"]["definition"]
        assert not indexes["ix_person_phones_lookup"]["is_unique"]
        assert all(row["valid"] and row["ready"] for row in indexes.values())

        tables = ["tenant_registry", "tenant_persons", "person_identifiers",
                  "person_phones", "patient_profiles", "user_accounts", "audit_entries"]
        rls_rows = await conn.fetch(
            """
            SELECT c.relname AS name, c.relrowsecurity AS enabled,
                   c.relforcerowsecurity AS forced
            FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='public' AND c.relname=ANY($1::text[])
            ORDER BY c.relname
            """,
            tables,
        )
        rls = {row["name"]: dict(row) for row in rls_rows}
        assert len(rls) == len(tables)
        assert all(row["enabled"] and row["forced"] for row in rls.values())
        policies = await conn.fetch(
            """
            SELECT tablename, policyname, permissive
            FROM pg_policies
            WHERE schemaname='public' AND tablename=ANY($1::text[])
            """,
            tables,
        )
        grouped = {}
        for row in policies:
            grouped.setdefault(row["tablename"], {})[row["policyname"]] = row["permissive"]
        expected = {
            "tenant_runtime_base": "PERMISSIVE",
            "tenant_runtime_guard": "RESTRICTIVE",
            "tenant_migrator_maintenance": "PERMISSIVE",
        }
        assert all(grouped.get(name) == expected for name in tables)
        # Only catalog metadata: never credentials, patient data, or row contents.
        result = {
            "scope": "ephemeral PostgreSQL 15 Testcontainers",
            "plane": plane,
            "database": await conn.fetchval("SELECT current_database()"),
            "server_version_num": server_version,
            "alembic_revision": revision,
            "indexes": indexes,
            "rls": rls,
            "policy_types": grouped,
        }
        output = Path("preflight-pg15-evidence")
        output.mkdir(exist_ok=True)
        (output / f"{plane}.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_control_plane_alembic_metadata_only(plane_topology) -> None:
    await ensure_control_plane_version_table_async(
        plane_topology.cloud_control.sqlalchemy_async_url()
    )
    conn = await asyncpg.connect(plane_topology.cloud_control.asyncpg_dsn())
    try:
        assert 150000 <= int(await conn.fetchval("SHOW server_version_num")) < 160000
        version_table = await conn.fetchval(
            "SELECT to_regclass('alembic_meta.alembic_version_cp')::text"
        )
        assert version_table is not None
        # This does not prove Control Plane business migrations are implemented.
    finally:
        await conn.close()

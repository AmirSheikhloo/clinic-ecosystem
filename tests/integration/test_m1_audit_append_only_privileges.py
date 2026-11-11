"""VERIFY-01: audit_entries is append-only for Tenant Plane Runtime after TP0007.

Proves effective privileges via has_table_privilege / has_column_privilege and
real UPDATE/DELETE denials under tp_app_login with a matching Tenant GUC so RLS
cannot masquerade as a privilege denial. Preserves Runtime INSERT (append).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.parse import quote_plus
from uuid import UUID

import asyncpg
import pytest

from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7
from tests.integration.alembic_runner import upgrade_tenant_plane_async
from tests.integration.docker_probe import DOCKER_AVAILABLE, SKIP_REASON

pytestmark = pytest.mark.integration

AUDIT_TABLE = "public.audit_entries"
AUDIT_COLUMNS = (
    "id",
    "tenant_id",
    "actor_type",
    "actor_id",
    "operation",
    "target_type",
    "target_id",
    "details_json",
    "created_at_utc",
)


def _runtime_dsn(plane_topology) -> str:
    pwd = plane_topology.passwords["tp_app_login"]
    ep = plane_topology.cloud_tenant
    return (
        f"postgresql://{quote_plus('tp_app_login')}:{quote_plus(pwd)}"
        f"@{ep.host}:{ep.port}/tenant_app"
    )


async def _seed_tenant_and_audit(
    mig: asyncpg.Connection,
) -> tuple[UUID, UUID, dict[str, object]]:
    """Insert tenant + audit fixture as migrator (authorized setup path)."""
    tenant_id = new_uuid7()
    audit_id = new_uuid7()
    actor_id = new_uuid7()
    now = datetime.now(timezone.utc)
    details = {"probe": "append-only-privilege", "marker": "unchanged"}
    await mig.execute("SET ROLE db_migrator")
    await mig.execute(
        """
        INSERT INTO tenant_registry (
          tenant_id, tenant_status, timezone_name, created_at_utc, updated_at_utc
        ) VALUES ($1, 'ACTIVE', 'UTC', $2, $2)
        """,
        tenant_id,
        now,
    )
    await mig.execute(
        """
        INSERT INTO audit_entries (
          id, tenant_id, actor_type, actor_id, operation,
          target_type, target_id, details_json, created_at_utc
        ) VALUES (
          $1, $2, 'USER', $3, 'PRIVILEGE_PROBE',
          'appointment', NULL, CAST($4 AS jsonb), $5
        )
        """,
        audit_id,
        tenant_id,
        actor_id,
        json.dumps(details),
        now,
    )
    await mig.execute("RESET ROLE")
    original = {
        "id": audit_id,
        "tenant_id": tenant_id,
        "actor_type": "USER",
        "actor_id": actor_id,
        "operation": "PRIVILEGE_PROBE",
        "target_type": "appointment",
        "target_id": None,
        "details_json": details,
        "created_at_utc": now,
    }
    return tenant_id, audit_id, original


@pytest.mark.asyncio
async def test_audit_entries_runtime_cannot_update_or_delete_with_tenant_guc(
    plane_topology,
) -> None:
    if not DOCKER_AVAILABLE:
        pytest.skip(SKIP_REASON)

    await upgrade_tenant_plane_async(plane_topology.cloud_tenant.sqlalchemy_async_url())

    tenant_id: UUID
    audit_id: UUID
    original: dict[str, object]
    baseline: asyncpg.Record

    mig = await asyncpg.connect(plane_topology.cloud_tenant.asyncpg_dsn())
    try:
        tenant_id, audit_id, original = await _seed_tenant_and_audit(mig)

        # --- A. Effective privilege checks (inherited + direct + PUBLIC) ---
        for role in ("tp_app_login", "db_app_runtime"):
            for priv in ("UPDATE", "DELETE"):
                granted = await mig.fetchval(
                    "SELECT has_table_privilege($1, $2, $3)",
                    role,
                    AUDIT_TABLE,
                    priv,
                )
                assert granted is False, f"{role} must lack table {priv} on {AUDIT_TABLE}"

            for col in AUDIT_COLUMNS:
                col_update = await mig.fetchval(
                    "SELECT has_column_privilege($1, $2, $3, 'UPDATE')",
                    role,
                    AUDIT_TABLE,
                    col,
                )
                assert col_update is False, (
                    f"{role} must lack column UPDATE on {AUDIT_TABLE}.{col}"
                )

        # PUBLIC must not retain table UPDATE/DELETE either.
        for priv in ("UPDATE", "DELETE"):
            assert (
                await mig.fetchval(
                    "SELECT has_table_privilege('public', $1, $2)",
                    AUDIT_TABLE,
                    priv,
                )
                is False
            ), f"PUBLIC must lack table {priv}"

        # Runtime must retain SELECT + INSERT (append-only contract).
        for role in ("tp_app_login", "db_app_runtime"):
            for priv in ("SELECT", "INSERT"):
                assert (
                    await mig.fetchval(
                        "SELECT has_table_privilege($1, $2, $3)",
                        role,
                        AUDIT_TABLE,
                        priv,
                    )
                    is True
                ), f"{role} must retain table {priv}"

        # Capture a byte-identical snapshot for post-mutation verification.
        baseline_row = await mig.fetchrow(
            """
            SELECT id, tenant_id, actor_type, actor_id, operation,
                   target_type, target_id, details_json::text AS details_text,
                   created_at_utc
            FROM audit_entries WHERE id = $1
            """,
            audit_id,
        )
        assert baseline_row is not None
        baseline = baseline_row
    finally:
        await mig.close()

    conn = await asyncpg.connect(_runtime_dsn(plane_topology))
    try:
        # --- B. Real UPDATE denial with matching Tenant GUC ---
        tx_update = conn.transaction()
        await tx_update.start()
        try:
            await conn.execute(
                "SELECT set_config('app.current_tenant_id', $1, true)", str(tenant_id)
            )
            visible = await conn.fetchrow(
                """
                SELECT id, operation, details_json::text AS details_text
                FROM audit_entries WHERE id = $1
                """,
                audit_id,
            )
            assert visible is not None, "target audit row must be visible under matching GUC"
            assert visible["id"] == audit_id
            assert visible["operation"] == "PRIVILEGE_PROBE"

            with pytest.raises(asyncpg.InsufficientPrivilegeError) as update_exc:
                await conn.execute(
                    """
                    UPDATE audit_entries
                    SET operation = 'TAMPERED'
                    WHERE id = $1
                    """,
                    audit_id,
                )
            assert update_exc.value.sqlstate == "42501"
        finally:
            await tx_update.rollback()

        # --- B. Real DELETE denial with matching Tenant GUC (fresh transaction) ---
        tx_delete = conn.transaction()
        await tx_delete.start()
        try:
            await conn.execute(
                "SELECT set_config('app.current_tenant_id', $1, true)", str(tenant_id)
            )
            visible = await conn.fetchval(
                "SELECT id FROM audit_entries WHERE id = $1", audit_id
            )
            assert visible == audit_id

            with pytest.raises(asyncpg.InsufficientPrivilegeError) as delete_exc:
                await conn.execute(
                    "DELETE FROM audit_entries WHERE id = $1",
                    audit_id,
                )
            assert delete_exc.value.sqlstate == "42501"
        finally:
            await tx_delete.rollback()

        # --- C. Runtime append (INSERT) remains permitted under matching GUC ---
        tx_insert = conn.transaction()
        await tx_insert.start()
        try:
            await conn.execute(
                "SELECT set_config('app.current_tenant_id', $1, true)", str(tenant_id)
            )
            append_id = new_uuid7()
            await conn.execute(
                """
                INSERT INTO audit_entries (
                  id, tenant_id, actor_type, actor_id, operation,
                  target_type, target_id, details_json, created_at_utc
                ) VALUES (
                  $1, $2, 'USER', $3, 'APPEND_PROBE',
                  'appointment', NULL, '{}'::jsonb, NOW()
                )
                """,
                append_id,
                tenant_id,
                new_uuid7(),
            )
            appended = await conn.fetchval(
                "SELECT id FROM audit_entries WHERE id = $1", append_id
            )
            assert appended == append_id
        finally:
            await tx_insert.rollback()
    finally:
        await conn.close()

    # --- Post-condition: original fixture row unchanged via authorized inspection ---
    inspect_conn = await asyncpg.connect(plane_topology.cloud_tenant.asyncpg_dsn())
    try:
        await inspect_conn.execute("SET ROLE db_migrator")
        after = await inspect_conn.fetchrow(
            """
            SELECT id, tenant_id, actor_type, actor_id, operation,
                   target_type, target_id, details_json::text AS details_text,
                   created_at_utc
            FROM audit_entries WHERE id = $1
            """,
            audit_id,
        )
        await inspect_conn.execute("RESET ROLE")
        assert after is not None
        assert after["id"] == baseline["id"]
        assert after["tenant_id"] == baseline["tenant_id"]
        assert after["actor_type"] == baseline["actor_type"]
        assert after["actor_id"] == baseline["actor_id"]
        assert after["operation"] == baseline["operation"]
        assert after["target_type"] == baseline["target_type"]
        assert after["target_id"] == baseline["target_id"]
        assert after["details_text"] == baseline["details_text"]
        assert after["created_at_utc"] == baseline["created_at_utc"]
        assert after["operation"] == original["operation"]
    finally:
        await inspect_conn.close()

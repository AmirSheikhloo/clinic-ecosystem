"""P2 generation-sidecar HMAC physical experiment on disposable PG15.

EXPERIMENTAL ONLY — higher frozen F.2 compatibility review burden than P1.
"""

from __future__ import annotations

from urllib.parse import quote_plus
from uuid import uuid4

import asyncpg
import pytest

from experiments.m102_hmac_physical.concurrent_ops import (
    create_unique_index_concurrently_via_alembic,
    two_session_unique_conflict,
)
from experiments.m102_hmac_physical.fixtures import (
    fetch_index_catalog,
    insert_identifier,
    seed_tenant_person,
    tp0002_indexes_intact,
)
from experiments.m102_hmac_physical.p2_generation_sidecar import (
    P2_CANDIDATE_INDEX,
    P2_CANDIDATE_INDEX_DDL,
    P2_NEXT_INDEX,
    P2_NEXT_INDEX_DDL,
    P2_TABLE,
    apply_p2_expand,
)
from experiments.m102_hmac_physical.phase_gate import (
    advance_to,
    cutover_generation,
    init_model,
    set_candidate_generation,
)
from experiments.m102_hmac_physical.rotation import (
    p2_backfill_candidate_batch,
    p2_upsert_generation,
)
from experiments.m102_hmac_physical.synthetic_hmac import synthetic_lookup_hmac
from tests.integration.alembic_runner import upgrade_tenant_plane_async
from tests.integration.docker_probe import DOCKER_AVAILABLE, SKIP_REASON

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not DOCKER_AVAILABLE, reason=SKIP_REASON),
]


async def _mig(ep):
    conn = await asyncpg.connect(ep.asyncpg_dsn())
    await conn.execute("SET ROLE db_migrator")
    return conn


def _runtime_dsn(plane_topology) -> str:
    pwd = plane_topology.passwords["tp_app_login"]
    ep = plane_topology.cloud_tenant
    return (
        f"postgresql://{quote_plus('tp_app_login')}:{quote_plus(pwd)}"
        f"@{ep.host}:{ep.port}/tenant_app"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("plane", ["cloud_tenant", "local_hub"])
async def test_p2_sidecar_expand_rls_and_nonredundant_candidate_index(
    plane_topology, plane: str
) -> None:
    ep = getattr(plane_topology, plane)
    await upgrade_tenant_plane_async(ep.sqlalchemy_async_url(), revision="tp0007")
    conn = await _mig(ep)
    try:
        await apply_p2_expand(conn)
        await init_model(conn, model="P2")
        tenant, person = await seed_tenant_person(conn)
        rows = []
        for i in range(4):
            rows.append(
                await insert_identifier(
                    conn,
                    tenant_id=tenant,
                    person_id=person,
                    normalized=f"444{i:07d}",
                    next_version=None,
                )
            )
        for fx in rows:
            await p2_upsert_generation(
                conn,
                tenant_id=fx.tenant_id,
                identifier_id=fx.identifier_id,
                person_id=fx.person_id,
                id_type=fx.id_type,
                authority=fx.authority,
                normalized=fx.normalized,
                hmac_key_version=1,
                status="ACTIVE",
            )
            await p2_upsert_generation(
                conn,
                tenant_id=fx.tenant_id,
                identifier_id=fx.identifier_id,
                person_id=fx.person_id,
                id_type=fx.id_type,
                authority=fx.authority,
                normalized=fx.normalized,
                hmac_key_version=2,
                status="CANDIDATE",
            )
        assert await tp0002_indexes_intact(conn)
        for phase in (1, 2, 3, 4, 5):
            await advance_to(conn, model="P2", phase=phase)
        await set_candidate_generation(conn, model="P2", candidate=2)
        # Sidecar FORCE RLS enabled.
        assert await conn.fetchval(
            """
            SELECT c.relrowsecurity AND c.relforcerowsecurity
            FROM pg_class c
            WHERE c.relname = $1
            """,
            P2_TABLE,
        )
    finally:
        await conn.close()

    await create_unique_index_concurrently_via_alembic(
        ep.sqlalchemy_async_url(), P2_CANDIDATE_INDEX_DDL
    )
    conn = await _mig(ep)
    try:
        await advance_to(conn, model="P2", phase=6)
        cat = {
            r["name"]: r
            for r in await fetch_index_catalog(
                conn,
                [
                    "uq_person_identifier_active_lookup",
                    "uq_person_identifier_next_lookup",
                    P2_CANDIDATE_INDEX,
                ],
            )
        }
        assert P2_CANDIDATE_INDEX in cat
        assert cat[P2_CANDIDATE_INDEX]["valid"] and cat[P2_CANDIDATE_INDEX]["ready"]
        assert "generation_status" in cat[P2_CANDIDATE_INDEX]["definition"]
        assert "CANDIDATE" in cat[P2_CANDIDATE_INDEX]["definition"]
        # Not the TP0002 next index expression.
        assert "lookup_hmac_next" not in cat[P2_CANDIDATE_INDEX]["definition"]
        assert await conn.fetchval(
            "SELECT version_num FROM alembic_meta.alembic_version_tp"
        ) == "tp0007"
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_p2_deterministic_candidate_writer_conflict(plane_topology) -> None:
    ep = plane_topology.cloud_tenant
    await upgrade_tenant_plane_async(ep.sqlalchemy_async_url(), revision="tp0007")
    conn = await _mig(ep)
    try:
        await apply_p2_expand(conn)
        tenant, p1 = await seed_tenant_person(conn)
        _, p2 = await seed_tenant_person(conn, tenant_id=tenant, person_id=uuid4())
        a = await insert_identifier(
            conn, tenant_id=tenant, person_id=p1, normalized="5550000001", next_version=None
        )
        b = await insert_identifier(
            conn, tenant_id=tenant, person_id=p2, normalized="5550000002", next_version=None
        )
    finally:
        await conn.close()

    await create_unique_index_concurrently_via_alembic(
        ep.sqlalchemy_async_url(), P2_CANDIDATE_INDEX_DDL
    )

    conflict = synthetic_lookup_hmac(
        tenant_id=tenant,
        id_type="IR_NATIONAL_ID",
        issuing_country_or_authority="IR",
        normalized_identifier="collision-canonical",
        hmac_key_version=2,
    )

    async def first_insert(c: asyncpg.Connection) -> None:
        await c.execute(
            f"""
            INSERT INTO {P2_TABLE} (
              id, tenant_id, identifier_id, person_id, id_type,
              issuing_country_or_authority, hmac_key_version, lookup_hmac,
              generation_status, created_at_utc
            ) VALUES ($1,$2,$3,$4,'IR_NATIONAL_ID','IR',2,$5,'CANDIDATE',NOW())
            """,
            uuid4(),
            tenant,
            a.identifier_id,
            p1,
            conflict,
        )

    async def second_insert(c: asyncpg.Connection) -> None:
        await c.execute(
            f"""
            INSERT INTO {P2_TABLE} (
              id, tenant_id, identifier_id, person_id, id_type,
              issuing_country_or_authority, hmac_key_version, lookup_hmac,
              generation_status, created_at_utc
            ) VALUES ($1,$2,$3,$4,'IR_NATIONAL_ID','IR',2,$5,'CANDIDATE',NOW())
            """,
            uuid4(),
            tenant,
            b.identifier_id,
            p2,
            conflict,
        )

    first, second = await two_session_unique_conflict(
        dsn=ep.asyncpg_dsn(),
        first_insert=first_insert,
        second_insert=second_insert,
    )
    assert first == "committed"
    assert second == "unique_violation"


@pytest.mark.asyncio
async def test_p2_two_cycle_backfill_cutover_and_runtime_rls(plane_topology) -> None:
    ep = plane_topology.cloud_tenant
    await upgrade_tenant_plane_async(ep.sqlalchemy_async_url(), revision="tp0007")
    conn = await _mig(ep)
    try:
        await apply_p2_expand(conn)
        await init_model(conn, model="P2")
        tenant, person = await seed_tenant_person(conn)
        for i in range(5):
            fx = await insert_identifier(
                conn,
                tenant_id=tenant,
                person_id=person,
                normalized=f"666{i:07d}",
                next_version=None,
            )
            await p2_upsert_generation(
                conn,
                tenant_id=fx.tenant_id,
                identifier_id=fx.identifier_id,
                person_id=fx.person_id,
                id_type=fx.id_type,
                authority=fx.authority,
                normalized=fx.normalized,
                hmac_key_version=1,
                status="ACTIVE",
            )
        for phase in (1, 2, 3):
            await advance_to(conn, model="P2", phase=phase)
        n1, cur = await p2_backfill_candidate_batch(
            conn, tenant_id=tenant, candidate_version=2, batch_size=2
        )
        assert n1 == 2
        n2, _ = await p2_backfill_candidate_batch(
            conn,
            tenant_id=tenant,
            candidate_version=2,
            batch_size=10,
            after_identifier_id=cur,
        )
        assert n2 == 3
        assert (
            await conn.fetchval(
                f"""
                SELECT count(*) FROM {P2_TABLE}
                WHERE tenant_id=$1 AND hmac_key_version=2 AND generation_status='CANDIDATE'
                """,
                tenant,
            )
            == 5
        )
        for phase in (4, 5):
            await advance_to(conn, model="P2", phase=phase)
    finally:
        await conn.close()

    await create_unique_index_concurrently_via_alembic(
        ep.sqlalchemy_async_url(), P2_CANDIDATE_INDEX_DDL
    )
    await create_unique_index_concurrently_via_alembic(
        ep.sqlalchemy_async_url(), P2_NEXT_INDEX_DDL
    )

    conn = await _mig(ep)
    try:
        for phase in (6, 7, 8):
            await advance_to(conn, model="P2", phase=phase)
        # Promote candidates -> NEXT then ACTIVE (cycle 1 cutover).
        await conn.execute(
            f"""
            UPDATE {P2_TABLE}
            SET generation_status='NEXT'
            WHERE tenant_id=$1 AND hmac_key_version=2
            """,
            tenant,
        )
        await conn.execute(
            f"""
            UPDATE {P2_TABLE}
            SET generation_status='RETIRED', retired_at_utc=NOW()
            WHERE tenant_id=$1 AND hmac_key_version=1 AND generation_status='ACTIVE'
            """,
            tenant,
        )
        await conn.execute(
            f"""
            UPDATE {P2_TABLE}
            SET generation_status='ACTIVE'
            WHERE tenant_id=$1 AND hmac_key_version=2
            """,
            tenant,
        )
        await cutover_generation(conn, model="P2", new_active=2)

        # Cycle 2: version 3 candidates.
        n3, _ = await p2_backfill_candidate_batch(
            conn, tenant_id=tenant, candidate_version=3, batch_size=50
        )
        assert n3 == 5
        await set_candidate_generation(conn, model="P2", candidate=3)
        await advance_to(conn, model="P2", phase=9)
        assert (
            await conn.fetchval(
                "SELECT phase9_operational_executed FROM m102_exp_rotation_phase_meta WHERE model='P2'"
            )
            is False
        )
        assert await tp0002_indexes_intact(conn)
        cat = await fetch_index_catalog(conn, [P2_CANDIDATE_INDEX, P2_NEXT_INDEX])
        assert len(cat) == 2
    finally:
        await conn.close()

    # Runtime login visibility under matching Tenant GUC (Cloud boundary).
    runtime = await asyncpg.connect(_runtime_dsn(plane_topology))
    try:
        visible_no_guc = await runtime.fetchval(f"SELECT count(*) FROM {P2_TABLE}")
        assert visible_no_guc == 0
        tx = runtime.transaction()
        await tx.start()
        try:
            await runtime.execute(
                "SELECT set_config('app.current_tenant_id', $1, true)", str(tenant)
            )
            visible = await runtime.fetchval(
                f"SELECT count(*) FROM {P2_TABLE} WHERE tenant_id=$1", tenant
            )
            assert visible >= 5
        finally:
            await tx.rollback()
    finally:
        await runtime.close()

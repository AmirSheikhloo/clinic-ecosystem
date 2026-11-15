"""P2 generation-sidecar experiment — N02/N03/N04 corrections.

EXPERIMENTAL ONLY — higher frozen F.2 compatibility review burden than P1.
"""

from __future__ import annotations

from urllib.parse import quote_plus
from uuid import uuid4

import asyncpg
import pytest

from experiments.m102_hmac_physical.concurrent_ops import (
    create_and_assert_unique_index,
    two_session_unique_conflict,
)
from experiments.m102_hmac_physical.fixtures import (
    insert_identifier,
    seed_tenant_person,
    tp0002_indexes_intact,
)
from experiments.m102_hmac_physical.lifecycle import (
    prepare_cutover_candidate,
    progress_with_evidence,
)
from experiments.m102_hmac_physical.p2_generation_sidecar import (
    P2_ACTIVE_INDEX,
    P2_ACTIVE_INDEX_DDL,
    P2_CANDIDATE_INDEX,
    P2_CANDIDATE_INDEX_DDL,
    P2_TABLE,
    apply_p2_expand,
)
from experiments.m102_hmac_physical.phase_gate import cutover_generation, get_state, init_model
from experiments.m102_hmac_physical.rotation import (
    p2_backfill_candidate_batch,
    p2_promote_candidate_to_active,
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
        await progress_with_evidence(conn, model="P2", to_phase=5)
        assert await conn.fetchval(
            """
            SELECT c.relrowsecurity AND c.relforcerowsecurity
            FROM pg_class c WHERE c.relname = $1
            """,
            P2_TABLE,
        )
        await conn.execute(f"DROP INDEX CONCURRENTLY IF EXISTS public.{P2_CANDIDATE_INDEX}")
        await conn.execute(f"DROP INDEX CONCURRENTLY IF EXISTS public.{P2_ACTIVE_INDEX}")
    finally:
        await conn.close()

    await create_and_assert_unique_index(
        sqlalchemy_async_url=ep.sqlalchemy_async_url(),
        inspect_dsn=ep.asyncpg_dsn(),
        ddl=P2_CANDIDATE_INDEX_DDL,
        index_name=P2_CANDIDATE_INDEX,
        table_name=P2_TABLE,
        required_fragments=["generation_status", "CANDIDATE"],
        forbidden_fragments=["lookup_hmac_next"],
    )
    await create_and_assert_unique_index(
        sqlalchemy_async_url=ep.sqlalchemy_async_url(),
        inspect_dsn=ep.asyncpg_dsn(),
        ddl=P2_ACTIVE_INDEX_DDL,
        index_name=P2_ACTIVE_INDEX,
        table_name=P2_TABLE,
        required_fragments=["generation_status", "ACTIVE"],
    )


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
        await conn.execute(f"DROP INDEX CONCURRENTLY IF EXISTS public.{P2_CANDIDATE_INDEX}")
    finally:
        await conn.close()

    await create_and_assert_unique_index(
        sqlalchemy_async_url=ep.sqlalchemy_async_url(),
        inspect_dsn=ep.asyncpg_dsn(),
        ddl=P2_CANDIDATE_INDEX_DDL,
        index_name=P2_CANDIDATE_INDEX,
        table_name=P2_TABLE,
        required_fragments=["CANDIDATE"],
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

    first, second, observed = await two_session_unique_conflict(
        dsn=ep.asyncpg_dsn(),
        first_insert=first_insert,
        second_insert=second_insert,
        require_observed_lock_wait=True,
    )
    assert first == "committed"
    assert second == "unique_violation"
    assert observed is True


@pytest.mark.asyncio
async def test_p2_active_uniqueness_person_consistency_and_two_cycles(
    plane_topology,
) -> None:
    ep = plane_topology.cloud_tenant
    await upgrade_tenant_plane_async(ep.sqlalchemy_async_url(), revision="tp0007")
    conn = await _mig(ep)
    try:
        await apply_p2_expand(conn)
        await init_model(conn, model="P2")
        tenant, person = await seed_tenant_person(conn)
        _, other = await seed_tenant_person(conn, tenant_id=tenant, person_id=uuid4())
        fixtures = []
        for i in range(5):
            fx = await insert_identifier(
                conn,
                tenant_id=tenant,
                person_id=person,
                normalized=f"666{i:07d}",
                next_version=None,
            )
            fixtures.append(fx)
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

        # Person mismatch must fail closed.
        with pytest.raises(asyncpg.PostgresError):
            await conn.execute(
                f"""
                INSERT INTO {P2_TABLE} (
                  id, tenant_id, identifier_id, person_id, id_type,
                  issuing_country_or_authority, hmac_key_version, lookup_hmac,
                  generation_status, created_at_utc
                ) VALUES ($1,$2,$3,$4,'IR_NATIONAL_ID','IR',9,$5,'CANDIDATE',NOW())
                """,
                uuid4(),
                tenant,
                fixtures[0].identifier_id,
                other,  # wrong person
                b"\x11" * 32,
            )

        await progress_with_evidence(conn, model="P2", to_phase=3)
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
        await progress_with_evidence(conn, model="P2", to_phase=5)
        await conn.execute(f"DROP INDEX CONCURRENTLY IF EXISTS public.{P2_ACTIVE_INDEX}")
        await conn.execute(f"DROP INDEX CONCURRENTLY IF EXISTS public.{P2_CANDIDATE_INDEX}")
    finally:
        await conn.close()

    # Build ACTIVE index before promotion (may cover existing ACTIVE v1 rows).
    await create_and_assert_unique_index(
        sqlalchemy_async_url=ep.sqlalchemy_async_url(),
        inspect_dsn=ep.asyncpg_dsn(),
        ddl=P2_ACTIVE_INDEX_DDL,
        index_name=P2_ACTIVE_INDEX,
        table_name=P2_TABLE,
        required_fragments=["ACTIVE"],
    )
    await create_and_assert_unique_index(
        sqlalchemy_async_url=ep.sqlalchemy_async_url(),
        inspect_dsn=ep.asyncpg_dsn(),
        ddl=P2_CANDIDATE_INDEX_DDL,
        index_name=P2_CANDIDATE_INDEX,
        table_name=P2_TABLE,
        required_fragments=["CANDIDATE"],
    )

    conn = await _mig(ep)
    try:
        await progress_with_evidence(conn, model="P2", to_phase=7)
        await prepare_cutover_candidate(conn, model="P2", candidate=2)
        await progress_with_evidence(conn, model="P2", to_phase=8)
        await p2_promote_candidate_to_active(
            conn, tenant_id=tenant, from_version=1, to_version=2
        )
        await cutover_generation(conn, model="P2", new_active=2)
        assert (
            await conn.fetchval(
                f"""
                SELECT count(*) FROM {P2_TABLE}
                WHERE tenant_id=$1 AND hmac_key_version=2 AND generation_status='ACTIVE'
                """,
                tenant,
            )
            == 5
        )

        # Duplicate ACTIVE under generation-2 authority must fail.
        with pytest.raises(asyncpg.UniqueViolationError):
            await conn.execute(
                f"""
                INSERT INTO {P2_TABLE} (
                  id, tenant_id, identifier_id, person_id, id_type,
                  issuing_country_or_authority, hmac_key_version, lookup_hmac,
                  generation_status, created_at_utc
                )
                SELECT $1, tenant_id, identifier_id, person_id, id_type,
                       issuing_country_or_authority, 99, lookup_hmac,
                       'ACTIVE', NOW()
                FROM {P2_TABLE}
                WHERE tenant_id=$2 AND hmac_key_version=2
                LIMIT 1
                """,
                uuid4(),
                tenant,
            )

        # Cycle 2 candidates (v3) while ACTIVE v2 remains indexed.
        n3, _ = await p2_backfill_candidate_batch(
            conn, tenant_id=tenant, candidate_version=3, batch_size=50
        )
        assert n3 == 5
        await prepare_cutover_candidate(conn, model="P2", candidate=3)
        await p2_promote_candidate_to_active(
            conn, tenant_id=tenant, from_version=2, to_version=3
        )
        await cutover_generation(conn, model="P2", new_active=3)
        assert (await get_state(conn, "P2")).active_generation == 3
        await progress_with_evidence(conn, model="P2", to_phase=9)
        assert (await get_state(conn, "P2")).phase9_operational_executed is False
        assert await tp0002_indexes_intact(conn)
    finally:
        await conn.close()

    runtime = await asyncpg.connect(_runtime_dsn(plane_topology))
    try:
        assert await runtime.fetchval(f"SELECT count(*) FROM {P2_TABLE}") == 0
        tx = runtime.transaction()
        await tx.start()
        try:
            await runtime.execute(
                "SELECT set_config('app.current_tenant_id', $1, true)", str(tenant)
            )
            assert (
                await runtime.fetchval(
                    f"SELECT count(*) FROM {P2_TABLE} WHERE tenant_id=$1", tenant
                )
                >= 5
            )
        finally:
            await tx.rollback()
    finally:
        await runtime.close()

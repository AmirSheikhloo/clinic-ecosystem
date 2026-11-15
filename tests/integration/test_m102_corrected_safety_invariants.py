"""Regression tests proving N01–N05 unsafe sequences now fail closed.

PASS means the previously observed safety gap is closed under disposable PG15.
"""

from __future__ import annotations

from uuid import uuid4

import asyncpg
import pytest

from experiments.m102_hmac_physical.concurrent_ops import create_and_assert_unique_index
from experiments.m102_hmac_physical.fixtures import insert_identifier, seed_tenant_person
from experiments.m102_hmac_physical.lifecycle import (
    prepare_cutover_candidate,
    progress_with_evidence,
)
from experiments.m102_hmac_physical.p1_staged_columns import (
    P1_GEN2_INDEX,
    P1_GEN2_INDEX_DDL,
    apply_p1_expand,
)
from experiments.m102_hmac_physical.p2_generation_sidecar import (
    P2_ACTIVE_INDEX,
    P2_ACTIVE_INDEX_DDL,
    P2_TABLE,
    apply_p2_expand,
)
from experiments.m102_hmac_physical.phase_gate import (
    PhaseGateError,
    advance_to,
    cutover_generation,
    get_state,
    init_model,
)
from experiments.m102_hmac_physical.rotation import (
    RotationError,
    p1_drop_generation_index_if_safe,
    p1_dual_write_gen2,
    p1_rollback_gen2,
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


@pytest.mark.asyncio
async def test_n01_closed_cannot_wipe_or_drop_active_gen2_after_cutover(
    plane_topology,
) -> None:
    ep = plane_topology.cloud_tenant
    await upgrade_tenant_plane_async(ep.sqlalchemy_async_url(), revision="tp0007")
    conn = await _mig(ep)
    try:
        await apply_p1_expand(conn)
        await init_model(conn, model="P1")
        tenant, person = await seed_tenant_person(conn)
        fx = await insert_identifier(
            conn, tenant_id=tenant, person_id=person, normalized="1000000099", next_version=None
        )
        await p1_dual_write_gen2(
            conn,
            identifier_id=fx.identifier_id,
            tenant_id=tenant,
            id_type=fx.id_type,
            authority=fx.authority,
            normalized=fx.normalized,
        )
        await progress_with_evidence(conn, model="P1", to_phase=5)
        await conn.execute(f"DROP INDEX CONCURRENTLY IF EXISTS public.{P1_GEN2_INDEX}")
    finally:
        await conn.close()

    await create_and_assert_unique_index(
        sqlalchemy_async_url=ep.sqlalchemy_async_url(),
        inspect_dsn=ep.asyncpg_dsn(),
        ddl=P1_GEN2_INDEX_DDL,
        index_name=P1_GEN2_INDEX,
        table_name="person_identifiers",
        required_fragments=["exp_lookup_hmac_gen2"],
    )
    conn = await _mig(ep)
    try:
        await progress_with_evidence(conn, model="P1", to_phase=7)
        await prepare_cutover_candidate(conn, model="P1", candidate=2)
        await progress_with_evidence(conn, model="P1", to_phase=8)
        await cutover_generation(conn, model="P1", new_active=2)
        assert (await get_state(conn, "P1")).active_generation == 2
        with pytest.raises(RotationError):
            await p1_rollback_gen2(conn, tenant_id=tenant)
        with pytest.raises(RotationError):
            await p1_drop_generation_index_if_safe(
                conn, model="P1", generation=2, index_name=P1_GEN2_INDEX
            )
        assert await conn.fetchval(
            "SELECT to_regclass($1)::text", f"public.{P1_GEN2_INDEX}"
        )
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_n02_n03_closed_active_index_and_person_mismatch_rejected(
    plane_topology,
) -> None:
    ep = plane_topology.cloud_tenant
    await upgrade_tenant_plane_async(ep.sqlalchemy_async_url(), revision="tp0007")
    conn = await _mig(ep)
    try:
        await apply_p2_expand(conn)
        tenant, p1 = await seed_tenant_person(conn)
        _, p2 = await seed_tenant_person(conn, tenant_id=tenant, person_id=uuid4())
        a = await insert_identifier(
            conn, tenant_id=tenant, person_id=p1, normalized="2000000099", next_version=None
        )
        digest = synthetic_lookup_hmac(
            tenant_id=tenant,
            id_type=a.id_type,
            issuing_country_or_authority=a.authority,
            normalized_identifier=a.normalized,
            hmac_key_version=2,
        )
        await conn.execute(
            f"""
            INSERT INTO {P2_TABLE} (
              id, tenant_id, identifier_id, person_id, id_type,
              issuing_country_or_authority, hmac_key_version, lookup_hmac,
              generation_status, created_at_utc
            ) VALUES ($1,$2,$3,$4,$5,$6,2,$7,'ACTIVE',NOW())
            """,
            uuid4(),
            tenant,
            a.identifier_id,
            p1,
            a.id_type,
            a.authority,
            digest,
        )
        await conn.execute(f"DROP INDEX CONCURRENTLY IF EXISTS public.{P2_ACTIVE_INDEX}")
    finally:
        await conn.close()

    await create_and_assert_unique_index(
        sqlalchemy_async_url=ep.sqlalchemy_async_url(),
        inspect_dsn=ep.asyncpg_dsn(),
        ddl=P2_ACTIVE_INDEX_DDL,
        index_name=P2_ACTIVE_INDEX,
        table_name=P2_TABLE,
        required_fragments=["ACTIVE"],
    )

    conn = await _mig(ep)
    try:
        assert await conn.fetchval(
            "SELECT to_regclass($1)::text", f"public.{P2_ACTIVE_INDEX}"
        )
        with pytest.raises(asyncpg.UniqueViolationError):
            await conn.execute(
                f"""
                INSERT INTO {P2_TABLE} (
                  id, tenant_id, identifier_id, person_id, id_type,
                  issuing_country_or_authority, hmac_key_version, lookup_hmac,
                  generation_status, created_at_utc
                ) VALUES ($1,$2,$3,$4,$5,$6,3,$7,'ACTIVE',NOW())
                """,
                uuid4(),
                tenant,
                a.identifier_id,
                p1,
                a.id_type,
                a.authority,
                digest,
            )
        with pytest.raises(asyncpg.PostgresError):
            await conn.execute(
                f"""
                INSERT INTO {P2_TABLE} (
                  id, tenant_id, identifier_id, person_id, id_type,
                  issuing_country_or_authority, hmac_key_version, lookup_hmac,
                  generation_status, created_at_utc
                ) VALUES ($1,$2,$3,$4,$5,$6,4,$7,'CANDIDATE',NOW())
                """,
                uuid4(),
                tenant,
                a.identifier_id,
                p2,
                a.id_type,
                a.authority,
                b"\x22" * 32,
            )
        with pytest.raises(asyncpg.PostgresError):
            await conn.execute(
                f"""
                INSERT INTO {P2_TABLE} (
                  id, tenant_id, identifier_id, person_id, id_type,
                  issuing_country_or_authority, hmac_key_version, lookup_hmac,
                  generation_status, created_at_utc
                ) VALUES ($1,$2,$3,$4,'FOREIGN_PASSPORT','US',5,$5,'CANDIDATE',NOW())
                """,
                uuid4(),
                tenant,
                a.identifier_id,
                p1,
                b"\x33" * 32,
            )
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_n05_closed_phase_gate_rejects_evidenceless_transitions(
    plane_topology,
) -> None:
    ep = plane_topology.cloud_tenant
    await upgrade_tenant_plane_async(ep.sqlalchemy_async_url(), revision="tp0007")
    conn = await _mig(ep)
    try:
        await init_model(conn, model="P1")
        with pytest.raises(PhaseGateError, match="cutover"):
            await cutover_generation(conn, model="P1", new_active=2)
        await advance_to(conn, model="P1", phase=1)
        await advance_to(conn, model="P1", phase=2)
        await advance_to(conn, model="P1", phase=3)
        with pytest.raises(PhaseGateError, match="drain"):
            await advance_to(conn, model="P1", phase=4)
        with pytest.raises(asyncpg.CheckViolationError):
            await conn.execute(
                """
                UPDATE m102_exp_rotation_phase_meta
                SET phase9_operational_executed=TRUE WHERE model='P1'
                """
            )
    finally:
        await conn.close()

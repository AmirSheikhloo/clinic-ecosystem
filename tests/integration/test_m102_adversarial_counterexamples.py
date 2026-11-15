"""Adversarial observations of experimental P1/P2 contract gaps.

Tests are NEGATIVE proofs on disposable PG15, not passing security acceptance.
A PASS here means a safety guarantee is MISSING from the experiment.
No production code or official migrations.
"""
from __future__ import annotations

from uuid import uuid4

import asyncpg
import pytest

from experiments.m102_hmac_physical.concurrent_ops import create_unique_index_concurrently_via_alembic
from experiments.m102_hmac_physical.fixtures import insert_identifier, seed_tenant_person
from experiments.m102_hmac_physical.p1_staged_columns import (
    P1_GEN2_INDEX, P1_GEN2_INDEX_DDL, apply_p1_expand,
)
from experiments.m102_hmac_physical.p2_generation_sidecar import (
    P2_TABLE, P2_ACTIVE_INDEX, apply_p2_expand,
)
from experiments.m102_hmac_physical.phase_gate import (
    advance_to, cutover_generation, get_state, init_model,
)
from experiments.m102_hmac_physical.rotation import p1_rollback_gen2
from experiments.m102_hmac_physical.synthetic_hmac import synthetic_lookup_hmac
from tests.integration.alembic_runner import upgrade_tenant_plane_async
from tests.integration.docker_probe import DOCKER_AVAILABLE, SKIP_REASON

pytestmark = [pytest.mark.integration, pytest.mark.skipif(not DOCKER_AVAILABLE, reason=SKIP_REASON)]


async def _migrator(ep):
    c = await asyncpg.connect(ep.asyncpg_dsn())
    await c.execute("SET ROLE db_migrator")
    assert await c.fetchval("SELECT current_user") == "db_migrator"
    return c


@pytest.mark.asyncio
async def test_adversarial_p1_cutover_then_rollback_removes_active_gen2_authority(plane_topology):
    """OBSERVED GAP: P1 phase-8 metadata can name generation 2 after its index is dropped."""
    ep = plane_topology.cloud_tenant
    await upgrade_tenant_plane_async(ep.sqlalchemy_async_url(), revision="tp0007")
    c = await _migrator(ep)
    try:
        await apply_p1_expand(c)
        await init_model(c, model="P1", active_generation=1)
        tenant, p1 = await seed_tenant_person(c)
        _, p2 = await seed_tenant_person(c, tenant_id=tenant, person_id=uuid4())
        a = await insert_identifier(c, tenant_id=tenant, person_id=p1,
                                    normalized="1000000011", next_version=None)
        b = await insert_identifier(c, tenant_id=tenant, person_id=p2,
                                    normalized="1000000022", next_version=None)
        for fx in (a, b):
            value = synthetic_lookup_hmac(
                tenant_id=tenant, id_type=fx.id_type,
                issuing_country_or_authority=fx.authority,
                normalized_identifier=fx.normalized, hmac_key_version=2
            )
            await c.execute(
                "UPDATE person_identifiers SET exp_lookup_hmac_gen2=$2, "
                "exp_hmac_key_version_gen2=2 WHERE id=$1", fx.identifier_id, value
            )
    finally:
        await c.close()

    await create_unique_index_concurrently_via_alembic(ep.sqlalchemy_async_url(), P1_GEN2_INDEX_DDL)
    c = await _migrator(ep)
    try:
        for phase in range(1, 9):
            await advance_to(c, model="P1", phase=phase)
        await cutover_generation(c, model="P1", new_active=2)
        # The exact rollback sequence used in the Cursor two-rotation-cycle test.
        assert await p1_rollback_gen2(c, tenant_id=tenant) == 2
        await c.execute(f"DROP INDEX CONCURRENTLY IF EXISTS public.{P1_GEN2_INDEX}")
        state = await get_state(c, "P1")
        assert state.active_generation == 2
        assert await c.fetchval("SELECT to_regclass($1)::text", f"public.{P1_GEN2_INDEX}") is None

        # Under the purported gen2 active authority, duplicate staged hashes
        # can now be written because the gen2 index is gone. Old gen1 hashes differ.
        new1 = await insert_identifier(c, tenant_id=tenant, person_id=p1,
                                       normalized="1000000033", next_version=None)
        new2 = await insert_identifier(c, tenant_id=tenant, person_id=p2,
                                       normalized="1000000044", next_version=None)
        collision = b"\x7a" * 32
        for ident in (new1.identifier_id, new2.identifier_id):
            await c.execute(
                "UPDATE person_identifiers SET exp_lookup_hmac_gen2=$2, "
                "exp_hmac_key_version_gen2=2 WHERE id=$1", ident, collision
            )
        assert await c.fetchval(
            "SELECT count(*) FROM person_identifiers "
            "WHERE tenant_id=$1 AND exp_lookup_hmac_gen2=$2", tenant, collision
        ) == 2
    finally:
        await c.close()


@pytest.mark.asyncio
async def test_adversarial_p2_active_status_has_no_unique_index_and_person_mismatch(plane_topology):
    """OBSERVED GAP: P2 never installs ACTIVE index; duplicated/mismatched rows pass."""
    ep = plane_topology.cloud_tenant
    await upgrade_tenant_plane_async(ep.sqlalchemy_async_url(), revision="tp0007")
    c = await _migrator(ep)
    try:
        await apply_p2_expand(c)
        tenant, p1 = await seed_tenant_person(c)
        _, p2 = await seed_tenant_person(c, tenant_id=tenant, person_id=uuid4())
        a = await insert_identifier(c, tenant_id=tenant, person_id=p1,
                                    normalized="2000000011", next_version=None)
        b = await insert_identifier(c, tenant_id=tenant, person_id=p2,
                                    normalized="2000000022", next_version=None)
        assert await c.fetchval(
            "SELECT to_regclass($1)::text", f"public.{P2_ACTIVE_INDEX}"
        ) is None
        collision = b"\x4b" * 32
        for identifier_id, person_id in ((a.identifier_id, p2), (b.identifier_id, p2)):
            await c.execute(
                f"INSERT INTO public.{P2_TABLE} "
                "(id,tenant_id,identifier_id,person_id,id_type,"
                "issuing_country_or_authority,hmac_key_version,lookup_hmac,"
                "generation_status,created_at_utc) "
                "VALUES($1,$2,$3,$4,'IR_NATIONAL_ID','IR',2,$5,'ACTIVE',NOW())",
                uuid4(), tenant, identifier_id, person_id, collision
            )
        assert await c.fetchval(
            f"SELECT count(*) FROM public.{P2_TABLE} "
            "WHERE tenant_id=$1 AND generation_status='ACTIVE' AND lookup_hmac=$2",
            tenant, collision,
        ) == 2
        # a.identifier_id belongs to p1 but the sidecar permits p2.
        assert await c.fetchval(
            f"SELECT person_id FROM public.{P2_TABLE} "
            "WHERE identifier_id=$1", a.identifier_id
        ) == p2
    finally:
        await c.close()


@pytest.mark.asyncio
async def test_adversarial_phase_gate_can_cutover_without_evidence_or_enforce_phase9_flag(plane_topology):
    """OBSERVED GAP: metadata-only phase stepping is not a real rollout gate."""
    ep = plane_topology.cloud_tenant
    await upgrade_tenant_plane_async(ep.sqlalchemy_async_url(), revision="tp0007")
    c = await _migrator(ep)
    try:
        await init_model(c, model="P1")
        # No schema expansion, old-instance drain, backfill, index, or validation.
        for phase in range(1, 9):
            await advance_to(c, model="P1", phase=phase)
        await cutover_generation(c, model="P1", new_active=99)
        assert (await get_state(c, "P1")).active_generation == 99
        await advance_to(c, model="P1", phase=9)
        await c.execute(
            "UPDATE public.m102_exp_rotation_phase_meta "
            "SET phase9_operational_executed=TRUE WHERE model='P1'"
        )
        assert (await get_state(c, "P1")).phase9_operational_executed is True
    finally:
        await c.close()

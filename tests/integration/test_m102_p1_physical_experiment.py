"""P1 staged-column HMAC physical experiment on disposable PG15.

EXPERIMENTAL ONLY — not Package-1, not official TP0008+, not Gate A evidence.
"""

from __future__ import annotations

from uuid import uuid4

import asyncpg
import pytest

from experiments.m102_hmac_physical.concurrent_ops import (
    create_unique_index_concurrently_via_alembic,
    drop_invalid_and_retry,
    force_invalid_unique_index,
    two_session_unique_conflict,
)
from experiments.m102_hmac_physical.fixtures import (
    fetch_index_catalog,
    insert_identifier,
    seed_tenant_person,
    tp0002_indexes_intact,
)
from experiments.m102_hmac_physical.p1_staged_columns import (
    P1_GEN2_INDEX,
    P1_GEN2_INDEX_DDL,
    P1_GEN3_INDEX,
    P1_GEN3_INDEX_DDL,
    apply_p1_expand,
)
from experiments.m102_hmac_physical.phase_gate import (
    PhaseGateError,
    advance_to,
    cutover_generation,
    experimental_upgrade_head,
    init_model,
    set_candidate_generation,
)
from experiments.m102_hmac_physical.rotation import (
    p1_backfill_gen2_batch,
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
@pytest.mark.parametrize("plane", ["cloud_tenant", "local_hub"])
async def test_p1_expand_preserves_tp0002_indexes_and_adds_nonredundant_gen2(
    plane_topology, plane: str
) -> None:
    ep = getattr(plane_topology, plane)
    await upgrade_tenant_plane_async(ep.sqlalchemy_async_url(), revision="tp0007")
    conn = await _mig(ep)
    try:
        await apply_p1_expand(conn)
        await init_model(conn, model="P1", active_generation=1)
        tenant, person = await seed_tenant_person(conn)
        # Populate before Phase-6 index build.
        for i in range(5):
            await insert_identifier(
                conn,
                tenant_id=tenant,
                person_id=person,
                normalized=f"001{i:07d}",
            )
        for i in range(5):
            row = await conn.fetchrow(
                "SELECT id, id_type, issuing_country_or_authority, id_ciphertext "
                "FROM person_identifiers WHERE tenant_id=$1 ORDER BY id OFFSET $2 LIMIT 1",
                tenant,
                i,
            )
            normalized = bytes(row["id_ciphertext"])[len(b"cipher:") :].decode()
            await p1_dual_write_gen2(
                conn,
                identifier_id=row["id"],
                tenant_id=tenant,
                id_type=row["id_type"],
                authority=row["issuing_country_or_authority"],
                normalized=normalized,
                gen2_version=2,
            )
        assert await tp0002_indexes_intact(conn)

        for phase in (1, 2, 3, 4, 5):
            await advance_to(conn, model="P1", phase=phase)
        await set_candidate_generation(conn, model="P1", candidate=2)
    finally:
        await conn.close()

    await create_unique_index_concurrently_via_alembic(
        ep.sqlalchemy_async_url(), P1_GEN2_INDEX_DDL
    )

    conn = await _mig(ep)
    try:
        await advance_to(conn, model="P1", phase=6)
        catalog = {
            r["name"]: r
            for r in await fetch_index_catalog(
                conn,
                [
                    "uq_person_identifier_active_lookup",
                    "uq_person_identifier_next_lookup",
                    P1_GEN2_INDEX,
                ],
            )
        }
        assert set(catalog) == {
            "uq_person_identifier_active_lookup",
            "uq_person_identifier_next_lookup",
            P1_GEN2_INDEX,
        }
        assert catalog[P1_GEN2_INDEX]["valid"] and catalog[P1_GEN2_INDEX]["ready"]
        assert "exp_lookup_hmac_gen2" in catalog[P1_GEN2_INDEX]["definition"]
        assert "lookup_hmac_next" not in catalog[P1_GEN2_INDEX]["definition"]
        # Nonredundant physical target: different OID and different indexed column.
        assert (
            catalog[P1_GEN2_INDEX]["oid"]
            != catalog["uq_person_identifier_next_lookup"]["oid"]
        )
        assert await conn.fetchval(
            "SELECT version_num FROM alembic_meta.alembic_version_tp"
        ) == "tp0007"
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_p1_deterministic_old_new_writer_conflict_on_gen2(
    plane_topology,
) -> None:
    ep = plane_topology.cloud_tenant
    await upgrade_tenant_plane_async(ep.sqlalchemy_async_url(), revision="tp0007")
    conn = await _mig(ep)
    try:
        await apply_p1_expand(conn)
        tenant, p1 = await seed_tenant_person(conn)
        _, p2 = await seed_tenant_person(conn, tenant_id=tenant, person_id=uuid4())
        # Existing active uniqueness remains for version-1 values.
        await insert_identifier(
            conn, tenant_id=tenant, person_id=p1, normalized="1111111111", next_version=None
        )
    finally:
        await conn.close()

    await create_unique_index_concurrently_via_alembic(
        ep.sqlalchemy_async_url(), P1_GEN2_INDEX_DDL
    )

    conflict_hmac = synthetic_lookup_hmac(
        tenant_id=tenant,
        id_type="IR_NATIONAL_ID",
        issuing_country_or_authority="IR",
        normalized_identifier="2222222222",
        hmac_key_version=2,
    )

    async def first_insert(c: asyncpg.Connection) -> None:
        fid = uuid4()
        await c.execute(
            """
            INSERT INTO person_identifiers (
              id, tenant_id, person_id, id_type, issuing_country_or_authority,
              id_ciphertext, nonce_96bit, auth_tag_128bit,
              encryption_key_version, aad_version, masked_display,
              verification_status, lookup_hmac_active, hmac_key_version_active,
              lookup_hmac_next, hmac_key_version_next, created_at_utc,
              exp_lookup_hmac_gen2, exp_hmac_key_version_gen2
            ) VALUES (
              $1,$2,$3,'IR_NATIONAL_ID','IR',
              $4,$5,$6,1,1,'****',
              'SYNTACTICALLY_VALID_UNVERIFIED',$7,1,NULL,NULL,NOW(),
              $8,2
            )
            """,
            fid,
            tenant,
            p1,
            b"cipher:race-a",
            b"\x03" * 12,
            b"\x04" * 16,
            synthetic_lookup_hmac(
                tenant_id=tenant,
                id_type="IR_NATIONAL_ID",
                issuing_country_or_authority="IR",
                normalized_identifier="race-a",
                hmac_key_version=1,
            ),
            conflict_hmac,
        )

    async def second_insert(c: asyncpg.Connection) -> None:
        fid = uuid4()
        await c.execute(
            """
            INSERT INTO person_identifiers (
              id, tenant_id, person_id, id_type, issuing_country_or_authority,
              id_ciphertext, nonce_96bit, auth_tag_128bit,
              encryption_key_version, aad_version, masked_display,
              verification_status, lookup_hmac_active, hmac_key_version_active,
              lookup_hmac_next, hmac_key_version_next, created_at_utc,
              exp_lookup_hmac_gen2, exp_hmac_key_version_gen2
            ) VALUES (
              $1,$2,$3,'IR_NATIONAL_ID','IR',
              $4,$5,$6,1,1,'****',
              'SYNTACTICALLY_VALID_UNVERIFIED',$7,1,NULL,NULL,NOW(),
              $8,2
            )
            """,
            fid,
            tenant,
            p2,
            b"cipher:race-b",
            b"\x05" * 12,
            b"\x06" * 16,
            synthetic_lookup_hmac(
                tenant_id=tenant,
                id_type="IR_NATIONAL_ID",
                issuing_country_or_authority="IR",
                normalized_identifier="race-b",
                hmac_key_version=1,
            ),
            conflict_hmac,
        )

    first, second = await two_session_unique_conflict(
        dsn=ep.asyncpg_dsn(),
        first_insert=first_insert,
        second_insert=second_insert,
    )
    assert first == "committed"
    assert second == "unique_violation"


@pytest.mark.asyncio
async def test_p1_resumable_backfill_rollback_and_two_rotation_cycles(
    plane_topology,
) -> None:
    ep = plane_topology.cloud_tenant
    await upgrade_tenant_plane_async(ep.sqlalchemy_async_url(), revision="tp0007")
    conn = await _mig(ep)
    try:
        await apply_p1_expand(conn)
        await init_model(conn, model="P1")
        tenant, person = await seed_tenant_person(conn)
        for i in range(7):
            await insert_identifier(
                conn,
                tenant_id=tenant,
                person_id=person,
                normalized=f"333{i:07d}",
                next_version=None,
            )
        for phase in (1, 2, 3):
            await advance_to(conn, model="P1", phase=phase)
        # Partial backfill (resumable).
        n1, cursor = await p1_backfill_gen2_batch(
            conn, tenant_id=tenant, batch_size=3, after_id=None
        )
        assert n1 == 3 and cursor is not None
        n2, cursor2 = await p1_backfill_gen2_batch(
            conn, tenant_id=tenant, batch_size=10, after_id=cursor
        )
        assert n2 == 4
        remaining = await conn.fetchval(
            """
            SELECT count(*) FROM person_identifiers
            WHERE tenant_id=$1 AND exp_lookup_hmac_gen2 IS NULL
            """,
            tenant,
        )
        assert remaining == 0
        # Idempotent re-run yields zero work.
        n3, _ = await p1_backfill_gen2_batch(conn, tenant_id=tenant, batch_size=50)
        assert n3 == 0

        await advance_to(conn, model="P1", phase=4)
        await advance_to(conn, model="P1", phase=5)
    finally:
        await conn.close()

    await create_unique_index_concurrently_via_alembic(
        ep.sqlalchemy_async_url(), P1_GEN2_INDEX_DDL
    )

    conn = await _mig(ep)
    try:
        for phase in (6, 7, 8):
            await advance_to(conn, model="P1", phase=phase)
        await cutover_generation(conn, model="P1", new_active=2)

        # Rollback window rehearsal: clear gen2 staging values.
        cleared = await p1_rollback_gen2(conn, tenant_id=tenant)
        assert cleared == 7
        await conn.execute(f"DROP INDEX CONCURRENTLY IF EXISTS public.{P1_GEN2_INDEX}")

        # Second rotation cycle targets gen3 (nonredundant vs gen2/next/active).
        for row in await conn.fetch(
            "SELECT id, id_type, issuing_country_or_authority, id_ciphertext "
            "FROM person_identifiers WHERE tenant_id=$1",
            tenant,
        ):
            normalized = bytes(row["id_ciphertext"])[len(b"cipher:") :].decode()
            digest = synthetic_lookup_hmac(
                tenant_id=tenant,
                id_type=row["id_type"],
                issuing_country_or_authority=row["issuing_country_or_authority"],
                normalized_identifier=normalized,
                hmac_key_version=3,
            )
            await conn.execute(
                """
                UPDATE person_identifiers
                SET exp_lookup_hmac_gen3=$2, exp_hmac_key_version_gen3=3
                WHERE id=$1
                """,
                row["id"],
                digest,
            )
        await set_candidate_generation(conn, model="P1", candidate=3)
    finally:
        await conn.close()

    await create_unique_index_concurrently_via_alembic(
        ep.sqlalchemy_async_url(), P1_GEN3_INDEX_DDL
    )
    conn = await _mig(ep)
    try:
        cat = await fetch_index_catalog(conn, [P1_GEN3_INDEX])
        assert len(cat) == 1 and cat[0]["valid"] and cat[0]["ready"]
        assert "exp_lookup_hmac_gen3" in cat[0]["definition"]
        assert await tp0002_indexes_intact(conn)
        # Phase-9 dry-run only — operational retirement not executed.
        await advance_to(conn, model="P1", phase=9)
        state_phase = await conn.fetchval(
            "SELECT phase9_operational_executed FROM m102_exp_rotation_phase_meta WHERE model='P1'"
        )
        assert state_phase is False
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_p1_invalid_index_cleanup_and_retry(plane_topology) -> None:
    ep = plane_topology.cloud_tenant
    await upgrade_tenant_plane_async(ep.sqlalchemy_async_url(), revision="tp0007")
    conn = await _mig(ep)
    try:
        await force_invalid_unique_index(
            conn,
            table="m102_exp_p1_invalid_probe",
            index_name="uq_exp_p1_invalid_probe",
            column="blind_key",
        )
        repaired = await drop_invalid_and_retry(
            conn,
            table="m102_exp_p1_invalid_probe",
            index_name="uq_exp_p1_invalid_probe",
            column="blind_key",
        )
        assert repaired["valid"] is True
        assert repaired["ready"] is True
        assert repaired["unique_index"] is True
    finally:
        await conn.execute("DROP INDEX CONCURRENTLY IF EXISTS public.uq_exp_p1_invalid_probe")
        await conn.execute("DROP TABLE IF EXISTS public.m102_exp_p1_invalid_probe")
        await conn.close()


@pytest.mark.asyncio
async def test_p1_unsafe_upgrade_head_fail_closed(plane_topology) -> None:
    ep = plane_topology.cloud_tenant
    await upgrade_tenant_plane_async(ep.sqlalchemy_async_url(), revision="tp0007")
    conn = await _mig(ep)
    try:
        await init_model(conn, model="P1")
        await advance_to(conn, model="P1", phase=1)
        with pytest.raises(PhaseGateError, match="refusing experimental upgrade head"):
            await experimental_upgrade_head(conn, model="P1", target_phase=6)
    finally:
        await conn.close()

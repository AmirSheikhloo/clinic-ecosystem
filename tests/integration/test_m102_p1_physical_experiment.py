"""P1 staged-column HMAC physical experiment — N01/N04/N06/N07 corrections.

EXPERIMENTAL ONLY — not Package-1, not official TP0008+, not Gate A evidence.
"""

from __future__ import annotations

from urllib.parse import quote_plus
from uuid import uuid4

import asyncpg
import pytest

from experiments.m102_hmac_physical.concurrent_ops import (
    create_and_assert_unique_index,
    force_invalid_unique_index,
    recover_invalid_generation_index,
    two_session_unique_conflict,
)
from experiments.m102_hmac_physical.fixtures import (
    insert_identifier,
    seed_tenant_person,
    tp0002_indexes_intact,
)
from experiments.m102_hmac_physical.lifecycle import (
    advance_phase_chain,
    advance_to_validate_after_backfill,
    advance_to_verify_after_index,
    prepare_cutover_candidate,
    prove_drain_and_backfill,
    prove_index,
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
    cutover_generation,
    experimental_upgrade_head,
    get_state,
    init_model,
    rollback_to_previous_active,
)
from experiments.m102_hmac_physical.rotation import (
    RotationError,
    p1_assert_generation_authority,
    p1_backfill_gen2_batch,
    p1_backfill_gen3_batch,
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


def _admin_tenant_dsn(plane_topology) -> str:
    """Superuser DSN on tenant_app — required to observe other backends' wait events."""
    admin = plane_topology.cloud_admin
    return (
        f"postgresql://{quote_plus(admin.user)}:{quote_plus(admin.password)}"
        f"@{admin.host}:{admin.port}/tenant_app"
    )


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
        for i in range(5):
            fx = await insert_identifier(
                conn, tenant_id=tenant, person_id=person, normalized=f"001{i:07d}"
            )
            await p1_dual_write_gen2(
                conn,
                identifier_id=fx.identifier_id,
                tenant_id=tenant,
                id_type=fx.id_type,
                authority=fx.authority,
                normalized=fx.normalized,
                gen2_version=2,
            )
        assert await tp0002_indexes_intact(conn)
        await advance_to_validate_after_backfill(
            conn, model="P1", tenant_id=tenant, generation=2
        )
    finally:
        await conn.close()

    cleaner = await _mig(ep)
    try:
        await cleaner.execute(f"DROP INDEX CONCURRENTLY IF EXISTS public.{P1_GEN2_INDEX}")
    finally:
        await cleaner.close()

    await create_and_assert_unique_index(
        sqlalchemy_async_url=ep.sqlalchemy_async_url(),
        inspect_dsn=ep.asyncpg_dsn(),
        ddl=P1_GEN2_INDEX_DDL,
        index_name=P1_GEN2_INDEX,
        table_name="person_identifiers",
        required_fragments=["exp_lookup_hmac_gen2", "UNIQUE"],
        forbidden_fragments=["lookup_hmac_next"],
    )

    conn = await _mig(ep)
    try:
        await advance_to_verify_after_index(
            conn,
            model="P1",
            index_name=P1_GEN2_INDEX,
            table_name="person_identifiers",
            generation=2,
        )
        assert await conn.fetchval(
            "SELECT version_num FROM alembic_meta.alembic_version_tp"
        ) == "tp0007"
        assert await tp0002_indexes_intact(conn)
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_p1_deterministic_old_new_writer_conflict_on_gen2(plane_topology) -> None:
    ep = plane_topology.cloud_tenant
    await upgrade_tenant_plane_async(ep.sqlalchemy_async_url(), revision="tp0007")
    conn = await _mig(ep)
    try:
        await apply_p1_expand(conn)
        tenant, p1 = await seed_tenant_person(conn)
        _, p2 = await seed_tenant_person(conn, tenant_id=tenant, person_id=uuid4())
        await insert_identifier(
            conn, tenant_id=tenant, person_id=p1, normalized="1111111111", next_version=None
        )
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

    conflict_hmac = synthetic_lookup_hmac(
        tenant_id=tenant,
        id_type="IR_NATIONAL_ID",
        issuing_country_or_authority="IR",
        normalized_identifier="2222222222",
        hmac_key_version=2,
    )

    async def first_insert(c: asyncpg.Connection) -> None:
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
            uuid4(),
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
            uuid4(),
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

    first, second, observed = await two_session_unique_conflict(
        dsn=ep.asyncpg_dsn(),
        inspector_dsn=_admin_tenant_dsn(plane_topology),
        first_insert=first_insert,
        second_insert=second_insert,
        require_observed_lock_wait=True,
        first_commits=True,
    )
    assert first == "committed"
    assert second == "unique_violation"
    assert observed is True

    # Rollback-loser path uses a fresh collision digest (prior winner remains indexed).
    conflict_hmac_rb = synthetic_lookup_hmac(
        tenant_id=tenant,
        id_type="IR_NATIONAL_ID",
        issuing_country_or_authority="IR",
        normalized_identifier="2222222299",
        hmac_key_version=2,
    )

    async def first_insert_rb(c: asyncpg.Connection) -> None:
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
            uuid4(),
            tenant,
            p1,
            b"cipher:race-a-rb",
            b"\x13" * 12,
            b"\x14" * 16,
            synthetic_lookup_hmac(
                tenant_id=tenant,
                id_type="IR_NATIONAL_ID",
                issuing_country_or_authority="IR",
                normalized_identifier="race-a-rb",
                hmac_key_version=1,
            ),
            conflict_hmac_rb,
        )

    async def second_insert_rb(c: asyncpg.Connection) -> None:
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
            uuid4(),
            tenant,
            p2,
            b"cipher:race-b-rb",
            b"\x15" * 12,
            b"\x16" * 16,
            synthetic_lookup_hmac(
                tenant_id=tenant,
                id_type="IR_NATIONAL_ID",
                issuing_country_or_authority="IR",
                normalized_identifier="race-b-rb",
                hmac_key_version=1,
            ),
            conflict_hmac_rb,
        )

    first_rb, second_rb, observed_rb = await two_session_unique_conflict(
        dsn=ep.asyncpg_dsn(),
        inspector_dsn=_admin_tenant_dsn(plane_topology),
        first_insert=first_insert_rb,
        second_insert=second_insert_rb,
        require_observed_lock_wait=True,
        first_commits=False,
    )
    assert first_rb == "rolled_back"
    assert second_rb == "inserted"
    assert observed_rb is True


@pytest.mark.asyncio
async def test_p1_atomic_dual_write_rejects_active_hmac_mismatch(plane_topology) -> None:
    ep = plane_topology.cloud_tenant
    await upgrade_tenant_plane_async(ep.sqlalchemy_async_url(), revision="tp0007")
    conn = await _mig(ep)
    try:
        await apply_p1_expand(conn)
        tenant, person = await seed_tenant_person(conn)
        fx = await insert_identifier(
            conn, tenant_id=tenant, person_id=person, normalized="1212121212", next_version=None
        )
        with pytest.raises(RotationError, match="active HMAC does not match"):
            await p1_dual_write_gen2(
                conn,
                identifier_id=fx.identifier_id,
                tenant_id=tenant,
                id_type=fx.id_type,
                authority=fx.authority,
                normalized="9999999999",  # wrong canonical vs stored active
                gen2_version=2,
            )
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_p1_two_complete_rotations_preserve_active_authority(plane_topology) -> None:
    ep = plane_topology.cloud_tenant
    await upgrade_tenant_plane_async(ep.sqlalchemy_async_url(), revision="tp0007")
    conn = await _mig(ep)
    try:
        await apply_p1_expand(conn)
        await init_model(conn, model="P1")
        tenant, person = await seed_tenant_person(conn)
        for i in range(6):
            await insert_identifier(
                conn,
                tenant_id=tenant,
                person_id=person,
                normalized=f"333{i:07d}",
                next_version=None,
            )
        await advance_phase_chain(conn, model="P1", to_phase=3)
        n1, cursor = await p1_backfill_gen2_batch(
            conn, tenant_id=tenant, batch_size=2, after_id=None
        )
        assert n1 == 2 and cursor is not None
        n2, _ = await p1_backfill_gen2_batch(
            conn, tenant_id=tenant, batch_size=10, after_id=cursor
        )
        assert n2 == 4
        assert (
            await conn.fetchval(
                """
                SELECT count(*) FROM person_identifiers
                WHERE tenant_id=$1 AND exp_lookup_hmac_gen2 IS NULL
                """,
                tenant,
            )
            == 0
        )
        await prove_drain_and_backfill(
            conn, model="P1", tenant_id=tenant, generation=2
        )
        await advance_phase_chain(conn, model="P1", to_phase=5)
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
        await advance_to_verify_after_index(
            conn,
            model="P1",
            index_name=P1_GEN2_INDEX,
            table_name="person_identifiers",
            generation=2,
        )
        await prepare_cutover_candidate(conn, model="P1", candidate=2)
        await advance_phase_chain(conn, model="P1", to_phase=8)
        await cutover_generation(conn, model="P1", new_active=2)
        await p1_assert_generation_authority(
            conn, model="P1", generation=2, index_name=P1_GEN2_INDEX
        )

        # Unsafe wipe while gen2 is active must fail closed.
        with pytest.raises(RotationError, match="refusing to clear gen2"):
            await p1_rollback_gen2(conn, tenant_id=tenant)
        with pytest.raises(RotationError, match="refusing DROP INDEX"):
            await p1_drop_generation_index_if_safe(
                conn, model="P1", generation=2, index_name=P1_GEN2_INDEX
            )

        # Authority-preserving rollback to old generation keeps gen2 index.
        await rollback_to_previous_active(conn, model="P1", previous_active=1)
        assert (await get_state(conn, "P1")).active_generation == 1
        await p1_assert_generation_authority(
            conn, model="P1", generation=1, index_name="uq_person_identifier_active_lookup"
        )
        assert await conn.fetchval(
            "SELECT to_regclass($1)::text", f"public.{P1_GEN2_INDEX}"
        )

        # Recutover to gen2 requires re-proving backfill/index after prior cutover reset.
        await prove_drain_and_backfill(
            conn, model="P1", tenant_id=tenant, generation=2
        )
        await prove_index(
            conn,
            model="P1",
            index_name=P1_GEN2_INDEX,
            table_name="person_identifiers",
            generation=2,
        )
        await prepare_cutover_candidate(conn, model="P1", candidate=2)
        await cutover_generation(conn, model="P1", new_active=2)
        await p1_assert_generation_authority(
            conn, model="P1", generation=2, index_name=P1_GEN2_INDEX
        )

        # Second rotation: gen3 backfill + index + cutover while gen2 remains.
        n3, _ = await p1_backfill_gen3_batch(conn, tenant_id=tenant, batch_size=50)
        assert n3 == 6
        await conn.execute(f"DROP INDEX CONCURRENTLY IF EXISTS public.{P1_GEN3_INDEX}")
    finally:
        await conn.close()

    await create_and_assert_unique_index(
        sqlalchemy_async_url=ep.sqlalchemy_async_url(),
        inspect_dsn=ep.asyncpg_dsn(),
        ddl=P1_GEN3_INDEX_DDL,
        index_name=P1_GEN3_INDEX,
        table_name="person_identifiers",
        required_fragments=["exp_lookup_hmac_gen3"],
        forbidden_fragments=["lookup_hmac_next", "exp_lookup_hmac_gen2"],
    )

    conn = await _mig(ep)
    try:
        # Prove gen3 backfill+index then cutover under existing phase 8.
        await prove_drain_and_backfill(
            conn, model="P1", tenant_id=tenant, generation=3
        )
        await prove_index(
            conn,
            model="P1",
            index_name=P1_GEN3_INDEX,
            table_name="person_identifiers",
            generation=3,
        )
        await prepare_cutover_candidate(conn, model="P1", candidate=3)
        await cutover_generation(conn, model="P1", new_active=3)
        await p1_assert_generation_authority(
            conn, model="P1", generation=3, index_name=P1_GEN3_INDEX
        )
        # gen2 index still present until explicit safe retirement after new authority.
        assert await conn.fetchval(
            "SELECT to_regclass($1)::text", f"public.{P1_GEN2_INDEX}"
        )
        await advance_phase_chain(conn, model="P1", to_phase=9)
        assert (await get_state(conn, "P1")).phase9_operational_executed is False
        # Only now may gen2 be dropped — it is no longer active.
        await p1_drop_generation_index_if_safe(
            conn, model="P1", generation=2, index_name=P1_GEN2_INDEX
        )
        assert await tp0002_indexes_intact(conn)
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_p1_invalid_generation_index_recovery_on_real_target(plane_topology) -> None:
    ep = plane_topology.cloud_tenant
    await upgrade_tenant_plane_async(ep.sqlalchemy_async_url(), revision="tp0007")
    conn = await _mig(ep)
    try:
        await apply_p1_expand(conn)
        tenant, p1 = await seed_tenant_person(conn)
        _, p2 = await seed_tenant_person(conn, tenant_id=tenant, person_id=uuid4())
        a = await insert_identifier(
            conn, tenant_id=tenant, person_id=p1, normalized="9000000001", next_version=None
        )
        b = await insert_identifier(
            conn, tenant_id=tenant, person_id=p2, normalized="9000000002", next_version=None
        )
        collision = b"\xcd" * 32
        for ident in (a.identifier_id, b.identifier_id):
            await conn.execute(
                """
                UPDATE person_identifiers
                SET exp_lookup_hmac_gen2=$2, exp_hmac_key_version_gen2=2
                WHERE id=$1
                """,
                ident,
                collision,
            )
        await conn.execute(f"DROP INDEX CONCURRENTLY IF EXISTS public.{P1_GEN2_INDEX}")
        try:
            await conn.execute(P1_GEN2_INDEX_DDL)
        except (asyncpg.UniqueViolationError, asyncpg.PostgresError):
            pass
        invalid = await conn.fetchval(
            """
            SELECT i.indisvalid FROM pg_index i
            JOIN pg_class c ON c.oid=i.indexrelid WHERE c.relname=$1
            """,
            P1_GEN2_INDEX,
        )
        assert invalid is False

        async def resolve(c: asyncpg.Connection) -> None:
            # Keep one colliding row's gen2 value; clear the other.
            await c.execute(
                """
                UPDATE person_identifiers
                SET exp_lookup_hmac_gen2=NULL, exp_hmac_key_version_gen2=NULL
                WHERE id=$1
                """,
                b.identifier_id,
            )

        await recover_invalid_generation_index(
            conn,
            index_name=P1_GEN2_INDEX,
            rebuild_ddl=P1_GEN2_INDEX_DDL,
            resolve_duplicates=resolve,
        )
        assert await conn.fetchval(
            """
            SELECT i.indisvalid AND i.indisready FROM pg_index i
            JOIN pg_class c ON c.oid=i.indexrelid WHERE c.relname=$1
            """,
            P1_GEN2_INDEX,
        )
    finally:
        await conn.execute(f"DROP INDEX CONCURRENTLY IF EXISTS public.{P1_GEN2_INDEX}")
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
        from experiments.m102_hmac_physical.concurrent_ops import drop_invalid_and_retry

        repaired = await drop_invalid_and_retry(
            conn,
            table="m102_exp_p1_invalid_probe",
            index_name="uq_exp_p1_invalid_probe",
            column="blind_key",
        )
        assert repaired["valid"] is True
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
        await advance_phase_chain(conn, model="P1", to_phase=1)
        with pytest.raises(PhaseGateError, match="refusing experimental upgrade head"):
            await experimental_upgrade_head(conn, model="P1", target_phase=6)
    finally:
        await conn.close()

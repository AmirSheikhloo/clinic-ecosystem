"""Disposable PG15 test-only proof of existing TP0002 next-index uniqueness.
Synthetic byte strings are not AES/HMAC computations or Phase-6 cutover proof.
"""
import asyncio
from datetime import datetime, timezone
from uuid import uuid4
import asyncpg
import pytest
from tests.integration.alembic_runner import upgrade_tenant_plane_async

pytestmark = pytest.mark.integration

@pytest.mark.asyncio
@pytest.mark.parametrize("plane", ["cloud_tenant", "local_hub"])
async def test_existing_tp0002_next_index_rejects_concurrent_synthetic_duplicate(
    plane_topology, plane
):
    ep = getattr(plane_topology, plane)
    await upgrade_tenant_plane_async(ep.sqlalchemy_async_url(), revision="tp0007")
    tenant = uuid4()
    people = [uuid4(), uuid4()]
    now = datetime.now(timezone.utc)
    seed = await asyncpg.connect(ep.asyncpg_dsn())
    try:
        await seed.execute("SET ROLE db_migrator")
        await seed.execute(
            """INSERT INTO tenant_registry
            (tenant_id,tenant_status,timezone_name,created_at_utc,updated_at_utc)
            VALUES($1,'ACTIVE','UTC',$2,$2)""", tenant, now
        )
        for p in people:
            await seed.execute(
                """INSERT INTO tenant_persons
                (id,tenant_id,first_name,last_name,aggregate_version,
                 created_at_utc,updated_at_utc)
                VALUES($1,$2,'Synthetic','Patient',1,$3,$3)""",
                p,tenant,now
            )
    finally:
        await seed.close()

    async def attempt(i):
        conn = await asyncpg.connect(ep.asyncpg_dsn())
        try:
            await conn.execute("SET ROLE db_migrator")
            try:
                await conn.execute(
                    """INSERT INTO person_identifiers
                    (id,tenant_id,person_id,id_type,issuing_country_or_authority,
                     id_ciphertext,nonce_96bit,auth_tag_128bit,
                     encryption_key_version,aad_version,masked_display,
                     verification_status,lookup_hmac_active,hmac_key_version_active,
                     lookup_hmac_next,hmac_key_version_next,created_at_utc)
                    VALUES($1,$2,$3,'IR_NATIONAL_ID','IR',
                           $4,$5,$6,1,1,'masked-test',
                           'SYNTACTICALLY_VALID_UNVERIFIED',$7,1,$8,2,$9)""",
                    uuid4(),tenant,people[i],b"synthetic-ciphertext",
                    bytes([i+1])*12,bytes([i+1])*16,
                    bytes([i+10])*32,bytes([42])*32,now
                )
            except asyncpg.UniqueViolationError:
                return "unique_violation"
            return "inserted"
        finally:
            await conn.close()

    outcomes = await asyncio.gather(attempt(0), attempt(1))
    assert sorted(outcomes) == ["inserted", "unique_violation"], outcomes
    probe = await asyncpg.connect(ep.asyncpg_dsn())
    try:
        await probe.execute("SET ROLE db_migrator")
        assert await probe.fetchval(
            "SELECT count(*) FROM person_identifiers WHERE tenant_id=$1",
            tenant
        ) == 1
        assert await probe.fetchval(
            """SELECT i.indisvalid AND i.indisready AND i.indisunique
            FROM pg_index i JOIN pg_class c ON c.oid=i.indexrelid
            WHERE c.relname='uq_person_identifier_next_lookup'"""
        ) is True
    finally:
        await probe.close()

"""Actual PostgreSQL 15 SQLSTATE 25P02 cleanup ordering, both migration planes.

This verifies the real SQLAlchemy+asyncpg same-connection sequence.
It is NOT evidence of Alembic autocommit_block/TP0011 or Gate A completion.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine
from tests.integration.docker_probe import DOCKER_AVAILABLE, SKIP_REASON

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not DOCKER_AVAILABLE, reason=SKIP_REASON),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "endpoint_name,role_name",
    [
        ("cloud_tenant", "db_migrator"),
        ("cloud_control", "cp_db_migrator"),
    ],
)
async def test_real_pg15_aborted_transaction_requires_rollback_before_reset_role(
    plane_topology, endpoint_name, role_name,
):
    endpoint = getattr(plane_topology, endpoint_name)
    engine = create_async_engine(endpoint.sqlalchemy_async_url())
    try:
        async with engine.connect() as conn:
            await conn.execute(text(f'SET ROLE "{role_name}"'))
            assert await conn.scalar(text("SELECT current_user")) == role_name
            with pytest.raises(DBAPIError):
                await conn.execute(text("SELECT 1/0"))
            # PostgreSQL 25P02: RESET ROLE is forbidden while txn is aborted.
            with pytest.raises(DBAPIError) as still_aborted:
                await conn.execute(text("RESET ROLE"))
            assert "25P02" in str(still_aborted.value) or "aborted" in str(still_aborted.value).lower()
            await conn.rollback()
            await conn.execute(text("RESET ROLE"))
            await conn.commit()
            user = await conn.scalar(text("SELECT current_user"))
            session_user = await conn.scalar(text("SELECT session_user"))
            assert user == session_user == endpoint.user
    finally:
        await engine.dispose()

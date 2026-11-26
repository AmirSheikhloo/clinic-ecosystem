"""Atomic group scheduling: all-or-nothing UoW, per-line overlap, group idempotency."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import asyncpg
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from clinic_ecosystem.application.scheduling.commands import (
    ScheduleAppointmentCommand,
    ScheduleAppointmentGroupCommand,
    ScheduleGroupLine,
)
from clinic_ecosystem.application.scheduling.exceptions import (
    GroupManualOverlapAcknowledgementRequired,
)
from clinic_ecosystem.domain.scheduling.model import BookingChannel, CapacityPool
from clinic_ecosystem.infrastructure.persistence.compose import build_handler_for_session
from clinic_ecosystem.shared_kernel.uuid7 import new_uuid7
from tests.integration.alembic_runner import upgrade_tenant_plane_async
from tests.integration.docker_probe import DOCKER_AVAILABLE, SKIP_REASON
from tests.integration.m1_seed import seed_scheduling_graph
from tests.integration.test_m1_schedule_appointment import _app_dsn, _app_url

pytestmark = pytest.mark.integration


async def _seed(plane_topology, **kwargs):
    await upgrade_tenant_plane_async(plane_topology.cloud_tenant.sqlalchemy_async_url())
    seed_conn = await asyncpg.connect(plane_topology.cloud_tenant.asyncpg_dsn())
    try:
        await seed_conn.execute("SET ROLE db_migrator")
        ids = await seed_scheduling_graph(seed_conn, **kwargs)
        await seed_conn.execute("RESET ROLE")
        return ids
    finally:
        await seed_conn.close()


def _group_cmd(ids, *, key: str, fingerprint: str, lines: list[ScheduleGroupLine]):
    return ScheduleAppointmentGroupCommand(
        correlation_id=new_uuid7(),
        idempotency_key=key,
        request_fingerprint=fingerprint,
        principal_id=ids.user_account_id,
        actor_type="USER",
        tenant_id=ids.tenant_id,
        beneficiary_patient_id=ids.patient_id,
        booker_person_id=ids.person_id,
        lines=tuple(lines),
    )


def _lines(ids, start: datetime, *, ack: bool = False, ack_ids=()):
    return [
        ScheduleGroupLine(
            client_line_id=f"line-{idx}",
            service_id=ids.service_id,
            resource_ids=(ids.resource_id,),
            start_at_utc=start + timedelta(hours=idx),
            end_at_utc=start + timedelta(hours=idx, minutes=30),
            acknowledge_overlap=ack if idx == 0 else False,
            acknowledged_conflict_ids=tuple(ack_ids) if idx == 0 else (),
        )
        for idx in range(3)
    ]


@pytest.mark.asyncio
async def test_group_atomic_success_of_three_lines(plane_topology) -> None:
    if not DOCKER_AVAILABLE:
        pytest.skip(SKIP_REASON)
    ids = await _seed(plane_topology, grant_manual_overbooking=True)
    engine = create_async_engine(_app_url(plane_topology), pool_size=2)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    start = datetime.now(timezone.utc) + timedelta(hours=8)

    async with session_factory() as session:
        result = await build_handler_for_session(session).handle_group(
            _group_cmd(
                ids,
                key="group-ok-1",
                fingerprint="fp-group-ok-1",
                lines=_lines(ids, start),
            )
        )
    assert result.replayed is False
    assert len(result.lines) == 3
    assert {line.client_line_id for line in result.lines} == {
        "line-0",
        "line-1",
        "line-2",
    }

    conn = await asyncpg.connect(_app_dsn(plane_topology))
    try:
        await conn.execute(
            "SELECT set_config('app.current_tenant_id', $1, false)", str(ids.tenant_id)
        )
        count = await conn.fetchval(
            "SELECT count(*) FROM appointments WHERE tenant_id = $1 AND beneficiary_patient_id = $2",
            ids.tenant_id,
            ids.patient_id,
        )
        assert count == 3
    finally:
        await conn.close()
    await engine.dispose()


@pytest.mark.asyncio
async def test_group_overlap_rolls_back_and_returns_per_line_conflicts(
    plane_topology,
) -> None:
    if not DOCKER_AVAILABLE:
        pytest.skip(SKIP_REASON)
    ids = await _seed(plane_topology, grant_manual_overbooking=True)
    engine = create_async_engine(_app_url(plane_topology), pool_size=2)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    start = datetime.now(timezone.utc) + timedelta(hours=10)
    end = start + timedelta(minutes=30)

    # Existing MANUAL booking that line-0 will overlap.
    async with session_factory() as session:
        existing = await build_handler_for_session(session).handle(
            ScheduleAppointmentCommand(
                correlation_id=new_uuid7(),
                idempotency_key="seed-overlap",
                request_fingerprint="fp-seed-overlap",
                principal_id=ids.user_account_id,
                actor_type="USER",
                tenant_id=ids.tenant_id,
                beneficiary_patient_id=ids.patient_id,
                booker_person_id=ids.person_id,
                patient_booking_note=None,
                service_id=ids.service_id,
                booking_channel=BookingChannel.MANUAL_STAFF,
                capacity_pool=CapacityPool.MANUAL,
                resource_ids=(ids.resource_id,),
                start_at_utc=start,
                end_at_utc=end,
                hold_expires_at_utc=None,
                acknowledge_overlap=False,
            )
        )

    with pytest.raises(GroupManualOverlapAcknowledgementRequired) as excinfo:
        async with session_factory() as session:
            await build_handler_for_session(session).handle_group(
                _group_cmd(
                    ids,
                    key="group-overlap-1",
                    fingerprint="fp-group-overlap-1",
                    lines=_lines(ids, start),
                )
            )
    assert "line-0" in excinfo.value.conflicts_by_line
    assert (
        excinfo.value.conflicts_by_line["line-0"][0].appointment_id
        == existing.appointment_id
    )

    conn = await asyncpg.connect(_app_dsn(plane_topology))
    try:
        await conn.execute(
            "SELECT set_config('app.current_tenant_id', $1, false)", str(ids.tenant_id)
        )
        count = await conn.fetchval(
            "SELECT count(*) FROM appointments WHERE tenant_id = $1",
            ids.tenant_id,
        )
        # Only the seed appointment — group rolled back entirely.
        assert count == 1
    finally:
        await conn.close()
    await engine.dispose()


@pytest.mark.asyncio
async def test_group_idempotent_replay(plane_topology) -> None:
    if not DOCKER_AVAILABLE:
        pytest.skip(SKIP_REASON)
    ids = await _seed(plane_topology, grant_manual_overbooking=True)
    engine = create_async_engine(_app_url(plane_topology), pool_size=2)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    start = datetime.now(timezone.utc) + timedelta(hours=14)
    command = _group_cmd(
        ids,
        key="group-idem-1",
        fingerprint="fp-group-idem-1",
        lines=_lines(ids, start),
    )

    async with session_factory() as session:
        first = await build_handler_for_session(session).handle_group(command)
    async with session_factory() as session:
        replay = await build_handler_for_session(session).handle_group(command)

    assert first.replayed is False
    assert replay.replayed is True
    assert [line.appointment_id for line in replay.lines] == [
        line.appointment_id for line in first.lines
    ]

    conn = await asyncpg.connect(_app_dsn(plane_topology))
    try:
        await conn.execute(
            "SELECT set_config('app.current_tenant_id', $1, false)", str(ids.tenant_id)
        )
        count = await conn.fetchval(
            "SELECT count(*) FROM appointments WHERE tenant_id = $1",
            ids.tenant_id,
        )
        assert count == 3
    finally:
        await conn.close()
    await engine.dispose()

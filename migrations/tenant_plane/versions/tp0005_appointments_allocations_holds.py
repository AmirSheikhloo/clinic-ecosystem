"""TP0005 — Appointment and multi-resource allocation (Appendix F.4 + F.5).

Verbatim F.4 appointments / appointment_resource_allocations and F.5
hold_expiry_work_items from docs/FINAL_MASTER_SPECIFICATION_v3.0.1_FINAL.txt.
ONLINE-only partial GiST EXCLUDE; MANUAL outside predicate. No UUID defaults.
No RLS (TP0007).

Revision ID: tp0005
Revises: tp0004
Create Date: 2026-11-10
"""

from typing import Sequence, Union

from alembic import op

revision: str = "tp0005"
down_revision: Union[str, None] = "tp0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_STATEMENTS = [
"""CREATE TABLE appointments (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
    beneficiary_patient_id UUID NOT NULL,
    booker_person_id UUID NULL,
    patient_booking_note TEXT NULL,
    service_id UUID NOT NULL,
    status VARCHAR(32) NOT NULL,
    booking_channel VARCHAR(32) NOT NULL
        CHECK (booking_channel IN ('ONLINE_WEB', 'ONLINE_BOT', 'MANUAL_STAFF')),
    capacity_pool VARCHAR(16) NOT NULL
        CHECK (capacity_pool IN ('ONLINE', 'MANUAL')),
    scheduled_start_at_utc TIMESTAMPTZ NOT NULL,
    scheduled_end_at_utc TIMESTAMPTZ NOT NULL,
    hold_expires_at_utc TIMESTAMPTZ NULL,
    aggregate_version BIGINT NOT NULL CHECK (aggregate_version > 0),
    created_at_utc TIMESTAMPTZ NOT NULL,
    updated_at_utc TIMESTAMPTZ NOT NULL,
    CONSTRAINT ck_appointment_valid_time
        CHECK (scheduled_start_at_utc < scheduled_end_at_utc),
    CONSTRAINT ck_appointment_patient_booking_note_length
        CHECK (patient_booking_note IS NULL OR char_length(patient_booking_note) <= 2000),
    CONSTRAINT ck_appointment_channel_pool CHECK (
        (booking_channel IN ('ONLINE_WEB', 'ONLINE_BOT') AND capacity_pool = 'ONLINE')
        OR (booking_channel = 'MANUAL_STAFF' AND capacity_pool = 'MANUAL')
    ),
    CONSTRAINT fk_appointment_beneficiary_patient_tenant
        FOREIGN KEY (tenant_id, beneficiary_patient_id)
        REFERENCES patient_profiles (tenant_id, id) MATCH FULL,
    CONSTRAINT fk_appointment_booker_person_tenant
        FOREIGN KEY (tenant_id, booker_person_id)
        REFERENCES tenant_persons (tenant_id, id) MATCH SIMPLE,
    CONSTRAINT fk_appointment_service_tenant
        FOREIGN KEY (tenant_id, service_id)
        REFERENCES services (tenant_id, id) MATCH FULL,
    CONSTRAINT uq_appointment_tenant_id UNIQUE (tenant_id, id)
)""",
"""CREATE TABLE appointment_resource_allocations (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
    appointment_id UUID NOT NULL,
    resource_id UUID NOT NULL,
    booking_channel VARCHAR(32) NOT NULL,
    capacity_pool VARCHAR(16) NOT NULL,
    allocation_status VARCHAR(32) NOT NULL,
    time_slot TSTZRANGE NOT NULL,
    created_at_utc TIMESTAMPTZ NOT NULL,
    CONSTRAINT fk_allocation_appointment_tenant
        FOREIGN KEY (tenant_id, appointment_id)
        REFERENCES appointments (tenant_id, id) MATCH FULL,
    CONSTRAINT fk_allocation_resource_tenant
        FOREIGN KEY (tenant_id, resource_id)
        REFERENCES bookable_resources (tenant_id, id) MATCH FULL,
    CONSTRAINT ck_allocation_bounded_half_open CHECK (
        NOT isempty(time_slot)
        AND NOT lower_inf(time_slot)
        AND NOT upper_inf(time_slot)
        AND lower_inc(time_slot)
        AND NOT upper_inc(time_slot)
        AND lower(time_slot) < upper(time_slot)
    ),
    CONSTRAINT ck_allocation_channel_pool CHECK (
        (booking_channel IN ('ONLINE_WEB', 'ONLINE_BOT') AND capacity_pool = 'ONLINE')
        OR (booking_channel = 'MANUAL_STAFF' AND capacity_pool = 'MANUAL')
    ),
    CONSTRAINT uq_allocation_one_resource_per_appointment
        UNIQUE (tenant_id, appointment_id, resource_id),
    CONSTRAINT uq_allocation_tenant_id UNIQUE (tenant_id, id),
    CONSTRAINT ex_online_resource_time
        EXCLUDE USING gist (
            tenant_id WITH =,
            resource_id WITH =,
            time_slot WITH &&
        ) WHERE (
            capacity_pool = 'ONLINE'
            AND allocation_status IN ('PENDING_PAYMENT_HOLD', 'CONFIRMED', 'CHECKED_IN')
        )
)""",
"""CREATE TABLE hold_expiry_work_items (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
    appointment_id UUID NOT NULL,
    due_at_utc TIMESTAMPTZ NOT NULL,
    work_state VARCHAR(24) NOT NULL
        CHECK (work_state IN ('PENDING', 'CLAIMED', 'DONE', 'RETRYABLE', 'NOOP')),
    claim_token UUID NULL,
    claimed_by TEXT NULL,
    lease_expires_at_utc TIMESTAMPTZ NULL,
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    created_at_utc TIMESTAMPTZ NOT NULL,
    updated_at_utc TIMESTAMPTZ NOT NULL,
    CONSTRAINT fk_hold_work_appointment_tenant
        FOREIGN KEY (tenant_id, appointment_id)
        REFERENCES appointments (tenant_id, id) MATCH FULL,
    CONSTRAINT uq_hold_work_appointment UNIQUE (tenant_id, appointment_id)
)""",
"""CREATE INDEX ix_hold_expiry_due_work
ON hold_expiry_work_items (due_at_utc, id)
WHERE work_state IN ('PENDING', 'RETRYABLE')""",
]


def upgrade() -> None:
    for stmt in _STATEMENTS:
        op.execute(stmt)


def downgrade() -> None:
    raise NotImplementedError(
        "TP0005 downgrade is intentionally irreversible under Appendix E.4."
    )

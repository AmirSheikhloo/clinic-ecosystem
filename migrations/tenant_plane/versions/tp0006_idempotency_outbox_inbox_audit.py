"""TP0006 — Idempotency, Outbox, Inbox, sync counters and audit.

Minimum persistence for clauses 161–184 / 213–231 and MANUAL overbooking audit
(clause 779). No UUID-generating defaults. No RLS (TP0007).

Revision ID: tp0006
Revises: tp0005
Create Date: 2026-11-10
"""

from typing import Sequence, Union

from alembic import op

revision: str = "tp0006"
down_revision: Union[str, None] = "tp0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_STATEMENTS = [
"""CREATE TABLE idempotency_records (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
    principal_id UUID NOT NULL,
    operation_scope VARCHAR(128) NOT NULL,
    idempotency_key VARCHAR(256) NOT NULL,
    request_fingerprint TEXT NOT NULL,
    state VARCHAR(32) NOT NULL
        CHECK (state IN ('IN_PROGRESS', 'COMPLETED', 'FAILED')),
    response_payload JSONB NULL,
    owner_token UUID NULL,
    created_at_utc TIMESTAMPTZ NOT NULL,
    updated_at_utc TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_idempotency_identity
        UNIQUE (tenant_id, principal_id, operation_scope, idempotency_key),
    CONSTRAINT uq_idempotency_tenant_id UNIQUE (tenant_id, id)
)""",
"""CREATE TABLE outbox_messages (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
    message_type VARCHAR(128) NOT NULL,
    payload_json JSONB NOT NULL,
    created_at_utc TIMESTAMPTZ NOT NULL,
    locked_until TIMESTAMPTZ NULL,
    lease_id UUID NULL,
    delivered_at_utc TIMESTAMPTZ NULL,
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    CONSTRAINT uq_outbox_tenant_id UNIQUE (tenant_id, id)
)""",
"""CREATE TABLE inbox_messages (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
    message_id UUID NOT NULL,
    processing_state VARCHAR(32) NOT NULL
        CHECK (processing_state IN ('RECEIVED', 'COMPLETED', 'POISON')),
    created_at_utc TIMESTAMPTZ NOT NULL,
    updated_at_utc TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_inbox_message UNIQUE (tenant_id, message_id),
    CONSTRAINT uq_inbox_tenant_id UNIQUE (tenant_id, id)
)""",
"""CREATE TABLE sync_stream_counters (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
    stream_name VARCHAR(128) NOT NULL,
    last_sequence BIGINT NOT NULL DEFAULT 0 CHECK (last_sequence >= 0),
    updated_at_utc TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_sync_stream UNIQUE (tenant_id, stream_name),
    CONSTRAINT uq_sync_stream_tenant_id UNIQUE (tenant_id, id)
)""",
"""CREATE TABLE audit_entries (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
    actor_type VARCHAR(32) NOT NULL,
    actor_id UUID NULL,
    operation VARCHAR(128) NOT NULL,
    target_type VARCHAR(128) NOT NULL,
    target_id UUID NULL,
    details_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at_utc TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_audit_tenant_id UNIQUE (tenant_id, id)
)""",
]


def upgrade() -> None:
    for stmt in _STATEMENTS:
        op.execute(stmt)


def downgrade() -> None:
    raise NotImplementedError(
        "TP0006 downgrade is intentionally irreversible under Appendix E.4."
    )

"""TP0004 — Catalog, resources and service requirements (Appendix F.3).

Verbatim F.3 from docs/FINAL_MASTER_SPECIFICATION_v3.0.1_FINAL.txt.
No UUID-generating defaults. No RLS (TP0007).

Revision ID: tp0004
Revises: tp0003
Create Date: 2026-11-10
"""

from typing import Sequence, Union

from alembic import op

revision: str = "tp0004"
down_revision: Union[str, None] = "tp0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_STATEMENTS = [
"""CREATE TABLE services (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
    service_code VARCHAR(64) NULL,
    service_name TEXT NOT NULL,
    default_duration_minutes INTEGER NOT NULL CHECK (default_duration_minutes > 0),
    default_price_irr BIGINT NOT NULL CHECK (default_price_irr >= 0),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    aggregate_version BIGINT NOT NULL CHECK (aggregate_version > 0),
    created_at_utc TIMESTAMPTZ NOT NULL,
    updated_at_utc TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_service_tenant_id UNIQUE (tenant_id, id)
)""",
"""CREATE TABLE bookable_resources (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
    resource_type VARCHAR(40) NOT NULL
        CHECK (resource_type IN ('PRACTITIONER', 'ROOM', 'DEVICE', 'DEFAULT_ONLINE_SLOT_STREAM')),
    resource_name TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at_utc TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_bookable_resource_tenant_id UNIQUE (tenant_id, id)
)""",
"""CREATE TABLE service_resource_requirements (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
    service_id UUID NOT NULL,
    requirement_group VARCHAR(64) NOT NULL,
    required_resource_type VARCHAR(40) NOT NULL,
    specific_resource_id UUID NULL,
    quantity_required INTEGER NOT NULL CHECK (quantity_required > 0),
    created_at_utc TIMESTAMPTZ NOT NULL,
    CONSTRAINT fk_requirement_service_tenant
        FOREIGN KEY (tenant_id, service_id)
        REFERENCES services (tenant_id, id) MATCH FULL,
    CONSTRAINT fk_requirement_specific_resource_tenant
        FOREIGN KEY (tenant_id, specific_resource_id)
        REFERENCES bookable_resources (tenant_id, id) MATCH SIMPLE,
    CONSTRAINT uq_service_requirement_tenant_id UNIQUE (tenant_id, id)
)""",
]


def upgrade() -> None:
    for stmt in _STATEMENTS:
        op.execute(stmt)


def downgrade() -> None:
    raise NotImplementedError(
        "TP0004 downgrade is intentionally irreversible under Appendix E.4."
    )

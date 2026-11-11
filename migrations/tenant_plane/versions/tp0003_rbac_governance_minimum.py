"""TP0003 — Minimum RBAC and governance tables for ScheduleAppointment.

Derived from clauses 78–88 / 199 / 779 (ALLOW_MANUAL_OVERBOOKING) and Section 51
tenant FK/UNIQUE rules. No verbatim Appendix F SQL exists for RBAC; this revision
creates the minimum server-side permission tables required for MANUAL overbooking
authorization in M1-01. No UUID defaults. No RLS (TP0007).

Revision ID: tp0003
Revises: tp0002
Create Date: 2026-11-10
"""

from typing import Sequence, Union

from alembic import op

revision: str = "tp0003"
down_revision: Union[str, None] = "tp0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_STATEMENTS = [
"""CREATE TABLE permission_catalog_snapshots (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
    catalog_version BIGINT NOT NULL CHECK (catalog_version > 0),
    permissions_json JSONB NOT NULL,
    created_at_utc TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_permission_catalog_tenant_version UNIQUE (tenant_id, catalog_version),
    CONSTRAINT uq_permission_catalog_tenant_id UNIQUE (tenant_id, id)
)""",
"""CREATE TABLE tenant_roles (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
    role_code VARCHAR(64) NOT NULL,
    role_name TEXT NOT NULL,
    is_system_defined BOOLEAN NOT NULL DEFAULT FALSE,
    created_at_utc TIMESTAMPTZ NOT NULL,
    CONSTRAINT ck_tenant_role_code_not_super_admin
        CHECK (role_code <> 'SUPER_ADMIN'),
    CONSTRAINT uq_tenant_role_code UNIQUE (tenant_id, role_code),
    CONSTRAINT uq_tenant_role_tenant_id UNIQUE (tenant_id, id)
)""",
"""CREATE TABLE role_permission_assignments (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
    role_id UUID NOT NULL,
    permission_code VARCHAR(128) NOT NULL,
    granted_at_utc TIMESTAMPTZ NOT NULL,
    CONSTRAINT fk_rpa_role_tenant
        FOREIGN KEY (tenant_id, role_id)
        REFERENCES tenant_roles (tenant_id, id) MATCH FULL,
    CONSTRAINT uq_rpa_role_permission UNIQUE (tenant_id, role_id, permission_code),
    CONSTRAINT uq_rpa_tenant_id UNIQUE (tenant_id, id)
)""",
"""CREATE TABLE user_role_assignments (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
    user_account_id UUID NOT NULL,
    role_id UUID NOT NULL,
    assigned_at_utc TIMESTAMPTZ NOT NULL,
    CONSTRAINT fk_ura_user_tenant
        FOREIGN KEY (tenant_id, user_account_id)
        REFERENCES user_accounts (tenant_id, id) MATCH FULL,
    CONSTRAINT fk_ura_role_tenant
        FOREIGN KEY (tenant_id, role_id)
        REFERENCES tenant_roles (tenant_id, id) MATCH FULL,
    CONSTRAINT uq_ura_user_role UNIQUE (tenant_id, user_account_id, role_id),
    CONSTRAINT uq_ura_tenant_id UNIQUE (tenant_id, id)
)""",
"""CREATE TABLE tenant_governance_assignments (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
    person_id UUID NOT NULL,
    governance_role VARCHAR(64) NOT NULL
        CHECK (governance_role IN (
            'CLINIC_OWNER', 'CLINIC_MANAGER', 'DEPUTY_ADMIN', 'RECEPTIONIST'
        )),
    assigned_at_utc TIMESTAMPTZ NOT NULL,
    CONSTRAINT fk_tga_person_tenant
        FOREIGN KEY (tenant_id, person_id)
        REFERENCES tenant_persons (tenant_id, id) MATCH FULL,
    CONSTRAINT uq_tga_person_role UNIQUE (tenant_id, person_id, governance_role),
    CONSTRAINT uq_tga_tenant_id UNIQUE (tenant_id, id)
)""",
]


def upgrade() -> None:
    for stmt in _STATEMENTS:
        op.execute(stmt)


def downgrade() -> None:
    raise NotImplementedError(
        "TP0003 downgrade is intentionally irreversible under Appendix E.4."
    )

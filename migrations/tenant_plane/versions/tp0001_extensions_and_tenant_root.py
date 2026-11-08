"""TP0001 — Extensions and tenant root.

Installs/verifies btree_gist and creates tenant_registry using the complete
verbatim F.2 definition from docs/FINAL_MASTER_SPECIFICATION_v3.0.1_FINAL.txt.
No UUID-generating defaults, no RLS, no other F.2 tables.

Revision ID: tp0001
Revises:
Create Date: 2026-11-08
"""

from typing import Sequence, Union

from alembic import op

revision: str = "tp0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Verbatim Appendix F.2 tenant root (v3.0.1) — do not paraphrase.
_F2_TENANT_ROOT_SQL = """
CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE tenant_registry (
    tenant_id UUID PRIMARY KEY,
    tenant_status VARCHAR(24) NOT NULL
        CHECK (tenant_status IN ('ACTIVE', 'SUSPENDED', 'DELETING', 'DELETED')),
    timezone_name TEXT NOT NULL,
    created_at_utc TIMESTAMPTZ NOT NULL,
    updated_at_utc TIMESTAMPTZ NOT NULL
);
"""


def upgrade() -> None:
    op.execute(_F2_TENANT_ROOT_SQL)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tenant_registry;")
    # Leave btree_gist installed; extension may be shared.

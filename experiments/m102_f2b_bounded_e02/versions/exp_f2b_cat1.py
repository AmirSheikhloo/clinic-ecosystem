"""Synthetic Catalog branch root — depends on base only, NOT HMAC Phase-8."""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "exp_f2b_cat1"
down_revision: Union[str, None] = "exp_f2b_base"
branch_labels: Union[str, Sequence[str], None] = ("tenant_catalog",)
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS exp_f2b_catalog_items (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES exp_f2b_tenants(tenant_id),
          atomic_capacity_units INT NOT NULL DEFAULT 1
            CHECK (atomic_capacity_units = 1),
          group_mode TEXT NOT NULL DEFAULT 'AND'
            CHECK (group_mode IN ('AND', 'OR'))
        )
        """
    )
    op.execute(
        """
        INSERT INTO exp_f2b_meta(key, value) VALUES ('catalog_rev', 'cat1')
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS exp_f2b_catalog_items CASCADE")
    op.execute("DELETE FROM exp_f2b_meta WHERE key = 'catalog_rev'")

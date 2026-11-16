"""Synthetic Catalog successor — still independent of HMAC branch."""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "exp_f2b_cat2"
down_revision: Union[str, None] = "exp_f2b_cat1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE exp_f2b_catalog_items
          ADD COLUMN IF NOT EXISTS schedule_hint TEXT NOT NULL DEFAULT 'none'
        """
    )
    op.execute(
        """
        INSERT INTO exp_f2b_meta(key, value) VALUES ('catalog_rev', 'cat2')
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE exp_f2b_catalog_items DROP COLUMN IF EXISTS schedule_hint"
    )
    op.execute(
        """
        INSERT INTO exp_f2b_meta(key, value) VALUES ('catalog_rev', 'cat1')
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """
    )

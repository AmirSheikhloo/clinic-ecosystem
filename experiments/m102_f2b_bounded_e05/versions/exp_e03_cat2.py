"""Synthetic Catalog successor."""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "exp_e03_cat2"
down_revision: Union[str, None] = "exp_e03_cat1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO exp_e03_meta(key, value) VALUES ('catalog_rev', 'cat2')
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """
    )


def downgrade() -> None:
    op.execute(
        """
        INSERT INTO exp_e03_meta(key, value) VALUES ('catalog_rev', 'cat1')
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """
    )

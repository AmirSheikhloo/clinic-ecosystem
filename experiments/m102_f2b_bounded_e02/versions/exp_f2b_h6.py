"""Synthetic HMAC Phase-6 analogue — concurrent unique index on next digest."""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "exp_f2b_h6"
down_revision: Union[str, None] = "exp_f2b_base"
branch_labels: Union[str, Sequence[str], None] = ("hmac_rotation",)
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Dedicated autocommit boundary for CONCURRENTLY (clause 771 phase-6 analogue).
    with op.get_context().autocommit_block():
        op.execute(
            """
            CREATE UNIQUE INDEX CONCURRENTLY uq_exp_f2b_next_lookup
            ON exp_f2b_identifiers (tenant_id, lookup_hmac_next)
            WHERE lookup_hmac_next IS NOT NULL
            """
        )
    op.execute(
        """
        INSERT INTO exp_f2b_meta(key, value) VALUES ('hmac_phase6', 'index_built')
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """
    )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS uq_exp_f2b_next_lookup")
    op.execute("DELETE FROM exp_f2b_meta WHERE key = 'hmac_phase6'")

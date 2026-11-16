"""Synthetic HMAC Phase-8 analogue — constraint validation + authority cutover gate."""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "exp_f2b_h8"
down_revision: Union[str, None] = "exp_f2b_h6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Require next digests populated before cutover marker.
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1 FROM exp_f2b_identifiers WHERE lookup_hmac_next IS NULL
          ) THEN
            RAISE EXCEPTION 'exp_f2b_h8 refused: Phase-8 backfill incomplete';
          END IF;
        END $$
        """
    )
    op.execute(
        """
        ALTER TABLE exp_f2b_identifiers
          ADD CONSTRAINT ck_exp_f2b_next_required
          CHECK (lookup_hmac_next IS NOT NULL) NOT VALID
        """
    )
    op.execute("ALTER TABLE exp_f2b_identifiers VALIDATE CONSTRAINT ck_exp_f2b_next_required")
    op.execute(
        """
        UPDATE exp_f2b_meta SET value = 'gen2'
        WHERE key = 'active_authority'
        """
    )
    op.execute(
        """
        INSERT INTO exp_f2b_meta(key, value) VALUES ('hmac_phase8', 'cutover')
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE exp_f2b_identifiers DROP CONSTRAINT IF EXISTS ck_exp_f2b_next_required"
    )
    op.execute(
        "UPDATE exp_f2b_meta SET value = 'gen1' WHERE key = 'active_authority'"
    )
    op.execute("DELETE FROM exp_f2b_meta WHERE key = 'hmac_phase8'")

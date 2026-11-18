"""Synthetic HMAC Phase-8 — real SET NOT NULL + validated CHECK + guarded cutover."""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "exp_e03_h8"
down_revision: Union[str, None] = "exp_e03_h6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _guard_catalog(conn) -> None:
    # incomplete backfill
    nulls = conn.execute(
        text("SELECT count(*) FROM exp_e03_identifiers WHERE lookup_hmac_next IS NULL")
    ).scalar()
    if nulls and nulls > 0:
        raise RuntimeError(f"exp_e03_h8 refused: Phase-8 backfill incomplete nulls={nulls}")
    idx = conn.execute(
        text(
            """
            SELECT i.indisvalid, i.indisready
            FROM pg_class c
            JOIN pg_index i ON i.indexrelid = c.oid
            WHERE c.relname = 'uq_exp_e03_next_lookup'
            """
        )
    ).first()
    if not idx or not idx[0] or not idx[1]:
        raise RuntimeError(f"exp_e03_h8 refused: next index invalid/absent {idx}")


def upgrade() -> None:
    conn = op.get_bind()
    _guard_catalog(conn)

    # Actual column NOT NULL (A02 corrective — not CHECK-only)
    op.execute("ALTER TABLE exp_e03_identifiers ALTER COLUMN lookup_hmac_next SET NOT NULL")
    op.execute(
        """
        ALTER TABLE exp_e03_identifiers
          ADD CONSTRAINT ck_exp_e03_next_required
          CHECK (lookup_hmac_next IS NOT NULL) NOT VALID
        """
    )
    op.execute("ALTER TABLE exp_e03_identifiers VALIDATE CONSTRAINT ck_exp_e03_next_required")

    # Catalog proofs before authority switch
    att = conn.execute(
        text(
            """
            SELECT a.attnotnull
            FROM pg_attribute a
            JOIN pg_class c ON c.oid = a.attrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public'
              AND c.relname = 'exp_e03_identifiers'
              AND a.attname = 'lookup_hmac_next'
              AND a.attnum > 0 AND NOT a.attisdropped
            """
        )
    ).scalar()
    con = conn.execute(
        text(
            """
            SELECT convalidated
            FROM pg_constraint
            WHERE conname = 'ck_exp_e03_next_required'
            """
        )
    ).scalar()
    if att is not True or con is not True:
        raise RuntimeError(
            f"exp_e03_h8 refused authority switch: attnotnull={att} convalidated={con}"
        )

    op.execute("UPDATE exp_e03_meta SET value = 'gen2' WHERE key = 'active_authority'")
    op.execute(
        """
        INSERT INTO exp_e03_meta(key, value) VALUES ('hmac_phase8', 'cutover')
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE exp_e03_identifiers DROP CONSTRAINT IF EXISTS ck_exp_e03_next_required"
    )
    op.execute(
        "ALTER TABLE exp_e03_identifiers ALTER COLUMN lookup_hmac_next DROP NOT NULL"
    )
    op.execute("UPDATE exp_e03_meta SET value = 'gen1' WHERE key = 'active_authority'")
    op.execute("DELETE FROM exp_e03_meta WHERE key = 'hmac_phase8'")

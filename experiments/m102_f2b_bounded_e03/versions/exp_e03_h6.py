"""Synthetic HMAC Phase-6 analogue — CONCURRENTLY unique index on next digest."""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "exp_e03_h6"
down_revision: Union[str, None] = "exp_e03_base"
branch_labels: Union[str, Sequence[str], None] = ("hmac_rotation",)
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    before = conn.execute(
        text("SELECT current_user, session_user, txid_current()")
    ).one()
    # Dedicated autocommit boundary for CONCURRENTLY (clause 771 phase-6 analogue).
    with op.get_context().autocommit_block():
        inside = conn.execute(
            text("SELECT current_user, session_user")
        ).one()
        if inside[0] != "exp_e03_migrator":
            raise RuntimeError(
                f"STOP_SECURITY: unexpected current_user inside autocommit_block: {inside}"
            )
        op.execute(
            """
            CREATE UNIQUE INDEX CONCURRENTLY uq_exp_e03_next_lookup
            ON exp_e03_identifiers (tenant_id, lookup_hmac_next)
            WHERE lookup_hmac_next IS NOT NULL
            """
        )
    after = conn.execute(
        text("SELECT current_user, session_user")
    ).one()
    if after[0] != "exp_e03_migrator":
        raise RuntimeError(
            f"STOP_SECURITY: role not restored after autocommit_block: {after} (before={before})"
        )
    # Refuse stamp advancement if index invalid
    row = conn.execute(
        text(
            """
            SELECT i.indisvalid, i.indisready
            FROM pg_class c
            JOIN pg_index i ON i.indexrelid = c.oid
            WHERE c.relname = 'uq_exp_e03_next_lookup'
            """
        )
    ).first()
    if not row or not row[0] or not row[1]:
        raise RuntimeError(
            f"STOP_SECURITY: refusing Phase-6 stamp; index state={row}"
        )
    op.execute(
        """
        INSERT INTO exp_e03_meta(key, value) VALUES ('hmac_phase6', 'index_built')
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """
    )
    op.execute(
        f"""
        INSERT INTO exp_e03_meta(key, value) VALUES
          ('h6_role_before', '{before[0]}'),
          ('h6_role_inside', '{inside[0]}'),
          ('h6_role_after', '{after[0]}')
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """
    )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS uq_exp_e03_next_lookup")
    op.execute("DELETE FROM exp_e03_meta WHERE key = 'hmac_phase6'")

"""CP0000 — Control Plane Alembic baseline (no business DDL).

Initializes Control Plane migration version tracking without inventing
CP0001 business tables or columns. M0 intentionally contains no CP schema.

Revision ID: cp0000
Revises:
Create Date: 2026-11-08
"""

from typing import Sequence, Union

revision: str = "cp0000"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # No Control Plane business DDL in M0.
    pass


def downgrade() -> None:
    pass

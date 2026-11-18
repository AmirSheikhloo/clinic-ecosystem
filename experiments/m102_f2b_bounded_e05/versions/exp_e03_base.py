"""Synthetic shared base — not an official TP revision."""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "exp_e03_base"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS exp_e03_tenants (
          tenant_id UUID PRIMARY KEY,
          label TEXT NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS exp_e03_identifiers (
          id UUID PRIMARY KEY,
          tenant_id UUID NOT NULL REFERENCES exp_e03_tenants(tenant_id),
          canonical_value TEXT NOT NULL,
          lookup_hmac_active BYTEA NOT NULL
            CHECK (octet_length(lookup_hmac_active) = 32),
          hmac_key_version_active SMALLINT NOT NULL DEFAULT 1,
          lookup_hmac_next BYTEA NULL
            CHECK (lookup_hmac_next IS NULL OR octet_length(lookup_hmac_next) = 32),
          hmac_key_version_next SMALLINT NULL,
          authority_generation SMALLINT NOT NULL DEFAULT 1,
          CONSTRAINT ck_exp_e03_next_pair CHECK (
            (lookup_hmac_next IS NULL AND hmac_key_version_next IS NULL)
            OR (lookup_hmac_next IS NOT NULL AND hmac_key_version_next IS NOT NULL)
          )
        )
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_exp_e03_active_lookup
        ON exp_e03_identifiers (tenant_id, lookup_hmac_active)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS exp_e03_meta (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL
        )
        """
    )
    op.execute(
        """
        INSERT INTO exp_e03_meta(key, value) VALUES ('active_authority', 'gen1')
        ON CONFLICT (key) DO NOTHING
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS exp_e03_admission_policy (
          source_heads TEXT NOT NULL,
          dest_heads TEXT NOT NULL,
          decision TEXT NOT NULL CHECK (decision IN ('ALLOW','DENY')),
          rationale TEXT NOT NULL,
          PRIMARY KEY (source_heads, dest_heads)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS exp_e03_admission_policy CASCADE")
    op.execute("DROP TABLE IF EXISTS exp_e03_identifiers CASCADE")
    op.execute("DROP TABLE IF EXISTS exp_e03_tenants CASCADE")
    op.execute("DROP TABLE IF EXISTS exp_e03_meta CASCADE")

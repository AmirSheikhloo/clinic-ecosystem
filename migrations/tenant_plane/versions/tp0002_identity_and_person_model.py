"""TP0002 — Identity and person model (Appendix F.2 remainder).

Creates tenant_persons, person_identifiers, person_phones, patient_profiles,
staff_profiles, and user_accounts using the complete verbatim F.2 definitions
from docs/FINAL_MASTER_SPECIFICATION_v3.0.1_FINAL.txt (after tenant_registry
already created by TP0001). No UUID-generating defaults. No RLS (TP0007).

Revision ID: tp0002
Revises: tp0001
Create Date: 2026-11-10
"""

from typing import Sequence, Union

from alembic import op

revision: str = "tp0002"
down_revision: Union[str, None] = "tp0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Verbatim Appendix F.2 statements (v3.0.1) — do not paraphrase.
# Split for asyncpg single-command prepare semantics; SQL text identical to F.2.

_STATEMENTS = [
"""CREATE TABLE tenant_persons (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    birth_date DATE NULL,
    gender VARCHAR(24) NULL,
    aggregate_version BIGINT NOT NULL CHECK (aggregate_version > 0),
    created_at_utc TIMESTAMPTZ NOT NULL,
    updated_at_utc TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_person_tenant_id UNIQUE (tenant_id, id)
)""",
"""CREATE TABLE person_identifiers (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
    person_id UUID NOT NULL,
    id_type VARCHAR(32) NOT NULL
        CHECK (id_type IN ('IR_NATIONAL_ID', 'FOREIGN_FIDA_CODE', 'FOREIGN_PASSPORT')),
    issuing_country_or_authority VARCHAR(64) NOT NULL,
    id_ciphertext BYTEA NOT NULL,
    nonce_96bit BYTEA NOT NULL CHECK (octet_length(nonce_96bit) = 12),
    auth_tag_128bit BYTEA NOT NULL CHECK (octet_length(auth_tag_128bit) = 16),
    encryption_key_version SMALLINT NOT NULL,
    aad_version SMALLINT NOT NULL,
    masked_display VARCHAR(64) NOT NULL,
    verification_status VARCHAR(40) NOT NULL
        CHECK (verification_status IN ('SYNTACTICALLY_VALID_UNVERIFIED', 'OFFICIALLY_VERIFIED')),
    lookup_hmac_active BYTEA NOT NULL CHECK (octet_length(lookup_hmac_active) = 32),
    hmac_key_version_active SMALLINT NOT NULL,
    lookup_hmac_next BYTEA NULL
        CHECK (lookup_hmac_next IS NULL OR octet_length(lookup_hmac_next) = 32),
    hmac_key_version_next SMALLINT NULL,
    created_at_utc TIMESTAMPTZ NOT NULL,
    CONSTRAINT fk_identifier_person_tenant
        FOREIGN KEY (tenant_id, person_id)
        REFERENCES tenant_persons (tenant_id, id) MATCH FULL,
    CONSTRAINT uq_identifier_tenant_id UNIQUE (tenant_id, id),
    CONSTRAINT ck_identifier_next_pair CHECK (
        (lookup_hmac_next IS NULL AND hmac_key_version_next IS NULL)
        OR (lookup_hmac_next IS NOT NULL AND hmac_key_version_next IS NOT NULL)
    )
)""",
"""CREATE UNIQUE INDEX uq_person_identifier_active_lookup
ON person_identifiers (tenant_id, id_type, issuing_country_or_authority, lookup_hmac_active)""",
"""CREATE UNIQUE INDEX uq_person_identifier_next_lookup
ON person_identifiers (tenant_id, id_type, issuing_country_or_authority, lookup_hmac_next)
WHERE lookup_hmac_next IS NOT NULL""",
"""CREATE TABLE person_phones (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
    person_id UUID NOT NULL,
    phone_ciphertext BYTEA NOT NULL,
    nonce_96bit BYTEA NOT NULL CHECK (octet_length(nonce_96bit) = 12),
    auth_tag_128bit BYTEA NOT NULL CHECK (octet_length(auth_tag_128bit) = 16),
    encryption_key_version SMALLINT NOT NULL,
    aad_version SMALLINT NOT NULL,
    masked_phone VARCHAR(32) NOT NULL,
    phone_lookup_hmac BYTEA NOT NULL CHECK (octet_length(phone_lookup_hmac) = 32),
    hmac_key_version SMALLINT NOT NULL,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    is_shared_phone BOOLEAN NOT NULL DEFAULT FALSE,
    phone_verified_at_utc TIMESTAMPTZ NULL,
    created_at_utc TIMESTAMPTZ NOT NULL,
    CONSTRAINT fk_person_phone_owner_tenant
        FOREIGN KEY (tenant_id, person_id)
        REFERENCES tenant_persons (tenant_id, id) MATCH FULL,
    CONSTRAINT uq_person_phone_tenant_id UNIQUE (tenant_id, id)
)""",
"""CREATE INDEX ix_person_phones_lookup
ON person_phones (tenant_id, hmac_key_version, phone_lookup_hmac)""",
"""CREATE TABLE patient_profiles (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
    person_id UUID NOT NULL,
    dossier_number VARCHAR(64) NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at_utc TIMESTAMPTZ NOT NULL,
    CONSTRAINT fk_patient_profile_person_tenant
        FOREIGN KEY (tenant_id, person_id)
        REFERENCES tenant_persons (tenant_id, id) MATCH FULL,
    CONSTRAINT uq_patient_profile_person UNIQUE (tenant_id, person_id),
    CONSTRAINT uq_patient_profile_tenant_id UNIQUE (tenant_id, id)
)""",
"""CREATE TABLE staff_profiles (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
    person_id UUID NOT NULL,
    staff_kind VARCHAR(32) NOT NULL,
    medical_council_code VARCHAR(64) NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at_utc TIMESTAMPTZ NOT NULL,
    CONSTRAINT fk_staff_profile_person_tenant
        FOREIGN KEY (tenant_id, person_id)
        REFERENCES tenant_persons (tenant_id, id) MATCH FULL,
    CONSTRAINT uq_staff_profile_person UNIQUE (tenant_id, person_id),
    CONSTRAINT uq_staff_profile_tenant_id UNIQUE (tenant_id, id)
)""",
"""CREATE TABLE user_accounts (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
    person_id UUID NOT NULL,
    login_identifier VARCHAR(254) NOT NULL,
    normalized_login_identifier VARCHAR(254) NOT NULL,
    password_hash_argon2id TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    failed_login_attempts INTEGER NOT NULL DEFAULT 0 CHECK (failed_login_attempts >= 0),
    locked_until_utc TIMESTAMPTZ NULL,
    password_changed_at_utc TIMESTAMPTZ NULL,
    aggregate_version BIGINT NOT NULL CHECK (aggregate_version > 0),
    created_at_utc TIMESTAMPTZ NOT NULL,
    updated_at_utc TIMESTAMPTZ NOT NULL,
    CONSTRAINT fk_user_account_person_tenant
        FOREIGN KEY (tenant_id, person_id)
        REFERENCES tenant_persons (tenant_id, id) MATCH FULL,
    CONSTRAINT uq_user_account_person UNIQUE (tenant_id, person_id),
    CONSTRAINT uq_user_account_login_identifier UNIQUE (tenant_id, normalized_login_identifier),
    CONSTRAINT uq_user_account_tenant_id UNIQUE (tenant_id, id)
)""",
]


def upgrade() -> None:
    for stmt in _STATEMENTS:
        op.execute(stmt)


def downgrade() -> None:
    raise NotImplementedError(
        "TP0002 downgrade is intentionally irreversible under Appendix E.4: "
        "identity tables may already hold tenant data and require a "
        "forward-fix/restore plan, not a destructive downgrade."
    )

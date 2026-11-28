CREATE TABLE patient_identity_reviews (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  patient_id UUID NOT NULL,
  review_state VARCHAR(24) NOT NULL CHECK (review_state IN ('NEEDS_COMPLETION', 'RESOLVED', 'CANCELLED')),
  reason VARCHAR(200) NOT NULL CHECK (length(btrim(reason)) > 0),
  opened_by_user_id UUID NOT NULL,
  opened_at_utc TIMESTAMPTZ NOT NULL,
  resolved_by_user_id UUID NULL,
  resolved_at_utc TIMESTAMPTZ NULL,
  resolution_reason VARCHAR(200) NULL,
  aggregate_version BIGINT NOT NULL CHECK (aggregate_version > 0),
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  FOREIGN KEY (tenant_id, patient_id) REFERENCES patient_profiles(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, opened_by_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, resolved_by_user_id) REFERENCES user_accounts(tenant_id, id) MATCH SIMPLE,
  CHECK (
    (review_state = 'NEEDS_COMPLETION' AND resolved_by_user_id IS NULL AND resolved_at_utc IS NULL AND resolution_reason IS NULL)
    OR (review_state IN ('RESOLVED', 'CANCELLED') AND resolved_by_user_id IS NOT NULL AND resolved_at_utc IS NOT NULL
        AND resolved_at_utc >= opened_at_utc AND resolution_reason IS NOT NULL AND length(btrim(resolution_reason)) > 0)
  )
);

CREATE UNIQUE INDEX patient_identity_open_review_uq ON patient_identity_reviews(tenant_id, patient_id)
  WHERE review_state = 'NEEDS_COMPLETION';

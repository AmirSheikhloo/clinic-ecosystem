CREATE TABLE payment_attempts (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  beneficiary_patient_id UUID NULL,
  appointment_id UUID NULL,
  invoice_id UUID NULL,
  merchant_instrument_id UUID NOT NULL,
  order_reference VARCHAR(128) NOT NULL,
  expected_amount_irr BIGINT NOT NULL CHECK (expected_amount_irr > 0),
  currency_code CHAR(3) NOT NULL CHECK (currency_code = 'IRR'),
  deposit_policy_version VARCHAR(64) NOT NULL,
  state VARCHAR(24) NOT NULL CHECK (state IN ('CREATED', 'INITIATED', 'PENDING', 'AMBIGUOUS', 'FAILED', 'VERIFIED', 'EXPIRED')),
  provider_paid_at_utc TIMESTAMPTZ NULL,
  callback_received_at_utc TIMESTAMPTZ NULL,
  aggregate_version BIGINT NOT NULL CHECK (aggregate_version > 0),
  created_at_utc TIMESTAMPTZ NOT NULL,
  updated_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, merchant_instrument_id, order_reference),
  FOREIGN KEY (tenant_id, beneficiary_patient_id) REFERENCES patient_profiles(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, appointment_id) REFERENCES appointments(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, invoice_id) REFERENCES invoice_documents(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, merchant_instrument_id) REFERENCES clinic_payment_instruments(tenant_id, id) MATCH FULL
);

CREATE TABLE unverified_payment_claims (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  beneficiary_patient_id UUID NULL,
  invoice_id UUID NULL,
  destination_instrument_id UUID NOT NULL,
  claimed_amount_irr BIGINT NOT NULL CHECK (claimed_amount_irr > 0),
  currency_code CHAR(3) NOT NULL CHECK (currency_code = 'IRR'),
  claimed_reference VARCHAR(128) NULL,
  evidence_object_reference VARCHAR(256) NULL,
  state VARCHAR(16) NOT NULL CHECK (state IN ('PENDING', 'REJECTED', 'VERIFIED')),
  recorded_by_user_id UUID NOT NULL,
  reviewed_by_user_id UUID NULL,
  reviewed_at_utc TIMESTAMPTZ NULL,
  review_reason VARCHAR(200) NULL,
  aggregate_version BIGINT NOT NULL CHECK (aggregate_version > 0),
  created_at_utc TIMESTAMPTZ NOT NULL,
  updated_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  FOREIGN KEY (tenant_id, beneficiary_patient_id) REFERENCES patient_profiles(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, invoice_id) REFERENCES invoice_documents(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, destination_instrument_id) REFERENCES clinic_payment_instruments(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, recorded_by_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, reviewed_by_user_id) REFERENCES user_accounts(tenant_id, id) MATCH SIMPLE,
  CHECK (
    (state = 'PENDING' AND reviewed_by_user_id IS NULL AND reviewed_at_utc IS NULL AND review_reason IS NULL)
    OR (state IN ('REJECTED', 'VERIFIED') AND reviewed_by_user_id IS NOT NULL AND reviewed_at_utc IS NOT NULL AND reviewed_at_utc >= created_at_utc)
  )
);

CREATE TABLE payment_receipts (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  receipt_number VARCHAR(32) NOT NULL,
  amount_irr BIGINT NOT NULL CHECK (amount_irr > 0),
  currency_code CHAR(3) NOT NULL CHECK (currency_code = 'IRR'),
  payment_method VARCHAR(24) NOT NULL CHECK (payment_method IN ('CASH', 'POS', 'CARD_TO_CARD', 'ONLINE')),
  occurred_at_utc TIMESTAMPTZ NOT NULL,
  operator_user_id UUID NULL,
  actor_type VARCHAR(32) NOT NULL CHECK (actor_type IN ('STAFF_USER', 'SYSTEM_CALLBACK')),
  actor_id UUID NOT NULL,
  correlation_id UUID NOT NULL,
  payer_patient_id UUID NULL,
  credit_beneficiary_patient_id UUID NULL,
  payer_source VARCHAR(100) NOT NULL,
  department_id UUID NULL,
  shift_id UUID NULL,
  instrument_id UUID NULL,
  payment_attempt_id UUID NULL,
  verified_claim_id UUID NULL,
  provider_reference VARCHAR(128) NULL,
  verification_evidence_ref VARCHAR(256) NULL,
  terminal_state VARCHAR(24) NULL,
  verified_at_utc TIMESTAMPTZ NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, receipt_number),
  UNIQUE (tenant_id, payment_attempt_id),
  UNIQUE (tenant_id, verified_claim_id),
  FOREIGN KEY (tenant_id, operator_user_id) REFERENCES user_accounts(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, payer_patient_id) REFERENCES patient_profiles(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, credit_beneficiary_patient_id) REFERENCES patient_profiles(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, department_id) REFERENCES departments(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, shift_id) REFERENCES cashier_shifts(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, instrument_id) REFERENCES clinic_payment_instruments(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, payment_attempt_id) REFERENCES payment_attempts(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, verified_claim_id) REFERENCES unverified_payment_claims(tenant_id, id) MATCH SIMPLE,
  CHECK ((actor_type = 'STAFF_USER' AND operator_user_id IS NOT NULL AND actor_id = operator_user_id)
      OR (actor_type = 'SYSTEM_CALLBACK' AND operator_user_id IS NULL AND payment_method = 'ONLINE')),
  CHECK (
    (payment_method = 'CASH' AND shift_id IS NOT NULL AND payment_attempt_id IS NULL AND verified_claim_id IS NULL AND terminal_state IS NULL)
    OR (payment_method = 'POS' AND shift_id IS NOT NULL AND instrument_id IS NOT NULL AND terminal_state IS NOT NULL
        AND terminal_state IN ('AUTHORIZED_CONFIRMED', 'SETTLED') AND verification_evidence_ref IS NOT NULL
        AND payment_attempt_id IS NULL AND verified_claim_id IS NULL)
    OR (payment_method = 'CARD_TO_CARD' AND instrument_id IS NOT NULL AND verified_claim_id IS NOT NULL
        AND provider_reference IS NOT NULL AND verification_evidence_ref IS NOT NULL
        AND payment_attempt_id IS NULL AND terminal_state IS NULL)
    OR (payment_method = 'ONLINE' AND instrument_id IS NOT NULL AND payment_attempt_id IS NOT NULL
        AND provider_reference IS NOT NULL AND verification_evidence_ref IS NOT NULL
        AND verified_claim_id IS NULL AND terminal_state IS NULL)
  )
);

CREATE UNIQUE INDEX receipt_provider_reference_uq ON payment_receipts(tenant_id, instrument_id, provider_reference)
  WHERE instrument_id IS NOT NULL AND provider_reference IS NOT NULL;

CREATE TABLE receipt_allocations (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  receipt_id UUID NOT NULL,
  invoice_id UUID NOT NULL,
  invoice_line_id UUID NOT NULL,
  allocation_kind VARCHAR(16) NOT NULL CHECK (allocation_kind IN ('APPLY', 'REVERSE')),
  reverses_allocation_id UUID NULL,
  amount_irr BIGINT NOT NULL CHECK (amount_irr > 0),
  operator_user_id UUID NOT NULL,
  correlation_id UUID NOT NULL,
  reason_code VARCHAR(64) NULL,
  occurred_at_utc TIMESTAMPTZ NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, receipt_id, invoice_id, invoice_line_id, id),
  FOREIGN KEY (tenant_id, receipt_id) REFERENCES payment_receipts(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, invoice_id, invoice_line_id) REFERENCES invoice_lines(tenant_id, invoice_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, receipt_id, invoice_id, invoice_line_id, reverses_allocation_id)
    REFERENCES receipt_allocations(tenant_id, receipt_id, invoice_id, invoice_line_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, operator_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL,
  CHECK ((allocation_kind = 'APPLY' AND reverses_allocation_id IS NULL)
      OR (allocation_kind = 'REVERSE' AND reverses_allocation_id IS NOT NULL AND reason_code IS NOT NULL)),
  CHECK (reverses_allocation_id IS NULL OR reverses_allocation_id <> id)
);

CREATE TABLE financial_adjustments (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  invoice_id UUID NOT NULL,
  invoice_line_id UUID NOT NULL,
  adjustment_kind VARCHAR(32) NOT NULL CHECK (adjustment_kind IN ('POST_PAYMENT_DISCOUNT', 'CORRECTION', 'WRITE_OFF', 'CHARGE_CANCELLATION', 'SUBSIDY_CORRECTION', 'ROUNDING_CORRECTION')),
  patient_delta_irr BIGINT NOT NULL,
  basic_insurer_delta_irr BIGINT NOT NULL DEFAULT 0,
  supplementary_insurer_delta_irr BIGINT NOT NULL DEFAULT 0,
  reason_code VARCHAR(64) NOT NULL,
  reason_text VARCHAR(500) NULL,
  operator_user_id UUID NOT NULL,
  approver_user_id UUID NULL,
  actor_type VARCHAR(32) NOT NULL CHECK (actor_type = 'STAFF_USER'),
  actor_id UUID NOT NULL,
  department_id UUID NULL,
  shift_id UUID NULL,
  correlation_id UUID NOT NULL,
  occurred_at_utc TIMESTAMPTZ NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  FOREIGN KEY (tenant_id, invoice_id, invoice_line_id) REFERENCES invoice_lines(tenant_id, invoice_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, operator_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, approver_user_id) REFERENCES user_accounts(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, department_id) REFERENCES departments(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, shift_id) REFERENCES cashier_shifts(tenant_id, id) MATCH SIMPLE,
  CHECK (actor_id = operator_user_id),
  CHECK (patient_delta_irr <> 0 OR basic_insurer_delta_irr <> 0 OR supplementary_insurer_delta_irr <> 0),
  CHECK (adjustment_kind NOT IN ('POST_PAYMENT_DISCOUNT', 'WRITE_OFF', 'CHARGE_CANCELLATION')
      OR (patient_delta_irr <= 0 AND basic_insurer_delta_irr <= 0 AND supplementary_insurer_delta_irr <= 0))
);

CREATE TABLE clinic_payment_refunds (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  refund_number VARCHAR(32) NOT NULL,
  original_receipt_id UUID NOT NULL,
  invoice_id UUID NULL,
  invoice_line_id UUID NULL,
  original_allocation_id UUID NULL,
  amount_irr BIGINT NOT NULL CHECK (amount_irr > 0),
  currency_code CHAR(3) NOT NULL CHECK (currency_code = 'IRR'),
  refund_method VARCHAR(24) NOT NULL CHECK (refund_method IN ('CASH', 'POS', 'CARD_TO_CARD', 'ONLINE')),
  instrument_id UUID NULL,
  destination_reference VARCHAR(128) NULL,
  provider_reference VARCHAR(128) NULL,
  verification_evidence_ref VARCHAR(256) NULL,
  reason_code VARCHAR(64) NOT NULL,
  reason_text VARCHAR(500) NULL,
  operator_user_id UUID NOT NULL,
  actor_type VARCHAR(32) NOT NULL CHECK (actor_type = 'STAFF_USER'),
  actor_id UUID NOT NULL,
  department_id UUID NULL,
  shift_id UUID NULL,
  correlation_id UUID NOT NULL,
  occurred_at_utc TIMESTAMPTZ NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, refund_number),
  FOREIGN KEY (tenant_id, original_receipt_id) REFERENCES payment_receipts(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, invoice_id, invoice_line_id) REFERENCES invoice_lines(tenant_id, invoice_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, original_receipt_id, invoice_id, invoice_line_id, original_allocation_id)
    REFERENCES receipt_allocations(tenant_id, receipt_id, invoice_id, invoice_line_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, instrument_id) REFERENCES clinic_payment_instruments(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, operator_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, department_id) REFERENCES departments(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, shift_id) REFERENCES cashier_shifts(tenant_id, id) MATCH SIMPLE,
  CHECK (actor_id = operator_user_id),
  CHECK ((invoice_id IS NULL AND invoice_line_id IS NULL AND original_allocation_id IS NULL)
      OR (invoice_id IS NOT NULL AND invoice_line_id IS NOT NULL AND original_allocation_id IS NOT NULL)),
  CHECK (
    (refund_method = 'CASH' AND shift_id IS NOT NULL)
    OR (refund_method = 'POS' AND shift_id IS NOT NULL AND instrument_id IS NOT NULL AND verification_evidence_ref IS NOT NULL)
    OR (refund_method IN ('CARD_TO_CARD', 'ONLINE') AND instrument_id IS NOT NULL AND destination_reference IS NOT NULL
        AND provider_reference IS NOT NULL AND verification_evidence_ref IS NOT NULL)
  )
);

CREATE UNIQUE INDEX clinic_refund_reference_uq ON clinic_payment_refunds(tenant_id, instrument_id, provider_reference)
  WHERE instrument_id IS NOT NULL AND provider_reference IS NOT NULL;
CREATE INDEX receipts_occurred_idx ON payment_receipts(tenant_id, occurred_at_utc, id);
CREATE INDEX allocations_receipt_idx ON receipt_allocations(tenant_id, receipt_id);
CREATE INDEX allocations_invoice_line_idx ON receipt_allocations(tenant_id, invoice_id, invoice_line_id);
CREATE INDEX adjustments_line_idx ON financial_adjustments(tenant_id, invoice_id, invoice_line_id);
CREATE INDEX refunds_receipt_idx ON clinic_payment_refunds(tenant_id, original_receipt_id);

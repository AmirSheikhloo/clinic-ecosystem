-- PROPOSED disposable ops tables for treatment courses / rolling recall (Task 34 R2 §9).
-- NOT an official Alembic revision. Apply only under CLINIC_OPS_SCHEMA_MODE=disposable.
-- Source: docs/validation/d010/proposed/TREATMENT_COURSES_ROLLING_RECALL_ARCHITECTURE.md
--
-- Replaces the prior stub (templates/courses/schedules only) with versioned templates,
-- independent sessions, reminder policy snapshots, synthetic outbox, and conservation guards.

-- ---------------------------------------------------------------------------
-- Catalog: service-linked course templates + immutable versions
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS service_course_templates (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  service_id UUID NOT NULL,
  template_code VARCHAR(64) NOT NULL,
  template_name VARCHAR(120) NOT NULL,
  current_version_no INT NOT NULL DEFAULT 1 CHECK (current_version_no > 0),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at_utc TIMESTAMPTZ NOT NULL,
  updated_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, id, service_id),
  UNIQUE (tenant_id, template_code),
  FOREIGN KEY (tenant_id, service_id) REFERENCES services(tenant_id, id) MATCH FULL
);

CREATE TABLE IF NOT EXISTS service_course_template_versions (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  template_id UUID NOT NULL,
  service_id UUID NOT NULL,
  version_no INT NOT NULL CHECK (version_no > 0),
  planned_sessions INT NOT NULL CHECK (planned_sessions > 0 AND planned_sessions <= 100),
  scheduling_mode VARCHAR(16) NOT NULL CHECK (scheduling_mode IN ('ROLLING', 'FIXED')),
  interval_kind VARCHAR(32) NOT NULL
    CHECK (interval_kind IN ('JALALI_CALENDAR_MONTH', 'FIXED_DAYS')),
  interval_value INT NOT NULL CHECK (interval_value > 0 AND interval_value <= 366),
  reminder_lead_days INT NOT NULL DEFAULT 2
    CHECK (reminder_lead_days >= 0 AND reminder_lead_days <= 30),
  quiet_hours_start_minute INT NOT NULL DEFAULT 1320
    CHECK (quiet_hours_start_minute >= 0 AND quiet_hours_start_minute < 1440),
  quiet_hours_end_minute INT NOT NULL DEFAULT 480
    CHECK (quiet_hours_end_minute >= 0 AND quiet_hours_end_minute < 1440),
  long_gap_days INT NOT NULL DEFAULT 120
    CHECK (long_gap_days > 0 AND long_gap_days <= 730),
  max_reminder_attempts INT NOT NULL DEFAULT 5
    CHECK (max_reminder_attempts > 0 AND max_reminder_attempts <= 20),
  billing_mode VARCHAR(24) NOT NULL DEFAULT 'PAY_PER_SESSION'
    CHECK (billing_mode IN ('PAY_PER_SESSION', 'PREPAID_DISABLED')),
  published_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, template_id, version_no),
  UNIQUE (tenant_id, id, service_id),
  FOREIGN KEY (tenant_id, template_id, service_id)
    REFERENCES service_course_templates(tenant_id, id, service_id) MATCH FULL
);

-- Backward-compatible alias view name used by the R2 amendment wording.
-- Prefer service_course_templates + versions for new code.
CREATE TABLE IF NOT EXISTS treatment_course_templates (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  service_id UUID NOT NULL,
  template_name VARCHAR(120) NOT NULL,
  planned_sessions INT NOT NULL CHECK (planned_sessions > 0 AND planned_sessions <= 100),
  interval_kind VARCHAR(32) NOT NULL
    CHECK (interval_kind IN ('JALALI_CALENDAR_MONTH', 'FIXED_DAYS', 'CALENDAR_MONTH')),
  interval_value INT NOT NULL CHECK (interval_value > 0 AND interval_value <= 366),
  reminder_lead_days INT NOT NULL DEFAULT 2 CHECK (reminder_lead_days >= 0 AND reminder_lead_days <= 30),
  billing_mode VARCHAR(24) NOT NULL DEFAULT 'PAY_PER_SESSION'
    CHECK (billing_mode IN ('PAY_PER_SESSION', 'PREPAID_DISABLED')),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  FOREIGN KEY (tenant_id, service_id) REFERENCES services(tenant_id, id) MATCH FULL
);

-- ---------------------------------------------------------------------------
-- Patient courses
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS treatment_courses (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  patient_id UUID NOT NULL,
  service_id UUID NOT NULL,
  template_id UUID,
  template_version_id UUID,
  planned_sessions INT NOT NULL CHECK (planned_sessions > 0 AND planned_sessions <= 100),
  completed_session_count INT NOT NULL DEFAULT 0
    CHECK (completed_session_count >= 0 AND completed_session_count <= planned_sessions),
  voided_session_count INT NOT NULL DEFAULT 0 CHECK (voided_session_count >= 0),
  status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE'
    CHECK (status IN (
      'ACTIVE', 'PAUSED', 'REASSESSMENT_REQUIRED', 'COMPLETED', 'TERMINATED'
    )),
  scheduling_mode VARCHAR(16) NOT NULL DEFAULT 'ROLLING'
    CHECK (scheduling_mode IN ('ROLLING', 'FIXED')),
  interval_kind VARCHAR(32) NOT NULL
    CHECK (interval_kind IN ('JALALI_CALENDAR_MONTH', 'FIXED_DAYS', 'CALENDAR_MONTH')),
  interval_value INT NOT NULL CHECK (interval_value > 0 AND interval_value <= 366),
  reminder_lead_days INT NOT NULL DEFAULT 2
    CHECK (reminder_lead_days >= 0 AND reminder_lead_days <= 30),
  quiet_hours_start_minute INT NOT NULL DEFAULT 1320
    CHECK (quiet_hours_start_minute >= 0 AND quiet_hours_start_minute < 1440),
  quiet_hours_end_minute INT NOT NULL DEFAULT 480
    CHECK (quiet_hours_end_minute >= 0 AND quiet_hours_end_minute < 1440),
  long_gap_days INT NOT NULL DEFAULT 120 CHECK (long_gap_days > 0 AND long_gap_days <= 730),
  max_reminder_attempts INT NOT NULL DEFAULT 5
    CHECK (max_reminder_attempts > 0 AND max_reminder_attempts <= 20),
  billing_mode VARCHAR(24) NOT NULL DEFAULT 'PAY_PER_SESSION'
    CHECK (billing_mode IN ('PAY_PER_SESSION', 'PREPAID_DISABLED')),
  -- Prepaid entitlement path remains disabled pending ratification.
  prepaid_entitlement_enabled BOOLEAN NOT NULL DEFAULT FALSE
    CHECK (prepaid_entitlement_enabled = FALSE),
  next_suggested_date_tehran DATE,
  last_completion_date_tehran DATE,
  current_schedule_version INT NOT NULL DEFAULT 0 CHECK (current_schedule_version >= 0),
  aggregate_version BIGINT NOT NULL DEFAULT 1 CHECK (aggregate_version > 0),
  created_at_utc TIMESTAMPTZ NOT NULL,
  updated_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, id, patient_id, service_id),
  FOREIGN KEY (tenant_id, patient_id) REFERENCES patient_profiles(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, service_id) REFERENCES services(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, template_version_id, service_id)
    REFERENCES service_course_template_versions(tenant_id, id, service_id) MATCH SIMPLE,
  CHECK (
    (billing_mode = 'PAY_PER_SESSION' AND prepaid_entitlement_enabled = FALSE)
    OR (billing_mode = 'PREPAID_DISABLED' AND prepaid_entitlement_enabled = FALSE)
  )
);

CREATE INDEX IF NOT EXISTS treatment_courses_patient_idx
  ON treatment_courses (tenant_id, patient_id, status, id);
CREATE INDEX IF NOT EXISTS treatment_courses_service_idx
  ON treatment_courses (tenant_id, service_id, status, id);

-- ---------------------------------------------------------------------------
-- Independent sessions (no artificial future debt rows required at enroll)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS treatment_course_sessions (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  course_id UUID NOT NULL,
  patient_id UUID NOT NULL,
  service_id UUID NOT NULL,
  session_no INT NOT NULL CHECK (session_no > 0 AND session_no <= 100),
  status VARCHAR(24) NOT NULL DEFAULT 'PLANNED'
    CHECK (status IN ('PLANNED', 'BOOKED', 'COMPLETED', 'VOIDED', 'SUPERSEDED')),
  appointment_id UUID,
  service_record_id UUID,
  completion_tehran_date DATE,
  completion_at_utc TIMESTAMPTZ,
  void_reason VARCHAR(120),
  idempotency_key VARCHAR(200),
  created_at_utc TIMESTAMPTZ NOT NULL,
  updated_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, course_id, session_no, status)
    DEFERRABLE INITIALLY IMMEDIATE,
  UNIQUE (tenant_id, course_id, idempotency_key),
  FOREIGN KEY (tenant_id, course_id, patient_id, service_id)
    REFERENCES treatment_courses(tenant_id, id, patient_id, service_id) MATCH FULL,
  FOREIGN KEY (tenant_id, appointment_id, patient_id, service_id)
    REFERENCES appointments(tenant_id, id, beneficiary_patient_id, service_id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, service_record_id, patient_id, service_id)
    REFERENCES service_records(tenant_id, id, patient_id, service_id) MATCH SIMPLE,
  -- Completion requires PERFORMED evidence timestamps; non-completed must not pretend.
  CHECK (
    (status = 'COMPLETED'
      AND service_record_id IS NOT NULL
      AND completion_tehran_date IS NOT NULL
      AND completion_at_utc IS NOT NULL)
    OR (status <> 'COMPLETED'
      AND service_record_id IS NULL
      AND completion_tehran_date IS NULL
      AND completion_at_utc IS NULL)
  ),
  -- Cancellation never yields COMPLETED (enforced together with trigger below).
  CHECK (status <> 'COMPLETED' OR void_reason IS NULL)
);

CREATE UNIQUE INDEX IF NOT EXISTS treatment_course_sessions_active_uq
  ON treatment_course_sessions (tenant_id, course_id, session_no)
  WHERE status IN ('PLANNED', 'BOOKED', 'COMPLETED');

CREATE UNIQUE INDEX IF NOT EXISTS treatment_course_sessions_performed_uq
  ON treatment_course_sessions (tenant_id, service_record_id)
  WHERE service_record_id IS NOT NULL AND status = 'COMPLETED';

-- ---------------------------------------------------------------------------
-- Reminder policy snapshots + recall schedules
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS treatment_reminder_policy_snapshots (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  course_id UUID NOT NULL,
  schedule_version INT NOT NULL CHECK (schedule_version > 0),
  reminder_lead_days INT NOT NULL CHECK (reminder_lead_days >= 0 AND reminder_lead_days <= 30),
  quiet_hours_start_minute INT NOT NULL
    CHECK (quiet_hours_start_minute >= 0 AND quiet_hours_start_minute < 1440),
  quiet_hours_end_minute INT NOT NULL
    CHECK (quiet_hours_end_minute >= 0 AND quiet_hours_end_minute < 1440),
  max_reminder_attempts INT NOT NULL CHECK (max_reminder_attempts > 0 AND max_reminder_attempts <= 20),
  destination_kind VARCHAR(32) NOT NULL DEFAULT 'SYNTHETIC_SINK'
    CHECK (destination_kind IN ('SYNTHETIC_SINK', 'SYNTHETIC_LOG')),
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, course_id, schedule_version),
  FOREIGN KEY (tenant_id, course_id) REFERENCES treatment_courses(tenant_id, id) MATCH FULL
);

CREATE TABLE IF NOT EXISTS treatment_recall_schedules (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  course_id UUID NOT NULL,
  patient_id UUID NOT NULL,
  service_id UUID NOT NULL,
  schedule_version INT NOT NULL CHECK (schedule_version > 0),
  cycle_no INT NOT NULL CHECK (cycle_no > 0),
  source_session_id UUID,
  suggested_date_tehran DATE NOT NULL,
  reminder_date_tehran DATE NOT NULL,
  reminder_kind VARCHAR(32) NOT NULL DEFAULT 'RETURN_VISIT'
    CHECK (reminder_kind IN ('RETURN_VISIT', 'LONG_GAP_REASSESSMENT')),
  scheduled_at_utc TIMESTAMPTZ NOT NULL,
  status VARCHAR(24) NOT NULL DEFAULT 'SCHEDULED'
    CHECK (status IN (
      'SCHEDULED', 'SUPPRESSED', 'SUPERSEDED', 'ATTEMPTED', 'ACCEPTED', 'FAILED', 'INVALIDATED'
    )),
  suppress_reason VARCHAR(64),
  policy_snapshot_id UUID NOT NULL,
  logical_key VARCHAR(200) NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  updated_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, logical_key),
  UNIQUE (tenant_id, course_id, schedule_version),
  FOREIGN KEY (tenant_id, course_id, patient_id, service_id)
    REFERENCES treatment_courses(tenant_id, id, patient_id, service_id) MATCH FULL,
  FOREIGN KEY (tenant_id, source_session_id)
    REFERENCES treatment_course_sessions(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, policy_snapshot_id)
    REFERENCES treatment_reminder_policy_snapshots(tenant_id, id) MATCH FULL,
  CHECK (reminder_date_tehran <= suggested_date_tehran)
);

CREATE INDEX IF NOT EXISTS treatment_recall_schedules_due_idx
  ON treatment_recall_schedules (tenant_id, status, reminder_date_tehran, id);

-- ---------------------------------------------------------------------------
-- Patient notification preferences (opt-out / identity generation)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS patient_notification_preferences (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  patient_id UUID NOT NULL,
  recalls_opted_out BOOLEAN NOT NULL DEFAULT FALSE,
  quiet_hours_start_minute INT
    CHECK (quiet_hours_start_minute IS NULL
      OR (quiet_hours_start_minute >= 0 AND quiet_hours_start_minute < 1440)),
  quiet_hours_end_minute INT
    CHECK (quiet_hours_end_minute IS NULL
      OR (quiet_hours_end_minute >= 0 AND quiet_hours_end_minute < 1440)),
  -- Opaque destination reference; never store raw phone in outbox payloads.
  destination_ref VARCHAR(128),
  destination_generation INT NOT NULL DEFAULT 1 CHECK (destination_generation > 0),
  updated_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, patient_id),
  FOREIGN KEY (tenant_id, patient_id) REFERENCES patient_profiles(tenant_id, id) MATCH FULL
);

-- ---------------------------------------------------------------------------
-- Synthetic notification outbox (mirrors TP0006 envelope; synthetic destinations only)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS notification_outbox_synthetic (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  message_type VARCHAR(128) NOT NULL,
  payload_json JSONB NOT NULL,
  logical_key VARCHAR(200) NOT NULL,
  course_id UUID,
  schedule_id UUID,
  schedule_version INT,
  destination_kind VARCHAR(32) NOT NULL DEFAULT 'SYNTHETIC_SINK'
    CHECK (destination_kind IN ('SYNTHETIC_SINK', 'SYNTHETIC_LOG')),
  destination_ref VARCHAR(128),
  destination_generation INT,
  earliest_send_at_utc TIMESTAMPTZ NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  locked_until TIMESTAMPTZ,
  lease_id UUID,
  delivered_at_utc TIMESTAMPTZ,
  attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
  max_attempts INTEGER NOT NULL DEFAULT 5 CHECK (max_attempts > 0 AND max_attempts <= 20),
  work_state VARCHAR(24) NOT NULL DEFAULT 'PENDING'
    CHECK (work_state IN (
      'PENDING', 'CLAIMED', 'RETRYABLE', 'DELIVERED', 'FAILED', 'INVALIDATED', 'SUPPRESSED'
    )),
  last_error_code VARCHAR(64),
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, logical_key),
  FOREIGN KEY (tenant_id, course_id) REFERENCES treatment_courses(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, schedule_id) REFERENCES treatment_recall_schedules(tenant_id, id) MATCH SIMPLE
);

CREATE INDEX IF NOT EXISTS notification_outbox_synthetic_due_idx
  ON notification_outbox_synthetic (tenant_id, work_state, earliest_send_at_utc, id)
  WHERE work_state IN ('PENDING', 'RETRYABLE');

CREATE TABLE IF NOT EXISTS synthetic_notification_deliveries (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  outbox_id UUID NOT NULL,
  logical_key VARCHAR(200) NOT NULL,
  message_type VARCHAR(128) NOT NULL,
  payload_json JSONB NOT NULL,
  destination_kind VARCHAR(32) NOT NULL
    CHECK (destination_kind IN ('SYNTHETIC_SINK', 'SYNTHETIC_LOG')),
  accepted_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, logical_key),
  UNIQUE (tenant_id, outbox_id),
  FOREIGN KEY (tenant_id, outbox_id)
    REFERENCES notification_outbox_synthetic(tenant_id, id) MATCH FULL
);

-- ---------------------------------------------------------------------------
-- Guards: PERFORMED-only completion; conservation; no payment completion
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION ops_treatment_session_performed_guard()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  v_kind TEXT;
BEGIN
  IF NEW.status = 'COMPLETED' THEN
    IF NEW.service_record_id IS NULL THEN
      RAISE EXCEPTION 'COURSE_COMPLETION_REQUIRES_PERFORMED_RECORD'
        USING ERRCODE = 'check_violation';
    END IF;
    SELECT record_kind INTO v_kind
    FROM service_records
    WHERE tenant_id = NEW.tenant_id AND id = NEW.service_record_id;
    IF v_kind IS DISTINCT FROM 'PERFORMED' THEN
      RAISE EXCEPTION 'COURSE_COMPLETION_REQUIRES_PERFORMED_RECORD'
        USING ERRCODE = 'check_violation';
    END IF;
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_ops_treatment_session_performed ON treatment_course_sessions;
CREATE TRIGGER trg_ops_treatment_session_performed
  BEFORE INSERT OR UPDATE OF status, service_record_id
  ON treatment_course_sessions
  FOR EACH ROW
  EXECUTE FUNCTION ops_treatment_session_performed_guard();

CREATE OR REPLACE FUNCTION ops_treatment_course_conservation_guard()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  v_completed INT;
BEGIN
  SELECT COUNT(*)::INT INTO v_completed
  FROM treatment_course_sessions
  WHERE tenant_id = NEW.tenant_id
    AND course_id = NEW.id
    AND status = 'COMPLETED';
  IF NEW.completed_session_count IS DISTINCT FROM v_completed THEN
    RAISE EXCEPTION 'COURSE_SESSION_COUNT_CONSERVATION'
      USING ERRCODE = 'check_violation';
  END IF;
  IF NEW.completed_session_count > NEW.planned_sessions THEN
    RAISE EXCEPTION 'COURSE_SESSION_COUNT_OVERFLOW'
      USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END;
$$;

-- Conservation checked on course UPDATE of counters (after session rows committed).
DROP TRIGGER IF EXISTS trg_ops_treatment_course_conservation ON treatment_courses;
CREATE CONSTRAINT TRIGGER trg_ops_treatment_course_conservation
  AFTER UPDATE OF completed_session_count, planned_sessions
  ON treatment_courses
  DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW
  EXECUTE FUNCTION ops_treatment_course_conservation_guard();

-- Marker for disposable apply idempotency.
CREATE TABLE IF NOT EXISTS ops_treatment_courses_schema_marker (
  id SMALLINT PRIMARY KEY CHECK (id = 1),
  applied_at_utc TIMESTAMPTZ NOT NULL,
  schema_label TEXT NOT NULL DEFAULT 'treatment_courses_r2_v1'
);

INSERT INTO ops_treatment_courses_schema_marker (id, applied_at_utc)
VALUES (1, NOW())
ON CONFLICT (id) DO NOTHING;

-- PROPOSED disposable ops DDL for Task 34 R2 dashboard (online review + notifications).
-- NOT an official Alembic revision. Apply only under CLINIC_OPS_SCHEMA_MODE=disposable.

ALTER TABLE staff_profiles ADD COLUMN IF NOT EXISTS job_title text;

CREATE TABLE IF NOT EXISTS online_booking_reviews (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  appointment_id UUID NOT NULL,
  reviewed_by_user_id UUID NOT NULL,
  reviewed_at_utc TIMESTAMPTZ NOT NULL,
  note TEXT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, appointment_id),
  FOREIGN KEY (tenant_id, appointment_id)
    REFERENCES appointments(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, reviewed_by_user_id)
    REFERENCES user_accounts(tenant_id, id) MATCH FULL
);

CREATE TABLE IF NOT EXISTS clinic_staff_notifications (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  notification_kind VARCHAR(64) NOT NULL,
  title TEXT NOT NULL,
  body TEXT NULL,
  related_appointment_id UUID NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  FOREIGN KEY (tenant_id, related_appointment_id)
    REFERENCES appointments(tenant_id, id) MATCH SIMPLE
);

CREATE TABLE IF NOT EXISTS clinic_notification_reads (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  notification_id UUID NOT NULL,
  reader_user_id UUID NOT NULL,
  read_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, notification_id, reader_user_id),
  FOREIGN KEY (tenant_id, notification_id)
    REFERENCES clinic_staff_notifications(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, reader_user_id)
    REFERENCES user_accounts(tenant_id, id) MATCH FULL
);

CREATE TABLE IF NOT EXISTS ops_dashboard_r2_schema_marker (
  label TEXT PRIMARY KEY,
  applied_at_utc TIMESTAMPTZ NOT NULL
);

INSERT INTO ops_dashboard_r2_schema_marker (label, applied_at_utc)
VALUES ('dashboard_r2_v1', NOW())
ON CONFLICT (label) DO NOTHING;

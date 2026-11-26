CREATE TABLE patient_operational_notes (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  patient_id UUID NOT NULL,
  department_id UUID NULL,
  service_id UUID NULL,
  body VARCHAR(2000) NOT NULL CHECK (length(btrim(body)) > 0),
  supersedes_note_id UUID NULL,
  created_by_user_id UUID NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, patient_id, id),
  UNIQUE (tenant_id, supersedes_note_id),
  FOREIGN KEY (tenant_id, patient_id) REFERENCES patient_profiles(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, patient_id, supersedes_note_id) REFERENCES patient_operational_notes(tenant_id, patient_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, department_id) REFERENCES departments(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, service_id) REFERENCES services(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, created_by_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL,
  CHECK (supersedes_note_id IS NULL OR supersedes_note_id <> id)
);

CREATE TABLE patient_note_actions (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  note_id UUID NOT NULL,
  action_kind VARCHAR(16) NOT NULL CHECK (action_kind IN ('PIN', 'UNPIN', 'RETRACT')),
  reason VARCHAR(200) NOT NULL CHECK (length(btrim(reason)) > 0),
  operator_user_id UUID NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  FOREIGN KEY (tenant_id, note_id) REFERENCES patient_operational_notes(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, operator_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL
);

CREATE TABLE staff_tag_catalog (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  tag_code VARCHAR(64) NOT NULL,
  tag_name VARCHAR(100) NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at_utc TIMESTAMPTZ NOT NULL,
  updated_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, tag_code)
);

CREATE TABLE patient_staff_tags (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  patient_id UUID NOT NULL,
  tag_id UUID NOT NULL,
  department_id UUID NULL,
  service_id UUID NULL,
  created_by_user_id UUID NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  removed_by_user_id UUID NULL,
  removed_at_utc TIMESTAMPTZ NULL,
  removal_reason VARCHAR(200) NULL,
  UNIQUE (tenant_id, id),
  FOREIGN KEY (tenant_id, patient_id) REFERENCES patient_profiles(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, tag_id) REFERENCES staff_tag_catalog(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, department_id) REFERENCES departments(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, service_id) REFERENCES services(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, created_by_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, removed_by_user_id) REFERENCES user_accounts(tenant_id, id) MATCH SIMPLE,
  CHECK (
    (removed_at_utc IS NULL AND removed_by_user_id IS NULL AND removal_reason IS NULL)
    OR (removed_at_utc IS NOT NULL AND removed_at_utc >= created_at_utc AND removed_by_user_id IS NOT NULL
        AND removal_reason IS NOT NULL AND length(btrim(removal_reason)) > 0)
  )
);

CREATE UNIQUE INDEX patient_staff_tag_active_uq ON patient_staff_tags(tenant_id, patient_id, tag_id, department_id, service_id)
  NULLS NOT DISTINCT WHERE removed_at_utc IS NULL;

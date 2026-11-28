CREATE TABLE patient_operational_notes (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  patient_id UUID NOT NULL,
  body TEXT NOT NULL,
  is_pinned_alert BOOLEAN NOT NULL DEFAULT FALSE,
  created_by_user_id UUID NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  CONSTRAINT patient_operational_notes_tenant_id_id_uq UNIQUE (tenant_id, id),
  CONSTRAINT patient_operational_notes_patient_fk
    FOREIGN KEY (tenant_id, patient_id) REFERENCES patient_profiles (tenant_id, id) MATCH FULL
);

CREATE TABLE patient_staff_tags (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  patient_id UUID NOT NULL,
  tag_code VARCHAR(64) NOT NULL,
  created_by_user_id UUID NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  CONSTRAINT patient_staff_tags_tenant_id_id_uq UNIQUE (tenant_id, id),
  CONSTRAINT patient_staff_tags_uq UNIQUE (tenant_id, patient_id, tag_code),
  CONSTRAINT patient_staff_tags_patient_fk
    FOREIGN KEY (tenant_id, patient_id) REFERENCES patient_profiles (tenant_id, id) MATCH FULL
);

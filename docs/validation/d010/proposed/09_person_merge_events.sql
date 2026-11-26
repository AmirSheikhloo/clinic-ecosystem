CREATE TABLE person_merge_events (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  surviving_person_id UUID NOT NULL,
  retired_person_id UUID NOT NULL,
  reason VARCHAR(200) NOT NULL,
  operator_user_id UUID NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  CONSTRAINT person_merge_events_tenant_id_id_uq UNIQUE (tenant_id, id),
  CONSTRAINT person_merge_events_surviving_fk
    FOREIGN KEY (tenant_id, surviving_person_id) REFERENCES tenant_persons (tenant_id, id) MATCH FULL,
  CONSTRAINT person_merge_events_retired_fk
    FOREIGN KEY (tenant_id, retired_person_id) REFERENCES tenant_persons (tenant_id, id) MATCH FULL
);

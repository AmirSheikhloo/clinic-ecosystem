CREATE TABLE person_merge_events (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  surviving_person_id UUID NOT NULL,
  retired_person_id UUID NOT NULL,
  reason VARCHAR(200) NOT NULL CHECK (length(btrim(reason)) > 0),
  operator_user_id UUID NOT NULL,
  correlation_id UUID NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, retired_person_id),
  FOREIGN KEY (tenant_id, surviving_person_id) REFERENCES tenant_persons(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, retired_person_id) REFERENCES tenant_persons(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, operator_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL,
  CHECK (surviving_person_id <> retired_person_id)
);

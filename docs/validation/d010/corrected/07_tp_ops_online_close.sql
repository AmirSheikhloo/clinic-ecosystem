CREATE TABLE online_availability_closures (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  service_id UUID NULL,
  resource_id UUID NULL,
  closure_date DATE NOT NULL, -- Tehran calendar date as DATE (business date)
  starts_at_utc TIMESTAMPTZ NOT NULL,
  ends_at_utc TIMESTAMPTZ NOT NULL,
  reason VARCHAR(200) NULL,
  created_by_user_id UUID NOT NULL,
  reopened_at_utc TIMESTAMPTZ NULL,
  reopened_by_user_id UUID NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  CONSTRAINT online_availability_closures_tenant_id_id_uq UNIQUE (tenant_id, id),
  CONSTRAINT online_availability_closures_range_chk CHECK (ends_at_utc > starts_at_utc),
  CONSTRAINT online_availability_closures_target_chk CHECK (
    service_id IS NOT NULL OR resource_id IS NOT NULL
  ),
  CONSTRAINT online_availability_closures_service_fk
    FOREIGN KEY (tenant_id, service_id) REFERENCES services (tenant_id, id) MATCH SIMPLE,
  CONSTRAINT online_availability_closures_resource_fk
    FOREIGN KEY (tenant_id, resource_id) REFERENCES bookable_resources (tenant_id, id) MATCH SIMPLE,
  CONSTRAINT online_availability_closures_created_by_fk
    FOREIGN KEY (tenant_id, created_by_user_id) REFERENCES user_accounts (tenant_id, id) MATCH FULL
);

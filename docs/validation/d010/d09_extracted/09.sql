CREATE TABLE service_availability_guards (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  service_id UUID NOT NULL,
  aggregate_version BIGINT NOT NULL CHECK (aggregate_version > 0),
  created_at_utc TIMESTAMPTZ NOT NULL,
  updated_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, service_id),
  FOREIGN KEY (tenant_id, service_id) REFERENCES services(tenant_id, id) MATCH FULL
);

CREATE TABLE online_availability_closures (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  service_id UUID NOT NULL,
  resource_id UUID NULL,
  closure_date DATE NOT NULL,
  starts_at_utc TIMESTAMPTZ NOT NULL,
  ends_at_utc TIMESTAMPTZ NOT NULL,
  reason VARCHAR(200) NOT NULL CHECK (length(btrim(reason)) > 0),
  created_by_user_id UUID NOT NULL,
  reopened_at_utc TIMESTAMPTZ NULL,
  reopened_by_user_id UUID NULL,
  reopen_reason VARCHAR(200) NULL,
  aggregate_version BIGINT NOT NULL CHECK (aggregate_version > 0),
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  FOREIGN KEY (tenant_id, service_id) REFERENCES services(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, resource_id) REFERENCES staff_practitioner_resources(tenant_id, bookable_resource_id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, created_by_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, reopened_by_user_id) REFERENCES user_accounts(tenant_id, id) MATCH SIMPLE,
  CHECK (ends_at_utc > starts_at_utc),
  CHECK (
    starts_at_utc >= (closure_date::timestamp AT TIME ZONE 'Asia/Tehran')
    AND ends_at_utc <= ((closure_date + 1)::timestamp AT TIME ZONE 'Asia/Tehran')
  ),
  CHECK (
    (reopened_at_utc IS NULL AND reopened_by_user_id IS NULL AND reopen_reason IS NULL)
    OR (reopened_at_utc IS NOT NULL AND reopened_at_utc >= created_at_utc AND reopened_by_user_id IS NOT NULL
        AND reopen_reason IS NOT NULL AND length(btrim(reopen_reason)) > 0)
  )
);

CREATE INDEX online_closure_active_idx ON online_availability_closures(tenant_id, service_id, starts_at_utc, ends_at_utc)
  WHERE reopened_at_utc IS NULL;

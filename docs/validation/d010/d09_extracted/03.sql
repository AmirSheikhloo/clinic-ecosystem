CREATE TABLE inventory_items (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  billable_item_id UUID NULL,
  item_code VARCHAR(64) NOT NULL,
  item_name VARCHAR(200) NOT NULL,
  unit_code VARCHAR(16) NOT NULL,
  quantity_scale SMALLINT NOT NULL CHECK (quantity_scale BETWEEN 0 AND 6),
  is_lot_tracked BOOLEAN NOT NULL,
  requires_expiry BOOLEAN NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  aggregate_version BIGINT NOT NULL CHECK (aggregate_version > 0),
  created_at_utc TIMESTAMPTZ NOT NULL,
  updated_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, id, quantity_scale),
  UNIQUE (tenant_id, id, is_lot_tracked, requires_expiry),
  UNIQUE (tenant_id, item_code),
  UNIQUE (tenant_id, billable_item_id),
  FOREIGN KEY (tenant_id, billable_item_id) REFERENCES billable_items(tenant_id, id) MATCH SIMPLE,
  CHECK (NOT requires_expiry OR is_lot_tracked)
);

CREATE TABLE inventory_lots (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  item_id UUID NOT NULL,
  lot_code VARCHAR(64) NOT NULL,
  is_lot_tracked BOOLEAN NOT NULL,
  requires_expiry BOOLEAN NOT NULL,
  expires_on DATE NULL,
  lot_status VARCHAR(24) NOT NULL CHECK (lot_status IN ('AVAILABLE', 'QUARANTINE', 'RECALLED', 'EXPIRED')),
  source_lot_id UUID NULL,
  received_at_utc TIMESTAMPTZ NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  updated_at_utc TIMESTAMPTZ NOT NULL,
  aggregate_version BIGINT NOT NULL CHECK (aggregate_version > 0),
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, item_id, id),
  UNIQUE (tenant_id, item_id, lot_code),
  FOREIGN KEY (tenant_id, item_id, is_lot_tracked, requires_expiry) REFERENCES inventory_items(tenant_id, id, is_lot_tracked, requires_expiry) MATCH FULL,
  FOREIGN KEY (tenant_id, item_id, source_lot_id) REFERENCES inventory_lots(tenant_id, item_id, id) MATCH SIMPLE,
  CHECK (source_lot_id IS NULL OR source_lot_id <> id),
  CHECK ((is_lot_tracked AND (NOT requires_expiry OR expires_on IS NOT NULL)) OR (NOT is_lot_tracked AND expires_on IS NULL)),
  CHECK (is_lot_tracked OR source_lot_id IS NULL OR lot_status IN ('QUARANTINE', 'RECALLED', 'EXPIRED'))
);
CREATE UNIQUE INDEX inventory_non_lot_single_bucket_uq ON inventory_lots(tenant_id, item_id)
  WHERE NOT is_lot_tracked AND source_lot_id IS NULL;

-- Every stocked quantity belongs to a lot/bucket; non-lot-tracked items use a single non-expiring origin bucket and linked
-- unavailable quarantine buckets; inspection/release transfers stock to the origin bucket.
-- No editable quantity_on_hand or quantity_reserved column exists.

CREATE TABLE stock_movements (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  item_id UUID NOT NULL,
  lot_id UUID NOT NULL,
  movement_kind VARCHAR(32) NOT NULL CHECK (movement_kind IN ('PURCHASE_RECEIPT', 'SERVICE_CONSUMPTION', 'SALE', 'RETURN', 'WRITE_OFF', 'ADJUSTMENT', 'TRANSFER_OUT', 'TRANSFER_IN')),
  quantity_delta BIGINT NOT NULL CHECK (quantity_delta <> 0),
  quantity_scale SMALLINT NOT NULL CHECK (quantity_scale BETWEEN 0 AND 6),
  appointment_id UUID NULL,
  service_record_id UUID NULL,
  invoice_id UUID NULL,
  invoice_line_id UUID NULL,
  original_movement_id UUID NULL,
  return_disposition VARCHAR(16) NULL,
  transfer_operation_id UUID NULL,
  bom_version VARCHAR(64) NULL,
  reason_code VARCHAR(64) NOT NULL,
  operator_user_id UUID NOT NULL,
  actor_type VARCHAR(32) NOT NULL CHECK (actor_type = 'STAFF_USER'),
  actor_id UUID NOT NULL,
  correlation_id UUID NOT NULL,
  occurred_at_utc TIMESTAMPTZ NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, item_id, id),
  FOREIGN KEY (tenant_id, item_id, quantity_scale) REFERENCES inventory_items(tenant_id, id, quantity_scale) MATCH FULL,
  FOREIGN KEY (tenant_id, item_id, lot_id) REFERENCES inventory_lots(tenant_id, item_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, appointment_id) REFERENCES appointments(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, service_record_id) REFERENCES service_records(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, invoice_id, invoice_line_id) REFERENCES invoice_lines(tenant_id, invoice_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, item_id, original_movement_id) REFERENCES stock_movements(tenant_id, item_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, operator_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL,
  CHECK (actor_id = operator_user_id),
  CHECK ((invoice_id IS NULL) = (invoice_line_id IS NULL)),
  CHECK (
    (movement_kind IN ('PURCHASE_RECEIPT', 'RETURN', 'TRANSFER_IN') AND quantity_delta > 0)
    OR (movement_kind IN ('SERVICE_CONSUMPTION', 'SALE', 'WRITE_OFF', 'TRANSFER_OUT') AND quantity_delta < 0)
    OR movement_kind = 'ADJUSTMENT'
  ),
  CHECK (movement_kind <> 'SERVICE_CONSUMPTION' OR (service_record_id IS NOT NULL AND bom_version IS NOT NULL)),
  CHECK (movement_kind <> 'SALE' OR invoice_line_id IS NOT NULL),
  CHECK (
    (movement_kind = 'RETURN' AND original_movement_id IS NOT NULL AND return_disposition IS NOT NULL AND return_disposition IN ('REUSABLE', 'QUARANTINE', 'WRITE_OFF'))
    OR (movement_kind <> 'RETURN' AND return_disposition IS NULL)
  ),
  CHECK ((movement_kind IN ('TRANSFER_OUT', 'TRANSFER_IN')) = (transfer_operation_id IS NOT NULL)),
  CHECK (original_movement_id IS NULL OR original_movement_id <> id)
);

CREATE TABLE inventory_lot_state_events (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  item_id UUID NOT NULL,
  lot_id UUID NOT NULL,
  old_status VARCHAR(24) NOT NULL CHECK (old_status IN ('AVAILABLE', 'QUARANTINE', 'RECALLED', 'EXPIRED')),
  new_status VARCHAR(24) NOT NULL CHECK (new_status IN ('AVAILABLE', 'QUARANTINE', 'RECALLED', 'EXPIRED')),
  reason_code VARCHAR(64) NOT NULL,
  operator_user_id UUID NOT NULL,
  occurred_at_utc TIMESTAMPTZ NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  FOREIGN KEY (tenant_id, item_id, lot_id) REFERENCES inventory_lots(tenant_id, item_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, operator_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL,
  CHECK (old_status <> new_status)
);

CREATE TABLE service_item_suggestions (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  service_id UUID NOT NULL,
  billable_item_id UUID NULL,
  inventory_item_id UUID NULL,
  default_quantity_scaled BIGINT NOT NULL CHECK (default_quantity_scaled > 0),
  quantity_scale SMALLINT NOT NULL CHECK (quantity_scale BETWEEN 0 AND 6),
  bom_version VARCHAR(64) NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  FOREIGN KEY (tenant_id, service_id) REFERENCES services(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, billable_item_id) REFERENCES billable_items(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, inventory_item_id, quantity_scale) REFERENCES inventory_items(tenant_id, id, quantity_scale) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, billable_item_id, quantity_scale) REFERENCES billable_items(tenant_id, id, quantity_scale) MATCH SIMPLE,
  CHECK ((billable_item_id IS NULL) <> (inventory_item_id IS NULL)),
  UNIQUE NULLS NOT DISTINCT (tenant_id, service_id, billable_item_id, inventory_item_id, bom_version)
);

CREATE INDEX inventory_fefo_idx ON inventory_lots(tenant_id, item_id, expires_on, received_at_utc, id)
  WHERE lot_status = 'AVAILABLE';
CREATE INDEX stock_movements_lot_idx ON stock_movements(tenant_id, item_id, lot_id, occurred_at_utc, id);
CREATE INDEX stock_movements_origin_idx ON stock_movements(tenant_id, original_movement_id);

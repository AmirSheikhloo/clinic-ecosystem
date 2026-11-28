CREATE TABLE inventory_items (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  item_code VARCHAR(64) NOT NULL,
  item_name VARCHAR(200) NOT NULL,
  unit_code VARCHAR(16) NOT NULL,
  is_stock_tracked BOOLEAN NOT NULL DEFAULT TRUE,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  default_sale_price_irr BIGINT NOT NULL DEFAULT 0,
  created_at_utc TIMESTAMPTZ NOT NULL,
  updated_at_utc TIMESTAMPTZ NOT NULL,
  CONSTRAINT inventory_items_tenant_id_id_uq UNIQUE (tenant_id, id),
  CONSTRAINT inventory_items_code_uq UNIQUE (tenant_id, item_code),
  CONSTRAINT inventory_items_price_chk CHECK (default_sale_price_irr >= 0)
);

CREATE TABLE inventory_lots (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  item_id UUID NOT NULL,
  lot_code VARCHAR(64) NOT NULL,
  expires_on DATE NULL,
  quantity_on_hand INT NOT NULL,
  quantity_reserved INT NOT NULL DEFAULT 0,
  lot_status VARCHAR(24) NOT NULL DEFAULT 'AVAILABLE',
  -- AVAILABLE | QUARANTINE | RECALLED | EXPIRED
  received_at_utc TIMESTAMPTZ NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  CONSTRAINT inventory_lots_tenant_id_id_uq UNIQUE (tenant_id, id),
  CONSTRAINT inventory_lots_item_fk
    FOREIGN KEY (tenant_id, item_id) REFERENCES inventory_items (tenant_id, id) MATCH FULL,
  CONSTRAINT inventory_lots_qty_chk CHECK (quantity_on_hand >= 0 AND quantity_reserved >= 0),
  CONSTRAINT inventory_lots_code_uq UNIQUE (tenant_id, item_id, lot_code)
);

CREATE TABLE stock_movements (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  item_id UUID NOT NULL,
  lot_id UUID NULL,
  movement_kind VARCHAR(32) NOT NULL,
  -- PURCHASE_RECEIPT | SERVICE_CONSUMPTION | SALE | RETURN | WRITE_OFF | ADJUSTMENT | QUARANTINE
  quantity_delta INT NOT NULL, -- signed; application enforces kind rules
  appointment_id UUID NULL,
  invoice_line_id UUID NULL,
  reason_code VARCHAR(64) NULL,
  operator_user_id UUID NOT NULL,
  occurred_at_utc TIMESTAMPTZ NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  CONSTRAINT stock_movements_tenant_id_id_uq UNIQUE (tenant_id, id),
  CONSTRAINT stock_movements_item_fk
    FOREIGN KEY (tenant_id, item_id) REFERENCES inventory_items (tenant_id, id) MATCH FULL,
  CONSTRAINT stock_movements_lot_fk
    FOREIGN KEY (tenant_id, lot_id) REFERENCES inventory_lots (tenant_id, id) MATCH SIMPLE,
  CONSTRAINT stock_movements_operator_fk
    FOREIGN KEY (tenant_id, operator_user_id) REFERENCES user_accounts (tenant_id, id) MATCH FULL
);

CREATE TABLE service_item_suggestions (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  service_id UUID NOT NULL,
  item_id UUID NOT NULL,
  default_quantity INT NOT NULL DEFAULT 1,
  bom_version VARCHAR(32) NOT NULL DEFAULT '1',
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at_utc TIMESTAMPTZ NOT NULL,
  CONSTRAINT service_item_suggestions_tenant_id_id_uq UNIQUE (tenant_id, id),
  CONSTRAINT service_item_suggestions_service_fk
    FOREIGN KEY (tenant_id, service_id) REFERENCES services (tenant_id, id) MATCH FULL,
  CONSTRAINT service_item_suggestions_item_fk
    FOREIGN KEY (tenant_id, item_id) REFERENCES inventory_items (tenant_id, id) MATCH FULL,
  CONSTRAINT service_item_suggestions_qty_chk CHECK (default_quantity > 0)
);


-- D010: deferred FK from ledger lines once inventory exists
DO $$
BEGIN
  IF to_regclass('public.invoice_lines') IS NOT NULL THEN
    ALTER TABLE invoice_lines
      ADD CONSTRAINT invoice_lines_inventory_item_fk
      FOREIGN KEY (tenant_id, inventory_item_id)
      REFERENCES inventory_items (tenant_id, id) MATCH SIMPLE;
  END IF;
END $$;

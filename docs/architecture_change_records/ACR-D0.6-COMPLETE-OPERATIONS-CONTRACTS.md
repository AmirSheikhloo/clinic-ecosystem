# ACR-D0.6 — Complete Operations Contracts (Task 30 / Task 28 continuation)

**Status:** PROPOSED — review candidate only. **Not approved. Do not land or execute Alembic revisions from this document.**  
**Branch tip at drafting:** `development/clinic-operations` @ `6232437a2bc3ff7f648e70a3880a663bfac6a25a` (and successors).  
**Purpose:** One unabridged, implementation-ready decision packet covering every remaining Category-C dependency required to finish the four clinic operations workspaces under Task 28 / D0.5.

---

## 0. Governance and classification legend

| Class | Meaning |
|-------|---------|
| **A** | Approved contract already present in schema/spec; missing or incomplete **implementation** only. |
| **B** | Approved capability that maps to an **already authorized** migration in Appendix E.2 (`TP0001`–`TP0007`). |
| **C** | Capability requires a **genuine new** schema/security/architecture decision and a **new** Tenant Plane revision **after** `TP0007`. |
| **D** | Blocked by missing external evidence (provider/legal/KMS production), not by missing DDL design. |

**Frozen lineage fact (authoritative):** Appendix E.2 of `docs/FINAL_MASTER_SPECIFICATION_v3.0.1_FINAL.txt` allocates **only** `TP0001`–`TP0007`. There are **no reserved official migration numbers** beyond `TP0007` in the frozen roadmap. Therefore this ACR proposes **logical packages** `TP-OPS-LEDGER`, `TP-OPS-INVENTORY`, `TP-OPS-WAITLIST`, `TP-OPS-ELIGIBILITY`, `TP-OPS-SCOPES`, `TP-OPS-ARRIVAL`, `TP-OPS-ONLINE-CLOSE`, `TP-OPS-NOTES` whose **official Alembic revision IDs must be assigned by Product Owner approval** before any file is added under `migrations/tenant_plane/versions/`.

**Do not invent official `tp0008+` numbers in the repository until explicitly approved.**

Money: integer IRR (`BIGINT`). Timestamps: `TIMESTAMPTZ` UTC. IDs: application UUIDv7. Tenant integrity: clauses 741–743. RLS: clause 746 three-policy pattern. Append-only audit: existing `audit_entries`.

---

## 1. Master classification (all Task 28 residual dependencies)

| # | Capability | Class | Spec / ACR refs | Current evidence |
|---|------------|-------|-----------------|------------------|
| 1 | Operational billing / ledger foundations | **C** | §50 clauses 692–739; money BIGINT in F.2 preamble | No CREATE TABLE for invoices in Appendix F; none in tp0001–7 |
| 2 | Combined reception invoices | **C** | 694–697, 704–705 | Same |
| 3–4 | Whole-invoice and line discounts (fixed/% ) | **C** | 698–701 | Same |
| 5–6 | Full/partial payments; balances & credits | **C** | 706–711 | Same |
| 7–8 | Post-payment adjustments; partial/full refunds | **C** | 696, 712–714 | Same |
| 9 | Billable items / service consumables (non-stock) | **C** | 694–697; §60 for stocked | Same |
| 10 | Optional inventory + FEFO movements | **C** | §60 clauses 824–827; ACR-v3-008 | Conceptual only; entitlement `MOD_INVENTORY` |
| 11 | Staff↔service eligibility / multi-skill | **C** | ACR-BETA02-001 §3.1 item 4; ACR-D0.4 row 6 | No link table; practitioners are `bookable_resources` |
| 12 | Physical arrival / waiting-room semantics | **A/C** | §50 726; appointment CHECK includes `CHECKED_IN` | **A:** status `CHECKED_IN` usable as arrival marker. **C:** dedicated `arrived_at_utc`, waiting-queue entity, wait-time derivation beyond scheduled start |
| 13 | Future appointment waitlist | **C** | Product D0.5; distinct from CHECKED_IN | No table |
| 14 | Authorized historical appointment entry | **A/C** | Audit `created_at_utc` vs scheduled occurrence | **A:** past `scheduled_*` + audit actor already. **C:** `historical_entry_reason`, `occurred_at_utc` distinct, reminder suppression flag |
| 15 | Temporary online availability closure | **C** | ONLINE capacity / holds in TP0005; product D0.5 | No closure table; ONLINE GiST EXCLUDE only |
| 16 | Scoped receptionist access | **C** | ACR-BETA02-001 §3.1 item 1 | No `role_permission_scopes` |
| 17 | Head receptionist supervision | **A** | Permissions model | Approximate via RECEPTIONIST + extra permissions; optional dedicated role code is product choice (**A** if permission-only) |
| 18 | Management audit access | **A** | `audit_entries` + permissions | Append-only store exists; filtered management UI/API incomplete (**implementation**) |
| 19 | Identity completion / correction / merge | **A/C** | §52 / F.2 identifiers; Clause 755 | **A:** encrypt/lookup on F.2. **C:** merge aliases / correction workflow tables if not expressible via audit+identifier rows alone |
| 20 | Patient notes, tags, operational alerts | **C** | ACR-BETA02-001 | No tables |
| 21 | Grouped reception atomic booking | **A** | Appointments UoW | Implemented; continue tests |
| 22 | Encrypted National ID / phone | **A** + **D** | F.2; Open Item 4–5 | Non-prod keys **A**; production KMS **D** |
| 23 | ONLINE vs MANUAL capacity | **A/B** | TP0005 GiST EXCLUDE | Implemented |
| 24 | Tariff preview (non-posted) | **A** | Catalog prices | Implemented; must not be labeled as posted invoice |

---

## 2. Package TP-OPS-LEDGER — Operational billing (Section 50)

### 2.1 Authoritative references

- Spec §50 clauses **692–739** (especially 694–714, 721, 733–734).
- ACR-v3-006 gateway/refund separation (clinic refunds only in Tenant Plane).
- Clause **741–746** tenant FK + RLS.
- Appendix F.2 preamble: money = `BIGINT` whole IRR; no DDL for ledger tables (gap → Class C).

### 2.2 Incompatibility / missing contract

Appendix E.2 ends at TP0007. Section 50 is normative for **behavior** but supplies **no** CREATE TABLE templates for invoices/receipts. Implementation cannot invent tables without an approved Tenant Plane revision.

### 2.3 Recommended resolution

Approve package **TP-OPS-LEDGER** as the first post-`TP0007` revision (official ID TBD). Ship draft→post invoices, lines with tariff snapshots, receipts, allocations, adjustments, refunds, human-readable numbers. Keep gateway verification stubs behind entitlement; do not claim live gateway (**Gate B**).

### 2.4 Proposed DDL (complete)

```sql
-- Logical package TP-OPS-LEDGER (official revision ID TBD after PO approval)
-- Apply AFTER tp0007. All statements under db_migrator ownership.

CREATE TABLE invoice_documents (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  invoice_number VARCHAR(32) NULL,
  status VARCHAR(16) NOT NULL,
  -- DRAFT | POSTED | VOIDED
  beneficiary_patient_id UUID NOT NULL,
  currency_code CHAR(3) NOT NULL DEFAULT 'IRR',
  issued_at_utc TIMESTAMPTZ NULL,
  posted_at_utc TIMESTAMPTZ NULL,
  voided_at_utc TIMESTAMPTZ NULL,
  reception_group_key VARCHAR(64) NULL,
  notes_internal VARCHAR(500) NULL,
  aggregate_version INT NOT NULL DEFAULT 1,
  created_at_utc TIMESTAMPTZ NOT NULL,
  updated_at_utc TIMESTAMPTZ NOT NULL,
  CONSTRAINT invoice_documents_status_chk CHECK (status IN ('DRAFT','POSTED','VOIDED')),
  CONSTRAINT invoice_documents_tenant_id_id_uq UNIQUE (tenant_id, id),
  CONSTRAINT invoice_documents_patient_fk
    FOREIGN KEY (tenant_id, beneficiary_patient_id)
    REFERENCES patient_profiles (tenant_id, id) MATCH SIMPLE,
  CONSTRAINT invoice_documents_number_uq UNIQUE (tenant_id, invoice_number)
);

CREATE TABLE invoice_lines (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  invoice_id UUID NOT NULL,
  line_no INT NOT NULL,
  appointment_id UUID NULL,
  service_id UUID NULL,
  inventory_item_id UUID NULL, -- nullable until inventory package; FK added when inventory lands OR deferred
  line_kind VARCHAR(24) NOT NULL, -- SERVICE | ITEM | ADJUSTMENT_PLACEHOLDER
  description_snapshot VARCHAR(200) NOT NULL,
  service_code_snapshot VARCHAR(64) NULL,
  quantity INT NOT NULL,
  unit_price_irr BIGINT NOT NULL,
  gross_service_amount BIGINT NOT NULL,
  discount_amount BIGINT NOT NULL DEFAULT 0,
  subsidy_amount BIGINT NOT NULL DEFAULT 0,
  rounding_reduction_amount BIGINT NOT NULL DEFAULT 0,
  rounding_surcharge_amount BIGINT NOT NULL DEFAULT 0,
  basic_insurance_expected_share BIGINT NOT NULL DEFAULT 0,
  supplementary_insurance_expected_share BIGINT NOT NULL DEFAULT 0,
  patient_payable_amount BIGINT NOT NULL,
  pricing_rule_version VARCHAR(64) NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  CONSTRAINT invoice_lines_tenant_id_id_uq UNIQUE (tenant_id, id),
  CONSTRAINT invoice_lines_invoice_fk
    FOREIGN KEY (tenant_id, invoice_id)
    REFERENCES invoice_documents (tenant_id, id) MATCH FULL,
  CONSTRAINT invoice_lines_appointment_fk
    FOREIGN KEY (tenant_id, appointment_id)
    REFERENCES appointments (tenant_id, id) MATCH SIMPLE,
  CONSTRAINT invoice_lines_service_fk
    FOREIGN KEY (tenant_id, service_id)
    REFERENCES services (tenant_id, id) MATCH SIMPLE,
  CONSTRAINT invoice_lines_qty_chk CHECK (quantity > 0),
  CONSTRAINT invoice_lines_money_nonneg_chk CHECK (
    unit_price_irr >= 0 AND gross_service_amount >= 0 AND discount_amount >= 0
    AND subsidy_amount >= 0 AND rounding_reduction_amount >= 0
    AND rounding_surcharge_amount >= 0 AND basic_insurance_expected_share >= 0
    AND supplementary_insurance_expected_share >= 0 AND patient_payable_amount >= 0
  ),
  CONSTRAINT invoice_lines_identity_chk CHECK (
    gross_service_amount - discount_amount - subsidy_amount - rounding_reduction_amount
      + rounding_surcharge_amount
    = basic_insurance_expected_share + supplementary_insurance_expected_share + patient_payable_amount
  ),
  CONSTRAINT invoice_lines_unique_line UNIQUE (tenant_id, invoice_id, line_no)
);

CREATE TABLE payment_receipts (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  receipt_number VARCHAR(32) NULL,
  amount_irr BIGINT NOT NULL,
  currency_code CHAR(3) NOT NULL DEFAULT 'IRR',
  payment_method VARCHAR(24) NOT NULL, -- CASH | POS | BANK_TRANSFER | ONLINE | OTHER
  occurred_at_utc TIMESTAMPTZ NOT NULL,
  operator_user_id UUID NOT NULL,
  payer_patient_id UUID NULL,
  shift_id UUID NULL,
  provider_reference VARCHAR(128) NULL,
  reconciliation_state VARCHAR(24) NOT NULL DEFAULT 'VERIFIED',
  -- VERIFIED | PENDING_RECONCILIATION (ONLINE only until Gate B)
  aggregate_version INT NOT NULL DEFAULT 1,
  created_at_utc TIMESTAMPTZ NOT NULL,
  CONSTRAINT payment_receipts_tenant_id_id_uq UNIQUE (tenant_id, id),
  CONSTRAINT payment_receipts_amount_chk CHECK (amount_irr > 0),
  CONSTRAINT payment_receipts_method_chk CHECK (payment_method IN ('CASH','POS','BANK_TRANSFER','ONLINE','OTHER')),
  CONSTRAINT payment_receipts_number_uq UNIQUE (tenant_id, receipt_number),
  CONSTRAINT payment_receipts_operator_fk
    FOREIGN KEY (tenant_id, operator_user_id)
    REFERENCES user_accounts (tenant_id, id) MATCH FULL,
  CONSTRAINT payment_receipts_patient_fk
    FOREIGN KEY (tenant_id, payer_patient_id)
    REFERENCES patient_profiles (tenant_id, id) MATCH SIMPLE
);

CREATE TABLE receipt_allocations (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  receipt_id UUID NOT NULL,
  invoice_id UUID NOT NULL,
  invoice_line_id UUID NULL,
  amount_irr BIGINT NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  CONSTRAINT receipt_allocations_tenant_id_id_uq UNIQUE (tenant_id, id),
  CONSTRAINT receipt_allocations_amount_chk CHECK (amount_irr > 0),
  CONSTRAINT receipt_allocations_receipt_fk
    FOREIGN KEY (tenant_id, receipt_id) REFERENCES payment_receipts (tenant_id, id) MATCH FULL,
  CONSTRAINT receipt_allocations_invoice_fk
    FOREIGN KEY (tenant_id, invoice_id) REFERENCES invoice_documents (tenant_id, id) MATCH FULL,
  CONSTRAINT receipt_allocations_line_fk
    FOREIGN KEY (tenant_id, invoice_line_id) REFERENCES invoice_lines (tenant_id, id) MATCH SIMPLE
);

CREATE TABLE patient_credits (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  patient_id UUID NOT NULL,
  source_receipt_id UUID NULL,
  remaining_irr BIGINT NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  CONSTRAINT patient_credits_tenant_id_id_uq UNIQUE (tenant_id, id),
  CONSTRAINT patient_credits_remaining_chk CHECK (remaining_irr >= 0),
  CONSTRAINT patient_credits_patient_fk
    FOREIGN KEY (tenant_id, patient_id) REFERENCES patient_profiles (tenant_id, id) MATCH FULL,
  CONSTRAINT patient_credits_receipt_fk
    FOREIGN KEY (tenant_id, source_receipt_id) REFERENCES payment_receipts (tenant_id, id) MATCH SIMPLE
);

CREATE TABLE financial_adjustments (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  invoice_id UUID NOT NULL,
  invoice_line_id UUID NULL,
  adjustment_kind VARCHAR(32) NOT NULL,
  -- POST_PAYMENT_DISCOUNT | CORRECTION | WRITE_OFF | OTHER
  amount_irr BIGINT NOT NULL,
  reason_code VARCHAR(64) NOT NULL,
  reason_text VARCHAR(500) NULL,
  operator_user_id UUID NOT NULL,
  occurred_at_utc TIMESTAMPTZ NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  CONSTRAINT financial_adjustments_tenant_id_id_uq UNIQUE (tenant_id, id),
  CONSTRAINT financial_adjustments_amount_chk CHECK (amount_irr > 0),
  CONSTRAINT financial_adjustments_invoice_fk
    FOREIGN KEY (tenant_id, invoice_id) REFERENCES invoice_documents (tenant_id, id) MATCH FULL,
  CONSTRAINT financial_adjustments_line_fk
    FOREIGN KEY (tenant_id, invoice_line_id) REFERENCES invoice_lines (tenant_id, id) MATCH SIMPLE,
  CONSTRAINT financial_adjustments_operator_fk
    FOREIGN KEY (tenant_id, operator_user_id) REFERENCES user_accounts (tenant_id, id) MATCH FULL
);

CREATE TABLE clinic_payment_refunds (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  refund_number VARCHAR(32) NULL,
  original_receipt_id UUID NOT NULL,
  amount_irr BIGINT NOT NULL,
  refund_method VARCHAR(24) NOT NULL,
  reason_code VARCHAR(64) NOT NULL,
  reason_text VARCHAR(500) NULL,
  operator_user_id UUID NOT NULL,
  occurred_at_utc TIMESTAMPTZ NOT NULL,
  reconciliation_state VARCHAR(24) NOT NULL DEFAULT 'VERIFIED',
  created_at_utc TIMESTAMPTZ NOT NULL,
  CONSTRAINT clinic_payment_refunds_tenant_id_id_uq UNIQUE (tenant_id, id),
  CONSTRAINT clinic_payment_refunds_amount_chk CHECK (amount_irr > 0),
  CONSTRAINT clinic_payment_refunds_number_uq UNIQUE (tenant_id, refund_number),
  CONSTRAINT clinic_payment_refunds_receipt_fk
    FOREIGN KEY (tenant_id, original_receipt_id) REFERENCES payment_receipts (tenant_id, id) MATCH FULL,
  CONSTRAINT clinic_payment_refunds_operator_fk
    FOREIGN KEY (tenant_id, operator_user_id) REFERENCES user_accounts (tenant_id, id) MATCH FULL
);

CREATE TABLE document_number_counters (
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  document_type VARCHAR(32) NOT NULL, -- INVOICE | RECEIPT | REFUND
  next_value BIGINT NOT NULL,
  PRIMARY KEY (tenant_id, document_type),
  CONSTRAINT document_number_counters_next_chk CHECK (next_value >= 1)
);

CREATE INDEX invoice_documents_tenant_patient_idx ON invoice_documents (tenant_id, beneficiary_patient_id, posted_at_utc DESC);
CREATE INDEX invoice_lines_tenant_appointment_idx ON invoice_lines (tenant_id, appointment_id);
CREATE INDEX payment_receipts_tenant_occurred_idx ON payment_receipts (tenant_id, occurred_at_utc DESC);
CREATE INDEX receipt_allocations_tenant_invoice_idx ON receipt_allocations (tenant_id, invoice_id);
CREATE INDEX clinic_payment_refunds_tenant_receipt_idx ON clinic_payment_refunds (tenant_id, original_receipt_id);
```

### 2.5 RLS and grants

For **each** new tenant-owned table above, apply clause 746 pattern exactly:

1. `ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY`
2. Permissive `tenant_runtime_base` TO `db_app_runtime`
3. Restrictive `tenant_isolation_guard` TO `db_app_runtime` on `app.current_tenant_id`
4. Permissive `tenant_migrator_maintenance` TO `db_migrator`
5. Grants: `SELECT, INSERT, UPDATE` to `db_app_runtime` as required; **no UPDATE/DELETE** on `payment_receipts`, `clinic_payment_refunds`, `receipt_allocations`, `financial_adjustments` after insert (append-only via revoke UPDATE/DELETE or trigger). Prefer: revoke UPDATE/DELETE for runtime on immutable tables; draft invoices allow UPDATE while `status='DRAFT'` enforced in application + optional trigger.

### 2.6 Permissions

| Code | Purpose |
|------|---------|
| `FINANCE_INVOICE_VIEW` | View invoices/derived balances |
| `FINANCE_INVOICE_DRAFT` | Create/edit draft |
| `FINANCE_INVOICE_POST` | Post draft |
| `FINANCE_RECEIPT_RECORD` | Record verified receipt |
| `FINANCE_DISCOUNT_APPLY` | Apply discount (draft or authorized adjustment) |
| `FINANCE_ADJUST_POSTED` | Post-payment adjustment |
| `FINANCE_REFUND_PARTIAL` | Partial refund |
| `FINANCE_REFUND_FULL` | Full refund |
| `FINANCE_EXPORT` | Export/print |

Seed into `permission_catalog_snapshots`. Receptionists may receive a **subset** via manager assignment; thresholds (max % / max IRR) are application policy rows (optional later table `finance_authority_limits`) — do not invent silent defaults beyond “permission grants the action; amount limits require explicit config rows.”

### 2.7 State transitions

- Invoice: `DRAFT` → `POSTED` (immutable snapshots); `DRAFT` → `VOIDED`; `POSTED` → never edit lines; corrections via `financial_adjustments` / credit / refund.
- Receipt: insert-only when verified; allocations insert-only; reversals = new compensating allocation rows (future) or explicit adjustment.
- Refund: insert-only; cumulative `SUM(refunds.amount)` ≤ receipt amount − prior refunds (enforced in transaction with `SELECT … FOR UPDATE` on receipt).

### 2.8 Transaction boundaries / concurrency / idempotency

- Post invoice, record receipt, refund: single UoW; lock invoice/receipt rows `FOR UPDATE` in deterministic ID order.
- Idempotency: existing `idempotency_records` keyed by operation (`finance.invoice.post`, `finance.receipt.record`, `finance.refund.create`).
- Human numbers: allocate via `UPDATE document_number_counters SET next_value = next_value + 1 … RETURNING` inside the same transaction.
- Outbox: emit `InvoicePosted`, `PaymentReceiptRecorded`, `ClinicRefundRecorded` for sync compatibility (payload without PII secrets).

### 2.9 Derived financial statuses (read model)

Compute, never store as mutable dropdown: `UNPAID`, `PARTIALLY_PAID`, `PAID`, `CREDIT`, `PARTIALLY_REFUNDED`, `FULLY_REFUNDED`, `OUTSTANDING` from posted lines − allocations − adjustments + credits − refunds.

### 2.10 API sketch

- `POST /api/v1/finance/invoices` (draft)
- `POST /api/v1/finance/invoices/{id}/post`
- `POST /api/v1/finance/receipts`
- `POST /api/v1/finance/refunds`
- `GET /api/v1/finance/patients/{id}/ledger`

### 2.11 Acceptance tests (minimum)

Map to Task 28 scenarios 67–86: combined draft; post; item qty; fixed/% whole and line discounts; unauthorized discount 403; integer rounding; verified/partial payment; outstanding; post-payment adjustment; partial/full refund; concurrent refund cap; cancel ≠ refund; immutable history; derived statuses; visibility.

### 2.12 Approval required

PO must: (1) approve package DDL, (2) assign official TP revision ID, (3) approve permission codes, (4) confirm no live gateway in this increment (Gate B remains open).

---

## 3. Package TP-OPS-INVENTORY — Optional FEFO inventory

### 3.1 References

- §60 clauses **824–827**; ACR-v3-008; entitlement `MOD_INVENTORY`.
- Clinics without entitlement: non-stock billable items via ledger `line_kind=ITEM` without lot movements.

### 3.2 DDL

```sql
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
```

FEFO selection: `ORDER BY expires_on ASC NULLS LAST, received_at_utc ASC, id ASC` where `lot_status='AVAILABLE'` and (`expires_on` IS NULL OR `expires_on >= CURRENT_DATE` in Tehran date policy as approved). Future booking **must not** deduct stock (824–826). Consumption at completion trigger inside appointment complete UoW when entitlement enabled.

RLS/grants: same clause 746; `stock_movements` append-only (no UPDATE/DELETE for runtime).

Permissions: `INVENTORY_VIEW`, `INVENTORY_RECEIVE`, `INVENTORY_CONSUME`, `INVENTORY_ADJUST`, `INVENTORY_CONFIG`.

**Approval:** package + entitlement gate + official revision ID. Dependency: after ledger if invoice_line FK required; otherwise inventory may land before ledger with nullable invoice_line_id.

---

## 4. Package TP-OPS-WAITLIST — Future-slot waitlist

Distinct from `CHECKED_IN` physical presence.

```sql
CREATE TABLE appointment_waitlist_entries (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  patient_id UUID NOT NULL,
  service_id UUID NOT NULL,
  preferred_resource_id UUID NULL,
  preferred_start_utc TIMESTAMPTZ NULL,
  preferred_end_utc TIMESTAMPTZ NULL,
  priority INT NOT NULL DEFAULT 100,
  status VARCHAR(24) NOT NULL DEFAULT 'OPEN',
  -- OPEN | CONTACTED | CONVERTED | CANCELLED | EXPIRED
  contact_state VARCHAR(24) NOT NULL DEFAULT 'NONE',
  converted_appointment_id UUID NULL,
  notes VARCHAR(500) NULL,
  created_by_user_id UUID NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  updated_at_utc TIMESTAMPTZ NOT NULL,
  CONSTRAINT appointment_waitlist_entries_tenant_id_id_uq UNIQUE (tenant_id, id),
  CONSTRAINT appointment_waitlist_entries_status_chk CHECK (status IN ('OPEN','CONTACTED','CONVERTED','CANCELLED','EXPIRED')),
  CONSTRAINT appointment_waitlist_entries_patient_fk
    FOREIGN KEY (tenant_id, patient_id) REFERENCES patient_profiles (tenant_id, id) MATCH FULL,
  CONSTRAINT appointment_waitlist_entries_service_fk
    FOREIGN KEY (tenant_id, service_id) REFERENCES services (tenant_id, id) MATCH FULL,
  CONSTRAINT appointment_waitlist_entries_resource_fk
    FOREIGN KEY (tenant_id, preferred_resource_id) REFERENCES bookable_resources (tenant_id, id) MATCH SIMPLE,
  CONSTRAINT appointment_waitlist_entries_converted_fk
    FOREIGN KEY (tenant_id, converted_appointment_id) REFERENCES appointments (tenant_id, id) MATCH SIMPLE
);
```

Permissions: `WAITLIST_VIEW`, `WAITLIST_MANAGE`. Conversion creates real appointment via existing schedule command inside one UoW.

---

## 5. Package TP-OPS-ELIGIBILITY — Staff↔service links

```sql
CREATE TABLE staff_service_links (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  staff_profile_id UUID NOT NULL,
  service_id UUID NOT NULL,
  bookable_resource_id UUID NOT NULL, -- practitioner resource representing this staff for scheduling
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at_utc TIMESTAMPTZ NOT NULL,
  CONSTRAINT staff_service_links_tenant_id_id_uq UNIQUE (tenant_id, id),
  CONSTRAINT staff_service_links_uq UNIQUE (tenant_id, staff_profile_id, service_id, bookable_resource_id),
  CONSTRAINT staff_service_links_staff_fk
    FOREIGN KEY (tenant_id, staff_profile_id) REFERENCES staff_profiles (tenant_id, id) MATCH FULL,
  CONSTRAINT staff_service_links_service_fk
    FOREIGN KEY (tenant_id, service_id) REFERENCES services (tenant_id, id) MATCH FULL,
  CONSTRAINT staff_service_links_resource_fk
    FOREIGN KEY (tenant_id, bookable_resource_id) REFERENCES bookable_resources (tenant_id, id) MATCH FULL
);
```

API: filter eligible practitioners by `service_id`. Changing service clears incompatible selections (application). Until approved, reception continues using `service_resource_requirements` + active practitioner resources (**PARTIAL** product behavior).

---

## 6. Package TP-OPS-SCOPES — Scoped receptionist enforcement

```sql
CREATE TABLE role_permission_scopes (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  role_id UUID NOT NULL,
  permission_code VARCHAR(64) NOT NULL,
  scope_kind VARCHAR(32) NOT NULL, -- DEPARTMENT | SERVICE | PROVIDER_RESOURCE | ALL
  scope_ref UUID NULL, -- NULL only when scope_kind='ALL'
  created_at_utc TIMESTAMPTZ NOT NULL,
  CONSTRAINT role_permission_scopes_tenant_id_id_uq UNIQUE (tenant_id, id),
  CONSTRAINT role_permission_scopes_role_fk
    FOREIGN KEY (tenant_id, role_id) REFERENCES tenant_roles (tenant_id, id) MATCH FULL,
  CONSTRAINT role_permission_scopes_kind_chk CHECK (scope_kind IN ('DEPARTMENT','SERVICE','PROVIDER_RESOURCE','ALL')),
  CONSTRAINT role_permission_scopes_ref_chk CHECK (
    (scope_kind = 'ALL' AND scope_ref IS NULL) OR (scope_kind <> 'ALL' AND scope_ref IS NOT NULL)
  )
);
CREATE INDEX role_permission_scopes_lookup_idx
  ON role_permission_scopes (tenant_id, role_id, permission_code);
```

**Enforcement:** permission resolver intersects scopes server-side for dashboard counts, search, lists, details, conflicts, mutations, history, finance visibility. Fail-closed if permission present without matching scope row (except explicit `ALL`). No client-only filters.

Note: `DEPARTMENT` requires a department catalog table if not present — if absent, approve either (a) add `departments` table in same package or (b) defer DEPARTMENT kind and ship SERVICE + PROVIDER_RESOURCE only.

---

## 7. Package TP-OPS-ARRIVAL — Physical waiting semantics

### 7.1 Minimal additive columns (preferred)

```sql
ALTER TABLE appointments
  ADD COLUMN arrived_at_utc TIMESTAMPTZ NULL,
  ADD COLUMN historical_entry_reason VARCHAR(200) NULL,
  ADD COLUMN suppress_reminders BOOLEAN NOT NULL DEFAULT FALSE;

ALTER TABLE appointments
  ADD CONSTRAINT appointments_arrived_chk CHECK (
    (status <> 'CHECKED_IN') OR (arrived_at_utc IS NOT NULL)
  );
```

Check-in command sets `arrived_at_utc = now()` (or explicit). Waiting time = `now() - arrived_at_utc`. Do **not** infer completion from elapsed schedule (existing rule).

Historical entry: set `historical_entry_reason`, `suppress_reminders=TRUE`, schedule in the past, status in allowed historical set; `created_at_utc` remains recording time.

### 7.2 Honesty until approved

UI must label `CHECKED_IN` as “حضور ثبت‌شده”, not claim a complete physical waiting-room product with queue ordering beyond appointment status filters.

---

## 8. Package TP-OPS-ONLINE-CLOSE — Temporary online closure

```sql
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
  CONSTRAINT online_availability_closures_service_fk
    FOREIGN KEY (tenant_id, service_id) REFERENCES services (tenant_id, id) MATCH SIMPLE,
  CONSTRAINT online_availability_closures_resource_fk
    FOREIGN KEY (tenant_id, resource_id) REFERENCES bookable_resources (tenant_id, id) MATCH SIMPLE
);
```

ONLINE schedule path must reject new online bookings overlapping an active closure; MANUAL unaffected; existing confirmed ONLINE preserved; active holds follow existing hold expiry rules with closure check on convert.

---

## 9. Package TP-OPS-NOTES — Notes, tags, alerts

```sql
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
```

No clinical diagnosis content. Staff-only.

---

## 10. Identity completion / correction / merge

**A (now):** F.2 `person_identifiers` / `person_phones`; Clause 755; encrypted lookup POST bodies; duplicate unique HMAC.

**C (if merge required beyond alias rows):**

```sql
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
```

Non-destructive: retire person retains historical FKs via immutable aliases / redirect; no silent phone-based merge.

Production crypto readiness remains **D** (Open Items 4–5 / Gate B KMS).

---

## 11. Recommended migration dependency order (logical)

1. **TP-OPS-ELIGIBILITY** (unblocks reception practitioner filter)
2. **TP-OPS-ARRIVAL** (ALTER appointments — unblocks waiting metrics honesty)
3. **TP-OPS-SCOPES** (+ optional departments)
4. **TP-OPS-NOTES**
5. **TP-OPS-WAITLIST**
6. **TP-OPS-ONLINE-CLOSE**
7. **TP-OPS-LEDGER**
8. **TP-OPS-INVENTORY** (after or with ledger; add FK from `invoice_lines.inventory_item_id` when both exist)
9. Identity merge package if required

Each revision must include: DDL, RLS policies, grants, permission catalog rows, upgrade-only Expand-and-Contract notes, integration tests.

---

## 12. Compatibility / sync / outbox

- Expand-and-Contract: additive tables/columns only; no rewrite of `appointments` PK.
- Local Hub: same Tenant Plane revisions when package approved for hub authority domains (reception/finance local).
- Outbox event types listed per package; no PII ciphertext in outbox payloads.
- Idempotency fingerprints include tenant + operation + business key.

---

## 13. Explicit Product Owner approval checklist

Approve or reject **each**:

- [ ] TP-OPS-LEDGER DDL + permissions + append-only rules  
- [ ] TP-OPS-INVENTORY DDL + FEFO + entitlement behavior  
- [ ] TP-OPS-WAITLIST  
- [ ] TP-OPS-ELIGIBILITY  
- [ ] TP-OPS-SCOPES (and DEPARTMENT kind decision)  
- [ ] TP-OPS-ARRIVAL column set  
- [ ] TP-OPS-ONLINE-CLOSE  
- [ ] TP-OPS-NOTES  
- [ ] person_merge_events (if required now)  
- [ ] Official Alembic revision ID assignment for each approved package  
- [ ] Confirm non-production `CLINIC_PII_*` policy for demo/test only  

**Until boxes are checked, repository must not contain Alembic files for these packages.**

---

## 14. Continuation plan after approval

1. Land approved packages in dependency order with PG15 Testcontainers.  
2. Wire reception invoice post + discounts + refunds.  
3. Wire inventory suggestions without auto-consume on future bookings.  
4. Enforce scopes on all Task 28 read/write paths.  
5. Expand demo profile with finance/inventory scenarios only for implemented modules.  
6. Re-run full 120-scenario matrix + Playwright + performance.

---

## 15. Related documents

- `docs/product/CLINIC_PRODUCT_RECEPTION_REQUIREMENTS_D0.5.md`  
- `docs/architecture_change_records/ACR-D0.5-FINANCE-INVENTORY-WAITLIST.md` (superseded in depth by this ACR; retained for history)  
- `docs/architecture_change_records/ACR-BETA02-001.md`  
- `docs/FINAL_MASTER_SPECIFICATION_v3.0.1_FINAL.txt` §50, §60, Appendix E.2, F.2–F.6  

END OF ACR-D0.6 (PROPOSED)

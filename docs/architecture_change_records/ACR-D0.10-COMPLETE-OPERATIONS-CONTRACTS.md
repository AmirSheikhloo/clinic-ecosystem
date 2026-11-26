# ACR-D0.10 — Complete Operations Contracts (Execution-Validated)

**Status:** PROPOSED — execution-validated against disposable PostgreSQL 15. **Not approved for Alembic landing.**  
**Supersedes for decision purposes:** ACR-D0.6 (PROPOSED).  
**Baseline tip:** `8309f2a044e944123ddb1f49a8bad1255e4ce2e0` (`development/clinic-operations`).  
**Validation artifacts:** `docs/validation/d010/` (proposed SQL, corrected SQL, RLS helper, evidence).  
**Harness:** `scripts/validate_ops_contracts_d010.py`  
**Evidence generated:** `2026-11-26T22:33:48.946519+00:00`  
**Cases:** 25 passed / 0 failed.

---

## 0. Source control note (ACR-D0.9)

Task 33 referenced an attached **ACR-D0.9** with findings **D09-01 through D09-14** and Appendix D.3. That document was **not present** in the agent VM (uploads, stores, GitHub, conversation transcript). Gmail MCP authentication was declined by the operator.

Therefore:

1. Disposable Appendix-D.3-style execution was performed against **ACR-D0.6** proposed SQL (last complete ops contracts on disk).
2. Finding IDs **D09-01…D09-14** below are **provisional** labels for defects discovered and corrected during that execution.
3. When the authoritative ACR-D0.9 text is supplied, remap Gemini findings 1:1 onto this register without changing the corrected DDL unless a genuine conflict appears.

---

## 1. Migration lineage reconciliation

| Fact | Evidence |
|------|----------|
| Official Tenant Plane revisions on disk | `tp0001` … `tp0007` only |
| Alembic head after upgrade | `tp0007` |
| Appendix E.2 frozen allocation | TP0001–TP0007 only — **no** reserved official `tp0008+` |
| Speculative migrations landed? | **No** — corrected SQL lives under `docs/validation/d010/corrected/` only |
| Logical packages awaiting PO ID assignment | TP-OPS-ELIGIBILITY → ARRIVAL → SCOPES (+ departments) → NOTES → WAITLIST → ONLINE-CLOSE → LEDGER → INVENTORY → person_merge_events |

**Governance rule preserved:** do not invent official `tp0008+` files under `migrations/tenant_plane/versions/` until PO assigns revision IDs and checks the approval boxes in §13.

---

## 2. Classification legend (unchanged)

| Class | Meaning |
|-------|---------|
| **A** | Approved contract already present; implementation only |
| **B** | Maps to authorized TP0001–TP0007 |
| **C** | Requires new Tenant Plane revision after TP0007 |
| **D** | External/KMS/provider gate |

Money: `BIGINT` IRR. Timestamps: `TIMESTAMPTZ` UTC. Compound tenant FKs: clause **741–743**. RLS: clause **746** / Appendix F.6 three-policy pattern with names **`tenant_runtime_base`**, **`tenant_runtime_guard`**, **`tenant_migrator_maintenance`** (must match `tp0007`).

---

## 3. Finding register (provisional D09-01…D09-14)

### D09-01 — ACR-D0.9 source text unavailable in execution environment
- **Severity:** BLOCKER_FOR_1TO1_MAP
- **Status:** SOURCE_UNAVAILABLE
- **Evidence:** Task 33 claimed attached ACR-D0.9; file absent; Gmail auth declined.
- **Correction:** Proceeded with ACR-D0.6 proposed SQL + disposable evidence; remap when D0.9 arrives.
### D09-02 — RLS policy naming drift vs tp0007 / Appendix F.6
- **Severity:** HIGH
- **Status:** RESOLVED
- **Evidence:** ACR-D0.6 prose used tenant_isolation_guard; live tp0007 uses tenant_runtime_guard.
- **Correction:** D0.10 + rls_clause746.sql use tenant_runtime_guard.
### D09-03 — Mandatory composite FKs used MATCH SIMPLE
- **Severity:** HIGH
- **Status:** RESOLVED
- **Evidence:** invoice_documents.beneficiary_patient_id is NOT NULL but FK was MATCH SIMPLE (clause 743).
- **Correction:** Corrected to MATCH FULL in corrected/01_tp_ops_ledger.sql.
### D09-04 — RLS/grants specified only in prose, not executable SQL
- **Severity:** HIGH
- **Status:** RESOLVED
- **Evidence:** Proposed packages lacked ENABLE/FORCE RLS and grants; runtime roles untested.
- **Correction:** Added docs/validation/d010/rls_clause746.sql and executed against db_app_runtime.
### D09-05 — Append-only finance tables lacked revoke/trigger evidence
- **Severity:** HIGH
- **Status:** RESOLVED
- **Evidence:** payment_receipts UPDATE succeeded under prose-only grants.
- **Correction:** Append-only via BEFORE UPDATE/DELETE reject triggers (UPDATE kept for FOR UPDATE locks); case finance_receipt_append_only.
### D09-06 — Refund cumulative cap not enforced in DDL
- **Severity:** HIGH
- **Status:** RESOLVED
- **Evidence:** Over-refund inserts possible without app FOR UPDATE discipline.
- **Correction:** Added clinic_refund_amount_within_receipt trigger; verified.
### D09-07 — inventory_item_id FK never closed after inventory package
- **Severity:** MEDIUM
- **Status:** RESOLVED
- **Evidence:** Ledger left inventory_item_id dangling without deferred FK step.
- **Correction:** Corrected inventory package adds MATCH SIMPLE FK when invoice_lines exists.
### D09-08 — DEPARTMENT scope_kind without departments catalog
- **Severity:** HIGH
- **Status:** RESOLVED
- **Evidence:** Scopes DDL allowed DEPARTMENT without referent table.
- **Correction:** Added departments + integrity trigger in corrected scopes package.
### D09-09 — Arrival CHECK unsafe for Expand-and-Contract upgrades
- **Severity:** MEDIUM
- **Status:** RESOLVED
- **Evidence:** Immediate CHECK on CHECKED_IN∧arrived_at would fail populated upgrades.
- **Correction:** Constraint added NOT VALID; VALIDATE after backfill demonstrated.
### D09-10 — Online closures allowed null service and resource (no target)
- **Severity:** MEDIUM
- **Status:** RESOLVED
- **Evidence:** Clinic-wide vs targeted closure ambiguous; empty target accepted.
- **Correction:** Added online_availability_closures_target_chk + created_by FK.
### D09-11 — Waitlist/notes missing created_by composite FKs
- **Severity:** MEDIUM
- **Status:** RESOLVED
- **Evidence:** Operator attribution columns lacked tenant-scoped FKs.
- **Correction:** Added MATCH FULL FKs to user_accounts.
### D09-12 — Official tp0008+ must not be invented
- **Severity:** GOVERNANCE
- **Status:** RESOLVED
- **Evidence:** Lineage audit: only tp0001–tp0007 on disk; Appendix E.2 ends at TP0007.
- **Correction:** Packages remain logical TP-OPS-*; no Alembic files landed.
### D09-13 — Financial identity CHECK + derived balance reconciliation
- **Severity:** HIGH
- **Status:** RESOLVED
- **Evidence:** Executable proof of identity CHECK and receipt allocation equality.
- **Correction:** Cases finance_line_* and finance_reconciliation_paid.
### D09-14 — Practitioner eligibility + FEFO inventory + lifecycle arrival
- **Severity:** HIGH
- **Status:** RESOLVED
- **Evidence:** Behavioral cases for staff_service_links, FEFO order, CHECKED_IN+arrived_at.
- **Correction:** See evidence cases list.


---

## 4. Execution evidence (disposable PG15)

PostgreSQL **15.20**. Runtime role **`db_app_runtime`** via `tp_app_login`. Migrator **`db_migrator`** via `tp_migrator_login`. No preview DB mutation. No live payment providers. Synthetic UUIDv7 fixtures only.

### 4.1 Cases

- `PASS` lineage_head_tp0007 — tp0007
- `PASS` postgres_15 — 15.20 (Debian 15.20-1.pgdg13+1)
- `PASS` corrected_packages_apply
- `PASS` rls_apply
- `PASS` rls_same_tenant_sees_invoice
- `PASS` rls_cross_tenant_hidden
- `PASS` rls_no_tenant_fail_closed
- `PASS` finance_line_identity_ok
- `PASS` finance_line_identity_rejects_mismatch
- `PASS` finance_reconciliation_paid
- `PASS` finance_refund_cap_enforced
- `PASS` finance_receipt_append_only
- `PASS` inventory_fefo_picks_earliest_expiry
- `PASS` inventory_consume_updates_lot
- `PASS` inventory_no_future_booking_deduction
- `PASS` eligibility_staff_service_link
- `PASS` lifecycle_checked_in_sets_arrived_at
- `PASS` arrival_constraint_validates_after_backfill
- `PASS` scopes_ref_integrity
- `PASS` waitlist_insert
- `PASS` notes_insert
- `PASS` online_close_insert
- `PASS` online_close_requires_target
- `PASS` document_number_monotonic
- `PASS` rls_policy_names_match_tp0007 — {'tenant_runtime_guard', 'tenant_migrator_maintenance', 'tenant_runtime_base'}

### 4.2 Proven behaviors

- Cross-tenant RLS fail-closed on `invoice_documents`
- Invoice line financial identity CHECK accept/reject
- Receipt allocation reconciles to patient payable
- Refund cumulative cap trigger blocks over-refund
- Append-only reject triggers on finance/inventory movement tables (UPDATE retained for `FOR UPDATE` locks)
- FEFO lot selection (`expires_on ASC NULLS LAST`)
- Staff↔service eligibility insert
- `CHECKED_IN` + `arrived_at_utc`; arrival CHECK `NOT VALID` then `VALIDATE`
- Scope referent integrity (DEPARTMENT/SERVICE/PROVIDER_RESOURCE)
- Online closure requires service or resource target
- Document number counter monotonic allocation

Machine-readable: `docs/validation/d010/evidence/execution_evidence.json`

---

## 5. Corrected package DDL

Official Alembic revision IDs remain **TBD**. Apply only after PO approval. Dependency order matches §11.

### 5.1 TP-OPS-ELIGIBILITY

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

### 5.2 TP-OPS-ARRIVAL

```sql
ALTER TABLE appointments
  ADD COLUMN IF NOT EXISTS arrived_at_utc TIMESTAMPTZ NULL,
  ADD COLUMN IF NOT EXISTS historical_entry_reason VARCHAR(200) NULL,
  ADD COLUMN IF NOT EXISTS suppress_reminders BOOLEAN NOT NULL DEFAULT FALSE;

-- D010 Expand-and-Contract: NOT VALID until backfill completes on upgrade paths
ALTER TABLE appointments DROP CONSTRAINT IF EXISTS appointments_arrived_chk;
ALTER TABLE appointments
  ADD CONSTRAINT appointments_arrived_chk CHECK (
    (status <> 'CHECKED_IN') OR (arrived_at_utc IS NOT NULL)
  ) NOT VALID;
```

### 5.3 TP-OPS-SCOPES (+ departments)

```sql
-- D010: departments catalog required before DEPARTMENT scope_kind is usable
CREATE TABLE departments (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  department_code VARCHAR(64) NOT NULL,
  department_name VARCHAR(200) NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at_utc TIMESTAMPTZ NOT NULL,
  CONSTRAINT departments_tenant_id_id_uq UNIQUE (tenant_id, id),
  CONSTRAINT departments_code_uq UNIQUE (tenant_id, department_code)
);

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


-- Fail-closed: DEPARTMENT scopes must reference existing departments
CREATE OR REPLACE FUNCTION role_permission_scopes_ref_integrity()
RETURNS trigger AS $$
BEGIN
  IF NEW.scope_kind = 'DEPARTMENT' THEN
    IF NOT EXISTS (
      SELECT 1 FROM departments d
      WHERE d.tenant_id = NEW.tenant_id AND d.id = NEW.scope_ref
    ) THEN
      RAISE EXCEPTION 'DEPARTMENT scope_ref must reference departments.id';
    END IF;
  ELSIF NEW.scope_kind = 'SERVICE' THEN
    IF NOT EXISTS (
      SELECT 1 FROM services s
      WHERE s.tenant_id = NEW.tenant_id AND s.id = NEW.scope_ref
    ) THEN
      RAISE EXCEPTION 'SERVICE scope_ref must reference services.id';
    END IF;
  ELSIF NEW.scope_kind = 'PROVIDER_RESOURCE' THEN
    IF NOT EXISTS (
      SELECT 1 FROM bookable_resources r
      WHERE r.tenant_id = NEW.tenant_id AND r.id = NEW.scope_ref
    ) THEN
      RAISE EXCEPTION 'PROVIDER_RESOURCE scope_ref must reference bookable_resources.id';
    END IF;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER role_permission_scopes_ref_trg
  BEFORE INSERT OR UPDATE ON role_permission_scopes
  FOR EACH ROW EXECUTE FUNCTION role_permission_scopes_ref_integrity();
```

### 5.4 TP-OPS-NOTES

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
    FOREIGN KEY (tenant_id, patient_id) REFERENCES patient_profiles (tenant_id, id) MATCH FULL,
  CONSTRAINT patient_operational_notes_created_by_fk
    FOREIGN KEY (tenant_id, created_by_user_id) REFERENCES user_accounts (tenant_id, id) MATCH FULL
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
    FOREIGN KEY (tenant_id, patient_id) REFERENCES patient_profiles (tenant_id, id) MATCH FULL,
  CONSTRAINT patient_staff_tags_created_by_fk
    FOREIGN KEY (tenant_id, created_by_user_id) REFERENCES user_accounts (tenant_id, id) MATCH FULL
);
```

### 5.5 TP-OPS-WAITLIST

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
    FOREIGN KEY (tenant_id, converted_appointment_id) REFERENCES appointments (tenant_id, id) MATCH SIMPLE,
  CONSTRAINT appointment_waitlist_entries_created_by_fk
    FOREIGN KEY (tenant_id, created_by_user_id) REFERENCES user_accounts (tenant_id, id) MATCH FULL
);
```

### 5.6 TP-OPS-ONLINE-CLOSE

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
```

### 5.7 TP-OPS-LEDGER

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
    REFERENCES patient_profiles (tenant_id, id) MATCH FULL,
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


-- D010 corrections: append-only runtime privileges are applied in rls_clause746.sql
-- Refund cumulative cap helper (application still uses FOR UPDATE; this is defense-in-depth)
CREATE OR REPLACE FUNCTION clinic_refund_amount_within_receipt()
RETURNS trigger AS $$
DECLARE
  receipt_amount BIGINT;
  prior_refunds BIGINT;
BEGIN
  SELECT amount_irr INTO receipt_amount
  FROM payment_receipts
  WHERE tenant_id = NEW.tenant_id AND id = NEW.original_receipt_id
  FOR UPDATE;
  IF receipt_amount IS NULL THEN
    RAISE EXCEPTION 'receipt not found';
  END IF;
  SELECT COALESCE(SUM(amount_irr), 0) INTO prior_refunds
  FROM clinic_payment_refunds
  WHERE tenant_id = NEW.tenant_id AND original_receipt_id = NEW.original_receipt_id;
  IF prior_refunds + NEW.amount_irr > receipt_amount THEN
    RAISE EXCEPTION 'refund exceeds remaining receipt amount';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER clinic_payment_refunds_cap_trg
  BEFORE INSERT ON clinic_payment_refunds
  FOR EACH ROW EXECUTE FUNCTION clinic_refund_amount_within_receipt();
```

### 5.8 TP-OPS-INVENTORY

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
```

### 5.9 person_merge_events

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

### 5.10 RLS / grants / append-only (required companion)

Must ship with every approved package (or as a dedicated follow-on revision immediately after). Executable form validated as:

```sql
-- Clause 746 / Appendix F.6 three-policy pattern for TP-OPS tables.
-- Applied only in disposable validation; not an Alembic revision.
-- Policy names MUST match tp0007: tenant_runtime_base, tenant_runtime_guard, tenant_migrator_maintenance.

DO $$
DECLARE
  t text;
  tables text[] := ARRAY[
    'invoice_documents',
    'invoice_lines',
    'payment_receipts',
    'receipt_allocations',
    'patient_credits',
    'financial_adjustments',
    'clinic_payment_refunds',
    'document_number_counters',
    'inventory_items',
    'inventory_lots',
    'stock_movements',
    'service_item_suggestions',
    'appointment_waitlist_entries',
    'staff_service_links',
    'role_permission_scopes',
    'online_availability_closures',
    'patient_operational_notes',
    'patient_staff_tags',
    'person_merge_events',
    'departments'
  ];
BEGIN
  FOREACH t IN ARRAY tables LOOP
    IF to_regclass('public.' || t) IS NULL THEN
      CONTINUE;
    END IF;
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
    EXECUTE format(
      'CREATE POLICY tenant_runtime_base ON %I AS PERMISSIVE FOR ALL TO db_app_runtime USING (true) WITH CHECK (true)',
      t
    );
    EXECUTE format(
      $p$CREATE POLICY tenant_runtime_guard ON %I AS RESTRICTIVE FOR ALL TO db_app_runtime
         USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
         WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)$p$,
      t
    );
    EXECUTE format(
      'CREATE POLICY tenant_migrator_maintenance ON %I AS PERMISSIVE FOR ALL TO db_migrator USING (true) WITH CHECK (true)',
      t
    );
  END LOOP;
END $$;

-- Runtime DML grants (immutable finance tables: INSERT+SELECT only)
GRANT SELECT, INSERT, UPDATE ON invoice_documents TO db_app_runtime;
GRANT SELECT, INSERT, UPDATE ON invoice_lines TO db_app_runtime;
-- Keep UPDATE privilege so SELECT … FOR UPDATE works for concurrency; enforce
-- append-only with reject triggers (REVOKE UPDATE would block row locks).
GRANT SELECT, INSERT, UPDATE ON payment_receipts TO db_app_runtime;
GRANT SELECT, INSERT, UPDATE ON receipt_allocations TO db_app_runtime;
GRANT SELECT, INSERT, UPDATE ON patient_credits TO db_app_runtime;
GRANT SELECT, INSERT, UPDATE ON financial_adjustments TO db_app_runtime;
GRANT SELECT, INSERT, UPDATE ON clinic_payment_refunds TO db_app_runtime;
GRANT SELECT, INSERT, UPDATE ON document_number_counters TO db_app_runtime;

GRANT SELECT, INSERT, UPDATE ON inventory_items TO db_app_runtime;
GRANT SELECT, INSERT, UPDATE ON inventory_lots TO db_app_runtime;
GRANT SELECT, INSERT, UPDATE ON stock_movements TO db_app_runtime;
GRANT SELECT, INSERT, UPDATE ON service_item_suggestions TO db_app_runtime;

GRANT SELECT, INSERT, UPDATE ON appointment_waitlist_entries TO db_app_runtime;
GRANT SELECT, INSERT, UPDATE ON staff_service_links TO db_app_runtime;
GRANT SELECT, INSERT, UPDATE ON role_permission_scopes TO db_app_runtime;
GRANT SELECT, INSERT, UPDATE ON online_availability_closures TO db_app_runtime;
GRANT SELECT, INSERT, UPDATE ON patient_operational_notes TO db_app_runtime;
GRANT SELECT, INSERT, UPDATE ON patient_staff_tags TO db_app_runtime;
GRANT SELECT, INSERT, UPDATE ON person_merge_events TO db_app_runtime;

REVOKE DELETE ON payment_receipts FROM db_app_runtime;
REVOKE DELETE ON receipt_allocations FROM db_app_runtime;
REVOKE DELETE ON financial_adjustments FROM db_app_runtime;
REVOKE DELETE ON clinic_payment_refunds FROM db_app_runtime;
REVOKE DELETE ON stock_movements FROM db_app_runtime;
REVOKE DELETE ON person_merge_events FROM db_app_runtime;

CREATE OR REPLACE FUNCTION reject_mutation_append_only()
RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'append-only table % rejects %', TG_TABLE_NAME, TG_OP;
END;
$$ LANGUAGE plpgsql;

DO $$
DECLARE
  t text;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'payment_receipts',
    'receipt_allocations',
    'financial_adjustments',
    'clinic_payment_refunds',
    'stock_movements',
    'person_merge_events'
  ] LOOP
    EXECUTE format(
      'CREATE TRIGGER %I_reject_update BEFORE UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION reject_mutation_append_only()',
      t, t
    );
    EXECUTE format(
      'CREATE TRIGGER %I_reject_delete BEFORE DELETE ON %I FOR EACH ROW EXECUTE FUNCTION reject_mutation_append_only()',
      t, t
    );
  END LOOP;
END $$;

DO $$
BEGIN
  IF to_regclass('public.departments') IS NOT NULL THEN
    EXECUTE 'GRANT SELECT, INSERT, UPDATE ON departments TO db_app_runtime';
  END IF;
END $$;
```

---

## 6. Permissions (seed into permission_catalog_snapshots when landing)

| Package | Codes |
|---------|-------|
| Ledger | `FINANCE_INVOICE_VIEW`, `FINANCE_INVOICE_DRAFT`, `FINANCE_INVOICE_POST`, `FINANCE_RECEIPT_RECORD`, `FINANCE_DISCOUNT_APPLY`, `FINANCE_ADJUST_POSTED`, `FINANCE_REFUND_PARTIAL`, `FINANCE_REFUND_FULL`, `FINANCE_EXPORT` |
| Inventory | `INVENTORY_VIEW`, `INVENTORY_RECEIVE`, `INVENTORY_CONSUME`, `INVENTORY_ADJUST`, `INVENTORY_CONFIG` |
| Waitlist | `WAITLIST_VIEW`, `WAITLIST_MANAGE` |
| Scopes | Enforced via resolver against `role_permission_scopes`; fail-closed without matching scope (except `ALL`) |

---

## 7. Genuine source dependencies vs independently solvable work

| Item | Kind | Notes |
|------|------|-------|
| Official TP revision IDs | **Source / PO** | Cannot invent `tp0008+` |
| Production KMS / live gateway | **Class D** | Gate B; stubs only |
| Corrected DDL/RLS/triggers | **Independently solvable** | Validated here; ready for approval |
| Four-workspace UI for finance/inventory/waitlist/scopes | **Blocked on approval** | Task 28 remains open |
| ACR-D0.9 1:1 remap | **Source missing** | Provisional D09 IDs used |

---

## 8. Explicit Product Owner approval checklist

Approve or reject **each**:

- [ ] TP-OPS-LEDGER DDL + permissions + append-only + refund cap trigger  
- [ ] TP-OPS-INVENTORY DDL + FEFO + deferred invoice_line FK  
- [ ] TP-OPS-WAITLIST  
- [ ] TP-OPS-ELIGIBILITY  
- [ ] TP-OPS-SCOPES + `departments` catalog  
- [ ] TP-OPS-ARRIVAL (`NOT VALID` then VALIDATE pattern)  
- [ ] TP-OPS-ONLINE-CLOSE (target required)  
- [ ] TP-OPS-NOTES  
- [ ] person_merge_events (if required now)  
- [ ] Companion RLS/grants/append-only SQL (§5.10)  
- [ ] Official Alembic revision ID assignment for each approved package  
- [ ] Confirm non-production `CLINIC_PII_*` policy for demo/test only  
- [ ] Accept provisional D09 register **or** supply ACR-D0.9 for remap  

**Until boxes are checked, repository must not contain Alembic files for these packages.**

---

## 9. Consolidated final approval request

Product Owner is requested to:

1. Accept **ACR-D0.10** as the corrected complete operations contracts packet, replacing ACR-D0.6 for implementation planning.
2. Acknowledge disposable PG15 evidence at `docs/validation/d010/evidence/` (25/25 cases passed on this run).
3. Assign official Tenant Plane revision IDs and check §8 boxes for packages authorized to land.
4. Optionally re-attach authoritative ACR-D0.9 so provisional D09-01…14 can be remapped to Gemini’s original wording without re-litigating corrected DDL.
5. Keep **Task 28 open** until the four clinic operations workspaces are implemented against approved packages and accepted.

---

## 10. Related documents

- `docs/architecture_change_records/ACR-D0.6-COMPLETE-OPERATIONS-CONTRACTS.md` (prior proposed packet)
- `docs/validation/d010/evidence/execution_evidence.json`
- `docs/records/D0.7_DEPENDENCY_MAP_PREP.md`
- `docs/FINAL_MASTER_SPECIFICATION_v3.0.1_FINAL.txt` §50, §60, Appendix E.2, F.2–F.6, clauses 741–746

END OF ACR-D0.10 (PROPOSED — EXECUTION-VALIDATED)

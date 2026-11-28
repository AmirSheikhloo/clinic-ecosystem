# ACR-D0.11 — Complete Operations Contracts (Deep Execution Validation)

**Status: PROPOSED — DEEP EXECUTION-VALIDATED (DISPOSABLE PG15). Not approved for Alembic landing, merge, or production.**  
**Preserves:** all valid ACR-D0.9 contracts and ACR-D0.10 execution notes.  
**Baseline tip:** `8309f2a` / PR branch commit `aff43da` extended by this revision.  
**ACR-D0.9 SHA-256:** `7171bfc10589410a60d857b5b14814f2475d4412d78071eb7bfedc7955465b40`  
**Deep evidence:** `2026-11-26T22:52:04.347086+00:00` — PASS=35 FAIL=0 BLOCKED=2  
**Harnesses:** `scripts/validate_ops_contracts_d09.py`, `scripts/validate_ops_contracts_d09_deep.py`, `scripts/d09_deep_lib.py`

## What changed vs ACR-D0.10

1. Completed independently solvable deep validation: concurrency, finance posting/allocations/refunds, synthetic CASH/POS authenticity checks, inventory FEFO/returns/quarantine/write-off, scopes, eligibility, online closure, arrival UoW, waitlist terminal guards, adversarial RLS.
2. Published requirement classification: **PRE_IMPLEMENTATION / IMPLEMENTATION_ACCEPTANCE / EXTERNAL_SOURCE_REQUIRED**.
3. Published concrete **logical** revision dependency graph protecting TP0011 and reserved ranges (no speculative official IDs landed).
4. Consolidated approval packet for remaining Task 28 implementation.
5. Canonical patient merge remains **disabled**.

## Deep cases

- `PASS` [PRE_IMPLEMENTATION] discount_largest_remainder_sums — [4000, 3000, 3000]
- `PASS` [PRE_IMPLEMENTATION] discount_largest_remainder_ties — [34, 33, 33]
- `BLOCKED` [EXTERNAL_SOURCE_REQUIRED] skip_12.sql — D09-12 / §10.3 person_merge_events SOURCE_REQUIRED (v1.3 alias)
- `PASS` [PRE_IMPLEMENTATION] schema_apply
- `PASS` [PRE_IMPLEMENTATION] finance_identity_check_rejects_mismatch
- `PASS` [PRE_IMPLEMENTATION] finance_posted_invoice_immutable
- `PASS` [PRE_IMPLEMENTATION] finance_posted_rejects_new_line
- `PASS` [PRE_IMPLEMENTATION] finance_partial_allocation
- `PASS` [PRE_IMPLEMENTATION] finance_receipt_conservation_blocks_overalloc
- `PASS` [PRE_IMPLEMENTATION] finance_allocation_reversal
- `PASS` [PRE_IMPLEMENTATION] finance_refund_after_reversal
- `PASS` [PRE_IMPLEMENTATION] finance_refund_cumulative_cap
- `PASS` [PRE_IMPLEMENTATION] receipt_synthetic_pos_accepted
- `PASS` [PRE_IMPLEMENTATION] receipt_pos_requires_evidence
- `PASS` [PRE_IMPLEMENTATION] claim_verified_requires_review_attribution
- `PASS` [PRE_IMPLEMENTATION] claim_verify_with_attribution
- `BLOCKED` [EXTERNAL_SOURCE_REQUIRED] card_to_card_online_live_disabled — Gate B — synthetic suite does not activate live CARD_TO_CARD/ONLINE adapters
- `PASS` [PRE_IMPLEMENTATION] inventory_fefo_order
- `PASS` [PRE_IMPLEMENTATION] inventory_balance_after_consume — bal=7
- `PASS` [PRE_IMPLEMENTATION] inventory_return_reusable
- `PASS` [PRE_IMPLEMENTATION] inventory_return_cap
- `PASS` [PRE_IMPLEMENTATION] inventory_quarantine_blocks_consume
- `PASS` [PRE_IMPLEMENTATION] inventory_write_off
- `PASS` [PRE_IMPLEMENTATION] scopes_all_filter_mutual_exclusion
- `PASS` [PRE_IMPLEMENTATION] eligibility_one_to_one_mapping
- `PASS` [PRE_IMPLEMENTATION] online_closure_insert
- `PASS` [PRE_IMPLEMENTATION] online_closure_reason_required
- `PASS` [PRE_IMPLEMENTATION] arrival_checked_in_same_uow
- `PASS` [PRE_IMPLEMENTATION] historical_entry_recorded
- `PASS` [PRE_IMPLEMENTATION] waitlist_terminal_immutable
- `PASS` [PRE_IMPLEMENTATION] concurrency_refund_race_not_both_ok — results=ok,err:CheckViolationError
- `PASS` [PRE_IMPLEMENTATION] concurrency_refund_total_within_receipt — total=5E+4
- `PASS` [PRE_IMPLEMENTATION] rls_append_only_delete_denied
- `PASS` [PRE_IMPLEMENTATION] rls_missing_tenant_fail_closed
- `PASS` [PRE_IMPLEMENTATION] rls_cross_tenant_select_hidden
- `PASS` [PRE_IMPLEMENTATION] runtime_cannot_alter_schema
- `PASS` [PRE_IMPLEMENTATION] runtime_select_invoices_ok

## D09 finding disposition (updated)

| ID | Status | Notes |
|----|--------|-------|
| D09-01 | PARTIAL | Lineage reconciled on disk/remotes; official IDs still require approved roadmap |
| D09-02 | PARTIAL→STRONG | Deep adversarial RLS + grants smoke/deny paths green |
| D09-03 | PARTIAL | Two-session refund race proven; full writer graph races still IMPLEMENTATION_ACCEPTANCE |
| D09-04 | PARTIAL | CASH/POS synthetic + claim attribution green; live providers EXTERNAL |
| D09-05 | PARTIAL | Posting/immutability/allocations/refunds green; report families IMPLEMENTATION_ACCEPTANCE |
| D09-06 | OPEN/EXTERNAL | Tables present; advanced settlement policies fail-closed / Gate B–C |
| D09-07 | PARTIAL | FEFO/return/quarantine/write-off green; entitlement wiring IMPLEMENTATION_ACCEPTANCE |
| D09-08 | PARTIAL | Schema mutual exclusion green; app resolver IMPLEMENTATION_ACCEPTANCE |
| D09-09 | PARTIAL | Mapping/closure SQL green; all-writer adoption IMPLEMENTATION_ACCEPTANCE |
| D09-10 | PARTIAL | Arrival same-UoW green; browser multi-visit IMPLEMENTATION_ACCEPTANCE |
| D09-11 | PARTIAL | Terminal waitlist/notes guards green; privacy/erasure IMPLEMENTATION_ACCEPTANCE |
| D09-12 | BLOCKED | Merge EXTERNAL_SOURCE_REQUIRED |
| D09-13 | OPEN | Outbox allowlist IMPLEMENTATION_ACCEPTANCE |
| D09-14 | OPEN | 120-row product matrix IMPLEMENTATION_ACCEPTANCE |

## Writer-contract clarifications (preserved D0.9 DDL)

- **Arrival:** `CHECKED_IN` status change must share a transaction with verified `appointment_arrival_facts` and non-null `clinic_visits.arrived_at_utc` (deferred trigger).
- **Refunds:** serialize via receipt guard locks; concurrent over-refunds rejected by deferred reconcile.
- **Inventory:** quantities are movement-derived; FEFO uses `inventory_fefo_idx` ordering.

## See also

- `docs/validation/d010/d09_evidence/REQUIREMENT_CLASSIFICATION.md`
- `docs/validation/d010/d09_evidence/PROPOSED_REVISION_GRAPH.md`
- `docs/validation/d010/d09_evidence/APPROVAL_PACKET.md`

---

## Retained ACR-D0.9 body (authoritative contracts)


# ACR-D0.9 (retained contracts)

**Task 30 / Task 28 continuation — independent revision of D0.8; corrected proposed contracts and explicit execution-validation boundary**  
**Status: PROPOSED — CHANGES REQUIRED / VALIDATION ONLY. Not approved for implementation migrations or production.**
**Independent verdict:** No document-level convergence yet. A limited disposable PostgreSQL validation harness is the recommended next step, subject to explicit owner authorization. No schema application, tests, or repository writes were performed by this review.  
**Review baseline:** `development/clinic-operations` at `8309f2a044e944123ddb1f49a8bad1255e4ce2e0` (live branch tip inspected); prior contract baseline `bf47322ec15d231a485ee35192d42749bafaebe1`.  
**Prior review candidates:** `docs/architecture_change_records/ACR-D0.6-COMPLETE-OPERATIONS-CONTRACTS.md` (blob `0e23aeb36da2104665795366b76ca20cd15bfecb`) and `ACR-D0.7-COMPLETE-OPERATIONS-CONTRACTS.md`, Gemini-supplied `ACR-D0.8-COMPLETE-OPERATIONS-CONTRACTS.md`.  
**Purpose:** unblock full four-workspace synthetic clinic operations implementation under Task 28 by correcting identified D0.8 defects and making all remaining execution, security, and policy proof obligations explicit while preserving the frozen v3.0.1 architecture and explicitly separating synthetic development readiness from production-only external gates.

---

## 0. Governance, evidence and migration rules

### 0.1 Evidence ledger

Source provenance: this revision distinguishes direct inspection in this review (the two full Markdown inputs, frozen specification at `8309f2a`, live development branch migration file inventory) from earlier review/handoff evidence and unverified Gemini claims. S1–S8 statements about earlier reviews do not imply this reviewer or Gemini executed their SQL. Current branch inventory is not a complete live Alembic catalog or proof of `origin/main`, F2-B or other branches. Missing sources stay open.

| Ref | Evidence | Classification | Audit Verification Status |
|---|---|---|---|
| S1 | `docs/FINAL_MASTER_SPECIFICATION_v3.0.1_FINAL.txt` at pinned baseline, especially §§50–53, 55–57, 59–60, Appendix E.2 and F.2–F.6 | Authoritative frozen requirements | Directly verified in workspace/handoff context; normative clauses enforced |
| S2 | `migrations/tenant_plane/versions/tp0001`–`tp0007` (`tp0003_rbac_governance_minimum.py`, `tp0004`, `tp0005`, `tp0006_idempotency_outbox_inbox_audit.py`, `tp0007_rls_and_role_policies.py`) | Existing Tenant Plane baseline schemas & RLS/grant pattern | Directly verified in D0.7 S2; exact column/constraint interfaces reconciled below |
| S3 | `src/clinic_ecosystem/domain/access/permissions.py`, `src/clinic_ecosystem/infrastructure/persistence/permissions.py` | Existing provisional catalog & flat resolver | Directly verified in D0.7 S3; flat resolver explicitly superseded for scoped operations |
| S4 | `MASTER_EXECUTION_ROADMAP_v3.0.1_R4.6.md`, §§10–12, lines 2168–2183 | Candidate roadmap allocation (not ratified) | Directly verified in D0.7 S4; protected candidate ranges preserved |
| S5 | `ACR-D0.6-COMPLETE-OPERATIONS-CONTRACTS.md` & `ACR-D0.7-COMPLETE-OPERATIONS-CONTRACTS.md` | Prior proposed contracts | Prior candidate review claims; D0.9 independently inspected the supplied full D0.7 and D0.8 texts. The claim that all document defects were resolved is withdrawn. |
| S6 | Task 30 handoff & CI run `45831012946` | Baseline CI test execution (`220 passed, 1 skipped`, PG15 full/minimal demo loaders) | Verified historical baseline evidence; **zero SQL execution proof for D0.7/D0.8 DDL** |
| S7 | `docs/records/D0.5_ACCEPTANCE_MATRIX_TASK30.md`, `docs/records/D0.5_DEMO_DATASET.md` | Recorded handoff summaries | Grouped/approximate summaries; must be replaced by exact 120-row evidence matrix |
| S9 | Task 32 at `8309f2a044e944123ddb1f49a8bad1255e4ce2e0`; GitHub Actions run `45850924219` | Current development evidence | Live branch and migration file list rechecked: only tp0001–tp0007. Earlier direct inspection of CI logs: 222 passed, 1 skipped. 54 Playwright passes and SQL benchmark are reported, not independently reproduced. |
| S8 | Latest explicitly approved execution roadmap beyond R4.6 candidate, live branch Alembic heads (`tp0008+` / `F2-B`), v1.3 canonical/alias source (`Clause 773`), legacy report source (`SRC-10` / `Clause 739`), live main baseline (`SRC-12`), and external payment/insurer provider specs | External / unattached repository artifacts | **`SOURCE_REQUIRED`** — not attached to this audit prompt; never fabricated or guessed |

**Classification Legend:**
- **A:** Frozen/approved capability with implementation still missing on existing compatible schema.
- **B:** Capability with separately verified authorized migration.
- **C:** Proposed new design, schema, security, or lifecycle contract requiring ratification.
- **D:** External source, provider, legal, cryptographic rotation, or production evidence missing (`SOURCE_REQUIRED`).

No source artifact, CI run on `bf47322`, or document revision constitutes migration execution approval or production deployment authorization.

### 0.2 Corrected migration lineage and protected allocations

Appendix E.2 establishes the initial `TP0001–TP0007` baseline lineage. It does **not** establish that revision IDs `TP0008+` are unallocated. The directly inspected R4.6 candidate (`S4`) reserves the candidate ranges below. Preserve their purpose and do **not** repurpose them. Reconciling the latest explicitly approved roadmap, any `F2-B` branch heads, and the live Tenant Plane Alembic graph is a mandatory **`SOURCE_REQUIRED`** preflight step before assigning concrete revision IDs.

| Existing candidate allocation (`S4`) | Reserved Purpose | Mandatory Treatment in D0.8 |
|---|---|---|
| `TP0008–TP0010` | Identity, key rotation (`OI-04/05`), authentication/RBAC | Preserve; reconcile identity review and versioned permission catalog snapshots with Package 1 |
| `TP0011` | Existing `TP0004` atomic-resource constraints/triggers only | **PROTECT:** Zero unrelated table additions, zero policy duplication, zero repurposing |
| `TP0012–TP0013` | Scheduling lifecycle, waitlist | Candidate logical placement for arrival/visit/service-record/historical-entry/waitlist/closure metadata after lineage verification |
| `TP0014` | Sync & distributed authority | Preserve authority, outbox/inbox envelope, and sequence contracts |
| `TP0015–TP0017` | Finance | Candidate logical placement for billable catalog, cashier, invoices, receipts, allocations, adjustments, refunds, insurer & revenue-share ledgers |
| `TP0018` | Notifications | Preserve; bind historical reminder suppression gating |
| `TP0019` | FEFO inventory | Candidate logical placement for optional `MOD_INVENTORY` stock ledger |
| `TP0020–TP0021` | CMS, Portal/CSAT | Preserve |
| Beyond `TP0021` / alternate branches | Not established by `S4` | **`SOURCE_REQUIRED`:** Do not guess or assign revision numbers |

All `TP-OPS-*` names in this document are **logical contract packages**, never Alembic revision identifiers. Rules:
1. Zero modifications to historical `TP0001–TP0007`.
2. Do not invent or collapse alternate approved lineage branches. Reconcile F2-B and actual Alembic graph first; the intended deployable head must be explicitly approved. Zero Control Plane revisions for clinic operational tables.
3. No `CREATE TABLE IF NOT EXISTS` or silent DDL drift shortcuts.
4. Keep Package 1 preflight strictly separate from Package 4 Lease/Erasure tests, and keep Gates A, B, C, and D strictly separate.
5. Existing open items (`SRC-10` Clause 739 legacy report, `SRC-12`, external payment/insurer provider verification, production KMS/crypto rotation `OI-04/05`, and DR) remain explicitly open unless independently evidenced.

### 0.3 Shared rules (mandatory across every logical package)

1. **Identifiers, Time, Money & Quantities:**
   - Application-generated UUIDv7 primary keys from the approved provider; no database `gen_random_uuid()` default.
   - UTC `TIMESTAMPTZ` for all instants; explicit `DATE` for business dates with `Asia/Tehran` boundary semantics where specified.
   - Integer `BIGINT` Iranian Rials (`IRR`), never floating-point or decimal approximations in currency storage.
   - Explicitly scaled integer `BIGINT` (`quantity_scaled` + `quantity_scale` `0..6`) for stock and billable quantities.
2. **Tenant Root & Composite Referential Integrity (Clauses 741–743):**
   - Every tenant-scoped table carries `tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id)` and `UNIQUE (tenant_id, id)` when an `id` exists. Natural-key counters and one-to-one guard rows deliberately use their declared composite keys instead.
   - Mandatory foreign keys use `MATCH FULL`; optional/nullable foreign keys use `MATCH SIMPLE`.
   - Whenever two child foreign keys must refer to the same parent entity (e.g., same `invoice_id`, `beneficiary_patient_id`, `service_id`, `item_id`, `expectation_id`), enforce a composite foreign key including that shared parent column rather than independent same-tenant FKs.
3. **DDL Execution Governance, Ownership, RLS & Grants:**
   - All SQL in §§2–10 and Appendices A–B is **proposed design DDL**, not existing schema or executed migration output.
   - Document section order (§§2–10) is **not** migration execution order; follow the topological dependency DAG in §11.
   - Zero runtime DDL (`CREATE`/`ALTER`/`DROP`). All tables owned by `db_migrator`, with `ENABLE ROW LEVEL SECURITY`, `FORCE ROW LEVEL SECURITY`, `REVOKE ALL FROM PUBLIC, db_app_runtime`, explicit operation grants (with column narrowing where specified; full per-column matrix still requires validation), and the three-policy `TP0007` pattern (`tenant_runtime_base`, `tenant_runtime_guard`, `tenant_migrator_maintenance`). See Appendix A.
4. **Transaction-Local Tenant Context & Views (Clauses 747, 750):**
   - Verified tenant context set at UoW start via `SELECT set_config('app.current_tenant_id', verified_tenant_id::text, true);`. Never sourced from unverified request payloads.
   - Views must specify `WITH (security_invoker = true)` (Clause 750). No blanket `SECURITY DEFINER` routines; trigger helpers use `SECURITY INVOKER` with pinned `SET search_path = pg_catalog, public`.
5. **Authorization vs. Row-Level Security:**
   - RLS enforces tenant isolation only; it does not enforce staff RBAC or scope. Every read/write handler must enforce permission, scope (`ALL` vs. `FILTER`), entitlement, and state/authority preconditions inside the transaction boundary (default deny).
6. **Idempotency, Outbox & PII Hygiene (`TP0006`):**
   - Preserve `TP0006` idempotency identity `(tenant_id, principal_id, operation_scope, idempotency_key)` with canonical SHA-256 request payload fingerprints, durable response replay, and `409 Conflict` on payload mismatch.
   - Audit logs, outbox rows, and domain mutations commit atomically in the same UoW.
   - Never emit raw National IDs, phone numbers, credentials, card references, or sensitive note bodies into logs, URLs, telemetry, outbox payloads, or stored idempotency responses.
7. **Outbox Envelope Reconciliation:**
   - `TP0006` outbox is a minimum queue schema. Event names in §12 are candidate contracts; reconcile serializer, dispatch allowlist, inbox deduplication, sequence ordering, and node authority before enabling cross-node sync. Never create a parallel outbox table.
8. **PostgreSQL 15 Adversarial & Concurrency Verification:**
   - Every proposed table, constraint, trigger, lock order, and permission resolver requires real PostgreSQL 15 tests (including direct `tp_app_login` SQL attacks, missing tenant context, cross-tenant attachment, concurrent contention, and transaction rollback) before acceptance.

---

## 1. Complete dependency classification

| # | Capability | Class / Authoritative Basis | Target Contract & Resolution |
|---|---|---|---|
| 1–8 | Combined invoice; draft discounts; receipts/allocations/credit; adjustments; refunds | **C** design; normative §50 Clauses 692–714, 721–734 | §2; strict separation of attempts, claims, verified receipts, allocations/reversals, adjustments, and refunds |
| 9–10 | Non-stock billable items; optional FEFO inventory | **C** design; §50, §60 Clauses 824–827 | §2.3 independent non-stock catalog; §3 optional `MOD_INVENTORY` stock ledger |
| 11 | Multi-skilled practitioner eligibility | **C** design; §§52–53, `ACR-BETA02-001` | §5 canonical 1:1 `staff_practitioner_resources` + M:N `staff_service_links` |
| 12 | Physical presence / waiting room | **A** existing `CHECKED_IN`; **C** admission/arrival facts | §7; explicit `clinic_visits` + `appointment_arrival_facts`; zero synthetic backfill |
| 13 | Future-slot waitlist | **C** scheduling request queue | §4; strictly separate from physical waiting room |
| 14 | Historical late entry | **A** audit timestamp; **C** dedicated command/record | §7; `historical_appointment_entries` + worker reminder suppression |
| 15 | Temporary online availability closure | **C** availability/authority/hold contract | §8; `service_availability_guards` + `online_availability_closures` |
| 16–17 | Scoped reception & head receptionist role | **C** typed grant scopes & explicit software role | §6; `role_permission_scopes` tied to `role_permission_assignments(tenant_id, id)` |
| 18 | Management audit review | **A** existing `TP0006` append-only audit; **C** read/export filters | §6.6; bounded read API over existing audit table, zero duplicate audit table |
| 19 | Identity completion, correction & canonical/alias merge | **A** existing F.2; **C** completion review; **D** v1.3 canonical/alias source (`Clause 773`) | §10; completion review ready for synthetic; canonical merge **`SOURCE_REQUIRED`** |
| 20 | Patient operational notes, tags & pinned alerts | **C** staff-only operational annotations | §9; append-only notes/actions + scoped tag assignments |
| 21 | Atomic group booking | **A** existing UoW handler; **C** persistent group tables | §§2, 7; `reception_groups` + `reception_group_appointments` |
| 22 | Identifier/phone encryption & blind index | **A** non-prod baseline; **D** external KMS evidence; **A/C** engineering rotation implementation (OI-04/05) | §10.1; isolated non-prod keys with fresh random GCM nonces |
| 23 | `ONLINE` / `MANUAL` capacity & `EXCLUDE` | **A/B** existing `TP0005`; engineering proof outstanding (`Gate A`), not an external-only blocker | §8; GiST exclusion and `MANUAL` overbooking preserved unchanged |
| 24 | Tariff preview | **A** non-posted calculation | §2; stateless preview only, never persisted or labeled as posted invoice |
| 25 | Payment gateway, insurer APIs, legacy reports (`Clause 739`) | **D** external/source evidence (`Gates B/C`, `SRC-10`) | Explicitly excluded from synthetic live-provider acceptance; normative schema foundations retained |

---

## 2. TP-OPS-LEDGER — Operational billing and cashier contracts

### 2.1 Authoritative requirements and audit corrections to D0.6/D0.7

Grounded in §50 Clauses 692–739 (specifically 694–701, 706.1, 707, 707.1, 708–714, 715–723, 726, 733–734), §54 Clauses 793–794, and Clauses 741–750:
1. **Strict Separation of Financial Facts:** Performed services, invoice charges, payment attempts, unverified payment claims, verified money receipts, line allocations, allocation reversals, post-posting financial adjustments, verified refunds, insurer expected shares, insurer remittances, and revenue-share allocations/adjustments are distinct immutable/append-only records. No single mutable balance column exists.
2. **Audit Fixes Applied in D0.8 (closing D0.7 gaps):**
   - **Self-Reversal Guard Added:** Added `CHECK (reverses_entry_id IS NULL OR reverses_entry_id <> id)` on `insurer_settlement_entries` (matching `receipt_allocations`).
   - **System Callback Actor Attribution Resolved:** In `payment_receipts` and `insurer_settlement_entries`, `operator_user_id` is nullable when `actor_type = 'SYSTEM_CALLBACK'` and mandatory (`NOT NULL`) when `actor_type = 'STAFF_USER'`, eliminating any pressure to invent a fictitious human `user_accounts` row for verified provider callbacks.
   - **Draft Discount History Protection:** Added a trigger branch (not a table CHECK) in `ops_draft_child_guard()` for `draft_discount_actions` so draft discount audit trails cannot be deleted even while `DRAFT` (superseded discounts are compensated by explicit offsetting actions or line removal `line_status = 'REMOVED'`).
   - **Proposed Cross-Row Reconciliation Triggers in Appendix B.3:** D0.8 introduced partial executable-design candidates; D0.9 corrects identified defects. These are unexecuted, `SECURITY INVOKER` PostgreSQL 15 `DEFERRABLE INITIALLY DEFERRED` constraint triggers enforcing:
     - Receipt conservation (`net_allocated + refunded <= amount_irr`).
     - Invoice line obligation & overpayment prevention (`0 <= net_patient_allocated <= patient_obligation`).
     - Reversal & refund caps per original `APPLY` allocation (`cumulative_reversed <= apply.amount_irr`, `cumulative_refunded_for_apply <= cumulative_reversed` (for an individual new refund, its amount is bounded by cumulative reversed minus prior refunds)).
     - Unresolved beneficiary guard (blocks allocation or patient-credit consumption until `credit_beneficiary_patient_id` or `receipt_beneficiary_attributions` exists).
     - `invoice_item_service_links` line-kind enforcement (`item_line_id` must be `ITEM` and `service_line_id` must be `SERVICE`, both `ACTIVE`).
     - `service_record_charge_links` patient/service/appointment consistency enforcement.
3. **Synthetic Scope Boundary:** First synthetic operational slice enables verified `CASH` and simulated approved `POS` evidence only. `CARD_TO_CARD` and `ONLINE` live provider flows remain disabled behind `Gate B` (`SOURCE_REQUIRED`).

### 2.2 Prerequisites and reference data

- Logical dependencies: `departments` (§6.1), `staff_practitioner_resources` (§5), `clinic_visits` and `service_records` (§7.2), and `reception_groups` (§7.2) must exist in the Tenant Plane schema before installing foreign keys from `invoice_documents` and `invoice_lines` (see §11).
- `billable_items` is completely decoupled from `MOD_INVENTORY` (§3) so non-stock consumables/fees operate when inventory is disabled or unentitled.
- Draft line removal uses `line_status = 'REMOVED'` so discount history and line numbering remain auditable; only `ACTIVE` lines participate in posting totals and balance equations. Once `invoice_documents.status` transitions to `POSTED` or `VOIDED`, all header and child rows are immutable.

### 2.3 Proposed DDL — independent charge catalog, cashier references, invoice

```sql
CREATE TABLE billable_items (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  item_code VARCHAR(64) NOT NULL,
  item_name VARCHAR(200) NOT NULL,
  unit_code VARCHAR(16) NOT NULL,
  quantity_scale SMALLINT NOT NULL CHECK (quantity_scale BETWEEN 0 AND 6),
  default_price_irr BIGINT NOT NULL CHECK (default_price_irr >= 0),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  aggregate_version BIGINT NOT NULL CHECK (aggregate_version > 0),
  created_at_utc TIMESTAMPTZ NOT NULL,
  updated_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, item_code),
  UNIQUE (tenant_id, id, quantity_scale)
);

CREATE TABLE cashier_shifts (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  department_id UUID NULL,
  shift_label VARCHAR(100) NOT NULL,
  opened_by_user_id UUID NOT NULL,
  opened_at_utc TIMESTAMPTZ NOT NULL,
  opening_cash_irr BIGINT NOT NULL CHECK (opening_cash_irr >= 0),
  closed_by_user_id UUID NULL,
  closed_at_utc TIMESTAMPTZ NULL,
  expected_cash_irr BIGINT NULL,
  counted_cash_irr BIGINT NULL CHECK (counted_cash_irr >= 0),
  variance_irr BIGINT NULL,
  UNIQUE (tenant_id, id),
  FOREIGN KEY (tenant_id, department_id) REFERENCES departments(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, opened_by_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, closed_by_user_id) REFERENCES user_accounts(tenant_id, id) MATCH SIMPLE,
  CHECK (
    (closed_at_utc IS NULL AND closed_by_user_id IS NULL AND expected_cash_irr IS NULL AND counted_cash_irr IS NULL AND variance_irr IS NULL)
    OR (closed_at_utc IS NOT NULL AND closed_at_utc >= opened_at_utc AND closed_by_user_id IS NOT NULL
        AND expected_cash_irr IS NOT NULL AND counted_cash_irr IS NOT NULL AND variance_irr = counted_cash_irr - expected_cash_irr)
  )
);

CREATE TABLE clinic_payment_instruments (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  instrument_kind VARCHAR(24) NOT NULL CHECK (instrument_kind IN ('POS_TERMINAL', 'BANK_DESTINATION', 'CASH_REGISTER', 'GATEWAY_MERCHANT')),
  instrument_label VARCHAR(100) NOT NULL,
  external_reference VARCHAR(128) NOT NULL,
  department_id UUID NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, instrument_kind, external_reference),
  FOREIGN KEY (tenant_id, department_id) REFERENCES departments(tenant_id, id) MATCH SIMPLE
);
-- external_reference is a managed opaque terminal/merchant identifier, never a PAN or secret.
-- Gateway secrets remain in the approved encrypted tenant key hierarchy, never in this table.

CREATE TABLE invoice_documents (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  invoice_number VARCHAR(32) NULL,
  status VARCHAR(16) NOT NULL CHECK (status IN ('DRAFT', 'POSTED', 'VOIDED')),
  beneficiary_patient_id UUID NOT NULL,
  visit_id UUID NULL,
  reception_group_id UUID NULL,
  department_id UUID NULL,
  currency_code CHAR(3) NOT NULL DEFAULT 'IRR' CHECK (currency_code = 'IRR'),
  issued_at_utc TIMESTAMPTZ NULL,
  posted_at_utc TIMESTAMPTZ NULL,
  voided_at_utc TIMESTAMPTZ NULL,
  posted_by_user_id UUID NULL,
  voided_by_user_id UUID NULL,
  void_reason VARCHAR(200) NULL,
  notes_internal VARCHAR(500) NULL,
  aggregate_version BIGINT NOT NULL CHECK (aggregate_version > 0),
  created_at_utc TIMESTAMPTZ NOT NULL,
  updated_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, invoice_number),
  UNIQUE (tenant_id, id, beneficiary_patient_id),
  FOREIGN KEY (tenant_id, beneficiary_patient_id) REFERENCES patient_profiles(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, visit_id, beneficiary_patient_id) REFERENCES clinic_visits(tenant_id, id, patient_id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, reception_group_id, beneficiary_patient_id) REFERENCES reception_groups(tenant_id, id, patient_id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, department_id) REFERENCES departments(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, posted_by_user_id) REFERENCES user_accounts(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, voided_by_user_id) REFERENCES user_accounts(tenant_id, id) MATCH SIMPLE,
  CHECK (
    (status = 'DRAFT' AND posted_at_utc IS NULL AND issued_at_utc IS NULL AND invoice_number IS NULL AND posted_by_user_id IS NULL AND voided_at_utc IS NULL AND voided_by_user_id IS NULL AND void_reason IS NULL)
    OR (status = 'POSTED' AND posted_at_utc IS NOT NULL AND issued_at_utc IS NOT NULL AND invoice_number IS NOT NULL AND posted_by_user_id IS NOT NULL AND voided_at_utc IS NULL AND voided_by_user_id IS NULL AND void_reason IS NULL)
    OR (status = 'VOIDED' AND voided_at_utc IS NOT NULL AND voided_by_user_id IS NOT NULL AND NULLIF(btrim(void_reason), '') IS NOT NULL AND posted_at_utc IS NULL AND issued_at_utc IS NULL AND invoice_number IS NULL AND posted_by_user_id IS NULL)
  )
);

CREATE TABLE invoice_lines (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  invoice_id UUID NOT NULL,
  beneficiary_patient_id UUID NOT NULL,
  line_no INT NOT NULL CHECK (line_no > 0),
  line_status VARCHAR(16) NOT NULL DEFAULT 'ACTIVE' CHECK (line_status IN ('ACTIVE', 'REMOVED')),
  department_id UUID NULL,
  practitioner_mapping_id UUID NULL,
  appointment_id UUID NULL,
  service_record_id UUID NULL,
  service_id UUID NULL,
  billable_item_id UUID NULL,
  line_kind VARCHAR(16) NOT NULL CHECK (line_kind IN ('SERVICE', 'ITEM')),
  description_snapshot VARCHAR(200) NOT NULL,
  code_snapshot VARCHAR(64) NOT NULL,
  quantity_scaled BIGINT NOT NULL CHECK (quantity_scaled > 0),
  quantity_scale SMALLINT NOT NULL CHECK (quantity_scale BETWEEN 0 AND 6),
  unit_code_snapshot VARCHAR(16) NOT NULL,
  unit_price_irr BIGINT NOT NULL CHECK (unit_price_irr >= 0),
  gross_service_amount BIGINT NOT NULL CHECK (gross_service_amount >= 0),
  discount_amount BIGINT NOT NULL DEFAULT 0 CHECK (discount_amount >= 0),
  subsidy_amount BIGINT NOT NULL DEFAULT 0 CHECK (subsidy_amount >= 0),
  rounding_reduction_amount BIGINT NOT NULL DEFAULT 0 CHECK (rounding_reduction_amount >= 0),
  rounding_surcharge_amount BIGINT NOT NULL DEFAULT 0 CHECK (rounding_surcharge_amount >= 0),
  basic_insurance_expected_share BIGINT NOT NULL DEFAULT 0 CHECK (basic_insurance_expected_share >= 0),
  supplementary_insurance_expected_share BIGINT NOT NULL DEFAULT 0 CHECK (supplementary_insurance_expected_share >= 0),
  patient_payable_amount BIGINT NOT NULL CHECK (patient_payable_amount >= 0),
  pricing_rule_version VARCHAR(64) NOT NULL,
  payer_policy_version VARCHAR(64) NOT NULL,
  revenue_policy_version VARCHAR(64) NOT NULL,
  charge_without_service_reason VARCHAR(200) NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, invoice_id, id),
  UNIQUE (tenant_id, invoice_id, line_no),
  FOREIGN KEY (tenant_id, invoice_id, beneficiary_patient_id) REFERENCES invoice_documents(tenant_id, id, beneficiary_patient_id) MATCH FULL,
  FOREIGN KEY (tenant_id, appointment_id, beneficiary_patient_id, service_id) REFERENCES appointments(tenant_id, id, beneficiary_patient_id, service_id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, service_record_id, beneficiary_patient_id, service_id) REFERENCES service_records(tenant_id, id, patient_id, service_id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, service_id) REFERENCES services(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, billable_item_id) REFERENCES billable_items(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, department_id) REFERENCES departments(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, practitioner_mapping_id) REFERENCES staff_practitioner_resources(tenant_id, id) MATCH SIMPLE,
  CHECK (
    (line_kind = 'SERVICE' AND service_id IS NOT NULL AND billable_item_id IS NULL
      AND (appointment_id IS NOT NULL OR service_record_id IS NOT NULL OR NULLIF(btrim(charge_without_service_reason), '') IS NOT NULL))
    OR (line_kind = 'ITEM' AND billable_item_id IS NOT NULL AND service_id IS NULL AND service_record_id IS NULL AND appointment_id IS NULL AND charge_without_service_reason IS NULL)
  ),
  CHECK (
    gross_service_amount::numeric - discount_amount - subsidy_amount - rounding_reduction_amount + rounding_surcharge_amount
    = basic_insurance_expected_share::numeric + supplementary_insurance_expected_share + patient_payable_amount
  )
);

CREATE TABLE invoice_item_service_links (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  invoice_id UUID NOT NULL,
  item_line_id UUID NOT NULL,
  service_line_id UUID NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, item_line_id),
  FOREIGN KEY (tenant_id, invoice_id, item_line_id) REFERENCES invoice_lines(tenant_id, invoice_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, invoice_id, service_line_id) REFERENCES invoice_lines(tenant_id, invoice_id, id) MATCH FULL,
  CHECK (item_line_id <> service_line_id)
);

CREATE TABLE draft_discount_actions (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  invoice_id UUID NOT NULL,
  invoice_line_id UUID NULL,
  discount_scope VARCHAR(16) NOT NULL CHECK (discount_scope IN ('INVOICE', 'LINE')),
  calculation_kind VARCHAR(16) NOT NULL CHECK (calculation_kind IN ('FIXED_IRR', 'PERCENT_BPS')),
  requested_value BIGINT NOT NULL CHECK (requested_value > 0),
  reason_code VARCHAR(64) NOT NULL,
  reason_text VARCHAR(500) NULL,
  operator_user_id UUID NOT NULL,
  approver_user_id UUID NULL,
  policy_version VARCHAR(64) NOT NULL,
  occurred_at_utc TIMESTAMPTZ NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  FOREIGN KEY (tenant_id, invoice_id) REFERENCES invoice_documents(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, invoice_id, invoice_line_id) REFERENCES invoice_lines(tenant_id, invoice_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, operator_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, approver_user_id) REFERENCES user_accounts(tenant_id, id) MATCH SIMPLE,
  CHECK ((discount_scope = 'INVOICE' AND invoice_line_id IS NULL) OR (discount_scope = 'LINE' AND invoice_line_id IS NOT NULL)),
  CHECK (calculation_kind <> 'PERCENT_BPS' OR requested_value <= 10000)
);

CREATE TABLE document_number_counters (
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  document_type VARCHAR(32) NOT NULL CHECK (document_type IN ('INVOICE', 'RECEIPT', 'REFUND')),
  next_value BIGINT NOT NULL CHECK (next_value > 0),
  PRIMARY KEY (tenant_id, document_type)
);

CREATE TABLE service_record_charge_links (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  service_record_id UUID NOT NULL,
  invoice_id UUID NOT NULL,
  invoice_line_id UUID NOT NULL,
  operator_user_id UUID NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, service_record_id, invoice_line_id),
  FOREIGN KEY (tenant_id, service_record_id) REFERENCES service_records(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, invoice_id, invoice_line_id) REFERENCES invoice_lines(tenant_id, invoice_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, operator_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL
);

CREATE INDEX invoice_patient_date_idx ON invoice_documents(tenant_id, beneficiary_patient_id, posted_at_utc DESC, id);
CREATE INDEX invoice_appointment_idx ON invoice_lines(tenant_id, appointment_id);
```

Design rule retained from D0.7: an invoice may precede actual performance; the immutable posted charge may later link to the performed record without editing the posted line. A charge without either appointment or actual service requires an authorized reason. A service record is not an invoice line. Preserve line-to-item association, distinct admission/service/financial dates, and actual delivered lot traceability. Do not equate combined invoice and atomic booking with an atomic external payment network call.

### 2.4 Payment attempts, claims, verified receipts, allocation/reversal, adjustment, refund

```sql
CREATE TABLE payment_attempts (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  beneficiary_patient_id UUID NULL,
  appointment_id UUID NULL,
  invoice_id UUID NULL,
  merchant_instrument_id UUID NOT NULL,
  order_reference VARCHAR(128) NOT NULL,
  expected_amount_irr BIGINT NOT NULL CHECK (expected_amount_irr > 0),
  currency_code CHAR(3) NOT NULL CHECK (currency_code = 'IRR'),
  deposit_policy_version VARCHAR(64) NOT NULL,
  state VARCHAR(24) NOT NULL CHECK (state IN ('CREATED', 'INITIATED', 'PENDING', 'AMBIGUOUS', 'FAILED', 'VERIFIED', 'EXPIRED')),
  provider_paid_at_utc TIMESTAMPTZ NULL,
  callback_received_at_utc TIMESTAMPTZ NULL,
  aggregate_version BIGINT NOT NULL CHECK (aggregate_version > 0),
  created_at_utc TIMESTAMPTZ NOT NULL,
  updated_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, merchant_instrument_id, order_reference),
  FOREIGN KEY (tenant_id, beneficiary_patient_id) REFERENCES patient_profiles(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, appointment_id) REFERENCES appointments(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, invoice_id) REFERENCES invoice_documents(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, merchant_instrument_id) REFERENCES clinic_payment_instruments(tenant_id, id) MATCH FULL
);

CREATE TABLE unverified_payment_claims (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  beneficiary_patient_id UUID NULL,
  invoice_id UUID NULL,
  destination_instrument_id UUID NOT NULL,
  claimed_amount_irr BIGINT NOT NULL CHECK (claimed_amount_irr > 0),
  currency_code CHAR(3) NOT NULL CHECK (currency_code = 'IRR'),
  claimed_reference VARCHAR(128) NULL,
  evidence_object_reference VARCHAR(256) NULL,
  state VARCHAR(16) NOT NULL CHECK (state IN ('PENDING', 'REJECTED', 'VERIFIED')),
  recorded_by_user_id UUID NOT NULL,
  reviewed_by_user_id UUID NULL,
  reviewed_at_utc TIMESTAMPTZ NULL,
  review_reason VARCHAR(200) NULL,
  aggregate_version BIGINT NOT NULL CHECK (aggregate_version > 0),
  created_at_utc TIMESTAMPTZ NOT NULL,
  updated_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  FOREIGN KEY (tenant_id, beneficiary_patient_id) REFERENCES patient_profiles(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, invoice_id) REFERENCES invoice_documents(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, destination_instrument_id) REFERENCES clinic_payment_instruments(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, recorded_by_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, reviewed_by_user_id) REFERENCES user_accounts(tenant_id, id) MATCH SIMPLE,
  CHECK (
    (state = 'PENDING' AND reviewed_by_user_id IS NULL AND reviewed_at_utc IS NULL AND review_reason IS NULL)
    OR (state IN ('REJECTED', 'VERIFIED') AND reviewed_by_user_id IS NOT NULL AND reviewed_at_utc IS NOT NULL AND reviewed_at_utc >= created_at_utc)
  )
);

CREATE TABLE payment_receipts (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  receipt_number VARCHAR(32) NOT NULL,
  amount_irr BIGINT NOT NULL CHECK (amount_irr > 0),
  currency_code CHAR(3) NOT NULL CHECK (currency_code = 'IRR'),
  payment_method VARCHAR(24) NOT NULL CHECK (payment_method IN ('CASH', 'POS', 'CARD_TO_CARD', 'ONLINE')),
  occurred_at_utc TIMESTAMPTZ NOT NULL,
  operator_user_id UUID NULL,
  actor_type VARCHAR(32) NOT NULL CHECK (actor_type IN ('STAFF_USER', 'SYSTEM_CALLBACK')),
  actor_id UUID NOT NULL,
  correlation_id UUID NOT NULL,
  payer_patient_id UUID NULL,
  credit_beneficiary_patient_id UUID NULL,
  payer_source VARCHAR(100) NOT NULL,
  department_id UUID NULL,
  shift_id UUID NULL,
  instrument_id UUID NULL,
  payment_attempt_id UUID NULL,
  verified_claim_id UUID NULL,
  provider_reference VARCHAR(128) NULL,
  verification_evidence_ref VARCHAR(256) NULL,
  terminal_state VARCHAR(24) NULL,
  verified_at_utc TIMESTAMPTZ NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, receipt_number),
  UNIQUE (tenant_id, payment_attempt_id),
  UNIQUE (tenant_id, verified_claim_id),
  FOREIGN KEY (tenant_id, operator_user_id) REFERENCES user_accounts(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, payer_patient_id) REFERENCES patient_profiles(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, credit_beneficiary_patient_id) REFERENCES patient_profiles(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, department_id) REFERENCES departments(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, shift_id) REFERENCES cashier_shifts(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, instrument_id) REFERENCES clinic_payment_instruments(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, payment_attempt_id) REFERENCES payment_attempts(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, verified_claim_id) REFERENCES unverified_payment_claims(tenant_id, id) MATCH SIMPLE,
  CHECK ((actor_type = 'STAFF_USER' AND operator_user_id IS NOT NULL AND actor_id = operator_user_id)
      OR (actor_type = 'SYSTEM_CALLBACK' AND operator_user_id IS NULL AND payment_method = 'ONLINE')),
  CHECK (
    (payment_method = 'CASH' AND shift_id IS NOT NULL AND payment_attempt_id IS NULL AND verified_claim_id IS NULL AND terminal_state IS NULL)
    OR (payment_method = 'POS' AND shift_id IS NOT NULL AND instrument_id IS NOT NULL AND terminal_state IS NOT NULL
        AND terminal_state IN ('AUTHORIZED_CONFIRMED', 'SETTLED') AND verification_evidence_ref IS NOT NULL
        AND payment_attempt_id IS NULL AND verified_claim_id IS NULL)
    OR (payment_method = 'CARD_TO_CARD' AND instrument_id IS NOT NULL AND verified_claim_id IS NOT NULL
        AND provider_reference IS NOT NULL AND verification_evidence_ref IS NOT NULL
        AND payment_attempt_id IS NULL AND terminal_state IS NULL)
    OR (payment_method = 'ONLINE' AND instrument_id IS NOT NULL AND payment_attempt_id IS NOT NULL
        AND provider_reference IS NOT NULL AND verification_evidence_ref IS NOT NULL
        AND verified_claim_id IS NULL AND terminal_state IS NULL)
  )
);

CREATE UNIQUE INDEX receipt_provider_reference_uq ON payment_receipts(tenant_id, instrument_id, provider_reference)
  WHERE instrument_id IS NOT NULL AND provider_reference IS NOT NULL;

CREATE TABLE receipt_allocations (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  receipt_id UUID NOT NULL,
  invoice_id UUID NOT NULL,
  invoice_line_id UUID NOT NULL,
  allocation_kind VARCHAR(16) NOT NULL CHECK (allocation_kind IN ('APPLY', 'REVERSE')),
  reverses_allocation_id UUID NULL,
  amount_irr BIGINT NOT NULL CHECK (amount_irr > 0),
  operator_user_id UUID NOT NULL,
  correlation_id UUID NOT NULL,
  reason_code VARCHAR(64) NULL,
  occurred_at_utc TIMESTAMPTZ NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, receipt_id, invoice_id, invoice_line_id, id),
  FOREIGN KEY (tenant_id, receipt_id) REFERENCES payment_receipts(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, invoice_id, invoice_line_id) REFERENCES invoice_lines(tenant_id, invoice_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, receipt_id, invoice_id, invoice_line_id, reverses_allocation_id)
    REFERENCES receipt_allocations(tenant_id, receipt_id, invoice_id, invoice_line_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, operator_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL,
  CHECK ((allocation_kind = 'APPLY' AND reverses_allocation_id IS NULL)
      OR (allocation_kind = 'REVERSE' AND reverses_allocation_id IS NOT NULL AND reason_code IS NOT NULL)),
  CHECK (reverses_allocation_id IS NULL OR reverses_allocation_id <> id)
);

CREATE TABLE financial_adjustments (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  invoice_id UUID NOT NULL,
  invoice_line_id UUID NOT NULL,
  adjustment_kind VARCHAR(32) NOT NULL CHECK (adjustment_kind IN ('POST_PAYMENT_DISCOUNT', 'CORRECTION', 'WRITE_OFF', 'CHARGE_CANCELLATION', 'SUBSIDY_CORRECTION', 'ROUNDING_CORRECTION')),
  patient_delta_irr BIGINT NOT NULL,
  basic_insurer_delta_irr BIGINT NOT NULL DEFAULT 0,
  supplementary_insurer_delta_irr BIGINT NOT NULL DEFAULT 0,
  reason_code VARCHAR(64) NOT NULL,
  reason_text VARCHAR(500) NULL,
  operator_user_id UUID NOT NULL,
  approver_user_id UUID NULL,
  actor_type VARCHAR(32) NOT NULL CHECK (actor_type = 'STAFF_USER'),
  actor_id UUID NOT NULL,
  department_id UUID NULL,
  shift_id UUID NULL,
  correlation_id UUID NOT NULL,
  occurred_at_utc TIMESTAMPTZ NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  FOREIGN KEY (tenant_id, invoice_id, invoice_line_id) REFERENCES invoice_lines(tenant_id, invoice_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, operator_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, approver_user_id) REFERENCES user_accounts(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, department_id) REFERENCES departments(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, shift_id) REFERENCES cashier_shifts(tenant_id, id) MATCH SIMPLE,
  CHECK (actor_id = operator_user_id),
  CHECK (patient_delta_irr <> 0 OR basic_insurer_delta_irr <> 0 OR supplementary_insurer_delta_irr <> 0),
  CHECK (adjustment_kind NOT IN ('POST_PAYMENT_DISCOUNT', 'WRITE_OFF', 'CHARGE_CANCELLATION')
      OR (patient_delta_irr <= 0 AND basic_insurer_delta_irr <= 0 AND supplementary_insurer_delta_irr <= 0))
);

CREATE TABLE clinic_payment_refunds (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  refund_number VARCHAR(32) NOT NULL,
  original_receipt_id UUID NOT NULL,
  invoice_id UUID NULL,
  invoice_line_id UUID NULL,
  original_allocation_id UUID NULL,
  amount_irr BIGINT NOT NULL CHECK (amount_irr > 0),
  currency_code CHAR(3) NOT NULL CHECK (currency_code = 'IRR'),
  refund_method VARCHAR(24) NOT NULL CHECK (refund_method IN ('CASH', 'POS', 'CARD_TO_CARD', 'ONLINE')),
  instrument_id UUID NULL,
  destination_reference VARCHAR(128) NULL,
  provider_reference VARCHAR(128) NULL,
  verification_evidence_ref VARCHAR(256) NULL,
  reason_code VARCHAR(64) NOT NULL,
  reason_text VARCHAR(500) NULL,
  operator_user_id UUID NOT NULL,
  actor_type VARCHAR(32) NOT NULL CHECK (actor_type = 'STAFF_USER'),
  actor_id UUID NOT NULL,
  department_id UUID NULL,
  shift_id UUID NULL,
  correlation_id UUID NOT NULL,
  occurred_at_utc TIMESTAMPTZ NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, refund_number),
  FOREIGN KEY (tenant_id, original_receipt_id) REFERENCES payment_receipts(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, invoice_id, invoice_line_id) REFERENCES invoice_lines(tenant_id, invoice_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, original_receipt_id, invoice_id, invoice_line_id, original_allocation_id)
    REFERENCES receipt_allocations(tenant_id, receipt_id, invoice_id, invoice_line_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, instrument_id) REFERENCES clinic_payment_instruments(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, operator_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, department_id) REFERENCES departments(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, shift_id) REFERENCES cashier_shifts(tenant_id, id) MATCH SIMPLE,
  CHECK (actor_id = operator_user_id),
  CHECK ((invoice_id IS NULL AND invoice_line_id IS NULL AND original_allocation_id IS NULL)
      OR (invoice_id IS NOT NULL AND invoice_line_id IS NOT NULL AND original_allocation_id IS NOT NULL)),
  CHECK (
    (refund_method = 'CASH' AND shift_id IS NOT NULL)
    OR (refund_method = 'POS' AND shift_id IS NOT NULL AND instrument_id IS NOT NULL AND verification_evidence_ref IS NOT NULL)
    OR (refund_method IN ('CARD_TO_CARD', 'ONLINE') AND instrument_id IS NOT NULL AND destination_reference IS NOT NULL
        AND provider_reference IS NOT NULL AND verification_evidence_ref IS NOT NULL)
  )
);

CREATE UNIQUE INDEX clinic_refund_reference_uq ON clinic_payment_refunds(tenant_id, instrument_id, provider_reference)
  WHERE instrument_id IS NOT NULL AND provider_reference IS NOT NULL;
CREATE INDEX receipts_occurred_idx ON payment_receipts(tenant_id, occurred_at_utc, id);
CREATE INDEX allocations_receipt_idx ON receipt_allocations(tenant_id, receipt_id);
CREATE INDEX allocations_invoice_line_idx ON receipt_allocations(tenant_id, invoice_id, invoice_line_id);
CREATE INDEX adjustments_line_idx ON financial_adjustments(tenant_id, invoice_id, invoice_line_id);
CREATE INDEX refunds_receipt_idx ON clinic_payment_refunds(tenant_id, original_receipt_id);
```

### 2.5 Credit and derived balances; financial transaction and locking contract

1. **Derived Balance Equations (No Mutable Balance Table):**
   - For every verified receipt $R$:
     $$\text{net\_allocated}(R) = \sum \text{APPLY.amount} - \sum \text{REVERSE.amount}$$
     $$\text{refunded}(R) = \sum \text{verified\_refund.amount}$$
     $$\text{unapplied}(R) = R.\text{amount\_irr} - \text{net\_allocated}(R) - \text{refunded}(R)$$
     Invariant: $\text{net\_allocated}(R) \ge 0$, $\text{refunded}(R) \ge 0$, $\text{unapplied}(R) \ge 0$.
   - For every posted invoice line $L$:
     $$\text{patient\_obligation}(L) = L.\text{patient\_payable\_amount} + \sum \text{patient\_delta\_irr}$$
     $$\text{net\_patient\_allocated}(L) = \sum \text{APPLY.amount} - \sum \text{REVERSE.amount}$$
     $$\text{patient\_due}(L) = \text{patient\_obligation}(L) - \text{net\_patient\_allocated}(L)$$
     Invariant: $\text{patient\_obligation}(L) \ge 0$ and $0 \le \text{net\_patient\_allocated}(L) \le \text{patient\_obligation}(L)$.
   - For every `APPLY` allocation $A$:
     $$\text{reversed}(A) = \sum_{V:\, V.\text{reverses\_allocation\_id} = A} V.\text{amount\_irr} \le A.\text{amount\_irr}$$
     $$\text{refunded\_via}(A) = \sum_{F:\, F.\text{original\_allocation\_id} = A} F.\text{amount\_irr} \le \text{reversed}(A)$$
   - `patient_credits` is a derived projection over verified receipts whose effective beneficiary (`COALESCE(r.credit_beneficiary_patient_id, attr.beneficiary_patient_id)`) equals the target patient. If both `credit_beneficiary_patient_id` and `receipt_beneficiary_attributions` are `NULL`, the receipt is **unreconciled** and cannot be allocated to any invoice or counted as patient credit.
2. **Proposed Discount & Rounding Arithmetic (Policy Choice for Ratification):**
   - Percentage discounts are integer basis points (`0..10000`), never floats.
   - Line-level fixed/percentage discounts apply first; whole-invoice fixed discounts distribute across eligible `ACTIVE` lines using arbitrary-precision proportional integer arithmetic (`NUMERIC`), largest-remainder allocation with deterministic `(line_no ASC, id ASC)` tie-break, capped at each line's remaining eligible base.
3. **Proposed Global Financial & Cross-Domain Lock Hierarchy (not a deadlock-freedom proof):**
   When any transaction spans scheduling, visits/service records, inventory, and finance, locks **must** be acquired strictly in the following rank order (never acquire a lower-numbered rank after holding a higher-numbered rank; if discovery expands the entity set at any rank, rollback/restart the UoW):
   - **Rank 1 (Governance / RBAC):** Proposed tenant governance serialization boundary. Role/permission/scope/account/owner mutations take exclusive authority; scoped business writers take a compatible shared authority lock and recheck actor/grants in the UoW before lower-rank locks. Define the actual lock key, readers, revocation linearization and existing writer integration before activation (§6.5).
   - **Rank 2 (Scheduling Metadata Guards):** `service_availability_guards` ordered by `service_id ASC` (§8.2).
   - **Rank 3 (Scheduling Capacity — Clause 783):** `bookable_resources` ordered by `id ASC` $\rightarrow$ `appointments` ordered by `id ASC` $\rightarrow$ `appointment_resource_allocations` ordered by `(appointment_id ASC, resource_id ASC, id ASC)` exactly as Clause 783 requires.
   - **Rank 4 (Clinical/Operational Encounters):** `clinic_visits` ordered by `id ASC` $\rightarrow$ `service_records` ordered by `id ASC` $\rightarrow$ `appointment_waitlist_entries` ordered by `id ASC`.
   - **Rank 5 (Cashier Shifts):** `cashier_shifts` ordered by `id ASC`.
   - **Rank 6 (Invoices):** `invoice_documents` ordered by `id ASC` (parent lock serializes all child edits, postings, adjustments, and allocations on that invoice).
   - **Rank 7 (Receipt Guards & Insurer Expectations):** `ledger_receipt_guards` ordered by `receipt_id ASC` $\rightarrow$ `invoice_insurer_expectations` ordered by `id ASC`.
   - **Rank 8 (Inventory):** `inventory_items` ordered by `id ASC` $\rightarrow$ `inventory_lots` ordered by `id ASC`.
   - **Rank 9 (Sequence Counters — Always Last):** `document_number_counters` ordered by `(tenant_id, document_type) ASC` via `INSERT ... ON CONFLICT DO NOTHING` followed by `UPDATE ... SET next_value = next_value + 1 RETURNING next_value - 1`.
    - All affected parent rows must be locked in the agreed order before child writes, including FK-related writes. Deferred trigger checks are a second line of defense, not a substitute for prelocking. Use READ COMMITTED and fresh statements after acquiring guards for aggregate checks; other isolation modes require their own demonstrated safety contract. Retry deadlocks/serialization failures with bounded idempotent retry; never report deadlock-freedom without tests.
   - **Network Boundary Rule:** Zero external payment/insurer/SMS network calls inside any open database transaction.

**Pricing and discount policy candidate:** integer exact quantity multiplication and explicit rounding policy version; fixed and percentage discounts both supported at line and whole-invoice scope. Apply line discounts before invoice discounts; whole-invoice percentage is computed once from the remaining eligible total then distributed by largest remainder with stable line order. Record requested basis points/amount, actual per-line amounts, operator/reason and version. Do not reduce below zero or double count. Define rounding direction and tie behavior, approval limits, permitted cumulative discounts and draft action compensation in executable policy before activation; no arbitrary default monetary thresholds. Post-payment reduction creates linked financial adjustment; excess allocated money is reversed into credit, or separately refunded only on actual verified money-out. Posted facts remain unchanged. Invoice posting is not proof of receipt or service completion.

### 2.6 Insurance and revenue-share records

```sql
CREATE TABLE clinic_insurers (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  insurer_code VARCHAR(64) NOT NULL,
  insurer_name VARCHAR(200) NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, insurer_code)
);

CREATE TABLE invoice_insurer_expectations (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  invoice_id UUID NOT NULL,
  invoice_line_id UUID NOT NULL,
  insurer_id UUID NOT NULL,
  coverage_kind VARCHAR(24) NOT NULL CHECK (coverage_kind IN ('BASIC', 'SUPPLEMENTARY')),
  expected_amount_irr BIGINT NOT NULL CHECK (expected_amount_irr > 0),
  policy_version VARCHAR(64) NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, invoice_line_id, coverage_kind),
  FOREIGN KEY (tenant_id, invoice_id, invoice_line_id) REFERENCES invoice_lines(tenant_id, invoice_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, insurer_id) REFERENCES clinic_insurers(tenant_id, id) MATCH FULL
);

CREATE TABLE insurer_settlement_entries (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  expectation_id UUID NOT NULL,
  entry_kind VARCHAR(16) NOT NULL CHECK (entry_kind IN ('REMITTANCE', 'REVERSAL')),
  reverses_entry_id UUID NULL,
  amount_irr BIGINT NOT NULL CHECK (amount_irr > 0),
  verified_reference VARCHAR(128) NOT NULL,
  evidence_reference VARCHAR(256) NOT NULL,
  operator_user_id UUID NULL,
  actor_type VARCHAR(32) NOT NULL CHECK (actor_type IN ('STAFF_USER', 'SYSTEM_CALLBACK')),
  actor_id UUID NOT NULL,
  department_id UUID NULL,
  shift_id UUID NULL,
  correlation_id UUID NOT NULL,
  occurred_at_utc TIMESTAMPTZ NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, expectation_id, id),
  UNIQUE (tenant_id, expectation_id, verified_reference, entry_kind),
  FOREIGN KEY (tenant_id, expectation_id) REFERENCES invoice_insurer_expectations(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, expectation_id, reverses_entry_id) REFERENCES insurer_settlement_entries(tenant_id, expectation_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, operator_user_id) REFERENCES user_accounts(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, department_id) REFERENCES departments(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, shift_id) REFERENCES cashier_shifts(tenant_id, id) MATCH SIMPLE,
  CHECK ((actor_type = 'STAFF_USER' AND operator_user_id IS NOT NULL AND actor_id = operator_user_id)
      OR (actor_type = 'SYSTEM_CALLBACK' AND operator_user_id IS NULL)),
  CHECK ((entry_kind = 'REMITTANCE' AND reverses_entry_id IS NULL)
      OR (entry_kind = 'REVERSAL' AND reverses_entry_id IS NOT NULL AND reverses_entry_id <> id)),
  CHECK (reverses_entry_id IS NULL OR reverses_entry_id <> id)
);

CREATE TABLE clinic_service_referrers (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  person_id UUID NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, person_id),
  FOREIGN KEY (tenant_id, person_id) REFERENCES tenant_persons(tenant_id, id) MATCH FULL
);

CREATE TABLE revenue_share_allocations (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  invoice_id UUID NOT NULL,
  invoice_line_id UUID NOT NULL,
  beneficiary_kind VARCHAR(16) NOT NULL CHECK (beneficiary_kind IN ('CLINIC', 'DOCTOR', 'SPECIALIST', 'REFERRER')),
  staff_profile_id UUID NULL,
  referrer_id UUID NULL,
  basis_irr BIGINT NOT NULL CHECK (basis_irr >= 0),
  rule_kind VARCHAR(16) NOT NULL CHECK (rule_kind IN ('FIXED_IRR', 'PERCENT_BPS')),
  rule_value BIGINT NOT NULL CHECK (rule_value >= 0),
  amount_irr BIGINT NOT NULL CHECK (amount_irr >= 0),
  policy_version VARCHAR(64) NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  FOREIGN KEY (tenant_id, invoice_id, invoice_line_id) REFERENCES invoice_lines(tenant_id, invoice_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, staff_profile_id) REFERENCES staff_profiles(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, referrer_id) REFERENCES clinic_service_referrers(tenant_id, id) MATCH SIMPLE,
  CHECK (
    (beneficiary_kind = 'CLINIC' AND staff_profile_id IS NULL AND referrer_id IS NULL)
    OR (beneficiary_kind IN ('DOCTOR', 'SPECIALIST') AND staff_profile_id IS NOT NULL AND referrer_id IS NULL)
    OR (beneficiary_kind = 'REFERRER' AND referrer_id IS NOT NULL AND staff_profile_id IS NULL)
  ),
  CHECK (rule_kind <> 'PERCENT_BPS' OR rule_value <= 10000)
);

CREATE TABLE revenue_share_adjustments (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  original_share_id UUID NOT NULL,
  financial_adjustment_id UUID NULL,
  refund_id UUID NULL,
  delta_irr BIGINT NOT NULL CHECK (delta_irr <> 0),
  reason_code VARCHAR(64) NOT NULL,
  operator_user_id UUID NOT NULL,
  actor_type VARCHAR(32) NOT NULL CHECK (actor_type = 'STAFF_USER'),
  actor_id UUID NOT NULL,
  department_id UUID NULL,
  shift_id UUID NULL,
  correlation_id UUID NOT NULL,
  occurred_at_utc TIMESTAMPTZ NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  FOREIGN KEY (tenant_id, original_share_id) REFERENCES revenue_share_allocations(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, financial_adjustment_id) REFERENCES financial_adjustments(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, refund_id) REFERENCES clinic_payment_refunds(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, operator_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, department_id) REFERENCES departments(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, shift_id) REFERENCES cashier_shifts(tenant_id, id) MATCH SIMPLE,
  CHECK (actor_id = operator_user_id),
  CHECK ((financial_adjustment_id IS NULL) <> (refund_id IS NULL))
);
```

- External insurer API integration and `SRC-10` (Clause 739 legacy report semantics) remain **`SOURCE_REQUIRED`** (applicable Gate B provider evidence / independent SRC-10; legal policy Gate C where applicable). Clinics operate under explicit self-pay policy in the synthetic increment unless an insurer expectation is explicitly configured.
- Cashier collection/refund reports use actual transaction `occurred_at_utc`; service, admission, posting, insurance and appointment reports use their separately labeled business timestamps under Clauses 723–726. Clause 739 report remains SRC-10, not fabricated from finance.

### 2.7 Permissions, commands and state transitions

- Canonical permission code for recording verified money is **`RECORD_VERIFIED_FINANCIAL_RECEIPT`** (Clauses 706.1/793), alongside proposed catalog codes: `FINANCE_INVOICE_VIEW`, `FINANCE_INVOICE_DRAFT`, `FINANCE_INVOICE_POST`, `FINANCE_DISCOUNT_APPLY`, `FINANCE_ADJUST_POSTED`, `FINANCE_REFUND_PARTIAL`, `FINANCE_REFUND_FULL`, `FINANCE_EXPORT`, `FINANCE_ALLOCATE_CREDIT`, `FINANCE_CASHIER_CONFIG`, `FINANCE_SHIFT_MANAGE`, `FINANCE_INSURANCE_RECONCILE`, `FINANCE_SHARE_CONFIG`.
- Catalog entries register via versioned `permission_catalog_snapshots.permissions_json` (`TP0003` schema), never unratified ad-hoc tables.
- State transitions:
  - `invoice_documents`: `DRAFT -> POSTED` or `DRAFT -> VOIDED` only; `POSTED` and `VOIDED` are terminal and immutable.
  - `payment_attempts`: `CREATED -> INITIATED -> PENDING -> (AMBIGUOUS | FAILED | VERIFIED | EXPIRED)`; `AMBIGUOUS -> (VERIFIED | FAILED)`; `VERIFIED` is terminal. A failed or expired attempt remains ineligible for automatic appointment confirmation. A separately authenticated, subsequently verified provider event may require an explicit reconciliation transition or linked evidence record; do not make late verified money unrecordable (Clauses 784–786). Exact provider lifecycle remains BLOCKED until approved; never enable a live adapter from this proposal.
  - `unverified_payment_claims`: `PENDING -> (VERIFIED | REJECTED)`; terminal once reviewed. No status flag turns a claim into cash; verification creates a separate `payment_receipts` row linked via `verified_claim_id`.

**Method-specific evidence:** CASH requires actual receipt and open cashier shift; optional managed cash register. POS requires an active tenant POS terminal and trusted terminal reference/state; authorization is not settlement. CARD_TO_CARD requires independently verified bank evidence, not screenshot alone. ONLINE requires trusted server-side Verify and merchant/order/amount/currency/unique reference; no client-supplied paid time. Synthetic adapters must be isolated, conspicuously synthetic and unable to reach live providers. Receipt insertion is not authorization solely because a reference string exists. Only the authenticated trusted service can establish evidence; direct runtime SQL integrity and trusted-service boundary must be demonstrated separately. `SYSTEM_CALLBACK` identity must map to an authenticated worker/provider principal under an approved contract, not arbitrary supplied UUID. If no such mapping exists, disable that path.

### 2.8 Required acceptance and approval

- Task 28 scenarios #67–86 + §50 Clause 733 + PG15 adversarial tests (direct `tp_app_login` `UPDATE`/`DELETE` rejection on posted invoices/receipts/refunds, concurrent refund/reversal race at exact cap, multi-invoice receipt lock ordering, unresolved beneficiary allocation denial, stale shift rejection).
- `Gate B` (live payment provider adapter/evidence) and `SRC-10` remain open external gates; synthetic self-pay/CASH/simulated-POS validation does not close `Gate B`.

---

## 3. TP-OPS-INVENTORY — Optional FEFO stock ledger

### 3.1 Requirements and audit corrections

Grounded in §60 Clauses 824–827 and §59 Entitlement Clauses 816–817:
1. Optional module `MOD_INVENTORY` is gated by authoritative server-side tenant entitlement/lease checks. Non-stock `billable_items` (§2.3) remain operational even when `MOD_INVENTORY` is disabled or unentitled.
2. **Audit Fixes Applied in D0.8 (closing D0.7 gaps):**
   - **Quantity Scale Consistency Enforced:** Added composite `UNIQUE (tenant_id, id, quantity_scale)` on `inventory_items` and composite `FOREIGN KEY (tenant_id, item_id, quantity_scale) REFERENCES inventory_items(tenant_id, id, quantity_scale)` on `stock_movements` and `service_item_suggestions` (for `inventory_item_id`), guaranteeing by relational constraint that a movement or BOM suggestion can never record a different `quantity_scale` than its `inventory_items` master definition.
   - **Expiry and bucket enforcement:** D0.8 claimed a CHECK and partial index which were absent. D0.9 uses the explicit tracking/expiry snapshot and composite FK in §3.2 plus a unique non-lot origin bucket and separately linked quarantine buckets. These proposed constraints must be executed and tested before inventory activation.
   - **Proposed cross-row triggers in Appendix B.3:** Non-negative per-lot balance, cumulative return cap and transfer pairing. Lot-state-event synchronization and immutable movement/return disposition remain mandatory preflight tests; not proven by this text.

### 3.2 Proposed DDL

```sql
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
```

### 3.3 Semantics, transactions, authorization and tests

- **FEFO Ordering & Expiry Boundary:** Eligible lots must have `lot_status = 'AVAILABLE'` and `expires_on IS NULL OR expires_on >= authoritative_tehran_business_date` (valid through end of `expires_on` in `Asia/Tehran`, using command business date rather than DB session `CURRENT_DATE`). Deterministic sort order: `expires_on ASC NULLS LAST, received_at_utc ASC, id ASC`.
- **Balances & Reservations:** $\text{on\_hand}(L) = \sum \text{quantity\_delta}$. Future appointments or draft/posted invoices **never** automatically deduct or reserve stock. When `MOD_INVENTORY` has no reservation lifecycle enabled, display `reserved = 0` explicitly labeled as non-reserved.
- **Service Delivery & Insufficient Stock (Clause 826):** Stock deduction occurs on actual service delivery (`SERVICE_CONSUMPTION` linked to `service_records`) or explicit retail `SALE` linked to an `invoice_lines` item row. If eligible stock is insufficient, block completion/deduction by default (Clause 826) unless a manager invokes an explicitly audited, policy-authorized override.
- **Returns & Transfers:**
  - `RETURN` requires `original_movement_id` (`SERVICE_CONSUMPTION` or `SALE`), and cumulative returned quantity across all `RETURN` movements referencing that `original_movement_id` cannot exceed `ABS(original.quantity_delta)`.
  - `REUSABLE`: restores quantity to the original lot only if that lot is currently `AVAILABLE` and unexpired.
  - `QUARANTINE`: credits a linked `QUARANTINE` lot (`source_lot_id = original_lot_id`), never making quarantined stock available.
  - `WRITE_OFF`: atomically records `RETURN` (`+qty`) and matching `WRITE_OFF` (`-qty`) in the same UoW so net available stock does not increase.
  - `TRANSFER_OUT` (`-qty`) and `TRANSFER_IN` (`+qty`) share `transfer_operation_id` and must sum to `0` within the same UoW.
- **Locking:** Follows Rank 8 (`inventory_items` ASC $\rightarrow$ `inventory_lots` ASC) after any higher-precedence scheduling/visit/financial locks (§2.5).
- **Permissions & Entitlement:** `INVENTORY_VIEW`, `INVENTORY_RECEIVE`, `INVENTORY_CONSUME`, `INVENTORY_SELL`, `INVENTORY_RETURN`, `INVENTORY_ADJUST`, `INVENTORY_CONFIG`, `INVENTORY_LOT_DISPOSITION`. Disabled/expired `MOD_INVENTORY` lease blocks writes while preserving read-only access under license expiry policy.
- **Acceptance:** Task 28 #87–95 + FEFO tie-break, Tehran midnight expiry boundary, return cap race, quarantine return isolation, rollback of service completion on insufficient stock, and direct SQL balance-forge rejection. Candidate roadmap `TP0019` protected.

---

## 4. TP-OPS-WAITLIST — Future appointment requests

### 4.1 Model and Proposed DDL

A future-slot waitlist is strictly distinct from physical waiting-room presence (`clinic_visits` / `appointment_arrival_facts`, §7).

```sql
CREATE TABLE appointment_waitlist_entries (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  patient_id UUID NOT NULL,
  service_id UUID NOT NULL,
  department_id UUID NULL,
  preferred_resource_id UUID NULL,
  preferred_start_utc TIMESTAMPTZ NULL,
  preferred_end_utc TIMESTAMPTZ NULL,
  priority INT NOT NULL DEFAULT 100 CHECK (priority BETWEEN 1 AND 1000),
  status VARCHAR(24) NOT NULL CHECK (status IN ('OPEN', 'CONTACTED', 'CONVERTED', 'CANCELLED', 'EXPIRED')),
  contact_state VARCHAR(24) NOT NULL CHECK (contact_state IN ('NONE', 'PENDING', 'CONTACTED', 'UNREACHABLE', 'DECLINED')),
  converted_appointment_id UUID NULL,
  notes VARCHAR(500) NULL,
  created_by_user_id UUID NOT NULL,
  updated_by_user_id UUID NOT NULL,
  aggregate_version BIGINT NOT NULL CHECK (aggregate_version > 0),
  created_at_utc TIMESTAMPTZ NOT NULL,
  updated_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, converted_appointment_id),
  FOREIGN KEY (tenant_id, patient_id) REFERENCES patient_profiles(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, service_id) REFERENCES services(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, department_id) REFERENCES departments(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, preferred_resource_id) REFERENCES staff_practitioner_resources(tenant_id, bookable_resource_id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, converted_appointment_id, patient_id, service_id)
    REFERENCES appointments(tenant_id, id, beneficiary_patient_id, service_id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, created_by_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, updated_by_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL,
  CHECK (preferred_start_utc IS NULL OR preferred_end_utc IS NULL OR preferred_start_utc < preferred_end_utc),
  CHECK ((status = 'CONVERTED') = (converted_appointment_id IS NOT NULL))
);

CREATE INDEX waitlist_open_idx ON appointment_waitlist_entries(tenant_id, service_id, priority, created_at_utc, id)
  WHERE status IN ('OPEN', 'CONTACTED');
```

**Audit Correction Applied in D0.8:**
- Changed `preferred_resource_id` FK from `bookable_resources(tenant_id, id)` to `staff_practitioner_resources(tenant_id, bookable_resource_id)` so a room or device can never be stored as a preferred practitioner, and enforced terminal state immutability (`CONVERTED`, `CANCELLED`, `EXPIRED`) via `ops_terminal_state_guard()` in Appendix B.3.

### 4.2 Semantics, concurrency and authorization

- **Ordering & Capacity:** Ordered by `priority ASC, created_at_utc ASC, id ASC`. Preferred range holds **zero** scheduling capacity.
- **State Machine & Atomic Conversion:** Allowed transitions: `OPEN <-> CONTACTED`, and `{OPEN, CONTACTED} -> {CONVERTED, CANCELLED, EXPIRED}`. Terminal rows (`CONVERTED`, `CANCELLED`, `EXPIRED`) are immutable. Conversion executes the canonical scheduling booking handler and waitlist state update in a single local UoW under global lock order: Rank 2 (`service_availability_guards`, if applicable) $\rightarrow$ Rank 3 (`bookable_resources` $\rightarrow$ `appointments` $\rightarrow$ `appointment_resource_allocations`) $\rightarrow$ Rank 4 (`appointment_waitlist_entries`). Conversion outside `preferred_start_utc..preferred_end_utc` requires explicit operator confirmation flag in the command payload.
- **Permissions & Tests:** `WAITLIST_VIEW`, `WAITLIST_MANAGE`, `WAITLIST_CONVERT` with full scope enforcement (§6.3). Required tests (NOT RUN): concurrent conversion vs. cancellation, idempotent retry, rollback on scheduling conflict, and terminal immutability.

---

## 5. TP-OPS-ELIGIBILITY — Canonical staff and practitioner resource identity

### 5.1 Authoritative basis and DDL

Grounded in §52 Clause 762 (staff profile independent of optional login) and §53 Clauses 776–783 (atomic resources and AND/OR requirement groups). Enforces a strict 1:1 mapping between `staff_profiles` and `bookable_resources` (`resource_type = 'PRACTITIONER'`) so multi-skilled practitioners share one capacity pool and cannot double `ONLINE` capacity.

```sql
CREATE TABLE staff_practitioner_resources (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  staff_profile_id UUID NOT NULL,
  bookable_resource_id UUID NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at_utc TIMESTAMPTZ NOT NULL,
  updated_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, staff_profile_id),
  UNIQUE (tenant_id, bookable_resource_id),
  FOREIGN KEY (tenant_id, staff_profile_id) REFERENCES staff_profiles(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, bookable_resource_id) REFERENCES bookable_resources(tenant_id, id) MATCH FULL
);

CREATE TABLE staff_service_links (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  practitioner_mapping_id UUID NOT NULL,
  service_id UUID NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  aggregate_version BIGINT NOT NULL CHECK (aggregate_version > 0),
  created_at_utc TIMESTAMPTZ NOT NULL,
  updated_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, practitioner_mapping_id, service_id),
  FOREIGN KEY (tenant_id, practitioner_mapping_id) REFERENCES staff_practitioner_resources(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, service_id) REFERENCES services(tenant_id, id) MATCH FULL
);

CREATE INDEX staff_service_eligible_idx ON staff_service_links(tenant_id, service_id, practitioner_mapping_id)
  WHERE is_active;
```

### 5.2 Invariants and concurrency

- **Immutable Identity & Resource Type Guard:** Appendices B.3/B.4 propose enforcement via `ops_practitioner_mapping_guard()` and `ops_bookable_resource_type_guard()` that `bookable_resources.resource_type = 'PRACTITIONER'` on insert/update and that `staff_profile_id` and `bookable_resource_id` on `staff_practitioner_resources` cannot be mutated after creation.
- **Booking & Grandfathering Policy:** New bookings and reschedules/re-allocations validate active `staff_practitioner_resources.is_active = TRUE` and active `staff_service_links.is_active = TRUE` under Rank 2 (`service_availability_guards`) + Rank 3 (`bookable_resources`) locks. Historical bookings created prior to eligibility activation remain valid unless rescheduled or re-allocated.
- **Permissions & Lineage:** `CATALOG_PRACTITIONER_ELIGIBILITY_MANAGE`. Candidate roadmap `TP0011` remains protected for `TP0004` atomic-resource constraints only; these new tables land in their reconciled schema revision (§11).

---

## 6. TP-OPS-SCOPES — Department, permission scope and supervision

### 6.1 Department semantics and DDL

Internal clinic departments are operational groupings within a single tenant (Clause 752), never multi-branch or multi-tenant boundaries. Small clinics with zero departments operate normally with `department_id IS NULL`.

```sql
CREATE TABLE departments (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  department_code VARCHAR(64) NOT NULL,
  department_name VARCHAR(200) NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  aggregate_version BIGINT NOT NULL CHECK (aggregate_version > 0),
  created_at_utc TIMESTAMPTZ NOT NULL,
  updated_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, department_code)
);

CREATE TABLE department_service_links (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  department_id UUID NOT NULL,
  service_id UUID NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at_utc TIMESTAMPTZ NOT NULL,
  updated_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, department_id, service_id),
  FOREIGN KEY (tenant_id, department_id) REFERENCES departments(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, service_id) REFERENCES services(tenant_id, id) MATCH FULL
);

CREATE TABLE department_practitioner_links (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  department_id UUID NOT NULL,
  practitioner_mapping_id UUID NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at_utc TIMESTAMPTZ NOT NULL,
  updated_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, department_id, practitioner_mapping_id),
  FOREIGN KEY (tenant_id, department_id) REFERENCES departments(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, practitioner_mapping_id) REFERENCES staff_practitioner_resources(tenant_id, id) MATCH FULL
);

ALTER TABLE appointments ADD COLUMN department_id UUID NULL;
ALTER TABLE appointments ADD CONSTRAINT appointments_department_fk
  FOREIGN KEY (tenant_id, department_id) REFERENCES departments(tenant_id, id) MATCH SIMPLE;
```

### 6.2 Scope schema tied to actual `TP0003` grants

Ties typed scopes directly to `role_permission_assignments(tenant_id, id)` from `TP0003`.

```sql
CREATE TABLE role_permission_scopes (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  role_permission_assignment_id UUID NOT NULL,
  scope_mode VARCHAR(16) NOT NULL CHECK (scope_mode IN ('ALL', 'FILTER')),
  department_id UUID NULL,
  service_id UUID NULL,
  provider_resource_id UUID NULL,
  created_by_user_id UUID NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE NULLS NOT DISTINCT (tenant_id, role_permission_assignment_id, scope_mode, department_id, service_id, provider_resource_id),
  FOREIGN KEY (tenant_id, role_permission_assignment_id) REFERENCES role_permission_assignments(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, department_id) REFERENCES departments(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, service_id) REFERENCES services(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, provider_resource_id) REFERENCES bookable_resources(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, provider_resource_id) REFERENCES staff_practitioner_resources(tenant_id, bookable_resource_id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, created_by_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL,
  CHECK (
    (scope_mode = 'ALL' AND department_id IS NULL AND service_id IS NULL AND provider_resource_id IS NULL)
    OR (scope_mode = 'FILTER' AND (department_id IS NOT NULL OR service_id IS NOT NULL OR provider_resource_id IS NOT NULL))
  )
);

CREATE INDEX role_permission_scopes_grant_idx ON role_permission_scopes(tenant_id, role_permission_assignment_id);
```

- **Mutual Exclusivity Enforced in Appendix B.3:** `ops_role_permission_scope_guard()` locks the parent `role_permission_assignments` row `FOR UPDATE` and rejects any `ALL` + `FILTER` coexistence on the same grant.

### 6.3 Formal authorization semantics

For an active `user_accounts` principal $U$ in verified tenant $T$ and operation permission $P$:
1. **Default Deny:** If $U$ holds no active role grant for $P$, or the matching `role_permission_assignments` rows have **zero** rows in `role_permission_scopes`, access is **DENIED**.
2. **Within-row AND:** a FILTER row matches a department/service pair iff each non-NULL scope dimension equals the verified target dimension; NULL target never matches a non-NULL restriction. For a particular practitioner r, a NULL provider restriction matches any practitioner and a non-NULL restriction matches only r.
3. **Across-grant OR, across practitioners AND:** ALL on any active grant for the requested permission authorizes that operation within its tenant, subject to all other state, entitlement and purpose checks. Otherwise, when the target has a nonempty relevant practitioner set, every practitioner must be covered by at least one FILTER row that also matches the same verified department/service pair. A match for one practitioner does not authorize the whole appointment. When the practitioner set is empty, only a FILTER row with NULL provider restriction can match. Use the same predicate for lists/counts/full details/mutations; partial projections require their own explicit privacy contract. A write that changes scope must cover both old and new facts. Never derive the complete practitioner set from client input alone.
4. **Global / Administrative Commands:** Any command lacking target $(d_O, s_O, R_O)$ dimensions requires `scope_mode = 'ALL'`.
5. **Anti-Escalation & Delegation Bounds:**
   - All role, permission, and scope mutations acquire Rank 1 (tenant governance serialization lock) and evaluate semantic coverage before and after mutation.
   - An actor cannot grant a permission $P$ or scope coverage $C_{\text{new}}$ that exceeds the actor's own delegable coverage for $P$ (`ALL` cannot be delegated by a `FILTER`-only actor; union of delegated `FILTER` rows must be a semantic subset of the actor's coverage).
   - Cannot remove, deactivate, or strip owner governance authority from the **last active login-capable owner** in the tenant.
   - No direct self-role/self-scope elevation, including through editing a role assigned to oneself. Owner-target actions require explicit owner authority and must preserve a last active login-capable owner. Validate every affected member of a changed role, not just the changed permission. Lock authority and re-evaluate delegation and target coverage before write. Do not equate owner status with implicit business permissions.

### 6.4 Object and operation enforcement matrix

| Object / Operation | Required Server-Side Scope & Privacy Enforcement |
|---|---|
| Dashboard, lists, calendar, KPIs | Apply scope predicate on base query **before** `COUNT`/`GROUP BY`/pagination; zero cross-scope count leakage |
| Appointment detail / create / move | Validate requested `service_id`, `department_id`, and complete practitioner set (both old and new scopes on move); atomic across entire `reception_group` |
| Manual overlap (`Clause 779`) | Compute complete conflict set server-side; display full safe details for in-scope conflicts; redact out-of-scope conflicts to time window + resource + redacted marker; bind opaque acknowledgement token to full conflict hash |
| Patient search / dossier | Canonical person shared across clinic; return authorized encounter/invoice projection only; mask National ID/phone according to purpose and permission |
| Prospective patient booking | Minimum safe identity lookup (`PROSPECTIVE_PATIENT_LOOKUP`) returns disambiguation confirmation only without exposing out-of-scope visit/financial history; duplicate identifier blocks creation without leaking unrelated dossier |
| Combined invoices & cashier | Mutations (`POST`, `VOID`, `DISCOUNT`, `ADJUST`, `ALLOCATE`, `REFUND`) require coverage of **all** lines, allocations, departments, and practitioners on the invoice; partial read visibility returns safe authorized line projection without leaking unauthorized line details or global invoice totals |
| Visits & future waitlist | Scope enforced on linked appointment/service/department/provider; patient presence count deduplicated by `visit_id` after scope filtering |
| Operational notes, tags & alerts | Staff-only permission + patient relationship + note/tag `(department_id, service_id)` scope; global unscoped notes (`department_id IS NULL AND service_id IS NULL`) visible only to explicitly authorized global-note roles |
| Reports, exports & management audit | Scope applied prior to aggregation; tenant-wide cross-user audit overview (`AUDIT_OPERATIONS_VIEW` / `AUDIT_OPERATIONS_EXPORT`) requires `scope_mode = 'ALL'` |

### 6.5 Migration activation and role governance

- **Explicit Activation Cutover:** Inventory existing `TP0003` grants, assign explicit `ALL` rows only to approved tenant-wide roles (such as general receptionist/manager), assign `FILTER` rows to scoped roles, deploy scope-aware API/workers, drain legacy workers, and invalidate permission caches before enabling scoped accounts.
- `HEAD_RECEPTIONIST` is an optional explicit software role name used for operational dashboard composition; it grants zero implicit privileges beyond its explicit `role_permission_assignments` and `role_permission_scopes`.

**Activation invariant:** prior flat grants do not automatically become ALL. Review grants and active owners, backfill explicitly, reconcile provisional codes with the canonical catalog and disable every legacy unscoped route before scoped access is enabled. Role scope revocation, in-flight writes, self-escalation via shared role, and cross-account cache tests are required. No cross-user audit for ordinary receptionists. In Task 32 the audit endpoint returns `details_json` as-is and joins current `login_identifier`; before claiming safe audit review, use an allowlisted read projection per event kind, safe historical actor identity, date/user/reference filters, bounded query, and tests for legacy free-text PII. Existing raw audit facts are not silently rewritten. No new audit table.

### 6.6 Management audit review

- Exposes bounded, keyset-paginated (`(created_at_utc DESC, id DESC)`) read and audited export endpoints directly over existing `TP0006` append-only audit records (`AUDIT_OPERATIONS_VIEW`, `AUDIT_OPERATIONS_EXPORT`). Zero second audit table. Never stores raw National IDs, phones, or note bodies in audit metadata.

---

## 7. TP-OPS-ARRIVAL — Reception grouping, actual arrival, service records and historical entry

### 7.1 Model and audit corrections

Grounded in §50 Clauses 695, 725–726 and §53 Clauses 781–783:
- Preserves existing `CHECKED_IN` appointments lacking arrival timestamps as `"check-in recorded; arrival time unavailable"` without fabricating `arrived_at_utc` or wait durations.
- Separates:
  1. `reception_groups` / `reception_group_appointments`: atomic multi-service booking association for one patient across one or more dates (not a physical arrival).
  2. `clinic_visits` / `visit_appointments`: physical admission (`admission_at_utc`), physical presence (`arrived_at_utc`), and departure (`departed_at_utc`).
  3. `appointment_arrival_facts`: per-appointment check-in fact (`checked_in_at_utc`) bound to `(visit_id, appointment_id)`.
  4. `service_records` / `service_record_practitioners`: actual service delivery or operational record (`PERFORMED` vs. `OPERATIONAL_RECORD`).
  5. `historical_appointment_entries`: explicit late-entry audit and reminder suppression (`suppress_past_reminders = TRUE`).

### 7.2 Proposed DDL

```sql
ALTER TABLE appointments ADD CONSTRAINT appointments_patient_service_uq
  UNIQUE (tenant_id, id, beneficiary_patient_id, service_id);
ALTER TABLE appointments ADD CONSTRAINT appointments_patient_uq
  UNIQUE (tenant_id, id, beneficiary_patient_id);

CREATE TABLE reception_groups (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  patient_id UUID NOT NULL,
  created_by_user_id UUID NOT NULL,
  correlation_id UUID NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, id, patient_id),
  FOREIGN KEY (tenant_id, patient_id) REFERENCES patient_profiles(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, created_by_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL
);

CREATE TABLE reception_group_appointments (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  group_id UUID NOT NULL,
  patient_id UUID NOT NULL,
  appointment_id UUID NOT NULL,
  line_key VARCHAR(128) NOT NULL,
  line_no INT NOT NULL CHECK (line_no > 0),
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, appointment_id),
  UNIQUE (tenant_id, group_id, line_key),
  UNIQUE (tenant_id, group_id, line_no),
  FOREIGN KEY (tenant_id, group_id, patient_id) REFERENCES reception_groups(tenant_id, id, patient_id) MATCH FULL,
  FOREIGN KEY (tenant_id, appointment_id, patient_id) REFERENCES appointments(tenant_id, id, beneficiary_patient_id) MATCH FULL
);

CREATE TABLE clinic_visits (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  patient_id UUID NOT NULL,
  admission_at_utc TIMESTAMPTZ NOT NULL,
  arrived_at_utc TIMESTAMPTZ NULL,
  departed_at_utc TIMESTAMPTZ NULL,
  registered_by_user_id UUID NOT NULL,
  departed_by_user_id UUID NULL,
  historical_reason VARCHAR(200) NULL,
  aggregate_version BIGINT NOT NULL CHECK (aggregate_version > 0),
  created_at_utc TIMESTAMPTZ NOT NULL,
  updated_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, id, patient_id),
  FOREIGN KEY (tenant_id, patient_id) REFERENCES patient_profiles(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, registered_by_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, departed_by_user_id) REFERENCES user_accounts(tenant_id, id) MATCH SIMPLE,
  CHECK (
    (departed_at_utc IS NULL AND departed_by_user_id IS NULL)
    OR (departed_at_utc IS NOT NULL AND arrived_at_utc IS NOT NULL AND departed_at_utc >= arrived_at_utc AND departed_by_user_id IS NOT NULL)
  )
);

CREATE TABLE visit_appointments (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  visit_id UUID NOT NULL,
  patient_id UUID NOT NULL,
  appointment_id UUID NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, appointment_id),
  UNIQUE (tenant_id, visit_id, appointment_id),
  FOREIGN KEY (tenant_id, visit_id, patient_id) REFERENCES clinic_visits(tenant_id, id, patient_id) MATCH FULL,
  FOREIGN KEY (tenant_id, appointment_id, patient_id) REFERENCES appointments(tenant_id, id, beneficiary_patient_id) MATCH FULL
);

CREATE TABLE appointment_arrival_facts (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  visit_id UUID NOT NULL,
  appointment_id UUID NOT NULL,
  checked_in_at_utc TIMESTAMPTZ NOT NULL,
  operator_user_id UUID NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, appointment_id),
  FOREIGN KEY (tenant_id, visit_id, appointment_id) REFERENCES visit_appointments(tenant_id, visit_id, appointment_id) MATCH FULL,
  FOREIGN KEY (tenant_id, operator_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL
);

CREATE TABLE service_records (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  patient_id UUID NOT NULL,
  service_id UUID NOT NULL,
  appointment_id UUID NULL,
  visit_id UUID NULL,
  department_id UUID NULL,
  record_kind VARCHAR(24) NOT NULL CHECK (record_kind IN ('PERFORMED', 'OPERATIONAL_RECORD')),
  occurred_at_utc TIMESTAMPTZ NOT NULL,
  reason_code VARCHAR(64) NULL,
  operator_user_id UUID NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, id, patient_id, service_id),
  FOREIGN KEY (tenant_id, patient_id) REFERENCES patient_profiles(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, service_id) REFERENCES services(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, appointment_id, patient_id, service_id) REFERENCES appointments(tenant_id, id, beneficiary_patient_id, service_id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, visit_id, patient_id) REFERENCES clinic_visits(tenant_id, id, patient_id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, department_id) REFERENCES departments(tenant_id, id) MATCH SIMPLE,
  FOREIGN KEY (tenant_id, operator_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL,
  CHECK (record_kind = 'PERFORMED' OR reason_code IS NOT NULL)
);

CREATE UNIQUE INDEX performed_record_per_appointment_uq ON service_records(tenant_id, appointment_id)
  WHERE appointment_id IS NOT NULL AND record_kind = 'PERFORMED';

CREATE TABLE service_record_practitioners (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  service_record_id UUID NOT NULL,
  practitioner_mapping_id UUID NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, service_record_id, practitioner_mapping_id),
  FOREIGN KEY (tenant_id, service_record_id) REFERENCES service_records(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, practitioner_mapping_id) REFERENCES staff_practitioner_resources(tenant_id, id) MATCH FULL
);

CREATE TABLE historical_appointment_entries (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  appointment_id UUID NOT NULL,
  late_entry_reason VARCHAR(200) NOT NULL CHECK (length(btrim(late_entry_reason)) > 0),
  reported_occurrence_at_utc TIMESTAMPTZ NULL,
  suppress_past_reminders BOOLEAN NOT NULL DEFAULT TRUE CHECK (suppress_past_reminders),
  operator_user_id UUID NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, appointment_id),
  FOREIGN KEY (tenant_id, appointment_id) REFERENCES appointments(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, operator_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL
);

CREATE INDEX clinic_visits_patient_time_idx ON clinic_visits(tenant_id, patient_id, admission_at_utc DESC, id);
CREATE INDEX clinic_visits_present_idx ON clinic_visits(tenant_id, arrived_at_utc, id) WHERE departed_at_utc IS NULL;
CREATE INDEX service_records_patient_time_idx ON service_records(tenant_id, patient_id, occurred_at_utc DESC, id);
```

### 7.3 Arrival, waiting room, completion and historical entry semantics

- **Physical Waiting Room Definition:** A patient is physically waiting if and only if `clinic_visits.arrived_at_utc IS NOT NULL AND clinic_visits.departed_at_utc IS NULL` and the visit links at least one active checked-in appointment not yet completed/cancelled/no-show. Unique waiting patients/visits are counted separately from service rows. Wait duration is `server_now_utc - COALESCE(appointment_arrival_facts.checked_in_at_utc, clinic_visits.arrived_at_utc)`.
- **Canonical State Transitions & Deferred Integrity (Appendix B.3):**
  - Transitioning an appointment to `CHECKED_IN` requires an `appointment_arrival_facts` row and `clinic_visits.arrived_at_utc IS NOT NULL` in the same UoW (enforced by deferred trigger `ops_appointment_lifecycle_facts_guard()` while grandfathering pre-existing rows).
  - Transitioning an appointment to `COMPLETED` requires a `service_records` row with `record_kind = 'PERFORMED'` in the same UoW (enforced by `ops_appointment_lifecycle_facts_guard()`). Never auto-complete from elapsed scheduled end time.
- **Historical Late Entry (`APPOINTMENTS_HISTORICAL_ENTRY`):** Records `historical_appointment_entries` with current server `created_at_utc`, operator, and `late_entry_reason`. Notification workers check `NOT EXISTS (SELECT 1 FROM historical_appointment_entries ... WHERE suppress_past_reminders)` before dispatching reminders. Never creates live holds or fake receipts.

---

## 8. TP-OPS-ONLINE-CLOSE — Temporary online availability closure

### 8.1 Source, policy and DDL

Preserves §53 Clauses 776–790 and `ONLINE` GiST exclusion unchanged. `MANUAL` overbooking remains unaffected.

```sql
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
```

### 8.2 Serialization, active holds and distributed authority

1. **Global Lock Order Integration (Rank 2 $\rightarrow$ Rank 3):**
   - `service_availability_guards` is **Rank 2**, strictly preceding Rank 3 (`bookable_resources` $\rightarrow$ `appointments` $\rightarrow$ `appointment_resource_allocations`).
   - Every `ONLINE` booking, `ONLINE` reschedule/re-acquisition, closure/reopen command, and practitioner eligibility mutation acquires `service_availability_guards` ordered by `service_id ASC` **before** acquiring any Rank 3 locks.
   - Background hold-expiration workers never acquire Rank 2 locks (they operate strictly on Rank 3), preventing any lock-order inversion.
   - All legacy writers must be drained before activating `online_availability_closures`.
2. **Existing Bookings, Active Holds & Late Callbacks (Clauses 784–786):**
   - New `ONLINE` reservations overlapping `[starts_at_utc, ends_at_utc)` (`reopened_at_utc IS NULL`) for `(service_id, resource_id)` or service-wide `(service_id, NULL)` fail closed.
   - Existing confirmed bookings and already-issued active holds are **not** cancelled; valid holds convert under normal hold conversion rules.
   - Late verified payment callbacks arriving after `EXPIRED_HOLD` follow Clauses 784–786: if a closure is active for that slot, fresh capacity reacquisition is blocked and the verified receipt is retained as patient credit or refunded via explicit authorized refund.
3. **Cloud Authority Boundary (`Gate A`):**
   - Online availability is Cloud-authoritative. Local Hub UI must not claim offline closure has closed external online channels until Cloud sync/authority (`TP0014` / `Gate A`) is verified. Synthetic tests execute on a single authoritative node with explicit labeling.
4. **Permissions:** `ONLINE_AVAILABILITY_CLOSE`, `ONLINE_AVAILABILITY_REOPEN`, `ONLINE_AVAILABILITY_VIEW`. Reopen immutability enforced by `ops_terminal_state_guard()` in Appendix B.3.

---

## 9. TP-OPS-NOTES — Patient operational notes, tags and pinned alerts

Staff-only reception annotations (zero clinical diagnosis or prescribing). Append-only notes and actions; terminal retractions enforced by `ops_note_action_guard()` in Appendix B.3.

```sql
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
```

- **Permissions & Privacy:** `PATIENT_OPERATIONAL_NOTES_VIEW`, `PATIENT_OPERATIONAL_NOTES_MANAGE`, `PATIENT_OPERATIONAL_NOTES_PIN`, `PATIENT_TAGS_MANAGE`, `CATALOG_STAFF_TAGS_MANAGE`. Note bodies are excluded from outbox payloads, logs, and audit detail JSON; erasure/retention (§§55–57) applies to stored note rows.

---

## 10. Identity completion, correction, canonical/alias merge and non-production keys

### 10.1 Existing F.2 contract and non-production crypto boundary

- Grounded in §52 Clauses 755–773 and Appendix F.2 (`person_identifiers`, `person_phones`):
  - Absence of an Iranian National ID never blocks patient profile creation (Clause 755). Normalize ASCII digits and preserve leading zeros; Mod11 syntax validation is format validation only, never government verification.
  - FIDA and foreign passport formats require independent issuer rules; no blanket 12-digit assumption.
  - Phone numbers (E.164) support shared-family non-unique lookup; never merge persons based on shared phone.
- **Crypto Boundary (`OI-04` / `OI-05`; Gate A implementation, Gate B KMS/provider evidence, Gate D production readiness):**
  - Production KMS provider evidence remains Gate B; AES/HMAC rotation implementations and concurrency tests are engineering Open Items under Gate A, not waived or reclassified as exclusively production-only. Production rollout remains Gate D.
  - Non-production synthetic environments enforce fail-closed environment refusal outside `test`/`dev`/`local`/`preview`, isolated non-production keys, and **fresh random 96-bit GCM nonces per encryption call** even on deterministic fixture seeds.

Retain verified actual F.2 field names, 96-bit random nonces, 128-bit tags, encryption version/AAD version, tenant/person/record/type/authority binding, domain-separated HMAC, separate independent key lifecycles and active/next uniqueness. POST lookup protects URL privacy but does not prove request bodies, error logging, browser history/cache or analytics are safe. Check missing key/refusal, AAD tamper, concurrent duplicate ID and shared-phone tests. No production key reuse; no external contacts. Staff login remains OFF by default and independent from patient identity.

### 10.2 Identity completion and corrections

```sql
CREATE TABLE patient_identity_reviews (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  patient_id UUID NOT NULL,
  review_state VARCHAR(24) NOT NULL CHECK (review_state IN ('NEEDS_COMPLETION', 'RESOLVED', 'CANCELLED')),
  reason VARCHAR(200) NOT NULL CHECK (length(btrim(reason)) > 0),
  opened_by_user_id UUID NOT NULL,
  opened_at_utc TIMESTAMPTZ NOT NULL,
  resolved_by_user_id UUID NULL,
  resolved_at_utc TIMESTAMPTZ NULL,
  resolution_reason VARCHAR(200) NULL,
  aggregate_version BIGINT NOT NULL CHECK (aggregate_version > 0),
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  FOREIGN KEY (tenant_id, patient_id) REFERENCES patient_profiles(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, opened_by_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, resolved_by_user_id) REFERENCES user_accounts(tenant_id, id) MATCH SIMPLE,
  CHECK (
    (review_state = 'NEEDS_COMPLETION' AND resolved_by_user_id IS NULL AND resolved_at_utc IS NULL AND resolution_reason IS NULL)
    OR (review_state IN ('RESOLVED', 'CANCELLED') AND resolved_by_user_id IS NOT NULL AND resolved_at_utc IS NOT NULL
        AND resolved_at_utc >= opened_at_utc AND resolution_reason IS NOT NULL AND length(btrim(resolution_reason)) > 0)
  )
);

CREATE UNIQUE INDEX patient_identity_open_review_uq ON patient_identity_reviews(tenant_id, patient_id)
  WHERE review_state = 'NEEDS_COMPLETION';
```

- Terminal states (`RESOLVED`, `CANCELLED`) are immutable (proposed Appendix B.3). Administrative resolution never implies government identity verification. Absence of a review row or identifier cannot block patient profile creation under Clause 755. A reason is encouraged or recorded via approved review without inventing dummy identifiers. Identity correction is permission-protected, audit-attributed, uniqueness-checked, AAD-safe and history-preserving; historical unknown reason remains unknown. Do not destructively merge or change staff/governance/login references.

### 10.3 Canonical/alias merge (`SOURCE_REQUIRED` — Clause 773)

- Clause 773 mandates continuity with the v1.3 canonical/alias person model. The exact v1.3 canonical/alias schema/source is not attached to this audit (**`SOURCE_REQUIRED`**).
- Candidate audit event table retained below; **cannot** be shipped alone as proof of canonical/alias merge completion:

```sql
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
```

- Merge requirements once v1.3 source is attached: acyclic canonical alias resolution, serialization of involved person records, re-validation of encrypted/blind-indexed identifiers with proper AAD re-binding, preservation of historical appointments/invoices/receipts/refunds, denial when merging conflicting staff/login/governance accounts without ratified collision policy, and full erasure/audit continuity.

---

## 11. Recommended logical dependency DAG (not assigned revision IDs)

| Topological Step | Logical Contract Package | Upstream Schema Dependencies | Candidate Roadmap Alignment (`S4`) |
|---|---|---|---|
| **0** | Preflight verification (`SOURCE_REQUIRED` reconciliation) | Pinned baseline `8309f2a`, `TP0001–TP0007` | Verify live Alembic heads, latest approved roadmap, `SRC-10`, `SRC-12`, v1.3 alias source |
| **1** | Identity, KMS/key policy & versioned permission catalog snapshots | `TP0003`, `TP0006`, `TP0007` | Reconcile `TP0008–TP0010` |
| **2** | Atomic resource constraints/triggers (`TP0004` completion) | `TP0004`, `TP0005` | Protect `TP0011` (zero unrelated tables) |
| **3** | Canonical practitioner mapping, service eligibility & departments (`§5`, `§6.1`) | `staff_profiles`, `bookable_resources`, `services`, `appointments` | Reconcile exact placement (`SOURCE_REQUIRED`); do not repurpose `TP0011` |
| **4** | Typed grant scopes, operational notes/tags & identity completion reviews (`§6.2`, `§9`, `§10.2`) | Step 3 (`departments`, `staff_practitioner_resources`) + `TP0003` (`role_permission_assignments`) | Reconcile placement (`SOURCE_REQUIRED`); activate scope resolver only after full cutover |
| **5** | Reception groups, visits, arrival facts, service records, historical entries, waitlist & online closure guards (`§4`, `§7`, `§8`) | Step 3 (`departments`, `staff_practitioner_resources`) + `appointments` composite UQs | Reconcile `TP0012–TP0013` + Rank 2 lock order |
| **6** | Sync envelope, inbox deduplication & node authority (`§12.1`) | `TP0006` outbox/inbox | Protect `TP0014` (`Gate A` required for multi-node sync) |
| **7** | Operational billing & cashier ledger (`billable_items`, shifts, instruments, invoices, lines, attempts, claims, receipts, guards, allocations, adjustments, refunds, insurers, revenue share — `§2`, `Appendix B`) | Step 3 (`departments`, `staff_practitioner_resources`) + Step 5 (`clinic_visits`, `reception_groups`, `service_records`, `appointments` composite UQs) | Reconcile `TP0015–TP0017` |
| **8** | Notification gating & historical reminder suppression | Step 5 (`historical_appointment_entries`) | Protect `TP0018` |
| **9** | Optional `MOD_INVENTORY` FEFO stock ledger (`§3`, `Appendix B.3`) | Step 5 (`service_records`) + Step 7 (`billable_items`, `invoice_lines`) | Reconcile `TP0019` |
| **10** | Canonical/alias merge (`§10.3`) & remaining modules | v1.3 alias source (`SOURCE_REQUIRED`) | Preserve `TP0020–TP0021` for CMS/Portal/CSAT; merge placement requires v1.3 and approved lineage, not reuse of these reservations. |

**Upgrade Discipline:** Additive expand $\rightarrow$ dual-compatible code deploy $\rightarrow$ drain legacy workers $\rightarrow$ enable triggers/guards $\rightarrow$ contract. Zero fabricated backfills. Upgrade-only Tenant Plane migrations; zero Control Plane revisions.

---

## 12. Compatibility, sync, outbox, security and external evidence

### 12.1 Compatibility and distributed authority

- Existing `appointments` PKs, `ONLINE`/`MANUAL` channel semantics, and `TP0005` GiST exclusion remain untouched.
- Candidate outbox event families (emitted in same UoW as business state and audit): `reception.group.created`, `appointment.arrived`, `appointment.completed`, `appointment.no_show`, `appointment.cancelled`, `appointment.rescheduled`, `waitlist.created`, `waitlist.updated`, `waitlist.converted`, `eligibility.changed`, `scope.changed`, `invoice.posted`, `invoice.voided`, `receipt.recorded`, `receipt.beneficiary_attributed`, `allocation.applied`, `allocation.reversed`, `adjustment.recorded`, `clinic_refund.recorded`, `insurer_settlement.recorded`, `revenue_share.adjusted`, `stock.movement.recorded`, `stock.lot_state.changed`, `availability.closed`, `availability.reopened`, `patient.identity_review.changed`, `patient.note.changed`.
- Outbox payloads contain opaque IDs, versions, and safe domain codes only — **never** raw National IDs, phone numbers, credentials, or note bodies.
- All new entities participate in tenant erasure/retention (§§55–57), backup/restore, and `Gate D` lifecycle policies.

### 12.2 External evidence and explicit exclusions

- Remaining external/source gates (strictly separated from synthetic workspace implementation):
  - **`SOURCE_REQUIRED` (Repo/Spec):** Latest approved roadmap beyond `R4.6`, live Alembic heads (`tp0008+` / `F2-B`), v1.3 canonical/alias person model (`Clause 773`), `SRC-10` (`Clause 739` legacy report semantics), and `SRC-12` live `main` baseline.
  - **`Gate A`:** Explicitly initiated isolated engineering, additive migrations, integration/security/concurrency tests, including multi-node sync authority and offline policy. Independent safe single-node development need not await external Gates B/C. No Gate A closure inferred.
  - **`Gate B`:** Verified external payment, SMS, KMS/key storage, object storage, backup and other production providers, including live POS and card-to-card evidence adapters/callbacks.
  - **`Gate C`:** Written legal/tax/commercial and retention/privacy approvals. External insurer API capability/adapter evidence belongs to Gate B when applicable; insurer policy and legal decisions are separately classified. No statutory e-invoicing claim.
  - **`Gate D`:** Production authorization, operational security, recovery and pilot readiness after applicable A/B/C evidence and explicit written approval. OI-04/05 engineering work remains under Gate A; provider KMS evidence under B.

---

## 13. Consolidated ratification and preflight checklist

- [ ] **1. Operational Ledger & Arithmetic (`§2`, `Appendix B`):** Ratify self-pay-first operational billing, strict separation of attempts/claims/receipts/allocations/reversals/adjustments/refunds, largest-remainder proportional discount arithmetic, and complete cross-row constraint triggers.
- [ ] **2. Optional FEFO Inventory (`§3`, `Appendix B.3`):** Ratify independent `billable_items`, `MOD_INVENTORY` entitlement gating, `Asia/Tehran` end-of-day expiry boundary, and movement/return/transfer invariants.
- [ ] **3. Practitioner Eligibility & Departments (`§5`, `§6.1`):** Ratify 1:1 `staff_practitioner_resources`, M:N `staff_service_links`, and optional internal clinic departments (`NULL`-safe).
- [ ] **4. Typed Scopes & Anti-Escalation (`§6.2–6.6`):** Ratify `role_permission_scopes` tied to `TP0003` grant IDs, within-row `AND` / across-row `OR` semantics, explicit `ALL` backfill review, `HEAD_RECEPTIONIST` non-privileged role label, and Rank 1 governance serialization.
- [ ] **5. Arrival, Service Records & Waitlist (`§4`, `§7`):** Ratify `reception_groups`, `clinic_visits`, `appointment_arrival_facts`, `service_records`, `historical_appointment_entries` (grandfathering legacy `CHECKED_IN`), and distinct future-slot `appointment_waitlist_entries`.
- [ ] **6. Temporary Online Closure (`§8`):** Ratify `service_availability_guards` Rank 2 lock placement, `Asia/Tehran` single-day closure bounds, active-hold preservation, and Cloud-authoritative boundary.
- [ ] **7. Notes, Tags & Identity Review (`§9`, `§10.2`):** Ratify append-only notes/actions, scoped tags, and `patient_identity_reviews` (keeping canonical merge gated on v1.3 source).
- [ ] **8. Lineage & `SOURCE_REQUIRED` Preflight (`§0.2`, `§11`):** Reconcile latest approved roadmap, live Alembic heads, `TP0011` protection, v1.3 canonical/alias source, and `SRC-10` before assigning concrete revision IDs.
- [ ] **9. Non-Production Crypto Policy (`§10.1`):** Ratify isolated non-production AES-GCM/HMAC test keys with fresh random nonces and zero external provider calls.
- [ ] **10. Independent Convergence:** Confirm final revised contract convergence before authorizing synthetic development migrations. Separate explicit approval for disposable validation-only execution from implementation migration approval.

---

## 14. Implementation continuation and acceptance (Task 28 remains OPEN)

### 14.1 Rich demo dataset requirements

- Preserve `demo` (default) and `minimal` (fast CI isolation) profiles with tenant-salted deterministic UUIDs and fresh random GCM nonces.
- Maintain baseline coverage (`520` patients, `42` staff, `32` services, `10,500` appointments, `344` test-day appointments, `110` tomorrow, `110` reception groups, `32` manual overlap pairs, `32` shared-phone families, `32` exceptional identity cases, `5,200` audit entries) and extend with real relational facts once approved migrations land:
  - $\ge 30$ approved foreign identity scenarios (`patient_identity_reviews` + `person_identifiers`).
  - $\ge 10$ multi-skilled practitioners (`staff_practitioner_resources` + multiple `staff_service_links`).
  - $\ge 30$ physically arrived/waiting patients (`clinic_visits` + `appointment_arrival_facts`).
  - $\ge 30$ future waitlist requests (`appointment_waitlist_entries`).
  - $\ge 2,000$ synthetic posted invoices, $\ge 100$ discount scenarios, $\ge 100$ partial/full refund & reversal scenarios, and $\ge 100$ inventory items/lots/movements reconciled on PostgreSQL 15.
- Windows one-command launcher (`-NoBrowser` supported) must verify Docker readiness, auto-open current URL, leave zero tracked runtime artifacts, and be tested on Windows host (or explicitly marked `NOT RUN`).

Existing counts are the earlier handoff snapshot, not immutable date targets: `appointments_today=344` was observed on the test day; enforce the original minimum (>=220 in current demo profile), relative to Tehran. Prior threshold tests do not establish that fixture note groups are true reception-group facts or CHECKED_IN means actual physical arrival. Preserve 68 prior National ID and 520 phone rows as reported history; extend coverage with valid synthetic identities, distinct patients, full scenario diversity and at least 20–30 meaningful examples per supported category. Include unpaid/partial/paid, discounts at both scopes, refunded versus merely cancelled, upcoming/past/elapsed-but-incomplete, eligible multi-skilled providers, stock expiry/return/quarantine, and permission-restricted accounts. No synthetic financial flags without actual ledger facts. Reconcile from live PG rows, preserve minimal/demo/performance separation and tenant-salted IDs with random GCM nonces. Disposable reset only; no reset of real tenant or paid clinic.

### 14.2 Exact 120-scenario acceptance matrix and performance targets

- Replace grouped `D0.5_ACCEPTANCE_MATRIX_TASK30.md` and `D0.5_ACCEPTANCE_MATRIX_TASK32.md` summaries with an exact **120-row** traceability matrix (`Scenario ID`, `Workspace/Contract`, `Code Location`, `Executed Test(s)`, `Commit SHA & Environment`, `Status: PASS | FAIL | NOT RUN | BLOCKED | N/A`).
- Full frontend unit, `tsc --noEmit`, `eslint`, production build, and fresh-stack Playwright E2E + visual screenshot verification at `1280px`, `1440px`, `1920px`, and responsive breakpoints (RTL, English digits, Jalali/`Asia/Tehran`, themes, keyboard focus, reduced motion).
- Performance benchmarks (`0`/`1`/`200`/`500` appointments/day, `10,500` demo appointments, `100,000` historical records): warm click-ready `< 1s`, list/filter API `p95 <= 500ms`, zero duplicate requests, settled layout shift `<= 1 CSS px`. Report p50/p95, actual endpoint (not count-only SQL), query plans, request counts, warm/cold state, concurrency and environment. Human usability targets (existing patient lookup <5s, registration <30s, routine booking <20s after sufficient input) are separate and not automatically proven by scripted timings. Include shared phone, identity, grouped booking, concurrent receptionists, manual overlap and financial query measurements. Windows runtime auto-open remains NOT RUN; browser visual artifact files must be actually inspected, not inferred from reports. Benchmark must refuse any unverified non-disposable DB before reading/writing; never select the first tenant in a general DSN or use production/admin credentials. Benchmark cleanup and failure isolation mandatory.

### 14.3 Final handoff criteria

- Single pinned commit SHA, ratified migration graph, four functional workspaces, 120-row verified evidence matrix, PG15 + Playwright artifacts, live dataset reconciliation counts, screenshots/benchmarks, and explicit list of remaining external gates (`Gates A–D`, `SRC-10`, `SRC-12`, v1.3 merge source).

---

## 15. Historical Gemini change log (D0.7 $\rightarrow$ D0.8)

The following six claims are retained for historical traceability only; D0.9 does not endorse completeness, execution, or resolution statements. Current verdict and outstanding evidence are in Appendix D.

1. **Completed Executable Cross-Row & State-Transition Integrity Triggers (`Appendix B.3`):** Replaced D0.7's abstract proof obligation table with complete, `SECURITY INVOKER` PostgreSQL 15 trigger functions covering receipt conservation, invoice line obligation/overpayment caps, per-allocation reversal & refund caps, unresolved-beneficiary blocking, item-to-service line-kind validation, service-record charge-link consistency, inventory scale/bucket/non-negative balance/return-cap/transfer-zero-sum/lot-status-event sync, canonical practitioner resource-type & immutability guards, `role_permission_scopes` `ALL`/`FILTER` mutual exclusivity, `appointments` lifecycle fact enforcement (`CHECKED_IN` arrival + `COMPLETED` performed service), and terminal-state immutability for waitlist, closures, note actions, and identity reviews.
2. **Resolved `operator_user_id` System Callback Contradiction (`§2.4`, `§2.6`):** Made `operator_user_id` nullable when `actor_type = 'SYSTEM_CALLBACK'` and enforced `CHECK ((actor_type = 'STAFF_USER' AND operator_user_id IS NOT NULL AND actor_id = operator_user_id) OR (actor_type = 'SYSTEM_CALLBACK' AND operator_user_id IS NULL))` on `payment_receipts` and `insurer_settlement_entries`, eliminating any need for a synthetic human operator account on verified gateway callbacks.
3. **Hardened Invoice Voiding, Line Attribution & Draft Discount History (`§2.3`, `Appendix B.1`):** Added `voided_by_user_id` and `void_reason` to `invoice_documents` `VOIDED` state check; added `practitioner_mapping_id` snapshot FK to `invoice_lines`; prevented `DELETE` on `draft_discount_actions` even while `DRAFT`.
4. **Hardened Unverified Claim Review & Inventory Scale/Bucket Integrity (`§2.4`, `§3.2`, `Appendix B.3`):** Added `reviewed_by_user_id`, `reviewed_at_utc`, `review_reason`, and `aggregate_version` to `unverified_payment_claims`; added composite `(tenant_id, id, quantity_scale)` FK from `stock_movements` and `service_item_suggestions` to `inventory_items`; enforced non-lot-tracked single-bucket uniqueness and `requires_expiry` lot validation.
5. **Tightened Waitlist & Insurer Self-Reversal Constraints (`§2.6`, `§4.1`):** Pointed `appointment_waitlist_entries.preferred_resource_id` to `staff_practitioner_resources(tenant_id, bookable_resource_id)` so non-practitioner rooms/devices cannot be selected as preferred providers; added `reverses_entry_id <> id` on `insurer_settlement_entries`.
6. **Preserved All Governance & External Boundaries (`§0`, `§11`, `§12`, `Appendix A`):** Preserved `TP0001–TP0007` baseline, protected `TP0011` and `R4.6` candidate allocations, marked unavailable repository/external artifacts explicitly as `SOURCE_REQUIRED`, and kept synthetic development readiness strictly distinct from `Gates A–D`.

---

## Appendix A — Concrete proposed RLS and grants (per approved migration)

Apply only to the explicit subset of relations created in each approved revision under `db_migrator`, using `TP0007`'s exact three-policy pattern (`tenant_runtime_base`, `tenant_runtime_guard`, `tenant_migrator_maintenance`).

```sql
-- The migration sets this transaction-local selector to an explicit JSON array
-- of only the tables created in that revision, e.g. '["departments"]'.
-- No default and no silent skip; reject unknown, duplicate or empty selections.
DO $policies$
DECLARE
  rel text;
  selected text[];
  append_only text[] := ARRAY[
    'reception_groups', 'reception_group_appointments', 'visit_appointments',
    'appointment_arrival_facts', 'service_records', 'service_record_practitioners',
    'historical_appointment_entries', 'draft_discount_actions', 'service_record_charge_links',
    'payment_receipts', 'receipt_beneficiary_attributions', 'receipt_allocations',
    'financial_adjustments', 'clinic_payment_refunds', 'insurer_settlement_entries',
    'revenue_share_adjustments', 'stock_movements', 'inventory_lot_state_events',
    'patient_operational_notes', 'patient_note_actions', 'person_merge_events'
  ];
  mutable_metadata text[] := ARRAY[
    'staff_practitioner_resources', 'staff_service_links', 'departments',
    'department_service_links', 'department_practitioner_links', 'clinic_visits',
    'appointment_waitlist_entries', 'service_availability_guards', 'online_availability_closures',
    'billable_items', 'cashier_shifts', 'clinic_payment_instruments',
    'invoice_documents', 'invoice_lines', 'document_number_counters',
    'payment_attempts', 'unverified_payment_claims', 'ledger_receipt_guards',
    'clinic_insurers', 'clinic_service_referrers', 'inventory_items',
    'inventory_lots', 'service_item_suggestions', 'staff_tag_catalog',
    'patient_staff_tags', 'patient_identity_reviews'
  ];
  controlled_delete text[] := ARRAY[
    'role_permission_scopes', 'invoice_item_service_links',
    'invoice_insurer_expectations', 'revenue_share_allocations'
  ];
BEGIN
  SELECT array_agg(value) INTO selected FROM jsonb_array_elements_text(
    NULLIF(current_setting('app.ops_migration_tables', true), '')::jsonb);
  IF selected IS NULL OR cardinality(selected) = 0
     OR EXISTS (SELECT 1 FROM unnest(selected) t(x) WHERE NOT (x = ANY(append_only || mutable_metadata || controlled_delete)))
     OR cardinality(selected) <> (SELECT count(DISTINCT x) FROM unnest(selected) t(x)) THEN
    RAISE EXCEPTION 'explicit valid migration table subset required';
  END IF;
  FOREACH rel IN ARRAY selected LOOP
    EXECUTE format('ALTER TABLE public.%I OWNER TO db_migrator', rel);
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', rel);
    EXECUTE format('ALTER TABLE public.%I FORCE ROW LEVEL SECURITY', rel);
    EXECUTE format('REVOKE ALL ON TABLE public.%I FROM PUBLIC, db_app_runtime', rel);

    EXECUTE format(
      'CREATE POLICY tenant_runtime_base ON public.%I AS PERMISSIVE FOR ALL TO db_app_runtime USING (true) WITH CHECK (true)',
      rel
    );
    EXECUTE format(
      'CREATE POLICY tenant_runtime_guard ON public.%I AS RESTRICTIVE FOR ALL TO db_app_runtime '
      'USING (tenant_id = NULLIF(current_setting(''app.current_tenant_id'', true), '''')::uuid) '
      'WITH CHECK (tenant_id = NULLIF(current_setting(''app.current_tenant_id'', true), '''')::uuid)',
      rel
    );
    EXECUTE format(
      'CREATE POLICY tenant_migrator_maintenance ON public.%I AS PERMISSIVE FOR ALL TO db_migrator USING (true) WITH CHECK (true)',
      rel
    );

    IF rel = ANY(append_only) THEN
      EXECUTE format('GRANT SELECT, INSERT ON TABLE public.%I TO db_app_runtime', rel);
    ELSIF rel = ANY(mutable_metadata) THEN
      EXECUTE format('GRANT SELECT, INSERT, UPDATE ON TABLE public.%I TO db_app_runtime', rel);
    ELSE
      EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.%I TO db_app_runtime', rel);
    END IF;
  END LOOP;
  IF 'ledger_receipt_guards' = ANY(selected) THEN
    REVOKE UPDATE ON TABLE public.ledger_receipt_guards FROM db_app_runtime;
    GRANT UPDATE (lock_version) ON TABLE public.ledger_receipt_guards TO db_app_runtime;
  END IF;
END $policies$;
```

---

## Appendix B — Executable PostgreSQL 15 integrity helpers (`SECURITY INVOKER`, not yet executed)

### B.1 Posted/voided invoice and draft child immutability

```sql
CREATE FUNCTION public.ops_invoice_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'invoice documents cannot be deleted at runtime' USING ERRCODE = '23514';
  END IF;
  IF TG_OP = 'INSERT' THEN
    IF NEW.status <> 'DRAFT' THEN
      RAISE EXCEPTION 'invoice document must begin in DRAFT status' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
  END IF;
  IF OLD.status <> 'DRAFT' THEN
    RAISE EXCEPTION 'posted or voided invoice document is immutable' USING ERRCODE = '23514';
  END IF;
  IF NEW.id <> OLD.id OR NEW.tenant_id <> OLD.tenant_id
     OR NEW.beneficiary_patient_id <> OLD.beneficiary_patient_id
     OR NEW.created_at_utc <> OLD.created_at_utc THEN
    RAISE EXCEPTION 'invoice identity fields are immutable' USING ERRCODE = '23514';
  END IF;
  IF NEW.aggregate_version <> OLD.aggregate_version + 1 THEN
    RAISE EXCEPTION 'invoice aggregate_version must increment by 1' USING ERRCODE = '23514';
  END IF;
  IF NEW.status = 'POSTED' AND NOT EXISTS (
    SELECT 1 FROM public.invoice_lines l
    WHERE l.tenant_id = OLD.tenant_id AND l.invoice_id = OLD.id AND l.line_status = 'ACTIVE'
  ) THEN
    RAISE EXCEPTION 'cannot post an invoice with zero ACTIVE lines' USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER invoice_documents_guard
  BEFORE INSERT OR UPDATE OR DELETE ON public.invoice_documents
  FOR EACH ROW EXECUTE FUNCTION public.ops_invoice_guard();

CREATE FUNCTION public.ops_draft_child_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
DECLARE
  v_tenant_id uuid;
  v_invoice_id uuid;
  v_status text;
BEGIN
  IF TG_OP = 'DELETE' THEN
    IF TG_TABLE_NAME = 'draft_discount_actions' THEN
      RAISE EXCEPTION 'draft_discount_actions are append-only and cannot be deleted' USING ERRCODE = '23514';
    END IF;
    v_tenant_id := OLD.tenant_id;
    v_invoice_id := OLD.invoice_id;
  ELSE
    v_tenant_id := NEW.tenant_id;
    v_invoice_id := NEW.invoice_id;
  END IF;

  IF TG_OP = 'UPDATE' AND (NEW.tenant_id <> OLD.tenant_id OR NEW.invoice_id <> OLD.invoice_id OR NEW.id <> OLD.id) THEN
    RAISE EXCEPTION 'invoice child identity cannot be reparented' USING ERRCODE = '23514';
  END IF;

  SELECT status INTO v_status
  FROM public.invoice_documents
  WHERE tenant_id = v_tenant_id AND id = v_invoice_id
  FOR UPDATE;

  IF NOT FOUND OR v_status IS DISTINCT FROM 'DRAFT' THEN
    RAISE EXCEPTION 'invoice children may mutate only while parent invoice is DRAFT' USING ERRCODE = '23514';
  END IF;

  IF TG_OP = 'DELETE' THEN
    RETURN OLD;
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER invoice_lines_draft_guard
  BEFORE INSERT OR UPDATE OR DELETE ON public.invoice_lines
  FOR EACH ROW EXECUTE FUNCTION public.ops_draft_child_guard();
CREATE TRIGGER invoice_item_service_draft_guard
  BEFORE INSERT OR UPDATE OR DELETE ON public.invoice_item_service_links
  FOR EACH ROW EXECUTE FUNCTION public.ops_draft_child_guard();
CREATE TRIGGER insurer_expectation_draft_guard
  BEFORE INSERT OR UPDATE OR DELETE ON public.invoice_insurer_expectations
  FOR EACH ROW EXECUTE FUNCTION public.ops_draft_child_guard();
CREATE TRIGGER revenue_share_draft_guard
  BEFORE INSERT OR UPDATE OR DELETE ON public.revenue_share_allocations
  FOR EACH ROW EXECUTE FUNCTION public.ops_draft_child_guard();
CREATE TRIGGER discount_action_draft_guard
  BEFORE INSERT OR UPDATE OR DELETE ON public.draft_discount_actions
  FOR EACH ROW EXECUTE FUNCTION public.ops_draft_child_guard();

REVOKE ALL ON FUNCTION public.ops_invoice_guard() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.ops_draft_child_guard() FROM PUBLIC;
```

### B.2 Receipt guard creation and beneficiary attribution integrity

```sql
CREATE TABLE ledger_receipt_guards (
  receipt_id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  lock_version BIGINT NOT NULL DEFAULT 1 CHECK (lock_version > 0),
  UNIQUE (tenant_id, receipt_id),
  FOREIGN KEY (tenant_id, receipt_id) REFERENCES payment_receipts(tenant_id, id) MATCH FULL
);

CREATE TABLE receipt_beneficiary_attributions (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenant_registry(tenant_id),
  receipt_id UUID NOT NULL,
  beneficiary_patient_id UUID NOT NULL,
  operator_user_id UUID NOT NULL,
  reason_code VARCHAR(64) NOT NULL,
  correlation_id UUID NOT NULL,
  created_at_utc TIMESTAMPTZ NOT NULL,
  UNIQUE (tenant_id, id),
  UNIQUE (tenant_id, receipt_id),
  FOREIGN KEY (tenant_id, receipt_id) REFERENCES payment_receipts(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, beneficiary_patient_id) REFERENCES patient_profiles(tenant_id, id) MATCH FULL,
  FOREIGN KEY (tenant_id, operator_user_id) REFERENCES user_accounts(tenant_id, id) MATCH FULL
);

CREATE FUNCTION public.ops_create_receipt_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
BEGIN
  INSERT INTO public.ledger_receipt_guards(receipt_id, tenant_id)
  VALUES (NEW.id, NEW.tenant_id);
  RETURN NEW;
END $$;

CREATE TRIGGER payment_receipt_create_guard
  AFTER INSERT ON public.payment_receipts
  FOR EACH ROW EXECUTE FUNCTION public.ops_create_receipt_guard();

CREATE FUNCTION public.ops_receipt_attribution_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
DECLARE
  v_existing_beneficiary uuid;
BEGIN
  PERFORM 1 FROM public.ledger_receipt_guards
  WHERE tenant_id = NEW.tenant_id AND receipt_id = NEW.receipt_id
  FOR UPDATE;

  SELECT credit_beneficiary_patient_id INTO v_existing_beneficiary
  FROM public.payment_receipts
  WHERE tenant_id = NEW.tenant_id AND id = NEW.receipt_id;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'receipt not found for attribution' USING ERRCODE = '23503';
  END IF;
  IF v_existing_beneficiary IS NOT NULL THEN
    RAISE EXCEPTION 'receipt already has an immutable beneficiary' USING ERRCODE = '23514';
  END IF;
  IF EXISTS (
    SELECT 1 FROM public.receipt_allocations
    WHERE tenant_id = NEW.tenant_id AND receipt_id = NEW.receipt_id
  ) THEN
    RAISE EXCEPTION 'cannot attribute receipt after allocations exist' USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER receipt_beneficiary_attribution_guard
  BEFORE INSERT ON public.receipt_beneficiary_attributions
  FOR EACH ROW EXECUTE FUNCTION public.ops_receipt_attribution_guard();

REVOKE ALL ON FUNCTION public.ops_create_receipt_guard() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.ops_receipt_attribution_guard() FROM PUBLIC;
```

### B.3 Proposed cross-row financial, inventory, scope, practitioner and lifecycle constraint triggers (partial; see Appendix D)

```sql
-- 1. Item-to-service link kind and ACTIVE status validation (deferred to commit)
CREATE FUNCTION public.ops_item_service_link_check() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
DECLARE
  v_item_kind text;
  v_item_status text;
  v_srv_kind text;
  v_srv_status text;
BEGIN
  SELECT line_kind, line_status INTO v_item_kind, v_item_status
  FROM public.invoice_lines
  WHERE tenant_id = NEW.tenant_id AND invoice_id = NEW.invoice_id AND id = NEW.item_line_id;

  SELECT line_kind, line_status INTO v_srv_kind, v_srv_status
  FROM public.invoice_lines
  WHERE tenant_id = NEW.tenant_id AND invoice_id = NEW.invoice_id AND id = NEW.service_line_id;

  IF v_item_kind IS DISTINCT FROM 'ITEM' OR v_item_status IS DISTINCT FROM 'ACTIVE'
     OR v_srv_kind IS DISTINCT FROM 'SERVICE' OR v_srv_status IS DISTINCT FROM 'ACTIVE' THEN
    RAISE EXCEPTION 'invoice_item_service_links requires an ACTIVE ITEM line and an ACTIVE SERVICE line'
      USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END $$;

CREATE CONSTRAINT TRIGGER invoice_item_service_link_check
  AFTER INSERT OR UPDATE ON public.invoice_item_service_links
  DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW EXECUTE FUNCTION public.ops_item_service_link_check();

-- 2. Service-record-to-charge-line patient/service/appointment consistency
CREATE FUNCTION public.ops_service_record_charge_link_check() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
DECLARE
  v_sr record;
  v_line record;
BEGIN
  SELECT patient_id, service_id, appointment_id INTO v_sr
  FROM public.service_records
  WHERE tenant_id = NEW.tenant_id AND id = NEW.service_record_id;

  SELECT beneficiary_patient_id, service_id, appointment_id, line_kind, line_status INTO v_line
  FROM public.invoice_lines
  WHERE tenant_id = NEW.tenant_id AND invoice_id = NEW.invoice_id AND id = NEW.invoice_line_id;

  IF v_line.line_kind IS DISTINCT FROM 'SERVICE' OR v_line.line_status IS DISTINCT FROM 'ACTIVE' THEN
    RAISE EXCEPTION 'service_record_charge_links requires an ACTIVE SERVICE invoice line' USING ERRCODE = '23514';
  END IF;
  IF v_sr.patient_id <> v_line.beneficiary_patient_id OR v_sr.service_id <> v_line.service_id THEN
    RAISE EXCEPTION 'service_record and invoice_line patient/service mismatch' USING ERRCODE = '23514';
  END IF;
  IF v_sr.appointment_id IS NOT NULL AND v_line.appointment_id IS NOT NULL
     AND v_sr.appointment_id <> v_line.appointment_id THEN
    RAISE EXCEPTION 'service_record and invoice_line appointment mismatch' USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END $$;

CREATE CONSTRAINT TRIGGER service_record_charge_link_check
  AFTER INSERT ON public.service_record_charge_links
  DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW EXECUTE FUNCTION public.ops_service_record_charge_link_check();

-- 3. Receipt allocation, reversal, beneficiary, and invoice-line obligation check (deferred)
CREATE FUNCTION public.ops_receipt_allocation_reconcile() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
DECLARE
  v_receipt record;
  v_attr_patient uuid;
  v_effective_patient uuid;
  v_inv record;
  v_line record;
  v_orig record;
  v_net_receipt_alloc numeric;
  v_total_refunded numeric;
  v_reversed_on_orig numeric;
  v_adj_delta numeric;
  v_net_line_alloc numeric;
BEGIN
  SELECT status, beneficiary_patient_id INTO v_inv
  FROM public.invoice_documents
  WHERE tenant_id = NEW.tenant_id AND id = NEW.invoice_id
  FOR UPDATE;

  PERFORM 1 FROM public.ledger_receipt_guards
  WHERE tenant_id = NEW.tenant_id AND receipt_id = NEW.receipt_id
  FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'receipt guard missing' USING ERRCODE = '23503'; END IF;

  SELECT id, amount_irr, credit_beneficiary_patient_id INTO v_receipt
  FROM public.payment_receipts
  WHERE tenant_id = NEW.tenant_id AND id = NEW.receipt_id;

  SELECT beneficiary_patient_id INTO v_attr_patient
  FROM public.receipt_beneficiary_attributions
  WHERE tenant_id = NEW.tenant_id AND receipt_id = NEW.receipt_id;

  v_effective_patient := COALESCE(v_receipt.credit_beneficiary_patient_id, v_attr_patient);
  IF v_effective_patient IS NULL THEN
    RAISE EXCEPTION 'cannot allocate receipt with unresolved beneficiary' USING ERRCODE = '23514';
  END IF;

  IF v_inv.status IS DISTINCT FROM 'POSTED' THEN
    RAISE EXCEPTION 'allocations require a POSTED invoice' USING ERRCODE = '23514';
  END IF;
  IF v_inv.beneficiary_patient_id <> v_effective_patient THEN
    RAISE EXCEPTION 'receipt beneficiary does not match invoice beneficiary' USING ERRCODE = '23514';
  END IF;

  SELECT line_status, patient_payable_amount INTO v_line
  FROM public.invoice_lines
  WHERE tenant_id = NEW.tenant_id AND invoice_id = NEW.invoice_id AND id = NEW.invoice_line_id;

  IF v_line.line_status IS DISTINCT FROM 'ACTIVE' THEN
    RAISE EXCEPTION 'cannot allocate to a REMOVED invoice line' USING ERRCODE = '23514';
  END IF;

  IF NEW.allocation_kind = 'REVERSE' THEN
    SELECT allocation_kind, amount_irr INTO v_orig
    FROM public.receipt_allocations
    WHERE tenant_id = NEW.tenant_id AND id = NEW.reverses_allocation_id;

    IF v_orig.allocation_kind IS DISTINCT FROM 'APPLY' THEN
      RAISE EXCEPTION 'reversal must target an APPLY allocation' USING ERRCODE = '23514';
    END IF;

    SELECT COALESCE(SUM(amount_irr), 0) INTO v_reversed_on_orig
    FROM public.receipt_allocations
    WHERE tenant_id = NEW.tenant_id
      AND allocation_kind = 'REVERSE'
      AND reverses_allocation_id = NEW.reverses_allocation_id;

    IF v_reversed_on_orig > v_orig.amount_irr THEN
      RAISE EXCEPTION 'cumulative reversals exceed original APPLY amount' USING ERRCODE = '23514';
    END IF;
  END IF;

  SELECT COALESCE(SUM(CASE WHEN allocation_kind = 'APPLY' THEN amount_irr ELSE -amount_irr END), 0)
  INTO v_net_receipt_alloc
  FROM public.receipt_allocations
  WHERE tenant_id = NEW.tenant_id AND receipt_id = NEW.receipt_id;

  SELECT COALESCE(SUM(amount_irr), 0) INTO v_total_refunded
  FROM public.clinic_payment_refunds
  WHERE tenant_id = NEW.tenant_id AND original_receipt_id = NEW.receipt_id;

  IF v_net_receipt_alloc < 0 OR (v_net_receipt_alloc + v_total_refunded) > v_receipt.amount_irr THEN
    RAISE EXCEPTION 'receipt net allocations plus refunds exceed verified receipt amount' USING ERRCODE = '23514';
  END IF;

  SELECT COALESCE(SUM(patient_delta_irr), 0) INTO v_adj_delta
  FROM public.financial_adjustments
  WHERE tenant_id = NEW.tenant_id AND invoice_id = NEW.invoice_id AND invoice_line_id = NEW.invoice_line_id;

  SELECT COALESCE(SUM(CASE WHEN allocation_kind = 'APPLY' THEN amount_irr ELSE -amount_irr END), 0)
  INTO v_net_line_alloc
  FROM public.receipt_allocations
  WHERE tenant_id = NEW.tenant_id AND invoice_id = NEW.invoice_id AND invoice_line_id = NEW.invoice_line_id;

  IF (v_line.patient_payable_amount::numeric + v_adj_delta) < 0
     OR v_net_line_alloc < 0
     OR v_net_line_alloc > (v_line.patient_payable_amount::numeric + v_adj_delta) THEN
    RAISE EXCEPTION 'invoice line patient obligation or allocation cap violated' USING ERRCODE = '23514';
  END IF;

  RETURN NEW;
END $$;

CREATE CONSTRAINT TRIGGER receipt_allocations_reconcile_trg
  AFTER INSERT ON public.receipt_allocations
  DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW EXECUTE FUNCTION public.ops_receipt_allocation_reconcile();

-- 4. Financial adjustment post-state & obligation invariant check (deferred)
CREATE FUNCTION public.ops_financial_adjustment_reconcile() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
DECLARE
  v_inv_status text;
  v_line record;
  v_adj_patient numeric;
  v_adj_basic numeric;
  v_adj_supp numeric;
  v_net_line_alloc numeric;
BEGIN
  SELECT status INTO v_inv_status
  FROM public.invoice_documents
  WHERE tenant_id = NEW.tenant_id AND id = NEW.invoice_id
  FOR UPDATE;

  IF v_inv_status IS DISTINCT FROM 'POSTED' THEN
    RAISE EXCEPTION 'financial adjustments require a POSTED invoice' USING ERRCODE = '23514';
  END IF;

  SELECT line_status, patient_payable_amount, basic_insurance_expected_share, supplementary_insurance_expected_share
  INTO v_line
  FROM public.invoice_lines
  WHERE tenant_id = NEW.tenant_id AND invoice_id = NEW.invoice_id AND id = NEW.invoice_line_id;

  IF v_line.line_status IS DISTINCT FROM 'ACTIVE' THEN
    RAISE EXCEPTION 'cannot adjust a REMOVED invoice line' USING ERRCODE = '23514';
  END IF;

  SELECT COALESCE(SUM(patient_delta_irr), 0),
         COALESCE(SUM(basic_insurer_delta_irr), 0),
         COALESCE(SUM(supplementary_insurer_delta_irr), 0)
  INTO v_adj_patient, v_adj_basic, v_adj_supp
  FROM public.financial_adjustments
  WHERE tenant_id = NEW.tenant_id AND invoice_id = NEW.invoice_id AND invoice_line_id = NEW.invoice_line_id;

  IF (v_line.patient_payable_amount::numeric + v_adj_patient) < 0
     OR (v_line.basic_insurance_expected_share::numeric + v_adj_basic) < 0
     OR (v_line.supplementary_insurance_expected_share::numeric + v_adj_supp) < 0 THEN
    RAISE EXCEPTION 'financial adjustment drives line obligation below zero' USING ERRCODE = '23514';
  END IF;

  SELECT COALESCE(SUM(CASE WHEN allocation_kind = 'APPLY' THEN amount_irr ELSE -amount_irr END), 0)
  INTO v_net_line_alloc
  FROM public.receipt_allocations
  WHERE tenant_id = NEW.tenant_id AND invoice_id = NEW.invoice_id AND invoice_line_id = NEW.invoice_line_id;

  IF v_net_line_alloc > (v_line.patient_payable_amount::numeric + v_adj_patient) THEN
    RAISE EXCEPTION 'post-adjustment net allocation exceeds reduced patient obligation; reverse excess in same UoW'
      USING ERRCODE = '23514';
  END IF;

  RETURN NEW;
END $$;

CREATE CONSTRAINT TRIGGER financial_adjustments_reconcile_trg
  AFTER INSERT ON public.financial_adjustments
  DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW EXECUTE FUNCTION public.ops_financial_adjustment_reconcile();

-- 5. Clinic payment refund cap & linked-reversal check (deferred)
CREATE FUNCTION public.ops_clinic_refund_reconcile() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
DECLARE
  v_receipt_amt bigint;
  v_net_receipt_alloc numeric;
  v_total_refunded numeric;
  v_orig_kind text;
  v_reversed_on_orig numeric;
  v_refunded_on_orig numeric;
BEGIN
  IF NEW.invoice_id IS NOT NULL THEN
    PERFORM 1 FROM public.invoice_documents WHERE tenant_id = NEW.tenant_id AND id = NEW.invoice_id AND status = 'POSTED' FOR UPDATE;
    IF NOT FOUND THEN RAISE EXCEPTION 'refund invoice must be posted' USING ERRCODE = '23514'; END IF;
  END IF;
  PERFORM 1 FROM public.ledger_receipt_guards
  WHERE tenant_id = NEW.tenant_id AND receipt_id = NEW.original_receipt_id
  FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'receipt guard missing' USING ERRCODE = '23503'; END IF;

  SELECT amount_irr INTO v_receipt_amt
  FROM public.payment_receipts
  WHERE tenant_id = NEW.tenant_id AND id = NEW.original_receipt_id;

  SELECT COALESCE(SUM(CASE WHEN allocation_kind = 'APPLY' THEN amount_irr ELSE -amount_irr END), 0)
  INTO v_net_receipt_alloc
  FROM public.receipt_allocations
  WHERE tenant_id = NEW.tenant_id AND receipt_id = NEW.original_receipt_id;

  SELECT COALESCE(SUM(amount_irr), 0) INTO v_total_refunded
  FROM public.clinic_payment_refunds
  WHERE tenant_id = NEW.tenant_id AND original_receipt_id = NEW.original_receipt_id;

  IF (v_net_receipt_alloc + v_total_refunded) > v_receipt_amt THEN
    RAISE EXCEPTION 'refund exceeds unapplied refundable balance on receipt' USING ERRCODE = '23514';
  END IF;

  IF NEW.original_allocation_id IS NOT NULL THEN
    SELECT allocation_kind INTO v_orig_kind
    FROM public.receipt_allocations
    WHERE tenant_id = NEW.tenant_id AND id = NEW.original_allocation_id;

    IF v_orig_kind IS DISTINCT FROM 'APPLY' THEN
      RAISE EXCEPTION 'refund original_allocation_id must reference an APPLY row' USING ERRCODE = '23514';
    END IF;

    SELECT COALESCE(SUM(amount_irr), 0) INTO v_reversed_on_orig
    FROM public.receipt_allocations
    WHERE tenant_id = NEW.tenant_id
      AND allocation_kind = 'REVERSE'
      AND reverses_allocation_id = NEW.original_allocation_id;

    SELECT COALESCE(SUM(amount_irr), 0) INTO v_refunded_on_orig
    FROM public.clinic_payment_refunds
    WHERE tenant_id = NEW.tenant_id AND original_allocation_id = NEW.original_allocation_id;

    IF v_refunded_on_orig > v_reversed_on_orig THEN
      RAISE EXCEPTION 'refunds attributed to allocation exceed reversed portion' USING ERRCODE = '23514';
    END IF;
  END IF;

  RETURN NEW;
END $$;

CREATE CONSTRAINT TRIGGER clinic_payment_refunds_reconcile_trg
  AFTER INSERT ON public.clinic_payment_refunds
  DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW EXECUTE FUNCTION public.ops_clinic_refund_reconcile();

-- 6. Inventory lot rules, non-negative balance, return cap, transfer zero-sum, and lot state sync
CREATE FUNCTION public.ops_inventory_lot_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
BEGIN
  IF TG_OP = 'UPDATE' THEN
    IF ROW(NEW.id, NEW.tenant_id, NEW.item_id, NEW.is_lot_tracked, NEW.requires_expiry,
           NEW.source_lot_id, NEW.expires_on, NEW.received_at_utc, NEW.created_at_utc)
       IS DISTINCT FROM ROW(OLD.id, OLD.tenant_id, OLD.item_id, OLD.is_lot_tracked, OLD.requires_expiry,
           OLD.source_lot_id, OLD.expires_on, OLD.received_at_utc, OLD.created_at_utc) THEN
      RAISE EXCEPTION 'lot identity, expiry and provenance immutable' USING ERRCODE = '23514';
    END IF;
  END IF;
  PERFORM 1 FROM public.inventory_items WHERE tenant_id = NEW.tenant_id AND id = NEW.item_id FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'inventory item missing' USING ERRCODE = '23503'; END IF;
  IF NEW.source_lot_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM public.inventory_lots l
    WHERE l.tenant_id = NEW.tenant_id AND l.item_id = NEW.item_id AND l.id = NEW.source_lot_id
      AND l.source_lot_id IS NULL AND l.expires_on IS NOT DISTINCT FROM NEW.expires_on
  ) THEN RAISE EXCEPTION 'invalid lot provenance' USING ERRCODE = '23514'; END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER inventory_lots_guard
  BEFORE INSERT OR UPDATE ON public.inventory_lots
  FOR EACH ROW EXECUTE FUNCTION public.ops_inventory_lot_guard();

CREATE FUNCTION public.ops_stock_movement_reconcile() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
DECLARE
  v_lot record;
  v_lot_balance numeric;
  v_orig record;
  v_returned_qty numeric;
  v_transfer_net numeric;
BEGIN
  PERFORM 1 FROM public.inventory_items
  WHERE tenant_id = NEW.tenant_id AND id = NEW.item_id
  FOR UPDATE;

  SELECT lot_status, source_lot_id, expires_on INTO v_lot
  FROM public.inventory_lots
  WHERE tenant_id = NEW.tenant_id AND item_id = NEW.item_id AND id = NEW.lot_id
  FOR UPDATE;

  IF NEW.movement_kind IN ('SERVICE_CONSUMPTION', 'SALE') AND
     (v_lot.lot_status <> 'AVAILABLE' OR (v_lot.expires_on IS NOT NULL AND
      v_lot.expires_on < (transaction_timestamp() AT TIME ZONE 'Asia/Tehran')::date)) THEN
    RAISE EXCEPTION 'cannot consume or sell from a non-AVAILABLE lot' USING ERRCODE = '23514';
  END IF;

  IF NEW.movement_kind = 'RETURN' THEN
    SELECT movement_kind, lot_id, quantity_delta INTO v_orig
    FROM public.stock_movements
    WHERE tenant_id = NEW.tenant_id AND item_id = NEW.item_id AND id = NEW.original_movement_id;

    IF v_orig.movement_kind NOT IN ('SERVICE_CONSUMPTION', 'SALE') THEN
      RAISE EXCEPTION 'stock return must reference SERVICE_CONSUMPTION or SALE' USING ERRCODE = '23514';
    END IF;

    IF NEW.return_disposition = 'REUSABLE' AND (NEW.lot_id <> v_orig.lot_id OR v_lot.lot_status <> 'AVAILABLE' OR
        (v_lot.expires_on IS NOT NULL AND v_lot.expires_on < (transaction_timestamp() AT TIME ZONE 'Asia/Tehran')::date)) THEN
      RAISE EXCEPTION 'REUSABLE return must restore the original AVAILABLE lot' USING ERRCODE = '23514';
    END IF;

    IF NEW.return_disposition = 'QUARANTINE' AND (v_lot.lot_status <> 'QUARANTINE' OR v_lot.source_lot_id IS DISTINCT FROM v_orig.lot_id) THEN
      RAISE EXCEPTION 'QUARANTINE return must target a QUARANTINE lot linked to original lot' USING ERRCODE = '23514';
    END IF;

    SELECT COALESCE(SUM(quantity_delta), 0) INTO v_returned_qty
    FROM public.stock_movements
    WHERE tenant_id = NEW.tenant_id
      AND item_id = NEW.item_id
      AND movement_kind = 'RETURN'
      AND original_movement_id = NEW.original_movement_id;

    IF v_returned_qty > ABS(v_orig.quantity_delta) THEN
      RAISE EXCEPTION 'cumulative returned stock exceeds original issued quantity' USING ERRCODE = '23514';
    END IF;
  END IF;

  IF NEW.movement_kind IN ('TRANSFER_OUT', 'TRANSFER_IN') THEN
    SELECT COALESCE(SUM(quantity_delta), 0) INTO v_transfer_net
    FROM public.stock_movements
    WHERE tenant_id = NEW.tenant_id
      AND item_id = NEW.item_id
      AND transfer_operation_id = NEW.transfer_operation_id;

    IF v_transfer_net <> 0 OR NOT EXISTS (
      SELECT 1 FROM public.stock_movements m
      WHERE m.tenant_id = NEW.tenant_id AND m.item_id = NEW.item_id
        AND m.transfer_operation_id = NEW.transfer_operation_id
      GROUP BY m.transfer_operation_id HAVING count(*) = 2 AND count(DISTINCT m.lot_id) = 2
    ) THEN
      RAISE EXCEPTION 'stock transfer pair must net to zero within the transaction' USING ERRCODE = '23514';
    END IF;
  END IF;

  SELECT COALESCE(SUM(quantity_delta), 0) INTO v_lot_balance
  FROM public.stock_movements
  WHERE tenant_id = NEW.tenant_id AND item_id = NEW.item_id AND lot_id = NEW.lot_id;

  IF v_lot_balance < 0 THEN
    RAISE EXCEPTION 'stock lot balance cannot become negative' USING ERRCODE = '23514';
  END IF;

  RETURN NEW;
END $$;

CREATE CONSTRAINT TRIGGER stock_movements_reconcile_trg
  AFTER INSERT ON public.stock_movements
  DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW EXECUTE FUNCTION public.ops_stock_movement_reconcile();

-- 7. Canonical practitioner resource-type & immutability guard
CREATE FUNCTION public.ops_practitioner_mapping_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
DECLARE
  v_res_type text;
BEGIN
  IF TG_OP = 'UPDATE' AND (NEW.staff_profile_id <> OLD.staff_profile_id OR NEW.bookable_resource_id <> OLD.bookable_resource_id) THEN
    RAISE EXCEPTION 'practitioner staff_profile_id and bookable_resource_id are immutable' USING ERRCODE = '23514';
  END IF;
  SELECT resource_type INTO v_res_type
  FROM public.bookable_resources
  WHERE tenant_id = NEW.tenant_id AND id = NEW.bookable_resource_id;

  IF v_res_type IS DISTINCT FROM 'PRACTITIONER' THEN
    RAISE EXCEPTION 'staff_practitioner_resources requires resource_type = PRACTITIONER' USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER staff_practitioner_resources_guard
  BEFORE INSERT OR UPDATE ON public.staff_practitioner_resources
  FOR EACH ROW EXECUTE FUNCTION public.ops_practitioner_mapping_guard();

-- 8. Typed role_permission_scopes ALL vs. FILTER mutual exclusivity guard
CREATE FUNCTION public.ops_role_permission_scope_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
BEGIN
  PERFORM 1 FROM public.role_permission_assignments
  WHERE tenant_id = NEW.tenant_id AND id = NEW.role_permission_assignment_id
  FOR UPDATE;

  IF EXISTS (
    SELECT 1 FROM public.role_permission_scopes
    WHERE tenant_id = NEW.tenant_id
      AND role_permission_assignment_id = NEW.role_permission_assignment_id
      AND scope_mode <> NEW.scope_mode
      AND id <> NEW.id
  ) THEN
    RAISE EXCEPTION 'ALL and FILTER scope modes cannot coexist on the same permission grant' USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER role_permission_scopes_guard
  BEFORE INSERT OR UPDATE ON public.role_permission_scopes
  FOR EACH ROW EXECUTE FUNCTION public.ops_role_permission_scope_guard();

-- 9. Terminal-state immutability guards (waitlist, online closure, note retraction, identity review)
CREATE FUNCTION public.ops_terminal_state_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
BEGIN
  IF NEW.id IS DISTINCT FROM OLD.id OR NEW.tenant_id IS DISTINCT FROM OLD.tenant_id
     OR NEW.created_at_utc IS DISTINCT FROM OLD.created_at_utc THEN
    RAISE EXCEPTION 'immutable identity' USING ERRCODE = '23514';
  END IF;
  IF NEW.aggregate_version <> OLD.aggregate_version + 1 THEN
    RAISE EXCEPTION 'aggregate version must advance by one' USING ERRCODE = '23514';
  END IF;
  -- Branch before accessing relation-specific record fields.
  CASE TG_TABLE_NAME
    WHEN 'appointment_waitlist_entries' THEN
      IF OLD.status IN ('CONVERTED','CANCELLED','EXPIRED') OR NEW.patient_id <> OLD.patient_id
         OR NEW.service_id <> OLD.service_id OR NEW.created_by_user_id <> OLD.created_by_user_id THEN
        RAISE EXCEPTION 'terminal waitlist or identity mutation' USING ERRCODE = '23514';
      END IF;
    WHEN 'online_availability_closures' THEN
      IF OLD.reopened_at_utc IS NOT NULL OR NEW.reopened_at_utc IS NULL
         OR ROW(NEW.service_id,NEW.resource_id,NEW.closure_date,NEW.starts_at_utc,NEW.ends_at_utc,NEW.reason,NEW.created_by_user_id)
         IS DISTINCT FROM ROW(OLD.service_id,OLD.resource_id,OLD.closure_date,OLD.starts_at_utc,OLD.ends_at_utc,OLD.reason,OLD.created_by_user_id) THEN
        RAISE EXCEPTION 'closure may only be reopened once' USING ERRCODE = '23514';
      END IF;
    WHEN 'patient_identity_reviews' THEN
      IF OLD.review_state <> 'NEEDS_COMPLETION' OR NEW.review_state NOT IN ('RESOLVED','CANCELLED')
         OR ROW(NEW.patient_id,NEW.reason,NEW.opened_by_user_id,NEW.opened_at_utc)
         IS DISTINCT FROM ROW(OLD.patient_id,OLD.reason,OLD.opened_by_user_id,OLD.opened_at_utc) THEN
        RAISE EXCEPTION 'invalid identity review transition' USING ERRCODE = '23514';
      END IF;
    ELSE RAISE EXCEPTION 'unexpected trigger relation' USING ERRCODE = '23514';
  END CASE;
  RETURN NEW;
END $$;

CREATE TRIGGER waitlist_terminal_guard
  BEFORE UPDATE ON public.appointment_waitlist_entries
  FOR EACH ROW EXECUTE FUNCTION public.ops_terminal_state_guard();
CREATE TRIGGER closure_terminal_guard
  BEFORE UPDATE ON public.online_availability_closures
  FOR EACH ROW EXECUTE FUNCTION public.ops_terminal_state_guard();
CREATE TRIGGER identity_review_terminal_guard
  BEFORE UPDATE ON public.patient_identity_reviews
  FOR EACH ROW EXECUTE FUNCTION public.ops_terminal_state_guard();

CREATE FUNCTION public.ops_note_action_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
BEGIN
  PERFORM 1 FROM public.patient_operational_notes
  WHERE tenant_id = NEW.tenant_id AND id = NEW.note_id
  FOR UPDATE;

  IF EXISTS (
    SELECT 1 FROM public.patient_note_actions
    WHERE tenant_id = NEW.tenant_id AND note_id = NEW.note_id AND action_kind = 'RETRACT'
  ) THEN
    RAISE EXCEPTION 'retracted operational note cannot receive further actions' USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER patient_note_actions_guard
  BEFORE INSERT ON public.patient_note_actions
  FOR EACH ROW EXECUTE FUNCTION public.ops_note_action_guard();

-- 10. Appointment lifecycle fact enforcement on new transitions (grandfathers legacy rows)
CREATE FUNCTION public.ops_appointment_lifecycle_facts_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
BEGIN
  IF NEW.status = 'CHECKED_IN' AND (TG_OP = 'INSERT' OR OLD.status IS DISTINCT FROM 'CHECKED_IN') THEN
    IF NOT EXISTS (
      SELECT 1
      FROM public.appointment_arrival_facts aaf
      JOIN public.clinic_visits cv
        ON cv.tenant_id = aaf.tenant_id AND cv.id = aaf.visit_id
      WHERE aaf.tenant_id = NEW.tenant_id
        AND aaf.appointment_id = NEW.id
        AND cv.arrived_at_utc IS NOT NULL
    ) THEN
      RAISE EXCEPTION 'new CHECKED_IN transition requires verified arrival fact and arrived_at_utc'
        USING ERRCODE = '23514';
    END IF;
  END IF;

  IF NEW.status = 'COMPLETED' AND (TG_OP = 'INSERT' OR OLD.status IS DISTINCT FROM 'COMPLETED') THEN
    IF NOT EXISTS (
      SELECT 1 FROM public.service_records sr
      WHERE sr.tenant_id = NEW.tenant_id
        AND sr.appointment_id = NEW.id
        AND sr.record_kind = 'PERFORMED'
    ) THEN
      RAISE EXCEPTION 'new COMPLETED transition requires a PERFORMED service_records entry'
        USING ERRCODE = '23514';
    END IF;
  END IF;
  RETURN NEW;
END $$;

CREATE CONSTRAINT TRIGGER appointments_lifecycle_facts_trg
  AFTER INSERT OR UPDATE OF status ON public.appointments
  DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW EXECUTE FUNCTION public.ops_appointment_lifecycle_facts_guard();

REVOKE ALL ON FUNCTION public.ops_item_service_link_check() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.ops_service_record_charge_link_check() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.ops_receipt_allocation_reconcile() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.ops_financial_adjustment_reconcile() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.ops_clinic_refund_reconcile() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.ops_inventory_lot_guard() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.ops_stock_movement_reconcile() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.ops_practitioner_mapping_guard() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.ops_role_permission_scope_guard() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.ops_terminal_state_guard() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.ops_note_action_guard() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.ops_appointment_lifecycle_facts_guard() FROM PUBLIC;
```

---


### B.4 D0.9 additional proposed integrity guards (NOT RUN)

Place this subsection after the B.3 functions in the applicable dependency packages, not after an unrelated migration. These guards improve relational/state checks; they do not prove external payment evidence, authorization, event delivery or correct lock acquisition by the application. Synthetic slice must keep external adapters and unreconciled advanced policies disabled. Install only the subset whose relations exist in the authorized validation DB.

```sql
-- Prevent a resource type change from invalidating a canonical practitioner mapping.
CREATE FUNCTION public.ops_bookable_resource_type_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
BEGIN
  IF NEW.resource_type IS DISTINCT FROM OLD.resource_type AND EXISTS (
    SELECT 1 FROM public.staff_practitioner_resources m
    WHERE m.tenant_id = OLD.tenant_id AND m.bookable_resource_id = OLD.id
  ) THEN
    RAISE EXCEPTION 'mapped practitioner resource type cannot change' USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER bookable_resources_practitioner_type_guard
  BEFORE UPDATE OF resource_type ON public.bookable_resources
  FOR EACH ROW EXECUTE FUNCTION public.ops_bookable_resource_type_guard();

-- Match instrument kind and active shift against receipt/refund facts.
-- Application must prelock shift before invoice/receipt guards. This check is not external verification.
CREATE FUNCTION public.ops_receipt_instrument_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
DECLARE
  v_method text;
  v_instrument record;
  v_shift record;
  v_expected_kind text;
BEGIN
  CASE TG_TABLE_NAME
    WHEN 'payment_receipts' THEN v_method := NEW.payment_method;
    WHEN 'clinic_payment_refunds' THEN v_method := NEW.refund_method;
    ELSE RAISE EXCEPTION 'unexpected relation';
  END CASE;
  IF NEW.shift_id IS NOT NULL THEN
    SELECT * INTO v_shift FROM public.cashier_shifts
      WHERE tenant_id = NEW.tenant_id AND id = NEW.shift_id FOR UPDATE;
    IF NOT FOUND OR v_shift.closed_at_utc IS NOT NULL
      OR NEW.occurred_at_utc < v_shift.opened_at_utc
      OR NEW.department_id IS DISTINCT FROM v_shift.department_id THEN
      RAISE EXCEPTION 'invalid cashier shift or department' USING ERRCODE = '23514';
    END IF;
  END IF;
  v_expected_kind := CASE v_method WHEN 'POS' THEN 'POS_TERMINAL'
    WHEN 'CARD_TO_CARD' THEN 'BANK_DESTINATION' WHEN 'ONLINE' THEN 'GATEWAY_MERCHANT'
    WHEN 'CASH' THEN 'CASH_REGISTER' END;
  IF NEW.instrument_id IS NOT NULL THEN
    SELECT * INTO v_instrument FROM public.clinic_payment_instruments
      WHERE tenant_id = NEW.tenant_id AND id = NEW.instrument_id FOR SHARE;
    IF NOT FOUND OR NOT v_instrument.is_active
      OR v_instrument.instrument_kind IS DISTINCT FROM v_expected_kind
      OR (v_instrument.department_id IS NOT NULL AND
          NEW.department_id IS DISTINCT FROM v_instrument.department_id) THEN
      RAISE EXCEPTION 'wrong or inactive payment instrument' USING ERRCODE = '23514';
    END IF;
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER payment_receipt_instrument_guard BEFORE INSERT ON public.payment_receipts
  FOR EACH ROW EXECUTE FUNCTION public.ops_receipt_instrument_guard();
CREATE TRIGGER clinic_refund_instrument_guard BEFORE INSERT ON public.clinic_payment_refunds
  FOR EACH ROW EXECUTE FUNCTION public.ops_receipt_instrument_guard();

-- This trigger verifies linkage and state, NOT trustworthiness of a bank/provider response.
-- Until a verified source/actor contract exists, runtime live ONLINE/CARD_TO_CARD posting is disabled.
CREATE FUNCTION public.ops_receipt_evidence_link_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
DECLARE
  a record;
  c record;
BEGIN
  IF NEW.payment_method = 'ONLINE' THEN
    SELECT * INTO a FROM public.payment_attempts
      WHERE tenant_id = NEW.tenant_id AND id = NEW.payment_attempt_id;
    IF NOT FOUND OR a.state IS DISTINCT FROM 'VERIFIED'
      OR a.expected_amount_irr IS DISTINCT FROM NEW.amount_irr
      OR a.currency_code IS DISTINCT FROM NEW.currency_code
      OR a.merchant_instrument_id IS DISTINCT FROM NEW.instrument_id
      OR a.beneficiary_patient_id IS DISTINCT FROM NEW.credit_beneficiary_patient_id
      OR NULLIF(btrim(NEW.provider_reference),'') IS NULL
      OR NULLIF(btrim(NEW.verification_evidence_ref),'') IS NULL THEN
      RAISE EXCEPTION 'receipt does not match verified attempt' USING ERRCODE = '23514';
    END IF;
  ELSIF NEW.payment_method = 'CARD_TO_CARD' THEN
    SELECT * INTO c FROM public.unverified_payment_claims
      WHERE tenant_id = NEW.tenant_id AND id = NEW.verified_claim_id;
    IF NOT FOUND OR c.state IS DISTINCT FROM 'VERIFIED'
      OR c.claimed_amount_irr IS DISTINCT FROM NEW.amount_irr
      OR c.currency_code IS DISTINCT FROM NEW.currency_code
      OR c.destination_instrument_id IS DISTINCT FROM NEW.instrument_id
      OR c.beneficiary_patient_id IS DISTINCT FROM NEW.credit_beneficiary_patient_id
      OR NULLIF(btrim(NEW.provider_reference),'') IS NULL
      OR NULLIF(btrim(NEW.verification_evidence_ref),'') IS NULL THEN
      RAISE EXCEPTION 'receipt does not match independently reviewed claim' USING ERRCODE = '23514';
    END IF;
  ELSIF NEW.payment_method = 'POS' AND NULLIF(btrim(NEW.verification_evidence_ref),'') IS NULL THEN
    RAISE EXCEPTION 'POS evidence missing' USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER payment_receipt_evidence_link_guard BEFORE INSERT ON public.payment_receipts
  FOR EACH ROW EXECUTE FUNCTION public.ops_receipt_evidence_link_guard();

-- Recheck linked line kinds and status when posting, even if a draft link was
-- created in a prior transaction and its lines subsequently changed.
CREATE FUNCTION public.ops_invoice_post_link_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
BEGIN
  IF OLD.status = 'DRAFT' AND NEW.status = 'POSTED' THEN
    IF EXISTS (
      SELECT 1 FROM public.invoice_item_service_links x
      JOIN public.invoice_lines i ON (i.tenant_id,i.invoice_id,i.id) = (x.tenant_id,x.invoice_id,x.item_line_id)
      JOIN public.invoice_lines l ON (l.tenant_id,l.invoice_id,l.id) = (x.tenant_id,x.invoice_id,x.service_line_id)
      WHERE x.tenant_id = NEW.tenant_id AND x.invoice_id = NEW.id
        AND (i.line_kind <> 'ITEM' OR i.line_status <> 'ACTIVE' OR l.line_kind <> 'SERVICE' OR l.line_status <> 'ACTIVE')
    ) THEN RAISE EXCEPTION 'invalid invoice item/service association' USING ERRCODE = '23514'; END IF;
    IF EXISTS (
      SELECT 1 FROM public.invoice_lines l
      WHERE l.tenant_id = NEW.tenant_id AND l.invoice_id = NEW.id AND l.line_status = 'ACTIVE'
       AND (l.basic_insurance_expected_share::numeric <> COALESCE((SELECT sum(e.expected_amount_irr)
          FROM public.invoice_insurer_expectations e WHERE e.tenant_id=l.tenant_id AND e.invoice_line_id=l.id AND e.coverage_kind='BASIC'),0)
        OR l.supplementary_insurance_expected_share::numeric <> COALESCE((SELECT sum(e.expected_amount_irr)
          FROM public.invoice_insurer_expectations e WHERE e.tenant_id=l.tenant_id AND e.invoice_line_id=l.id AND e.coverage_kind='SUPPLEMENTARY'),0))
    ) THEN RAISE EXCEPTION 'insurer expectation snapshot mismatch' USING ERRCODE = '23514'; END IF;
    IF EXISTS (SELECT 1 FROM public.invoice_insurer_expectations e JOIN public.invoice_lines l
      ON (l.tenant_id,l.invoice_id,l.id)=(e.tenant_id,e.invoice_id,e.invoice_line_id)
      WHERE e.tenant_id=NEW.tenant_id AND e.invoice_id=NEW.id AND l.line_status <> 'ACTIVE') THEN
      RAISE EXCEPTION 'expectation on removed invoice line' USING ERRCODE = '23514';
    END IF;
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER invoice_post_link_guard BEFORE UPDATE OF status ON public.invoice_documents
  FOR EACH ROW EXECUTE FUNCTION public.ops_invoice_post_link_guard();

-- Terminal tag removal cannot be undone or alter the original assignment.
CREATE FUNCTION public.ops_patient_tag_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY INVOKER SET search_path = pg_catalog, public AS $$
BEGIN
  IF OLD.removed_at_utc IS NOT NULL OR NEW.removed_at_utc IS NULL OR
    ROW(NEW.id,NEW.tenant_id,NEW.patient_id,NEW.tag_id,NEW.department_id,NEW.service_id,NEW.created_by_user_id,NEW.created_at_utc)
    IS DISTINCT FROM ROW(OLD.id,OLD.tenant_id,OLD.patient_id,OLD.tag_id,OLD.department_id,OLD.service_id,OLD.created_by_user_id,OLD.created_at_utc) THEN
    RAISE EXCEPTION 'tag assignment may only be removed once' USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER patient_staff_tag_guard BEFORE UPDATE ON public.patient_staff_tags
  FOR EACH ROW EXECUTE FUNCTION public.ops_patient_tag_guard();

REVOKE ALL ON FUNCTION public.ops_bookable_resource_type_guard() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.ops_receipt_instrument_guard() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.ops_receipt_evidence_link_guard() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.ops_invoice_post_link_guard() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.ops_patient_tag_guard() FROM PUBLIC;
```

**Important:** B.4 is an unexecuted proposed addition. Instrument and attempt/claim locks must be integrated into the complete ordered call graph before acceptance; current function bodies alone cannot establish trustworthy evidence or safe all-writer concurrency. In particular, mapping creation must prelock the actual resource before type check; instrument configuration must be serialized with financial commands; all composite references and insert-state guards must be verified against actual catalog. The remaining proof gaps in Appendix D are release blockers for their affected features.


---

## Appendix C — Audit resolution matrix (`D06-01` through `D06-15`) and remaining blockers

| Finding ID | Severity | Audit Defect Summary | D0.9 disposition (design only; validation remains open) |
|---|---|---|---|
| `D06-01` | Critical | Assumed `TP0008+` numbers were free | **Revised proposal, NOT VERIFIED:** Preserved `TP0001–TP0007`, protected `TP0011` and `R4.6` candidate allocations, marked unattached later roadmap/heads `SOURCE_REQUIRED`. |
| `D06-02` | Critical | Pending/default-verified receipts & invented methods | **Revised proposal, NOT VERIFIED:** Strict separation of `payment_attempts`, `unverified_payment_claims`, and `payment_receipts`; system callback `operator_user_id` nullable when `actor_type = 'SYSTEM_CALLBACK'`; `Gate B` kept closed for live providers. |
| `D06-03` | Critical | Editable posted invoices; optional triggers | **Revised proposal, NOT VERIFIED:** Mandatory `db_migrator` ownership, `FORCE RLS`, narrowed grants, and executable `ops_invoice_guard` / `ops_draft_child_guard` triggers (`Appendix B.1`). |
| `D06-04` | Critical | Unlinked FKs, missing reversals, ambiguous credit/refund math | **Revised proposal, NOT VERIFIED:** Composite parent FKs, immutable `REVERSE` allocations, `ledger_receipt_guards`, exact algebraic invariants and proposed deferred triggers (`Appendix B.3`). |
| `D06-05` | High | Missing shift/service/insurer/revenue-share facts | **Revised proposal, NOT VERIFIED:** Full schema + self-reversals; `SRC-10` (`Clause 739` legacy report) retained as explicit `SOURCE_REQUIRED`. |
| `D06-06` | High | Mutable stock balances, scale mismatch, unlimited returns | **Revised proposal, NOT VERIFIED:** Append-only `stock_movements`, composite `(tenant_id, item_id, quantity_scale)` FK, single origin bucket plus segregated quarantine, return caps, quarantine isolation, and zero-sum transfers (`Appendix B.3`). |
| `D06-07` | High | Unconstrained waitlist conversion & non-practitioner preference | **Revised proposal, NOT VERIFIED:** Composite `(tenant_id, converted_appointment_id, patient_id, service_id)` FK, practitioner-only `preferred_resource_id` FK, and terminal immutability trigger (`Appendix B.3`). |
| `D06-08` | Critical | Duplicated practitioner capacity across services | **Revised proposal, NOT VERIFIED:** 1:1 `staff_practitioner_resources` + M:N `staff_service_links` + `ops_practitioner_mapping_guard` (`Appendix B.3`). |
| `D06-09` | Critical | Polymorphic `scope_ref` without FK; ambiguous intersection | **Revised proposal, NOT VERIFIED:** Typed `role_permission_scopes` tied to `TP0003` grant IDs, formal within-row `AND` / across-row `OR` rules, `ALL`/`FILTER` mutual exclusivity trigger, and Rank 1 anti-escalation locking. |
| `D06-10` | High | Arrival `CHECK` broke legacy `CHECKED_IN`; missing service facts | **Revised proposal, NOT VERIFIED:** Separate `reception_groups`, `clinic_visits`, `appointment_arrival_facts`, `service_records`, and `historical_appointment_entries` + deferred transition trigger grandfathering legacy rows (`Appendix B.3`). |
| `D06-11` | High | All-null closure scope & booking/hold race | **Revised proposal, NOT VERIFIED:** Explicit `(service_id, resource_id)` + `Asia/Tehran` business-date bounds + Rank 2 `service_availability_guards` lock rank + terminal reopen trigger. |
| `D06-12` | High | Notes/tags lacked creator FKs, retraction immutability, visibility | **Revised proposal, NOT VERIFIED:** Append-only notes/actions, `ops_note_action_guard`, scoped tags, and PII-safe outbox/audit exclusions. |
| `D06-13` | High | Event table mistaken for canonical/alias merge | **Revised proposal, NOT VERIFIED:** Preserved `Clause 773` v1.3 canonical/alias requirement; gated merge implementation on actual v1.3 source. |
| `D06-14` | High | Incomplete triggers/grants/dependency order | **Revised proposal, NOT VERIFIED:** Complete `Appendix A` RLS/grants, partial proposed `Appendix B.1–B.3` triggers, and topological DAG (`§11`). |
| `D06-15` | High | Grouped acceptance counts & unrun browser/Windows checks | **Revised proposal, NOT VERIFIED:** Mandated exact 120-row scenario matrix, fresh-stack Playwright/visual/performance benchmarks, and explicit Windows runtime reporting. |



---

## Appendix D — D0.9 independent disposition and executable-validation boundary

### D.1 Change log and evidence

The complete D0.8 file was inspected and revised in place as D0.9, retaining all 51 candidate table definitions, the original package sections and historical finding identifiers. Corrections directly change conflicting scope quantifiers, Clause 783 allocation ordering, receipt/refund trigger lock order, cross-relation terminal trigger dispatch, non-lot inventory bucket/expiry constraints, lot provenance and transfer pairing, scaled billable and stock item FK constraints, per-revision RLS table selection, payment instrument/evidence-link checks and invoice posting link checks. D0.7 product/test safeguards missing from D0.8 were restored in context. None of the proposed SQL was executed. This is not a completed independent architectural convergence, approved design, or production-ready release. The prior candidate's claim of complete cross-row triggers is rejected.

The current live branch tip was independently rechecked at `8309f2a044e944123ddb1f49a8bad1255e4ce2e0`. The recursive repository tree contains only Tenant Plane migration files `tp0001` through `tp0007` at that SHA; no later revision files on that branch. That is not proof of all other branches, live main, the complete approved roadmap, or a successful Alembic upgrade. Historical verified CI run `45850924219` yielded 222 passed, 1 skipped; Task 32 reports 54 Playwright passes, screenshots and median SQL timings. None executes this D0.9 SQL. No new repository changes, PR changes, tests or migration executions occurred in this review. A file-only audit cannot prove SQL compilation, role grants, concurrent correctness or operational performance.

Source input SHA-256 (exact supplied files):

- D0.7: `81b1cfeaed99fa4dadcb4caa362027e41fab64d66b3bb735b652a0663f02c5b0`
- D0.8: `eec7a5e2870080b1e089c1c6c77a1936759645680ff1899ad6b2d96153988e7a`


### D.2 Remaining proof/contract gaps — no false closure

All rows below remain OPEN unless real current evidence establishes closure. D0.9 repairs identifiable defects, but intentionally does not fabricate approved rules or claim a full executable migration. A failure in a row blocks the affected feature activation, not unrelated Gate A development. Recommended handling is one consolidated disposable PG15 validation cycle with direct fixes to a complete next revision, then narrowly scoped independent review of the corrected full artifact and evidence.

| ID | Boundary / remaining risk | Required closure evidence and decision |
|---|---|---|
| D09-01 | Migration/source: later approved roadmap/F2-B/live main/SRC-12 not attached | Inspect actual source, reconcile allocations without changing TP0001–TP0007 or protected TP0011; return official proposed revisions, down_revision graph and approval request. Never assign arbitrary ID or repurpose TP0020–21. Preserve Package 1 vs Package 4 and Gates A–D. |
| D09-02 | RLS and trigger install ordering: Appendix A requires explicit subset, B functions span packages, existing TP0007 grants may permit more columns than claimed | Assemble a real topological SQL validation harness against actual TP0001–0007 catalog. Apply every new table's ENABLE/FORCE RLS, root/composite tenant FKs, role ownership, explicit grants in same step. No `IF NOT EXISTS` drift. Check role login/inheritance, missing tenant context, cross-tenant SELECT/INSERT/UPDATE/DELETE/attachments, function search_path and trusted schema creation privileges. Per-column mutation policies and function execution privileges must be proven. No runtime owner/superuser or RLS bypass. |
| D09-03 | Lock order: earlier D0.8 inverted invoice/receipt and used incorrect allocation key; new FK/trigger locks still need complete ordering | Draw actual writer call graph including instrument/attempt/claim, cashier shift, invoice, receipt guards, stock and service/eligibility metadata. Mandatory prelocks and deterministic full sets, restart on rediscovery, READ COMMITTED fresh reads and two-session PG race tests. Prove concurrent cross-invoice refunds, multiple receipts/lines, shift close, provider state updates, stock returns, eligibility and closure. Reject stale or missing guard, handle deadlocks safely; no deadlock-free claim. |
| D09-04 | Receipt truth and attempt/claim lifecycle: B.4 checks linked state, not evidence authenticity or state transition integrity | Implement exact initial and legal transition guards, immutable attempt identity/expected amount/merchant/order, review attribution, callback worker authentication, verified evidence binding and late verified payment path per 706.1/784–786. Reject pending claim, arbitrary evidence string, wrong instrument, stale shift, wrong amount/beneficiary, duplicate reference, ambiguous callback. No live CARD_TO_CARD/ONLINE; test CASH and isolated POS simulation using fake evidence clearly labeled. For refunds prove actual money-out, linked limits and state; define separate requests/reconciliation for uncertain external refunds. No fake `VERIFIED` money. |
| D09-05 | Ledger posting and financial reporting: B.1/B.3/B.4 do not cover every mutation or exact arithmetic | Preserve active lines, immutable posting, validate quantity×tariff with versioned rounding, actual line/whole invoice fixed and percentage discount action totals, subsidy/rounding/payer identities, posted history and allocation reversals. Implement explicit compensation for superseded draft discount actions (append-only), exact policy/version and approved thresholds. Prevent active linked line invalidation across draft transactions; link actual service/appointment and matching patient, including across both link methods. Test direct SQL, retry, concurrency, over-allocation, negative obligations, partial/full refunds, credit/debt and whole-invoice rounding. Prove all 21 clause 725 dimensions and 7 report families where supported; SRC-10 independent. |
| D09-06 | Insurer and revenue-share: D0.8 includes tables but no complete cross-row settlement/reversal/share bound functions | Enforce posted active line and exact expected-share snapshot; remittance/reversal references correct original kind and cumulative caps, no double count, patient debt independent. Define distributable base, policy version, allowed beneficiaries, exact share upper bound and adjustment links to same line/refund/adjustment, nonnegative net share and rounding. Provide actual executable functions + tests; advanced policies remain fail-closed until resolved; synthetic self-pay workflow may be separately validated. Insurer API evidence Gate B, legal Gate C. |
| D09-07 | Inventory: lot status event synchronization, actual service/charge links, write-off return pairing, FEFO lock coverage and unit policies incomplete | Enforce immutable lot origin, no available quarantine/recalled/expired units, status change exactly one ordered event, valid source disposition, actual BOM/version/delivery links, movement signs and nonnegative reconciled lot balance, return cap under item lock. WRITE_OFF return must have matched compensating movement in same UoW with identity link and exact amount; no direct positive AVAILABLE return bypass. Transfer pair must stay within item/scale and authorized disposition. Use authoritative Tehran transaction date for current operations; historical stock adjustments need separately authorized actual-time policy. Validate optional entitlement and non-stock operation, authorized manager override without silent negative stock. |
| D09-08 | Scope and role enforcement: schema is tenant RLS, not application authorization | Implement one exact resolver with all-practitioner coverage, verified full object facts, safe projection of out-of-scope conflicts and patient identity, cache and role changes serialized. Check safe activation/backfill, no scope default widening, department eligibility, no self elevation/last owner removal, all read/write paths incl audit/export and replay. Prove races with actual active users and old workers drained. D0.9 formal predicate replaces contradictory D0.8. |
| D09-09 | Practitioner eligibility and online close: guards need lifecycle/all-writer adoption | Backfill from real evidence only, initialize guards for all active services in same UoW, never bypass if guard missing; lock service(s) before resources, all MANUAL/ONLINE writers that validate eligibility, provider/resource deactivation, eligibility/catalog mutations and multi-service groups. Protect resource capacity and mapping uniqueness/type. Verify online closure vs new bookings, active holds preserved, late verified money credit/refund, overlapping closures, reopen and Cloud authority. No claim local offline closure reaches web. |
| D09-10 | Arrival/service/historical facts: deferred trigger only checks forward status transition, facts can be inconsistent in reverse direction | Enforce canonical state machine and allocation mapping, legitimate new arrival/visit/check-in/performed facts, actual server recording time, one physical visit counted correctly, no false completion, patient/appointment/visit/service/department/practitioner association. No historical fabricated timestamps; future-only normal reschedule, authorized historical command reason and reminder suppression. Prevent direct fact insertion for invalid appointment states; grandfather only genuinely pre-existing records, not newly forged terminal inserts. Real PG and browser tests with multiple visits, cancellation and stock rollback. |
| D09-11 | Waitlist/notes/tags/reviews: terminal UPDATE guards insufficient for initial states, note supersession and privacy | Validate initial OPEN/pending states, terminal conversion only through booking UoW, no waitlist capacity; initial closure unreopened, initial tag active, initial identity review pending; exact timestamp and immutable actor/source. Serialize note supersession and pin/retract, prevent cycles/scope widening, preserve safe read projection and privacy/erasure. Test same-tenant out-of-scope and concurrent writes. Identity completion not official verification. |
| D09-12 | Crypto and canonical merge | Keep OI-04/05 engineering open; exact v1.3 alias source required for merge. Isolated test keys only with real AES-GCM/AAD/HMAC tests; no live provider/KMS claims. Preserve audit and history; no destructive or auto merge. Independent unaffected identity completion can advance. |
| D09-13 | Outbox, sync, APIs, retention and provider | Verify actual TP0006 event type registration, producer/consumer authority and payload schemas; no fabricated external evidence. Correct event/operation idempotency, privacy, retention/erasure and backup coverage. Define exact request/response/permission/error schemas and command state transitions before implementation. Scope-aware single-node synthetic operations may be tested independently of external provider verification. |
| D09-14 | Product acceptance evidence | Exact 120 individual rows with test IDs, result, pinned SHA and environment, no estimated counts. Full synthetic data, browser/visual/perf, Tehran rollover, actual Windows auto-launch, no production data. Fix benchmark disposable-database refusal and raw audit projection. Existing successful CI is historical; D0.9 SQL and new workflows NOT RUN. |

### D.3 Synthetic validation-only request (requires express owner authorization)

A validation harness may be built in a separate disposable local PG15/Testcontainers database or isolated temporary workspace only after the owner explicitly authorizes this validation-only task. This is **not** approval to land or execute new Alembic revisions on the development preview, merge, deploy, change PRs or use real patient data. Do not mutate historical TP0001–TP0007. The existing authorized baseline migrations may be applied inside that disposable harness. Draft SQL may be assembled and executed solely there for review, with no official revision assignment and no change to the preview database. Destroy the disposable validation environment after capturing evidence. Enforce safety guardrails before opening any database connection.

1. Pin and inspect actual baseline, all proposed dependencies and available authoritative sources; report missing sources separately. Use SQL block extraction and topological relation/function/trigger ordering, not copy/paste the document order. Include all proposed tables except explicitly source-blocked merge; no fake schema substitutions or `IF NOT EXISTS` shortcuts. Reject external/production DSNs and keys, disable outbound live adapters, use generated credentials in disposable topology.
2. Compile/execute each applicable proposed schema subset under db_migrator, establish exact runtime grants/RLS and actual db_app_runtime login test. Capture `pg_catalog`, errors and resolved fixes. Verify constraints, trigger execution, valid state transitions, and direct-SQL rejection cases. No PASS when a path is skipped or missing. All proposed SQL is unverified until executed.
3. Run targeted positive/negative/concurrency tests from D.2 (including valid cash/partial payment/discount/refund, scope and multi-provider checks, closure and manual overlap, stock movement/return/expiry, current vs historical arrival, notes and identity). Diagnose and correct failing proposed SQL and its precise writer contracts in one full revised Markdown candidate; do not merely remove the constraint or suppress an error. If a capability genuinely needs source or approved business policy, leave it explicitly BLOCKED and explain the minimum evidence/decision required. No claims of implementing a UI merely by validating DDL.
4. Return one full corrected Markdown revision (D0.10), a concise reproducible command/test evidence manifest with exact SHA and actual PASS/FAIL/SKIP/BLOCKED/NOT RUN, a proposed lineage reconciled against actual sources, and a short consolidated ratification request. Retain all valid D0.9 content and open items. No production readiness claim. Source proof, validation-only authorization, independent review convergence, explicit implementation migration approval, actual implementation, and product acceptance are distinct steps.

### D.4 Product-owner decision summary (proposals, not approvals)

Recommend deterministic largest-remainder invoice discount allocation, Tehran end-of-day expiry policy, one actual practitioner resource across all services, optional internal departments, typed scope union with all-practitioner coverage, explicit head-receptionist permissions, actual arrival and distinct future waitlist, single-node synthetic closure preserving valid existing holds, non-stock billing without inventory, immutable ledger and actual receipt/refund separation. These are engineering/product proposals for ratification; no unapproved migration may be landed. Do not ask the owner to invent revision IDs or SQL. Do not conflate prototype completeness with production authorization. No repeated broad rewrite before actual technical evidence is obtained.

### D.5 Historical D0.7 change record (retained for traceability, not current instructions)

### D0.6 → D0.7 change log

1. Corrected unsupported free migration number assertion; retained initial frozen lineage and protected later candidate reservations, particularly TP0011. Latest approved roadmap remains source-required.
2. Replaced unsafe receipt default/pending receipt with distinct attempts, claims and verified actual receipts; canonical payment vocabulary, managed instruments, shift/operator/context and explicit method evidence; external adapter evidence not fabricated.
3. Expanded ledger relations for immutable posted facts, parent-consistent invoice-line links, explicit allocation reversals, signed adjustments, linked refunds, derived patient credit/debt, insurer and revenue-share facts; no double counting or editable balance. Added proposed pricing allocation policy and hard integrity requirement. Exact cross-row trigger/evidence policy still needs review.
4. Independent non-stock billable catalog; stock ledger optional, same-item/lot FK, signed movement/disposition/FEFO, return limits, no automatic future deduction or mutable stock balance.
5. Corrected waitlist creator/converted identity/terminal/priority/state contract and conversion atomicity.
6. Canonical practitioner mapping prevents multiplying resource capacity; separate explicit multi-skill eligibility.
7. Typed scope FK attached to actual permission grant, formal union/conjunction semantics, explicit ALL backfill, department grouping and anti-escalation, scope-aware identity/conflict/finance/audit access.
8. Replaced invalid arrival backfill/constraint with separate group, actual visit, per-appointment arrival, service and historical facts; no fabricated timestamps; preserve canonical status mapping and grandfather legacy unknown arrival.
9. Closure targets explicit service and optional practitioner, scoped actor and date constraints, proposed serialization/authority and hold-conversion rules; no weakening of existing bookings/EXCLUDE.
10. Notes/tags append-history and actor FKs, explicit visibility, correction/pin/retract, safe audit.
11. Identity completion review and canonical merge source dependency preserved; event table alone not alias implementation; no fake production crypto evidence.
12. Reconciled logical dependency order, security/RLS/grants, outbox compatibility, external gates and exact demo/acceptance obligations. Existing implementation status and open items remain explicit.

The complete D0.6 document was inspected. This revised standalone candidate retains the substantive logical packages and valid prior requirements, replaces defective DDL/semantics and expands missing contracts. It is not a byte-for-byte preservation of the old proposal; defective fields, constraints and unsafe semantics were intentionally replaced. All added DDL is **proposed design**, not extracted existing schema or proven execution. No new SQL was executed. Remaining gaps and decisions are explicitly enumerated below rather than mislabeled as approval-ready.

END OF ACR-D0.9 — PROPOSED / CHANGES AND EXECUTION PROOF REQUIRED

---

END OF ACR-D0.11 — PROPOSED / DEEP EXECUTION-VALIDATED / OPEN ITEMS PRESERVED

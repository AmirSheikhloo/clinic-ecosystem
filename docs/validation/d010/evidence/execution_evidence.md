# D0.10 disposable PG15 execution evidence

Generated: `2026-11-26T22:33:48.946519+00:00`

- Cases passed: **25**
- Cases failed: **0**
- Findings resolved: **13**
- Findings open: **0**
- Source unavailable: **1**

## Cases

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

## Findings

### D09-01 — ACR-D0.9 source text unavailable in execution environment
- Severity: BLOCKER_FOR_1TO1_MAP
- Status: **SOURCE_UNAVAILABLE**
- Evidence: Task 33 claimed attached ACR-D0.9; file absent; Gmail auth declined.
- Correction: Proceeded with ACR-D0.6 proposed SQL + disposable evidence; remap when D0.9 arrives.

### D09-02 — RLS policy naming drift vs tp0007 / Appendix F.6
- Severity: HIGH
- Status: **RESOLVED**
- Evidence: ACR-D0.6 prose used tenant_isolation_guard; live tp0007 uses tenant_runtime_guard.
- Correction: D0.10 + rls_clause746.sql use tenant_runtime_guard.

### D09-03 — Mandatory composite FKs used MATCH SIMPLE
- Severity: HIGH
- Status: **RESOLVED**
- Evidence: invoice_documents.beneficiary_patient_id is NOT NULL but FK was MATCH SIMPLE (clause 743).
- Correction: Corrected to MATCH FULL in corrected/01_tp_ops_ledger.sql.

### D09-04 — RLS/grants specified only in prose, not executable SQL
- Severity: HIGH
- Status: **RESOLVED**
- Evidence: Proposed packages lacked ENABLE/FORCE RLS and grants; runtime roles untested.
- Correction: Added docs/validation/d010/rls_clause746.sql and executed against db_app_runtime.

### D09-05 — Append-only finance tables lacked revoke/trigger evidence
- Severity: HIGH
- Status: **RESOLVED**
- Evidence: payment_receipts UPDATE succeeded under prose-only grants.
- Correction: Append-only via BEFORE UPDATE/DELETE reject triggers (UPDATE kept for FOR UPDATE locks); case finance_receipt_append_only.

### D09-06 — Refund cumulative cap not enforced in DDL
- Severity: HIGH
- Status: **RESOLVED**
- Evidence: Over-refund inserts possible without app FOR UPDATE discipline.
- Correction: Added clinic_refund_amount_within_receipt trigger; verified.

### D09-07 — inventory_item_id FK never closed after inventory package
- Severity: MEDIUM
- Status: **RESOLVED**
- Evidence: Ledger left inventory_item_id dangling without deferred FK step.
- Correction: Corrected inventory package adds MATCH SIMPLE FK when invoice_lines exists.

### D09-08 — DEPARTMENT scope_kind without departments catalog
- Severity: HIGH
- Status: **RESOLVED**
- Evidence: Scopes DDL allowed DEPARTMENT without referent table.
- Correction: Added departments + integrity trigger in corrected scopes package.

### D09-09 — Arrival CHECK unsafe for Expand-and-Contract upgrades
- Severity: MEDIUM
- Status: **RESOLVED**
- Evidence: Immediate CHECK on CHECKED_IN∧arrived_at would fail populated upgrades.
- Correction: Constraint added NOT VALID; VALIDATE after backfill demonstrated.

### D09-10 — Online closures allowed null service and resource (no target)
- Severity: MEDIUM
- Status: **RESOLVED**
- Evidence: Clinic-wide vs targeted closure ambiguous; empty target accepted.
- Correction: Added online_availability_closures_target_chk + created_by FK.

### D09-11 — Waitlist/notes missing created_by composite FKs
- Severity: MEDIUM
- Status: **RESOLVED**
- Evidence: Operator attribution columns lacked tenant-scoped FKs.
- Correction: Added MATCH FULL FKs to user_accounts.

### D09-12 — Official tp0008+ must not be invented
- Severity: GOVERNANCE
- Status: **RESOLVED**
- Evidence: Lineage audit: only tp0001–tp0007 on disk; Appendix E.2 ends at TP0007.
- Correction: Packages remain logical TP-OPS-*; no Alembic files landed.

### D09-13 — Financial identity CHECK + derived balance reconciliation
- Severity: HIGH
- Status: **RESOLVED**
- Evidence: Executable proof of identity CHECK and receipt allocation equality.
- Correction: Cases finance_line_* and finance_reconciliation_paid.

### D09-14 — Practitioner eligibility + FEFO inventory + lifecycle arrival
- Severity: HIGH
- Status: **RESOLVED**
- Evidence: Behavioral cases for staff_service_links, FEFO order, CHECKED_IN+arrived_at.
- Correction: See evidence cases list.


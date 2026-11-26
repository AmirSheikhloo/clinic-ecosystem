# ACR-D0.9 disposable PG15 execution evidence

Generated: `2026-11-26T22:43:00.409285+00:00`
ACR-D0.9 SHA-256: `7171bfc10589410a60d857b5b14814f2475d4412d78071eb7bfedc7955465b40`

- Apply OK: 17
- Apply FAIL: 0
- Apply SKIPPED: 1
- Cases PASS/FAIL/BLOCKED: 23/0/1

## Apply log

- `OK` [raw/step3_eligibility] 05.sql
- `OK` [raw/step3_departments] 06.sql
- `OK` [raw/step4_scopes] 07.sql
- `OK` [raw/step4_notes] 10.sql
- `OK` [raw/step4_identity_reviews] 11.sql
- `OK` [raw/step5_arrival] 08.sql
- `OK` [raw/step5_waitlist] 04.sql
- `OK` [raw/step5_online_close] 09.sql
- `OK` [raw/step7_ledger_core] 00.sql
- `OK` [raw/step7_ledger_core] 01.sql
- `OK` [raw/step7_ledger_core] 02.sql
- `OK` [raw/step7_b2_receipt_guards] 15.sql
- `OK` [raw/step7_b1_invoice_guards] 14.sql
- `OK` [raw/step9_inventory] 03.sql
- `OK` [raw/step7_b3_crossrow] 16.sql
- `OK` [raw/step7_b4_misc] 17.sql
- `OK` [raw/appendix_a_rls] 13.sql
- `BLOCKED` 12.sql — D09-12 / §10.3 person_merge_events SOURCE_REQUIRED (v1.3 alias)

## Cases

- `PASS` lineage_head_tp0007 — tp0007
- `PASS` postgres_15 — 15.20 (Debian 15.20-1.pgdg13+1)
- `BLOCKED` skip_12.sql — D09-12 / §10.3 person_merge_events SOURCE_REQUIRED (v1.3 alias)
- `PASS` raw_d09_apply_all_non_skipped
- `PASS` eligibility_mapping_insert — ['bookable_resource_id', 'created_at_utc', 'id', 'is_active', 'staff_profile_id', 'tenant_id', 'updated_at_utc']
- `PASS` rls_departments_cross_tenant_hidden
- `PASS` rls_departments_no_tenant_fail_closed
- `PASS` rls_invoice_policy_names — {'tenant_runtime_base', 'tenant_migrator_maintenance', 'tenant_runtime_guard'}
- `PASS` function_present_ops_invoice_guard
- `PASS` function_present_ops_receipt_allocation_reconcile
- `PASS` function_present_ops_practitioner_mapping_guard
- `PASS` function_present_ops_inventory_lot_guard
- `PASS` function_present_ops_terminal_state_guard
- `PASS` function_present_ops_appointment_lifecycle_facts_guard
- `PASS` invoice_draft_insert
- `PASS` invoice_rejects_non_draft_insert
- `PASS` inventory_lots_present
- `PASS` inventory_fefo_index_present
- `PASS` waitlist_present
- `PASS` online_closures_present
- `PASS` arrival_facts_present
- `PASS` service_records_present
- `PASS` invoice_guard_trigger_installed
- `PASS` rls_rejects_forged_tenant_insert

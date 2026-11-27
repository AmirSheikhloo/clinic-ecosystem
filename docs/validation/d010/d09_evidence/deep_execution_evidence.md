# ACR-D0.9 deep disposable PG15 evidence

Generated: `2026-11-27T00:10:27.836486+00:00`
PASS/FAIL/BLOCKED: **38/0/2**

## Cases

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
- `PASS` [IMPLEMENTATION_ACCEPTANCE] inventory_paired_write_off_return — paired=2
- `PASS` [IMPLEMENTATION_ACCEPTANCE] inventory_write_off
- `PASS` [PRE_IMPLEMENTATION] scopes_all_filter_mutual_exclusion
- `PASS` [PRE_IMPLEMENTATION] eligibility_one_to_one_mapping
- `PASS` [PRE_IMPLEMENTATION] online_closure_insert
- `PASS` [PRE_IMPLEMENTATION] online_closure_reason_required
- `PASS` [PRE_IMPLEMENTATION] arrival_checked_in_same_uow
- `PASS` [PRE_IMPLEMENTATION] historical_entry_recorded
- `PASS` [PRE_IMPLEMENTATION] waitlist_terminal_immutable
- `PASS` [IMPLEMENTATION_ACCEPTANCE] concurrency_refund_race_exactly_one_ok — results=ok,err:CheckViolationError
- `PASS` [IMPLEMENTATION_ACCEPTANCE] concurrency_refund_race_not_both_ok — results=ok,err:CheckViolationError
- `PASS` [IMPLEMENTATION_ACCEPTANCE] concurrency_refund_total_within_receipt — total=5E+4
- `PASS` [IMPLEMENTATION_ACCEPTANCE] concurrency_refund_competing_rejected — errs=['err:CheckViolationError']
- `PASS` [PRE_IMPLEMENTATION] rls_append_only_delete_denied
- `PASS` [PRE_IMPLEMENTATION] rls_missing_tenant_fail_closed
- `PASS` [PRE_IMPLEMENTATION] rls_cross_tenant_select_hidden
- `PASS` [PRE_IMPLEMENTATION] runtime_cannot_alter_schema
- `PASS` [PRE_IMPLEMENTATION] runtime_select_invoices_ok

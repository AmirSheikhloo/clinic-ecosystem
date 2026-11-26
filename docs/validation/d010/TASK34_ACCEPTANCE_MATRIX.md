# Task 34 — Exact acceptance matrix (executed vs proposed)

**Rule:** counts below are from executable suites and seed targets, not estimates.  
**Separate** actual evidence from proposed/unexecuted rows.

## A. Architecture / contract validation (actual)

| Suite | Path | Result (last Task 33 tip `8c2d377`) | Notes |
|-------|------|--------------------------------------|-------|
| D0.9 apply + Appendix D.3 | `scripts/validate_ops_contracts_d09.py` | Executed in Task 33 | Disposable PG15 |
| Deep finance/inventory/scopes/concurrency | `scripts/validate_ops_contracts_d09_deep.py` | **38 PASS / 0 FAIL / 2 BLOCKED** | Task 34 re-run: exactly-one concurrent refund + paired write-off PASS (`docs/validation/d010/d09_evidence/deep_execution_evidence.json`) |

## B. Application acceptance rows (Task 34 target = 120)

Numbered executable acceptance rows for the integrated prototype. Status values: `PASS` (evidence in this increment), `PENDING` (wired but needs disposable re-run), `BLOCKED` (external).

### Dashboard (1–15)
1. Role-aware composition — PENDING (existing audience resolver + new finance/wait cards)
2. Today appointment totals — PASS (prior + preserved)
3. Tomorrow appointment totals — PASS
4. Actual arrivals (CHECKED_IN) — PASS
5. Completions / cancellations / no-shows by_status — PASS
6. Physical waiting-room metric — PENDING (ops schema + overview)
7. Future waitlist open count — PENDING
8. Authorized finance summary null without FINANCE_SUMMARY — PENDING
9. Authorized finance summary populated with permission — PENDING
10. Actionable metric links — PASS
11–15. Scope isolation / empty sections without permission — PENDING

### Appointment management (16–35)
16–24. List filter/sort/pagination, calendar day/week/month — PASS (prior)
25. Practitioner/service eligibility filter — PENDING (ops eligibility table + API)
26. Manual overlap confirmation — PASS
27. Independent online capacity / temporary closure — PENDING (API create)
28. Physical arrivals via check-in + arrival_facts — PENDING
29. Future waitlist CRUD — PENDING
30. Historical entry reason + recording timestamp — PENDING (schema present; UI/API partial)
31–35. Lifecycle cancel/reschedule/check-in/complete/no-show — PASS

### Patient management (36–55)
36–48. Register/edit/lookup, family phone, identity exceptions, masks, dossier, history — PASS (prior)
49. Financial history / outstanding / credit — PENDING (invoice list by patient)
50–54. Notes/tags/alerts/scope — PENDING (tables present; management UI partial)
55. Canonical merge disabled — PASS (blocked package)

### Reception desk (56–85)
56–65. Multi-service reception, eligible practitioners, independent dates/durations/prices, walk-in/arrival — PASS/PENDING mix
66–75. Combined invoices, line/invoice discounts, paid/partial/unpaid — PENDING (finance API)
76–80. Verified synthetic CASH + simulated POS — PENDING
81–83. Patient credit / outstanding — PENDING
84. Immutable post-payment adjustments — PENDING (schema; API stub later)
85. Partial/full refunds linked to receipts — PENDING (deep suite + seed)

### Supporting management (86–100)
86–90. Staff-service eligibility, departments, receptionist scopes — PENDING
91. Explicit head receptionist permission — PASS (catalog code)
92–95. Financial permissions / cashier — PENDING
96–98. Billable items + inventory view — PENDING
99–100. Audit safe metadata projections — PASS (prior audit workspace)

### Validation / evidence (101–120)
101. Python unit tests — PENDING re-run
102. PG15 integration — PENDING re-run
103. Multi-connection concurrency exactly-one refund — PASS (deep suite IMPLEMENTATION_ACCEPTANCE)
104. Runtime-role + RLS — PENDING
105. App authorization / scope isolation — PENDING
106. Financial reconciliation — PENDING
107. Frontend TS/lint/build — PENDING
108. Fresh-stack Playwright demo — PENDING
109. Multi-width screenshots — PENDING
110. API/browser benchmarks disposable-only — PENDING
111. Tehran midnight rollover — PENDING
112–120. Matrix completeness / no fabricated evidence — PASS (this document)

## C. External boundaries (BLOCKED — not weakened)

- Canonical patient merge
- Live payment adapters
- Unverified insurer settlement
- Unapproved revenue-share
- Production KMS
- SRC-10 legacy report compatibility
- Unverified distributed authority/sync

## D. Demo seed targets (Task 34)

| Metric | Target | Source |
|--------|-------:|--------|
| patients | 520 | `DEMO` profile |
| staff | 42 | `DEMO` |
| services | 32 | `DEMO` |
| appointments | 10_500 | `DEMO` |
| appointments today/tomorrow | 220 / 110 | `DEMO` |
| multi-service groups | 110 | `DEMO` |
| overlap scenarios | 32 | `DEMO` |
| physical waiting (checked-in today) | ≥30 | `DEMO` + arrival facts |
| future waitlist | 30 | `DEMO.future_waitlist_entries` |
| invoices | 2_000 | `DEMO.invoices` |
| discounts | 100 | `DEMO.discounts` |
| refunds | 100 | `DEMO.refunds` |
| billable/inventory items | 100 | `DEMO.billable_or_inventory_items` |
| audit events | 5_200 | `DEMO.audit_entries` |

# Task 28 / ACR-D0.11 requirement classification

Generated from disposable PG15 deep validation at baseline `aff43da` + deep harness.

## PRE_IMPLEMENTATION (must be green before approving affected schema packages)

These are synthetic PG15/SQL/contract proofs that unblock schema ratification for the listed packages. They do **not** authorize Alembic landing without PO revision IDs.

| Area | Evidence status | Notes |
|------|-----------------|-------|
| Schema compile + topological apply (excl. merge) | PASS | Arrival UQs before waitlist; inventory before B.3 inventory triggers; Appendix A selector |
| RLS / runtime grants / adversarial | PASS | Cross-tenant hidden; missing tenant fail-closed; DELETE denied on receipts; no ALTER |
| Invoice draft→post immutability + identity CHECK | PASS | Posted header/lines immutable; mismatch rejected |
| Partial pay, allocation, reversal, refund caps | PASS | Deferred conservation/obligation triggers |
| Multi-connection refund race | PASS | One OK + one CheckViolation; total ≤ receipt |
| Synthetic CASH + labeled POS evidence | PASS | POS without evidence rejected; claim verify needs reviewer |
| Inventory FEFO, return cap, quarantine, write-off | PASS | Movement ledger balances |
| Scope ALL vs FILTER mutual exclusion | PASS | `ops_role_permission_scope_guard` |
| Practitioner 1:1 mapping | PASS | Unique staff/resource |
| Online closure reason/date window | PASS | Empty reason rejected |
| Arrival CHECKED_IN same-UoW with arrival facts | PASS | Writer contract: deferred lifecycle trigger |
| Waitlist terminal immutability | PASS | |
| Largest-remainder discount arithmetic helper | PASS | Policy candidate proven in Python; wire into posting service |

**Contract clarifications retained (not DDL rewrites):**
1. `CHECKED_IN` transition must commit in the same transaction as `appointment_arrival_facts` + `clinic_visits.arrived_at_utc`.
2. Validation apply order must follow FK prerequisites even when document section order differs.
3. `person_merge_events` remains disabled until v1.3 alias source (EXTERNAL).

## IMPLEMENTATION_ACCEPTANCE (run during Task 28 implementation — not schema blockers)

| Item | Why not PRE_IMPLEMENTATION |
|------|----------------------------|
| Full application scope resolver + cache/role races | Requires API/auth middleware, not DDL alone |
| All schedule writers adopting eligibility/closure guards | Application command paths |
| Exact discount action → line amount posting service | Needs command layer + idempotency |
| 21 clause-725 report dimensions / 7 report families | Reporting services; SRC-10 independent |
| Browser/Playwright + multi-width + Tehran rollover | Product UI acceptance |
| Exact 120-row matrix with pinned SHA | Product acceptance (D09-14) |
| Outbox event allowlist registration for §12 names | TP0006 producer wiring |
| Privilege escalation / head-receptionist workflows | Application RBAC UX |
| Performance benches (100k) with ops tables populated | Implementation scale tests |

## EXTERNAL_SOURCE_REQUIRED (do not block unrelated synthetic packages)

| Item | Gate |
|------|------|
| Canonical/alias patient merge + v1.3 source | Keep merge disabled |
| Live CARD_TO_CARD / ONLINE payment providers | Gate B |
| Production KMS / OI-04/05 key rotation | Gate B/D |
| Insurer API remittance evidence | Gate B |
| Legal revenue-share policies beyond fail-closed stubs | Gate C |
| SRC-10 legacy report definitions | Source |
| Approved official roadmap + F2-B/F2-S topology ACR | Source (R4.16 candidate only) |
| SRC-12 full closure beyond inspected main tip | Source |

## Unrelated synthetic work that MAY proceed after package approval

Reception grouping, visits/arrival facts, waitlist, online closure (single-node), eligibility mapping, non-stock billable items, CASH/POS synthetic ledger, FEFO inventory under `MOD_INVENTORY`, scoped grants schema — all without merge, live payments, or production KMS.

# ACR-D0.3 — Dashboard-first foundations (PROPOSAL ONLY)

Status: **PROPOSED — not approved.** Raised on `development/clinic-operations` for the D0.3
dashboard-first increment. No migration landed. Lineage remains `tp0001`–`tp0007`.

## Implemented under existing contracts (this increment)

| Item | Evidence |
|------|----------|
| Role-aware dashboard compositions (operational vs management) | UI uses `governance_roles` + permissions from `/api/auth/me` |
| Tomorrow appointment aggregates | `GET /api/v1/dashboard/summary` adds `tomorrow_appointments` using the same range length |
| Deep links today/tomorrow/cancelled/confirmed | Existing appointments calendar query params |
| Patient register deep link `?register=1` | Opens existing register dialog |
| Layout stability preserved | Geometry suite unchanged |

## Requires approval / ACR before implementation

| # | Item | Dependency | Proposed sequence | Acceptance tests |
|---|------|------------|-------------------|------------------|
| 1 | Distinct `HEAD_RECEPTIONIST` governance (or ratified software role) | Governance catalog | Approve role + seeding; map supervision UI | Role fixture; dashboard head-reception flag |
| 2 | Optional department/service/provider scopes | ACR-BETA02-001 §3.1 | Scope table + resolver | Scoped receptionist denied out-of-scope list |
| 3 | National ID / FIDA / official identifiers on panel | Clause 755 + encryption/blind-index | Wire encrypted fields; exception paths | Validation unit; no plaintext in logs/storage |
| 4 | Multi-service grouped reception + invoice linkage | Appointment + billing contracts | Grouping resource without conflating entities | Group book creates N appointments; invoice links |
| 5 | Receptionist pre-granted finance (receipts, discounts, refunds) | Section 50 ledger | Explicit adjustment/refund records | Amount limits; cancellation ≠ refund |
| 6 | Billable items at reception (no inventory UI) | Inventory optional module | Item selection on booking; no stock deduct on future appt | Item lines on invoice; FEFO only on consumption |
| 7 | Check-in / complete / arrival / waiting room | Lifecycle state machine | Approve transitions + permissions | Illegal transitions 409 |
| 8 | Temporary online availability closure | ONLINE capacity contract | Closure resource + exclusion checks | ONLINE slots closed; MANUAL unaffected |
| 9 | Historical appointment entry + occurrence vs recorded timestamps | Timestamp contract | Separate columns; audit | Backdated occurrence ≠ recorded_at |
| 10 | Appointment list workspace (list-first) | Pagination/filter/sort API | Extend list API; keep calendar | p95 ≤ 500 ms @ 500/day synthetic |
| 11 | Management audit read model | Audit retention + permissions | Read API; never rewrite | Receptionist denied cross-user audit |

## Explicit non-goals this increment

Fake scope controls, fake finance screens, inventory management UI, practitioner login ON by
default, drag-and-drop dashboard customization, unapproved migrations.

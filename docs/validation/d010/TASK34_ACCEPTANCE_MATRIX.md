# Task 34 / Task 28 — 120 individually numbered acceptance rows

**Rule:** each row is one scenario. Status is `PASS` only with current tip evidence, else `PENDING`/`BLOCKED`.  
**Tip under test:** re-evaluate after each push on `cursor/d010-ops-contracts-validation-95a4`.  
**Evidence roots:** deep suite JSON, demo manifest, Playwright artifacts, API routes + RTL screens listed in Source.

## Dashboard (1–15)

| # | Scenario | Source | Status |
|--:|----------|--------|--------|
| 1 | Role-aware dashboard composition (ops vs management) | `DashboardView` + `resolveDashboardAudience` | PASS |
| 2 | Today appointment totals from server range | `GET /api/v1/dashboard/summary` | PASS |
| 3 | Tomorrow appointment totals equal-length next span | overview tomorrow block | PASS |
| 4 | Actual arrivals count (CHECKED_IN) | summary by_status / waiting_room | PASS |
| 5 | Completions visible in by_status | dashboard status chips | PASS |
| 6 | Cancellations visible in by_status | dashboard status chips | PASS |
| 7 | No-shows visible in by_status | dashboard status chips | PASS |
| 8 | Physical waiting-room metric when ops schema present | `waiting_room.checked_in_count` | PASS |
| 9 | Future waitlist open count with WAITLIST_VIEW | `future_waitlist.open_count` | PASS |
| 10 | Finance summary null without FINANCE_SUMMARY | overview finance section null | PASS |
| 11 | Finance summary populated with FINANCE_SUMMARY | overview + FinanceView | PASS |
| 12 | Metric cards link to actionable list/calendar/finance/waitlist | `metric-cards.ts` hrefs | PASS |
| 13 | Unauthorized sections omitted (permission-stable cards) | metric card builders | PASS |
| 14 | Global search patients/staff/services scoped by permission | `GET /api/v1/search` | PASS |
| 15 | RTL / Jalali day bounds for summary window | `tehranDayBoundsUtc` | PASS |

## Appointment management (16–40)

| # | Scenario | Source | Status |
|--:|----------|--------|--------|
| 16 | List-first management page | `/appointments` list view | PASS |
| 17 | Server-side status filter | management query params | PASS |
| 18 | Server-side date filter | management query params | PASS |
| 19 | Server-side pagination limit/offset | management API | PASS |
| 20 | Day calendar | DayTimeline | PASS |
| 21 | Week calendar | WeekView | PASS |
| 22 | Month calendar | MonthView | PASS |
| 23 | Appointment details drawer | AppointmentDetailsDialog | PASS |
| 24 | Manual overlap acknowledgement | OverlapDialog + ALLOW_MANUAL_OVERBOOKING | PASS |
| 25 | Practitioner/service eligibility links readable | `GET /api/v1/ops/eligibility` | PASS |
| 26 | Eligibility upsert | `POST /api/v1/ops/eligibility` | PASS |
| 27 | Online temporary closure create | `POST /api/v1/ops/online-closures` | PASS |
| 28 | Check-in lifecycle | `POST .../check-in` | PASS |
| 29 | Check-in writes arrival facts when ops schema present | `SqlArrivalOps` | PASS |
| 30 | Complete lifecycle | `POST .../complete` | PASS |
| 31 | No-show lifecycle | `POST .../no-show` | PASS |
| 32 | Cancel lifecycle | cancel panel | PASS |
| 33 | Reschedule with overlap rules | reschedule panel | PASS |
| 34 | Physical waiting list via CHECKED_IN filter link | desk waiting-room link | PASS |
| 35 | Future waitlist list OPEN entries | WaitlistView | PASS |
| 36 | Waitlist create | `POST /api/v1/waitlist/entries` | PASS |
| 37 | Waitlist status update CONTACTED | PATCH waitlist entry | PASS |
| 38 | Historical late entry with reason | `POST .../historical-entry` | PASS |
| 39 | Historical entry records actual created_at_utc | GET historical-entry | PASS |
| 40 | Invoice navigation from finance to patient dossier | FinanceView patient link | PASS |

## Patient management (41–60)

| # | Scenario | Source | Status |
|--:|----------|--------|--------|
| 41 | Secure patient registration | patients register API/UI | PASS |
| 42 | Patient edit | PatientEditForm | PASS |
| 43 | Patient lookup by directory search | PatientsView | PASS |
| 44 | Shared family phone support | demo builders + lookup | PASS |
| 45 | Official identity exceptions | register identity exception | PASS |
| 46 | Identity completion path | patient profile fields | PASS |
| 47 | Masked identity fields | masked_identifier UI | PASS |
| 48 | Masked phone fields | masked_phone UI | PASS |
| 49 | Operational dossier page | PatientProfileView | PASS |
| 50 | Appointment history on dossier | PatientHistory | PASS |
| 51 | Financial history on dossier | PatientDossierOps invoices | PASS |
| 52 | Outstanding balances | `GET /finance/patients/{id}/balance` | PASS |
| 53 | Patient credit projection | balance.patient_credit_irr | PASS |
| 54 | Operational notes create/list | notes API + UI | PASS |
| 55 | Note pin/unpin/retract actions | note actions API | PASS |
| 56 | Tags/alerts assign | tags API + UI | PASS |
| 57 | Tag remove with reason | DELETE tags | PASS |
| 58 | Scope-aware patient access (permission gate) | AccessDenied without VIEW_PROFILE | PASS |
| 59 | Canonical patient merge disabled | package 12 skipped / BLOCKED | BLOCKED |
| 60 | Activate/deactivate patient | toggle active | PASS |

## Reception desk (61–90)

| # | Scenario | Source | Status |
|--:|----------|--------|--------|
| 61 | Atomic multi-service group booking | `/appointments/group` | PASS |
| 62 | Eligible practitioner/resource selection | BookingForm resources | PASS |
| 63 | Independent service dates per line | draft lines localStart | PASS |
| 64 | Independent durations per line | draft durationMinutes | PASS |
| 65 | Independent prices per line | draft priceIrr | PASS |
| 66 | Walk-in now helper | setWalkInNow | PASS |
| 67 | Immediate check-in / arrival handling | immediate_check_in + check-in | PASS |
| 68 | Live draft invoice lines on desk | CashierPanel lines | PASS |
| 69 | Combined multi-line desk checkout invoice | `POST /finance/desk-checkout` | PASS |
| 70 | Line-level fixed discount on checkout | desk-checkout discount_amount | PASS |
| 71 | Invoice-level discount API | `POST /finance/discounts` INVOICE | PASS |
| 72 | Line-level discount API | `POST /finance/discounts` LINE | PASS |
| 73 | Post draft invoice | desk-checkout post / post endpoint | PASS |
| 74 | Full CASH payment | desk-checkout CASH | PASS |
| 75 | Simulated POS payment with evidence | desk-checkout POS + evidence | PASS |
| 76 | Partial payment leaves PARTIAL status | allocation < payable | PASS |
| 77 | Unpaid posted invoice UNPAID | no receipt | PASS |
| 78 | Paid invoice PAID | full allocation | PASS |
| 79 | Patient credit / outstanding on cashier result | cashier-result outstanding | PASS |
| 80 | Immutable post-payment adjustment API | `POST /finance/adjustments` | PASS |
| 81 | Adjustment rejected on DRAFT | adjustment guard | PASS |
| 82 | Partial refund linked to original receipt/allocation | refunds API + seed | PASS |
| 83 | Full refund after reverse allocation | deep suite + seed mode 7 | PASS |
| 84 | Concurrent refund exactly one success | deep concurrency cases | PASS |
| 85 | Optional billable items list | `GET /ops/billable-items` | PASS |
| 86 | Inventory on-hand derived from movements | inventory items API | PASS |
| 87 | FEFO lot listing with expiry | inventory lots API | PASS |
| 88 | Actual inventory write-off | `POST /ops/inventory/write-off` | PASS |
| 89 | Inventory return with disposition | `POST /ops/inventory/return` | PASS |
| 90 | Quarantine lot blocks consume (deep) + UI quarantine | quarantine API + deep | PASS |

## Supporting management (91–105)

| # | Scenario | Source | Status |
|--:|----------|--------|--------|
| 91 | Departments list/create | ops departments | PASS |
| 92 | Department–service links seeded | persist_ops | PASS |
| 93 | Practitioner resources mapped | staff_practitioner_resources | PASS |
| 94 | Staff–service eligibility manage UI/API | OpsConfigView eligibility | PASS |
| 95 | General receptionist permissions bundle | beta02 RECEPTIONIST_EXTRA | PASS |
| 96 | Explicit HEAD_RECEPTIONIST permission code | permissions catalog | PASS |
| 97 | Financial permissions on receptionist | finance_* grants | PASS |
| 98 | Cashier shift seeded/open | persist_ops cashier_shifts | PASS |
| 99 | Inventory adjust permission gated | INVENTORY_ADJUST | PASS |
| 100 | Management audit list safe metadata | AuditView | PASS |
| 101 | Audit mutations denied | append-only | PASS |
| 102 | Online closure management permission | ONLINE_CLOSURE_MANAGE | PASS |
| 103 | Ops config workspace nav gated | NAV_ITEMS /ops | PASS |
| 104 | Windows one-command preview launcher | `scripts/start_preview.ps1` | PASS |
| 105 | Auto-open browser unless -NoBrowser | start_preview_stack | PASS |

## Validation / evidence / boundaries (106–120)

| # | Scenario | Source | Status |
|--:|----------|--------|--------|
| 106 | Deep PG15 suite ≥38 PASS / 0 FAIL | deep_execution_evidence.json (38/0/2) tip f113b8c | PASS |
| 107 | Concurrent refund competing rejected | deep suite | PASS |
| 108 | Paired write-off + consumption evidence | inventory_paired_write_off_return | PASS |
| 109 | Minimal disposable ops seed smoke | invoices/waitlist/arrivals | PASS |
| 110 | Demo profile targets defined (520/10500/2000/100/100) | profiles.DEMO | PASS |
| 111 | Full demo PG15 seed executed this tip | demo_seed_validation.json 520/10500/2000/100/100 | PASS |
| 112 | Python unit tests green this tip | pytest unit 122 passed / 1 skipped | PASS |
| 113 | App integration/RLS suite this tip | deep suite RLS + live API smoke on preview stack | PASS |
| 114 | Frontend production build this tip | next build (Next.js 16.4.6) | PASS |
| 115 | Fresh-stack Playwright against demo | 55 passed Playwright Chromium on demo stack | PASS |
| 116 | Multi-width screenshot inspection | capture-multi-width + task34-screens | PASS |
| 117 | API/browser benchmarks disposable-only | measure-perf.ts against preview stack | PASS |
| 118 | Tehran midnight rollover case | test_tehran_day_bounds_are_half_open_utc | PASS |
| 119 | Live providers / merge / KMS / SRC-10 remain blocked | EXTERNAL_SOURCE_REQUIRED | BLOCKED |
| 120 | No official Alembic tp0008+ landed; TP0001–7 intact | migrations versions + apply.py | PASS |

## Count summary (must stay exact)

- PASS: count rows marked PASS above after each tip update  
- PENDING: executable but not yet re-run on this tip  
- BLOCKED: external / unapproved sources  

Do not mark PASS from table existence alone; each PASS row names a runnable source.

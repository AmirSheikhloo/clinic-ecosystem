# CLINIC PRODUCT — RECEPTION & DASHBOARD REQUIREMENTS D0.3

**Status:** Product requirements record (authorized by Product Owner).  
**Authority:** Complements, does not replace, `docs/FINAL_MASTER_SPECIFICATION_v3.0.1_FINAL.txt`.  
**Baseline branch:** `development/clinic-operations` @ `599f5e9336b6f156947d569bedb334c7cb2af264` (layout-shift fix preserved).

> Note: This file was reconstructed from the Product Owner’s authorized dashboard-first
> implementation brief when a separate attachment was not available in the agent environment.
> Treat it as the D0.3 product requirements record for this increment.

## 1. Mission

Dashboard-first increment. Product Owner reviews receptionist experience first, then head
receptionist, manager and owner. Implement shared backend foundations and management
capabilities in parallel where approved contracts permit. Do not redesign all existing tabs.

## 2. Role-aware architecture

Maintain separate concepts: person identity, staff profile, job title, professional skill,
login account, governance responsibility, software role, permission, data/resource scope.

Accepted direction:

- Clinic Owner — management dashboard.
- Clinic Manager — management dashboard.
- Delegated Administrator — only explicitly assigned permissions.
- Head Receptionist / Internal Manager — shared operational dashboard + authorized supervision.
- General Receptionist — all clinic appointment operations by default, subject to permissions.
- Optional scoped Receptionist — only when scopes are server-enforced (no fake controls).
- Optional practitioner login — OFF by default.

No specialized finance or inventory staff dashboards in this increment.

## 3. Receptionist dashboard (command center)

Not a BI report. Include:

- Current Jalali date and relevant Tehran time.
- Clear operational greeting and context.
- Real appointment counts (today, tomorrow, supported status summaries).
- Today’s schedule and actionable upcoming appointments.
- Quick registration and booking actions.
- Operational alerts backed by actual data only.
- Distinct empty, loading, refreshing and failure states.

Remove irrelevant administrative metrics from the default receptionist dashboard
(e.g. total system staff, strategic statistics) unless a specific operational permission
and use case justify them.

Distinguish: scheduled appointment, elapsed appointment time, actual completed service,
patient arrival, physical waiting room, future-slot waitlist. Never infer completion from
elapsed scheduled time. Do not present unsupported appointment states as implemented.
Remain useful when modules are disabled.

## 4. Actionable cards and deep links

Reusable metric/action contract. Clicking supported cards navigates with filters applied:

- Today’s appointments → today’s results.
- Tomorrow’s appointments → tomorrow’s results.
- Cancelled → cancelled status filter.
- Upcoming → appointment details when authorized.
- Patient registration / search / new booking → supported workflows.

No inert links, misleading counts or fake destinations. Do not redesign destination workspaces.

## 5. Manager and head receptionist dashboard

Shared components and read models. Management composition for owner/manager:

- Operational overview, appointment volume, status breakdowns.
- Service/provider indicators only where reliable data exists.
- Authorized management shortcuts and issues requiring attention.

Head receptionist: supervision only within authorized scope. Finance/inventory/advanced
analytics widgets only when modules and data exist. No fabricated metrics. Defer
drag-and-drop dashboard customization.

## 6. Shared appointment foundations

Prepare (implement where contracts allow): accurate aggregates, bounded queries,
server-side pagination/filters/sort, stable query semantics, dense schedules.
Future Appointment Management is list-first with secondary calendar — do not redesign yet.
Preserve ONLINE/MANUAL separation; MANUAL has no online-slot quota; overlap acknowledgement
and audit rules apply. Never bypass ONLINE exclusion.

Accepted direction to prepare: temporary online availability closure, walk-in, historical
entry, separate occurrence/recording timestamps, validated status transitions — only under
approved contracts; otherwise ACR.

## 7. Patient identification groundwork

National-ID-centered normal registration with explicit exception paths:

- Iranian National ID: 10 ASCII digits, leading zeros preserved.
- Foreign FIDA: documented 12-digit format; do not assume all foreign IDs share it.
- Other official identifiers type/issuer-specific; passport is not universal-format.
- Shared family mobiles permitted; never unique person identity.
- Independent internal person and dossier identifiers.

Exceptions: foreign nationals, missing documents, urgent admission, historical registration.
Do not fabricate IDs. Preserve clause 755 optional official identifiers. Normal form may
prioritize National ID and guide to alternatives; do not deny profile creation solely for
absent identifier. Strict enforcement conflicting with frozen architecture → narrow ACR.
Preserve encrypted storage, blind indexes, uniqueness, tenant isolation. No plaintext
sensitive identifiers in logs, persistence or browser storage. Do not redesign Patient workspace.

## 8. Multi-service reception and provider foundations

One patient, multiple services in one reception operation; each service has own identity,
eligible provider, resources, date/time, duration, appointment identity, price snapshot.
Common date/time may copy then edit per service. Practitioner may provide multiple services
with one shared resource/time identity. Filter providers by approved eligibility.
Prepare grouped reception + independently manageable appointments and combined invoice
linkage without conflating appointment, completion, invoice and receipt. No unapproved
batch transaction migration. Do not redesign Reception Desk yet.

## 9. Financial foundations (Section 50)

Pre-granted financial authority for authorized receptionists without routine manager
interruptions. Prepare/implement when contracts allow: receipts, invoice-wide and line
discounts (fixed/%), post-payment adjustments, partial/full refunds, authorized cancellation,
auditable corrections. Preserve original posted documents; use adjustments/refunds not
destructive edits. Financial status from ledger facts; cancellation ≠ refund. Validate
limits, prior refunds, currency, operator, reason, authorization. Document deterministic
whole-invoice discount allocation. No fake finance screens.

## 10. Items and inventory foundations

Billable items during multi-service reception; distinguish billable items, stock-tracked
products, non-stock charges, consumables, BOM. Inventory optional. Future appointment does
not deduct stock; consumption/delivery/sale follow approved rules. FEFO, immutable movements,
shortage and returns. No pharmacy. No new inventory UI in this increment.

## 11. Audit and supervision

Actor attribution for business mutations. Safe audit facts only. Receptionists do not get
cross-user audit review by default. Managers may correct business facts via authorized
actions but never rewrite audit history. No sensitive identifiers/credentials in logs.

## 12. Contract-sensitive policy

Classify each workstream: implementable under approved contracts; needs clarification;
needs ACR/migration; blocked on upstream evidence. Implement unblocked work. Produce one
consolidated ACR candidate for blocked items. No unapproved migrations. Do not stop the
entire increment because one stream is blocked.

## 13. UI/UX and engineering

Persian RTL, English ASCII digits, Jalali, Tehran/UTC, four themes × light/dark, tokens,
fonts/icons, accessible controls, restrained motion, stable shell, responsive, keyboard.
Do not regress layout-shift fix. Clean Architecture; cohesive modules; no speculative APIs.

## 14. Human usability targets (product acceptance)

Automated tests do not alone verify these; report limitations:

- Patient lookup under 5 seconds.
- Routine registration under 30 seconds.
- Existing-patient single appointment booking under 20 seconds.

## 15. Performance targets (reference environment)

- Warm click-to-usable: under 1 second.
- List/filter API p95: at most 500 ms.
- Shared shell geometry: ~1 CSS px maximum unintended settled deviation.

Load scenarios: 0, 1, 200, 500 appointments/day; 100,000 historical; concurrent receptionists
where reproducible.

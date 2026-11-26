# BETA-02 operations increment — evidence and handoff

Branch: `development/clinic-operations` (non-production, synthetic data only).
No deployment, production activation, gate closure or merge was performed or claimed.
No migration was added (lineage `tp0001`-`tp0007`). Proposed contracts: `docs/architecture_change_records/ACR-BETA02-001.md`.

## Modules and workflows (backend + BFF + UI)

| Workstream | Status | Screens / workflows |
|------------|--------|---------------------|
| A Patient registry | Complete within approved scope | Register, paged directory search, status filter, profile edit (If-Match), activate/deactivate, appointment history, links to calendar and desk |
| B Staff and providers | Complete within approved scope | Directory, create/edit, kinds, optional council code, activate/deactivate, opt-in login provisioning (OFF by default) |
| C Users, roles, permissions | Complete except granular scopes | Account directory, role CRUD, permission picker, explicit assignment, effective-permission inspection, account suspend, governance (owner/manager/deputy) with anti-escalation |
| D Appointments | Complete within approved lifecycle | Day/week/month Jalali calendar, filters, details, reschedule and cancel with expected-version and idempotency, overlap acknowledgement, multi-resource booking from the desk |
| E Services and resources | Complete within approved schema | Manager-only create/edit, duration, tariff, requirements, activate/deactivate |
| F Dashboard and UX | Complete | Real summary counts (hidden when unavailable), global search over authorized data (`/`, Ctrl/Cmd+K), permission-aware sidebar, shared dialog/toast/table/pagination, four themes x light/dark |

Blocked or partial (see the ACR): granular department/service/provider scopes, patient notes/tags/alerts,
phones and official identifiers, staff-service/resource links, check-in/complete/no-show, forced password change,
resource version column, online-pool cancellation (returns 409 by design).

`useReceptionDesk.ts` was split from 487 to 67 lines (feedback, booking state, catalog, patients, submit, API hooks).
No new frontend or backend source file exceeds 300 lines.

## Dashboard-first D0.3 (this increment)

* Fresh-stack Playwright (`run_browser_e2e`): **51 passed**, 0 failed, 0 skipped (includes dashboard-roles + layout geometry).
* Frontend unit: **58 passed**. `tsc` / `eslint` / `next build`: clean.
* Summary API integration asserts `tomorrow_appointments` under appointments-list permission.

## Dashboard-first D0.3 details

* Product requirements: `docs/product/CLINIC_PRODUCT_RECEPTION_REQUIREMENTS_D0.3.md`
* Contract proposals: `docs/architecture_change_records/ACR-D0.3-DASHBOARD-FOUNDATIONS.md` (not approved)
* Operational vs management dashboard compositions; receptionist metrics exclude staff/catalog admin cards
* Summary API: `tomorrow_appointments` under the same appointments-list permission
* Deep links: today / tomorrow / cancelled / confirmed / patient `?register=1`
* Head receptionist approximated via RECEPTIONIST + supervision permissions (no new governance code)

## Layout stability and preferences (this increment)

* Persistent `(app)` shell: sidebar, top bar, search and account keep the same rectangles across navigation (Playwright geometry suite, real scrollbars).
* Preferences workspace (`/preferences`): browser-local theme, appearance, density, sidebar and motion only — never clinic-wide or permission-linked.
* Day calendar: proportional hour grid, overlap lanes, hour range expands for out-of-hours visits, dense days scroll inside their own frame.
* Shared SearchField / SegmentedControl; directory tables use fixed column widths + `keepPrevious` busy dimming.
* Tools: `e2e/tools/measure-layout.ts`, `measure-perf.ts`, `capture-screens.ts`, `dense-shots.ts`.
* Known backend dependency: patient directory has no server-side sort parameter (UI sorting not offered).

## Security properties exercised

* Server-side RBAC on every route; UI gating is advisory. Receptionist and deputy are denied direct API calls (403) in E2E.
* BFF `/api/v1/*` proxy: allowlisted roots only, auth routes not proxied (404), CSRF + Origin on mutations, bearer only from the HttpOnly cookie,
  only `If-Match` and `Idempotency-Key` forwarded, query and body size limits, 401 clears cookies.
* Browser storage holds only the theme preference (checked by E2E); no tokens or patient data.
* Tenant isolation / RLS / role membership tests in the existing suite still pass.

## Validation evidence (this session, final tree)

| Check | Command | Result |
|-------|---------|--------|
| Backend unit + PG15 integration (RLS, RBAC escalation, cross-tenant, idempotency, concurrency, overlap, migrations) | `python3 -m pytest tests/unit tests/integration -q` | 174 passed, 0 failed, 0 skipped |
| Frontend unit | `npm test` in `beta-panel` | 58 passed, 0 failed, 0 skipped |
| TypeScript | `npx tsc --noEmit` | clean |
| ESLint | `npx eslint .` | clean |
| Next build | `npx next build` | succeeded |
| Playwright E2E on real panel + BFF + API + PG15 | `PYTHONPATH=src:. python3 -m tests.e2e.beta01b.run_browser_e2e` | 21 passed, 0 failed, 0 skipped |

E2E covers: staff, roles, governance, catalog admin, patient registry, calendar views/reschedule/cancel/overlap,
dashboard and global search, authorization denials, BFF proxy limits, 4 themes x light/dark with labelled controls and
Latin digits, 390/768 px overflow, dialog focus trap and Escape, tab arrow keys, reduced motion, storage hygiene.

Defects found by this validation and fixed: unlabeled patient and search inputs; the 16 rem sidebar consumed the
content area at phone width (shell now stacks below `md`); implicit grid tracks overflowed on narrow screens.

Package 1 preflight is distinct from Package 4 Lease/Erasure tests; the latter were not run and are not claimed.

## Not performed

No independent security review was done by this session. An independent Gemini security review of the BFF proxy,
access-administration service and anti-escalation rules is recommended before any further increment.
No load or performance measurements were taken, so no performance claims are made.

## UX refinement increment — backend contract dependencies (no backend change)

The refinement is frontend-only. These items stay blocked on an approved contract (ACR-BETA02-001 is a
proposal) and have no fake UI: granular department/service/provider scopes; patient notes, tags, alerts,
phones and identifiers; staff-to-service links; check-in, complete and no-show transitions; forced
password change; resource version column; cancelling online-pool appointments (server answers 409).
Existing unresolved security-review items remain open and are not represented as resolved.


## Task 26 / D0.4 reception operations (this increment)

Product record: `docs/product/CLINIC_PRODUCT_RECEPTION_REQUIREMENTS_D0.4.md` (full requirements preserved).

### Capability classification (not production approval)

| Capability | Status |
|------------|--------|
| Role-aware dashboards + deep links (D0.3) | IMPLEMENTED / TESTED |
| Appointment list-first management | IMPLEMENTED / TESTED |
| Lifecycle check-in / complete / no-show | IMPLEMENTED / TESTED (unit + E2E lifecycle) |
| Server-side upcoming appointments query | IMPLEMENTED |
| National ID normalize + checksum + UI/API validation | IMPLEMENTED / TESTED (unit); encrypted storage PARTIAL / BLOCKED (no KMS) |
| Clause 755 exceptional registration reason | IMPLEMENTED (audit detail; no fabricated IDs) |
| Multi-service reception + invoice preview (tariff) | IMPLEMENTED (sequential group submit; honest partial success) |
| Walk-in “now” time shortcut | IMPLEMENTED |
| Section 50 billing / discounts / refunds / ledger | BLOCKED (no approved DDL / migrations beyond tp0007) |
| Inventory / stock movements | BLOCKED |
| Encrypted phone + shared-family phone search | BLOCKED (crypto + schema wiring) |
| Scoped receptionist server enforcement | BLOCKED (ACR scope table) |
| Staff↔service eligibility links | BLOCKED (no link table) |
| Historical late-entry workflow (separate recording timestamps) | BLOCKED / PARTIAL (manual past schedule possible; dedicated audited late-entry reason not yet) |
| Management audit review workspace | PARTIAL (append-only audit exists; dedicated filtered UI not complete) |
| Windows Docker readiness + untracked PREVIEW_URL | IMPLEMENTED |

### Migrations

Lineage unchanged: `tp0001`–`tp0007`. No unapproved migrations executed or invented.

### Preview / Windows

* Docker readiness checked before stack start (`scripts/start_preview_stack.py`, `scripts/start_preview.ps1`).
* Runtime URLs/credentials under `P03_HANDOFF/beta_panel_preview/runtime/` (gitignored); legacy `PREVIEW_URL.txt` also gitignored.


## Task 28 / D0.5 (this increment)

Product record: `docs/product/CLINIC_PRODUCT_RECEPTION_REQUIREMENTS_D0.5.md`.
Decision packet (Category C finance/inventory/waitlist/scopes/staff-service): `docs/architecture_change_records/ACR-D0.5-FINANCE-INVENTORY-WAITLIST.md`.

| Capability | Status |
|------------|--------|
| Encrypted National ID + phone persist/lookup (TP0002) | IMPLEMENTED / TESTED (unit crypto); integration pending full suite |
| Atomic group booking API + FE | IMPLEMENTED |
| Waiting-room read model (CHECKED_IN) | IMPLEMENTED |
| Dashboard unique_patients + waiting_checked_in | IMPLEMENTED |
| Windows Docker-before-prepare + auto-browser | IMPLEMENTED |
| Rich demo builders + loader | PARTIAL (generator present; preview stack wiring / full count verification pending) |
| Section 50 finance / inventory / waitlist entity / scopes / staff-service links | BLOCKED (no approved DDL beyond tp0007) |
| Migration lineage | tp0001–tp0007 unchanged |

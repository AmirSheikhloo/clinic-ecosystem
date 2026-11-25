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
| Frontend unit | `npm test` in `beta-panel` | 42 passed, 0 failed, 0 skipped |
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

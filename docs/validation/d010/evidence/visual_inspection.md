# Task 34 R2 — visual inspection

**Tip SHA:** `7ac3d137a8a4f2672a4cd4b1c51235261e8d15fc` (tested tip; evidence on this branch)
**Artifact dir:** `/opt/cursor/artifacts/task34-r2-visuals/`  
**Capture tool:** `beta-panel/e2e/tools/task34-r2-visuals.ts`  
**Preview:** disposable synthetic stack (`CLINIC_DEMO_ALIASES_ENABLED=1`)

Multi-width screenshots (full-page PNG):

| Route | 375 | 768 | 1280 | 1440 |
|---|---|---|---|---|
| dashboard | `/opt/cursor/artifacts/task34-r2-visuals/dashboard-375.png` | `…/dashboard-768.png` | `…/dashboard-1280.png` | `…/dashboard-1440.png` |
| reception desk | `…/reception-desk-375.png` | `…/reception-desk-768.png` | `…/reception-desk-1280.png` | `…/reception-desk-1440.png` |
| appointments calendar | `…/appointments-calendar-375.png` | `…/appointments-calendar-768.png` | `…/appointments-calendar-1280.png` | `…/appointments-calendar-1440.png` |

Also present from prior capture helpers (same dir): `desk-*.png`, `appointments-month-*.png`.

## Observations

- RTL Persian shell (`dir=rtl`, `lang=fa`); Latin/ASCII digits in metric and schedule tables.
- Dashboard: three quick actions, four operational metric cards, server-paginated today schedule with page size control (25 default) and per-row finance action.
- Reception desk: three-stage rail (identify → book → review) with sticky live cashier/cart column on desktop; stacks on 375px.
- Appointments: calendar/list chrome reachable at all widths; month/list variants captured.

## Limitations

- Screenshots are synthetic preview only — not a Windows PO hardware session.
- Theme matrix a11y via top-bar `theme-menu-button` is obsolete; use `/preferences` (see evidence JSON).

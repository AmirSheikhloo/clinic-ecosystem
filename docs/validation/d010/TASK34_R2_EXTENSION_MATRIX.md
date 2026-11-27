# Task 34 R2 — Extension acceptance matrix (Appendix A)

Separate from the original 120 Task 28 rows. Status reflects tip evidence only.

**Tested tip:** pending commit after R2 increment. Environment: Linux agent (Windows hardware NOT RUN).

| Decision ID | Scenario | Test / evidence | Status | Limitation |
|---|---|---|---|---|
| UX-01 | Persian labels + ASCII digits + Jalali Tehran display | Panel RTL shell + `tehran.ts` | IMPLEMENTED | Full seed Persian richness needs demo re-run |
| UX-02 | Four themes light/dark + shared tokens | Existing `config/theme.ts` | PASS (prior) | Visual re-inspect pending |
| UX-03 | Eight demo aliases + Clinic123! one-click login | `demo_aliases.py`, login role selector, preview seed | IMPLEMENTED | Requires preview stack with CLINIC_DEMO_ALIASES_ENABLED |
| UX-04 | Top bar without search/theme/logout; sidebar red logout | TopBar/Sidebar rewrite | IMPLEMENTED | E2E selectors may need update |
| UX-05 | Hierarchical breadcrumbs + live clock | Breadcrumbs + LiveTehranClock | IMPLEMENTED | |
| UX-06 | Auto refresh 20s + focus | DashboardView poll | IMPLEMENTED | Mutation invalidation incomplete for all views |
| DASH-01 | 3 quick actions only | `quick-actions.ts` | IMPLEMENTED | |
| DASH-02 | 4 metric cards blue/purple/amber/rose | `metric-cards.ts` | IMPLEMENTED | Server needs_status_count optional |
| DASH-03 | Needs-status badge ≤2 pulses | StatusNeedsAttentionBadge | IMPLEMENTED | |
| DASH-04 | Six RTL schedule columns | TodaySchedule | IMPLEMENTED | Enrichment fields optional until API expands |
| DASH-05 | Debounced filters + pagination | Partial (appointments mgmt prior) | PARTIAL | Dashboard search panel not complete |
| DASH-06 | Filled secondary appointments button | TodaySchedule link | IMPLEMENTED | |
| APPT-01 | One ordinary completion action | Prior lifecycle + details drawer | PARTIAL | Bulk completion pending |
| APPT-02 | Jalali calendar day/week/month | Prior AppointmentsView | PASS (prior) | Period aggregates incomplete |
| APPT-03 | Independent rows + group view | PARTIAL | Group expansion pending |
| PAT-01 | Exact ID + inline register + exceptions | Prior PatientQuickRegister | PARTIAL | Clause 755 ACR reconciliation pending |
| PAT-02 | DB insurance catalog | Proposed disposable SQL | PROPOSED | Seed/catalog UI pending full wire |
| PAT-03 | Directory/dossier invoices expandable | Prior PatientDossierOps | PARTIAL | |
| DESK-01 | Three-step reception 65/35 | PARTIAL | Layout redesign in progress |
| DESK-02 | Interdependent comboboxes | PARTIAL | APG combobox component pending |
| DESK-03 | Distinct appointment drafts | Prior draft lines | PARTIAL | |
| DESK-04 | Manual overlap + historical | Prior OverlapDialog | PASS (prior deep) | |
| FIN-01–05 | Server pricing, discounts, refunds, drawer | Prior finance + a3401b8 tip | PARTIAL | Left finance drawer pending |
| MULTI-01/02 | Multi-patient cart; shared settlement OFF | Feature-flagged OFF | BLOCKED (ratification) | ACR amendment drafted |
| PRINT-01/02 | 80mm thermal + simulated adapter | Print module + templates | IMPLEMENTED (synthetic) | Hardware/QZ silent print NOT RUN |
| COURSE-01/02 | Pay-per-session courses | Disposable schema + API stub | PROPOSED/IMPLEMENTED stub | Ratification required |
| RECALL-01–03 | Rolling recall + synthetic sink | Proposed worker contract | PROPOSED | Synthetic only |
| PREPAY-01/02 | Prepaid packages | Design-only; disabled | BLOCKED (policy) | |
| SEC-01/02 | Fail-closed scopes + audit projection | a3401b8 + this tip | PASS (unit/deep) | Adversarial multi-user API incomplete |
| OPS-01 | Manager config + inventory | Prior OpsConfigView | PARTIAL | |
| WIN-01 | tzdata + start_preview.ps1 | a3401b8 | PASS (unit) | Actual Windows PO run NOT RUN this tip |
| DATA-01 | Rich Persian demo | Prior demo seed | PASS (prior counts) | Waiting-room reconciliation audit pending |
| QA-01 | Matrices + CI | This doc + Task28 matrix | PARTIAL | CI URL after push |
| GOV-01 | ACR revision for multi-patient/courses | `docs/architecture/...R2_AMENDMENT` | PROPOSED | Owner/independent review required |

## Counts (extension)

- IMPLEMENTED / PASS (this tip or preserved): see Status column
- PROPOSED / BLOCKED / PARTIAL / NOT RUN: remaining work listed in Section 30 handoff

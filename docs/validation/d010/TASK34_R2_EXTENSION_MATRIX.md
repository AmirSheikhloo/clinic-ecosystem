# Task 34 R2 — Extension acceptance matrix (Appendix A)

Separate from the original 120 Task 28 rows. Status reflects tip evidence only.

**Tested tip:** `3d37f74b23594525c3219609c1894a8c9bd4ada2`  
**Environment:** Linux agent (Windows hardware NOT RUN this tip).  
**Unit evidence:** Python `156 passed / 1 skipped`; frontend checkout/print unit suites green; `tsc --noEmit` green.

| Decision ID | Scenario | Test / evidence | Status | Limitation |
|---|---|---|---|---|
| UX-01 | Persian labels + ASCII digits + Jalali Tehran display | Panel RTL shell + `tehran.ts` | IMPLEMENTED | Full seed Persian richness needs demo re-run |
| UX-02 | Four themes light/dark + shared tokens | Existing `config/theme.ts` | PASS (prior) | Visual re-inspect pending |
| UX-03 | Eight demo aliases + Clinic123! one-click login | `demo_aliases.py` fail-closed disposable marker; login clears session | PASS (unit) | Requires preview stack env |
| UX-04 | Top bar without search/theme/logout; sidebar red logout | TopBar/Sidebar | IMPLEMENTED | |
| UX-05 | Hierarchical breadcrumbs + live clock | Breadcrumbs + LiveTehranClock | IMPLEMENTED | |
| UX-06 | Auto refresh 20s + focus/reconnect | DashboardView poll | IMPLEMENTED | |
| DASH-01 | 3 quick actions only | `quick-actions.ts` | IMPLEMENTED | |
| DASH-02 | 4 exact metric predicates (server) | `operational_metric_counts` + summary fields | IMPLEMENTED | PG15 multi-user adversarial pending |
| DASH-03 | Needs-status badge ≤2 pulses | StatusNeedsAttentionBadge | IMPLEMENTED | |
| DASH-04 | Six RTL schedule columns + finance action | TodaySchedule + finance drawer | IMPLEMENTED | Enrichment still partial |
| DASH-05 | Server search/sort/filters + 25/50/100 | `GET /api/v1/dashboard/day` | IMPLEMENTED | |
| DASH-06 | Filled secondary appointments button | TodaySchedule link | IMPLEMENTED | |
| APPT-01 | Ordinary completion + bulk ops | Details dialog + BulkAppointmentOps | IMPLEMENTED | |
| APPT-02 | Jalali calendar day/week/month | AppointmentsView | PASS (prior) | Period aggregates incomplete |
| APPT-03 | Independent rows + group view | Prior group booking | PARTIAL | |
| PAT-01 | Exact ID + inline register + exceptions | PatientQuickRegister | IMPLEMENTED | Clause 755 ACR reconciliation pending |
| PAT-02 | Insurance catalog Persian UI | `insurance-catalog.ts` + register select | IMPLEMENTED | Disposable DB catalog seed optional |
| PAT-03 | Directory/dossier invoices expandable | Prior PatientDossierOps | PARTIAL | |
| DESK-01 | Three-stage reception ~65/35 sticky cart | DeskView stage rail + layout | IMPLEMENTED | Nested-scroll regression needs Playwright |
| DESK-02 | Searchable accessible comboboxes | SearchableCombobox + BookingForm | IMPLEMENTED | |
| DESK-03 | Distinct appointment drafts + multi-line links | draft lines + BookedSummary.lines | IMPLEMENTED | |
| DESK-04 | Manual overlap + historical | OverlapDialog | PASS (prior deep) | |
| FIN-01 | Server tariffs; no client money authority | desk-checkout | PASS (unit/prior deep) | |
| FIN-02 | Durable UUID checkout intent (no truncation) | `checkout-intent.ts` unit | PASS | |
| FIN-03 | Left finance drawer dashboard+appointments | AppointmentFinanceDrawer | IMPLEMENTED | |
| FIN-04 | Reason catalogs + OTHER explanation | finance-reasons.ts | IMPLEMENTED | |
| FIN-05 | Discount largest-remainder; no type combine; no silent clamp | finance.py + unit | PASS (unit) | |
| MULTI-01 | Multi-patient cart independent invoices | MultiPatientCartPanel; shared OFF | IMPLEMENTED | |
| MULTI-02 | Shared settlement | ACR-D0.12 candidate | BLOCKED (ratification) | Guards preserved |
| PRINT-01 | 80/58mm Persian RTL; independent + batch; privacy; course/next hints | `features/print/*` unit tests | IMPLEMENTED (synthetic) | Physical hardware NOT RUN |
| PRINT-02 | Enrollment/test-print; job identity; failed/unknown/disconnect; reprint≠checkout; QZ blocked | printJobs + workstationPrinter + snapshot API | IMPLEMENTED (synthetic) | Real QZ signing/hardware BLOCKED pending approval |
| COURSE-01 | Versioned templates + sessions + conservation SQL | proposed_treatment_courses.sql + store/service | IMPLEMENTED (disposable) | Prepaid disabled |
| RECALL-01 | Mehr→Aban→Azar rolling from completion | `test_rolling_recall_mehr_aban` + `test_treatment_courses_rolling_recall` | PASS (17 unit) | |
| RECALL-02 | Synthetic reminder worker (dedupe/retry/quiet/opt-out) | `application/treatment_courses/reminder_worker.py` | IMPLEMENTED | No real SMS; PG15 claim NOT RUN (no Docker) |
| RECALL-03 | Qualifying future appointment suppression | service path | IMPLEMENTED (code) | PG15 integration pending |
| PREPAY-01/02 | Prepaid packages | Design-only; disabled | BLOCKED (policy) | |
| SEC-01 | Object-level ALL/FILTER scopes | permissions + scope_access + appointment/finance/patient | PASS (unit) | Live multi-user PG pending |
| SEC-02 | Demo aliases disposable-only | demo_aliases unit | PASS | |
| OPS-01 | Manager config + inventory | Prior OpsConfigView | PARTIAL | |
| WIN-01 | tzdata + start_preview.ps1 | a3401b8 | PASS (unit) | Windows PO NOT RUN |
| DATA-01 | Rich Persian demo | Prior demo seed | PASS (prior) | Waiting-room audit pending |
| QA-01 | Matrices + CI branch triggers | workflows m0/m1 include PR branch | PARTIAL | CI URL after push |
| GOV-01 | Settlement + courses ACR candidates | ACR-D0.12 + TREATMENT_COURSES arch | PROPOSED | Owner review required |

## Counts (extension)

- PASS / IMPLEMENTED: majority of independently solvable UX/security/finance/print/course engineering
- BLOCKED: MULTI-02 shared settlement; PREPAY; real QZ/SMS/CARD_TO_CARD/ONLINE; canonical merge
- Playwright mutations 3/3 PASS this tip; multi-width visuals captured; adversarial scope script+unit present; Windows PO / CI tip conclusion pending

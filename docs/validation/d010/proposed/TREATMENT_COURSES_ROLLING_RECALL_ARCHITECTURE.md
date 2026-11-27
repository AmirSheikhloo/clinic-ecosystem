# Treatment courses + rolling recall — proposed architecture revision (Task 34 R2 §9)

**Status:** PROPOSED / DISPOSABLE / NOT RATIFIED  
**Does not:** land official Alembic `tp0008+`, activate prepaid entitlements, shared multi-patient settlement, or real SMS/bot channels.  
**Applies only when:** `CLINIC_OPS_SCHEMA_MODE=disposable` on synthetic PG15.

## 1. Source grounding

| Source | What it contributes |
|---|---|
| `ACR_D0.11_TASK34_R2_AMENDMENT.md` §2 | Disposable tables: templates, courses, sessions, recall schedules, synthetic notification outbox; PERFORMED-only completion; Tehran rolling; synthetic sink only |
| ACR-D0.11 §7.2 / `08.sql` | `service_records` with `record_kind='PERFORMED'`, composite FKs `(tenant_id, appointment_id, patient_id, service_id)`, unique PERFORMED per appointment |
| ACR-D0.11 §12 / `TP0006` | Outbox envelope: `message_type`, JSON payload (opaque IDs only), lease/attempt pattern; **no parallel production outbox**; disposable synthetic queue mirrors the envelope for reminder delivery only |
| `hold_expiry_worker.py` | Claim → `FOR UPDATE SKIP LOCKED` → bounded attempts → lease expiry pattern reused by synthetic reminder worker |
| `SqlOutboxStore` | Same-UoW staging pattern; course lifecycle may emit safe domain events into `outbox_messages` while reminder jobs live in `notification_outbox_synthetic` |
| Jane return-visit reminders (research matrix) | Suggested date ≠ reminder send date; suppress when qualifying future booking exists; re-evaluate after cancel/no-show |
| Cliniko recalls (research matrix) | Cap cycles; quiet hours — avoid indefinite daily spam |
| Jane packages (research matrix) | Redemption ≠ booking; no-show does **not** consume clinical session by default → maps to PREPAY disabled + no cancellation/no-show session consumption |

Prior disposable stub `d09_extracted/proposed_treatment_courses.sql` lacked sessions, versioned templates, reminder policy snapshots, concurrency, conservation, and a real synthetic worker. This revision replaces that stub.

## 2. Core model

```
service_course_templates (catalog, per service)
  └─ service_course_template_versions (immutable version rows)
       └─ treatment_courses (patient-specific config snapshot + live state)
            ├─ treatment_course_sessions (independent clinical units)
            ├─ treatment_recall_schedules (versioned suggested/reminder plan)
            └─ treatment_reminder_policy_snapshots (frozen lead/quiet/opt policy)
notification_outbox_synthetic  ← reminder delivery jobs (synthetic destinations only)
synthetic_notification_deliveries ← accepted sink rows (no SMS/bot)
patient_notification_preferences ← opt-out / quiet hours / destination identity
```

### 2.1 Versioned templates

- `service_course_templates` is the mutable catalog head (name, active flag, current_version_no).
- Each publish creates an immutable `service_course_template_versions` row: interval kind/value, planned sessions, reminder lead days, quiet-hours window, long-gap days, scheduling mode (`ROLLING` | `FIXED`), billing mode (`PAY_PER_SESSION` | `PREPAID_DISABLED`).
- Patient courses bind to a **specific template version**; later template edits do not rewrite active courses.

### 2.2 Patient-specific course config

`treatment_courses` holds:

- Composite identity `(tenant_id, id)` and consistency keys `(tenant_id, patient_id, service_id)`.
- Snapshot of interval/reminder/planned_sessions from the bound template version (overridable at enroll time within policy bounds).
- Live counters: `completed_session_count`, `voided_session_count`, `aggregate_version` (optimistic concurrency).
- Status: `ACTIVE | PAUSED | REASSESSMENT_REQUIRED | COMPLETED | TERMINATED`.
- `billing_mode` always `PAY_PER_SESSION` for this tip; `PREPAID_DISABLED` is the only prepaid-related value and keeps entitlement paths fail-closed.

### 2.3 Independent course sessions

Each `treatment_course_sessions` row is one clinical unit:

| Field | Rule |
|---|---|
| `session_no` | Dense logical index 1..planned; conservation enforced |
| `status` | `PLANNED | BOOKED | COMPLETED | VOIDED | SUPERSEDED` |
| `appointment_id` | Optional; composite FK to appointment patient+service |
| `service_record_id` | Required for `COMPLETED`; must be PERFORMED |
| `completion_tehran_date` | Tehran local calendar date of actual completion |
| `completion_at_utc` | UTC instant of evidence |
| `idempotency_key` | Per-course unique for completion/correction commands |

**No future-session artificial debt:** enrolling a 10-session course does **not** pre-create 10 incomplete “owed” sessions. Sessions are materialised on book/complete/correction. Planned count is a ceiling, not a ledger of negative debt.

## 3. Consistency & conservation

1. **Patient/service/appointment/service-record:** every linked appointment and PERFORMED `service_record` must share `(tenant_id, patient_id, service_id)` with the course (MATCH FULL composite FKs).
2. **Actual completion evidence:** only `service_records.record_kind = 'PERFORMED'` may drive `COMPLETED` session status and rolling recall. Payment receipts, invoice posts, bookings, and cancellations never complete a session.
3. **NO payment-created completion:** triggers reject session completion without a PERFORMED service_record link.
4. **NO cancellation/no-show session consumption:** `CANCELLED` / `NO_SHOW` appointments never set session `COMPLETED`; they may clear `BOOKED` → reopen recall evaluation.
5. **Session count conservation:**  
   `completed_session_count + remaining_capacity = planned_sessions` where remaining excludes VOIDED/SUPERSEDED.  
   `completed_session_count = COUNT(sessions WHERE status='COMPLETED')`.  
   Corrections VOID or SUPERSEDE prior completion and adjust counters in one UoW.
6. **Idempotent completion/correction:** `(tenant_id, course_id, idempotency_key)` unique; replay returns prior result.
7. **Concurrency:** `aggregate_version` on course + `SELECT … FOR UPDATE` on course row during complete/correct/pause/resume; conflicting writers fail closed (`412` / conflict code).

## 4. Scheduling & Tehran/Jalali rules

### 4.1 Modes

| Mode | Behaviour |
|---|---|
| `ROLLING` | Next suggested Tehran date = f(actual completion Tehran date, interval) |
| `FIXED` | Next suggested date from a fixed schedule template (weekday/day-of-month anchors); still reminder-lead derived; completion does not shift the lattice except for missed-cycle skip policy |

### 4.2 Interval kinds

| Kind | Rule |
|---|---|
| `JALALI_CALENDAR_MONTH` | Add N Jalali months to completion day-of-month; clamp to last day of target month (Esfand leap/non-leap) |
| `FIXED_DAYS` | Add N civil days on the Tehran calendar |

### 4.3 Reminder derivation

`reminder_tehran_date = suggested_tehran_date − reminder_lead_days` (Tehran calendar).  
Exact example (lead=2, interval=1 Jalali month, ROLLING):

| Event | Completion (Tehran) | Next visit | Reminder |
|---|---|---|---|
| Session 1 | 5 Mehr | 5 Aban | 3 Aban |
| Session 2 | 15 Aban | 15 Azar | 13 Azar |

Rolling uses **completion date**, never booking or payment date.

### 4.4 Persistence

- Business calendar fields: `DATE` as Tehran local calendar day.
- Instants (`created_at_utc`, `scheduled_at_utc`, `completion_at_utc`, leases): `TIMESTAMPTZ` UTC.
- Conversion always via `Asia/Tehran` (tzdata required).

### 4.5 Long-gap reassessment

If `now_tehran_date − last_completion_tehran_date > long_gap_days`, course → `REASSESSMENT_REQUIRED` and open recall jobs are invalidated until clinician/reception resumes.

## 5. Recall schedules & reminder policy snapshots

On each successful completion (or resume/re-evaluate):

1. Snapshot reminder policy into `treatment_reminder_policy_snapshots` (lead days, quiet hours start/end Tehran minutes, opt-out check token, max attempts).
2. Insert `treatment_recall_schedules` with `schedule_version` incremented; prior `SCHEDULED` rows for the course become `SUPERSEDED`.
3. Logical key: `course:{id}:v{schedule_version}:remind:{tehran_date}` — unique per tenant (dedup).
4. Qualifying future appointment suppression: if an appointment exists for same patient+service with `status IN ('CONFIRMED','CHECKED_IN')` and Tehran start date in `[today, suggested+grace]`, schedule status → `SUPPRESSED` and synthetic outbox job is not created (or is invalidated).
5. Cancellation/no-show of that qualifying appointment triggers re-evaluation: if course still ACTIVE and no other qualifier, revive/create a new schedule version.

## 6. Lifecycle commands

| Command | Effect |
|---|---|
| `enroll` | Create course from template version; billing PAY_PER_SESSION |
| `pause` / `resume` | Status flip; pause invalidates open reminder jobs |
| `terminate` | Terminal; no further recall |
| `complete_course` | When `completed_session_count >= planned_sessions` |
| `record_session_completion` | Link PERFORMED evidence; roll next recall |
| `correct_session_completion` | VOID/SUPERSEDE prior; recompute counters + recall |
| `reevaluate_recall` | After cancel/no-show/booking changes |

Pay-per-session finance remains ordinary invoice/receipt flow per session visit — course rows never mint prepaid entitlements.

## 7. Synthetic reminder worker (compatible outbox)

### 7.1 Why a disposable synthetic table

ACR-D0.11 forbids inventing a **parallel production** outbox competing with `TP0006.outbox_messages`. Reminder delivery for this tip is **synthetic-only** and must not register live SMS/bot providers. Therefore:

- Domain-safe lifecycle events (`course.session_completed`, `course.recall_suppressed`, …) may stage into existing `outbox_messages` (opaque IDs only).
- Reminder **delivery jobs** use `notification_outbox_synthetic`, which **mirrors** the TP0006 envelope (`message_type`, `payload_json`, `locked_until`, `lease_id`, `attempt_count`, `delivered_at_utc`) plus reminder-specific columns (`logical_key`, `schedule_version`, `earliest_send_at_utc`, `destination_kind`).

### 7.2 Worker guarantees

| Concern | Mechanism |
|---|---|
| Deduplication | Unique `(tenant_id, logical_key)`; sink unique on same key |
| Bounded retries | `attempt_count < max_attempts` (from policy snapshot); then `FAILED` |
| Stale-job invalidation | Job carries `schedule_version`; worker no-ops if course schedule advanced or status not ACTIVE |
| Schedule versioning | Only current version’s jobs are eligible |
| Quiet hours | If Tehran local time in quiet window, defer `earliest_send_at_utc` to window end |
| Opt-out | Prefer `patient_notification_preferences.recalls_opted_out`; mark `SUPPRESSED` |
| Recipient identity changes | Payload stores destination **reference id + generation**; mismatch → invalidate and reschedule |
| Synthetic-only destinations | `destination_kind IN ('SYNTHETIC_SINK','SYNTHETIC_LOG')` only — CHECK constraint; no SMS/Telegram |

Claim pattern matches `HoldExpirationWorker`: `FOR UPDATE SKIP LOCKED`, lease, attempt increment.

## 8. Explicit non-goals (this tip)

- Prepaid package entitlement, forfeiture, shared settlement batches — **DISABLED** pending ratification.
- Real SMS/bot providers / Gate B notification providers.
- Official Alembic landing.
- Creating N future incomplete session rows as artificial debt.

## 9. Disposable SQL & apply path

- SQL: `docs/validation/d010/d09_extracted/proposed_treatment_courses.sql`
- Apply helper: `clinic_ecosystem.infrastructure.ops_schema.apply_treatment_courses_schema` (idempotent; requires disposable mode; does not rewrite TP0001–TP0007).
- Tests: unit calendar/worker tests always; PG15 apply optional when Docker available.

## 10. Acceptance anchors

- EXT-RECALL-01: Mehr→Aban→Azar rolling example (completion-based).
- EXT-RECALL-02: quiet hours + capped attempts.
- EXT-RECALL-03: synthetic sink only.
- COURSE-01/02: pay-per-session enroll + session completion stubs; prepaid fail-closed.

# Task 34 R2 §9 — treatment courses / rolling recall evidence

**Tip:** local commits on `cursor/d010-ops-contracts-validation-95a4` (parent pushes).  
**Mode:** disposable / synthetic only. No official Alembic. No real SMS/bot. Prepaid OFF.

## Deliverables

| Artifact | Path |
|---|---|
| Architecture revision | `docs/validation/d010/proposed/TREATMENT_COURSES_ROLLING_RECALL_ARCHITECTURE.md` |
| Disposable PG15 SQL | `docs/validation/d010/d09_extracted/proposed_treatment_courses.sql` |
| Apply helper | `clinic_ecosystem.infrastructure.ops_schema.apply_treatment_courses_schema` |
| Domain calendar/rolling | `src/clinic_ecosystem/domain/treatment_courses/` |
| App service | `src/clinic_ecosystem/application/treatment_courses/service.py` |
| Synthetic worker | `src/clinic_ecosystem/application/treatment_courses/reminder_worker.py` |
| HTTP stubs | `src/clinic_ecosystem/presentation/http/treatment_courses.py` |
| UI hooks | `beta-panel/features/courses/*` (+ patient dossier / ops config) |

## Tests run (this tip)

```
PYTHONPATH=src python3 -m pytest \
  tests/unit/test_treatment_courses_rolling_recall.py \
  tests/unit/test_rolling_recall_mehr_aban.py \
  tests/unit/test_synthetic_reminder_worker_logic.py -q
```

**Result:** 17 passed.

Exact example asserted:

- Session 1 completed **5 Mehr 1405** → next **5 Aban** → reminder **3 Aban**
- Session 2 completed **15 Aban 1405** → next **15 Azar** → reminder **13 Azar**
- Rolling from completion date, not booking/payment

Also covered: Jalali leap/end-of-month clamp, FIXED_DAYS, quiet-hours deferral, SQL marker needles, pay-per-session stub flags.

## Not run / blockers

- Full disposable PG15 apply + worker claim integration: **Docker unavailable** in this agent environment (`DOCKER_NO`).
- Owner ratification of ACR amendment (courses + multi-patient settlement).
- Prepaid entitlement / shared settlement: remain **DISABLED**.
- Real SMS/bot providers: forbidden.
- Official Alembic `tp0008+`: not landed.

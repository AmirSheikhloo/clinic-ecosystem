# M102 F2-B E0.2 — Final Consolidated Experiment Report

**Classification:** `EXPERIMENT_COMPLETED_WITH_EVIDENCE`  
**Feasibility (bounded):** `EXPERIMENTAL_FEASIBILITY_SUPPORTED` for the synthetic harness only  
**Not:** Package 1 implementation, official TP migration approval, F2-B architecture approval, ACR signature, or Gate A–D acceptance

---

## 1. Authority record

| Field | Value |
|---|---|
| Governing contract | `M102_F2B_REPLACEMENT_BOUNDED_EXPERIMENT_CONTRACT_E0.2_PROPOSED.md` |
| Contract SHA-256 | `03c471825a0ec404eb0ce173789a9d0dd87e3c42a656ed6cad459f277909ec31` (**matched**) |
| PO approval | Exact Persian statement in handoff approving that filename+digest for Cursor-only bounded experiment |
| E0.1 | **Not used** (unavailable; E0.2 is approved replacement) |
| Executor | Cursor |
| Hard expiry | earlier of final report delivery or `2026-11-23T22:59:00Z` |
| Report UTC | `2026-11-16T20:42:10Z` (Berlin `2026-11-16T21:42:10+01:00`) — **before expiry** |
| Stop reason after this report | Authorization **terminates on delivery of this report** |

**PO quotation (authorization):**  
> نسخه M102_F2B_REPLACEMENT_BOUNDED_EXPERIMENT_CONTRACT_E0.2_PROPOSED.md با SHA-256 03c471825a0ec404eb0ce173789a9d0dd87e3c42a656ed6cad459f277909ec31 را صرفاً برای آزمایش محدود Cursor و با تمام محدودیت‌های مندرج در آن تأیید می‌کنم.

---

## 2. Source evidence

| Source | Status |
|---|---|
| Frozen spec `docs/FINAL_MASTER_SPECIFICATION_v3.0.1_FINAL.txt` @ main blob `befde437…` | Read; clauses **771–772** applied as experiment analogues only |
| R4.15 §§11.8–11.9 | Read from upload `MASTER_EXECUTION_ROADMAP_v3.0.1_R4.15_8114.md` (SHA-256 `ab232139…`); status **REVIEW CANDIDATE / F2-B PROPOSED NOT APPROVED** |
| Official TP lineage on main | `tp0001`–`tp0007` only; **no** official `tp0008+` created or executed |
| `TP0011` / `TP0023` | **Not reallocated**; synthetic IDs `exp_f2b_*` only |

---

## 3. Repository evidence

| Field | Value |
|---|---|
| Remote | `https://github.com/AmirSheikhloo/clinic-ecosystem` |
| Base | `origin/main` = `fdae362e1a889831975060808ac612369d3b0d0a` |
| Experiment branch | `experiment/m102-f2b-e02-20261116-fdae362` |
| Tested HEAD (green CI) | `e1897078076296c771a7caedb97dc75b2b28db22` |
| Initial tree | Clean before branch creation |
| Changed paths | Only `experiments/m102_f2b_bounded_e02/**` and `.github/workflows/m102-f2b-bounded-e02.yml` |
| Official migrations / `src/` / `tests/` / `ops/` / other workflows | **Unchanged** |

---

## 4. Environment evidence

| Field | Value |
|---|---|
| Local Docker | **ABSENT** on Cursor VM |
| Execution venue | GitHub Actions `ubuntu-24.04` + service `postgres:15` |
| CI run | [43952295235](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/43952295235) **success** |
| Artifact | `m102-f2b-e02-evidence` ID `14266348935` |
| Data | Fabricated tenants/HMAC bytes only |
| Roles | `exp_f2b_migrator`, `exp_f2b_app` (NOSUPERUSER, NOBYPASSRLS) |
| Version table | `public.exp_f2b_alembic_version` (not `alembic_meta.alembic_version_tp`) |
| Draft PR | **NOT USED** (push-only experiment workflow; avoids unrelated M0 jobs on PR-to-main) |
| Disposal | Job-scoped Actions service container (ephemeral) |

---

## 5. §5.1 matrix

| ID | Result | Evidence |
|---|---|---|
| E02-5.1-A Approval integrity | **PASS** | Digest match + PO statement |
| E02-5.1-B Source chain | **PASS** | Spec 771–772; R4.15 F2-B vs F2-L/F2-S as review candidate |
| E02-5.1-C Live repo facts | **PASS** | Clean; main `fdae362`; TP0001–7 inventory |
| E02-5.1-D Safety manifest | **PASS** | `evidence/E02_5_1_SAFETY_MANIFEST.md` |
| E02-5.1-E Run eligibility | **PASS** | Clock OK; CI PG15 isolation substituted for missing local Docker |

---

## 6. §5.2 test matrix (CI @ `e189707`)

| Test ID | Result | Classification |
|---|---|---|
| E02-F2B-01 Synthetic graph audit | **PASS** | `OBSERVED_PASS` — heads `{exp_f2b_h8, exp_f2b_cat2}` |
| E02-F2B-02 Explicit head targeting | **PASS** | `OBSERVED_PASS` |
| E02-F2B-03 Dangerous-target negatives | **PASS** | `OBSERVED_PASS` — `head`/`heads`/unknown refused pre-mutation |
| E02-F2B-04 Version-table state machine | **PASS** | `OBSERVED_PASS` — cardinality 0/1/2 |
| E02-F2B-05 Catalog-only independence | **PASS** | `OBSERVED_PASS` — authority stayed `gen1` |
| E02-F2B-06 HMAC-only independence | **PASS** | `OBSERVED_PASS` — no catalog objects |
| E02-F2B-07 Phase-6 TX boundary | **PASS** | `OBSERVED_PASS` — CONCURRENTLY ok via autocommit; in-TX rejected |
| E02-F2B-08 Concurrent-index failure/retry | **PASS** | `OBSERVED_PASS` |
| E02-F2B-09 Phase-8 guarded cutover | **PASS** | `OBSERVED_PASS` — incomplete backfill refused; validated CHECK cutover |
| E02-F2B-10 Dual-write / active uniqueness | **PASS** | `OBSERVED_PASS` |
| E02-F2B-11 Role/privilege negatives | **PASS** | `OBSERVED_PASS` |
| E02-F2B-12 Cloud/Local mixed-state simulation | **PASS** | `OBSERVED_PASS` — **Sync/app still UNVERIFIED** |
| E02-F2B-13 Interrupted upgrade semantics | **PASS** | `OBSERVED_PASS` — partial `h6` then remediate to `h8` |
| E02-F2B-14 Scope/clock/closure | **PASS** | `OBSERVED_PASS` |

**Counts:** PASS=14, FAIL=0, BLOCKED=0, NOT_RUN=0 (authorized §5.2 suite)  
**CI summary:** `total=14 failed=0 skipped=0`  
**Per-test JSON + digests:** `experiments/m102_f2b_bounded_e02/evidence/E02-F2B-*.json`, `EVIDENCE_SHA256SUMS.txt`

Prior failed runs (retained audit trail): `43951617080` (logging.ini), `43951909176` (4 negatives) — both remediated before green `43952295235`.

---

## 7. Security / deviations / residuals

- No patient data, real keys, persistent DB, or official TP execution.
- No Draft PR (CI scope kept to experiment push workflow only).
- Residual: production Sync/app/worker compatibility **UNVERIFIED**; official `env.py` still transactional; F2-B numbering **not approved**.
- `TP0011` Package-2 historical reservation **not consumed** by this experiment.

---

## 8. Explicit non-authorization statement

No official Package 1 implementation or migration was authorized; no permanent/real database was used; no patient data or real keys were used; no PR was merged; no ACR signed; no Gate A, B, C, or D was accepted.

---

## 9. Final classification

`EXPERIMENT_COMPLETED_WITH_EVIDENCE` / `EXPERIMENTAL_FEASIBILITY_SUPPORTED` (synthetic only) / **F2-B NOT APPROVED** / **Package 1 NOT AUTHORIZED** / **Gate A NOT ACCEPTED**

**Next for Product Owner:** Review this report and decide whether to commission a separate migration ACR / governance review of F2-B; do **not** treat this run as deployable graph approval.

# M1-02 P1 vs P2 HMAC Physical Design Experiment — Corrected Engineering Report (Q0.1)

**Date:** 2026-11-16  
**Repository:** `AmirSheikhloo/clinic-ecosystem`  
**Correction branch:** `cursor/m102-p1-p2-n01-n09-corrections-95a4`  
**PR:** https://github.com/AmirSheikhloo/clinic-ecosystem/pull/3 (DRAFT — do not merge)  
**Base `main`:** `fdae362e1a889831975060808ac612369d3b0d0a` (unchanged)  
**Tested code SHA:** `2f0b1eb16d3d1572fb7226377fc5ae55519a58d2`  
**Classification:** `EXPERIMENTAL CORRECTIONS TESTED / NOT APPROVED / NOT Package-1 / NOT Gate A–D / NO ACR / NO Option C`

Status vocabulary: **PROPOSED**, **IMPLEMENTED**, **TESTED**, **PASS**, **FAIL**, **BLOCKED**, **APPROVED** (unused).

This is the **one complete revised engineering report** after independent audits N0.1 and Q0.1. It preserves prior valid execution evidence and supersedes earlier safety interpretations where Q01–Q02 applied. Gemini’s “Experimental Review PASS” is **not** relied upon (incorrect source references; see Q0.1 §3).

---

## 0. Authority and non-claims

| Statement | Status |
|---|---|
| Frozen spec clauses 767, 771–772 | `SOURCE CONTRACT` (unchanged) |
| Official `TP0008+` Alembic revisions | `NOT CREATED` |
| Option C / Package-1 / Gates A–D | `NOT SELECTED` / `NOT AUTHORIZED` |
| Production keys, patient data, persistent DBs | `NOT ACCESSED` |
| ACR / MIG-DEC-01 / INDEX-DEC-15 | `UNSIGNED` |
| Synthetic digests | Explicit stand-in — not real HMAC custody |
| Deployable Alembic migration gate | `BLOCKED` (experiment only) |

---

## 1. Git identity

| Field | Value |
|---|---|
| Correction branch | `cursor/m102-p1-p2-n01-n09-corrections-95a4` |
| **Authoritative tested HEAD** | `2f0b1eb16d3d1572fb7226377fc5ae55519a58d2` |
| Q01/Q02 implementation | `988bbb68a99f6bef0f511b64b0688efbb9937856` |
| Positive multi-tenant + evidence preserve | `124a358082047e576bffa67b79ecb974a847ba7a` |
| Shared-session population fix | `2f0b1eb16d3d1572fb7226377fc5ae55519a58d2` |
| Branched from original experiment | `016d547c673bfc79bfcc192e56f35b3108e4be56` |
| Original green test SHA | `c08f057962be2a4b6da8f6d1e516213266e302d6` |
| Merged to `main`? | **No** |

---

## 2. Preserved prior evidence

| Evidence | Observation | Classification |
|---|---|---|
| Original green CI [43750114653](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/43750114653) @ `c08f057` | 87/87 PASS | `PASS` bounded execution (pre-N0.1) |
| Adversarial audit [43759658695](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/43759658695) @ `b6280e1` | 87/87 + 3/3 gap confirmations | N01–N05 gaps confirmed |
| Pre-Q0.1 green [43763052360](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/43763052360) @ `7f7ac60` | 89+4=93, required=22 | N01–N09 experimental closures (pre-population-scope) |
| Docs HEAD [43763279458](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/43763279458) @ `1a240fa` | 93 PASS | Audited by Q0.1 |
| Q0.1 independent audit [43766316024](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/43766316024) @ `6b61bcf` | **2/2 counterexamples PASS** | Q01+Q02 gaps confirmed |
| Q01/Q02 impl CI [43766648382](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/43766648382) @ `988bbb6` | 89 + 6 safety = 95; `required=24` | Population-scope + DB immutability closed |
| Pre-fix positive attempt [43766985265](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/43766985265) @ `124a358` | **FAIL** — shared-session leftover null rows | Fixed in `2f0b1eb` |
| **Authoritative green** [43767195809](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/43767195809) @ `2f0b1eb` | 90 + 6 safety = 96; `required=25` | Q01/Q02 + positive multi-tenant cutover |
| M0 @ `2f0b1eb` [43767200949](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/43767200949) | SUCCESS | Full M0 suite |

TP0002 active/next indexes remain the frozen baseline; official TP lineage ends at `TP0007`.

---

## 3. Q0.1 findings and corrections

| ID | Finding | Correction | Result |
|---|---|---|---|
| **Q01** | Single-tenant backfill set model-global `backfill_complete`; cutover while other tenants incomplete | `collect_backfill_proof` scans **all** `person_identifiers` tenants; attest/cutover re-validate full population; prove helpers drive global backfill | **PASS** (experimental) |
| **Q02** | Evidence UPDATE/DELETE by `db_migrator`; `init_model` DELETE | BEFORE UPDATE/DELETE triggers raise; REVOKE UPDATE/DELETE; `init_model` no longer erases evidence | **PASS** (experimental DB trust boundary) / **BLOCKED** for cryptographic/admin-bypass immutability claims |

Fail-closed regressions (isolated session) — previously successful audit counterexamples now reject:

- `test_n05_closed_partial_tenant_backfill_cannot_cutover` → **PASS** (reject)
- `test_n05_closed_evidence_log_db_immutable_against_migrator` → **PASS** (reject UPDATE/DELETE; evidence preserved across `init_model`)

Positive multi-tenant path:

- `test_p1_multitenant_backfill_then_cutover_succeeds` → **PASS** (full-population complete → cutover)

---

## 4. N01–N09 disposition (retained)

| ID | Result |
|---|---|
| N01 active-authority wipe/DROP refusal | **PASS** |
| N02 P2 ACTIVE uniqueness | **PASS** |
| N03 parent person/type/authority binding | **PASS** |
| N04 mandatory Lock/LWLock (superuser inspector) | **PASS** |
| N05 proof-bound phase + population scope + DB append-only | **PASS** experimental / **BLOCKED** deployable Alembic gate |
| N06 exact catalog + real-target invalid recovery | **PASS** |
| N07 atomic dual-write / two rotations | **PASS** (synthetic) |
| N08 recommendation | **PROPOSED** P1 only — not APPROVED |
| N09 tested SHA vs docs HEAD | Distinguished in this report |

---

## 5. Code and tests (`IMPLEMENTED` / `TESTED`)

`experiments/m102_hmac_physical/`:

- `phase_gate.py` — full-population `collect_backfill_proof`; cutover live re-check; `m102_exp_forbid_evidence_mutation` triggers; REVOKE UPDATE/DELETE; `init_model` does not DELETE evidence
- `lifecycle.py` — `_backfill_all_tenants` + prove helpers ignore tenant-local shortcuts
- P1/P2 DDL, rotation, concurrent ops, index catalog (prior N01–N09 closures retained)

Tests:

- P1/P2 physical, fresh/upgrade guards, unit contracts
- Isolated `test_m102_corrected_safety_invariants.py` (fresh Testcontainers session)
- Required CI nodes include both Q01/Q02 fail-closed tests and positive multi-tenant cutover

Workflow: `.github/workflows/m102-p1-p2-physical-experiment.yml` (two pytest sessions + required-node guard).

---

## 6. Authoritative CI (HEAD `2f0b1eb`)

| Run | SHA | Result |
|---|---|---|
| [43767195809](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/43767195809) | `2f0b1eb` | **success** — main 90 + safety 6; guard `required=25 total=96 failed=0 skipped=0` |
| [43767200949](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/43767200949) | `2f0b1eb` | **success** — M0 full suite |

**Artifact:** `m102-p1-p2-physical-evidence` ID [`14181789494`](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/43767195809)

```
required=25
total=96
failed=0
skipped=0
acceptance_status=EXPERIMENTAL_CORRECTIONS_TESTED_NOT_APPROVED
```

JUnit/pytest logs confirm:

- `test_p1_multitenant_backfill_then_cutover_succeeds` PASSED
- `test_n05_closed_partial_tenant_backfill_cannot_cutover` PASSED
- `test_n05_closed_evidence_log_db_immutable_against_migrator` PASSED

---

## 7. Requirement matrix

| Requirement | Result |
|---|---|
| Multi-tenant backfill completeness before cutover | **PASS** |
| Partial-tenant cutover rejection | **PASS** |
| Positive multi-tenant backfill + cutover | **PASS** |
| DB-enforced evidence append-only (migrator UPDATE/DELETE denied) | **PASS** (trigger boundary) |
| Evidence preserved across `init_model` | **PASS** |
| Mandatory lock wait / authority-preserving rotation / P2 ACTIVE+FK | **PASS** |
| Real HMAC/AES/AAD, offline Local fencing, TP0008+, ACRs, Gates | **BLOCKED** |
| Privileged superuser/replication-role evidence bypass | **BLOCKED** (not claimed defeated) |

---

## 8. Reassessed recommendation — **PROPOSED** only

**Prefer P1** as the continuing design candidate for a future migration ACR.  
**Retain P2** as a documented alternative with higher RLS/grant review burden.  
**Neither model is APPROVED.** Do not sign INDEX-DEC-15 or MIG-DEC-01 from this report.

---

## 9. Remaining blockers

| Blocker | Status |
|---|---|
| Independent re-review of Q01/Q02 closures | `BLOCKED` pending reviewer |
| Deployable Alembic TP0008+ / Package-2 ordering | `BLOCKED` |
| Real keyed HMAC + AES-GCM AAD | `BLOCKED` |
| Production-like writer drain/lease fencing | `BLOCKED` |
| Cryptographic / superuser-proof evidence anchoring | `BLOCKED` |
| Package-1 / Gates A–D authorization | `BLOCKED` |

---

## 10. Final outcome

`Q01+Q02 CLOSED UNDER DISPOSABLE PG15 (2f0b1eb / run 43767195809: 96 tests, required=25) / PRIOR N01–N09 + AUDIT EVIDENCE PRESERVED / POSITIVE MULTI-TENANT CUTOVER PASS / P1 PROPOSED (NOT APPROVED) / DEPLOYABLE GATE BLOCKED / NO TP0008+ / NO PACKAGE-1 / NO ACR OR GATE DECLARATION / MAIN UNCHANGED / PR #3 REMAINS DRAFT`

**End of corrected report.**

# M1-02 P1 vs P2 HMAC Physical Design Experiment — Corrected Engineering Report

**Date:** 2026-11-15  
**Repository:** `AmirSheikhloo/clinic-ecosystem`  
**Correction branch:** `cursor/m102-p1-p2-n01-n09-corrections-95a4`  
**Original experiment branch:** `cursor/m102-p1-p2-hmac-physical-experiment-95a4`  
**Base `main`:** `fdae362e1a889831975060808ac612369d3b0d0a`  
**Tested code SHA:** `0b5bb6a8409e60055d7cd244817f61ec7e7ef4db` (authoritative green experiment CI — do not conflate with later docs-only commits)  
**Classification:** `EXPERIMENTAL CORRECTIONS TESTED / NOT APPROVED / NOT Package-1 / NOT Gate A–D / NO ACR`

Status vocabulary: **PROPOSED**, **IMPLEMENTED**, **TESTED**, **PASS**, **FAIL**, **BLOCKED**, **APPROVED** (unused).

This document is the **one complete corrected engineering report** for the M1-02 P1/P2 physical experiment after independent adversarial audit N0.1. It preserves prior valid execution evidence and supersedes the original report’s **safety interpretation** where N01–N09 applied.

---

## 0. Authority and non-claims

| Statement | Status |
|---|---|
| Frozen `docs/FINAL_MASTER_SPECIFICATION_v3.0.1_FINAL.txt` clauses 767, 771–772 | `SOURCE CONTRACT` (unchanged) |
| R4.12 / C0.4 / L0.2 as review candidates | `NOT ALTERED` — L0.2 DOCUMENT REVIEW PASS retained |
| Official `TP0008+` Alembic revisions | `NOT CREATED` |
| Option C migration numbering | `NOT SELECTED` / `NOT APPROVED` |
| Package-1 implementation / Gates A–D | `NOT AUTHORIZED` / `NOT CLAIMED` |
| Production keys, patient data, persistent target DB | `NOT ACCESSED` |
| ACR / MIG-DEC-01 / INDEX-DEC-15 | `UNSIGNED` / `NOT DECLARED` |
| Synthetic digests (`synthetic_hmac.py`) | Explicit stand-in — **not** real HMAC key custody |

---

## 1. Git identity

| Field | Value |
|---|---|
| Correction branch | `cursor/m102-p1-p2-n01-n09-corrections-95a4` |
| Tested code SHA (green CI) | `0b5bb6a8409e60055d7cd244817f61ec7e7ef4db` |
| N01–N09 implementation commit | `55f4d9a6565a3825256560555564e195aeb24259` |
| Lock-wait inspector fix | `0b5bb6a8409e60055d7cd244817f61ec7e7ef4db` |
| Docs-only report commits | May advance branch HEAD; tested code SHA above remains authoritative |
| Branched from original experiment HEAD | `016d547c673bfc79bfcc192e56f35b3108e4be56` |
| Original green test SHA | `c08f057962be2a4b6da8f6d1e516213266e302d6` |
| Original implementation | `101d1d8bab662d8ece4219382efcc83a57d1e8c6` |
| PR | https://github.com/AmirSheikhloo/clinic-ecosystem/pull/3 |
| Merged to `main`? | **No** |

---

## 2. Prior evidence preserved (original experiment + N0.1 audit)

### 2.1 Original Cursor experiment (still valid as execution ledger)

| Evidence | Observation | Classification |
|---|---|---|
| Original branch | `cursor/m102-p1-p2-hmac-physical-experiment-95a4` @ `016d547…` | PRESERVED |
| Green CI | [Run 43750114653](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/43750114653), SHA `c08f057…`, **87 passed / 0 failed / 0 skipped**, `required=16` | `PASS` bounded execution |
| Later HEAD CI | [Run 43750323263](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/43750323263), `016d547…` | Workflow success (report commit) |
| Guard-fail CI | [Run 43749863252](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/43749863252), `101d1d8…` | Tests 87/87; guard missed parametrized names |
| Artifact | `m102-p1-p2-physical-evidence` ID `14176340152` | PRESERVED listing |
| Prior spikes | Runs 43747042672 / 43747538019 / 43748254928 | HISTORICAL ONLY |

The original 87-pass suite remains authentic evidence that the *then-asserted* nodes executed on disposable PG15. It is **not** sufficient safety acceptance (N0.1).

### 2.2 Independent adversarial audit N0.1

| Evidence | Observation | Classification |
|---|---|---|
| Audit branch | `audit/m102-cursor-adversarial-20261116` @ `b6280e1547a191bdb39b108ec6f25f4b5d60d01c` | PRESERVED |
| Contaminated first audit CI | [Run 43759564790](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/43759564790) | Fixture contamination; not baseline regression |
| Isolated audit CI | [Run 43759658695](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/43759658695) | Original **87/87 PASS**; counterexamples **3/3 PASS** (gaps confirmed) |
| Audit disposition | Material defects N01–N09; approval blocked | `FAIL` as safety basis |

### 2.3 TP0002 indexes preserved (unchanged contract)

```sql
CREATE UNIQUE INDEX uq_person_identifier_active_lookup
ON person_identifiers (tenant_id, id_type, issuing_country_or_authority, lookup_hmac_active);

CREATE UNIQUE INDEX uq_person_identifier_next_lookup
ON person_identifiers (tenant_id, id_type, issuing_country_or_authority, lookup_hmac_next)
WHERE lookup_hmac_next IS NOT NULL;
```

Official TP lineage on `main` still ends at `TP0007`.

---

## 3. N01–N09 correction disposition

| ID | Finding (N0.1) | Correction in experimental code/tests | Result |
|---|---|---|---|
| **N01** | P1 wipe/DROP of active gen2 after cutover | `p1_rollback_gen2` / `p1_drop_generation_index_if_safe` refuse while `active_generation` matches; `rollback_to_previous_active` keeps index; two complete rotations assert authority | **PASS** (closed under disposable PG15) |
| **N02** | P2 ACTIVE uniqueness missing after promotion | Build/assert `P2_ACTIVE_INDEX` before promotion; duplicate ACTIVE rejected | **PASS** |
| **N03** | Sidecar person/type/authority unbound | Composite FK `(tenant_id,identifier_id,person_id)` + BEFORE trigger for type/authority | **PASS** |
| **N04** | Lock wait optional / ignored | `require_observed_lock_wait=True` fail-closed; superuser inspector DSN; commit + rollback loser paths | **PASS** |
| **N05** | Evidenceless phase/cutover; tautological phase9 CHECK | Evidence flags + `m102_exp_phase_evidence`; cutover requires drain/backfill/index/cutover_ready + candidate match; `phase9_operational_executed` forced FALSE | **PASS** (metadata simulation only — still not a real Alembic gate) |
| **N06** | `IF NOT EXISTS` without catalog assert; probe-only invalid recovery | Exact `pg_get_indexdef` catalog assert; recover invalid on real gen2 target | **PASS** |
| **N07** | Atomic dual-write / two full rotations incomplete | `p1_atomic_dual_write_gen` same-TX verify+write; resumable FOR UPDATE backfill; gen2 then gen3 cutovers with prior index retained until safe drop | **PASS** (synthetic canonical source) |
| **N08** | Premature P1/P2 recommendation | Reassessed below; neither APPROVED | **PASS** (recommendation corrected) |
| **N09** | Stale report HEAD metadata | This report distinguishes tested code SHA vs report commit SHA | **PASS** (documentation) |

---

## 4. Corrected code and tests (`IMPLEMENTED` / `TESTED`)

### 4.1 Experimental package

`experiments/m102_hmac_physical/`:

- `p1_staged_columns.py` — gen2/gen3 columns; concurrent unique DDL **without** `IF NOT EXISTS`
- `p2_generation_sidecar.py` — sidecar + parent identity FK/trigger + ACTIVE/CANDIDATE/NEXT indexes
- `phase_gate.py` — evidence-bound phase metadata; authority-preserving rollback API
- `rotation.py` — atomic dual-write, resumable backfill, active-authority assertions, safe drop
- `concurrent_ops.py` — Alembic concurrent build, catalog assert wrapper, mandatory Lock/LWLock barrier via privileged inspector, real-target invalid recovery
- `index_catalog.py`, `lifecycle.py` — catalog equality helpers; evidence-advancing runner
- `fixtures.py`, `synthetic_hmac.py` — synthetic populated fixtures only

### 4.2 Tests

- `tests/integration/test_m102_p1_physical_experiment.py`
- `tests/integration/test_m102_p2_physical_experiment.py`
- `tests/integration/test_m102_fresh_upgrade_and_package2_guard.py`
- `tests/integration/test_m102_corrected_safety_invariants.py` (isolated session)
- `tests/unit/test_m102_p1_p2_experiment_contracts.py`
- Workflow: `.github/workflows/m102-p1-p2-physical-experiment.yml` (two pytest processes)

### 4.3 Exact experimental index definitions

**P1 gen2 / gen3 (nonredundant vs TP0002 next):**

```sql
CREATE UNIQUE INDEX CONCURRENTLY uq_exp_p1_identifier_gen2_lookup
ON public.person_identifiers (
  tenant_id, id_type, issuing_country_or_authority, exp_lookup_hmac_gen2
) WHERE exp_lookup_hmac_gen2 IS NOT NULL;

CREATE UNIQUE INDEX CONCURRENTLY uq_exp_p1_identifier_gen3_lookup
ON public.person_identifiers (
  tenant_id, id_type, issuing_country_or_authority, exp_lookup_hmac_gen3
) WHERE exp_lookup_hmac_gen3 IS NOT NULL;
```

**P2 status-scoped (ACTIVE required after promotion):**

```sql
CREATE UNIQUE INDEX CONCURRENTLY uq_exp_p2_hmac_active_lookup
ON public.person_identifier_hmac_generations_exp (
  tenant_id, id_type, issuing_country_or_authority, lookup_hmac
) WHERE generation_status = 'ACTIVE';

CREATE UNIQUE INDEX CONCURRENTLY uq_exp_p2_hmac_candidate_lookup
ON public.person_identifier_hmac_generations_exp (
  tenant_id, id_type, issuing_country_or_authority, lookup_hmac
) WHERE generation_status = 'CANDIDATE';
```

---

## 5. Corrected CI evidence (`VERIFIED` execution)

| Run | SHA | Workflow | Conclusion | Notes |
|---|---|---|---|---|
| [43760906258](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/43760906258) | `55f4d9a…` | M1-02 P1/P2 physical | **failure** | 87 passed; **2 failed** — Lock wait unobserved under migrator-role inspector (N04 observation path) |
| [43760917123](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/43760917123) | `55f4d9a…` | M0 PostgreSQL integration | **failure** | Same barrier + shared-fixture global empty-table assert |
| [43761147557](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/43761147557) | `0b5bb6a…` | M1-02 P1/P2 physical | **success** | Main suite **89 passed**; isolated safety **3 passed**; guard `required=21 total=92 failed=0 skipped=0` |
| [43761151991](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/43761151991) | `0b5bb6a…` | M0 PostgreSQL integration | **success** | Confirms corrections under full M0 suite |

**Authoritative corrected green run:** https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/43761147557  

**Artifact:** `m102-p1-p2-physical-evidence` ID `14180930174`  
Contains: `m102-p1-p2-junit.xml`, `m102-p1-p2-pytest.txt`, `m102-safety-junit.xml`, `m102-safety-pytest.txt`, `m102-p1-p2-summary.txt`

```
required=21
total=92
failed=0
skipped=0
acceptance_status=EXPERIMENTAL_CORRECTIONS_TESTED_NOT_APPROVED
```

First correction CI failure is recorded deliberately: tests were **not** weakened; the inspector privilege path was fixed so the mandatory lock-wait assertion can observe reality.

---

## 6. Requirement matrix (reclassified)

| Requirement | Result | Notes |
|---|---|---|
| Existing PG15 TP0002 indexes and RLS | **PASS** | Bounded; preserved under expand |
| Nonredundant P1 gen2/gen3 / P2 candidate+ACTIVE | **PASS** | Catalog-asserted definitions |
| `CONCURRENTLY` on populated synthetic rows | **PASS** | Alembic autocommit_block |
| Deterministic blocked-writer barrier (observed) | **PASS** | Fail-closed; admin inspector |
| Gen2 authority retained through cutover/rollback/rotation | **PASS** | Wipe/DROP refused while active |
| P2 ACTIVE uniqueness after promotion | **PASS** | Index built before promote; duplicate denied |
| Sidecar person/type/authority consistency | **PASS** | FK + trigger |
| Resumable backfill + atomic dual-write (synthetic) | **PASS** | FOR UPDATE batches; HMAC mismatch denied |
| Two complete consecutive rotations | **PASS** | P1 gen2→gen3; P2 v2→v3 with ACTIVE retained |
| Invalid index recovery on real generation target | **PASS** | Gen2 target + probe table |
| Evidence-bound experimental phase transitions | **PASS** | Still metadata simulation only |
| Real Alembic TP0008+ / Package-2 deployable gate | **BLOCKED** | No official revisions; not claimed |
| Real HMAC/AES/AAD and key custody | **BLOCKED** | Synthetic only |
| Offline Local Hub drain/fencing (production lease) | **BLOCKED** | Evidence flag stand-in only |
| Persistent target Cloud/Local catalog | **BLOCKED** | Not accessed |
| Signed MIG/GATE/API ACRs | **BLOCKED** | Unsigned |

---

## 7. P1 vs P2 comparison (post-correction)

| Dimension | P1 staged columns | P2 generation sidecar |
|---|---|---|
| Frozen F.2 proximity | Closer (additive columns) | Farther (new relation + grants/RLS) |
| Active uniqueness handoff | GenN partial unique index retained through cutover | ACTIVE partial unique index required before promote |
| Identity consistency | Same-row columns | Composite parent FK + type/authority trigger |
| Repeat rotation | Finite slots (gen2/gen3 shown); slot reuse needs ACR | Multi-version rows; retirement lifecycle still needs ACR |
| Dual-write atomicity | Same-row fields in one TX | Parent lock + sidecar upsert |
| Migration / review burden | Lower | Higher |
| Experimental safety after N01–N09 | Material gaps closed under PG15 | Material gaps closed under PG15 |

---

## 8. Reassessed recommendation — **PROPOSED** only

**Prefer P1 as the continuing design candidate** for a future migration ACR: additive on frozen `person_identifiers`, lower RLS/grant novelty, and demonstrated authority-preserving cutover/rollback across two complete synthetic rotations.

**Retain P2 as a documented alternative** when durable multi-generation history beyond fixed slots is a hard requirement — now with ACTIVE uniqueness and parent identity binding demonstrated experimentally, but still with higher frozen-spec compatibility and RLS review burden.

**Neither model is APPROVED or “VERIFIED SAFE” for production.** Do **not** sign INDEX-DEC-15 or MIG-DEC-01 from this report alone. Do **not** create official `TP0008+` or implement Package-1 from this experiment.

---

## 9. Remaining technical blockers

| Blocker | Status | Evidence required |
|---|---|---|
| Independent re-review of correction branch vs 771–772 | `BLOCKED` | Written review citing this report’s SHAs/CI |
| Signed `ACR-M102-MIG-001` (model + TP graph + Phase-9 + re-rotation) | `NOT EFFECTIVE` | PO/DBA signed ACR |
| Real keyed HMAC + AES-GCM AAD normalizer | `BLOCKED` | Crypto vectors under test-key custody |
| Production-like writer drain / lease fencing | `BLOCKED` | Offline Local Hub fence proofs beyond evidence flags |
| Deployable Alembic heads (TP0008+) and Package-2 ordering | `BLOCKED` | Approved TP graph after physical ACR |
| Persistent Cloud/Local catalog inventory | `BLOCKED` | Explicit read-only access policy |
| Gate A–D / Package-1 coding authorization | `BLOCKED` | Separate gate evidence |

---

## 10. Final outcome

`N01–N09 EXPERIMENTAL CORRECTIONS IMPLEMENTED + PG15-TESTED + CI-VERIFIED (89+3=92 / required=21 on run 43761147557 @ 0b5bb6a) / PRIOR 87-PASS + AUDIT 43759658695 EVIDENCE PRESERVED / P1 REMAINS PROPOSED CANDIDATE (NOT APPROVED) / P2 RETAINED AS DOCUMENTED ALTERNATIVE / NO TP0008+ / NO PACKAGE-1 / NO ACR OR GATE DECLARATION / MAIN UNCHANGED`

**End of corrected report.**

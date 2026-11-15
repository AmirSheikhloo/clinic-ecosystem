# M1-02 P1 vs P2 HMAC Physical Design Experiment — Engineering Report

**Date:** 2026-11-15
**Repository:** `AmirSheikhloo/clinic-ecosystem`
**Branch:** `cursor/m102-p1-p2-hmac-physical-experiment-95a4`
**Base:** `origin/main` @ `fdae362e1a889831975060808ac612369d3b0d0a`
**HEAD SHA:** `c08f057962be2a4b6da8f6d1e516213266e302d6`
**Classification:** `EXPERIMENTAL / PROPOSED / TESTED / VERIFIED-IN-EPHEMERAL-PG15 / NOT APPROVED / NOT Package-1 / NOT Gate A`

Status vocabulary used below: **PROPOSED**, **IMPLEMENTED**, **TESTED**, **VERIFIED**, **APPROVED**, **BLOCKED**.

---

## 0. Authority and non-claims

| Statement | Status |
|---|---|
| Frozen `docs/FINAL_MASTER_SPECIFICATION_v3.0.1_FINAL.txt` clauses 771–772 | `SOURCE CONTRACT` (unchanged) |
| R4.12 roadmap / C0.4 contract in this checkout | `NOT PRESENT` — unavailable locally; handoff-only review candidates |
| Option C migration numbering | `NOT SELECTED` / `NOT APPROVED` |
| Official `TP0008+` Alembic revisions | `NOT CREATED` |
| Package-1 implementation / Gates A–D | `NOT AUTHORIZED` / `NOT CLAIMED` |
| Production keys, patient data, persistent target DB | `NOT ACCESSED` |
| Prior CI runs 72/75/77 | `HISTORICAL SPIKES ONLY` — not HMAC Phase-6 generation proof |
| This experiment | `IMPLEMENTED` + `TESTED` + `VERIFIED` (ephemeral PG15 only) |

No Package-1 authorization, Gate A acceptance, or production readiness is claimed.

---

## 1. Git identity

| Field | Value |
|---|---|
| Branch | `cursor/m102-p1-p2-hmac-physical-experiment-95a4` |
| HEAD | `c08f057962be2a4b6da8f6d1e516213266e302d6` |
| Implementation commit | `101d1d8bab662d8ece4219382efcc83a57d1e8c6` |
| Evidence-guard fix | `c08f057962be2a4b6da8f6d1e516213266e302d6` |
| Base `main` | `fdae362e1a889831975060808ac612369d3b0d0a` |
| Merged to `main`? | **No** |

---

## 2. Source inspection (verified)

### 2.1 Clause 771–772

HMAC rotation is a nine-phase expand/dual-write/drain/backfill/validate/`CREATE UNIQUE INDEX CONCURRENTLY`/indisvalid-remediation/cutover/contract lifecycle. Dual-write must compute old and new indexes from the same canonical source in one write transaction; failed concurrent indexes must be detected and remediated before cutover.

### 2.2 TP0002 indexes (preserved)

```sql
CREATE UNIQUE INDEX uq_person_identifier_active_lookup
ON person_identifiers (tenant_id, id_type, issuing_country_or_authority, lookup_hmac_active);

CREATE UNIQUE INDEX uq_person_identifier_next_lookup
ON person_identifiers (tenant_id, id_type, issuing_country_or_authority, lookup_hmac_next)
WHERE lookup_hmac_next IS NOT NULL;
```

TP lineage on `main` ends at `TP0007`. Phone lookup remains nonunique (out of this experiment’s mutation scope).

### 2.3 Prior CI (re-checked)

| Run | SHA | Observation |
|---|---|---|
| [43747042672](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/43747042672) | `a49171a` | foundations preflight |
| [43747538019](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/43747538019) | `4039293` | duplicate next-index on empty table |
| [43748254928](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/43748254928) | `8a13097` | existing next-index only; no deterministic TX barrier |

---

## 3. Complete code and test changes

### 3.1 Experimental package (`IMPLEMENTED`)

`experiments/m102_hmac_physical/`:

- `p1_staged_columns.py` — gen2/gen3 columns + concurrent index DDL
- `p2_generation_sidecar.py` — sidecar table, FORCE RLS, status-scoped indexes
- `phase_gate.py` — one-step phase metadata + fail-closed experimental upgrade-head
- `rotation.py` — dual-write / resumable backfill / rollback helpers
- `concurrent_ops.py` — Alembic autocommit concurrent index, two-session barrier, invalid-index repair
- `fixtures.py`, `synthetic_hmac.py` — synthetic populated fixtures (not production crypto)

### 3.2 Tests (`IMPLEMENTED` / `TESTED`)

- `tests/integration/test_m102_p1_physical_experiment.py`
- `tests/integration/test_m102_p2_physical_experiment.py`
- `tests/integration/test_m102_fresh_upgrade_and_package2_guard.py`
- `tests/unit/test_m102_p1_p2_experiment_contracts.py`
- Workflow: `.github/workflows/m102-p1-p2-physical-experiment.yml`

### 3.3 Exact experimental index definitions observed

**P1 gen2 (nonredundant vs TP0002 next):**

```sql
CREATE UNIQUE INDEX CONCURRENTLY uq_exp_p1_identifier_gen2_lookup
ON public.person_identifiers (
  tenant_id, id_type, issuing_country_or_authority, exp_lookup_hmac_gen2
) WHERE exp_lookup_hmac_gen2 IS NOT NULL;
```

**P1 gen3 (second rotation cycle):**

```sql
CREATE UNIQUE INDEX CONCURRENTLY uq_exp_p1_identifier_gen3_lookup
ON public.person_identifiers (
  tenant_id, id_type, issuing_country_or_authority, exp_lookup_hmac_gen3
) WHERE exp_lookup_hmac_gen3 IS NOT NULL;
```

**P2 candidate / next (sidecar):**

```sql
CREATE UNIQUE INDEX CONCURRENTLY uq_exp_p2_hmac_candidate_lookup
ON public.person_identifier_hmac_generations_exp (
  tenant_id, id_type, issuing_country_or_authority, lookup_hmac
) WHERE generation_status = 'CANDIDATE';

CREATE UNIQUE INDEX CONCURRENTLY uq_exp_p2_hmac_next_lookup
ON public.person_identifier_hmac_generations_exp (
  tenant_id, id_type, issuing_country_or_authority, lookup_hmac
) WHERE generation_status = 'NEXT';
```

Observed behavior in disposable PG15: indexes created via Alembic `autocommit_block`; catalog showed `indisunique/indisvalid/indisready`; TP0002 active/next indexes remained present with distinct OIDs; Alembic version stayed `tp0007`.

---

## 4. GitHub Actions evidence (`VERIFIED`)

| Run | SHA | Conclusion | Pytest | Evidence guard |
|---|---|---|---|---|
| [43749863252](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/43749863252) | `101d1d8` | failure (guard only) | **87 passed / 0 failed / 0 skipped** | missed parametrized `[cloud_tenant]`/`[local_hub]` names |
| [43750114653](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/43750114653) | `c08f057` | **success** | **87 passed / 0 failed / 0 skipped** | `OK required=16 total=87 failed=0 skipped=0` |

**Artifact (both runs):** `m102-p1-p2-physical-evidence`
- `m102-p1-p2-junit.xml`
- `m102-p1-p2-pytest.txt`
- `m102-p1-p2-summary.txt` (green run)

Authoritative green run: https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/43750114653

---

## 5. Requirement matrix (`TESTED` / `VERIFIED` in ephemeral PG15)

| Requirement | P1 | P2 | Result |
|---|---|---|---|
| Compatibility with `person_identifiers` | PASS | PASS | `VERIFIED` |
| Preserve TP0002 active/next indexes | PASS | PASS | `VERIFIED` |
| Nonredundant physical generation index | PASS | PASS | `VERIFIED` |
| `CREATE UNIQUE INDEX CONCURRENTLY` on populated tables | PASS | PASS | `VERIFIED` |
| Deterministic two-session TX barrier conflicts | PASS | PASS | `VERIFIED` |
| Invalid-index detect/cleanup/retry | PASS | shared probe | `VERIFIED` |
| Resumable backfill + rollback | PASS | PASS | `VERIFIED` |
| Two consecutive rotation cycles | PASS (gen2→gen3) | PASS (v2→v3) | `VERIFIED` |
| Roles / RLS / Cloud+Local | PASS both planes | PASS + runtime GUC | `VERIFIED` |
| Fresh install vs upgrade | PASS | expand on fresh | `VERIFIED` |
| Phase gate / unsafe `upgrade head` | PASS | shared meta | `VERIFIED` |
| Package-2 / deferred Phase-9 impact | PASS (no TP0008+/TP0011; phase9 not operational) | PASS | `VERIFIED` |

M0/M1-01 regressions included in the same 87-pass suite.

---

## 6. P1 vs P2 comparison (security & migration)

| Dimension | P1 staged columns | P2 generation sidecar |
|---|---|---|
| Frozen F.2 proximity | Closer (additive columns) | Farther (new relation) |
| Nonredundant Phase-6 | Indexes gen2/gen3, not `lookup_hmac_next` | Status-scoped sidecar indexes |
| Repeat rotation | Needs more slots or recycling ACR | Multi-version rows; cleanup ACR still required |
| Dual-write atomicity | Same-row fields | Parent + sidecar row(s) |
| RLS | Inherits `person_identifiers` | Must mirror FORCE RLS/grants |
| Migration novelty / review burden | Lower | Higher |
| Security | Keep HMAC/ciphertext out of logs; synthetic digests only in tests | Larger grant/RLS surface if misconfigured |
| Package-2 while experimental | Unaffected (no official TP) | Unaffected |

---

## 7. Recommended physical design — **PROPOSED** (not approved)

**Prefer P1** as the default candidate for a future migration ACR: additive on frozen `person_identifiers`, preserves active/next until handoff, and makes Phase-6 a genuinely new physical index on generation-specific columns.

**Retain P2** as a documented alternative when durable multi-generation history / more than two staged slots is a hard requirement, subject to explicit frozen-spec compatibility ACR.

This recommendation is **PROPOSED** only. It is **not** `APPROVED`, does not select Option C numbering, and does not authorize `TP0008+` or Package-1 coding.

---

## 8. Remaining blockers and evidence needed

| Blocker | Status | Evidence required to resolve |
|---|---|---|
| Independent architecture/DBA review of this branch vs 771–772 | `BLOCKED` | Written review citing exact DDL/tests/CI SHA |
| Signed `ACR-M102-MIG-001` (generation model + TP graph + deferred Phase-9 + re-rotation) | `NOT EFFECTIVE` | PO/DBA signed ACR text |
| R4.12 / C0.4 files absent from checkout | `BLOCKED` | Provide/mount actual roadmap + C0.4 sources |
| Real HMAC/AAD/normalizer (not synthetic digests) | `NOT TESTED` | Crypto vectors under test-key custody policy |
| Persistent Cloud/Local catalog | `UNKNOWN` | Read-only inventory under explicit access policy |
| Full offline Local drain/fencing (clause 771 phase 3) | `PARTIAL` | Dedicated drain/lease fence proofs beyond dual-plane fixtures |
| Option C / Package-2 TP0011–14 graph | `OPEN` | Approved release graph after physical ACR |

---

## 9. Final outcome

`PHYSICAL EXPERIMENT IMPLEMENTED + PG15-TESTED + CI-VERIFIED (87/87 on run 43750114653) / DESIGN RECOMMENDATION PROPOSED (P1 preferred) / NO PACKAGE-1 AUTHORIZATION / NO PRODUCTION READINESS / MAIN UNCHANGED`

# M1-02 P1 vs P2 HMAC Physical Design Experiment — Engineering Report

**Date:** 2026-11-15
**Repository:** `AmirSheikhloo/clinic-ecosystem`
**Branch:** `cursor/m102-p1-p2-hmac-physical-experiment-95a4`
**Base:** `origin/main` @ `fdae362e1a889831975060808ac612369d3b0d0a`
**Experiment SHAs:**
- Implementation: `101d1d8bab662d8ece4219382efcc83a57d1e8c6`
- Evidence-guard fix: _(this commit)_
**Classification:** `EXPERIMENTAL / PROPOSED / TESTED-IN-EPHEMERAL-PG15 / NOT APPROVED / NOT Package-1 / NOT Gate A`

## 0. Authority and non-claims

| Statement | Status |
|---|---|
| Frozen source clauses 771–772 | `SOURCE CONTRACT` (unchanged) |
| R4.12 / C0.4 files in repository checkout | `NOT PRESENT` — unavailable locally; handoff-only review candidates |
| Option C migration numbering | `NOT SELECTED / NOT APPROVED` |
| Official `TP0008+` | `NOT CREATED` |
| Package-1 / Gates A–D | `NOT AUTHORIZED / NOT CLAIMED` |
| Production keys / patient data / persistent DB | `NOT ACCESSED` |
| Prior runs 72/75/77 | `HISTORICAL SPIKES ONLY` |

## 1. Source inspection (verified)

### 1.1 Clause 771–772

Nine-phase HMAC rotation with dual-write, drain, backfill, `CREATE UNIQUE INDEX CONCURRENTLY` in dedicated autocommit Alembic revision, `indisvalid` remediation, cutover/rollback window, later contraction. Dual-write must use one canonical source value per write transaction.

### 1.2 TP0002 unique indexes (immutable on this experiment)

```sql
CREATE UNIQUE INDEX uq_person_identifier_active_lookup
ON person_identifiers (tenant_id, id_type, issuing_country_or_authority, lookup_hmac_active);

CREATE UNIQUE INDEX uq_person_identifier_next_lookup
ON person_identifiers (tenant_id, id_type, issuing_country_or_authority, lookup_hmac_next)
WHERE lookup_hmac_next IS NOT NULL;
```

### 1.3 Prior CI (not new generation proof)

| Run | SHA | Notes |
|---|---|---|
| [43747042672](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/43747042672) | `a49171a` | foundations preflight |
| [43747538019](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/43747538019) | `4039293` | duplicate next-index on empty table |
| [43748254928](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/43748254928) | `8a13097` | existing next-index only; no TX barrier |

## 2. Experimental models (PROPOSED)

### P1 — staged columns

Additive `exp_lookup_hmac_gen2/gen3` (+ version + pairing CHECKs) on `person_identifiers`.

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

### P2 — generation sidecar

`person_identifier_hmac_generations_exp` with status-scoped unique indexes and FORCE RLS.

```sql
CREATE UNIQUE INDEX CONCURRENTLY uq_exp_p2_hmac_candidate_lookup
ON public.person_identifier_hmac_generations_exp (
  tenant_id, id_type, issuing_country_or_authority, lookup_hmac
) WHERE generation_status = 'CANDIDATE';
```

### Phase gate

`m102_exp_rotation_phase_meta` one-step advances; experimental upgrade-head fail-closed; phase 9 dry-run only (`phase9_operational_executed=FALSE`).

## 3. Code/test inventory

- `experiments/m102_hmac_physical/` runtime scratch DDL/helpers
- `tests/integration/test_m102_p1_physical_experiment.py`
- `tests/integration/test_m102_p2_physical_experiment.py`
- `tests/integration/test_m102_fresh_upgrade_and_package2_guard.py`
- `tests/unit/test_m102_p1_p2_experiment_contracts.py`
- `.github/workflows/m102-p1-p2-physical-experiment.yml`

## 4. CI evidence

### Run A (implementation SHA `101d1d8`)

- URL: https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/43749863252
- Pytest: **87 passed / 0 failed / 0 skipped** (`TESTED`)
- Workflow overall: **failure** because evidence-summary required unparametrized names and missed `[cloud_tenant]/[local_hub]` nodes (`BLOCKED` evidence-guard only; tests themselves passed)
- Artifact: `m102-p1-p2-physical-evidence` (`m102-p1-p2-junit.xml`, `m102-p1-p2-pytest.txt`)

### Run B (evidence-guard fix)

- _Pending push of this commit_

## 5. Requirement results from Run A JUnit (ephemeral PG15)

| Requirement | P1 | P2 | Status |
|---|---|---|---|
| Compatibility with `person_identifiers` | PASS | PASS | `TESTED` |
| Preserve TP0002 active/next indexes | PASS | PASS | `TESTED` |
| Nonredundant physical generation index | PASS (gen2/gen3 cols) | PASS (sidecar + status predicate) | `TESTED` |
| `CREATE UNIQUE INDEX CONCURRENTLY` on populated tables | PASS | PASS | `TESTED` |
| Deterministic two-session TX barrier uniqueness | PASS | PASS | `TESTED` |
| Invalid-index detect/cleanup/retry | PASS | shared probe | `TESTED` |
| Resumable backfill + rollback | PASS | PASS (candidate batches) | `TESTED` |
| Two consecutive rotation cycles | PASS (gen2 then gen3) | PASS (v2 then v3) | `TESTED` |
| Roles / RLS / Cloud+Local | PASS (both planes) | PASS (+ runtime GUC) | `TESTED` |
| Fresh install vs upgrade | PASS | expand on fresh | `TESTED` |
| Phase gate / unsafe head | PASS | shared meta | `TESTED` |
| Package-2 / deferred Phase-9 | PASS (no TP0008+/TP0011; phase9 not operational) | PASS | `TESTED` (static+meta) |

## 6. P1 vs P2 comparison (PROPOSED)

| Dimension | P1 staged columns | P2 generation sidecar |
|---|---|---|
| Frozen F.2 proximity | Closer: additive columns on existing table | Farther: new relation beyond F.2 core shape |
| Nonredundant Phase-6 index | Yes — indexes gen2/gen3 columns, not `lookup_hmac_next` | Yes — status-scoped sidecar indexes |
| Repeat rotation | Needs additional staged slots or slot recycling ACR | Natural multi-version rows; still needs phase-9 cleanup ACR |
| Dual-write atomicity | Same-row update with active/next/genN | Row + sidecar row(s); more moving parts |
| RLS/privileges | Inherits `person_identifiers` policies | Must mirror FORCE RLS/grants (done experimentally) |
| Migration risk | Lower schema novelty; column churn on hot table | Higher review burden; clearer generation history |
| Package-2 impact | None while experimental (no official TP) | None while experimental |
| Security notes | Keep ciphertext/HMAC out of logs; synthetic digests only in tests | Sidecar increases attack surface if grants/RLS wrong |

### Recommended physical design (PROPOSED — not approved)

**Prefer P1 as the default candidate for a future migration ACR**, because it stays additive on the frozen `person_identifiers` relation, preserves existing active/next indexes until handoff, and makes Phase-6 a genuinely new physical index on generation-specific columns.

**Keep P2 as a documented alternative** when multi-generation history / more than two staged slots becomes a hard requirement, subject to explicit frozen-spec compatibility ACR (higher review burden).

Neither recommendation authorizes `TP0008+`, Option C numbering, or Package-1 implementation.

## 7. Remaining blockers (evidence still required)

1. **Independent architecture/DBA review** of this branch’s exact DDL/tests vs clauses 771–772 — status `BLOCKED` until reviewer sign-off.
2. **Signed ACR-M102-MIG-001** choosing implementable generation model + TP graph (incl. deferred Phase-9 placement and repeat-rotation revisions) — `NOT EFFECTIVE`.
3. **R4.12 / C0.4 source files** were not present in the repository checkout; Package-2 numbering must be confirmed against the actual roadmap file once available — `BLOCKED / SOURCE UNAVAILABLE LOCALLY`.
4. **Production-like crypto** (real HMAC keys, AAD, normalizer) not exercised; only synthetic digests — `NOT TESTED`.
5. **Persistent target DB catalog** still `UNKNOWN`; ephemeral CI does not prove live Cloud/Local state.
6. **Offline Local writer drain/fencing** beyond dual-plane fixtures remains incomplete relative to full clause-771 phase 3 — `PARTIAL`.
7. Workflow evidence-guard false-negative on parametrized names (fixed in this commit) — re-run required for green workflow conclusion.

## 8. Final status

`PHYSICAL EXPERIMENT IMPLEMENTED AND PG15-TESTED (87/87) / WORKFLOW GUARD FIX PENDING GREEN RE-RUN / DESIGN RECOMMENDATION PROPOSED / NO PACKAGE-1 AUTHORIZATION / NO PRODUCTION READINESS`

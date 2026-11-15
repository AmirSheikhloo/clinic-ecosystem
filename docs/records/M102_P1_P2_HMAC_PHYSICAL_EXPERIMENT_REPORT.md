# M1-02 P1 vs P2 HMAC Physical Design Experiment — Engineering Report

**Date:** 2026-11-15
**Repository:** `AmirSheikhloo/clinic-ecosystem`
**Branch:** `cursor/m102-p1-p2-hmac-physical-experiment-95a4`
**Base:** `origin/main` @ `fdae362e1a889831975060808ac612369d3b0d0a`
**Experiment commit SHA:** _(filled after push)_
**Classification:** `EXPERIMENTAL / PROPOSED / TESTED-IN-EPHEMERAL-PG15-ONLY / NOT APPROVED / NOT Package-1 / NOT Gate A`

## 0. Authority and non-claims

| Statement | Status |
|---|---|
| Frozen source `docs/FINAL_MASTER_SPECIFICATION_v3.0.1_FINAL.txt` clauses 771–772 | `SOURCE CONTRACT` (unchanged) |
| R4.12 roadmap / C0.4 contract files in this checkout | `NOT PRESENT in repository tree` — referenced by handoff docs only; treated as `REVIEW CANDIDATE / UNAVAILABLE LOCALLY` |
| Option C migration numbering | `NOT SELECTED / NOT APPROVED` |
| Official `TP0008+` migrations | `NOT CREATED` |
| Package-1 implementation / Gate A/B/C/D | `NOT AUTHORIZED / NOT CLAIMED` |
| Production keys, patient data, persistent target DB | `NOT ACCESSED` |
| Prior CI runs 72/75/77 | `HISTORICAL SPIKES ONLY` — do not prove HMAC Phase-6 generation design |

## 1. Source inspection (verified)

### 1.1 Clause 771–772 (frozen)

HMAC rotation requires nine phases including dual-write, drain, backfill, `CREATE UNIQUE INDEX CONCURRENTLY` in a dedicated autocommit Alembic revision, `pg_index.indisvalid` remediation, cutover with rollback window, and later contraction/key retirement. Dual-write must compute old/new indexes from the same canonical source in one write transaction; old writers must be drained; partial/failed concurrent indexes must be remediated before cutover.

### 1.2 TP0002 indexes (implemented on `main`)

```sql
CREATE UNIQUE INDEX uq_person_identifier_active_lookup
ON person_identifiers (tenant_id, id_type, issuing_country_or_authority, lookup_hmac_active);

CREATE UNIQUE INDEX uq_person_identifier_next_lookup
ON person_identifiers (tenant_id, id_type, issuing_country_or_authority, lookup_hmac_next)
WHERE lookup_hmac_next IS NOT NULL;
```

TP lineage on `main` ends at `TP0007`. Control Plane versions directory remains `.gitkeep` only in source.

### 1.3 Prior CI evidence (re-checked, not re-counted as new unique proof)

| Run | SHA | Result | Limitation |
|---|---|---|---|
| [43747042672](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/43747042672) | `a49171a` | success / 72 passed | Foundations preflight |
| [43747538019](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/43747538019) | `4039293` | success / 75 passed | Duplicate next-index spike on empty table |
| [43748254928](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/43748254928) | `8a13097` | success / 77 passed | Existing next-index only; no deterministic TX barrier |

## 2. Experimental physical models (PROPOSED)

### 2.1 P1 — staged generation columns

Additive columns on `person_identifiers`:

- `exp_lookup_hmac_gen2` / `exp_hmac_key_version_gen2`
- `exp_lookup_hmac_gen3` / `exp_hmac_key_version_gen3`
- pairing CHECKs

Phase-6 candidate indexes (nonredundant vs TP0002 next):

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

### 2.2 P2 — generation sidecar

Table `person_identifier_hmac_generations_exp` with denormalized `(id_type, issuing_country_or_authority)`, `hmac_key_version`, `lookup_hmac`, `generation_status ∈ {ACTIVE,NEXT,CANDIDATE,RETIRED}`, FK to `person_identifiers`, FORCE RLS mirror of tenant runtime/migrator policies.

```sql
CREATE UNIQUE INDEX CONCURRENTLY uq_exp_p2_hmac_candidate_lookup
ON public.person_identifier_hmac_generations_exp (
  tenant_id, id_type, issuing_country_or_authority, lookup_hmac
) WHERE generation_status = 'CANDIDATE';
```

### 2.3 Phase gate metadata

Table `m102_exp_rotation_phase_meta` enforces one-step phase advances and fail-closed experimental `upgrade head`. Phase 9 is dry-run only (`phase9_operational_executed = FALSE`).

## 3. Tests implemented

Runtime experimental package: `experiments/m102_hmac_physical/`
Integration tests:

- `tests/integration/test_m102_p1_physical_experiment.py`
- `tests/integration/test_m102_p2_physical_experiment.py`
- `tests/integration/test_m102_fresh_upgrade_and_package2_guard.py`

Unit contracts: `tests/unit/test_m102_p1_p2_experiment_contracts.py`
Workflow: `.github/workflows/m102-p1-p2-physical-experiment.yml`

## 4. Requirement matrix (filled after CI)

| Requirement | P1 | P2 | Notes |
|---|---|---|---|
| Compatibility with `person_identifiers` | _pending CI_ | _pending CI_ | |
| Preserve TP0002 active/next indexes | _pending CI_ | _pending CI_ | |
| Nonredundant physical generation index | _pending CI_ | _pending CI_ | |
| `CREATE UNIQUE INDEX CONCURRENTLY` on populated tables | _pending CI_ | _pending CI_ | |
| Deterministic two-session TX barrier conflicts | _pending CI_ | _pending CI_ | |
| Invalid-index detect/cleanup/retry | _pending CI_ | N/A (shared probe) | |
| Resumable backfill + rollback | _pending CI_ | _pending CI_ | |
| Two consecutive rotation cycles | _pending CI_ | _pending CI_ | |
| Roles / RLS / Cloud+Local | _pending CI_ | _pending CI_ | |
| Fresh install vs upgrade | _pending CI_ | expand covered | |
| Phase gate / unsafe head | _pending CI_ | meta shared | |
| Package-2 / deferred Phase-9 impact | PASS (static) | PASS (static) | no TP0008+/TP0011 invented |

## 5. CI evidence

_Pending first push of this branch._

## 6. Comparison and recommendation

_Pending CI results. Recommendation will be marked **PROPOSED** only._

## 7. Remaining blockers

See final section after CI. No Package-1 authorization is implied by this experiment.

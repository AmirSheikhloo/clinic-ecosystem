# M102 F2-B E0.5 — Final Consolidated Report

**Status:** `E05_FORENSIC_GATES_PASSED_PENDING_EXTERNAL_AUDIT`  
**Contract:** `M102_F2B_E0.5_FAIL_CLOSED_FORENSIC_ACCEPTANCE_CONTRACT_R0.1_PROPOSED.md`  
**Approval status:** APPROVED-AND-VERIFIED (new separate PO grant; hashes matched)  
**Delivery UTC:** 2026-11-18T18:46:24Z  
**Grant termination:** This report delivery terminates **this** E0.5 execution permission.

---

## 1. Authorization

**New separate PO grant** (2026-11-18 ~18:42Z) for bounded E0.5 fail-closed forensic acceptance.  
A prior terminated E0.5 grant on `experiment/m102-f2b-e05-20261118-f1b1173` (historical CI `44322975094`) confers **no** authority and is **out of this grant’s CI budget**.

| Document | SHA-256 |
|---|---|
| E0.5 technical contract | `6cc9be44ded30170266427f669c1b159bee0d8b27c7ab2fcfecd8735271df783` |
| D0.1 execution instrument | `15712f73fa02cb589109645ade6be700c5bd0ab9832d23e2286dba1fc86b4ec3` |
| Handoff ZIP (transport) | `9d6a91f60c9f9fc33d96bae1d741151a2e93b040a937d4eabd736c98e0c7de64` |

**CI mode:** push-only; max 1 initial + 1 non-security corrective.  
**Cutoff:** earlier of this report or `2026-12-04T22:59:00Z`.  
**Not authorized / not claimed:** F2-B approval, Package 1, ACR, Gates A–D, production readiness, real Sync, E5-E independent audit PASS.

---

## 2. Source provenance

| Item | Value |
|---|---|
| Repository | `https://github.com/AmirSheikhloo/clinic-ecosystem` |
| Base / parent | `f1b11731590fe29a294f86cf7cf5b64878d8ec7d` (E0.4 final evidence; parent tested `8d015959…`) |
| Branch | `experiment/m102-f2b-e05-20261118-1842-f1b1173` |
| Tested commit | `8652686f41f6420a7afe97e84b5f8f151c2a15bb` |
| Frozen spec blob | `befde437b6f951e1da71fdb4f0e61d043049c168` |
| R4.15 | REVIEW CANDIDATE (not approved production baseline) |
| Equivalence ledger | `evidence/E05_SOURCE_EQUIVALENCE_LEDGER.json` |

### Allowlisted changed paths (base → tested)

Only:

- `.github/workflows/m102-f2b-bounded-e05.yml`
- `experiments/m102_f2b_bounded_e05/**`

Pre-SQL full-range allowlist guard passed. Prior e05 branch was not modified.

---

## 3. CI attempts (this grant only)

| Attempt | Run | SHA | Event | Result |
|---|---|---|---|---|
| 1 (initial, final) | [44372870212](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/44372870212) | `8652686f41f6420a7afe97e84b5f8f151c2a15bb` | push | **success** |

Job: `135044107357` — Disposable PG15 E0.5 forensic suite  
Artifact: `m102-f2b-e05-evidence` (id `14459202886`)  
PostgreSQL: `server_version_num=150020`  
Workflow: `permissions: contents: read`; no PR/dispatch; evidence path-excluded.

**Corrective attempt not used.** Remaining budget forfeited on report termination.

---

## 4. Distinguishing metrics (mandatory)

### A. CI / pytest execution metric (observed)

- Pytest functions: **32** collected / **32** passed / **0** failed / **0** skipped  
- Label: `E05_CI_GREEN_SELF_REPORTED` (provider success; not full forensic sufficiency alone)

### B. Forensic acceptance metric (self-verifier, observed)

- Post-pytest forensic verifier: **ok=true**, `require_acceptance_pass=true`, errors=[]  
- Primary case manifest SHA-256: `2f735ce09bd84f2edf69b2b9cee8f621479390982c7f1794449951e8cab33423`  
- Post-seal verifier: **ok=true**, errors=[]  
- Auxiliary manifest SHA-256: `ef2c69eed3832a70a5b5fcbfc9a7b2b49ca1e4c1ff5abf359694db9647e61e49`  
- Root digests: `self_hashed=false`, independent verification `PENDING`  
- Label: `E05_FORENSIC_GATES_PASSED_PENDING_EXTERNAL_AUDIT`

### C. Independent external verification (E5-E)

- **NOT PERFORMED** under this grant.  
- `independently_verified=false` in seal record.  
- Must not be conflated with (A) or (B).

---

## 5. Contract metric — 19 inherited case IDs (current-run)

All 19 `E03-*` IDs: **OBSERVED_PASS** (bound to run `44372870212`, SHA `8652686…`).  
Historical E0.3/E0.4/prior-E0.5 records remain immutable; this report does not rewrite them.

---

## 6. Contract metric — 14 retained E04 validator fixtures

All `E04-V01` … `E04-V14`: **OBSERVED_PASS** (real-gate invocations on disposable trees; not additional physical PG15 cases).

---

## 7. E05-FC01..FC10 predicates

All ten predicates enforced by acceptance/seal gates in this run (status acceptance, ID/finding/kind map, CI lineage, types/UTC, path safety, nested redaction, real-gate fixtures, dual manifests, JUnit/19/14 cross-bind, distinct CI vs self-verifier vs independent states with E5-E PENDING).

---

## 8. Cleanup and limitations

- Hosted Actions ephemeral Postgres disposed with job end (platform-owned).  
- Synthetic `exp_e03_*` roles/tables only; no official `TP*` / `migrations/**` / `src/**` writes.  
- Residual: GitHub manual re-run not cryptographically revocable by workflow alone.  
- **Independent read-only audit: NOT YET PERFORMED** (E5-E pending).

---

## 9. Open dependencies (unchanged)

Real Cloud/Local Sync; official multi-head Tenant Alembic/ACR; production Phase-6/8 writer lifecycle; Package 1; Gates A–D; SRC-10/SRC-12.

---

## 10. Final classification

**`E05_FORENSIC_GATES_PASSED_PENDING_EXTERNAL_AUDIT`**

Observed CI success and self-reported forensic gates passed on disposable PG15 for this synthetic scope.  
This is **not** `E05_SYNTHETIC_FORENSIC_EVIDENCE_SUFFICIENT_FOR_GOVERNANCE_REVIEW` until a separate independent audit verifies immutable CI artifacts and sources.  
**Explicit non-claims:** F2-B not approved; Package 1 not authorized; no ACR; no Gate A–D acceptance; not production-ready; E5-E not completed.

---

## 11. Next Product Owner action (exactly one)

**Commission an independent read-only audit of CI run `44372870212`, tested SHA `8652686…`, primary manifest `2f735ce0…`, auxiliary manifest `ef2c69ee…`, artifact `14459202886`, and this final report—without authorizing new code, CI, Package 1, or F2-B.**

---

=== END OF E0.5 FINAL CONSOLIDATED REPORT ===

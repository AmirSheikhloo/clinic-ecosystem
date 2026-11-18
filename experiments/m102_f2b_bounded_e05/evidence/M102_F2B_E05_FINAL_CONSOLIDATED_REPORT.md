# M102 F2-B E0.5 — Final Consolidated Report

**Status:** `E05_FORENSIC_GATES_PASSED_PENDING_EXTERNAL_AUDIT`  
**Contract:** `M102_F2B_E0.5_FAIL_CLOSED_FORENSIC_ACCEPTANCE_CONTRACT_R0.1_PROPOSED.md`  
**Approval status:** APPROVED-AND-VERIFIED (new separate PO grant; hashes matched)  
**Delivery UTC:** 2026-11-18T14:21:09Z  
**Grant termination:** This report delivery terminates E0.5 execution permission.

---

## 1. Authorization

**New separate PO grant** (2026-11-18) for bounded E0.5 fail-closed forensic acceptance. Not a reactivation of terminated E0.4.

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
| Branch | `experiment/m102-f2b-e05-20261118-f1b1173` |
| Tested commit | `db4ce755b8ef9696419855974a0be44edc240dac` |
| Frozen spec blob | `befde437b6f951e1da71fdb4f0e61d043049c168` |
| R4.15 | REVIEW CANDIDATE (not approved production baseline) |
| Equivalence ledger | `evidence/E05_SOURCE_EQUIVALENCE_LEDGER.json` |

### Allowlisted changed paths (base → tested)

Only:

- `.github/workflows/m102-f2b-bounded-e05.yml`
- `experiments/m102_f2b_bounded_e05/**`

Pre-SQL full-range allowlist guard passed.

---

## 3. CI attempts

| Attempt | Run | SHA | Event | Result |
|---|---|---|---|---|
| 1 (initial, final) | [44322975094](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/44322975094) | `db4ce755b8ef9696419855974a0be44edc240dac` | push | **success** |

Job: `134866598408` — Disposable PG15 E0.5 forensic suite  
Artifact: `m102-f2b-e05-evidence` (id `14434899257`)  
PostgreSQL: `server_version_num=150020`  
Workflow: `permissions: contents: read`; no PR/dispatch; evidence path-excluded.

**Corrective attempt not used.** CI budget remaining unused = 1 (forfeited on report termination).

---

## 4. Distinguishing metrics (mandatory)

### A. CI / pytest execution metric (observed)

- Pytest functions: **32** collected
- Passed: **32**
- Failed: **0**
- Skipped: **0**
- Label: `E05_CI_GREEN_SELF_REPORTED` (provider success; not full forensic sufficiency alone)

### B. Forensic acceptance metric (self-verifier, observed)

- Post-pytest forensic verifier: **ok=true**, errors=[]
- Require acceptance pass: **true** (E05-FC01 enforced)
- Primary case manifest SHA-256: `f5c9ea3993298e0e12589f4c9093e5db2483c4606d6fe28b5396c2b2ab131680` (19 entries)
- Post-seal verifier: **ok=true**, errors=[]
- Auxiliary manifest SHA-256: `7f439e7bcf2d775f208c02c22bb2c9ec6bd8fbee4c5baa851ef165bb38b773b6`
- Root digests: `EVIDENCE_ROOT_DIGESTS.json` (`self_hashed=false`, independent verification `PENDING`)
- Label: `E05_FORENSIC_GATES_PASSED_PENDING_EXTERNAL_AUDIT`

### C. Independent external verification (E5-E)

- **NOT PERFORMED** under this grant.
- `independently_verified=false` in seal record.
- Must not be conflated with (A) or (B).

---

## 5. Contract metric — 19 inherited case IDs (current-run)

| Case ID | Kind | Classification |
|---|---|---|
| E03-A01-P01 | PHYSICAL_PG15 | OBSERVED_PASS |
| E03-A01-N01 | PHYSICAL_PG15 | OBSERVED_PASS |
| E03-A02-N01 | PHYSICAL_PG15 | OBSERVED_PASS |
| E03-A02-P01 | PHYSICAL_PG15 | OBSERVED_PASS |
| E03-A02-N02 | PHYSICAL_PG15 | OBSERVED_PASS |
| E03-A03-P01 | PHYSICAL_PG15 | OBSERVED_PASS |
| E03-A03-N01 | PHYSICAL_PG15 | OBSERVED_PASS |
| E03-A04-P01 | PHYSICAL_PG15 | OBSERVED_PASS |
| E03-A04-N01 | PHYSICAL_PG15 | OBSERVED_PASS |
| E03-A05-C01 | GOVERNANCE_CONTROL | OBSERVED_PASS |
| E03-A06-P01 | PHYSICAL_PG15 | OBSERVED_PASS |
| E03-A06-N01 | PHYSICAL_PG15 | OBSERVED_PASS |
| E03-A06-N02 | PHYSICAL_PG15 | OBSERVED_PASS |
| E03-A07-C01 | GOVERNANCE_CONTROL | OBSERVED_PASS (staged; no circular missing-self) |
| E03-A07-C02 | GOVERNANCE_CONTROL | OBSERVED_PASS |
| E03-A08-N01 | GOVERNANCE_CONTROL | OBSERVED_PASS |
| E03-A08-P01 | GOVERNANCE_CONTROL | OBSERVED_PASS |
| E03-REG-P01 | PHYSICAL_PG15 | OBSERVED_PASS |
| E03-CLOSE-C01 | GOVERNANCE_CONTROL | OBSERVED_PASS |

Historical E0.3/E0.4 records remain immutable; this report does not rewrite them.

---

## 6. Contract metric — 14 retained E04 validator fixtures

All `E04-V01` … `E04-V14`: **OBSERVED_PASS** (disposable copies / real-gate invocations; not additional physical PG15 cases).

Semantic hardenings exercised:

- V03/V04/V08/V13/V14 call the production-equivalent `verify_case_manifest` / `ci_gate_sequence` entrypoints
- V08 injects `OBSERVED_FAIL` with freshly valid rehash → acceptance denial (E05-FC01)
- V14 requires primary manifest existence (no `or True` bypass)

---

## 7. E05-FC01..FC10 predicates (summary)

| Predicate | Result (self-verifier) |
|---|---|
| E05-FC01 status acceptance | OBSERVED_PASS required for all 19; FAIL/BLOCKED/etc denied |
| E05-FC02 ID/finding/kind map | basename ↔ case_id ↔ finding ↔ kind enforced |
| E05-FC03 CI lineage | SHA/run/attempt/contract/E0.2–E0.4 parents bound |
| E05-FC04 types/UTC/evidence | typed fields, UTC, nonempty observed_result on PASS |
| E05-FC05 paths | allowlisted relative regular files; no traversal/symlink |
| E05-FC06 nested redaction | recursive secret scan; sentinel not echoed |
| E05-FC07 real-gate fixtures | V03/V04/V13/V14 invoke actual verifier/orchestrator |
| E05-FC08 dual manifests | primary + auxiliary + root digests; no self-hash |
| E05-FC09 cross-bind | 32 pytest / 19 JSON / 14 fixtures / CI success |
| E05-FC10 verification states | CI / self-verifier / independent kept distinct; E5-E PENDING |

---

## 8. Cleanup and limitations

- Hosted Actions ephemeral Postgres disposed with job end (platform-owned).
- Synthetic `exp_e03_*` roles/tables only; no official `TP*` / `migrations/**` / `src/**` writes.
- Residual: GitHub manual re-run cannot be cryptographically revoked by workflow alone (governance ban recorded).
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

**Commission an independent read-only audit of CI run `44322975094`, tested SHA `db4ce755…`, primary manifest `f5c9ea39…`, auxiliary manifest `7f439e7b…`, artifact `14434899257`, and this final report—without authorizing new code, CI, Package 1, or F2-B.**

---

=== END OF E0.5 FINAL CONSOLIDATED REPORT ===

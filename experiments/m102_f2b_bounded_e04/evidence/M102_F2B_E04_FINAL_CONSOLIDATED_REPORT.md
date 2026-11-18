# M102 F2-B E0.4 — Final Consolidated Report

**Status:** `E04_CI_AND_FORENSIC_CHECKS_PASSED_PENDING_INDEPENDENT_AUDIT`  
**Contract:** `M102_F2B_E0.4_FORENSIC_EVIDENCE_RECONCILIATION_CONTRACT_R0.1_PROPOSED.md`  
**Approval status:** APPROVED-AND-VERIFIED (new separate PO grant; hashes matched)  
**Delivery UTC:** 2026-11-18T11:25:38Z  
**Grant termination:** This report delivery terminates E0.4 execution permission.

---

## 1. Authorization

**New separate PO grant** (2026-11-18) replacing the prior G0-blocked attempt (which had terminated). Not a reactivation of the terminated task.

| Document | SHA-256 |
|---|---|
| E0.4 technical contract | `8dbb6b774e7baa532fb424aa7260b0439f3fed10c0575061b546757199ca04e3` |
| D0.1 execution instrument | `27e576be6f297691c59150c44b97d04829a8117a622ba5c56d51e8bc8c1d53a9` |
| Handoff ZIP | `6532dbf0832ea34abd37db03570de410a73bb48c67539bbc8f15ceaacb87e5a9` |

**CI mode:** push-only; max 1 initial + 1 non-security corrective.  
**Cutoff:** earlier of this report or `2026-11-30T22:59:00Z`.  
**Not authorized / not claimed:** F2-B approval, Package 1, ACR, Gates A–D, production readiness, real Sync.

---

## 2. Source provenance

| Item | Value |
|---|---|
| Repository | `https://github.com/AmirSheikhloo/clinic-ecosystem` |
| Base / parent | `0145b3fd114a022dd004a3a36be43a9a0994a9b5` (E0.3 final evidence; parent `3c63e938…`) |
| Branch | `experiment/m102-f2b-e04-20261118-0145b3fd` |
| Tested commit | `8d015959ec6b2570da74d63d8f7ee0e88d1cff64` |
| Frozen spec blob | `befde437b6f951e1da71fdb4f0e61d043049c168` |
| E0.3 test blob (at base) | `686f1411f3c9ec3f894dce74f022b408101a6e45` |
| E0.3 evidence.py blob | `95c6c8608944903550c0638eda18c6fbc5f993e1` |
| R4.15 | REVIEW CANDIDATE (not approved production baseline) |
| Equivalence ledger | `evidence/E04_SOURCE_EQUIVALENCE_LEDGER.json` |

### Allowlisted changed paths (base → tested)

Only:

- `.github/workflows/m102-f2b-bounded-e04.yml`
- `experiments/m102_f2b_bounded_e04/**`

Pre-SQL full-range allowlist guard passed on both CI attempts.

---

## 3. CI attempts

| Attempt | Run | SHA | Event | Result |
|---|---|---|---|---|
| 1 (initial) | [44293883965](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/44293883965) | `2a561cb…` | push | **failure** — 4 failed / 28 passed (non-security: stale e03 branch string in A05) |
| 2 (corrective, final) | [44294184379](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/44294184379) | `8d015959ec6b2570da74d63d8f7ee0e88d1cff64` | push | **success** |

Job: `134766795665` — Disposable PG15 E0.4 forensic suite  
Artifact: `m102-f2b-e04-evidence`  
PostgreSQL: `server_version_num=150020`  
Workflow: `permissions: contents: read`; no PR/dispatch; evidence path-excluded.

**CI budget exhausted (1+1).** No further runs authorized.

---

## 4. Execution metric vs contract metric

### Execution metric (attempt 2)

- Pytest functions: **32** collected
- Passed: **32**
- Failed: **0**
- Skipped: **0**
- Post-pytest forensic verifier: **ok=true**, errors=[]
- Case digest manifest SHA-256: `af8ce95a77931bc5f57934f6082e833136ed7c14fc607fe1abd521ab2ed5d765` (19 entries)

### Contract metric — 19 inherited case IDs (current-run)

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

Historical E0.3 attempt-2 `E03-A07-C01=OBSERVED_FAIL` remains immutable history; this report does not rewrite it.

### Contract metric — 14 E0.4 validator fixtures

All `E04-V01` … `E04-V14`: **OBSERVED_PASS** (disposable copies / governance controls; not additional physical PG15 cases).

---

## 5. Forensic gate

- Staged C01 protocol (§5.1): peers validated → in-memory candidate → write C01 → external 19-file manifest → independent post-pytest read-back verifier.
- Verifier result: `POST_PYTEST_FORENSIC_VERIFIER.json` (`ok: true`).
- Manifest does not self-hash; case JSON files do not embed their own digests.
- Trusted identity: `run_id=44294184379`, `tested_commit_sha=8d015959ec6b2570da74d63d8f7ee0e88d1cff64` bound in case evidence.

---

## 6. Cleanup and limitations

- Hosted Actions ephemeral Postgres disposed with job end (platform-owned).
- Synthetic `exp_e03_*` roles/tables only; no official `TP*` / `migrations/**` / `src/**` writes.
- Residual: GitHub manual re-run cannot be cryptographically revoked by workflow alone (governance ban recorded).
- **Independent read-only audit: NOT YET PERFORMED** (E4-E pending).

---

## 7. Open dependencies (unchanged)

Real Cloud/Local Sync; official multi-head Tenant Alembic/ACR; production Phase-6/8 writer lifecycle; Package 1; Gates A–D; SRC-10/SRC-12.

---

## 8. Final classification

**`E04_CI_AND_FORENSIC_CHECKS_PASSED_PENDING_INDEPENDENT_AUDIT`**

Observed CI/pytest/forensic gates passed on disposable PG15 for this synthetic scope.  
This is **not** `E04_FORENSIC_EVIDENCE_SUFFICIENT_FOR_GOVERNANCE_REVIEW` until a separate independent audit verifies immutable CI artifacts and sources.  
**Explicit non-claims:** F2-B not approved; Package 1 not authorized; no ACR; no Gate A–D acceptance; not production-ready.

---

## 9. Next Product Owner action (exactly one)

**Commission an independent read-only audit of CI run `44294184379`, tested SHA `8d015959…`, the 19-case digest manifest `af8ce95a…`, and this final report—without authorizing new code, CI, Package 1, or F2-B.**

---

=== END OF E0.4 FINAL CONSOLIDATED REPORT ===

# M102 F2-B E0.3 — Final Consolidated Report

**Status:** `CORRECTIVE_EVIDENCE_INCOMPLETE`  
**Contract:** `M102_F2B_CORRECTIVE_EVIDENCE_AND_GOVERNANCE_CONTRACT_E0.3_PROPOSED.md`  
**Approval status:** APPROVED-AND-VERIFIED (hashes matched)  
**Delivery UTC:** 2026-11-17T15:20:14Z  
**Grant termination:** This report delivery terminates E0.3 execution permission.

---

## 1. Authorization quotation and boundaries

**PO approval record** `M102_F2B_E0.3_PO_APPROVAL_RECORD.md`  
SHA-256 `784e4b63348ef4b6bf39a300964a5ea30d0448a911d1a49c7ceb0ae52df3129f`

Verified PO-approved document digests:

| Document | SHA-256 |
|---|---|
| E0.3 contract | `b5f8d33a33ff25e398cb75be76bebfab02a32cf8386e04b1e46f6cecc89ecb28` |
| D0.1 execution authorization | `4e8a8f5f25649bc263af68f72e897313366b77320c47401f0c6ea3fc5f87a643` |
| E0.2 independent audit A0.1 (historical) | `9c5f8947a52c8750fbfaa5a798dfee88069f9d64f8e76840b225e12a057b758f` |

**Authorized CI mode (adopted):** branch-restricted `push` only; no PR; max **1 initial + 1 corrective** non-security attempt.  
**Expiry:** earlier of this final report **or** `2026-11-27T22:59:00Z`.  
**E0.2 grant:** terminated / historical only. E0.2 green tests did **not** close A01–A08.

**Not authorized / not claimed:** F2-B approval, Package 1, official `TP0008+`, ACR, Gates A–D, real Cloud/Local Sync proof, production DB access.

---

## 2. Source provenance

| Item | Value |
|---|---|
| Repository | `https://github.com/AmirSheikhloo/clinic-ecosystem` |
| Parent (E0.2 final evidence commit) | `471f88417bfcf69ce864b333114e7fb0f777ede0` |
| E0.3 branch | `experiment/m102-f2b-e03-20261117-471f884` |
| Tested commit (CI attempt 2) | `3c63e93846e7a79e6700414ab891fc5e3d983427` |
| Frozen spec blob SHA | `befde437b6f951e1da71fdb4f0e61d043049c168` (`docs/FINAL_MASTER_SPECIFICATION_v3.0.1_FINAL.txt`, clauses 771–772 read) |
| R4.15 upload SHA-256 | `ab2321398cb235f03df4b641948a19b5c696874c6edaae133c0883dc97299eb9` |
| R4.15 status | `REVIEW CANDIDATE` / F2-B **PROPOSED, NOT APPROVED** (§§11.8–11.9) |
| Historical E0.2 tested SHA | `e1897078076296c771a7caedb97dc75b2b28db22` (run `43952295235`) — historical only |
| Local Docker | ABSENT → CI disposable `postgres:15` used |

### Changed-path manifest (parent → tested)

Only allowlisted paths:

- `.github/workflows/m102-f2b-bounded-e03.yml`
- `experiments/m102_f2b_bounded_e03/**`

Full `git diff --name-status` allowlist guard executed in CI **before SQL** (step success on both runs).

---

## 3. CI attempts (exhausted)

| Attempt | Run | SHA | Event | Pytest | Classification |
|---|---|---|---|---|---|
| 1 (initial) | [44111930395](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/44111930395) | `29b6220…` | `push` | 9 failed / 9 passed / 0 skipped | NON_SECURITY_HARNESS (`autocommit_block` TX + A03 barrier deadlock) |
| 2 (corrective, final authorized) | [44112675849](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/44112675849) | `3c63e93846e7a79e6700414ab891fc5e3d983427` | `push` | **1 failed / 17 passed / 0 skipped** | NON_SECURITY_HARNESS (A07-C01 self-file ordering) |

**No further CI attempt is authorized.** Job `1341…` artifact: `m102-f2b-e03-evidence`.  
PostgreSQL: `server_version_num=150020` (15.20).  
Workflow: push-only; `permissions: contents: read`; path filters exclude `evidence/**`; no `pull_request` / `workflow_dispatch` / secrets / deploy.

Residual limitation: GitHub manual re-run cannot be technically revoked by the workflow alone (recorded per E0.3 §7).

---

## 4. Execution metric vs contract metric

### Execution metric (CI attempt 2)

- Collected pytest functions: **18**
- Passed: **17**
- Failed: **1** (`test_e03_zz_a07_c01_evidence_schema`)
- Skipped: **0**
- PG15: **150020**
- Logs: `evidence/pytest.txt`, `evidence/junit.xml`, `evidence/summary.txt`

### Contract metric (19 case IDs)

| Case ID | Finding | Kind | Classification (CI record) |
|---|---|---|---|
| E03-A01-P01 | A01 | PHYSICAL_PG15 | OBSERVED_PASS |
| E03-A01-N01 | A01 | PHYSICAL_PG15 | OBSERVED_PASS |
| E03-A02-N01 | A02 | PHYSICAL_PG15 | OBSERVED_PASS |
| E03-A02-P01 | A02 | PHYSICAL_PG15 | OBSERVED_PASS (`attnotnull=true`, `convalidated=true`) |
| E03-A02-N02 | A02 | PHYSICAL_PG15 | OBSERVED_PASS |
| E03-A03-P01 | A03 | PHYSICAL_PG15 | OBSERVED_PASS (overlapping TX; loser SQLSTATE 23505) |
| E03-A03-N01 | A03 | PHYSICAL_PG15 | OBSERVED_PASS (stale/unknown fence) |
| E03-A04-P01 | A04 | PHYSICAL_PG15 | OBSERVED_PASS (synthetic admission ALLOW) |
| E03-A04-N01 | A04 | PHYSICAL_PG15 | OBSERVED_PASS (DENY before mutation) |
| E03-A05-C01 | A05 | GOVERNANCE_CONTROL | OBSERVED_PASS (push-only workflow audit; run `44112675849`) |
| E03-A06-P01 | A06 | PHYSICAL_PG15 | OBSERVED_PASS (role before/inside/after autocommit) |
| E03-A06-N01 | A06 | PHYSICAL_PG15 | OBSERVED_PASS (invalid index + repair) |
| E03-A06-N02 | A06 | PHYSICAL_PG15 | OBSERVED_PASS (GRANT/ALTER/RLS negatives) |
| E03-A07-C01 | A07 | GOVERNANCE_CONTROL | **OBSERVED_FAIL** (self-referential missing-file check) |
| E03-A07-C02 | A07 | GOVERNANCE_CONTROL | OBSERVED_PASS (19-row G2 preflight manifest) |
| E03-A08-N01 | A08 | GOVERNANCE_CONTROL | OBSERVED_PASS (injected path denials) |
| E03-A08-P01 | A08 | GOVERNANCE_CONTROL | OBSERVED_PASS (full-range diff allowlist) |
| E03-REG-P01 | REG | PHYSICAL_PG15 | OBSERVED_PASS |
| E03-CLOSE-C01 | CLOSE | GOVERNANCE_CONTROL | OBSERVED_PASS |

**Offline post-hoc schema recheck** (`POST_HOC_EVIDENCE_SCHEMA_RECHECK.json`): all 19 JSON files present with required §6 fields; **schema_errors=[]**. This does **not** convert A07-C01 to PASS or authorize another CI run.

---

## 5. A01–A08 disposition

| Finding | Disposition under this grant |
|---|---|
| A01 fail-closed SET ROLE | Physical evidence PASS (P01+N01) |
| A02 real NOT NULL + CHECK | Physical evidence PASS (N01/P01/N02) |
| A03 overlapping writers + fence | Physical evidence PASS (P01+N01) |
| A04 admission decision | Physical synthetic PASS (P01+N01); **not** real Sync |
| A05 CI governance mode | PASS for adopted push-only mode; CI job nevertheless red on attempt 2 |
| A06 autocommit / invalid index / privs | Physical evidence PASS |
| A07 evidence schema integrity | **INCOMPLETE** — C02 PASS; **C01 FAIL** in CI |
| A08 full-range allowlist | PASS |

Independent post-run audit: **NOT PERFORMED**.

---

## 6. Cleanup and privilege isolation

- Hosted Actions ephemeral Postgres service disposed with job end (platform-owned).
- Experiment roles/objects namespaced `exp_e03_*`; no official `TP*` / `migrations/**` / `src/**` writes.
- No production DSN/secrets used.
- Evidence digests: `evidence/EVIDENCE_SHA256SUMS.txt`.

---

## 7. Open dependencies (unchanged)

- Real Cloud/Local Sync and admission (SRC application behavior)
- Official Tenant Alembic multi-head runner/ACR
- Production Phase-6/8 + offline writer lifecycle
- Formal governance: Package 1, Gates A–D, SRC-10/SRC-12

---

## 8. Final classification

**`CORRECTIVE_EVIDENCE_INCOMPLETE`**

Reasons:

1. Authorized CI budget exhausted (1+1); attempt 2 job **failed** (1 pytest failure).
2. Case **E03-A07-C01** remains `OBSERVED_FAIL` in the immutable CI-written evidence record.
3. Independent audit of E0.3 evidence has **not** occurred.
4. Therefore **`CORRECTIVE_EVIDENCE_SUFFICIENT_FOR_GOVERNANCE_REVIEW` is not claimed**, even though 18/19 CI case records are `OBSERVED_PASS` and offline schema recheck is clean.

**Explicit non-claims:** F2-B not approved; Package 1 not authorized; no Gate A–D acceptance; no official migration authority.

---

## 9. Next Product Owner action (exactly one)

**Authorize a separate, narrowly scoped follow-up (new D0.x/E0.x grant) solely to repair and re-prove E03-A07-C01 evidence-schema self-validation and obtain one clean CI completion + independent audit—or formally accept the current incomplete package and keep F2-B blocked.**

---

=== END OF E0.3 FINAL CONSOLIDATED REPORT ===

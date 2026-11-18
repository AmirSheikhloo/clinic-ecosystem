# M102 F2-B E0.7 — Final Consolidated Report (TERMINAL FAILED)

**Status:** `E07_EVIDENCE_INCOMPLETE`  
**Task status:** `FAILED`  
**Contract:** `M102_F2B_E0.7_CONSOLIDATED_FORENSIC_HARNESS_CLOSURE_CONTRACT_R0.3_PROPOSED.md`  
**Approval status:** APPROVED-AND-VERIFIED (NEW separate PO grant; hashes matched)  
**Delivery UTC:** 2026-11-18T21:13:33Z  
**Grant termination:** This terminal report delivery terminates **this** E0.7 execution permission. CI budget 1+1 is exhausted; no third attempt.

---

## 1. Authorization

| Document | SHA-256 |
|---|---|
| E0.7 technical contract R0.3 | `a9fbaf3edba705159d327dc292db71ac0072bd170d6010d868f6bf8690e7b32e` |
| D0.3 execution instrument | `ba099b0767548d7e32c33f146b4d183600030ff0a71430f66dbb5f308ff2d4a7` |
| Handoff ZIP | `35a2d36e95dab45648665e3a3975659906e36a3d86da11b471e5e938662fcc0e` |

**CI mode:** push-only; max 1 initial + 1 non-security corrective; `GITHUB_RUN_ATTEMPT==1`.  
**Cutoff:** earlier of this report or `2026-12-20T22:59:00Z`.  
**Not authorized / not claimed:** F2-B, Package 1, ACR, Gates A–D, PR/merge, E7-F PASS.

G0 hashes matched. G1 DAG recorded `PROVABLE_NONCIRCULAR`. G4 static audit passed before first push.

---

## 2. Source provenance

| Item | Value |
|---|---|
| Repository | `https://github.com/AmirSheikhloo/clinic-ecosystem` |
| Exact base | `36a0cebc67bda89e0942b0491d5bb2eff9745b04` |
| Branch | `experiment/m102-f2b-e07-20261118-36a0ceb` |
| Tested commit (final CI attempt) | `d0f8a352fdfedee001f2e3a08aa3b7817ab52dff` |
| Initial harness commit | `223f9e1c84f02299d7f807000476ee163ee51192` |
| Allowlist | `experiments/m102_f2b_bounded_e07/**`, `.github/workflows/m102-f2b-bounded-e07.yml` |
| Versions | five `exp_e03_*.py` byte-identical to E0.6 |

---

## 3. CI attempts (budget exhausted)

| Attempt | Run | SHA | Result |
|---|---|---|---|
| 1 (initial) | [44398524613](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/44398524613) | `223f9e1…` | **failure** — E04-V04 asserted legacy `"hash mismatch"` text; CLI correctly returned nonzero `PRIMARY_HASH_MISMATCH` (non-security fixture defect; corrected) |
| 2 (corrective, final) | [44398800080](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/44398800080) | `d0f8a35…` | **failure** — FC matrix validator: `DETECTOR_OR_RECEIPT_MISMATCH` for E05-FC05/FC06 |

- Attempt-2 job: `135135862474`
- Artifact: `m102-f2b-e07-evidence` id `14470918160`
- PostgreSQL: disposable PG15 service
- **No third push permitted.**

---

## 4. Distinguishing metrics

### A. CI / pytest (attempt 2, observed)

- Pytest: **32/32 passed**, 0 failed, 0 skipped on attempt 2  
- Label: partial `E07_CI_GREEN_SELF_REPORTED` for Step 1 only — **job overall FAILED** at Step 3

### B. Forensic self-verifier

- Step 2 primary seal+verify: **ok** on attempt 2  
- Step 3 FC matrix schema validation: **FAILED**  
- Steps 4–7 (closures, seal writer, zero-write post-seal): **NOT REACHED**  
- Label: `E07_EVIDENCE_INCOMPLETE`

### C. Independent E7-F

- **NOT PERFORMED** / **PENDING** — cannot be claimed from failed self-run

---

## 5. What passed on attempt 2 (partial)

- 19/19 E03 case JSONs written `OBSERVED_PASS` (current-run bound)  
- 14/14 E04 fixtures `OBSERVED_PASS` (after V04 assertion fix)  
- Exact 32 JUnit identities collected  
- Primary manifest written and primary_verify_cli exit 0  
- FC builder produced a 10-row / 12-vector matrix file and 24 process receipts, but **matrix_validator_cli rejected** it

---

## 6. Root cause of terminal FC failure (attempt 2)

In `harness/evidence.py` `verify_case_manifest` error classification:

```python
elif "timestamp" in e or "exit_code" in e or "postgres_server_version" in e or "must be structured":
```

The final clause is a **boolean always-true string**, missing `in e`. Consequently many real denials (including ownership and secret-pattern) were labeled `TYPE_OR_UTC` in CLI `error_codes`.

Observed stdout receipts from original provider artifact:

- FC05 negative: `error_codes: ["TYPE_OR_UTC"]` while message is `evidence_files must include own canonical path` (should be `EVIDENCE_OWNERSHIP`)
- FC06 primary-secret negative: `error_codes: ["TYPE_OR_UTC"]` while message is `potential secret patterns` (should be `SECRET_PATTERN`)

Matrix builder recorded `observed_detector` as the **expected** canonical code; `matrix_validator_cli` correctly required that detector appear in authentic stdout → `DETECTOR_OR_RECEIPT_MISMATCH`.

This is a **harness detector-provenance defect**. CI budget already consumed by the V04 corrective; **no further push is authorized**.

---

## 7. E05-FC / E07-C / seal status

| Control | Status |
|---|---|
| FC01–FC10 (12 vectors / 24 outcomes) | **INCOMPLETE** — matrix rejected; FC05/FC06 detector provenance failed |
| E07-C01..C07 | **NOT EXECUTED** (Step 4 skipped) |
| Frozen aux seal + zero-write post-seal | **NOT EXECUTED** (Steps 6–7 skipped) |
| External `/tmp` pre/post snapshot proof | **NOT EXECUTED** |

---

## 8. Limitations and non-claims

- Synthetic disposable PG15 only; no official `src/**` / `migrations/**` writes  
- No PR/merge  
- Not F2-B / Package 1 / ACR / Gates A–D  
- Not `E07_SYNTHETIC_FORENSIC_EVIDENCE_SUFFICIENT_FOR_GOVERNANCE_REVIEW`  
- E7-F independent audit cannot pass on incomplete evidence  
- SRC-10 / SRC-12 remain open  

---

## 9. Final classification

**`E07_EVIDENCE_INCOMPLETE` / `FAILED`**

Attempt 2 reached green pytest + primary verify but failed mandatory FC detector authentication. Budget 1+1 exhausted. Grant terminates on this report.

---

## 10. Next Product Owner action (exactly one)

**Decide whether to issue a NEW separate E0.7+ (or later) grant** to fix the `verify_case_manifest` detector classification bug (`"must be structured" in e`) and re-prove FC05/FC06 authentic detectors, 12-vector matrix acceptance, seven E07-C closures, and zero-write post-seal — without treating this failed grant as continuing authority. Do not authorize PR/merge, Package 1, or F2-B from this report.

---

=== END OF E0.7 FINAL CONSOLIDATED REPORT ===

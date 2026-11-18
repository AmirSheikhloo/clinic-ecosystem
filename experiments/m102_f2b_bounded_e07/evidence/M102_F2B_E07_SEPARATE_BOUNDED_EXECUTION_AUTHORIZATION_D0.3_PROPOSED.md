# Clinic Ecosystem — M102 F2-B E0.7 Separate Bounded Execution Authorization Instrument

**Document:** `M102_F2B_E07_SEPARATE_BOUNDED_EXECUTION_AUTHORIZATION_D0.3_PROPOSED.md`  
**Version:** `D0.3_PROPOSED`, 2026-11-19 UTC (supersedes `D0.2_PROPOSED` in document review only).  
**Status:** `REVIEW-ONLY / UNSIGNED / NOT AUTHORIZED`.  
**Technical contract:** `M102_F2B_E0.7_CONSOLIDATED_FORENSIC_HARNESS_CLOSURE_CONTRACT_R0.3_PROPOSED.md`  
**Exact contract SHA-256 (computed from complete final R0.3 bytes):** `a9fbaf3edba705159d327dc292db71ac0072bd170d6010d868f6bf8690e7b32e`. This pinned value is immutable for this D0.3 document. The D0.3 SHA-256 is computed externally from its completed bytes and MUST appear in any future separate PO approval envelope; it is not self-embedded.  
**No authority is granted by this instrument or a future joint document-review PASS.**

## 1. Authority and non-negotiable history

Frozen `docs/FINAL_MASTER_SPECIFICATION_v3.0.1_FINAL.txt` is authoritative. E0.6's terminal report ended the prior grant at `2026-11-18T19:41:28Z`. E0.6 E6-E independent audit is **NOT PASSED** with seven jointly confirmed findings (`E6A-01..E6A-07`). Preserve E0.6's real CI success (`44382487747`, tested SHA `56a08278c18659458f625b4b30fa68aa590b0f0b`), all 19/19 primary and 35/35 auxiliary SHA matches, 11/11 indirectly hash-bound stdout receipts and unchanged five inherited experimental migrations as historical evidence. No fabricated E0.7 CI or validation is allowed. R4.15 remains review candidate. F2-B, Package 1, ACR, Gates A–D remain unapproved/unexecuted for this experiment.

## 2. Proposed grant parameters — effective only after NEW explicit PO statement

| Field | Exact proposed value |
|---|---|
| Repository | `AmirSheikhloo/clinic-ecosystem` |
| Technical contract | `M102_F2B_E0.7_CONSOLIDATED_FORENSIC_HARNESS_CLOSURE_CONTRACT_R0.3_PROPOSED.md`; exact verified SHA-256 `a9fbaf3edba705159d327dc292db71ac0072bd170d6010d868f6bf8690e7b32e`; PO and Cursor MUST independently recompute and match this value |
| This D0.3 instrument | `M102_F2B_E07_SEPARATE_BOUNDED_EXECUTION_AUTHORIZATION_D0.3_PROPOSED.md`; SHA-256 independently computed on finalized `D0.3` bytes and stated verbatim by PO; do NOT embed its self-digest in this file |
| Source base | `36a0cebc67bda89e0942b0491d5bb2eff9745b04` (terminal E0.6 evidence-only commit) |
| Tested historical parent | `56a08278c18659458f625b4b30fa68aa590b0f0b` |
| New branch | exactly one `experiment/m102-f2b-e07-*` from pinned base |
| Write allowlist | `experiments/m102_f2b_bounded_e07/**` and `.github/workflows/m102-f2b-bounded-e07.yml` ONLY |
| CI budget | one initial push-triggered run + at most one conditional corrective push triggered by a **proven nonsecurity harness orchestration defect**; `GITHUB_RUN_ATTEMPT == 1`; no manual rerun/third attempt |
| Proposed UTC cutoff | **2026-12-20T22:59:00Z** or first terminal report delivery (whichever first) |
| Data and runtime | synthetic, disposable PostgreSQL 15, synthetic roles/credentials, no real patient data or production connectivity |
| Output | ONE complete evidence-grounded terminal consolidated report, possible evidence-only child commit if authorized; no PR or merge |

The PO grant MUST name both exact filenames (`R0.3_PROPOSED` and `D0.3_PROPOSED`) and both full independently verified SHA-256 hashes, pinned base, allowlist, attempt budget, UTC cutoff and scope. The R0.3 digest **already pinned above** must match the actual contract bytes; the separately calculated final D0.3 digest must match the PO statement. Neither digest may be substituted with the prior R0.1/R0.2 or D0.1/D0.2 digests. A ZIP upload, a Gemini/ChatGPT review PASS, or an earlier PO grant cannot substitute for these conditions. If an approval digest is absent, malformed or mismatched, return `BLOCKED_APPROVAL` and terminate with a truthful terminal report before writes.

## 3. Seven mandatory corrective closures (one scope, no dilution)

- `E6A-01` (`E07-C01`): rectify and reject every contradictory positive `expected_exit_code`; strict integer exit types (no bools); disposable negative proof via `matrix_validator_cli` -> `EXPECTED_EXIT_CONTRADICTION`.
- `E6A-02` (`E07-C02`): true **gate-specific** positives and negatives for all 10 FC IDs (**12 vector pairs / 24 actual subprocess exit results**; FC06 and FC09 each require two vectors)—including `FC06` (`primary_verify_cli` + `aux_redaction_readback_cli`), `FC07` (`ci_gate_sequence`), `FC08` (`aux_integrity_readback_cli`), `FC09` (`junit_and_fixture_identity_readback_cli`), and `FC10` (`root_identity_readback_cli`)—using the exact mandatory subgates composed by `post_seal_verify_cli`; separate actual process receipts for every FC; reject wrong gate family (`WRONG_GATE_FAMILY`).
- `E6A-03` (`E07-C03`): frozen canonical `finding_ids` JSON arrays; actual detector parsed from subprocess stdout `error_codes`, not copied expected strings; schema/receipt/log hash authenticating all twelve FC gate-vector proof pairs across ten predicate rows via `matrix_validator_cli` (`DETECTOR_OR_RECEIPT_MISMATCH`).
- `E6A-04` (`E07-C04`): strict all-14-fixture ID/filename/source/JUnit/full §2 lineage/run/SHA/attempt and negative receipt binding via `junit_and_fixture_identity_readback_cli`; disposable forged-fixture re-seal proof -> `FIXTURE_PROVENANCE_MISMATCH`.
- `E6A-05` (`E07-C05`): distinct manifest/root **writer** (`seal_writer_cli`) and **zero-write** final **read-only verifier** (`post_seal_verify_cli`), independently frozen policy-derived auxiliary inventory, and byte-for-byte pre/post `evidence/` tree snapshot equality verified using external `/tmp/` snapshots (zero writes inside `evidence/` during Step 7).
- `E6A-06` (`E07-C06`): seven prospective `E07-C01..C07` closure judgments written BEFORE seal (Step 4) alongside their disposable falsifiability receipts (`closure_receipts/E07-C*.json` + `.stdout.txt`), included directly in original provider artifact and auxiliary manifest, with truthful `SELF_TESTED_PENDING_FINAL_GATE_AND_EXTERNAL_AUDIT` status; negative proof via `closure_judgments_validator_cli` -> `CLOSURE_JUDGMENT_INVALID`; historical six E06-EV records stay immutable.
- `E6A-07` (`E07-C07`): exact complete policy-derived auxiliary name set including every required stable FC receipt `.json` and redacted `.stdout.txt`, every E07 closure receipt `.json` and `.stdout.txt`, `fc_matrix_builder.txt`, and `E07_EV_CLOSURE_JUDGMENTS.json`; direct SHA-256 entries; recursive JSON+text redaction scan with zero sentinel echo.

Retain all 19 inherited case IDs, 14 fixture IDs (using only disposable or in-memory **test inputs** inside Step 1 pytest so `E04-V14` has no circular dependency on Step 2 primary sealing; write only each final fixture-result JSON to the real evidence directory before sealing), 18+14 exact JUnit function names, 10 E05-FC predicate IDs and five byte-identical synthetic `versions/exp_e03_*.py` files. Preserve historical SQLSTATE, role, writer fencing and other negative proofs. No extra pytest/physical PG15 counts may be invented from the ten FC or seven closure process controls.

## 4. Strict preflight gates, including a real design-completeness checkpoint BEFORE CI

*(Lifecycle mapping: `D0.3` gates `G0–G2` correspond to `R0.3` pre-CI gates `G0–G4`; `D0.3` `G3–G5` execute `R0.3` §9 Steps 1–8; `D0.3` `G6` corresponds to `R0.3` `E7-F`.)*

**G0 (approval and availability — maps to R0.3 G0):** Verify physical access to both complete reviewed Markdown files (`R0.3` and `D0.3`); recompute their byte SHA-256 in Cursor; verify fresh exact PO authority and immutable base; ensure no previous terminal report under this grant. STOP if any missing/mismatch. Never claim sandbox URL alone implies accessible Cursor upload.

**G1 (source and DAG — maps to R0.3 G1):** Validate base commit and E0.6 original artifact/source. Create a fully enumerated code-level **file-write/read dependency DAG**, exact auxiliary inventory generator/checker **derived from frozen policy**, the strict receipt schema and exact per-FC detector registry. Confirm that Step 1 `E04-V01..V14` operate strictly on disposable copies, and that Step 3 FC subgate proofs + Step 4 `E07-C01..C07` falsifiability proofs run on disposable **presealed** roots without needing their own not-yet-generated real FC matrix or real auxiliary manifest. This is the central anti-circularity test: **prove that C05 tests the complete final verifier on a fully clean disposable presealed root before targeted tampering, and that C06 uses independently staged disposable judgment test input rather than requiring its own future real receipt.** Distinguish synthetic disposable validator test inputs from actual current-run process receipts. The tested FC schema must require exactly two ordered vectors for FC06 and FC09 and one for all eight other FC IDs; verify all twelve clean/negative subprocess pairs and exact detectors. If a bypass, self-referential seal, fabricated claimed subprocess result, or unprovable clean full-gate test root is needed, stop with `BLOCKED_DESIGN` before CI.

**G2 (allowlist/proof source — maps to R0.3 G2–G4):** New branch from exact base; no other files changed. Confirm the five synthetic SQL versions are byte-identical. Prepare only approved harness/orchestration/fixtures/workflow files under the two allowlisted paths. Independently review source and actual test code for detector authenticity, zero-write verifier compliance, and potential file mutations *before first push-triggered CI*.

**G3 (CI — executes R0.3 §9 Steps 1–8):** Only after G0–G2 pass, one initial GitHub Actions push-only workflow, disposable PG15; 32 exact pytest tests must pass, 19 case+14 fixture JSON records with identity and real source bindings; all twelve FC gate-vector positive/negative receipt pairs (**24 true subprocess outcomes**) and seven closure receipts + provisional judgments; original provider artifact plus both manifests, root, recursive redaction and external `/tmp/` pre/post `evidence/` tree snapshot equality verification.

**G4 (conditional correction):** Only for an evidenced non-security harness orchestration defect; preserve failed attempt evidence, apply an allowlisted minimal correction and consume at most one second push-run. Fail-closed STOP for any actual SQL security, RLS, migration privilege, writer-fence, secret, authorization, source-provenance or tampering defect; no retry to chase a green job.

**G5 (terminal report):** One complete consolidated report with actual provider-run/job/artifact IDs, tried commits, both CI results, SHA manifests, FC/fixture/closure receipts, external pre/post snapshot proof, and all limitations. Its first delivery terminates the grant, including a BLOCKED or FAILED report. No CI rerun after terminal report or cutoff, even if the archive becomes accessible later.

**G6 (independent `E7-F`):** Separate read-only external audit AFTER Cursor's final report using original provider artifact, exact GitHub source and independent hashing. Not performed by Cursor under this grant. Neither self-tests nor CI green can promote its result.

These **experimental** G0–G6 are entirely distinct from Clinic Ecosystem official Gates A, B, C, D and Package 1 / Package 4 acceptance.

## 5. Workflow/permission hard constraints

The E07 workflow must be triggered only by `push` to the exact experimental branch family and in-scope paths, never `workflow_dispatch`, schedule, PR, release or evidence-only report push. It enforces `GITHUB_RUN_ATTEMPT == 1`, uses `contents: read` permissions, no persisted checkout credentials, a fresh disposable synthetic database with real PostgreSQL 15 proof, fixed branch/base and pre-SQL path diff. Pre/post `evidence/` tree snapshot files and `post_seal_verify_cli` stdout MUST be stored strictly outside `evidence/` (`/tmp/`) during Step 7 so `evidence/` stays byte-immutable; unsealed post-seal outputs are uploaded only in a clearly separated unsealed staging folder. The workflow fails on any nonzero mandatory gate. An operator could manually rerun a GitHub job outside YAML; the authorization **forbids** it even though not cryptographically revocable. Do not count a failed run as a success or use more than 1+1 distinct push-triggered runs.

## 6. Safety STOP and status vocabulary

| Classification | Rule |
|---|---|
| `E07_DOCUMENT_REVIEW_PENDING` | Proposed docs only, no execution authority |
| `BLOCKED_APPROVAL` | No valid new PO exact-hash grant / inaccessible files / placeholder hash remaining; terminal |
| `BLOCKED_DESIGN` | An unresolvable cycle, fake detector/expected exit or impossible zero-write final gate found *before CI*; terminal |
| `E07_CI_GREEN_SELF_REPORTED` | Real hosted CI success on synthetic PG15; only a provider execution fact |
| `E07_SELF_FORENSIC_GATES_PASSED_PENDING_EXTERNAL_AUDIT` | Current-run complete 19/14/10/7 proofs, exact inventory and zero-write read-only gate passed; external `E7-F` not yet verified |
| `E07_EVIDENCE_INCOMPLETE` | Any missing/mismatched acceptance detail, real negative failure, malformed report or prohibited scope; STOP |
| `E07_SYNTHETIC_FORENSIC_EVIDENCE_SUFFICIENT_FOR_GOVERNANCE_REVIEW` | May be issued **only** by independent later `E7-F` audit of immutable artifact/code; not F2-B or production approval |

A failed physical protection proof, actual secret leakage, forbidden write or untrusted provider identity shall NEVER be reclassified as a benign harness defect to enable a corrective CI run. STOP is fail-closed. An independent `E7-F` finding is not self-approved and no automatic E0.8 follows.

## 7. Explicitly excluded implementation/governance topics

No `src/**` changes, no official migrations `TP0008+`, no real API or UI implementation, no deployment, no production patients/PHI, no external secrets, no PR/merge, no Cloud/Local Sync integration, no F2-B architecture approval, no official Package 1 code, no ACR, no PR #3 merge, no official Gate A–D acceptance, no reuse of Package 4 Lease/Erasure cases as Package 1 evidence. Preserve `SRC-10`/`SRC-12` unresolved; record actual evidence needed for their later closure.

## 8. Mandatory final response (if separately executed)

Provide exactly one complete report with `TASK STATUS: COMPLETED/BLOCKED/FAILED`, `CONTRACT: M102 F2-B E0.7 (APPROVAL_STATUS: ...)`, `EXECUTION STATE: TERMINATED`, source and tested SHA, all CI and artifacts, G0–G6 evidence classification, 19/14/10/7 results and distinct 12-vector/24-process FC cardinality, 32 JUnit function identities, exact primary+aux manifest/receipt hashes, external pre/post zero-write snapshot proof, unresolved risks, one next PO action and `=== END OF CURSOR RESPONSE ===` at the end. Do not assert success before real provider evidence. A terminal blocker **ends** the grant.

## 9. Joint document review and amendment policy

This file and the full `R0.3` contract are **REVIEW CANDIDATES**, not signed instruments. Gemini's R0.2/D0.2 revision addressed `E7R-01..E7R-06`; ChatGPT independently corrected residual hash and execution-proof ambiguities in R0.3/D0.3. The exact R0.3 contract digest is pinned above. Only after an independent review of the final R0.3/D0.3 bytes—and independent computation of the final D0.3 digest—may the PO decide whether to issue a fresh execution authorization. A review PASS grants **zero execution authority**.

**Revision ledger:**
- `D0.1_PROPOSED`, 2026-11-18 (superseded): Initial bounded E0.7 authorization proposal pinned to superseded `R0.1` hash `f251362e42cd4f72da9991f5616b5673e1b2d56ff4cc7110d26ad0a8c2b7f4fb`.
- `D0.2_PROPOSED`, 2026-11-18 (independent Gemini joint audit correction): Updated linked contract to `R0.2_PROPOSED` with explicit external SHA-256 computation requirement (no invented hash); aligned all seven `E07-C01..C07` closures, disposable-copy isolation for Step 1 `E04-V01..V14`, dual-vector `E05-FC06`/`FC09`, Step 4 closure falsifiability receipts, zero-write post-seal verifier with `/tmp/` pre/post tree snapshots, `GITHUB_RUN_ATTEMPT == 1` in §5, and explicit `G0–G6` ↔ `R0.2` gate cross-mapping in §4.
- `D0.3_PROPOSED`, 2026-11-19 (independent ChatGPT correction): Pinned the exact computed contract R0.3 digest, eliminating the D0.2 blocker-placeholder contradiction; retained independent D0.3 SHA in the future PO envelope; enforced 10 FC predicate rows / 12 gate-vector positive-negative pairs / 24 actual subprocess outcomes; required clean disposable full-gate C05 and independent C06 judgment test bootstrap; aligned Step 1 fixture output semantics and all R0.3 G0–G4 and Step 1–8 cross-references. Neither R0.3 nor D0.3 is approved or executable.

=== END OF E0.7 D0.3 INSTRUMENT PROPOSAL ===

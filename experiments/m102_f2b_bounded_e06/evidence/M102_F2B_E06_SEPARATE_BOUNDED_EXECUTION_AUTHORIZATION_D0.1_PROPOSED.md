# Clinic Ecosystem — M102 F2-B E0.6 Separate Bounded Execution Authorization Instrument

**Document:** `M102_F2B_E06_SEPARATE_BOUNDED_EXECUTION_AUTHORIZATION_D0.1_PROPOSED.md`  
**Review revision:** D0.1 (proposed)  
**Date:** 2026-11-18 UTC  
**Status:** **PROPOSED / UNSIGNED / REVIEW-ONLY / NO EXECUTION AUTHORITY**  
**Exact linked contract:** `M102_F2B_E0.6_COMPLETE_FORENSIC_CLOSURE_CONTRACT_R0.1_PROPOSED.md`  
**Linked contract full SHA-256:** `492aa65345a0d6033fb46d858185510f8721afc6435cdce0b8cdddf69861fb5a`  
**Product Owner E0.6 authorization:** **NOT PRESENT**; this is a future approval envelope, not a signature.  
**Executor:** Cursor **only if** a subsequent, separate, affirmative PO message approves exact full byte hashes of **both** final reviewed documents.  

## 1. Purpose, history and authority hierarchy

This separate D0.1 proposes **only** the narrow isolated E0.6 forensic-coverage correction of the independently confirmed `E5A-01..E5A-06`. The E0.5 first-run success `44372870212` at `8652686f41f6420a7afe97e84b5f8f151c2a15bb` with artifact `14459202886`, 32/32 pytest, 19/19 correct primary case SHA-256s and 23/23 correct auxiliary SHA-256s is historical **executed** evidence. Its six missing acceptance controls are confirmed in independent A0.1 and Gemini's read-only review; green CI does not prove all FC01..FC10. The E0.5 grant **terminated** on final report. A previous separately terminated E0.5 branch is not permission to resume anything.

Authority order: frozen v3.0.1 specification and latest explicitly approved decisions > fresh exact-scope Product Owner grant > linked technical contract as bounded by that grant > subordinate task prompts. The R4.15 Roadmap is only a review candidate. A completed document review, a proposed technical plan, earlier E0.5 owner consent, or an attached archive is **never** a new E0.6 grant. Conflicts and missing source cause STOP / NO-GO; do not invent evidence.

## 2. Proposed exact authorization envelope (not yet granted)

| Field | Proposed value |
|---|---|
| Repository | `AmirSheikhloo/clinic-ecosystem` |
| Technical contract | `M102_F2B_E0.6_COMPLETE_FORENSIC_CLOSURE_CONTRACT_R0.1_PROPOSED.md`; SHA-256 `492aa65345a0d6033fb46d858185510f8721afc6435cdce0b8cdddf69861fb5a` |
| Separate instrument | `M102_F2B_E06_SEPARATE_BOUNDED_EXECUTION_AUTHORIZATION_D0.1_PROPOSED.md`; **compute this file's own full SHA-256 externally after final review**; do not insert a self-referential hash |
| Executor | Cursor only, after a new explicit PO message referencing both exact files and full SHA-256s |
| Pinned branch base | E0.5 evidence-only final `92b240d7ef2da0b33ed9c50ed841ffb5e194fd83`; direct parent `8652686f41f6420a7afe97e84b5f8f151c2a15bb` |
| Branch | Exactly one NEW `experiment/m102-f2b-e06-*` branch (no reuse of E0.5 or previous task branches) |
| Write paths | `experiments/m102_f2b_bounded_e06/**` and `.github/workflows/m102-f2b-bounded-e06.yml` **ONLY** |
| Synthetic DB | Disposable PostgreSQL 15, fake data/roles/credentials, no patient information or production endpoints |
| Source preservation | Copy E0.5 physical SQL/Alembic semantics; no weakening inherited tests; real-source equivalence ledger |
| Mandatory evidence | Exactly **19 E03 case JSON**, **14 E04 fixture JSON**, exact **32** JUnit function identities, **10** E05-FC positive+negative process outcomes and **6** E06-EV closure judgments |
| Cryptographic proof | Primary 19 case manifest; expanded stable auxiliary manifest including ten-row FC ledger + real process receipts; no self-hashing; read-only post-seal checks and provider identity |
| Workflow | Branch/path scoped `push` ONLY; `permissions: contents: read`; no PR/dispatch/manual rerun/deployment |
| Attempt budget | Maximum **1 initial CI run + 1 optional *non-security* corrective CI run**, both under the same future grant; never run a third or reuse prior E0.5 attempt |
| Proposed UTC cutoff | `2026-12-12T22:59:00Z`, effective only if user later affirmatively approves; first terminal report or blocker ends authority earlier |
| Strictly forbidden | Official `src/**` or `migrations/**`, TP0008+, real Cloud/Local Sync, patient records/credentials, PR/merge, application features, ACR, F2-B approval, Package 1, Gates A–D or Package 4 acceptance |

**The above does NOT grant authority.** No active E0.6 branch, writes, tests, SQL, CI or GitHub action is asserted by this document. The exact two document files must be independently hash-verified **when** a later owner grant is made and before any write.

## 3. Source preservation and six mandatory acceptance closures

| ID | Mandatory bounded proof |
|---|---|
| `E5A-01` | Validate all approved/historical contract and authorization digests, tested/final parent SHA and exact trusted provider run/SHA/attempt; nonzero real CLI on rehashed wrong/missing identity |
| `E5A-02` | Strict typed JSON, UTC zero offset, expected-negative SQL roles/states, unique canonical case-owned regular-file refs and path traversal/symlink denial |
| `E5A-03` | Real production-equivalent CLI negative process exits for V03/V04/V11/V13, including auxiliary tamper, plus nonconditional positive V14; no acceptance bypass flags |
| `E5A-04` | Ten-row `E06_FC_PROOF_MATRIX.json`: all FC01..FC10 positive+negative actual exits, redacted command/receipt, detected fault, trusted provider binding; matrix/schema tested and sealed |
| `E5A-05` | Exact 32 expected JUnit function identities, 19 E03 case↔source + 14 E04 fixture↔source linkage, all relevant JSON/JUnit/logs nested secret scanning with non-echoing negative control |
| `E5A-06` | Root record run_id + SHA + run_attempt trusted provider match, no self-signed independent verification; read-only post-seal CLI forged-metadata denial |

All closure results require both successful clean case **and** actual negative nonzero **process** evidence. Preserve all original 19 case IDs and 14 fixture IDs; the technical contract contains every exact ID and expected test name. No new database business feature or migration semantics, no substitution of historical CI evidence.

## 4. Mandatory inherited nineteen and fourteen identifiers

| Original E03 case | Finding | Kind | Required E06 result |
|---|---|---|---|
| `E03-A01-P01` | A01 | `PHYSICAL_PG15` | Fresh real `OBSERVED_PASS` / truthful failure; preserve `test_e03_a01_p01_fail_closed_migrator` physical or governance meaning |
| `E03-A01-N01` | A01 | `PHYSICAL_PG15` | Fresh real `OBSERVED_PASS` / truthful failure; preserve `test_e03_a01_n01_set_role_denial` physical or governance meaning |
| `E03-A02-N01` | A02 | `PHYSICAL_PG15` | Fresh real `OBSERVED_PASS` / truthful failure; preserve `test_e03_a02_n01_incomplete_backfill` physical or governance meaning |
| `E03-A02-P01` | A02 | `PHYSICAL_PG15` | Fresh real `OBSERVED_PASS` / truthful failure; preserve `test_e03_a02_p01_notnull_and_check` physical or governance meaning |
| `E03-A02-N02` | A02 | `PHYSICAL_PG15` | Fresh real `OBSERVED_PASS` / truthful failure; preserve `test_e03_a02_n02_guard_denies_without_catalog` physical or governance meaning |
| `E03-A03-P01` | A03 | `PHYSICAL_PG15` | Fresh real `OBSERVED_PASS` / truthful failure; preserve `test_e03_a03_p01_overlapping_writers` physical or governance meaning |
| `E03-A03-N01` | A03 | `PHYSICAL_PG15` | Fresh real `OBSERVED_PASS` / truthful failure; preserve `test_e03_a03_n01_stale_writer_fence` physical or governance meaning |
| `E03-A04-P01` | A04 | `PHYSICAL_PG15` | Fresh real `OBSERVED_PASS` / truthful failure; preserve `test_e03_a04_p01_admission_allow` physical or governance meaning |
| `E03-A04-N01` | A04 | `PHYSICAL_PG15` | Fresh real `OBSERVED_PASS` / truthful failure; preserve `test_e03_a04_n01_admission_deny` physical or governance meaning |
| `E03-A05-C01` | A05 | `GOVERNANCE_CONTROL` | Fresh real `OBSERVED_PASS` / truthful failure; preserve `test_e03_a05_c01_ci_governance` physical or governance meaning |
| `E03-A06-P01` | A06 | `PHYSICAL_PG15` | Fresh real `OBSERVED_PASS` / truthful failure; preserve `test_e03_a06_p01_autocommit_role` physical or governance meaning |
| `E03-A06-N01` | A06 | `PHYSICAL_PG15` | Fresh real `OBSERVED_PASS` / truthful failure; preserve `test_e03_a06_n01_invalid_index_recovery` physical or governance meaning |
| `E03-A06-N02` | A06 | `PHYSICAL_PG15` | Fresh real `OBSERVED_PASS` / truthful failure; preserve `test_e03_a06_n02_privilege_negatives` physical or governance meaning |
| `E03-A07-C01` | A07 | `GOVERNANCE_CONTROL` | Fresh real `OBSERVED_PASS` / truthful failure; preserve `test_e03_zz_a07_c01_evidence_schema` physical or governance meaning |
| `E03-A07-C02` | A07 | `GOVERNANCE_CONTROL` | Fresh real `OBSERVED_PASS` / truthful failure; preserve `test_e03_a07_c02_preflight_manifest` physical or governance meaning |
| `E03-A08-N01` | A08 | `GOVERNANCE_CONTROL` | Fresh real `OBSERVED_PASS` / truthful failure; preserve `test_e03_a08_n01_injected_path_denials` physical or governance meaning |
| `E03-A08-P01` | A08 | `GOVERNANCE_CONTROL` | Fresh real `OBSERVED_PASS` / truthful failure; preserve `test_e03_a08_p01_full_range_diff` physical or governance meaning |
| `E03-REG-P01` | REG | `PHYSICAL_PG15` | Fresh real `OBSERVED_PASS` / truthful failure; preserve `test_e03_reg_p01_topology` physical or governance meaning |
| `E03-CLOSE-C01` | CLOSE | `GOVERNANCE_CONTROL` | Fresh real `OBSERVED_PASS` / truthful failure; preserve `test_e03_zz_a07_c01_evidence_schema` physical or governance meaning |

| Original E04 fixture | E06 requirement |
|---|---|
| `E04-V01` | Preserve `test_e04_v01_no_circular_missing_c01` with actual corresponding verifier subprocess outcomes; no fake positive/negative |
| `E04-V02` | Preserve `test_e04_v02_complete_19_and_manifest` with actual corresponding verifier subprocess outcomes; no fake positive/negative |
| `E04-V03` | Preserve `test_e04_v03_missing_or_duplicate_id` with actual corresponding verifier subprocess outcomes; no fake positive/negative |
| `E04-V04` | Preserve `test_e04_v04_byte_tamper_fails_manifest` with actual corresponding verifier subprocess outcomes; no fake positive/negative |
| `E04-V05` | Preserve `test_e04_v05_stale_sha_rejected` with actual corresponding verifier subprocess outcomes; no fake positive/negative |
| `E04-V06` | Preserve `test_e04_v06_stale_run_id_rejected` with actual corresponding verifier subprocess outcomes; no fake positive/negative |
| `E04-V07` | Preserve `test_e04_v07_invalid_field_rejected` with actual corresponding verifier subprocess outcomes; no fake positive/negative |
| `E04-V08` | Preserve `test_e04_v08_skipped_as_pass_rejected` with actual corresponding verifier subprocess outcomes; no fake positive/negative |
| `E04-V09` | Preserve `test_e04_v09_unsafe_paths_rejected` with actual corresponding verifier subprocess outcomes; no fake positive/negative |
| `E04-V10` | Preserve `test_e04_v10_secret_redaction` with actual corresponding verifier subprocess outcomes; no fake positive/negative |
| `E04-V11` | Preserve `test_e04_v11_bad_manifest_rejected` with actual corresponding verifier subprocess outcomes; no fake positive/negative |
| `E04-V12` | Preserve `test_e04_v12_physical_nota_rejected` with actual corresponding verifier subprocess outcomes; no fake positive/negative |
| `E04-V13` | Preserve `test_e04_v13_forensic_gate_independent` with actual corresponding verifier subprocess outcomes; no fake positive/negative |
| `E04-V14` | Preserve `test_e04_v14_clean_validator_pending_audit` with actual corresponding verifier subprocess outcomes; no fake positive/negative |

| Exact FC predicate | Required measured process evidence |
|---|---|
| `E05-FC01` | Positive CLI return `0` + specific negative/tamper CLI nonzero return, canonical detector, redacted signed-off receipt and current-run source binding |
| `E05-FC02` | Positive CLI return `0` + specific negative/tamper CLI nonzero return, canonical detector, redacted signed-off receipt and current-run source binding |
| `E05-FC03` | Positive CLI return `0` + specific negative/tamper CLI nonzero return, canonical detector, redacted signed-off receipt and current-run source binding |
| `E05-FC04` | Positive CLI return `0` + specific negative/tamper CLI nonzero return, canonical detector, redacted signed-off receipt and current-run source binding |
| `E05-FC05` | Positive CLI return `0` + specific negative/tamper CLI nonzero return, canonical detector, redacted signed-off receipt and current-run source binding |
| `E05-FC06` | Positive CLI return `0` + specific negative/tamper CLI nonzero return, canonical detector, redacted signed-off receipt and current-run source binding |
| `E05-FC07` | Positive CLI return `0` + specific negative/tamper CLI nonzero return, canonical detector, redacted signed-off receipt and current-run source binding |
| `E05-FC08` | Positive CLI return `0` + specific negative/tamper CLI nonzero return, canonical detector, redacted signed-off receipt and current-run source binding |
| `E05-FC09` | Positive CLI return `0` + specific negative/tamper CLI nonzero return, canonical detector, redacted signed-off receipt and current-run source binding |
| `E05-FC10` | Positive CLI return `0` + specific negative/tamper CLI nonzero return, canonical detector, redacted signed-off receipt and current-run source binding |

The corresponding `E05-FC01..FC10` predicates must **all** have an independently auditable actual positive and negative subprocess receipt, with a ten-row sealed inventory. A mere 32/32 pytest count does not discharge this obligation. Physical cases must retain all originally tested SQLSTATE/catalog/role/writer proofs; the `E03-CLOSE-C01` case is an extra record generated by the C01 test, not a new pytest function. The complete mandatory JUnit function-name list and the six `E06-EV01..EV06` closure predicates are specified in the linked contract. No waiver or semantic dilution is authorized.

## 5. Exact proposed preflight-to-closeout sequence

- **G0 — approval:** verify the *new* user's separate affirmative Product Owner grant, exact two filenames and 64-hex byte SHA-256s, source availability, clock and no previous terminal report under this grant. An inaccessible document is a **terminal blocker** and ends a grant on final response.
- **G1 — source:** read pinned base `92b240d7ef2da0b33ed9c50ed841ffb5e194fd83`, inspect its tested parent `8652686f41f6420a7afe97e84b5f8f151c2a15bb`, current frozen v3.0.1 spec and accurate E0.5 original source/artifact. Compare exact source bytes; do not trust history from report titles.
- **G2 — branch and scope:** one new E06 branch from that base; `git diff --name-status <pinned-base>...<head>` or the appropriate full-range comparison **before any SQL**. All changes must match the two allowed paths. If not, STOP, no cosmetic hiding of forbidden edits.
- **G3 — bounded source:** only experiment-path harness, fixtures, read-only CLI/seal steps and workflow modifications. Copy 5 synthetic SQL/Alembic version files preserving bytes if possible; source-equivalence ledger for all adaptations. No official migrations or product changes.
- **G4 — synthetic proof:** one push-only GitHub Actions run with disposable PostgreSQL 15, 18 E03 pytest functions + 14 E04 pytest functions, all 19 case files, explicit original semantics and zero failed/skipped tests.
- **G5 — real-gate proof:** exact ten FC positive+negative process outcomes including real exit codes, exact 32 JUnit identities, all 33 record identities, recursive redaction, primary manifest, auxiliary seal and **read-only** post-seal verifier with trusted root context. All must fail closed on any rejection.
- **G6 — report:** one complete consolidated Markdown report with provider run/job/artifact IDs, tested source SHA, exact raw digest manifests, six finding closures, 19/14/10 case/fixture/FC matrix, truthful classifications and limits; evidence-only final commit then deliver once, terminating this grant.

**Note:** These are synthetic experiment G0–G6 steps, distinct from roadmap Gates A/B/C/D and Package 1 vs Package 4 acceptance. `E6-E` is a separate **post-delivery independent audit**, not performed by the experiment executor.

## 6. Correct handling of non-circular hashing and negative tests

1. Write 19 stable case JSONs through staged C01 and generate primary manifest without self-hash. Do not modify these after primary manifest finalization.
2. Finish 14 fixture JSONs, stable pytest JUnit/raw logs, post-pytest forensic report, source-equivalence and preflight records.
3. Run real read-only primary and auxiliary gate CLI against **disposable** evidence trees to record ten FC positive/negative outcomes and six E06-EV controls. For FC08/09/10 a disposable pre-seal auxiliary/root fixture can be constructed, independent of the not-yet-written final aux manifest. Do not write final `E06_FC_PROOF_MATRIX.json` until all required process receipts exist and are correct.
4. Make an explicit final stable auxiliary inventory including all 14 fixtures, required stable logs/source records, original primary manifest/digest record **and** the E06 ten-row FC matrix and receipts. Verify the precise expected inventory; never silently omit files to achieve green.
5. Write the auxiliary manifest and external root digests, excluding themselves, final verifier's own output, provider logs and subsequent final report to avoid recursion. Invoke independent read-only post-seal CLI to rehash both manifests, all sealed bytes, exact metadata, JUnit and redaction; return nonzero on any failure. CI exit is the true job gate, not a self-reported PASS.
6. Upload original CI artifact. A final report may be committed **only as later evidence-only commit**; no new CI or source mutation and no claim it was included in earlier seal. The independent reviewer separately checks provider metadata, artifact bytes and the post-CI report Git parent.

The CLI used for CI must use the same production-equivalent logic/options as the tamper tests. No `test_mode` or `--require-acceptance=0` bypass. No stored hardcoded synthetic credentials in exposed evidence logs; never publish actual secrets/PII. A deliberately bad synthetic fixture passes only when real CLI exit is nonzero **for the intended detector**.

## 7. Stop conditions, attempt budget, expiry and separate decisions

**Fail-closed STOP with no corrective retry:** any owner authorization/hash mismatch, forbidden write, untrusted provider identity, real security/RLS/role/writer fence failure, real secret exposure, failed physical proof, unauthorized migration, source-semantic drift, or no safe way to seal the mandatory evidence. A non-security test-harness/CI orchestration defect may use the **single** conditional correction only when the first failure is evidenced, the fix fits the allowlist and no hard STOP was triggered. No manual rerun, third attempt, workflow_dispatch, PR, merge, deployment or package expansion.

A new PO grant, **if issued**, terminates on whichever happens first: (a) first terminal final report (`COMPLETED`, `BLOCKED`, or `FAILED`) delivered with required marker, including G0 blocked report; or (b) **2026-12-12T22:59:00Z**. After termination no more writes, reruns, CI, SQL, Cursor continuation or artifact edits under that grant. Re-uploading missing files cannot resurrect it. Only a genuinely new explicit exact-hash PO grant can create another bounded task. GitHub manual re-run controls cannot be disabled cryptographically by workflow YAML alone; the governing prohibition remains.

## 8. Final reporting: status must reflect real independent evidence

| Status | Meaning |
|---|---|
| `E06_PROPOSED_DOCUMENT_ONLY` | This proposal and joint read-only review; **zero permission** to execute |
| `E06_AUTHORIZED_PENDING_PREFLIGHT` | Exact owner grant later received; no verified execution yet |
| `E06_CI_SUCCESS_OBSERVED` | Real GitHub Actions CI success, disposable PG15, 32/32 and correct current-run basics |
| `E06_SELF_FORENSIC_GATES_PASSED_PENDING_EXTERNAL_AUDIT` | Mandatory full 19+14+10 real-gate, manifests, JUnit and root checks succeeded **inside** CI |
| `E06_EXTERNAL_FORENSIC_EVIDENCE_SUFFICIENT_FOR_GOVERNANCE_REVIEW` | Only independent later reviewer of original provider artifact and exact source may classify this; does **not** approve F2-B |
| `E06_EVIDENCE_INCOMPLETE` | Any missing predicate/negative process exit, manifest or provider source; STOP with evidence |

F2-B, Package 1, ACR, real Sync, production readiness and official Gates A–D may never be approved by this instrument or the E0.6 synthetic experiment. E0.5's 32/32 execution and hash successes remain legitimate recorded history; its contract gaps are not erased.

## 9. Unresolved architecture and review boundaries

`SRC-10` original Clause 739 report and `SRC-12` complete approved Git baseline remain unresolved. The frozen architecture, TP0008+ ordering, official Control Plane bodies, shared Outbox compatibility, real tenant RLS/Sync/worker lifecycle and Package 4 Lease/Erasure gates are outside E06. Do not propose fixes or test those production questions using fabricated source. E06 experimental gates `E6-A..E6-F` must remain separate from the roadmap's Gates A, B, C, D.

## 10. Independent joint document review, later exact-hash Product Owner decision

Gemini shall independently inspect this **entire** D0.1 and the **entire** linked contract, with source-grounded E0.5 A0.1. Correct all document-level defects **in one pass**, with complete Markdown files preserving all valid content. The next PO approval, if desired, must explicitly name the final exact contract and D0.1 filenames and both SHA-256 digests, branch parent, allowlist, 19+14+10+6 predicates, CI budget, cutoff and hard STOP terms. Until then NO active E06 grant exists. Review of a ZIP's metadata without the original source text is NOT a valid joint review.

## 11. Conditional later Cursor report marker — NO EXECUTION REQUEST HERE

```text
TASK STATUS: COMPLETED / BLOCKED / FAILED
CONTRACT: M102 F2-B E0.6 (APPROVAL_STATUS: APPROVED-AND-VERIFIED / BLOCKED_APPROVAL)
EXECUTION STATE: NOT STARTED / IN PROGRESS / TERMINATED
WORK PERFORMED: <real actions or NONE>
EVIDENCE: <actual provider source, logs, artifact, SHA, or NONE>
OPEN FINDINGS: <actual defect IDs or NONE>
NEXT ACTION FOR PRODUCT OWNER: <one concrete action>
=== END OF CURSOR RESPONSE ===
```

## 12. Revision history and terminal status

| Revision | Date | Change | Classification |
|---|---|---|---|
| `D0.1` | 2026-11-18 | New separate **unsigned** E0.6 instrument; linked exact R0.1 SHA; preserves all 19/14 inventories and 10 FC predicates, defines six E06-EV closures, expanded aux manifest and real subprocess proof, source-equivalence and trusted CI provenance, strict isolation/1+1 budget/termination, independent audit boundary | `PROPOSED / NOT EXECUTED` |

**Final authorization state:** `E06_D0.1_PROPOSED / PO_SIGNATURE_MISSING / NO_ACTIVE_GRANT / NO_E06_CI / F2B_UNAPPROVED / PACKAGE1_NOT_AUTHORIZED / ACR_NOT_APPROVED / GATES_A_TO_D_OPEN`.

=== END OF E0.6 SEPARATE PROPOSED AUTHORIZATION D0.1 ===

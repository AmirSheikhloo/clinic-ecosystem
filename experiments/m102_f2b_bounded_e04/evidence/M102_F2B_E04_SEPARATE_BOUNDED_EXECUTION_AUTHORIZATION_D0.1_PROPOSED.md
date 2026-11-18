# Clinic Ecosystem — M102 F2-B E0.4 Separate Bounded Forensic Reconciliation Authorization Instrument

**Document identity:** `M102_F2B_E04_SEPARATE_BOUNDED_EXECUTION_AUTHORIZATION_D0.1_PROPOSED.md`  
**Revision / date:** `D0.1` / 2026-11-17  
**Status:** **PROPOSED — INDEPENDENT REVIEW REQUIRED — NOT APPROVED — NOT EXECUTABLE**  
**Owner:** Clinic Ecosystem Product Owner (PO)  
**Potential executor:** Cursor **only after fresh, exact, affirmative PO approval**  
**Technical contract, exact unmodified bytes:** `M102_F2B_E0.4_FORENSIC_EVIDENCE_RECONCILIATION_CONTRACT_R0.1_PROPOSED.md`  
**Technical contract SHA-256:** `8dbb6b774e7baa532fb424aa7260b0439f3fed10c0575061b546757199ca04e3`  
**Repository:** `AmirSheikhloo/clinic-ecosystem`  
**Pinned proposed branch base:** `0145b3fd114a022dd004a3a36be43a9a0994a9b5` (historical E0.3 final evidence commit)  
**New authority, execution, CI attempts and approval record:** **NONE EXIST under this proposal.**

> **NON-EXECUTABLE DOCUMENT.** This instrument is prepared for one combined, read-only independent review together with the entire E0.4 R0.1 technical contract. It is **not** a Cursor instruction, permission to run tests, or an owner's signature. Even an unqualified Gemini PASS does not turn it into an effective grant. The E0.3 authority terminated with its final report on 2026-11-17T15:20:14Z. Never reuse the earlier E0.3 authorization or its remaining calendar time. Before any execution, the Product Owner must personally approve the exact final independently reviewed E0.4 contract and this final authorization instrument by **both** full SHA-256 hashes and all bounds below; Cursor must independently verify the files and that consent before its first write.

---

## 1. Purpose and source hierarchy

### 1.1 Sole allowed purpose if separately approved

Repair and independently re-prove the E0.3 forensic-evidence chain for `E03-A07-C01`, without waiving any of the **19 inherited E0.3 case IDs** or the **14 proposed E0.4 validator fixtures**. The correction addresses:

1. **Circular C01 publication:** the historical E0.3 final-test case checked for its own evidence JSON before writing it.
2. **Insufficient forensic checks:** the historical `validate_evidence_file()` checked primarily required-field presence and status membership, not independent tested-commit/run identity, trusted manifest bytes, cross-references, safe paths, redaction or semantic contradictions.
3. **Current-run evidence:** a new, genuine synthetic PostgreSQL 15 CI execution would be required to bind all inherited case records and the forensic validator to a **new current run**, not to falsely relabel historical red CI as green.
4. **Consolidated proof:** one genuine source/CI provenance record, 19 final stable evidence JSONs, 14 positive/negative validator fixture results, an independently re-read digest manifest, a complete final report, and a **separate post-run read-only audit**.

**Source precedence:** the frozen `docs/FINAL_MASTER_SPECIFICATION_v3.0.1_FINAL.txt` (historically inspected Git blob `befde437b6f951e1da71fdb4f0e61d043049c168`) remains architecture authority; the latest explicitly approved roadmap version controls roadmap decisions. `MASTER_EXECUTION_ROADMAP_v3.0.1_R4.15.md` remains a review candidate unless there is documented later approval. E0.3 technical contract SHA-256 `b5f8d33a33ff25e398cb75be76bebfab02a32cf8386e04b1e46f6cecc89ecb28` remains the inherited test baseline; the D0.1 E0.3 grant SHA-256 `4e8a8f5f25649bc263af68f72e897313366b77320c47401f0c6ea3fc5f87a643` is **historical and terminated**. E0.4 R0.1 adds **forensic validation requirements**, not new migrations, schema semantics, architecture or implementation package authority.

### 1.2 Read-only evidence that motivates this proposal

- E0.3 CI initial attempt: [`44111930395`](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/44111930395), head `29b622003f178e90e7670ba0de068a03ec9acd8d`, **failure**, 9/18 pytest passed.
- E0.3 CI final allowed attempt: [`44112675849`](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/44112675849), tested head `3c63e93846e7a79e6700414ab891fc5e3d983427`, **failure**, **17 passed / 1 failed / 0 skipped**. The failing test reported `missing E03-A07-C01`.
- Historical final evidence and report commit: `0145b3fd114a022dd004a3a36be43a9a0994a9b5` (parent `3c63e93846e7a79e6700414ab891fc5e3d983427`). That final report classified E0.3 as `CORRECTIVE_EVIDENCE_INCOMPLETE`.
- Source at that final commit: `experiments/m102_f2b_bounded_e03/tests/test_e03_corrective_suite.py` (Git blob `686f1411f3c9ec3f894dce74f022b408101a6e45`) and `experiments/m102_f2b_bounded_e03/harness/evidence.py` (Git blob `95c6c8608944903550c0638eda18c6fbc5f993e1`).
- E0.3 independent audit A0.1 SHA-256 `bda1a8891311e1138383221546845f3d170129eef539118fd12cca191c74a657`. The owner forwarded a Gemini review confirming its four audit findings; that is a **document review report**, not executable or runtime evidence.
- The Product Owner has forwarded a Gemini independent `E0.4 R0.1 DOCUMENT REVIEW PASS` for the **technical contract only**. It is **not** a review of this newly drafted execution instrument and is not PO execution approval.

Do not claim a fresh GitHub baseline, implementation or verification of external Cloud/Local/Sync behavior without actual evidence. At the time of later execution, rerun all mandatory **read-only** source-preflight checks against the source then visible; uncertainty must stop execution.

---

## 2. Approval envelope — proposed, not granted

| Field | Proposed bound | Fail-closed interpretation |
|---|---|---|
| Executor | Cursor only | Any other actor/tool must not execute under this grant |
| Contract bytes | E0.4 R0.1 file and exact SHA in header (or a later complete, independently reviewed replacement) | Missing, different or unreviewed contract: `BLOCKED_APPROVAL` |
| Instrument bytes | The final independently reviewed successor to this D0.1, with **its own computed SHA-256** | Approval of draft D0.1 does not follow a material revision automatically |
| PO act | Fresh affirmative PO message naming BOTH complete filenames, SHA-256 hashes, UTC cutoff, CI budget and E0.4 scope | A review PASS or authorization template is **not** consent |
| Branch base | Exact Git commit `0145b3fd114a022dd004a3a36be43a9a0994a9b5` | Missing/wrong/unrelated parent: stop; no inferred rebase |
| New branch | **One** `experiment/m102-f2b-e04-<UTCSTAMP>-0145b3fd`, unique and newly created from that base | No write to `main`, E0.2 or E0.3 branches; no force-push |
| Allowed writes | **Only** `experiments/m102_f2b_bounded_e04/**` and `.github/workflows/m102-f2b-bounded-e04.yml` | Every other path is forbidden, including previous experiment histories |
| Work type | Source equivalence mapping, evidence/test harness refactor, E0.4 validator fixtures, synthetic PG15 rerun and final report only | No application features, new migration semantics, production connectors or real keys |
| CI trigger | Restricted **push** only to approved E0.4 experiment branch + allowed paths | No `pull_request`, `workflow_dispatch`, scheduled/reusable/deployment jobs, PR or merge |
| CI budget | At most **one initial push-triggered run + one corrective push-triggered run**, with corrective allowed **only for a non-security harness/forensic-test defect within scope and active deadline** | No second run after security fail, scope fail, verified approval mismatch, prior final report or cutoff; no automatic extra runs |
| Absolute cutoff | **2026-11-30T22:59:00Z** (2026-11-30 23:59 Europe/Berlin) — independently proposed fresh deadline | This is **not** the terminated E0.3 cutoff and does not authorize action before PO approval |
| Earlier cutoff | **Actual delivery of one E0.4 final consolidated report** (whether clean, incomplete, blocked or failed) | Earlier of report delivery or absolute UTC timestamp **ends authority immediately** |
| Data and environment | Only disposable PostgreSQL 15 with synthetic rows/keys and isolated temporary test roles | No patient/staff information, production, staging, shared services, actual Sync, persistent clinical resources |
| Review | Independent read-only audit **after** the run's final artifact/report is available | CI green alone does not satisfy forensic governance acceptance |

**No silent restart:** A negative security assertion unexpectedly succeeding is a terminal `STOP_SECURITY`, not a repairable harness failure within this grant. If a genuine security defect is found, or the root cause requires a new SQL migration, altered PG schema, changed role-policy semantics, official source edits or additional CI attempt, preserve truthful failure evidence, terminate, and obtain a wholly separate owner decision. Authorizing this table would not authorize Gate A, B, C or D, Package 1, an ACR, a production rollout, or F2-B adoption.

### 2.1 Why the proposed corrective run is conditional

The single optional corrective attempt may occur **only** if: (i) initial CI reached the actual permitted suite, (ii) a non-security failure is reproduced and clearly classified, (iii) all safety/privilege/role/index/fencing negatives behaved safely, (iv) a minimal within-allowlist correction is documented and inspected, (v) original CI failure evidence remains immutable, (vi) the final report has **not yet been delivered**, (vii) the new cutoff is still active, and (viii) the new commit and event identity pass fresh pre-SQL guards. The executor cannot exploit a path-excluded evidence-only push or a manual rerun to bypass the budget. **Two independent run IDs** count as two CI attempts even when each has `GITHUB_RUN_ATTEMPT=1`; manually re-running a historical run is prohibited. Do not create third-party tasks or scheduled Actions on the owner's behalf.

---

## 3. Immutable provenance and write guards

### 3.1 New branch origin

The new branch must be rooted exactly in the E0.3 **final evidence commit** `0145b3fd114a022dd004a3a36be43a9a0994a9b5`, **not** in its prior tested head (`3c63e938...`) or E0.2 report (`471f884...`). Verify source objects, parent SHA, branch absence and clean worktree **before** branch creation. Record the tested E0.4 CI commit and any later final evidence-only commit **separately**. The historical E0.3 failure remains `OBSERVED_FAIL`; do not rewrite or reclassify it.

### 3.2 Comprehensive pre-SQL diff guard

Before **any** PostgreSQL connection used to execute tests, CI must compare `git diff --name-status` plus file modes and actual paths from approved base commit to actual checked-out `GITHUB_SHA`. Reject disallowed paths, rename/move tricks, symlinks, traversal, Git submodules/executable changes where disallowed, case-insensitive collisions and dirty/untracked paths. Ensure the workflow being executed and test harness are within the allowlist. Verify the branch is the exact one created under new PO consent, rather than trusting a broad wildcard prefix. A red, missing or bypassed diff guard => **no SQL**. Manual local testing, if independently authorized, remains subject to the same approval/scope and disposable-DB checks; local results do not replace CI.

**Sole write paths:** `experiments/m102_f2b_bounded_e04/**`, `.github/workflows/m102-f2b-bounded-e04.yml`.

**Read-only paths:** `experiments/m102_f2b_bounded_e03/**`, `experiments/m102_f2b_bounded_e02/**`, any original migrations and service code (`migrations/**`, `src/**`, `docs/**`, etc.), all old workflow files and repository configuration. Never modify `main`, branch protection or old audit artifacts; never open a PR.

### 3.3 Equivalent code and limited permissible adaptations

Preserve the **semantics** of inherited synthetic physical tests and synthetic migration revisions byte-for-byte where possible. Any necessary path/import adjustments must have an explicit old→new source-hash equivalence ledger and byte/AST or reviewable semantic diff. Only logic for C01 publication/verification, `harness/evidence.py`-equivalent forensic validation, tamper fixtures, new workflow integration, new report/evidence, and minimal paths may change. **Do not** change target DDL, schema, concurrency assumptions, RLS grants, HMAC lifecycle, branch topology or negative-test expected outcomes to make them green. A physical case that passes only after its expected assertion was weakened is `BLOCKED_SCOPE`, not a successful E0.4 correction.

---

## 4. Non-negotiable forensic acceptance protocol

### 4.1 C01 circularity and finalization

Follow the six-stage protocol of technical contract §5.1. In particular:

1. The old E0.3 C01 record stays historically red. Build a distinct **new current-run** provisional C01 (`UNVERIFIED` or equivalent) and all other 18 records; no preliminary green label.
2. Validate the other 18 final-intent records and C01's proposed final payload in memory against independent runner identity, schema, semantics, cross-references, path safety and redaction. Do **not** merely delete C01 from `REQUIRED_CASE_IDS`.
3. Finalize all 19 actual JSON file bytes including C01; exclude all self-digest cycles. Generate one deterministic, standalone 19-case SHA-256 manifest **after** those bytes are stable.
4. Launch a **separate post-finalization** verifier that re-opens every byte stream, checks all 19 unique IDs, verifies canonical paths and exact per-file hashes, validates the manifest itself for illegal self-entries and duplicates, compares run/commit identities to actual CI context and exits nonzero on any failure. A bad verifier exit must fail the **entire CI job**, even if pytest reports 100% green.
5. Verify redaction in fields and referenced logs, including negative injection cases. Failed checks must remain failed. No report may assert C01 or E0.4 complete on the strength of an offline after-the-fact check alone.
6. If JUnit/logs and other mandatory evidence are produced later, finalize a **second independently verified evidence layer**; avoid manifest self-inclusion or post-verification mutation. Hash the stable manifest and record the digest in the final report. The GitHub artifact identity and later independent audit are distinct external corroborations.

**Integrity model:** SHA-256 provides byte-integrity checks, not a signature or independent proof of the runner's honesty. `GITHUB_SHA`, `GITHUB_RUN_ID`, `GITHUB_RUN_ATTEMPT`, branch/ref/event, `git rev-parse HEAD`, fixed parent identity and GitHub Actions API metadata must be reconciled as *separate* sources of proof. Stale, syntactically fake, missing or self-claimed values are not equivalent to trusted provenance. Redact credentials, real DSNs and any private data from all artifacts; negative test fixtures must avoid publishing the injected secret even in their own summaries.

### 4.2 Evidence schema and semantic validation

Preserve every E0.3 §6.2 required field and verify the **value** and type, not merely presence. Mandatory set:

`case_id`, `finding_id`, `classification`, `execution_kind`, `contract_sha256`, `parent_e02_final_commit_sha`, `tested_commit_sha`, `run_id`, `timestamp_utc`, `postgres_server_version_num`, `database_label`, `session_user`, `current_user`, `preconditions`, `command_redacted`, `expected_result`, `observed_result`, `exit_code`, `before_state`, `after_state`, `evidence_files`, `limitations`.

Check ID↔finding↔execution-kind mapping, approved contract SHA and two-tier historical lineage, timezone-aware UTC timestamp and plausible run boundaries, current PostgreSQL actual version/role/DB/catalog for physical proofs, nonempty relevant observations, success/failure/exit-code consistency, explicit justified `NOT_APPLICABLE` only for governance controls, real canonical evidence file existence, safe regular files (no symlink/traversal) and nonempty source/test linkage. Reject `SKIPPED`/`UNVERIFIED`/`BLOCKED` or conflicting record as `OBSERVED_PASS`. Fail closed on invalid/missing SHA manifest, duplicate/hash-conflicting files and accidental leaked secrets. Preserve applicable E0.3 §6.3 and E0.4 §§5.2–5.4 without substitution.

### 4.3 Full preserved inherited case matrix — **19**

| Case ID | Historical E0.3 attempt 2 | Mandatory E0.4 re-proof |
|---|---|---|
| `E03-A01-P01` | `OBSERVED_PASS` | Current-run PG15, restricted role and fail-closed migration |
| `E03-A01-N01` | `OBSERVED_PASS` | Denied role transition, no elevated fallback |
| `E03-A02-N01` | `OBSERVED_PASS` | Block incomplete backfill before Phase-8 |
| `E03-A02-P01` | `OBSERVED_PASS` | `attnotnull=true` and validated CHECK; real catalog read |
| `E03-A02-N02` | `OBSERVED_PASS` | Missing Catalog guard rejects Phase-8 |
| `E03-A03-P01` | `OBSERVED_PASS` | Real overlapping TX, uniqueness SQLSTATE |
| `E03-A03-N01` | `OBSERVED_PASS` | Stale/offline writer fencing before mutation |
| `E03-A04-P01` | `OBSERVED_PASS` | Synthetic mixed Cloud/Local admission ALLOW |
| `E03-A04-N01` | `OBSERVED_PASS` | Synthetic mixed-state DENY/no mutation |
| `E03-A05-C01` | `OBSERVED_PASS` | New E0.4 workflow governance and stop controls |
| `E03-A06-P01` | `OBSERVED_PASS` | Role restoration across autocommit |
| `E03-A06-N01` | `OBSERVED_PASS` | Invalid index inspection and safe recovery |
| `E03-A06-N02` | `OBSERVED_PASS` | Role-grant/RLS privilege negatives |
| `E03-A07-C01` | **`OBSERVED_FAIL`** | 19 finalized files, trusted identity, SHA checks, semantic/redaction gate |
| `E03-A07-C02` | `OBSERVED_PASS` | Genuinely pre-execution complete 19-row manifest |
| `E03-A08-N01` | `OBSERVED_PASS` | Strict off-allowlist path attack denials |
| `E03-A08-P01` | `OBSERVED_PASS` | Full new-base-to-tested-commit guard before SQL |
| `E03-REG-P01` | `OBSERVED_PASS` | Same synthetic topology semantics; no new migrations |
| `E03-CLOSE-C01` | `OBSERVED_PASS` | Truthful cleanup and termination provenance |

These statuses are historic and do **not** carry forward as E0.4 passes. Test counts, case counts, physical tests and governance controls are different metrics. A later `OBSERVED_PASS` must be linked to **real current-run evidence** and only to the exact historical criteria; no inherited case ID is waived.

### 4.4 E0.4 validator mutation-fixture matrix — **14**

| Fixture | Required negative/positive proof |
|---|---|
| `E04-V01` | Staged C01: not prematurely accepted; no circular false failure |
| `E04-V02` | Valid 19 JSONs + manifest; separate byte re-read succeeds |
| `E04-V03` | Missing/duplicated/swapped ID is rejected |
| `E04-V04` | Post-manifest byte mutation is rejected |
| `E04-V05` | Fake/stale tested SHA, `LOCAL_UNKNOWN` rejected in CI |
| `E04-V06` | Fake/stale run ID/attempt, `LOCAL_NOT_CI` rejected in CI |
| `E04-V07` | Invalid UTC/type/mandatory field is rejected |
| `E04-V08` | Contradictory PASS, `SKIPPED` or `UNVERIFIED` rejected |
| `E04-V09` | Path traversal, symlink, wrong ref/case collision rejected |
| `E04-V10` | Secret/real DSN injected in **disposable dummy** fixture is detected without leaked reporting |
| `E04-V11` | Missing/duplicated/self-hashed/stale digest manifest rejected |
| `E04-V12` | Physical PG proof replaced with governance `NOT_APPLICABLE` rejected |
| `E04-V13` | Isolated simulated green pytest + failed forensic verifier leads to **expected nonzero** workflow-gate simulation; the real healthy CI still may pass |
| `E04-V14` | Clean 19 + manifest + trusted actual CI context and suite succeed; **independent audit still pending** |

Fixture-negative success means correct **rejection of deliberately tampered disposable inputs**. No failure fixture may mutate the final genuine evidence tree or cause a deliberately red real authorized CI when an isolated subprocess simulation would prove the intended control. Keep full expected/observed and exit-code evidence for each fixture, with no secret leakage.

---

## 5. One-pass source/technical preflight and execution sequence (conditional)

1. **`E4-A / G0 — Authority`**: full exact-file digest checks, verify new PO message and fixed UTC bounds, verify instrument and contract both independently reviewed; if any mismatch => `BLOCKED_APPROVAL`, **no branch, edits, local tests or DB**.
2. **`G1 — Read-only source`**: verify frozen spec, latest explicitly approved roadmap state, all historical contract/audit files, both red CI run IDs and source blob identities, E0.3 final report, actual E0.3 branch commit, clean worktree. Any missing required source => `BLOCKED_SOURCE`; don't fabricate missing code or evidence.
3. **`G2 — Complete preflight plan`**: before a write, build full 19-case + 14-fixture plan, threat/DB/role and proof manifest, date/attempt budget, expected SQLSTATE/PG catalog assertions, source equivalence checks and automatic fail-closed controls; perform permitted static/lint checks so a trivial schema-order bug does not waste the first CI attempt. Planning and dry inspection alone do not justify running the CI without fresh PO consent.
4. **`G3 — Isolated work`**: create exactly one new E0.4 branch from the fixed E0.3 report commit, port original synthetic suite without semantic changes (record source and copy hashes), implement C01 staged publication and external verifier, E04-V01..V14 fixtures and new workflow only under allowlist.
5. **`G4 — Synthetic PG15`**: verify server identity and safe non-production DSN; run complete old physical suite unchanged with real catalog, restricted roles, concurrency and negative proofs; stop immediately for true security violations.
6. **`G5 — Restricted CI`**: only push to the approved E0.4 branch, with read-only GitHub permission, strict exact-branch/CI-attempt/time/source guard before SQL; `postgres:15` disposable service; no service secrets/production vars, PRs, manual triggers, deployment steps or merger actions. CI pipeline must have two independent success gates: suite green/no skips, **then** post-pytest forensic verifier green. Upload evidence on failure without rewriting outcome.
7. **`G6 — Evidence and closeout`**: finalize 19 JSONs, manifest, verified hash and raw logs; keep original run metadata, artifact ID, tested commit; if optional corrected attempt occurred, retain original failure details too. One complete consolidated report and optional evidence-only commit (which must not relaunch CI); report delivery terminates grant instantly. A later independent read-only audit verifies source and GitHub artifact and alone may classify the evidence as sufficient for experimental governance review.

**CI workflow guard considerations:** Workflow triggers must be `push` only with strict branch and path filters; `permissions: contents: read`; no checkout credentials persisted; no reusable jobs, privileged service, secrets, deployment or manual dispatch. Explicitly reject unexpected `GITHUB_RUN_ATTEMPT`, `GITHUB_EVENT_NAME`, `GITHUB_REF`, `GITHUB_SHA`, run identity, time or branch. **A workflow cannot technically revoke repository users' GitHub manual rerun capability**, so retain the governance prohibition in all instructions. Evidence-only pushes must be path-excluded to avoid third CI runs. If the chosen path-filter syntax cannot be demonstrated to exclude them, use a safer expressly reviewed method or STOP rather than assume.

**Hard stop:** discovered real credential/patient data, uncontrolled external database, failed role/RLS/GRANT/fencing/index negative, real SQL schema change required, inconsistent proof, leaked sensitive data, CI job identity or artifact mismatch, outside-path modification, mutable historical evidence, approval/hash failure, budget exhausted, report already delivered or UTC expiry. Preserve evidence without further run; classify **`INCOMPLETE`**, `BLOCKED_*` or `STOP_SECURITY` as appropriate. Neither successful negative fixtures nor green pytest can waive these stops.

---

## 6. Acceptance and truthful final classifications

**E0.4 experimental controls (not roadmap Gates A–D):**

| Gate | Condition | Fail state |
|---|---|---|
| `E4-A` authority | New PO approved both SHA-pinned docs and active deadline, permissions and budget | `BLOCKED_APPROVAL` |
| `E4-B` scope | Exact base, source mapping and full-range allowlist, historical immutable | `BLOCKED_SOURCE_OR_SCOPE` |
| `E4-C` physical / CI | Actual PG15, inherited physical tests and control proofs, no failed/skipped CI tests | `CI_OR_PHYSICAL_PROOF_INCOMPLETE` |
| `E4-D` forensics | Final all 19 file checks + 14 fixtures, trusted CI/run SHA, redaction, independent manifest byte re-read | `FORENSIC_EVIDENCE_INCOMPLETE` |
| `E4-E` independent audit | Later separate source-grounded review of real immutable CI artifact and report | `INDEPENDENT_AUDIT_PENDING_OR_FAILED` |
| `E4-F` closeout | Complete truthful report, cleanup evidence, actual delivery UTC, grant terminated | `CLOSEOUT_INCOMPLETE` |

**Until independent post-run review, the maximum claim after a truly clean authorized CI is:** `E04_CI_AND_FORENSIC_CHECKS_PASSED_PENDING_INDEPENDENT_AUDIT`. After independent verification, at most `E04_FORENSIC_EVIDENCE_SUFFICIENT_FOR_GOVERNANCE_REVIEW`, **never** approved F2-B architecture, Package 1 implementation/permission, ACR signed, formal migrations, production readiness or Gate A–D. Existing SRC-10 / SRC-12, official Tenant Alembic multi-head runner and real Cloud/Local Sync remain separate unresolved sources; this instrument does not address them.

A failed or red run, C01 failing, manifest integrity gap, unverified real runner linkage, test skips, absent post-final verifier or deficient report **must** remain `FORENSIC_EVIDENCE_INCOMPLETE` or more severe fail-closed status even if individual case JSONs have `OBSERVED_PASS`. Once the designated CI budget is used or the report delivered, do not silently schedule/retry another run.

---

## 7. Final report, independent review and termination

If subsequently approved, Cursor must provide **one complete final consolidated Markdown report** in `experiments/m102_f2b_bounded_e04/evidence/M102_F2B_E04_FINAL_CONSOLIDATED_REPORT.md`, including: exact owner approval, both final file names/hashes; source spec and roadmap statuses; parent/tested/final commits; full change/equivalence ledger; actual CI event/job IDs and attempt count, URL and raw logs; actual Postgres 15 server_version_num and role/DB proof; old 19 E0.3 case IDs and new 14 fixture IDs separately with honest status; full trusted provenance comparison and 19-digest manifest SHA; secret/path/validator-negative results; E0.2/E0.3 red history; no out-of-scope files; cleanup ownership/platform caveat; residual open items; one next PO action; and the final status. If preflight stops before a new branch, provide a complete blocker report in Cursor response instead; do not falsify a repository report path. No PR or merge.

**Grant termination:** the new cutoff if approved is the **earlier** of (i) actual delivery of **one** final consolidated report or (ii) `2026-11-30T22:59:00Z`. A CI failure can be corrected within the chosen 1+1 budget only before report delivery, only for permitted non-security harness problems, and only while the grant is otherwise active. If blocked, terminate with an honest failure/blocker report. No actions under the grant after final delivery, even if the fixed clock time has not arrived. The independent reviewer afterwards is **read-only**; its assessment cannot reactivate the expired permission.

**Mandatory Cursor final marker** for any separately authorized task (even if BLOCKED/FAILED):

```text
TASK STATUS: COMPLETED / BLOCKED / FAILED
CONTRACT: M102 F2-B E0.4 (APPROVAL_STATUS: PROPOSED / APPROVED-AND-VERIFIED)
EXECUTION STATE: NOT STARTED / IN PROGRESS / TERMINATED
WORK PERFORMED: <precise actions performed and expressly not performed>
EVIDENCE: <real source SHAs, CI runs, artifacts, manifest digest, or NONE>
OPEN FINDINGS: <actual outstanding case IDs or NONE>
NEXT ACTION FOR PRODUCT OWNER: <one exact action, or NONE>
=== END OF CURSOR RESPONSE ===
```

Any future Cursor instruction must explicitly demand the marker ending **exactly** with `=== END OF CURSOR RESPONSE ===` and forbid new work after that line. A user-visible summary must never imply a CI pass, a PR merge or an F2-B approval without current source evidence.

---

## 8. Product Owner decision form — illustrative, not yet signed

> **NO CONSENT IS GIVEN HERE.** This quoted block is a template requiring a **new, separate, personal affirmative act** by the Product Owner, **after independent joint review of both complete files**. The PO must identify the final independently reviewed filenames and full hashes. If the reviewer revises either file, recompute the changed hash and obtain fresh review and approval for that version. An empty or unverified field means NO GRANT.

```text
I, the Product Owner of Clinic Ecosystem, explicitly and separately approve
Cursor ONLY to execute the bounded M102 F2-B E0.4 synthetic forensic-evidence
reconciliation experiment, and NOTHING ELSE, according to:

Technical contract filename: <EXACT FINAL INDEPENDENTLY REVIEWED E0.4 FILE>
Technical contract SHA-256: <EXACT VERIFIED FULL SHA-256>
Execution authorization filename: <EXACT FINAL INDEPENDENTLY REVIEWED E0.4 D0.x FILE>
Execution authorization SHA-256: <EXACT VERIFIED FULL SHA-256>

Scope: ONE new experiment/m102-f2b-e04-<UTCSTAMP>-0145b3fd branch, based only
on commit 0145b3fd114a022dd004a3a36be43a9a0994a9b5; write only under
experiments/m102_f2b_bounded_e04/** and .github/workflows/m102-f2b-bounded-e04.yml.
CI: only approved branch push-trigger, one initial run and one optional bounded
non-security corrective run; NO PR, no workflow_dispatch, no manual rerun,
no merge or deployment. Failure of a security assertion: immediate STOP.
Resources: disposable PostgreSQL 15 and wholly synthetic data/credentials.
Deadline: earlier of final report delivery or 2026-11-30T22:59:00Z.
Proof: all 19 inherited E0.3 case IDs plus E04-V01..V14, separate post-pytest
forensic manifest verifier and later independent read-only GitHub audit.
Exclusions: no official migrations, app code, shared/persistent databases,
actual patient data or keys, real Sync, ACR, Package 1, Gate A–D, F2-B approval,
PR/merge, old evidence rewrites or additional CI runs.

This is strictly an E0.4 experimental grant, not architecture approval.
```

**NO signature, no executable authority, and no permission to forward the template directly as a Cursor command** are implied by this illustrative block. Once independently reviewed, the owner must actually send a clear approval message that fills the final verified identities.

---

## 9. Mandatory consolidated independent-review instruction (one pass)

The immediate next review should inspect **both complete documents in a single session**: the SHA-pinned E0.4 R0.1 technical contract (already reported Gemini PASS) and this fresh D0.1 execution instrument. Check every section, full 19 inherited cases, all 14 fixture IDs, current historical E0.3 CI/API facts, existing code/validator, new branch and exact write-path guard, cutoff and budget, two-layer evidence hashing without circularity, runner provenance, security/regression STOP, no unauthorized execution, and PO final approval template. Distinguish `PROPOSED`, `TESTED`, `VERIFIED`, `APPROVED` and `BLOCKED`. An independent source-grounded review is **not itself an execution instruction**.

If either document has a substantive defect, directly correct the affected complete artifact with **no loss of valid text or case matrix**, supply its full revised `.md` file and an accurate revision log; note the new filename/hash explicitly. Review the pair for compatibility; if both are sound, explicitly identify **both** filenames as reviewed, with an unambiguous **DOCUMENT-LEVEL PASS**. No GitHub writes, Cursor runs, PostgreSQL connections, or approval on the owner's behalf.

---

## 10. Revision history

| Revision | Date | Scope of change | Actual status |
|---|---|---|---|
| `D0.1` | 2026-11-17 | New, independent proposed E0.4 execution instrument; fixes authorized branch origin, scope, 1+1 bounded attempts, fresh UTC deadline, all 19 inherited cases and 14 forensic fixtures, source-provenance and validator controls, explicit STOP, closeout and exact-file PO approval dependencies. The source E0.4 R0.1 contract is preserved **unchanged** and has a user-forwarded Gemini PASS; this instrument itself has **not** yet been independently reviewed. | `PROPOSED / NOT AUTHORIZED / NOT EXECUTED` |

**Terminal documentary classification:** `E04_CONTRACT_REVIEW_REPORTED_PASS / E04_D0.1_INSTRUMENT_AWAITING_JOINT_REVIEW / NO_NEW_PO_E04_GRANT / ZERO_AUTHORIZED_CI_ATTEMPTS / F2-B_UNAPPROVED`.

=== END OF E0.4 D0.1 PROPOSED AUTHORIZATION INSTRUMENT ===

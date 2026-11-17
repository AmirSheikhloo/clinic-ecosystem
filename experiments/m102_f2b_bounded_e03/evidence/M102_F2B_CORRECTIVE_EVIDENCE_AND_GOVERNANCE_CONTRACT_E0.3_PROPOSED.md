# Clinic Ecosystem — M102 F2-B Corrective Evidence and Governance Contract E0.3

**Artifact identifier:** `M102_F2B_CORRECTIVE_EVIDENCE_AND_GOVERNANCE_CONTRACT_E0.3`  
**Revision:** `E0.3 — PROPOSED / REVIEW ONLY / NOT AUTHORIZED FOR EXECUTION`  
**Draft date:** 2026-11-17  
**Repository:** `AmirSheikhloo/clinic-ecosystem`  
**Potential executor after a separate approval:** Cursor only  
**Intended reviewers:** ChatGPT and Gemini, independently  
**Document type:** A standalone *replacement corrective proposal*, **not** an amendment made in-place to E0.2, an ACR, or an implementation authorization  
**Normative language:** English. `MUST`, `MUST NOT`, `SHALL`, and `STOP` are binding requirements **only if** a future PO authorization makes this exact E0.3 artifact executable.

> **GOVERNANCE HOLD — NO EXECUTION AUTHORITY.** The Product Owner requested **drafting only**. Creating or reading this file authorizes **no** repository edit, branch, push, workflow change, SQL, PostgreSQL container, test run, Draft PR, official migration, Package 1 development, ACR signature, or Gate A–D acceptance. The prior E0.2 grant **terminated when its consolidated report was delivered**. E0.3 does not revive that grant, inherit its expiry, approve F2-B, or modify the frozen specification. A future, separate PO approval must identify this exact document filename **and its independently calculated SHA-256**, name the executor, define the permitted period (including a fixed UTC termination instant), and explicitly adopt the CI mode in §7. Until then all execution gates are closed.

---

## 1. Purpose, prior evidence, and decision boundaries

### 1.1 Exact purpose

This proposal defines a **bounded corrective follow-up**, subject to future authorization, to close eight confirmed defects and evidence gaps (`A01`–`A08`) in the E0.2 synthetic F2-B experiment. It is **not** a blanket rerun, a new official migration design, an approval of the two-head Tenant DAG, or a waiver of any previously failed acceptance criterion. Preserve every valid prior finding and avoid rerunning unrelated successful work without a demonstrated regression dependency.

### 1.2 Source and evidence register

| Source ID | Document, code, or evidence | Observed classification / scope |
|---|---|---|
| `S01` | `docs/FINAL_MASTER_SPECIFICATION_v3.0.1_FINAL.txt` (repository `main`); clauses **771–772** | Frozen architectural authority: Phase-6 `CREATE UNIQUE INDEX CONCURRENTLY`/autocommit, invalid-index recovery, Phase-8 validation and guarded cutover, same-source dual-write, old-writer drain, old-authority preservation. Read and fingerprint again before any future execution. |
| `S02` | `MASTER_EXECUTION_ROADMAP_v3.0.1_R4.15.md`, §§11.8–11.9 | Review candidate describing F2-B: HMAC `tp0010 → tp0011 → tp0012` and separate Catalog `tp0010 → tp0013 → … → tp0023`. Independent document review reported no document-level defects; **not an effective migration ACR or implementation permission**. Exact attachment/hash and approval chain require live verification. |
| `S03` | `M102_F2B_REPLACEMENT_BOUNDED_EXPERIMENT_CONTRACT_E0.2_PROPOSED.md`; **SHA-256 `03c471825a0ec404eb0ce173789a9d0dd87e3c42a656ed6cad459f277909ec31`** | PO-approved, completed, now **terminated** experimental contract. Its §§5.1–5.3 are the criteria against which E0.2 coverage was audited. Never change its bytes. |
| `S04` | `M102_F2B_E0.2_INDEPENDENT_AUDIT_A0.1.md`; **SHA-256 `9c5f8947a52c8750fbfaa5a798dfee88069f9d64f8e76840b225e12a057b758f`** | Independent ChatGPT audit; eight material findings, `A01`–`A08`. Gemini separately confirmed **all eight** in the user's 2026-11-17 response. This statement records concurrence, not a separate executable test. |
| `S05` | E0.2 CI: [run 43952295235](https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/43952295235), tested commit **`e1897078076296c771a7caedb97dc75b2b28db22`**, job `133597677679`, artifact `14266348935` | **Executed:** 14 authored pytest tests green on PostgreSQL 15.20 (`14 passed, 0 failed, 0 skipped`). **Not verified:** satisfaction of all contractual E0.2 acceptance criteria. |
| `S06` | E0.2 consolidated report: `experiments/m102_f2b_bounded_e02/evidence/M102_F2B_E02_FINAL_CONSOLIDATED_REPORT.md`, Git blob `c6a113cd6a7534a6a7347e63ef45176c350e2c85` | Report committed after tested SHA; reports synthetic-only feasibility. Not production assurance. |
| `S07` | E0.2 source in `experiment/m102-f2b-e02-20261116-fdae362`: `env.py`, `tests/test_e02_f2b_suite.py`, `versions/exp_f2b_h8.py`, `harness/upgrade_wrapper.py`, `.github/workflows/m102-f2b-bounded-e02.yml` | Source-grounded observations underlying A01–A08. Record immutable Git object IDs again if later executed. |
| `S08` | Recorded `main` baseline `fdae362e1a889831975060808ac612369d3b0d0a` | Historical E0.2 base, **not** an assertion that all future refs remain unchanged. Official Tenant migration lineage observed as `tp0001`–`tp0007`; official runtime runner still defaults to `head` at inspected baseline. |
| `S09` | Missing `M102_F2B_SOURCE_RECONCILIATION_AND_BOUNDED_EXPERIMENT_AUTHORIZATION_E0.1.md` | Original E0.1 was not recovered. E0.2 was an explicitly approved replacement and E0.3 is a **new** corrective proposal; do not fabricate E0.1 sections. |

### 1.3 Prior result: precise evidence status

**Preserve as historical fact:** the green E0.2 CI run, its negative PostgreSQL errors, disposable service cleanup, reported evidence and exact tested SHA. **Preserve as unresolved:** coverage gaps A01–A08. Neither 14/14 pytest success nor two-head *synthetic* feasibility equals full E0.2 contractual acceptance, app/Sync compatibility, official Phase-6/8 readiness, Package 1 authorization, or any ACR/Gate decision.

### 1.4 Non-goals and protected allocations

No official `TP0008+` migration may be created, edited, run, renumbered, stamped, or approved. No claim of assigning `TP0011` or `TP0023` is allowed beyond the explicitly *proposed* R4.15 mapping. Do not modify official `migrations/**`, `src/**`, `tests/**`, `ops/**`, `docs/**`, RLS policies, official Alembic runner, architecture baseline, roadmap or approved records. Keep Package 1 preflight separate from Package 4 Lease/Erasure tests; maintain distinct Gates A, B, C and D. A successful E0.3 may only support **design/evidence consideration** in a separate later ACR process.

---

## 2. Approval gates and proposed future authority (currently CLOSED)

### 2.1 Present status

- **`E03-G0 = PROPOSED / NOT EFFECTIVE`**. No execution under E0.3. No user statement requesting this draft is an authorization to run it.
- **`E02-GRANT = TERMINATED`** upon delivery of the E0.2 consolidated final report (recorded 2026-11-16). The previous 2026-11-23 Berlin outer deadline does **not** extend its life.
- **`F2-B = PROPOSED DESIGN`**, even if independent reviews agree that the R4.15 *document* is internally consistent.
- **`E03-EXPIRY = UNSET`**; an unexpired, affirmative future PO grant is an indispensable precondition. No placeholder date is an executable deadline.

### 2.2 Proposed PO authorization checklist — do not presume completion

A **new, distinct affirmative PO decision** would have to record: (1) complete exact E0.3 filename and SHA-256 of its final reviewed bytes; (2) executor **Cursor only**; (3) one independent experiment branch and explicit path allowlist in §3; (4) only disposable PostgreSQL 15, fabricated records and dummy keys; (5) the chosen, explicitly acknowledged **branch-restricted CI `push` mode** in §7 or an independently approved replacement CI plan; (6) an **absolute end time in UTC** and the earlier-of-final-report-delivery stop; (7) confirmation that all official code, migration, main, merge, ACR and Gate exclusions remain in force; and (8) whether an optional Draft PR is permitted (this proposal defaults to **no PR**). Approval must not be inferred from a model's endorsement or a successful run.

**Until every field is unambiguously approved:** Cursor must answer `BLOCKED_APPROVAL`, perform at most authorized read-only inspection, and **not** open the experiment or invoke any workflow.

### 2.3 Review and activation workflow

1. ChatGPT independently reviews the complete proposed artifact and corrects defects in one complete Markdown file.
2. Gemini independently reviews the **entire** file against the exact E0.2 contract, code, report, CI logs and A01–A08, correcting defects in one complete revised file when necessary.
3. Continue independent review to document-level convergence. **Neither reviewer may turn a proposed technical contract into permission.**
4. After review, the PO may separately decide whether to approve the exact final digest with the fields in §2.2. Approval, if given, is only for the bounded corrective experiment; it is **not** approval of F2-B's official migration DAG.

---

## 3. Proposed immutable baseline, branch, write allowlist, and isolation

**This entire section is conditional on a future valid §2.2 approval.**

### 3.1 Preserve E0.2 evidence without rewriting it

The E0.2 branch, test implementation, CI logs, artifacts, contract, consolidated report, JSON evidence and checksums are **historical evidence** and MUST remain unchanged. Never alter, cherry-pick into an official branch, amend, force-push, rewrite or relabel the original evidence. E0.3 results must carry **new IDs**, new evidence files and new source-SHA provenance; a new green run cannot retroactively change the outcomes or acceptance status of E0.2.

### 3.2 Proposed branch and exclusive write allowlist

After read-only verification of the E0.2 final evidence commit and a clean worktree, create **one new branch**, named `experiment/m102-f2b-e03-<YYYYMMDD>-<short-verified-source-sha>`, from the exact verified E0.2 **final evidence commit** (record its full SHA; do not assume the short label `471f884` is sufficient evidence). Using that parent preserves direct provenance without changing its source branch. **No second branch** and no edits to the parent are permitted. If the base changes or the source cannot be verified, STOP rather than guessing or reconstructing missing content.

| Repo-relative path | Proposed permission | Constraints |
|---|---|---|
| `experiments/m102_f2b_bounded_e03/**` | **Only authorized experiment write subtree** | Minimal independent E0.3 harness, copied/adapted *synthetic* sources, tests, evidence, proofs and ONE consolidated report. Distinct schema/DB/role/revision names prefixed `exp_e03_`, not the official Tenant version table and not E0.2's mutable resources. Never copy secrets, patient data, DB dumps, or unidentified external code. |
| `.github/workflows/m102-f2b-bounded-e03.yml` | **Conditional, single new CI workflow file** | Only if required for genuine disposable PG15 evidence and the §7 CI admission gate passes. No existing workflow modifications. Least-privilege, no deployment, and explicit experimental event/branch/path restrictions. |

Everything else, **including the complete `experiments/m102_f2b_bounded_e02/**` tree and its historical workflow**, is read-only. No edits to `.gitignore`, `README.md`, `pyproject.toml`, `docs/**`, `migrations/**`, `src/**`, `tests/**`, `ops/**`, or existing `.github/**`. Test outputs, bytecode, pip cache and temporary databases must live outside the tracked worktree or within the E0.3 evidence folder as permitted; do not let incidental writes escape the allowlist. Reject symlinks, submodules, `..`, absolute-path escapes, and path-casing tricks. No force push, `git reset --hard`, `git clean`, blanket `git add .`, merge, or official PR.

### 3.3 Environment constraints

- Fresh, single-purpose PostgreSQL **15.x**, with version verified from the **actual connected server** (`SHOW server_version_num` in `[150000,159999]`), ownership and network endpoints checked **before** any SQL state change; no persistent volume or inherited production URL.
- Synthetic tenants and deterministic non-patient examples; cryptographic values are **test-only non-secret** material, not real HMAC/encryption keys. Never log a real credential or accept privileged external networks.
- Provisioning/admin role used exclusively for controlled temporary setup and independent inspection. Test migrator and test app actors must be demonstrably **NOSUPERUSER**, **NOBYPASSRLS** and least privileged; exact `session_user`, `current_user`, and relevant role memberships must be captured.
- Experimental Alembic environment and version table only; explicitly reject `alembic_meta.alembic_version_tp`, any `TPxxxx` revision, official migration files or real Cloud/Local databases. Any fallback to admin privileges, source mismatch, unsafe SQL endpoint or forbidden negative-test success is an immediate **`STOP_SECURITY`**.
- Enforce finite job/test timeouts and cleanup before the **earlier** of a future PO-fixed expiry or the final report. Record cleanup facts with actual runtime evidence, not assertions of universal resource absence.

---

## 4. Defect-by-defect corrective acceptance contract

A test is **`OBSERVED_PASS` only when its complete expected/actual evidence is present**. A Python assertion passing is not alone proof of every contractual subcondition. Each row below defines a minimal case; tests may use helpers, but one passing high-level pytest function MUST NOT silently substitute for multiple untested subconditions. Reuse older E0.2 evidence only for explicitly unchanged historical facts, and label it `HISTORICAL_E02`, never `EXECUTED_E03`.

### A01 — Migration role fallback must fail closed (**HIGH**)

**Observed defect:** E0.2 `env.py` tries `SET ROLE exp_f2b_migrator`, catches exceptions, rolls back and continues to `context.configure()`; this does not establish a restricted effective role. It is a latent fail-open path, **not** proof that elevated migrations actually occurred in the green CI run.

**Corrective invariant:** Before any migration DDL or Alembic stamp, the experimental runtime MUST positively verify the exact intended `current_user`, allowed `session_user`/membership, `rolsuper = false`, `rolbypassrls = false`, and required least privileges. Failed `SET ROLE` or failed identity check MUST abort without DDL, stamp or fallback. A cleanup rollback is not permission to continue. No privileged login may be silently substituted.

| Case ID | Required physical proof | Mandatory negative / positive result |
|---|---|---|
| `E03-A01-P01` | Valid restricted migrator path; capture identity and version table before/after targeted synthetic migration | DDL occurs only under allowed restricted role and the expected stamp advances; no unintended role privileges |
| `E03-A01-N01` | Deliberately force a `SET ROLE` denial or wrong current user in an **isolated synthetic** fixture | Immediate controlled error; no migration body, object mutation, or stamp; no privileged fallback; record SQLSTATE and identity |

**Reject:** testing only successful `SET ROLE` without the failure path; swallowing an exception; relying only on comments or mocks.

### A02 — Phase-8 actual `NOT NULL` **and** validated `CHECK` (**HIGH**)

**Observed defect:** E0.2 Phase-8 adds and validates a CHECK but never sets `lookup_hmac_next` to column `NOT NULL`; test 09 fetches `attnotnull` yet asserts only `convalidated`.

**Corrective invariant:** In a *synthetic, separate* Phase-8 migration, check index validity, backfill completion, correct dual-write/old-writer fence and explicit constraint safety, then perform an **actual** `ALTER COLUMN lookup_hmac_next SET NOT NULL` and validate the required CHECK. Inspect **both** `pg_attribute.attnotnull = true` and `pg_constraint.convalidated = true` (correct relation/column/constraint OIDs), together with `pg_index.indisvalid` and `indisready`. Switch simulated authority only after all guards have passed within an appropriately bounded transaction. No official Phase-8 claim.

| Case ID | Required physical proof | Mandatory result |
|---|---|---|
| `E03-A02-N01` | Existing NULL next digest / incomplete backfill; attempt cutover | Cutover refused; old authority and version stamp unchanged; no unsafe success |
| `E03-A02-P01` | Fully prepared fixture; execute synthetic Phase-8 | Real `attnotnull=true`, validated CHECK, valid index and guarded authority switch, catalog proofs attached |
| `E03-A02-N02` | Simulate invalid/absent NOT NULL or unvalidated CHECK while cutover guard is evaluated | Guard denies authority switch, including when a separate metadata flag misleadingly says “ready” |

**Reject:** `CHECK (col IS NOT NULL)` as a substitute for `attnotnull=true`; checking a different table/constraint; updating metadata before catalog verification.

### A03 — Real overlapping writers and stale/offline-writer fencing (**HIGH**)

**Observed defect:** E0.2 test 10 uses sequential writes; no deterministic overlapping transactions or old-writer fencing proof.

**Corrective invariant:** Use at least **two independent PostgreSQL connections and overlapping transactions**, with deterministic synchronization points, bounded lock timeouts, an externally visible ordering trace and final authoritative DB assertions. Old and next hashes for a write MUST derive from the same synthetic canonical input and commit atomically. The old active uniqueness rule MUST remain effective throughout the test. A simulated stale/pre-drain/offline Local writer MUST be refused at the **admission/fencing** boundary; merely relying on a later NOT NULL failure is insufficient to prove writer lifecycle fencing. Model a monotonic synthetic generation/epoch token and a fail-closed admission decision, without asserting the real application implements it.

| Case ID | Required physical proof | Mandatory result |
|---|---|---|
| `E03-A03-P01` | Two concurrent sessions with identical active identity, staged interleaving, one commit and one conflicting writer | At most one authoritative identity write commits; collision/rollback and old/next atomicity observed; timeline and SQLSTATE preserved |
| `E03-A03-N01` | Stale old-version writer/offline-writer token before and after simulated drain/cutover | Explicit fence denies stale actor **before protected write**; no change to active authority, new index, version or table state; unknown token denies |

**Reject:** sequential writes described as concurrent; sleep-only nondeterminism; automatically calling this a proven `Zero-Race-Window` for production.

### A04 — Cloud/Local mixed-head **admission decision** and Sync fencing (**HIGH**)

**Observed defect:** E0.2 test 12 created Cloud/Local-named logical DBs and compared Alembic rows, without exercising an admission/fencing decision.

**Corrective invariant:** Two genuinely independent disposable synthetic databases (separate containers if needed for independent fault simulation) must represent `{base, HMAC-only, Catalog-only, both}` with an **explicit reviewable admission-policy table**. The default is **DENY** for unknown, missing or contradictory head sets. Every allowed pair must have a declared synthetic protocol compatibility rationale; disallowed pairs must be rejected **before** simulated Sync/read/write, preserving source and destination state. Test directionality, stale/unknown/multiple-head combinations and fail-closed behavior. Do not infer real Cloud/Local Sync or worker compatibility.

| Case ID | Required physical proof | Mandatory result |
|---|---|---|
| `E03-A04-P01` | An expressly allowlisted synthetic version pair, plus the exact policy row and two DB version inventories | Admission only when explicitly listed; authorized synthetic operation has bounded expected effect |
| `E03-A04-N01` | Unlisted/mismatched/reversed/stale/unknown head states; deliberately attempt the synthetic operation | Admission is denied before mutation, with recorded policy reason and unchanged inventories/data |

**Reject:** proof consisting only of two version-table SELECTs; treating Catalog independence in the synthetic DAG as application or Sync compatibility.

### A05 — CI trigger, scope and terminated-grant governance (**MEDIUM/HIGH**)

**Observed deviation:** E0.2 authorized a PR-oriented CI plan, but its successful run was triggered by `push`; the workflow also checked only the fixed expiry, not the earlier report-delivery termination. This was a contract-governance defect, not evidence of production deployment.

**Proposed E0.3 disposition:** **Do not retroactively excuse E0.2.** If a new PO grant explicitly adopts this E0.3 **including this paragraph**, the authorized default CI mode shall be **one narrowly scoped, experiment-branch-only `push`** workflow, because an unmerged newly authored workflow is not automatically eligible for arbitrary PR base-branch events. This is an **intentional proposed E0.3 policy change**, not permission borrowed from E0.2. No `pull_request`, `pull_request_target`, `workflow_dispatch`, schedule, secrets, privileged token, environment deployment, self-hosted runner or production service. The workflow must restrict **branch and changed paths** to E0.3 harness/tests/new workflow; evidence-only publication MUST NOT cause a second CI run. If the PO disallows this changed CI mode, or if event/branch/permissions behavior cannot be verified read-only, return **`BLOCKED_CI_SCOPE`**. No silent fallback to another event type. No Draft PR under this E0.3 proposal.

The CI runner cannot by itself reliably learn that a report was delivered *outside* the tested commit. Therefore, **do not claim an automatic hard revocation that cannot be enforced**: record future PO-fixed expiry, stop new pushes and queued work at or before that expiry, prohibit any run/rerun after final delivery, publish evidence-only final commit without triggering CI, and record residual GitHub manual-rerun risk. If the required operational controls cannot be demonstrated, BLOCK rather than pretend the cutoff is technically enforced.

| Case ID | Proof | Mandatory result |
|---|---|---|
| `E03-A05-C01` | Pre-execution CI event/permissions/branch/path/timeout gate; successful isolated run ID/event SHA if authorized; evidence-only push behavior and closure timeline | Approved **new** CI trigger used exactly; no unrelated workflow/deployment/privileged event; no post-final work. A simulated/adversarial unexpected trigger is refused. |

### A06 — Autocommit role restoration, invalid indexes, role-grant negatives (**MEDIUM**)

**Observed gaps:** E0.2 test 07 did not verify restricted role across the autocommit boundary; test 08 allowed a missing invalid-index state without a mandatory valid explanation; test 11 omitted role-grant mutation negatives.

| Case ID | Required physical proof | Mandatory result |
|---|---|---|
| `E03-A06-P01` | PostgreSQL `session_user`, `current_user`, `rolsuper`, `rolbypassrls` and transaction/role evidence immediately **before**, **inside**, and **after** `autocommit_block()` | Correct restricted role persists/restores as specified; `CREATE INDEX CONCURRENTLY` succeeds only outside a transaction; unexpected identity aborts |
| `E03-A06-N01` | Engineered duplicate next-digest causes failed `CREATE UNIQUE INDEX CONCURRENTLY`; inspect `pg_index` and version metadata before recovery | If an invalid index is left, record exact `indisvalid=false`, `indisready`, unique status, forbid false enforcement/stamp; safe explicit drop/repair/retry then inspect valid result. If PostgreSQL legitimately leaves no index for the chosen failure mode, **do not claim that invalid-index remediation was tested**: construct an appropriate separate fixture or mark this proof `BLOCKED` with evidence. |
| `E03-A06-N02` | Restricted app actor attempts `GRANT`, `ALTER ROLE`/role membership privilege escalation, mutation of version metadata, and cross-tenant RLS violations | All forbidden operations denied at correct privilege/RLS boundary, no state change and no bypass; negative SQLSTATE/observed catalog state attached |

**Reject:** role-restoration assertion only after a connection reset; admin-privileged test connection masquerading as a restricted user; treating any exception as sufficient without checking state.

### A07 — Source-to-test safety manifest and forensic-quality evidence (**MEDIUM**)

**Observed gap:** E0.2 safety manifest and per-test JSON lack consistently required rationale, preconditions, negative stop rules, commands, role/database information and catalog observations.

| Case ID | Proof | Mandatory result |
|---|---|---|
| `E03-A07-C01` | Machine validation of §6 evidence schema for **every required E0.3 case**, plus independent SHA-256 manifest | No absent required field, unknown classification, missing actual SHA/CI ID, unredacted sensitive material, skipped-as-pass or mismatched digest |
| `E03-A07-C02` | Complete **pre-execution** §5.1 safety manifest with one row per ID in this §4 and source anchors; observed post-run test matrix | Every criterion mapped to source rationale, precondition, exact expected positive/negative state, role, transaction boundary, allowed path, stop rule, evidence location and actual outcome |

**Reject:** reconstructing missing preflight evidence after running without labeling it retrospective; publishing only a green pytest line or metadata-only JSON as full proof.

### A08 — Enforced diff allowlist rather than a cosmetic CI step (**MEDIUM**)

**Observed gap:** E0.2 CI checked branch name, folder existence and absence of one dummy migration file but did not compare the complete change set against the allowlist. An independent inspection nevertheless found the actual E0.2 diff in scope.

| Case ID | Proof | Mandatory result |
|---|---|---|
| `E03-A08-N01` | Unit-test the path guard with injected `migrations/**`, `src/**`, existing workflow, symlink, rename, traversal and case-collision cases **inside synthetic test inputs only** | Fail-closed before test/DDL/push; list every offending path; no actual forbidden repository edit |
| `E03-A08-P01` | CI `git diff` of **full pinned approved base → tested SHA** (including additions, deletions, renames, modes and relevant submodule/symlink metadata) and final independent `git status`/diff | Exactly the two new E0.3 allowlist entries; all unrelated tracked paths unmodified. The guard must execute **before** the PG15 test step, and failures must block further steps. |

**Reject:** checking one representative path, only the last commit, or a self-reported clean diff without actually enumerating changes.

### Cross-cutting regression and closure cases

| Case ID | Proof | Mandatory result |
|---|---|---|
| `E03-REG-P01` | Limited regression on synthetic two-head topology, explicit branch-qualified targets, rejection of `head`/`heads`, old active uniqueness and catalog-only independence on the modified E0.3 harness | Existing established safety properties still hold; no need to rerun unrelated E0.2 suites unless dependency mapping identifies a changed behavior |
| `E03-CLOSE-C01` | Server/version/endpoint evidence, immutable historical E0.2 references, new branch/CI SHA, checked allowlist, owned-resource disposal, future grant cutoff and final report-delivery time | Cleanup before delivery; status honestly terminates; no action after final report. State unresolved external dependencies without claiming them closed |

**Prescribed case inventory: 19 IDs.** Some are governance/evidence controls (`C01`) and not physical PostgreSQL test functions; report **both** physical PG15 case counts and all-contract case counts separately. Do not claim “19 PG15 tests” or “19/19 contractual criteria satisfied” based merely on pytest collection counts.

---

## 5. Conditional future execution sequence and STOP gates

**This sequence is a specification, not a present instruction to act.**

1. **`G0 — independent review and fresh PO authorization`:** complete independent review of E0.3, then check exact SHA, scope, executor, fixed new UTC expiry, selected CI mode and PO's affirmative words. Missing/ambiguous -> `BLOCKED_APPROVAL`, no writes.
2. **`G1 — read-only source reconciliation`:** verify real repository remote, current `main`, final E0.2 evidence commit, branch topology, E0.2 contract digest, R4.15 candidate source/approval state, frozen spec clauses 771–772, clean worktree, all A01–A08 baselines and non-duplicated test rationale. Any discrepancy needing an official change -> `BLOCKED_SOURCE_OR_SCOPE`.
3. **`G2 — safety manifest`:** independently construct all 19 traceability rows in memory **before** branch/work; verify path allowlist, exact CI event policy, no untrusted DB endpoints, planned roles, PG version, time, temporary resource ownership, negative-case handling and cleanup strategy. Missing entry -> `BLOCKED_PREFLIGHT`.
4. **`G3 — isolated branch and experiment-only corrections`:** create one new E0.3 branch from verified E0.2 final evidence commit; create **only** new E0.3 files. Copy/port the minimum required synthetic experiment components into E0.3 without changing any E0.2 files. No official migrations, no patient data and no real keys.
5. **`G4 — case execution`:** provision disposable PG15, verify endpoint/roles, run case-level negatives and positives; immediate `STOP_SECURITY` if any forbidden operation succeeds or role/DDL/status guard fails. Preserve failed-run traces with truthful classification. Make bounded corrections only within §3 allowlist if a **new** authorized attempt remains inside the PO-fixed window; never hide prior failures.
6. **`G5 — safe CI provenance`:** when CI is genuinely necessary, verify §7 source event/permissions and test SHA, execute the one scoped workflow, collect raw logs/JUnit/catalog outputs, confirm no skip and upload evidence. A green CI is not enough without §4 criteria evidence. No automatic run after final report.
7. **`G6 — consolidate and terminate`:** clean up owned resources, verify branch/diff/path integrity, and publish exactly **one** final consolidated Markdown report. Delivery **immediately terminates** any future E0.3 execution permission. If blocked before any branch/write, report the blocker only in Cursor's final response; do not make a repository file.

**Universal STOP conditions:** approval mismatch or expiry; dirty/unsafe worktree; unauthorized path; unmatched baseline; use of a real/persistent/shared/patient-bearing DB, real secret or production endpoint; privilege fallback; successful unauthorized grant/RLS bypass; invalid index falsely treated as valid; missing `NOT NULL` or CHECK while authority changes; stale writer admitted; unsafe CI event/secret/permission; unexpected workflow; failure to collect provenance; after report delivery. Classify as `STOPPED_SECURITY`, `BLOCKED_*`, `EXPIRED`, or `INCOMPLETE`, never silently reinterpret a failure as PASS.

---

## 6. Mandatory evidence structure and classification

### 6.1 Pre-execution manifest schema

One row per §4 ID must include: `case_id`, `finding_id`, `source_uri_and_immutable_sha`, `rationale`, `preconditions`, `synthetic_db_and_role`, `transaction_boundary`, `proposed_allowed_write_paths`, `expected_positive`, `expected_negative`, `stop_rule`, `evidence_destination`, `regression_dependency`, `run_eligibility`. This matrix is produced **before** execution; an updated observed-result matrix must preserve that original preflight record.

### 6.2 Per-case evidence schema

Every executed test/control must have **real**, redacted, independently linkable fields:

```json
{
  "case_id": "E03-A02-P01",
  "finding_id": "A02",
  "classification": "OBSERVED_PASS",
  "execution_kind": "PHYSICAL_PG15",
  "contract_sha256": "<final E0.3 digest, independently checked>",
  "parent_e02_final_commit_sha": "<verified full SHA>",
  "tested_commit_sha": "<full SHA actually checked out by runner>",
  "run_id": "<actual CI run ID or LOCAL_NOT_CI>",
  "timestamp_utc": "<actual ISO8601 UTC timestamp>",
  "postgres_server_version_num": 150020,
  "database_label": "<synthetic ephemeral identifier>",
  "session_user": "<captured identity>",
  "current_user": "<captured identity>",
  "preconditions": "<observed values>",
  "command_redacted": "<real invocation / SQL operation>",
  "expected_result": "<falsifiable condition>",
  "observed_result": "<actual catalog outputs / return value / SQLSTATE>",
  "exit_code": "<real exit code or NOT_APPLICABLE_WITH_REASON>",
  "before_state": "<redacted pg_catalog / version / data fingerprint>",
  "after_state": "<redacted pg_catalog / version / data fingerprint>",
  "evidence_files": ["<repo-relative E0.3 evidence path>"],
  "limitations": ["<unverified external facts>"]
}
```

The JSON above is a **schema illustration, not evidence**; no sample constant (including `150020`) is a claimed future server result. If a field is truly not applicable, record explicit `NOT_APPLICABLE` **with rationale**, not an omitted value or invented success. For controls without a PostgreSQL connection set `execution_kind` to `GOVERNANCE_CONTROL` and specify why database fields do not apply. Do not write secrets, live connection strings, patient identifiers or credential-bearing logs.

SHA-256 of each completed evidence file belongs in a **separate immutable manifest** to avoid self-referential hashing. The final report must cross-reference the matching test source SHA, CI job and evidence manifest. Preserve the difference between `HISTORICAL_E02`, `EXECUTED_E03`, `OBSERVED_PASS`, `OBSERVED_FAIL`, `BLOCKED`, `NOT_RUN`, `UNVERIFIED`, and `REVIEW_ONLY`. `SKIPPED` is never `PASS`.

### 6.3 Two distinct success metrics

1. **Execution metric:** number of collected/actually executed/failed/skipped pytest functions, plus PostgreSQL version and relevant physical logs.
2. **Contract metric:** the full 19-case matrix with **separate statuses per case** and the subcondition-level positive/negative evidence. A test function may cover multiple cases only where evidence independently demonstrates each case's criteria. Any missing mandatory subcondition prevents the case from being `OBSERVED_PASS`.

A classification of **`CORRECTIVE_EVIDENCE_SUFFICIENT_FOR_GOVERNANCE_REVIEW`** is permitted only if all mandatory E0.3 subconditions were actually verified and independently audited. This **still does not approve F2-B or official implementation**. If at least one criterion is unproved, use **`CORRECTIVE_EVIDENCE_INCOMPLETE`** with the exact blocked IDs and evidence needed.

---

## 7. Proposed CI workflow admission and termination policy

**Not authorized now.** For a future explicitly PO-approved E0.3:

- **Single new workflow:** `.github/workflows/m102-f2b-bounded-e03.yml`; `permissions: contents: read`; `actions/checkout` with persisted credentials disabled; hosted ephemeral runner only; `postgres:15` (pin to an exact patch/digest when feasible); test-specific generated credentials and no external secrets. No `pull_request_target`, manual dispatch, schedule, reusable privileged workflow, deployment environment, existing workflow edits or merge.
- **Proposed event:** branch-filtered `push` only on `experiment/m102-f2b-e03-*`, with **positive path filters for E0.3 harness/test/source and that one new workflow** and explicit exclusion of E0.3 `evidence/**` so a final evidence-only push does not rerun tests. This is a deliberate, **separately approvable difference from E0.2**, not a retrospective waiver.
- **Preflight code:** enumerate `git diff --name-status` (including rename/copy and mode changes) and verify the entire **verified E0.2 final parent → checked-out E0.3 SHA** range, not merely the most recent commit, against the strict allowlist. Verify no unsafe symlink/submodule. Check trigger event, branch, pinned commit, time and runtime privileges **before** installing packages or performing SQL. An injected-path unit test must demonstrate the guard refuses out-of-scope content; the real branch diff must also be checked.
- **No implicit CI acceptance:** job must stop if the PO grant or its fixed expiry is unverifiable, tests are skipped, PG version differs, role checks fail, a negative fails, evidence files are incomplete or unexpected workflows run. A GitHub `success` result is only one evidence field. Preserve all failing attempts and exact CI IDs.
- **Termination:** after the final report is delivered, no new branch push, manual CI rerun, PR edit, code write, test or cleanup needing new access is permitted under that grant. CI cannot inherently prove an externally delivered report did not already terminate the grant; retain a human/audit control and explicitly classify this limitation. If a true enforceable revocation mechanism is required but unavailable within scope, STOP and seek a new policy decision rather than claim one exists.

**Alternative event modes** (e.g. Draft PR) are not silently authorized. They require an independent, exact new PO decision and a revised reviewed contract before any action. E0.3 does not authorize an official PR merge.

---

## 8. Final report content and governance decisions

If E0.3 is later separately authorized and run, produce **one complete** file at `experiments/m102_f2b_bounded_e03/evidence/M102_F2B_E03_FINAL_CONSOLIDATED_REPORT.md` after all safe cleanup, containing:

1. The exact new PO approval quotation, E0.3 filename/SHA, authorized window and CI event; explicit statement that E0.2 had terminated.
2. Frozen spec source SHA, R4.15 exact review-candidate provenance, E0.2 historical tested/evidence SHAs, E0.3 parent/tested/final SHAs, entire changed-path manifest and actual privilege/isolation proof.
3. Exact A01–A08 resolution matrix and all **19 case IDs** with individual expected/observed evidence, source anchors, timestamps, return codes and independent digests; do not suppress historical E0.2 failures or negative E0.3 runs.
4. Clear separation between physical PG15 results, governance control results, borrowed historical evidence, and `UNVERIFIED` real application/Sync/Cloud–Local/offline-writer behavior.
5. All CI event/run/artifact URLs, actual resource cleanup, any optional deviations explicitly approved, incident/STOP reasons and completion time.
6. Explicit status: `CORRECTIVE_EVIDENCE_SUFFICIENT_FOR_GOVERNANCE_REVIEW` **or** `CORRECTIVE_EVIDENCE_INCOMPLETE` / `STOPPED_SECURITY` / `BLOCKED_*`, as supported. Never report approval of F2-B, real migrations, Package 1, ACR, or Gates A–D.
7. One **next PO decision**, which may be: request independent governance/ACR feasibility review, authorize another separate bounded investigation, or keep F2-B blocked. **No PO decision is presumed.**

**No automatic progression:** even a fully passing E0.3 must stop at a *reviewable experimental evidence package*. A new migration/governance ACR would require separate design, signer/approval chain and implementation authorization, real official runner/transaction/roles/Sync compatibility proofs, and independent audit. SRC-10 and SRC-12 are not silently closed by synthetic evidence.

---

## 9. Mandatory Cursor completion marker (only for a future authorized task)

Every *future* Cursor response on E0.3 must close with an unambiguous truthful status. For an actual final response use `EXECUTION STATE: TERMINATED` and never continue after the marker:

```text
TASK STATUS: COMPLETED / BLOCKED / FAILED
CONTRACT: M102 F2-B E0.3 (APPROVAL_STATUS: PROPOSED / APPROVED-AND-VERIFIED)
EXECUTION STATE: NOT STARTED / IN PROGRESS / TERMINATED
WORK PERFORMED: <precisely observed actions; distinguish code edits from executed tests>
EVIDENCE: <verified paths, hashes, CI runs; or NONE>
OPEN FINDINGS: <A01-A08, case IDs and why; or NONE>
NEXT ACTION FOR PRODUCT OWNER: <exactly one concrete action, or NONE>

=== END OF CURSOR RESPONSE ===
```

A blocked or expired task must say `TASK STATUS: BLOCKED` and, if final, `EXECUTION STATE: TERMINATED`; do not say `COMPLETED` when mandatory work was prevented.

---

## 10. Traceability, unresolved dependencies, and draft change log

### 10.1 A01–A08 completeness index

| Finding | Mandatory E0.3 proof IDs | Original deficient E0.2 criterion | Document disposition |
|---|---|---|---|
| A01 | `E03-A01-P01`, `E03-A01-N01` | Privilege fallback in experiment Alembic `env.py` | **PROPOSED** fail-closed fix + physical role-failure test |
| A02 | `E03-A02-N01`, `E03-A02-P01`, `E03-A02-N02` | `E02-F2B-09` | **PROPOSED** real NOT NULL/CHECK and negative guards |
| A03 | `E03-A03-P01`, `E03-A03-N01` | `E02-F2B-10` | **PROPOSED** concurrent writes + stale-writer fence |
| A04 | `E03-A04-P01`, `E03-A04-N01` | `E02-F2B-12` | **PROPOSED** actual synthetic admission decision |
| A05 | `E03-A05-C01` | E0.2 CI event mismatch and termination | **PROPOSED** explicitly new scoped CI governance mode |
| A06 | `E03-A06-P01`, `E03-A06-N01`, `E03-A06-N02` | `E02-F2B-07`, `08`, `11` | **PROPOSED** autocommit role/index/role-grant negatives |
| A07 | `E03-A07-C01`, `E03-A07-C02` | E0.2 §5.1-D and per-case evidence | **PROPOSED** preflight + schema validation |
| A08 | `E03-A08-N01`, `E03-A08-P01` | E0.2 CI path guard | **PROPOSED** tested denylist injection + full-range real diff |
| Cross-cutting | `E03-REG-P01`, `E03-CLOSE-C01` | Regression and closure invariants | **PROPOSED** limited regression + terminal evidence |

**Arithmetic cross-check:** 2 + 3 + 2 + 2 + 1 + 3 + 2 + 2 + 2 = **19** distinct case IDs. All are **PROPOSED / NOT EXECUTED** at drafting time.

### 10.2 Still-open external dependencies

- **Real Cloud/Local Sync and admission:** requires authentic application/Sync code, device lifecycle and actual migration state contracts. Synthetic model is not a substitute.
- **Official Tenant Alembic operations:** the existing runner, version table, role transaction semantics, multi-head policy and startup/deploy orchestration require separate source-grounded architecture decisions and PostgreSQL 15 acceptance.
- **Phase-6/8 production migration and old-writer life cycle:** actual dual-writing workers, key rotation, rollback/retirement and bounded offline Local Hub fencing are not proven by experimental clones.
- **Formal governance:** migration DAG/numbering ACR and competent signatories, effective roadmap authority, SRC-10, SRC-12, Package 1 authorization and Gate A–D remain independent and open wherever not separately evidenced.

### 10.3 Change log

| Revision | Date | Change | Evidence grade |
|---|---|---|---|
| `E0.3 PROPOSED` | 2026-11-17 | New standalone corrective contract replacing **no** historical file; closes the design of eight A01–A08 remediation tasks, defines 19 auditable controls, a separate proposed CI governance policy, immutable E0.2 evidence and explicit PO authorization/termination gates. | `DOCUMENT_DRAFTED / NOT EXECUTED / NOT APPROVED` |

**Draft disposition:** `E0.3 PROPOSED — READY FOR INDEPENDENT DOCUMENT REVIEW ONLY`  
**Explicitly not:** `E0.3 APPROVED`, `EXPERIMENT RUN`, `F2-B APPROVED`, `PACKAGE 1 AUTHORIZED`, `ACR SIGNED`, `GATE A–D ACCEPTED`.

=== END OF E0.3 PROPOSED CONTRACT ===

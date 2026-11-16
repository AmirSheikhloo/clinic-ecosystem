# M102 F2-B — Replacement Source Reconciliation and Bounded Experiment Contract

**Artifact ID:** `M102_F2B_REPLACEMENT_BOUNDED_EXPERIMENT_CONTRACT_E0.2`  
**Revision:** `E0.2 — PROPOSED / NOT EFFECTIVE`  
**Prepared:** 2026-11-16  
**Project:** Clinic Ecosystem  
**Repository:** `AmirSheikhloo/clinic-ecosystem`  
**Intended executor:** Cursor only  
**Approval authority:** Product Owner (PO), by a **new, explicit, artifact-identifying approval**  
**Language:** English is normative for the execution contract; the owner-facing explanation can be Persian.

> **CRITICAL PROVENANCE NOTICE:** This is a **new, independently drafted replacement proposal**, not the recovered text, reconstruction, amendment, or verified continuation of the unavailable `M102_F2B_SOURCE_RECONCILIATION_AND_BOUNDED_EXPERIMENT_AUTHORIZATION_E0.1.md`. The original E0.1 §§5.1–5.3 were not available to the drafter or to Cursor. No wording, path allowlist, or test list in this E0.2 is represented as coming from that missing document. The existing PO permission referenced *only* the missing E0.1. **E0.2 creates no new execution authority until the PO separately approves this exact E0.2 artifact.** If the original E0.1 is subsequently found and conflicts with this replacement, STOP and request an explicit reconciliation decision; do not silently combine the two.

## 1. Approval and effective-status rules

1. **Current state is `PROPOSED / NOT AUTHORIZED TO EXECUTE`.** Until this complete file has been read by the PO and expressly approved by an affirmative message identifying the exact **filename and SHA-256**, Cursor may perform **read-only source inspection only**. Do not create a branch, edit files, start a database, run tests, push, open a PR, or launch Actions on the strength of this draft.
2. A qualifying PO decision may read: **“I expressly approve `M102_F2B_REPLACEMENT_BOUNDED_EXPERIMENT_CONTRACT_E0.2_PROPOSED.md`, SHA-256 `<actual file digest>`, as the replacement bounded F2-B experiment contract for Cursor only, within all stated limits; this is not Package 1, an official migration, an ACR signature, or Gate A–D acceptance.”** The PO must supply the actual file digest; Cursor must calculate and match it before any action. The proposed status on the file does not self-convert into approval. No signature, approval, or consent may be inferred from this drafting request.
3. After valid approval, the *outer bounds* remain exactly those stated by the PO on 2026-11-16: **Cursor only**, one new independent experiment branch, **fresh disposable PostgreSQL 15**, **synthetic data only**, only the paths designated in §4, and at most **one optional Draft PR** solely if necessary for safe GitHub Actions execution. All official Package 1 work, official migration/application edits, any real/persistent DB access, patient data, real keys, PR merge, ACR signature, and Gate A/B/C/D acceptance remain forbidden.
4. **Hard expiry:** authorization ends at the **earlier** of (a) delivery of **one consolidated final report** or (b) **2026-11-23 23:59:00 Europe/Berlin (CET; 2026-11-23T22:59:00Z)**. At or after the boundary, no further work under this grant. The approval, if given, does not reset or extend this deadline. A new PO approval would be required for any continuation.
5. **Priority:** the PO's explicit exclusions and the frozen specification always constrain this experiment. E0.2 defines only an experimental proof-of-feasibility envelope; it does **not** supersede the architecture baseline, establish an implementation roadmap, amend any official revision numbering, or approve the proposed F2-B migration design.

## 2. Grounding, provenance, and open dependencies

### 2.1 Verified in the preparer's GitHub read-only check on 2026-11-16

- `main` HEAD: `fdae362e1a889831975060808ac612369d3b0d0a` **at inspection time**, not a guaranteed future HEAD.
- Frozen specification file: `docs/FINAL_MASTER_SPECIFICATION_v3.0.1_FINAL.txt`, blob SHA `befde437b6f951e1da71fdb4f0e61d043049c168` at inspected `main`. In particular, clause **771** requires an expand/backfill/cutover/contract HMAC rotation, a dedicated non-transactional/autocommit `CREATE UNIQUE INDEX CONCURRENTLY` boundary in phase (6), catalog checks for invalid indexes, and subsequent Phase-(8) constraint validation before authority switch; clause **772** mandates dual-write from the same canonical value and protection of active uniqueness.
- Tenant Alembic migration files visible on `main` are **linear `tp0001`–`tp0007`**. No official `tp0008+` is present in the inspected main tree.
- `migrations/tenant_plane/env.py` currently wraps migrations in `context.begin_transaction()` and uses the `alembic_meta.alembic_version_tp` table; its blob SHA on inspection: `04b12d8d83634ad8d8ea2cecb2fcfcf27f71a79e`.
- `tests/integration/alembic_runner.py` currently defaults tenant upgrades to `revision="head"`; blob SHA: `d947da0974065563aa16e3aa0aad3f2a83acecf2`.
- `tests/integration/conftest.py` documents a disposable, two-container PostgreSQL 15 Cloud/Local test topology. Its existence is **not evidence that this proposed experiment ran or passed**.

**Read-only evidence links:**

- `https://github.com/AmirSheikhloo/clinic-ecosystem/blob/main/docs/FINAL_MASTER_SPECIFICATION_v3.0.1_FINAL.txt`
- `https://github.com/AmirSheikhloo/clinic-ecosystem/blob/main/migrations/tenant_plane/env.py`
- `https://github.com/AmirSheikhloo/clinic-ecosystem/blob/main/tests/integration/alembic_runner.py`
- `https://github.com/AmirSheikhloo/clinic-ecosystem/blob/main/tests/integration/conftest.py`

### 2.2 Unverified / NOT asserted

- The original E0.1 §§5.1–5.3: **UNAVAILABLE**; this new contract is not claimed to reproduce them.
- Complete authenticated text and approval state of `MASTER_EXECUTION_ROADMAP_v3.0.1_R4.15.md`: **NOT independently inspected by this drafter**. Cursor's supplied 2026-11-16 read-only audit describes its §§11.8–11.9 as a **proposed** two-branch Tenant DAG, and identifies blocking runner/Phase-6/Phase-8 issues. Treat that audit as an informative report, not a replacement for the actual roadmap file or approval record.
- F2-B's proposed mapping involving `tp0010`/`tp0011`/`tp0012` and the separate Catalog branch through `tp0023`: **review design only, not an approved deployable graph**. Do not reallocate any real `TPxxxx` identifier based on this proposal. In particular, avoid assumptions about `TP0011` ownership or a `TP0023` migration until the exact current roadmap and governing decisions have been reconciled.
- SRC-10 legacy Clause 739 report source, SRC-12 comprehensive live baseline, ACR effectiveness, CI history and PostgreSQL 15 experiment outcomes: **not closed by this document**.

## 3. Experiment question and permitted conclusions

**Narrow research question:** In a **separate synthetic Alembic/PG15 harness**, can a two-branch F2-B-shaped dependency graph support individually targeted HMAC and Catalog upgrades, fail-closed handling of ambiguous upgrades, an explicit Phase-6 concurrent-index/autocommit boundary, a separate Phase-8 constraint/cutover barrier, and selected synthetic Cloud/Local mixed-state negative cases **without writing the official Tenant migration lineage or application code**?

**Allowed conclusion:** `EXPERIMENTAL_FEASIBILITY_SUPPORTED` or `EXPERIMENTAL_FEASIBILITY_NOT_SUPPORTED`, strictly bounded by the exact tests actually executed and evidenced. A positive result does **not** establish real application/Sync compatibility, official migration feasibility, key lifecycle security, readiness to merge, migration numbering approval, Package 1 authority, or any gate closure.

**Not in scope:** implementing actual TP0008+; modifying the real tenant runner; changing `src/`, `migrations/`, `ops/`, `tests/`, `docs/`, existing workflows, services, secrets, production databases, or formal role/RLS policies; realistic patient records; external integrations; broad Suite/Package 4 Lease/Erasure acceptance; implementing Catalog or HMAC product features; rewriting the roadmap; changing ACR status; deploying anywhere persistent.

## 4. Exclusive write allowlist and branch / CI boundaries

Only the following **new, repo-relative paths** may be created or changed **after the separate PO approval**:

| Path | Permission | Constraints |
|---|---|---|
| `experiments/m102_f2b_bounded_e02/**` | ALLOW | New synthetic-only harness, fixtures, local test modules, experiment-only Alembic scripts, sanitized outputs, evidence matrices, final report. No symlinks, submodules, secrets, binary dumps, large generated artifacts, or copied patient data. |
| `.github/workflows/m102-f2b-bounded-e02.yml` | **CONDITIONAL ALLOW** | Create **only if needed** to obtain safe, isolated Actions evidence. Only this new workflow filename; never modify any existing workflow. It must have least-privilege permissions and no production integration. If policy, source triggers, or actual runner isolation cannot be demonstrated, do not create or invoke it. |

**Everything else is immutable under this authorization**, including `docs/**`, `migrations/**`, `src/**`, `tests/**`, `ops/**`, other `.github/**`, `.gitignore`, `pyproject.toml`, README, any pre-existing experimental files/branches, and local editor settings. All tests must live under `experiments/m102_f2b_bounded_e02/tests/`; evidence under `experiments/m102_f2b_bounded_e02/evidence/`. Keep pytest cache, bytecode, coverage, downloaded packages, DB files, and container scratch **outside the repo** in an individually owned disposable temp directory; avoid any dirty `git status` elsewhere.

**Canonical-path enforcement:** before every write, resolve real/canonical paths and repository root; reject `..`, absolute-path escapes, symlinks/junctions, case-collisions, nested repositories and any target not covered by the two entries above. Before each commit or push, check both staged and unstaged/untracked paths; fail closed if **any** path is outside the allowlist. Never use `git clean`, `reset --hard`, force push, blanket `git add .`, or unauthorized deletion to fix an unexpected diff.

**Branch:** exactly one new isolated branch, `experiment/m102-f2b-e02-<YYYYMMDD>-<short-base-sha>` (append a non-conflicting numeric suffix if necessary), from a freshly verified clean `main` base. Do not reuse or edit the existing Cursor M102 branches, PR #3, or `main`. If branch creation from the intended base cannot be completed safely without moving/losing existing work, **BLOCK**. No merge, rebasing protected branches, cherry-picking official code, changing branch protection, or publication as official work.

## 5. Replacement experimental §§5.1–5.3 (new E0.2 requirements)

> These are **new proposed instructions**, not copied or paraphrased from the missing E0.1. Execute them only after valid exact-file PO approval. Report each ID with `PASS`, `FAIL`, `BLOCKED`, or `NOT_RUN`; `SKIPPED` is not a pass.

### 5.1 — Source-grounded, read-only reconciliation and safety gate

**No branch, database, file edits, tests, PR, or pushes during this subsection.**

1. **`E02-5.1-A` — Approval integrity.** Check the PO's explicit approving statement, the exact E0.2 filename, and the SHA-256 of the exact uploaded bytes. If missing, mismatched, ambiguous, revoked, or unsigned where a specific signature would be required, return `BLOCKED_APPROVAL` and end. This E0.2 does not itself constitute an authorization.
2. **`E02-5.1-B` — Source chain.** Read `docs/FINAL_MASTER_SPECIFICATION_v3.0.1_FINAL.txt` (clause 771–772 and relevant RLS/migration boundaries) from the exact checked commit, and the complete available R4.15 review candidate §§11.8–11.9 (read-only). Confirm its status and correct F2-B versus F2-L/F2-S interpretation. If the R4.15 text is absent, contradictory, or cannot support a bounded interpretation, return `BLOCKED_SOURCE_OR_SCOPE`. Do not resolve contradictions by assumption.
3. **`E02-5.1-C` — Live repository facts.** Record `git remote -v`, repo root, `git status --porcelain=v1 --untracked-files=all`, `git rev-parse HEAD`, `git rev-parse origin/main`, `git branch --show-current`, and the full tracked TP revision inventory. Check exit codes. Require clean worktree before branch creation; dirty/untracked worktree -> stop without touching it. Do not claim universal SRC-12 closure.
4. **`E02-5.1-D` — Safety manifest.** Produce an in-memory pre-execution matrix mapping each §5.2 test ID to source rationale, preconditions, exact proposed write paths, expected result, PG15 role/transaction boundary, negative-case stop rule, and evidence location. Verify no tests need disallowed files. Any required official edit -> `BLOCKED_SCOPE`.
5. **`E02-5.1-E` — Run eligibility.** Check authenticated system time and convert to Europe/Berlin using an IANA timezone implementation; check `now < 2026-11-23T22:59:00Z`; verify isolation availability, Docker/CI privileges, and planned token/secret absence. If any safety prerequisite is missing, stop with a factual report before any write.

**§5.1 exit gate:** all A–E evidence obtained, reconciled, and no open scope ambiguity. A lack of verification is `BLOCKED`, never inferred `PASS`.

### 5.2 — Synthetic isolated PostgreSQL 15 / Alembic experiments

**Only after §5.1 passes.** Create the new branch and only allowlisted experiment files. Build **one stand-alone Alembic script environment** under `experiments/m102_f2b_bounded_e02/` with a synthetic namespace (`exp_f2b`) and its own version table (`exp_f2b_alembic_version`), **not** `alembic_meta.alembic_version_tp`. Use **synthetic revision IDs only** such as `exp_f2b_base`, `exp_f2b_h6`, `exp_f2b_h8`, `exp_f2b_cat1`, and `exp_f2b_cat2`; they are analogues, **never** official `TPxxxx` migrations. No import of the repo's official Alembic `env.py` to run experimental migrations and no modification to the official test runner.

Provision exclusively experiment-owned, fresh, ephemeral **PostgreSQL 15** container(s) with fabricated tenant identifiers and dummy HMAC bytes produced from **test-only** random material. Pin image version (and image digest when feasible), verify `SHOW server_version_num` is between `150000` and `159999` from the actual connection, assert database/server identity and local/CI network confinement **before** any SQL writes. No persistent volumes, inherited DB URLs, external IPs/services, production environment files, GitHub secrets, real keys, clinical data, or sharing with existing test databases. Use uniquely named synthetic roles with minimal privileges; use a provisioning/admin role only for ephemeral setup/inspection, a restricted migrator for migration cases, and a restricted app actor for negative permissions. Test `current_user`, role memberships and relevant privilege catalogs; deny `BYPASSRLS` to experiment service actors. Do not report a mock as an executed database test.

| Test ID | Required experiment | Pass criterion / negative expectation |
|---|---|---|
| `E02-F2B-01` | Synthetic graph audit | One base with independent HMAC and Catalog descendants; `alembic heads` output explicitly matches the expected **synthetic** two-head set; no hidden merge/depends_on or unplanned branch edge. |
| `E02-F2B-02` | Explicit head targeting | Controlled wrapper accepts only allowlisted explicit synthetic target revisions or branch-qualified selectors; no implicit latest head. Re-entrant upgrade is idempotent where Alembic semantics require. |
| `E02-F2B-03` | Dangerous-target negatives | Invocations of `upgrade head`, `upgrade heads`, blank/unknown targets, or unintended branch targets fail **before** schema mutation; verify unchanged version-row set and table/catalog state. Read-only `alembic heads` inspection is permitted. |
| `E02-F2B-04` | Version-table state machine | Probe fresh/base/HMAC-only/Catalog-only/both. Validate **set equality** of version rows, including cardinality 0/1/2 as appropriate, not a single `fetchval` assumption. Unexpected version/head -> fail closed. |
| `E02-F2B-05` | Catalog-only independence | Apply the Catalog descendant without HMAC Phase-8. Assert synthetic active-HMAC authority, unique index, and associated columns/markers are unchanged. Negative fixtures requiring Phase-8 fields must be rejected. |
| `E02-F2B-06` | HMAC-only independence | Apply HMAC descendant(s) without Catalog. Assert no Catalog-only objects or state are required or implicitly installed; forbidden cross-branch assumptions must be caught. |
| `E02-F2B-07` | Phase-6 transaction boundary | On PG15, demonstrate positive `CREATE UNIQUE INDEX CONCURRENTLY` outside a transaction block using a dedicated autocommit/Alembic boundary. Separately demonstrate transaction-block rejection, correct role/session restoration, and no false revision stamp. |
| `E02-F2B-08` | Concurrent-index failure/retry | Induce a synthetic duplicate/collision scenario and inspect `pg_index.indisvalid`; never treat an invalid index as safety evidence or as automatic uniqueness enforcement. Block cutover, remediate in a fresh synthetic fixture, and prove a successful subsequent build. Avoid destructive actions outside the experiment. |
| `E02-F2B-09` | Phase-8 guarded cutover | Use synthetic `NOT NULL`/`CHECK` constraints and inspect `pg_attribute.attnotnull` / `pg_constraint.convalidated`. A cutover attempt with unmet validation **must** be refused; a validated case may proceed only in the sandbox. No claim about official TP Phase-8. |
| `E02-F2B-10` | Dual-write / active uniqueness | Synthetic same-source old/new HMAC behavior under overlapping transactions; verify the old authoritative uniqueness is never bypassed, collisions reject atomically, and incomplete backfill or stale old-writer state blocks cutover. No `Zero-Race-Window` claim without relevant concurrency evidence. |
| `E02-F2B-11` | Role and privilege negatives | Show restricted synthetic app actor cannot mutate migration metadata, role grants, or other synthetic tenants' protected rows. Exercise RLS-negative tests only with an accurately configured, actual PostgreSQL 15 synthetic RLS policy; fail on unexpectedly permissive operations. |
| `E02-F2B-12` | Cloud/Local mixed-state **simulation** | Use independent synthetic DBs/containers to cover selected `{base, HMAC-only, Catalog-only, both}` pairs. Test version admission/fencing under an explicit **synthetic model**. Record that actual production Sync/app/worker compatibility remains UNVERIFIED. |
| `E02-F2B-13` | Interrupted upgrade semantics | In a synthetic forced-failure test, verify that partial nontransactional index artifacts and version stamps are distinguishable, recovery requires explicit checks, and no unsafe automatic onward upgrade occurs. |
| `E02-F2B-14` | Scope / clock / resource closure | Before writes and final delivery, inspect changed-path allowlist, real PG15 endpoint/version, synthetic fixture provenance, deadline, and cleanup of experiment-owned containers/networks/temporary resources. Record residuals rather than deleting external resources. |

**Evidence requirements for every test:** tested source SHA; command/argv (with secrets redacted); UTC timestamp; PostgreSQL server version; synthetic role/database label; expected and observed outcome; return code; relevant `pg_catalog` rows/diffs or redacted test output; evidence path; SHA-256 of evidence; and `PASS`/`FAIL`/`BLOCKED`/`NOT_RUN`. For negative tests, a forbidden operation that succeeds is `FAIL` and triggers `STOP_SECURITY`. A not-run case is not success. No code change is allowed as a workaround for a failed security assertion; only correct experiment-local code within scope can be revised, with the failure retained in the audit trail.

**Explicit limitations:** These experiments cannot prove or amend the official `TP0011`, `TP0023`, Package 2, Cloud/Local Sync, or application-layer migration contracts. Where source-grounded application independence cannot be exercised without modifying prohibited code, mark `BLOCKED_EXTERNAL_EVIDENCE`, document the precise needed evidence, and **do not** infer compatibility from an isolated SQL graph. No official migration execution is authorized here, even on a disposable instance; all migration execution uses the dedicated experimental script environment.

**Experiment-only CI option:** If local tests cannot be sufficiently evidenced and a safe GitHub-hosted job is necessary, the **single new** workflow file permitted by §4 may be created with `pull_request` on the experiment branch, an explicit `permissions: { contents: read }`, no `pull_request_target`, `workflow_dispatch`, `push` deployment trigger, write-token requirement, external service, real secret, self-hosted runner or privileged container. Checkout must not persist credentials. Inspect pre-existing workflow triggers; if the Draft PR would cause unrelated/privileged jobs, **STOP_CI_SCOPE** rather than proceeding. CI must set a hard job timeout, verify the same cutoff clock, use fresh disposable PG15 + synthetic fixtures, run only experiment-local tests, upload only redacted evidence, and clean up owned resources in a `finally`/always-run lifecycle. If a Draft PR genuinely is required, create **at most one**, name it `EXPERIMENT ONLY — M102 F2-B E0.2 — DO NOT MERGE`, keep it Draft, never mark ready or merge, and record its link and actual Actions run IDs. A queued/skipped/timed-out/cancelled run is not PASS. If CI is impossible within these rules, finish with a factual BLOCKED/INCOMPLETE report; do not widen permissions.

### 5.3 — Final consolidation, evidence grading, stop, and termination

1. Complete safe cleanup **before** final report delivery. The full consolidated report must be one Markdown file under `experiments/m102_f2b_bounded_e02/evidence/M102_F2B_E02_FINAL_CONSOLIDATED_REPORT.md` **if the approved experiment branch has been created**. If blocked before writes, put the **complete blocker report in Cursor's final response only**; do not create a repository file.
2. The consolidated report must contain the approval text and exact E0.2 SHA; original E0.1 missing-source disclosure; frozen spec blob and live base SHA; roadmap candidate actual revision/status; branch/commit/diff and every changed-path entry; temp resource IDs and PostgreSQL server proof; role/connection/isolation checks; each §5.1 and §5.2 obligation with expected/actual/exit status/evidence digest; total PASS/FAIL/BLOCKED/NOT_RUN; CI/PR URL if used; clean resource-disposal result; defects and exact unresolved app/Sync/migration dependencies.
3. **Evidence classifications:** `PROPOSED`, `EXECUTED`, `OBSERVED_PASS`, `OBSERVED_FAIL`, `BLOCKED`, `NOT_RUN`, `UNVERIFIED`. Use `EXPERIMENT_COMPLETED_WITH_EVIDENCE` only when every authorized test actually ran and its evidence is attached; otherwise `EXPERIMENT_INCOMPLETE`, `BLOCKED_APPROVAL`, `BLOCKED_SOURCE_OR_SCOPE`, `BLOCKED_CI_SCOPE`, `STOPPED_SECURITY`, or `EXPIRED` as appropriate. Never say `IMPLEMENTED`, `VERIFIED FOR PRODUCTION`, `APPROVED F2-B`, or any Gate acceptance based on these tests.
4. **Final evidence integrity:** safe redaction, `git diff`/status inspection, no changes outside allowlist, no official migration or application edits, no retained secret or patient data. Record the final branch SHA and existing Draft PR state. Report any unproved non-action as `UNVERIFIED`, not as a categorical success.
5. **Termination:** delivery of this single consolidated report **immediately terminates** this authorization. Also terminate at the hard time deadline, whichever comes first. No post-report/past-deadline push, edit, rerun, cleanup requiring new access, PR update, or test is authorized. Place time checks before every state-changing step; if expiry approaches, stop at a safe boundary and publish an honest partial report. Preconfigure temporary resource lifetimes/cleanup to prevent unattended operations past expiry.

## 6. Mandatory STOP conditions and incident handling

Immediately stop and return a precise reason if any of the following occurs:

- Approval text / SHA mismatch; absent R4.15 necessary source or contradictory architecture; missing source-to-test map.
- Expiry or delivery of a final consolidated report; inability to verify an authoritative clock.
- Incorrect repo, dirty tree, unsafe branch/base, disallowed changed path, unsafe symlink, unknown inherited environment variable or command failure obscuring state.
- Non-PostgreSQL-15 server; a persistent, externally hosted, patient-bearing, or shared DB; exposure of real credentials/data; unexpected external network access.
- Active uniqueness or RLS/permission security-negative test unexpectedly permits a forbidden action; failed cutover barrier; invalid index treated as valid; unsafe continuing after a failed migration step.
- A test requires editing official migrations, application code, real runner, existing CI, secrets, or resource ownership boundaries.
- CI triggers unsafe jobs or requires elevated tokens, production environments, or a non-Draft PR; a PR would be merged or an ACR/gate asserted.

When stopping, collect **only safe, in-scope redacted evidence**, do not mutate out-of-scope resources, and report `STOPPED_SECURITY` / an appropriate `BLOCKED_*` category. Do not treat green tests or an AI response as new authorization.

## 7. Mandatory Cursor response format — clear termination marker

**At the end of every Cursor response for this task (including intermediate BLOCKED status), print this exact terminal format with truthful values:**

```text
TASK STATUS: COMPLETED / BLOCKED / FAILED
CONTRACT: M102 F2-B E0.2 (PROPOSED / APPROVED-AND-VERIFIED)
EXECUTION STATE: NOT STARTED / IN PROGRESS / TERMINATED
WORK PERFORMED: <precise factual summary>
EVIDENCE: <exact files/run URLs, or NONE>
NEXT ACTION FOR PRODUCT OWNER: <exactly one action, or NONE>

=== END OF CURSOR RESPONSE ===
```

If the response is final, `EXECUTION STATE` must be `TERMINATED`, even if the task is `BLOCKED` or `FAILED`. Never say `COMPLETED` for work that was blocked. **Do not continue silently after the end marker.**

## 8. Instructions to Cursor when this file is supplied

1. First read the complete E0.2 file, independently hash it, and look for **explicit PO approval identifying this exact digest**. If absent, perform no writes and reply `BLOCKED_APPROVAL` with the §7 terminal marker.
2. Once, and only once, the approval is matched and within the fixed time window, carry out §5.1. If a gate fails, return its blocker without subsequent test activity.
3. If §5.1 passes, carry out §§5.2–5.3 in order under the allowlist, using only a new experiment branch and wholly disposable synthetic resources. No unapproved scope expansion.
4. End with a single consolidated factual report and the **exact** §7 terminal marker. This does not authorize further action.

---

**Document disposition at preparation:** `E0.2 PROPOSED / NOT EFFECTIVE / NO EXECUTION AUTHORIZATION / ORIGINAL E0.1 NOT RECOVERED`.  
**For the PO:** Do not run this as an authorized instruction until you separately approve the exact artifact identity and digest. The file is intentionally comprehensive so the **same file**, after approval, can be forwarded to Cursor without a second incompatible prompt.

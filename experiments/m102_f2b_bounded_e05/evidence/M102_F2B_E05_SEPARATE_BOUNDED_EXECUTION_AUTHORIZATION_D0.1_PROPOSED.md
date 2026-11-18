# Clinic Ecosystem — M102 F2-B E0.5 Separate Bounded Execution Authorization Instrument

**Document:** `M102_F2B_E05_SEPARATE_BOUNDED_EXECUTION_AUTHORIZATION_D0.1_PROPOSED.md`  
**Review revision:** D0.1 (proposal)  
**Date:** 2026-11-18 UTC  
**STATE:** `PROPOSED / UNSIGNED / INACTIVE / NO CURSOR EXECUTION OR CI AUTHORITY`  
**Technical contract (exact):** `M102_F2B_E0.5_FAIL_CLOSED_FORENSIC_ACCEPTANCE_CONTRACT_R0.1_PROPOSED.md`  
**Technical contract SHA-256 (full):** `6cc9be44ded30170266427f669c1b159bee0d8b27c7ab2fcfecd8735271df783`  
**New E0.5 PO approval:** **NOT GIVEN**. This document contains a future *approval template*, not a signed authorization.

## 1. Purpose, non-transferable history, strict document hierarchy

This separate proposed instrument defines **possible future**, explicitly PO-authorized execution of a **new isolated synthetic E0.5** experiment solely to resolve the four post-E0.4 forensic coverage findings A0.1-01 through A0.1-04. The independently reviewed E0.4 CI run `44294184379` at `8d015959ec6b2570da74d63d8f7ee0e88d1cff64` succeeded with 32/32 pytest and independently matching original case SHA-256s, yet its validator semantics were inadequate for whole-contract acceptance. Both E0.4 CI attempts were consumed; its grant ended with the final report. **Nothing herein resurrects or modifies E0.4 authority or evidence.**

Precedence: frozen specification v3.0.1 > latest explicitly approved architecture contract > distinct exact-hash PO grant > complete E0.5 technical contract (this instrument authorizes only its in-scope subset) > technical tasks. Roadmap R4.15 remains a *review candidate*, not an execution source. Any conflict requires STOP and a PO-reviewed change, never unilateral interpretation. Read-only Gemini/ChatGPT review does not grant authority.

## 2. Exact proposed approval envelope (all gates mandatory)

| Variable | Proposed value (not granted) |
|---|---|
| Executor | Cursor only, after fresh explicit PO acceptance of both exact full SHA-256s |
| Contract | `M102_F2B_E0.5_FAIL_CLOSED_FORENSIC_ACCEPTANCE_CONTRACT_R0.1_PROPOSED.md`; SHA-256 `6cc9be44ded30170266427f669c1b159bee0d8b27c7ab2fcfecd8735271df783` |
| Instrument | `M102_F2B_E05_SEPARATE_BOUNDED_EXECUTION_AUTHORIZATION_D0.1_PROPOSED.md`; SHA-256 **to be independently calculated after this file is frozen** (see approval template) |
| Repository | `AmirSheikhloo/clinic-ecosystem` |
| Branch parent | E0.4 **final evidence** `f1b11731590fe29a294f86cf7cf5b64878d8ec7d` (parent of this is tested SHA `8d015959ec6b2570da74d63d8f7ee0e88d1cff64`) |
| Branch | exactly one new branch under `experiment/m102-f2b-e05-*`, from the pinned parent |
| Only write paths | `experiments/m102_f2b_bounded_e05/**` and `.github/workflows/m102-f2b-bounded-e05.yml` |
| Tests | Re-prove **all 19** inherited E03 case IDs, all **14** retained E04 validator fixtures, plus E05-FC01..FC10 predicates within those tests/gates; no physical migration feature added |
| Database | Disposable PostgreSQL 15, synthetic-only data/roles/keys |
| CI | Push-only; branch/path-filtered; at most **1 initial + 1 conditional non-security corrective** run; no manual rerun or third attempt |
| Proposed cutoff | `2026-12-04T22:59:00Z` UTC (requires later explicit exact-hash PO approval); **first final report or terminal blocker ends grant earlier** |
| Permissions | Read-only GitHub Actions `contents: read`; no secrets, deploy or external DSNs |
| Explicit prohibitions | Official code/migrations, production DB/data, PR, merge, ACR, F2-B approval, Package 1, Gates A–D, new package, real Sync assertions |

The values above are **proposals** only. A fresh PO decision must restate filename and exact SHA-256 of both final reviewed documents, execution scope, base, allowlist, attempt budget and cutoff. A past approval, previous ZIP, a new upload, a technical PASS or the presence of documents cannot substitute for that statement. Do not write to GitHub while this instrument remains unapproved.

## 3. Current evidence and unmodifiable facts

- E0.4 original successful Actions run: <https://github.com/AmirSheikhloo/clinic-ecosystem/actions/runs/44294184379>; tested SHA `8d015959ec6b2570da74d63d8f7ee0e88d1cff64`; original artifact ID `14422442843`.
- E0.4 prior initial failed attempt `44293883965` and second successful attempt `44294184379` consumed the authorized 1+1 budget; do not claim these are E0.5 budget entries.
- E0.4 final evidence commit `f1b11731590fe29a294f86cf7cf5b64878d8ec7d`, with only evidence files added relative to tested SHA as verified by a read-only GitHub comparison in the earlier independent audit.
- Historical E0.3 run `44112675849` had an authentic failed `E03-A07-C01`; E0.4 historical cases are separately green but not yet full forensic contract acceptance. Never rewrite historical results.
- Frozen-spec Git blob `befde437b6f951e1da71fdb4f0e61d043049c168`; source integrity and actual live repo baseline must be rechecked independently when a future grant begins.

## 4. Proposed safe preflight before any future write or SQL

`G0 APPROVAL`: verify accessible unmodified E0.5 contract and instrument bytes, exact full SHA-256 matching new PO text, separate approval message with date and scope, active clock. If inaccessible -> final `BLOCKED`, no work. **Final blocker ends that grant.**

`G1 PROVENANCE`: verify exact base SHA `f1b11731590fe29a294f86cf7cf5b64878d8ec7d` exists and parent `8d015959ec6b2570da74d63d8f7ee0e88d1cff64`; read current frozen specification and reviewed E0.4 source/artifact, branch history, source-equivalence ledger. If Git reads are stale, state `UNVERIFIED`; never assume source semantics.

`G2 SCOPE`: create fresh isolated E05 branch; check full Git diff from pinned base for allowed paths **before** SQL. Any out-of-scope file -> STOP; do not try to hide/rollback unauthorized edits silently.

`G3 CODE`: modify only E05-namespaced forensic verifier/harness, fixture and necessary CI orchestration. Copy existing E0.4 synthetic physical SQL/Phase6/Phase8/roles/RLS/writer fencing with semantic-equivalence ledger; do not change official migrations or weaken inherited cases.

`G4 PHYSICAL`: on disposable PG15, re-prove inherited cases with actual catalog/SQLSTATE/role/session evidence. Negative security failures => STOP_SECURITY, no retry.

`G5 FORENSIC`: enforce E05-FC01..FC10 with real final verifier, nonzero tamper-negative controls, positive clean gate, exact 19/14 results and two non-circular SHA manifest layers. Must separately fail if any inherited case status != `OBSERVED_PASS` even if its digest is correct.

`G6 CI`: one push-only workflow with expected ref/attempt and absolute UTC gate; run pytest, mandatory post-pytest verifier, **final stable auxiliary manifest seal**, then **read-only final seal verifier** as distinct mandatory steps. Every gate's shell exit must determine overall CI status. No `continue-on-error`, permissive fallback or silent warning. Check artifact inventory stability before upload.

`G7 CLOSEOUT`: report true result, include both initial and corrective CI attempts, JUnit/logs, 19+14 IDs, each denial's invoked validator and exit code, both exact digest manifests, independent audit pending flag, cleanup limitations, one PO action. Deliver first consolidated report, **then grant is TERMINATED**, even for BLOCKED/FAILED. No post-report CI, new push or tests.

## 5. Mandatory inherited IDs — no waiver, no silent replacement

| Case ID | Required current E05 proof |
|---|---|
| `E03-A01-P01` | Restricted migrator executes only when SET ROLE succeeds; role evidence, no privileged fallback (`PHYSICAL_PG15`) |
| `E03-A01-N01` | Failed SET ROLE denies migration and preserves state (`PHYSICAL_PG15`) |
| `E03-A02-N01` | Incomplete backfill blocks Phase 8 (`PHYSICAL_PG15`) |
| `E03-A02-P01` | Real pg_attribute.attnotnull=true and pg_constraint.convalidated=true (`PHYSICAL_PG15`) |
| `E03-A02-N02` | Missing catalog prerequisite denies Phase 8 (`PHYSICAL_PG15`) |
| `E03-A03-P01` | Overlapping write transactions, uniqueness SQLSTATE and no silent loss (`PHYSICAL_PG15`) |
| `E03-A03-N01` | Stale/offline/unknown writer fenced before mutation (`PHYSICAL_PG15`) |
| `E03-A04-P01` | Synthetic Cloud/Local mixed-state admission ALLOW (`PHYSICAL_PG15`) |
| `E03-A04-N01` | Synthetic admission DENY before mutation (`PHYSICAL_PG15`) |
| `E03-A05-C01` | New E0.5 push-only CI, branch, attempt, clock and path guards (`GOVERNANCE_CONTROL`) |
| `E03-A06-P01` | Role before/inside/after Alembic autocommit restored in same session (`PHYSICAL_PG15`) |
| `E03-A06-N01` | Invalid concurrent-index catalog state and controlled recovery (`PHYSICAL_PG15`) |
| `E03-A06-N02` | Negative GRANT/ALTER/RLS privilege checks, unchanged protected state (`PHYSICAL_PG15`) |
| `E03-A07-C01` | 19 stable case records and final external validation without circular self-check (`GOVERNANCE_CONTROL`) |
| `E03-A07-C02` | Pre-execution 19-row manifest with preconditions and stop rules (`GOVERNANCE_CONTROL`) |
| `E03-A08-N01` | Injected forbidden path mutation rejected before execution (`GOVERNANCE_CONTROL`) |
| `E03-A08-P01` | Full-range pinned-base-to-tested-commit diff allowlist enforced before SQL (`GOVERNANCE_CONTROL`) |
| `E03-REG-P01` | Branched synthetic topology with both heads and correct Alembic targets (`PHYSICAL_PG15`) |
| `E03-CLOSE-C01` | Cleanup, grant cutoff and no implied architecture/package/gate authority (`GOVERNANCE_CONTROL`) |

## 6. Mandatory E04 validator fixtures — no fake-only acceptance

| Fixture ID | Exact E05 expectation |
|---|---|
| `E04-V01` | Staged C01 materialization: missing-self cannot cause false denial; premature acceptance forbidden |
| `E04-V02` | Clean 19 JSON records plus external manifest through real final validator and separate read-back |
| `E04-V03` | Remove/duplicate/swap ID; call real final validator on disposable tree; expect nonzero denial |
| `E04-V04` | Mutate one byte post-manifest; call real manifest verifier on disposable tree; expect nonzero denial |
| `E04-V05` | Wrong/LOCAL tested SHA even if 40-hex syntactically valid; expect CI-context refusal |
| `E04-V06` | Wrong/local run ID or wrong run attempt; expect trusted-context refusal |
| `E04-V07` | Malformed UTC timestamp, mandatory-field type or missing field; expect refusal |
| `E04-V08` | SKIPPED/UNVERIFIED/OBSERVED_FAIL/BLOCKED/NOT_RUN with valid recomputed hashes; expect final refusal |
| `E04-V09` | Path traversal, symlink, wrong reference or duplicate case path; expect refusal |
| `E04-V10` | Dummy credential/DSN sentinel nested in evidence; fail without echoing sensitive sentinel |
| `E04-V11` | Absent/duplicate/self-hashed/stale primary or auxiliary manifest; expect refusal |
| `E04-V12` | Physical-PG evidence replaced by NOT_APPLICABLE governance labels; expect refusal |
| `E04-V13` | Green simulated pytest + negative forensic step, execute actual gate orchestration; expect nonzero job-equivalent result |
| `E04-V14` | Mandatory clean positive after stable artifacts + trusted CI identity; no unconditional true/skip fallback |

## 7. Additional forensic predicates (all required, same experimental scope)

| Predicate | Mandatory substantive correction |
|---|---|
| `E05-FC01` | Reject `OBSERVED_FAIL/BLOCKED/NOT_RUN/UNVERIFIED/REVIEW_ONLY/SKIPPED` as full acceptance despite freshly valid manifest; accept only exact 19/19 `OBSERVED_PASS` |
| `E05-FC02` | Enforce basename ↔ case ID ↔ finding/type mapping, exact 19 IDs, no duplicates or swaps |
| `E05-FC03` | Match trusted real CI SHA/run/attempt plus E0.2/E0.3/E0.4 lineage, contract SHA |
| `E05-FC04` | Strict field types and meaningful per-case physical/governance evidence; UTC; negative SQL semantics |
| `E05-FC05` | Strict canonical, regular-file, non-symlink evidence refs and no escaping path |
| `E05-FC06` | Recursive nested synthetic secret/DSN redaction; no leaked sentinel in diagnostics |
| `E05-FC07` | Re-prove V03/V04/V13/V14 using *actual* final gate; reject tautological test patterns |
| `E05-FC08` | Exact primary and auxiliary manifest inventories, independent SHA checks and seal layer; no self-hash |
| `E05-FC09` | Cross-bind JUnit, 19 case files, 14 fixtures, GitHub CI success and no fail/skip |
| `E05-FC10` | Distinguish self-reported pass, CI pass and independent external verification; never self-certify E5-E |

**Fail-closed proof pattern:** For status failures, deliberately change a synthetic case status to `OBSERVED_FAIL` (and separately `BLOCKED` etc.) while regenerating correct SHA manifests; the real post-pytest acceptor must return nonzero for the *status*, not for hash mismatch. For corruption cases, recompute actual bytes against the original immutable manifest and require a deterministic hash denial. Exact negative evidence (redacted command, exit, detector, expected/observed) must be retained. Disallowed synthetic secrets must never be printed. The parent E0.4 physical test semantics must not change to make the suite green.

## 8. CI budget, technical expiry, post-report immutability

- Proposed max **two separate push-triggered workflow runs**: one initial; at most one corrective only if first failed from a proven non-security/CI harness issue and no real security, scope, secrecy or data failure. Re-running a GitHub run attempt via platform UI does not count as an authorized fresh execution; it is forbidden.
- Absolute cutoff is proposed `2026-12-04T22:59:00Z`. Active authority (if separately granted) terminates at first consolidated final report **or earlier cutoff**, regardless of remaining budget. A final `BLOCKED`/`FAILED` marker is a terminal report, not a checkpoint or permission to resume.
- The workflow cannot cryptographically disable a GitHub manual rerun; enforce technical best-effort run-attempt/event/bounds plus binding PO governance ban.
- If failed post-pytest validator/auxiliary seal gate, CI **must fail**, even if pytest is green. No acceptance classification upgrade based on offline rehash alone. Preserve the original artifact and all failures.
- GitHub evidence-only report commit **after** successful CI is allowed solely in the E05 evidence directory; no new CI, and source code/workflow must be byte-identical to tested commit. CI manifests cannot include the later report; independent audit checks final report parent/blob separately.

## 9. Acceptance gates and exact status limits

| Gate | Must be shown | Missing/failed label |
|---|---|---|
| E5-A authority | Fresh signed PO full SHA approval, time, executor | `BLOCKED_APPROVAL` |
| E5-B source | Pinned parent, source-equivalence, pre-SQL complete diff | `BLOCKED_SOURCE_OR_SCOPE` |
| E5-C PG/CI | Current PostgreSQL 15, 18 inherited pytest functions / 19 case records, no fail/skip | `CI_OR_PHYSICAL_EVIDENCE_INCOMPLETE` |
| E5-D forensic | All 14 retained fixtures plus 10 predicates with true negative/positive results; two sealed manifests, statuses and types fail closed | `FORENSIC_CONTRACT_INCOMPLETE` |
| E5-E independent | Post-report independent original artifact and source review, read-only | `INDEPENDENT_AUDIT_PENDING_OR_FAILED` |
| E5-F finalization | Accurate final report, cutoff, immutable history, cleanup info, no later work | `CLOSEOUT_INCOMPLETE` |

The E5 gates are not roadmap Gates A, B, C, D. At most an independent audit can label **synthetic forensic evidence sufficient for future governance consideration**, never F2-B approved, production tested, Package 1 authorized or ACR signed. Existing SRC-10 and SRC-12 remain unresolved; real Sync, official multi-head Alembic and Control Plane require separate source-grounded work.

## 10. Conditions of STOP and permitted reporting

Immediately STOP (no corrective retry) on: unsigned/unverifiable PO approval, expired cutoff or report already delivered, source/base mismatch, prohibited paths, real endpoint/secrets/PII, privilege/RLS/old-writer fencing failure, incompatible Phase 6/8 behavior, changed official migration, tampered historical artifacts, impossible forensic sealing, status inflation or known untrusted CI identity.

If a *non-security* harness error occurs, only the separately granted optional corrective attempt may be used after recording exactly why it is non-security and how it will be fixed within the allowlist. A fresh PO authorization is required if anything exceeds these limits. No background work or promises of later unapproved runs.

The final report must list every `E03-*`, every `E04-V*`, every new `E05-FC*` result, real run/commit/artifact references, both manifest root hashes, negative test exit outcomes, changes compared with previous synthetic source, honest limitations and next owner action. `E5-E` must remain `PENDING` until external audit is performed.

## 11. Product Owner future decision — NOT PRESENT, NO IMPLICIT SIGNATURE

If and ONLY IF independent joint document review passes (or full revised documents are re-reviewed), the owner may issue a **new separate authorization** in a subsequent message explicitly identifying:

1. Exact E0.5 contract filename `M102_F2B_E0.5_FAIL_CLOSED_FORENSIC_ACCEPTANCE_CONTRACT_R0.1_PROPOSED.md` and its full SHA-256 `6cc9be44ded30170266427f669c1b159bee0d8b27c7ab2fcfecd8735271df783` **only if unchanged after review**.
2. Exact E0.5 D0.1 filename `M102_F2B_E05_SEPARATE_BOUNDED_EXECUTION_AUTHORIZATION_D0.1_PROPOSED.md` and its full SHA-256 as recomputed from the **final** reviewed bytes.
3. Base `f1b11731590fe29a294f86cf7cf5b64878d8ec7d`, two strict E05 paths, synthetic PG15, required 19+14+10 acceptance predicates, CI max 1+1 with no security retries, report-first/UTC cutoff `2026-12-04T22:59:00Z`, and all forbidden actions.

**No** signed PO statement is embedded here and no owner consent is inferred from requesting a review, uploading this ZIP or acknowledging Gemini. This instrument is not self-activating. A Cursor instruction prepared for *later* is expressly inert until an exact owner grant exists.

## 12. Reviewer instruction and final terminal marker

Gemini must review **both complete E0.5 files together**, all source-grounded E0.4 findings and all matrices, and directly correct complete documents as needed. No isolated patch-only response. If a revision changes the contract SHA, the instrument's linked hash must also be revised; recompute every file digest before PO decision.

A future Cursor terminal report (only under new explicit approval) MUST end with:

```text
TASK STATUS: COMPLETED / BLOCKED / FAILED
CONTRACT: M102 F2-B E0.5 (APPROVAL_STATUS: APPROVED-AND-VERIFIED / BLOCKED_APPROVAL)
EXECUTION STATE: NOT STARTED / IN PROGRESS / TERMINATED
WORK PERFORMED: <truthful actions and non-actions>
EVIDENCE: <actual CI URLs, SHAs, artifacts or NONE>
OPEN FINDINGS: <specific IDs and missing evidence>
NEXT ACTION FOR PRODUCT OWNER: <one concrete action or NONE>
=== END OF CURSOR RESPONSE ===
```

## 13. Version history / status

| Revision | Date | Complete documentary changes | Classification |
|---|---|---|---|
| D0.1 | 2026-11-18 | First separate **proposed** E0.5 authorization envelope; linked SHA-pinned R0.1 contract; retained exact 19+14 matrix, added 10 forensic acceptance predicates, bounded isolated branch/PG15, two-stage manifests, CI budget, new PO approval requirement and termination markers; no tests, code changes or authority | `PROPOSED / UNSIGNED / NOT EXECUTED` |

**Final authorization state:** `E05_D0.1_PROPOSED / NO_ACTIVE_GRANT / ZERO_E05_RUNS_AUTHORIZED / E0.4_GRANT_TERMINATED / F2-B_UNAPPROVED`.

=== END OF E0.5 PROPOSED AUTHORIZATION D0.1 ===

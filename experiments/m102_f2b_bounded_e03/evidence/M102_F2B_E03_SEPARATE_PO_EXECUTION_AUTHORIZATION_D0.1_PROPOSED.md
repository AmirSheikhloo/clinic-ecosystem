# Clinic Ecosystem — M102 F2-B E0.3 Separate Bounded Corrective Experiment Authorization Instrument

**Artifact:** `M102_F2B_E03_SEPARATE_PO_EXECUTION_AUTHORIZATION_D0.1_PROPOSED.md`  
**Revision:** `D0.1 — PROPOSED / FOR INDEPENDENT REVIEW / NOT EXECUTABLE`  
**Prepared:** 2026-11-17  
**Project / repository:** Clinic Ecosystem / `AmirSheikhloo/clinic-ecosystem`  
**Proposed executor:** Cursor **only**, subject to a new and separate Product Owner (PO) approval  
**Intended independent reviewer:** Gemini (read-only review of this instrument), after ChatGPT's review  
**Applicable technical contract:** `M102_F2B_CORRECTIVE_EVIDENCE_AND_GOVERNANCE_CONTRACT_E0.3_PROPOSED.md`, **SHA-256 `b5f8d33a33ff25e398cb75be76bebfab02a32cf8386e04b1e46f6cecc89ecb28`** (the exact existing E0.3 bytes; do not edit or silently replace).  
**Approval of this draft:** **NONE.** A request to *prepare* this authorization instrument is not an authorization to execute it.

> **STOP — NOT AN EXECUTION ORDER.** This D0.1 is a proposal for the PO and independent reviewers. It does not authorize Cursor or any other agent to create a branch, edit/push files, start PostgreSQL, run tests or Actions, open a PR, sign an ACR, merge code, or accept a gate. The prior E0.2 authority **terminated on delivery of its final consolidated report**. No part of that old grant can be reused. Only a future, affirmative PO statement identifying the exact *final* D0.1 (or successor) SHA-256 **and** the exact E0.3 contract SHA-256, together with the fixed UTC cutoff and event policy below, could open this narrowly bounded corrective experiment.

---

## 1. Authority hierarchy and documentary record

1. **Frozen governing architecture:** `docs/FINAL_MASTER_SPECIFICATION_v3.0.1_FINAL.txt`, especially clauses 771–772 (HMAC rotation, Phase-6 `CREATE UNIQUE INDEX CONCURRENTLY` autocommit, invalid-index remediation, real Phase-8 constraints, same-source dual-write and old-writer drain). No change to frozen specification is authorized.
2. **Design review candidate, not effective deployment authority:** `MASTER_EXECUTION_ROADMAP_v3.0.1_R4.15.md`, §§11.8–11.9. The F2-B two-head mapping is a **proposal**; do not treat review approval as an ACR or production migration graph approval. Historical numbering (`TP0011`, `TP0023`) cannot be changed by this experiment.
3. **New normative corrective criteria (if separately approved):** the exact E0.3 technical contract named and SHA-pinned above, including all its §§1–10, 19 case IDs, §3 write allowlist, §7 proposed isolated `push` CI policy, §5 stop gates, §6 evidence schema and §9 Cursor end marker.
4. **Historical, closed grant and historical evidence:** E0.2, SHA-256 `03c471825a0ec404eb0ce173789a9d0dd87e3c42a656ed6cad459f277909ec31`; green experimental CI run `43952295235` (tested SHA `e1897078076296c771a7caedb97dc75b2b28db22`, 14 pytest functions passed), with independent eight-finding audit `M102_F2B_E0.2_INDEPENDENT_AUDIT_A0.1.md`, SHA-256 `9c5f8947a52c8750fbfaa5a798dfee88069f9d64f8e76840b225e12a057b758f`. **The eight findings A01–A08 are not closed by that green run.** Gemini previously concurred on all eight, based on the review text supplied by the PO.
5. **Original E0.1 not recovered.** Neither this instrument nor E0.3 purports to reproduce it.
6. **Precedence:** explicit PO prohibitions and the frozen specification > the more restrictive of the final approved E0.3 contract and final approved authorization instrument > explanatory handoff. An inconsistency is a **STOP** pending a new PO decision; never silently pick a permissive interpretation.

**Repository grounding limit:** previous independent read-only inspection verified E0.2 experimental sources and GitHub Actions run; this document does **not** claim that a future branch, database, runner, CI execution, live `main`, or Cursor worktree has been verified. Cursor must independently re-check live repository identities and SHA-pinned inputs during the read-only preflight, but only after a separate PO approval.

---

## 2. Proposed separate grant — all fields must be approved together

**Current effectiveness:** `NOT APPROVED / NOT EFFECTIVE`.

| Required approval field | Exact proposed value / rule |
|---|---|
| Contract | `M102_F2B_CORRECTIVE_EVIDENCE_AND_GOVERNANCE_CONTRACT_E0.3_PROPOSED.md`, SHA-256 `b5f8d33a33ff25e398cb75be76bebfab02a32cf8386e04b1e46f6cecc89ecb28` |
| Authorization instrument | `M102_F2B_E03_SEPARATE_PO_EXECUTION_AUTHORIZATION_D0.1_PROPOSED.md`, **actual final SHA-256 to be calculated and quoted exactly after independent review**; no blank hash is executable |
| Executor | Cursor only; ChatGPT/Gemini are independent reviewers, not runtime executors under this grant |
| Purpose | Correct **only** the eight confirmed E0.2 experimental coverage/governance findings A01–A08, with 19 prescribed E0.3 proof/control IDs and minimal dependent regression/closure checks |
| Origin | One **new** E0.3 experiment branch created from the exactly verified E0.2 **final evidence commit** (record complete SHA first). Never write to original E0.2 branch or `main` |
| Proposed branch form | `experiment/m102-f2b-e03-<YYYYMMDD>-<short-source-sha>`, subject to E0.3 §3 naming and one-branch rule |
| Allowed repository writes | **Only** new `experiments/m102_f2b_bounded_e03/**`; plus **only if necessary** the one new `.github/workflows/m102-f2b-bounded-e03.yml` |
| Forbidden repository writes | All E0.2 files; `migrations/**`, `src/**`, `tests/**`, `ops/**`, `docs/**`, `pyproject.toml`, `.gitignore`, existing workflows, `main`, approved records, and anything else outside the two exact allowlist entries |
| Test environment | Fresh ephemeral PostgreSQL **15.x** on isolated, disposable local/hosted infrastructure; synthetic tenants/bytes/keys only. Prove endpoint, server version, roles and isolation **before any SQL mutation** |
| CI mode | **PROPOSED ONLY:** one branch-restricted **`push`** workflow consistent with E0.3 §§4 A05/7; `permissions: contents: read`, no secrets/deployment, no privileged runner, strict changed-path filters and runtime diff guard; evidence-only final commit must not trigger a new run |
| PR mode | **No PR**, even Draft, under this proposed grant; any alternate CI event/PR mode requires separately reviewed document and explicit new PO decision |
| Proposed absolute hard stop | **2026-11-27T22:59:00Z** = 2026-11-27 23:59 Europe/Berlin (CET). This date is a *proposal only*; it becomes an actual cutoff only if the PO affirms this exact value in a later approval. No extension is inferred |
| Earlier termination | The moment **one final consolidated E0.3 report** is delivered, including a truthful BLOCKED/INCOMPLETE final report, even if the absolute cutoff has not arrived |
| After termination | No new execution, retries, branch push, workflow rerun, PR change, SQL, or post-delivery work under this grant. Existing external/manual rerun capacity cannot be magically revoked; E0.3 requires procedural enforcement and explicit residual-risk disclosure |
| Formal exclusions | No Package 1 or Package 4 implementation, no official `TP0008+` migrations or runner edits, no production/persistent DB, no patient data/real keys, no merge, no ACR signature, no official F2-B adoption and **no Gate A/B/C/D acceptance** |

**Important expiry rule:** If independent review or PO approval takes place at or after the proposed cutoff, this D0.1 **cannot be executed**; prepare and independently review a new *expressly selected* future cutoff before seeking approval. The proposed date is not an instruction for unattended future action, and there are no scheduled/background tasks.

---

## 3. Exact authorized work *if and only if* the PO later approves

The future grant is **not** a blanket permission to improve the repository. Execution must remain within the existing E0.3 contract and its nineteen auditable case IDs:

| Finding | Exact case IDs | Non-negotiable demonstration |
|---|---|---|
| **A01: fail-closed migrator identity** | `E03-A01-P01`, `E03-A01-N01` | Valid restricted-role migration succeeds; intentionally denied `SET ROLE`/wrong identity fails **before DDL or version stamping**, with no privileged fallback |
| **A02: real Phase-8 catalog guarantees** | `E03-A02-N01`, `E03-A02-P01`, `E03-A02-N02` | Negative incomplete state refused; positive **actual** `pg_attribute.attnotnull=true` **and** validated CHECK, valid index; invalid metadata/catalog state must not switch active authority |
| **A03: concurrent writes / stale-writer fencing** | `E03-A03-P01`, `E03-A03-N01` | At least two distinct overlapping PG transactions with deterministic interleaving; atomic old/new writes and old uniqueness; explicit monotonic token gate rejects stale/offline writer **before protected write** |
| **A04: Cloud/Local admission simulation** | `E03-A04-P01`, `E03-A04-N01` | Two independent disposable synthetic DBs and explicit allowlisted compatibility table; unknown/mixed/stale/reverse states refused before mock Sync mutations; real Sync remains UNVERIFIED |
| **A05: event/CI policy and closure** | `E03-A05-C01` | PO-approved new **push-only** branch/path policy, no secret/privilege/deployment leakage, correct run SHA, safe final evidence-only report without a second CI trigger; no post-final work |
| **A06: autocommit role / invalid-index / grant negatives** | `E03-A06-P01`, `E03-A06-N01`, `E03-A06-N02` | Actual role/session before/inside/after autocommit; indisvalid/index lifecycle observed and safely remediated; app-role `GRANT`/`ALTER ROLE`/RLS/version-table negatives refused with state checks |
| **A07: preflight and complete evidence** | `E03-A07-C01`, `E03-A07-C02` | Time-ordered pre-execution 19-case manifest, detailed per-case expected/observed/roles/SQLSTATE/catalog/logs, independently checked evidence checksums; no green-only shortcut |
| **A08: real allowlist guard** | `E03-A08-N01`, `E03-A08-P01` | Adversarial synthetic paths rejected; pre-SQL/CI full **source-parent→tested-SHA** diff includes adds/deletes/renames/modes/symlinks; no unauthorized paths |
| **Regression and termination** | `E03-REG-P01`, `E03-CLOSE-C01` | Only necessary synthetic safety regression, real PG15/source/cleanup proof and one final consolidated report; preserve immutable E0.2 evidence |

**Evidence success is not pytest success:** differentiate physical cases, governance controls, historical E0.2 results, NOT_RUN, BLOCKED, negative-case outcomes and the overall 19-case acceptance matrix. Even fully evidenced corrections permit **only independent governance review**, never official deployment or migration approval.

---

## 4. Mandatory execution order and conservative stop rules

This is a **conditional future sequence**. Do not execute it on receipt of this proposal.

1. **P0: approval barrier — READ ONLY.** Check exact separately approved E0.3 digest and separately approved final authorization-instrument digest; match the PO approval sentence and absolute UTC cutoff. Check it is before cutoff and no consolidated report has already been delivered. Any mismatch -> `BLOCKED_APPROVAL`, no writes.
2. **P1: source/CI and worktree reconciliation — READ ONLY.** Confirm repo remote identity, fresh clean worktree, E0.2 final SHA (not a short prefix), freeze the E0.2 evidence, mainline specification, actual R4.15 §§11.8–11.9 status, and all A01–A08 source baselines. Check existing CI triggers and production secret/deployment exposure. Record failures instead of guessing. No branch creation until all source gates pass.
3. **P2: pre-execution 19-case manifest — NO REPOSITORY WRITES.** Map each E0.3 case to source SHA, preconditions, role/transaction boundary, expected positive/negative, stop rule, exact allowed output and evidence schema. Check absolute time and operational ability to stop. If any required field absent -> `BLOCKED_PREFLIGHT`.
4. **P3: one experiment-only branch and allowlisted files.** Create one independent branch from verified E0.2 final evidence commit. Permit only two §2 allowed path entries, with canonical path and `git diff` checks. No E0.2 edits. Do not reuse E0.2 role/DB/version table in a mutable way; use `exp_e03_*` naming as defined in E0.3.
5. **P4: narrowly scoped, disposable PG15 experiment.** Prove server/version/net isolation first; use restricted app/migrator roles. Run the corrective case matrix and minimal regression with test-only data. On **any forbidden operation unexpectedly succeeding**, an unsafe role fallback, missed NOT NULL, active-uniqueness failure, absent writer fence or out-of-scope change, **STOP SECURITY**. Never silently make an unsafe result green. Do not repair official code.
6. **P5: exactly defined CI event, if necessary.** Only the separately approved E0.3 branch-restricted `push` mode. First confirm entire source-parent-to-tested-SHA changed-path guard and workflow privileges. Preserve all prior failed runs. No manual reruns outside still-active permission. Do not launch Actions if job/event restrictions or expiry cannot be controlled.
7. **P6: finish, clean up, consolidate, terminate.** Collect evidence and safe cleanup **before** final report delivery. Final output is one complete Markdown report at `experiments/m102_f2b_bounded_e03/evidence/M102_F2B_E03_FINAL_CONSOLIDATED_REPORT.md`, if a branch was created; otherwise a complete blocker report in Cursor response only. Include all 19 statuses, negative/positive actual PG evidence, sources/hashes, CI URLs, residuals, any STOP reason and one owner action. Final delivery **terminates** the grant.

**Hard STOP reasons:** missing/unapproved/mismatched source or hashes; no current PO grant; expiry or prior report delivery; dirty/unreconciled repo; disallowed path/symlink; unproven disposable DB identity; real/patient/persistent data or secrets; unverified restriction of PG roles; any successful negative security operation; incomplete Phase-8 catalog proof while authority switches; stale writer admitted; invalid index claimed valid; CI event/role/path leakage; unexpected external actions; unprovable evidence; cleanup requiring external privileges. In a STOP, preserve only safe permitted evidence and never broaden scope to fix it.

### 4.1 Additional limit: retries

This proposal deliberately imposes a conservative default: **at most one initial CI run and one corrective CI attempt** within the active grant, **only if** the first result is a non-security harness/coverage failure and changes remain within the allowlist. If a negative security assertion unexpectedly succeeds, or a true privilege/DB/isolation boundary is violated, the same grant **cannot be used to retry**: stop and seek a new PO decision. If the limited attempts cannot satisfy all proofs, publish an `INCOMPLETE` final report; never extend the grant by convention. Locally executed tests, when authorized, remain bounded by the same fixed cutoff and evidence rules.

---

## 5. Mandatory final evidence and prohibitions

The final record, if this instrument is later approved and executed, MUST include:

- Exact PO approval statement, **both complete file identities and SHA-256**, execution window, chosen `push` event, verified base/tested/final commits, and time of final delivery (all UTC).
- Frozen specification and roadmap candidate source identifiers; full source/evidence provenance, including independently validated historical E0.2 commit/artifact and original audit A01–A08.
- Each of **all 19** E0.3 IDs, with a separate full expected/observed, role/transaction, pg_catalog evidence, SQLSTATE/exit, timestamp, artifact digest and `PASS`/`FAIL`/`BLOCKED`/`NOT_RUN` status as specified by E0.3 §6. Indicate controls and physical tests separately.
- Branch and workflow diff path manifest before CI; no edited official sources; all run attempts and reason for any reattempt; exact PostgreSQL 15 server version and verified disposable role/DB provenance.
- Real cleanup evidence and any residual uncertainty; do not claim persistent Cloud/Local/Sync/security lifecycle compatibility based on synthetic proofs.
- One of `CORRECTIVE_EVIDENCE_SUFFICIENT_FOR_GOVERNANCE_REVIEW` or `CORRECTIVE_EVIDENCE_INCOMPLETE` / `STOPPED_SECURITY` / `BLOCKED_*`, according to evidence; **never** `F2-B APPROVED`, `PACKAGE 1 IMPLEMENTED/AUTHORIZED`, `ACR SIGNED`, or Gate A/B/C/D accepted.

No new official `TP0008+`, real migration DDL, deployment, permanent DB, patient data/real keys, code merge, policy/roadmap rewrite, ACR signature, official Package 1 or Package 4 work, or modification of historical E0.2 evidence may occur under this instrument.

---

## 6. Independent review gate for this instrument (current next stage)

Gemini should review **this entire D0.1 text**, the **complete exact E0.3** contract (not a summary), the A01–A08 independent audit, frozen spec clauses 771–772, historical CI run and source evidence (read-only), against the following questions:

1. Is the D0.1 document unequivocally **PROPOSED / NOT EXECUTABLE** until a new owner decision with **both** exact SHAs and fixed cutoff?
2. Does it preserve all E0.3 case IDs, safe branch origin, strict allowlist, original E0.2 immutability, negative STOP semantics, and limitation on synthetic evidence?
3. Does the changed `push`-only CI policy remain expressly conditional on a **new PO approval** and have an evidence-only no-rerun rule? Does any uncontrolled GitHub rerun/deployment path remain falsely claimed as impossible?
4. Does it avoid any implication of authorizing Package 1, official migrations, migration numbers, merge, real DB usage, ACR or Gate acceptance?
5. Are branch base, time cutoff, role privileges, schema evidence, cleanup, initial/retry bounds and termination requirements logically executable **within the proposal**, without any hidden out-of-scope edit?
6. Can the exact approval template in §7 be unambiguously matched to the **final independently reviewed bytes**? A material edit after review requires another hash and renewed review before owner approval.

**Reviewer output:** `PASS` or a **single complete revised `.md` file** with a new review revision (for example `D0.2`), preserving all valid content and supplying a precise change log. The reviewer must not create repository changes, launch Cursor or treat its independent assessment as an approval. If correction changes the authorization instrument, the owner must approve only the **last independently reviewed** filename and hash, not this superseded D0.1.

**Direct-agent limitation:** This instrument does not claim ChatGPT directly contacted Gemini or Cursor; external independent review requires actual delivery to those tools/chats. Prior Gemini's concurrence on the E0.3 **technical proposal** is not a review of this newly drafted D0.1 authorization instrument.

---

## 7. PO approval template — illustrative; **not signed or effective**

> **DO NOT TREAT THE QUOTATION BELOW AS ACTUAL CONSENT.** It is a sample for a later affirmative act after independent review. The owner must personally provide an unambiguous positive message naming the last reviewed document and its verified digest. If any field is missing or placeholder text remains, Cursor must return `BLOCKED_APPROVAL` without execution.

```text
I, as Product Owner of Clinic Ecosystem, separately and explicitly authorize Cursor ONLY to execute the bounded E0.3 corrective synthetic PostgreSQL 15 experiment under:
- Technical contract: M102_F2B_CORRECTIVE_EVIDENCE_AND_GOVERNANCE_CONTRACT_E0.3_PROPOSED.md
- Technical contract SHA-256: b5f8d33a33ff25e398cb75be76bebfab02a32cf8386e04b1e46f6cecc89ecb28
- Final authorization instrument: <EXACT REVIEWED FILENAME>
- Final authorization instrument SHA-256: <EXACT VERIFIED HASH>
- Absolute hard cutoff: 2026-11-27T22:59:00Z (2026-11-27 23:59 Europe/Berlin)
- Earlier cutoff: delivery of ONE final consolidated E0.3 report.
- Executor and scope: Cursor only; exactly one isolated E0.3 branch; only experiments/m102_f2b_bounded_e03/** and, if necessary, .github/workflows/m102-f2b-bounded-e03.yml; new branch-filtered push-only CI with E0.3 path guards; no PR, no merge.
- Resources: new disposable PostgreSQL 15, synthetic data and test-only keys; no actual persistent/clinical DBs.
- Work: the nineteen precisely enumerated E0.3 corrective and regression/closure cases; no formal Package 1 or official migration implementation.
- Exclusions: no changes to official migrations/app/runner, E0.2 historical sources/evidence, frozen specification or roadmap; no real patient data/secrets; no official ACR signature, adoption of F2-B DAG, PR merge, or acceptance of Gates A–D.
- Stop policy: immediate fail-closed STOP on source/approval/role/RLS/transaction/index/fencing/CI/path/time violations; no post-final work; initial and retry limits as recorded in the approved instrument.
This approval is only for this bounded correction experiment, not a production, migration or gate authorization.
```

**Approval controls:** The words above are neither PO consent nor a digital signature. PO may reject the proposal or change its requested expiration/CI bounds; any change must be recorded and independently reviewed, and the changed bytes separately approved. The immutable approval statement should be retained as evidence, but no approval or ACR is inferred from drafting this form.

---

## 8. Mandatory Cursor terminal marker (conditional future task)

For every future Cursor response on **an actually approved E0.3 task**, require the format from E0.3 §9, including the exact final terminal line. The final response must truthfully say `EXECUTION STATE: TERMINATED`, including BLOCKED/FAILED. Cursor must not keep working after that marker.

```text
TASK STATUS: COMPLETED / BLOCKED / FAILED
CONTRACT: M102 F2-B E0.3 (APPROVAL_STATUS: PROPOSED / APPROVED-AND-VERIFIED)
EXECUTION STATE: NOT STARTED / IN PROGRESS / TERMINATED
WORK PERFORMED: <precise actions, including what was not done>
EVIDENCE: <real SHAs/files/CI URLs, or NONE>
OPEN FINDINGS: <A01-A08 and case IDs; or NONE>
NEXT ACTION FOR PRODUCT OWNER: <exactly one actionable item, or NONE>

=== END OF CURSOR RESPONSE ===
```

---

## 9. Change log and final disposition

| Revision | Date | Summary | Classification |
|---|---|---|---|
| D0.1 | 2026-11-17 | New **separate proposed** PO authorization instrument, SHA-pinned to reviewed E0.3; binds one future Cursor-only experiment, nineteen corrective proof/control IDs, strictly allowlisted branch/resources, explicit new push-only CI policy, proposal-only UTC expiry, conservative retries, independent Gemini review, final-report termination and visible Cursor completion marker. | `DRAFTED / NOT APPROVED / NOT EXECUTED` |

**Terminal state:** `D0.1 PROPOSED / INDEPENDENT REVIEW PENDING / NO PO EXECUTION AUTHORITY / NO CURSOR WORK AUTHORIZED`.

=== END OF AUTHORIZATION INSTRUMENT D0.1 ===

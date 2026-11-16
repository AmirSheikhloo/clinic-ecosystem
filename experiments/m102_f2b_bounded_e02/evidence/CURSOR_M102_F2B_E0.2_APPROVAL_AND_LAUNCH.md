# Cursor launch instruction — M102 F2-B E0.2 bounded experiment

**Handoff prepared:** 2026-11-16. **Executor:** Cursor only. **Status:** PO-approved artifact; actual experiment has NOT been run or validated by ChatGPT. This handoff is a record of a user statement, not a cryptographic signature or an ACR/Gate approval.

## A. Explicit Product Owner authorization — exact quotation

> نسخه M102_F2B_REPLACEMENT_BOUNDED_EXPERIMENT_CONTRACT_E0.2_PROPOSED.md با SHA-256 03c471825a0ec404eb0ce173789a9d0dd87e3c42a656ed6cad459f277909ec31 را صرفاً برای آزمایش محدود Cursor و با تمام محدودیت‌های مندرج در آن تأیید می‌کنم.

This explicit statement was delivered by the Product Owner in the Clinic Ecosystem ChatGPT conversation on 2026-11-16. It identifies the **exact file and SHA-256** and is separate from the draft's historical `PROPOSED / NOT EFFECTIVE` status label. Do **not** edit the approved contract to change that label: changing its bytes would invalidate the approved digest. Treat this statement as conditional authorization **only for the exact digest**, only within the contracted scope and unexpired time window. Do not misstate this statement as an independent digital signature.

**Approved file (archive member):** `M102_F2B_REPLACEMENT_BOUNDED_EXPERIMENT_CONTRACT_E0.2_PROPOSED.md`  
**Expected SHA-256:** `03c471825a0ec404eb0ce173789a9d0dd87e3c42a656ed6cad459f277909ec31`  
**Hard stop:** earlier of (1) delivery of the one final consolidated report, or (2) `2026-11-23 23:59 Europe/Berlin` = `2026-11-23T22:59:00Z`.

## B. Instructions — preserve exact precedence and boundaries

1. **Before any state-changing action**, inspect this handoff and the accompanying approved E0.2 contract inside the archive **read-only/in-memory**, independently calculate SHA-256 of the E0.2 member's *raw bytes*, and compare to the expected value. Confirm the exact PO approval quoted above. Do not rely on the ZIP checksum alone, a renamed file, a cached summary, or a different revision. If mismatch or ambiguity: `BLOCKED_APPROVAL`; stop without writing. If any information in this handoff conflicts with the exact E0.2 body or the explicit PO exclusions, the **more restrictive rule wins**; stop for unresolved contradictions.
2. The previously referenced E0.1 file could not be located. **This is an approved replacement contract**, not a claim to reproduce E0.1. Do **not** demand the missing E0.1 as a prerequisite just because the *previous* Cursor directive required it. Do **not** apply or reuse `CURSOR_M102_F2B_BOUNDED_EXPERIMENT_INSTRUCTION_E0.1.md` as the governing instruction. If the original E0.1 becomes available and substantively conflicts, stop for reconciliation; never silently combine them.
3. **Run §5.1 of the E0.2 contract first, entirely read-only**. Verify current repository identity/cleanliness/base SHA; independently inspect actual frozen specification and complete accessible R4.15 §§11.8–11.9; validate safety manifest, allowlist, isolation, UTC/Berlin clock and expiry. If a source is unavailable or a gate fails, stop. Never infer pass from the prior read-only audit.
4. **Only after all §5.1 gates pass**, create exactly one *new independent* experiment branch, limited strictly to `experiments/m102_f2b_bounded_e02/**` and, **only if safe and necessary**, `.github/workflows/m102-f2b-bounded-e02.yml`. Follow §5.2 exactly, including all 14 IDs `E02-F2B-01`..`E02-F2B-14`, using *only fresh disposable PostgreSQL 15*, synthetic fixtures, independent synthetic Alembic revision IDs and experiment-local migrations. Execute **no official** `TPxxxx` migrations; change no mainline code, official migrations, real runner, `src/`, `tests/`, `ops/`, existing workflows, roadmap or docs. Do not touch permanent databases, patient records or real keys.
5. At most one Draft PR may be opened, **only if genuinely needed** for safe Actions execution and only after checking that no unrelated jobs, secrets or elevated permissions are activated. Never merge, mark ready, sign ACR, approve Gates A–D, or treat experimental outcomes as official deployability evidence.
6. Follow §5.3 exactly: provide ONE complete, source-grounded consolidated report with a test-by-test outcome/evidence matrix, security and cleanup facts, real commit/run IDs where observed, and unresolved blockers. Clean up experiment-owned resources safely **before final report delivery**. The authorization automatically terminates upon that delivery, even before the calendar deadline. Do not work or invoke CI after either cutoff.
7. For **every final response**, use the exact terminal format in E0.2 §7, ending in the visible line `=== END OF CURSOR RESPONSE ===`. A blocked result must say `TASK STATUS: BLOCKED`, `EXECUTION STATE: TERMINATED`, a short factual explanation, and **one** clear next action for the Product Owner (or `NONE`). Do not say the task is complete merely because the audit finished. No silent work after the marker.

## C. Next action for Cursor

Read the approved E0.2 contract verbatim and this PO approval, verify hash, then execute only the scope and prerequisites that actually pass. Do not ask the Product Owner to locate E0.1. Do not ask for further authorization for this identical E0.2 unless there is a genuine evidence, safety, scope, or expiry blocker; never broaden approval by interpretation.

**IMPORTANT:** This handoff and the ZIP are delivery aids only; the approved E0.2 bytes and the PO's explicit exclusions are the authority. Their attachment does not itself prove any experiment was executed.

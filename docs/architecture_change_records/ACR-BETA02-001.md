# ACR-BETA02-001 — Proposed contracts for the operations increment (PROPOSAL ONLY)

Status: **PROPOSED — not approved.** Raised by the autonomous development session on
branch `development/clinic-operations`. Only the Product Owner can approve or reject.
Nothing below closes an authorization gate. No migration was added: the tenant
lineage is still `tp0001`–`tp0007`.

## 1. What was implemented without a new contract

The increment uses only existing tables (`tenant_roles`, `role_permission_assignments`,
`user_role_assignments`, `staff_profiles`, `patient_profiles`, `appointments`,
`appointment_resource_allocations`, `services`, `service_resource_requirements`,
`resources`, audit and outbox tables). Writes carry expected-version (`If-Match`),
`Idempotency-Key`, audit rows and Outbox events where the existing event contract
allows it.

## 2. Provisional permission codes (ratification requested)

`BETA02_*` codes in `src/clinic_ecosystem/domain/access/permissions.py` (and the earlier
`BETA01B_*` codes) are provisional catalog entries used for synthetic data only. They are
enforced server-side; the browser only uses them to hide navigation. Decision needed:
ratify, rename or replace them with the approved catalog before any non-synthetic use.

## 3. Items blocked on missing contracts (isolated, no bypass introduced)

| # | Item | Why blocked | Proposed contract |
|---|------|-------------|-------------------|
| 1 | Granular department / service / provider permission scopes | No approved scope table or claim | `role_permission_scopes(tenant_id, role_id, permission_code, scope_kind, scope_ref)` with RLS; scope-aware checks in the permission resolver |
| 2 | Patient staff-only notes, tags, alerts | No schema | `patient_notes`, `patient_tags`, `patient_alerts` tables with encryption classification |
| 3 | Patient phones and official identifiers | Encryption / blind-index persistence still blocked; **syntax validation + Clause 755 exception path IMPLEMENTED (D0.4 PARTIAL)** — National ID validated, not stored as ciphertext until keys exist | Wire production KMS + panel lookup |
| 4 | Staff-to-service and staff-to-resource links | No link table | `staff_service_links` / `staff_resource_links` |
| 5 | ~~Check-in, complete, no-show transitions~~ | **IMPLEMENTED (D0.4)** on existing status CHECK values + provisional BETA02_* perms; no new migration | Ratify permission codes |
| 6 | Forced password change at first login | No `must_change_password` contract | Add column plus login-flow contract |
| 7 | Server-side `staff_kind` enum | Kind list is currently an application constant | DB enum or lookup table |
| 8 | Resource optimistic-concurrency version | `resources` has no version column; resource edits are idempotent but last-writer-wins | Add `row_version` to `resources` |
| 9 | Outbox event types for `appointment.cancelled` / `appointment.rescheduled` | Event-type registry lacks entries | Register event types and payload schemas |
| 10 | Name / trigram search indexes | Directory search is bounded (`LIMIT`, offset cap) but unindexed | Approve `pg_trgm` or a blind-index design for names |
| 11 | Tenant system-role seeding | System roles are created by fixtures only | Approved seeding migration or provisioning flow |
| 12 | Online-pool appointment cancellation | Intentionally returns 409; ONLINE and MANUAL capacity remain separate | Needs payment/refund lifecycle contract |

## 4. Anti-escalation rules implemented (for review)

* An actor can grant or revoke only permissions the actor holds (`privilege_escalation_denied`).
* An actor cannot change their own roles, governance or account status (`self_change_denied`).
* System-defined roles and reserved role codes cannot be created or edited through the API.
* `CLINIC_OWNER` and `CLINIC_MANAGER` governance is assignable only by an owner; other
  governance roles by an owner or manager. Governance edits need `BETA02_GOVERNANCE_MANAGE`.
* The last clinic owner cannot be removed (`last_owner`).
* A staff profile or doctor kind never grants access; login accounts are optional and separate.

## 5. Decisions requested from the Product Owner

1. Approve / rename the provisional permission codes (section 2).
2. Prioritise which blocked items (section 3) get contracts first; items 1, 5 and 8 unlock most product value.
3. Confirm whether an independent Gemini security review should gate any next increment.

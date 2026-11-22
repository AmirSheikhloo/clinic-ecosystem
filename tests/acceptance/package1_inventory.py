"""F0.5 90-case Package-1 acceptance inventory classifier.

Loads the pinned F0.5 CSV (SHA-256 638082e1...) and emits
PASS / FAIL / BLOCKED / NOT_EXECUTED with evidence. Never skip-as-pass.
"""
from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

EXPECTED_CSV_SHA256 = (
    "638082e119d37a468d4041dacca059509a8bb83a0c6da1bc06daec0552843e88"
)
FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "F0.5_90_CASE_R416_SOURCE_RECONCILED_TRACEABILITY.csv"
)
MIGRATIONS = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "tenant_plane"
    / "versions"
)

# Supporting unit/structural evidence does NOT constitute a complete
# F0.5 case-level Gate A PASS. Every outcome needs direct acceptance proof.
_SUPPORTING = {
    "RP1-021": (
        "PARTIAL_UNIT_EVIDENCE: non-UNIQUE ix_person_phones_lookup preserved in TP0002; "
        "SqlPhoneVault shared-phone create unit + PG15 shared HMAC coexistence test when Docker available"
    ),
    "RP1-023": "PARTIAL_UNIT_EVIDENCE: tests/unit/test_pii_contracts.py require_e164 vectors",
    "RP1-031": "PARTIAL_UNIT_EVIDENCE: tests/unit/test_pii_encryption.py AES-GCM roundtrip",
    "RP1-032": "PARTIAL_UNIT_EVIDENCE: tests/unit/test_pii_encryption.py AAD tenant/record transplant InvalidTag",
    "RP1-033": "PARTIAL_UNIT_EVIDENCE: tests/unit/test_pii_encryption.py original_person_id transplant InvalidTag",
    "RP1-035": "PARTIAL_UNIT_EVIDENCE: encrypt_phone/SqlNonceRegistry nonce reuse rejection",
    "RP1-036": "PARTIAL_UNIT_EVIDENCE: wrong key version + auth-tag tamper tests (encryption + reveal)",
    "RP1-051": "PARTIAL_STRUCTURAL_EVIDENCE: official versions directory contains only tp0001..tp0007 (no unauthorized tp0008+)",
    "RP1-055": "PARTIAL_UNIT_EVIDENCE: TP+CP env.py rollback-before-RESET ROLE unit proofs",
}

_BLOCKED = {
    "RP1-017": "BLOCKED: second-scan indisready=true/indisvalid=false NOT_PROVEN; needs Gate A PG15",
    "RP1-026": "BLOCKED: PH-01 official next-column migration unsigned; PO directions SHA 3f4f411a not found",
    "RP1-027": "BLOCKED: multi-generation phone read path depends on unsigned PH-01/PH-02 ADR",
    "RP1-028": "BLOCKED: PH-02 child table not selected/authorized",
    "RP1-034": "BLOCKED: phone AAD field/issuer tokens not frozen by attributable PO publication",
    "RP1-039": "BLOCKED: Local Hub per-tenant KMS isolation requires real KMS adapter",
    "RP1-040": "BLOCKED: tenant key revocation store/KMS unavailable",
    "RP1-041": "BLOCKED: dual-write rotation requires signed SCHEMA/HMAC ADR + keyed providers",
    "RP1-042": "BLOCKED: old-writer drain fence needs signed SCHEMA contract + deployment topology",
    "RP1-043": "BLOCKED: phase5 population scope requires authorized migration + keyed HMAC",
    "RP1-044": "BLOCKED: phase5 null-safe target version requires authorized SCHEMA ADR",
    "RP1-045": "BLOCKED: phase5 server-selected target version requires authorized SCHEMA ADR",
    "RP1-046": "BLOCKED: rotation #2+ slot lifecycle requires signed ADR",
    "RP1-047": "BLOCKED: phase8 attnotnull cutover migration not authorized",
    "RP1-048": "BLOCKED: phase8 VALIDATE CONSTRAINT cutover migration not authorized",
    "RP1-049": "BLOCKED: phase8 rollback window requires authorized cutover migrations",
    "RP1-050": "BLOCKED: phase9 requires separate authorization (explicitly out of M1-02)",
    "RP1-052": "BLOCKED: tp0011 competing allocations / F2-B official DAG not authorized (3f4f411a missing)",
    "RP1-054": "BLOCKED: official Alembic direct-argv fail-closed policy not implemented in env.py",
    "RP1-057": "BLOCKED: tp0011 multi-index crash recovery requires authorized Phase-6 migration",
    "RP1-058": "BLOCKED: two-hub cross-branch upgrade orderings require F2-B authority + topology",
    "RP1-059": "BLOCKED: true fresh-vs-upgrade T16 parity requires authorized tp0008+ heads",
    "RP1-060": "BLOCKED: Gate A nonprod full rotation proof reserved post-code / unsigned ADR",
    "RP1-068": "BLOCKED: API-PII-18 GET→POST controlled amendment not published",
    "RP1-072": "BLOCKED: Package-1 rotation writer-fencing/Sync ADR unsigned; writer-fencing implementation unproven",
    "RP1-073": "BLOCKED: Package-1 rotation writer-fencing/Sync ADR unsigned; writer-fencing implementation unproven",
    "RP1-074": "BLOCKED: Package-1 rotation writer-fencing/Sync ADR unsigned; writer-fencing implementation unproven",
    "RP1-075": "BLOCKED: stale writer fence across hubs requires topology + signed SCHEMA",
    "RP1-076": "BLOCKED: mixed-hub old HMAC compatibility requires authorized rotation",
    "RP1-077": "BLOCKED: Package-1 rotation writer-fencing/Sync ADR unsigned; writer-fencing implementation unproven",
    "RP1G-001": "BLOCKED: Route B / ACR provenance exception not effective",
    "RP1G-002": "BLOCKED: case identifier uniqueness supersession requires effective ACR",
    "RP1G-003": "BLOCKED: schema constraint catalog Gate A depends on unsigned physical ADRs",
    "RP1G-006": "BLOCKED: crypto backfill/alias depends on unsigned AAD/HMAC + SCHEMA ADR",
    "RP1G-007": "BLOCKED: disaster rollback of rotation requires authorized migrations",
    "RP1G-010": "BLOCKED: Gate A/B/C/D evidence receipt requires separate human decisions",
}


@dataclass(frozen=True)
class CaseOutcome:
    case_id: str
    case_title: str
    outcome: str
    evidence: str


def fixture_sha256() -> str:
    return hashlib.sha256(FIXTURE.read_bytes()).hexdigest()


def official_tp_revisions() -> list[str]:
    return sorted(p.name for p in MIGRATIONS.glob("tp*.py"))


def load_cases() -> list[dict[str, str]]:
    digest = fixture_sha256()
    if digest != EXPECTED_CSV_SHA256:
        raise RuntimeError(
            f"F0.5 CSV digest mismatch: got {digest}, expected {EXPECTED_CSV_SHA256}"
        )
    with FIXTURE.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def classify_case(row: dict[str, str]) -> CaseOutcome:
    case_id = row["case_id"]
    title = row.get("case_title", "")
    if case_id == "RP1-051":
        revisions = official_tp_revisions()
        expected = [
            "tp0001_extensions_and_tenant_root.py",
            "tp0002_identity_and_person_model.py",
            "tp0003_rbac_governance_minimum.py",
            "tp0004_catalog_resources_requirements.py",
            "tp0005_appointments_allocations_holds.py",
            "tp0006_idempotency_outbox_inbox_audit.py",
            "tp0007_rls_and_role_policies.py",
        ]
        if revisions != expected:
            return CaseOutcome(
                case_id,
                title,
                "FAIL",
                f"unexpected official revisions: {revisions}",
            )
        return CaseOutcome(
            case_id, title, "NOT_EXECUTED",
            _SUPPORTING[case_id] + "; SHA256 baseline plus case-level proof missing",
        )
    if case_id in _SUPPORTING:
        return CaseOutcome(
            case_id, title, "NOT_EXECUTED",
            _SUPPORTING[case_id] + "; F0.5 case-specific acceptance not executed",
        )
    if case_id in _BLOCKED:
        return CaseOutcome(case_id, title, "BLOCKED", _BLOCKED[case_id])
    return CaseOutcome(
        case_id,
        title,
        "NOT_EXECUTED",
        "no case-level automated evidence credited on this SHA; "
        "related unit/integration may exist but Gate A case remains open",
    )


def build_inventory() -> list[CaseOutcome]:
    return [classify_case(row) for row in load_cases()]


def inventory_summary(outcomes: list[CaseOutcome] | None = None) -> dict[str, object]:
    rows = outcomes or build_inventory()
    counts = {"PASS": 0, "FAIL": 0, "BLOCKED": 0, "NOT_EXECUTED": 0}
    for row in rows:
        counts[row.outcome] = counts.get(row.outcome, 0) + 1
    return {
        "csv_sha256": EXPECTED_CSV_SHA256,
        "case_count": len(rows),
        "counts": counts,
        "gate_a_pass_count": 0,
        "supporting_partial_evidence_count": sum(
            row.case_id in _SUPPORTING for row in rows
        ),
        "official_tp_revisions": official_tp_revisions(),
        "cases": [asdict(row) for row in rows],
    }


def write_inventory_json(path: Path) -> dict[str, object]:
    payload = inventory_summary()
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload

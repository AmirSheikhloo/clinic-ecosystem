"""Safe audit detail projections — never return raw free-form JSON to managers."""

from __future__ import annotations

from typing import Any

# Operation → allowlisted detail keys. Unknown keys are dropped.
_ALLOWLIST: dict[str, frozenset[str]] = {
    "finance.desk_checkout": frozenset(
        {"posted", "payment_method", "line_count", "received_irr", "applied_irr", "unapplied_credit_irr"}
    ),
    "finance.discount_applied": frozenset({"scope", "value"}),
    "finance.adjustment_recorded": frozenset({"kind", "patient_delta_irr", "invoice_id"}),
    "finance.refund_recorded": frozenset({"amount_irr", "original_receipt_id", "idempotency_key"}),
    "finance.receipt_recorded": frozenset({"invoice_id", "amount_irr", "payment_method", "idempotency_key"}),
    "appointment.checked_in": frozenset({"appointment_id"}),
    "appointment.completed": frozenset({"appointment_id"}),
    "appointment.cancelled": frozenset({"appointment_id", "reason_code"}),
    "appointment.no_show": frozenset({"appointment_id"}),
    "appointment.rescheduled": frozenset({"appointment_id"}),
}

_DEFAULT_ALLOW = frozenset({"result", "status", "count", "reason_code", "kind"})

# Keys that must never appear even if allowlisted by mistake.
_DENY = frozenset(
    {
        "password",
        "password_hash",
        "token",
        "access_token",
        "refresh_token",
        "secret",
        "ciphertext",
        "encrypted",
        "national_id",
        "phone",
        "phone_e164",
        "plaintext",
        "card_number",
        "pan",
        "cvv",
        "note_body",
        "body",
        "raw",
    }
)


def project_audit_details(operation: str, details: dict[str, Any] | None) -> dict[str, Any]:
    if not details:
        return {}
    allowed = _ALLOWLIST.get(operation, _DEFAULT_ALLOW)
    safe: dict[str, Any] = {}
    for key, value in details.items():
        lk = str(key).lower()
        if lk in _DENY or any(part in lk for part in _DENY):
            continue
        if key not in allowed:
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe[key] = value
        elif isinstance(value, list) and all(isinstance(x, (str, int, float, bool)) for x in value):
            safe[key] = value
        else:
            # Nested objects are not projected — avoid accidental PII leakage.
            safe[key] = "[redacted]"
    return safe

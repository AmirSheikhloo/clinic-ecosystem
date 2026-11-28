"""Audit detail allowlists must strip PII and unexpected keys."""

from __future__ import annotations

from clinic_ecosystem.presentation.http.audit_projection import project_audit_details


def test_known_operation_keeps_allowlisted_keys_only() -> None:
    details = {
        "posted": True,
        "payment_method": "CASH",
        "line_count": 2,
        "phone": "+98912",
        "national_id": "001",
        "ciphertext": "abc",
        "extra_secret": "nope",
    }
    out = project_audit_details("finance.desk_checkout", details)
    assert out == {"posted": True, "payment_method": "CASH", "line_count": 2}
    assert "phone" not in out
    assert "ciphertext" not in out


def test_unknown_operation_uses_default_allow_and_denies_sensitive() -> None:
    out = project_audit_details(
        "custom.op",
        {"status": "ok", "password": "x", "note_body": "secret note", "count": 3},
    )
    assert out == {"status": "ok", "count": 3}


def test_nested_objects_on_allowlist_are_redacted() -> None:
    # Force a nested value through the default allowlist key "status".
    out = project_audit_details(
        "custom.op",
        {"status": {"nested": True}, "count": 1, "password": "x"},
    )
    assert out["status"] == "[redacted]"
    assert out["count"] == 1
    assert "password" not in out

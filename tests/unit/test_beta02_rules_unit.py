"""Pure-logic unit tests for BETA-02 authorization rules and validators."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from clinic_ecosystem.application.catalog_admin.service import clean_service_fields
from clinic_ecosystem.application.patient_registry.service import PatientChanges, validate_changes
from clinic_ecosystem.application.shared.errors import (
    PreconditionRequired,
    ValidationFailed,
)
from clinic_ecosystem.application.shared.idempotent import fingerprint, validate_key
from clinic_ecosystem.application.shared.preconditions import etag, parse_if_match
from clinic_ecosystem.application.staff.service import LoginSpec, validate_login
from clinic_ecosystem.domain.access import permissions as perm
from clinic_ecosystem.domain.access import rules
from clinic_ecosystem.infrastructure.persistence.sql_helpers import like_contains


def test_permission_catalog_is_complete_and_unique() -> None:
    codes = [v for k, v in vars(perm).items() if k.isupper() and isinstance(v, str)]
    assert len(codes) == len(set(codes))
    assert set(codes) == set(perm.PERMISSION_CATALOG)
    for definition in perm.PERMISSION_CATALOG.values():
        assert definition.label_fa and definition.description and definition.category


def test_legacy_settings_still_export_original_codes() -> None:
    from clinic_ecosystem.infrastructure.auth import settings

    assert settings.PATIENTS_SEARCH == "BETA01B_PATIENTS_SEARCH"
    assert settings.CATALOG_SERVICES_READ == "CATALOG_SERVICES_READ"


@pytest.mark.parametrize("code", ["SUPER_ADMIN", "CLINIC_OWNER", "lowercase", "AB", "A" * 65, "BAD CODE"])
def test_role_code_rejections(code: str) -> None:
    assert rules.validate_role_code(code)


def test_role_code_accepts_valid() -> None:
    assert rules.validate_role_code("FRONT_DESK_2") is None


def test_ungrantable_is_set_difference() -> None:
    assert rules.ungrantable({"A", "B"}, {"A", "C"}) == {"C"}
    assert rules.ungrantable({"A"}, set()) == set()


def test_governance_authority_matrix() -> None:
    assert rules.governance_change_allowed({"CLINIC_OWNER"}, "CLINIC_OWNER")
    assert not rules.governance_change_allowed({"CLINIC_MANAGER"}, "CLINIC_OWNER")
    assert not rules.governance_change_allowed({"CLINIC_MANAGER"}, "CLINIC_MANAGER")
    assert rules.governance_change_allowed({"CLINIC_MANAGER"}, "DEPUTY_ADMIN")
    assert not rules.governance_change_allowed({"DEPUTY_ADMIN"}, "RECEPTIONIST")
    assert not rules.governance_change_allowed(set(), "RECEPTIONIST")


def test_if_match_parsing() -> None:
    assert parse_if_match('"7"') == 7
    assert parse_if_match('W/"12"') == 12
    assert parse_if_match("3") == 3
    assert etag(4) == '"4"'
    with pytest.raises(PreconditionRequired):
        parse_if_match(None)
    with pytest.raises(PreconditionRequired):
        parse_if_match("  ")
    for bad in ("abc", '"1.5"', "-1", "9" * 30):
        with pytest.raises(ValidationFailed):
            parse_if_match(bad)


def test_idempotency_key_validation_and_fingerprint_stability() -> None:
    assert validate_key("  abc ") == "abc"
    for bad in (None, "", "   ", "k" * 129):
        with pytest.raises(ValidationFailed):
            validate_key(bad)
    assert fingerprint({"a": 1, "b": [1, 2]}) == fingerprint({"b": [1, 2], "a": 1})
    assert fingerprint({"a": 1}) != fingerprint({"a": 2})


def test_patient_change_validation() -> None:
    ok = validate_changes(PatientChanges(
        fields_set=frozenset({"first_name", "dossier_number", "birth_date"}),
        first_name="  Ali ", dossier_number="  ", birth_date=date(1990, 1, 1)))
    assert ok == {"first_name": "Ali", "dossier_number": None, "birth_date": date(1990, 1, 1)}
    with pytest.raises(ValidationFailed):
        validate_changes(PatientChanges(fields_set=frozenset({"last_name"}), last_name=""))
    with pytest.raises(ValidationFailed):
        validate_changes(PatientChanges(fields_set=frozenset({"first_name"}), first_name="x" * 121))
    with pytest.raises(ValidationFailed):
        validate_changes(PatientChanges(fields_set=frozenset({"is_active"}), is_active=None))
    with pytest.raises(ValidationFailed):
        validate_changes(PatientChanges(fields_set=frozenset({"birth_date"}),
                                        birth_date=date.today() + timedelta(days=1)))
    assert validate_changes(PatientChanges(fields_set=frozenset())) == {}


def test_login_validation_never_accepts_weak_credentials() -> None:
    login, normalized = validate_login(LoginSpec("Dr.Test@clinic.test", "correct-horse-battery"))
    assert login == "Dr.Test@clinic.test" and normalized == "dr.test@clinic.test"
    for bad in (LoginSpec("ab", "correct-horse-battery"), LoginSpec("has space", "correct-horse-battery"),
                LoginSpec("valid@x.test", "short"), LoginSpec("valid@x.test", "x" * 129),
                LoginSpec("same-login-value", "same-login-value")):
        with pytest.raises(ValidationFailed):
            validate_login(bad)


def test_service_field_validation() -> None:
    created = clean_service_fields({"service_name": " Massage ", "default_duration_minutes": 45,
                                    "default_price_irr": 0}, creating=True)
    assert created["service_name"] == "Massage"
    for bad in ({"service_name": "", "default_duration_minutes": 5, "default_price_irr": 1},
                {"service_name": "x", "default_duration_minutes": 0, "default_price_irr": 1},
                {"service_name": "x", "default_duration_minutes": True, "default_price_irr": 1},
                {"service_name": "x", "default_duration_minutes": 5, "default_price_irr": -1}):
        with pytest.raises(ValidationFailed):
            clean_service_fields(bad, creating=True)
    assert clean_service_fields({"is_active": False}, creating=False) == {"is_active": False}
    with pytest.raises(ValidationFailed):
        clean_service_fields({"is_active": "no"}, creating=False)


def test_like_contains_escapes_metacharacters() -> None:
    assert like_contains("50%_off\\") == "%50\\%\\_off\\\\%"

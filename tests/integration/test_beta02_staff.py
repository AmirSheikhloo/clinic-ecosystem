"""BETA-02 Workstream B: staff directory, optional login provisioning."""

from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest

pytestmark = pytest.mark.integration


def _create(ops, headers, key, **overrides):
    body = {"first_name": "Sara", "last_name": "Staff", "staff_kind": "DOCTOR",
            "medical_council_code": "MC-1"} | overrides
    return ops.client.post("/api/v1/staff", headers={**headers, "Idempotency-Key": key}, json=body)


def test_staff_requires_permissions(ops) -> None:
    unauth = ops.unauthorized()
    assert ops.client.get("/api/v1/staff", headers=unauth).status_code == 403
    assert _create(ops, unauth, str(uuid.uuid4())).status_code == 403
    rec = ops.receptionist()
    assert ops.client.get("/api/v1/staff", headers=rec).status_code == 403
    assert ops.client.get("/api/v1/staff").status_code == 401


def test_create_staff_without_login_has_no_account_or_roles(ops) -> None:
    mgr = ops.manager()
    key = str(uuid.uuid4())
    res = _create(ops, mgr, key)
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["account_id"] is None
    detail = ops.client.get(f"/api/v1/staff/{body['staff_profile_id']}", headers=mgr)
    assert detail.status_code == 200 and detail.json()["account"] is None
    assert detail.json()["staff_kind"] == "DOCTOR"

    replay = _create(ops, mgr, key)
    assert replay.status_code == 200 and replay.json() == body
    assert replay.headers["Idempotent-Replay"] == "true"
    conflict = _create(ops, mgr, key, last_name="Different")
    assert conflict.status_code == 409 and conflict.json()["error"] == "idempotency_key_reuse"
    assert _create(ops, mgr, "").status_code in (400, 422)
    assert ops.client.post("/api/v1/staff", headers=mgr, json={"first_name": "a", "last_name": "b",
                                                              "staff_kind": "DOCTOR"}).status_code == 400


def test_validation_rejects_bad_kind_and_names(ops) -> None:
    mgr = ops.manager()
    assert _create(ops, mgr, str(uuid.uuid4()), staff_kind="WIZARD").status_code == 400
    assert _create(ops, mgr, str(uuid.uuid4()), first_name="  ").status_code == 400
    assert _create(ops, mgr, str(uuid.uuid4()), medical_council_code="x" * 65).status_code == 422


def test_login_provisioning_is_optional_separate_and_grants_nothing(ops) -> None:
    mgr = ops.manager()
    login = f"doc-{uuid.uuid4().hex[:8]}@beta02.test"
    res = _create(ops, mgr, str(uuid.uuid4()), create_login_account=True,
                  login={"login_identifier": login, "password": "A-long-test-password-1"})
    assert res.status_code == 201, res.text
    account_id = res.json()["account_id"]
    assert account_id

    session = ops.login(login, "A-long-test-password-1")
    me = ops.client.get("/api/v1/auth/me", headers=session).json()
    assert me["permissions"] == [] and me["governance_roles"] == []
    assert ops.client.get("/api/v1/staff", headers=session).status_code == 403
    assert ops.client.get("/api/v1/patients/directory", headers=session).status_code == 403

    dup = _create(ops, mgr, str(uuid.uuid4()), create_login_account=True,
                  login={"login_identifier": login.upper(), "password": "Another-long-password-2"})
    assert dup.status_code == 409 and dup.json()["error"] == "login_identifier_taken"
    weak = _create(ops, mgr, str(uuid.uuid4()), create_login_account=True,
                   login={"login_identifier": "weak@beta02.test", "password": "short"})
    assert weak.status_code == 400
    no_login = _create(ops, mgr, str(uuid.uuid4()), create_login_account=True)
    assert no_login.status_code == 400

    rows = ops.admin_query("SELECT password_hash_argon2id FROM user_accounts WHERE id = $1",
                           uuid.UUID(account_id))
    assert rows[0]["password_hash_argon2id"].startswith("$argon2id$")
    audit = ops.admin_query(
        "SELECT operation, details_json::text AS d FROM audit_entries WHERE target_id = $1",
        uuid.UUID(account_id))
    assert audit and "A-long-test-password" not in audit[0]["d"]


def test_provisioning_needs_dedicated_permission(ops) -> None:
    deputy = ops.deputy()
    # deputy holds STAFF_VIEW only: cannot create staff at all
    assert _create(ops, deputy, str(uuid.uuid4())).status_code == 403


def test_update_activate_deactivate_preserves_identity(ops) -> None:
    mgr = ops.manager()
    created = _create(ops, mgr, str(uuid.uuid4()), staff_kind="RECEPTIONIST",
                      create_login_account=True,
                      login={"login_identifier": f"rc-{uuid.uuid4().hex[:6]}@beta02.test",
                             "password": "Receptionist-pass-1234"}).json()
    sid = created["staff_profile_id"]
    url = f"/api/v1/staff/{sid}"
    headers = {**mgr, "If-Match": '"1"'}
    assert ops.client.patch(url, headers=mgr, json={"is_active": False}).status_code == 428
    off = ops.client.patch(url, headers=headers, json={"is_active": False})
    assert off.status_code == 200 and off.json()["is_active"] is False
    assert off.json()["account"]["is_active"] is True  # login access is separate
    stale = ops.client.patch(url, headers=headers, json={"first_name": "Late"})
    assert stale.status_code == 412
    upd = ops.client.patch(url, headers={**mgr, "If-Match": '"2"'},
                           json={"first_name": "Renamed", "staff_kind": "NURSE", "is_active": True})
    assert upd.status_code == 200
    assert (upd.json()["first_name"], upd.json()["staff_kind"]) == ("Renamed", "NURSE")
    ops_logged = ops.admin_query(
        "SELECT operation FROM audit_entries WHERE target_id = $1 ORDER BY created_at_utc",
        uuid.UUID(sid))
    assert [r["operation"] for r in ops_logged] == ["staff.created", "staff.deactivated", "staff.updated"]


def test_provision_login_for_existing_staff_and_duplicate_account(ops) -> None:
    mgr = ops.manager()
    sid = _create(ops, mgr, str(uuid.uuid4())).json()["staff_profile_id"]
    key = str(uuid.uuid4())
    body = {"login_identifier": f"late-{uuid.uuid4().hex[:6]}@beta02.test",
            "password": "Provisioned-pass-1234"}
    res = ops.client.post(f"/api/v1/staff/{sid}/login-account", headers={**mgr, "Idempotency-Key": key}, json=body)
    assert res.status_code == 201, res.text
    again = ops.client.post(f"/api/v1/staff/{sid}/login-account",
                            headers={**mgr, "Idempotency-Key": str(uuid.uuid4())},
                            json={**body, "login_identifier": "other-" + body["login_identifier"]})
    assert again.status_code == 409 and again.json()["error"] == "account_exists"


def test_staff_directory_filters_and_cross_tenant(ops) -> None:
    mgr = ops.manager()
    page = ops.client.get("/api/v1/staff", headers=mgr, params={"kind": "DOCTOR", "limit": 3})
    assert page.status_code == 200
    assert all(i["staff_kind"] == "DOCTOR" for i in page.json()["items"])
    assert str(ops.seed.tenant_b_staff_id) not in str(page.json())
    assert ops.client.get(f"/api/v1/staff/{ops.seed.tenant_b_staff_id}", headers=mgr).status_code == 404
    res = ops.client.patch(f"/api/v1/staff/{ops.seed.tenant_b_staff_id}",
                           headers={**mgr, "If-Match": '"1"'}, json={"is_active": False})
    assert res.status_code == 404
    assert ops.client.get("/api/v1/staff", headers=mgr, params={"limit": 101}).status_code == 422


def test_concurrent_creates_with_same_key_create_one_staff(ops) -> None:
    mgr = ops.manager()
    key = str(uuid.uuid4())
    marker = f"Conc{uuid.uuid4().hex[:6]}"
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: _create(ops, mgr, key, last_name=marker), range(4)))
    codes = sorted(r.status_code for r in results)
    assert set(codes) <= {200, 201, 425}, codes
    assert codes.count(201) == 1
    listing = ops.client.get("/api/v1/staff", headers=mgr, params={"q": marker}).json()
    assert listing["total"] == 1

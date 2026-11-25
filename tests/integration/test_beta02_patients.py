"""BETA-02 Workstream A: patient registry API on disposable PostgreSQL 15."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


def _hdr(token_headers, version=None, **extra):
    headers = dict(token_headers)
    if version is not None:
        headers["If-Match"] = f'"{version}"'
    headers.update(extra)
    return headers


def _register(ops, headers, first="Reza", last="Registry"):
    res = ops.client.post(
        "/api/v1/patients", headers=headers, json={"first_name": first, "last_name": last}
    )
    assert res.status_code == 201, res.text
    return res.json()["patient_profile_id"]


def test_registry_list_profile_and_filters(ops) -> None:
    rec = ops.receptionist()
    pid = _register(ops, rec, "Dina", "Directory")
    listing = ops.client.get(
        "/api/v1/patients/directory", headers=rec, params={"q": "Directory", "limit": 5}
    )
    assert listing.status_code == 200
    body = listing.json()
    assert body["total"] >= 1 and body["limit"] == 5
    assert any(i["patient_profile_id"] == pid for i in body["items"])

    inactive = ops.client.get("/api/v1/patients/directory", headers=rec, params={"status": "inactive"})
    assert inactive.status_code == 200
    assert all(not i["is_active"] for i in inactive.json()["items"])
    assert any(i["patient_profile_id"] == str(ops.seed.base.patient_inactive_id) for i in inactive.json()["items"])

    profile = ops.client.get(f"/api/v1/patients/{pid}", headers=rec)
    assert profile.status_code == 200
    assert profile.headers["ETag"] == '"1"'
    assert profile.json()["aggregate_version"] == 1

    assert ops.client.get("/api/v1/patients/directory", params={"q": "x"}).status_code == 401
    unauth = ops.unauthorized()
    assert ops.client.get("/api/v1/patients/directory", headers=unauth).status_code == 403
    assert ops.client.get(f"/api/v1/patients/{pid}", headers=unauth).status_code == 403


def test_pagination_is_bounded(ops) -> None:
    rec = ops.receptionist()
    assert ops.client.get("/api/v1/patients/directory", headers=rec, params={"limit": 51}).status_code == 422
    page1 = ops.client.get("/api/v1/patients/directory", headers=rec, params={"limit": 1, "offset": 0}).json()
    page2 = ops.client.get("/api/v1/patients/directory", headers=rec, params={"limit": 1, "offset": 1}).json()
    assert len(page1["items"]) == 1
    assert page1["items"][0]["patient_profile_id"] != page2["items"][0]["patient_profile_id"]


def test_update_requires_if_match_and_detects_stale_versions(ops) -> None:
    rec = ops.receptionist()
    pid = _register(ops, rec, "Vera", "Version")
    url = f"/api/v1/patients/{pid}"
    assert ops.client.patch(url, headers=rec, json={"first_name": "Vera2"}).status_code == 428
    assert ops.client.patch(url, headers=_hdr(rec, "abc"), json={"first_name": "x"}).status_code == 400

    ok = ops.client.patch(url, headers=_hdr(rec, 1), json={"first_name": "Vera2", "dossier_number": "D-1001"})
    assert ok.status_code == 200, ok.text
    assert ok.json()["aggregate_version"] == 2 and ok.json()["dossier_number"] == "D-1001"
    assert ok.headers["ETag"] == '"2"'

    stale = ops.client.patch(url, headers=_hdr(rec, 1), json={"first_name": "Stale"})
    assert stale.status_code == 412
    assert stale.json()["current_version"] == 2
    assert stale.headers["content-type"].startswith("application/problem+json")

    noop = ops.client.patch(url, headers=_hdr(rec, 2), json={"first_name": "Vera2"})
    assert noop.status_code == 200 and noop.json()["aggregate_version"] == 2

    other = _register(ops, rec, "Dup", "Dossier")
    dup = ops.client.patch(f"/api/v1/patients/{other}", headers=_hdr(rec, 1), json={"dossier_number": "D-1001"})
    assert dup.status_code == 409 and dup.json()["error"] == "dossier_in_use"

    bad = ops.client.patch(url, headers=_hdr(rec, 2), json={"first_name": "   "})
    assert bad.status_code == 400
    future = ops.client.patch(url, headers=_hdr(rec, 2), json={"birth_date": "2999-01-01"})
    assert future.status_code == 400


def test_activation_needs_its_own_permission_and_is_audited(ops) -> None:
    rec = ops.receptionist()
    pid = _register(ops, rec, "Anna", "Active")
    denied = ops.client.patch(f"/api/v1/patients/{pid}", headers=_hdr(rec, 1), json={"is_active": False})
    assert denied.status_code == 403

    mgr = ops.manager()
    ok = ops.client.patch(f"/api/v1/patients/{pid}", headers=_hdr(mgr, 1), json={"is_active": False})
    assert ok.status_code == 200 and ok.json()["is_active"] is False
    rows = ops.admin_query(
        "SELECT operation, details_json FROM audit_entries WHERE target_id = $1 ORDER BY created_at_utc",
        __import__("uuid").UUID(pid),
    )
    assert [r["operation"] for r in rows] == ["patient.registered", "patient.deactivated"]
    assert "Anna" not in str(rows[1]["details_json"])

    reactivated = ops.client.patch(f"/api/v1/patients/{pid}", headers=_hdr(mgr, 2), json={"is_active": True})
    assert reactivated.status_code == 200 and reactivated.json()["is_active"] is True


def test_cross_tenant_and_unknown_patient_return_404(ops) -> None:
    rec = ops.receptionist()
    secret = str(ops.seed.base.patient_b_id)
    assert ops.client.get(f"/api/v1/patients/{secret}", headers=rec).status_code == 404
    res = ops.client.patch(f"/api/v1/patients/{secret}", headers=_hdr(rec, 1), json={"first_name": "Hijack"})
    assert res.status_code == 404
    hist = ops.client.get(f"/api/v1/patients/{secret}/appointments", headers=rec)
    assert hist.status_code == 404
    search = ops.client.get("/api/v1/patients/directory", headers=rec, params={"q": "Secret", "status": "all"})
    assert search.status_code == 200 and search.json()["items"] == []


def test_patient_history_lists_appointments(ops) -> None:
    rec = ops.receptionist()
    base = ops.seed.base
    pid = str(base.patient_a_id)
    res = ops.client.get(f"/api/v1/patients/{pid}/appointments", headers=rec, params={"limit": 10})
    assert res.status_code == 200
    body = res.json()
    assert set(body) == {"items", "total", "limit", "offset"}
    assert ops.client.get(f"/api/v1/patients/{pid}/appointments", headers=ops.unauthorized()).status_code == 403

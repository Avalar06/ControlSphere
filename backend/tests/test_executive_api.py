from datetime import date, datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.permissions import RoleEnum
from app.core.security import get_password_hash
from app.models.organization import Organization
from app.models.user import User
from tests.conftest import get_token_headers


@pytest.fixture
def exec_api_fixture(db: Session, org_apex: Organization):
    admin = User(
        email="exec_api_admin@apex.com",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Executive Admin",
        role=RoleEnum.ADMIN,
        is_active=True,
        organization_id=org_apex.id,
    )
    manager = User(
        email="exec_api_mgr@apex.com",
        hashed_password=get_password_hash("MgrPass123!"),
        full_name="Executive Manager",
        role=RoleEnum.MANAGER,
        is_active=True,
        organization_id=org_apex.id,
    )
    analyst = User(
        email="exec_api_analyst@apex.com",
        hashed_password=get_password_hash("AnalystPass123!"),
        full_name="Executive Analyst",
        role=RoleEnum.GRC_ANALYST,
        is_active=True,
        organization_id=org_apex.id,
    )
    viewer = User(
        email="exec_api_viewer@apex.com",
        hashed_password=get_password_hash("ViewerPass123!"),
        full_name="Executive Viewer",
        role=RoleEnum.VIEWER,
        is_active=True,
        organization_id=org_apex.id,
    )

    db.add_all([admin, manager, analyst, viewer])
    db.commit()
    for u in [admin, manager, analyst, viewer]:
        db.refresh(u)

    admin_headers = get_token_headers(admin)
    mgr_headers = get_token_headers(manager)
    analyst_headers = get_token_headers(analyst)
    viewer_headers = get_token_headers(viewer)

    return {
        "org": org_apex,
        "admin": admin,
        "manager": manager,
        "analyst": analyst,
        "viewer": viewer,
        "admin_headers": admin_headers,
        "mgr_headers": mgr_headers,
        "analyst_headers": analyst_headers,
        "viewer_headers": viewer_headers,
    }


def test_telemetry_live_and_trends_api(client: TestClient, exec_api_fixture):
    headers = exec_api_fixture["analyst_headers"]

    # Live telemetry
    res = client.get("/api/v1/executive/telemetry/live", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "overall_posture_score" in data
    assert "domain_posture_breakdown" in data
    assert "audit_readiness_index" in data

    # Domain matrix
    res_matrix = client.get("/api/v1/executive/telemetry/domain-matrix", headers=headers)
    assert res_matrix.status_code == 200
    assert "domains" in res_matrix.json()

    # Trends
    res_trends = client.get("/api/v1/executive/telemetry/trends?window_days=30", headers=headers)
    assert res_trends.status_code == 200
    assert len(res_trends.json()["data_points"]) >= 1


def test_snapshot_lifecycle_api(client: TestClient, exec_api_fixture):
    analyst_headers = exec_api_fixture["analyst_headers"]

    # 1. Capture snapshot
    payload = {"snapshot_code": "SNAP-API-001", "notes": "API test snapshot"}
    res = client.post("/api/v1/executive/snapshots", json=payload, headers=analyst_headers)
    assert res.status_code == 201
    snap = res.json()
    assert snap["snapshot_code"] == "SNAP-API-001"
    assert len(snap["data_hash_sha256"]) == 64
    snap_id = snap["id"]

    # 2. List snapshots
    res_list = client.get("/api/v1/executive/snapshots", headers=analyst_headers)
    assert res_list.status_code == 200
    assert any(s["id"] == snap_id for s in res_list.json())

    # 3. Get single snapshot
    res_get = client.get(f"/api/v1/executive/snapshots/{snap_id}", headers=analyst_headers)
    assert res_get.status_code == 200
    assert res_get.json()["snapshot_code"] == "SNAP-API-001"


def test_dossier_full_api_workflow(client: TestClient, exec_api_fixture):
    admin_headers = exec_api_fixture["admin_headers"]
    analyst_headers = exec_api_fixture["analyst_headers"]
    mgr_headers = exec_api_fixture["mgr_headers"]

    # 1. Create Dossier by Manager
    payload = {
        "dossier_code": "DOS-API-001",
        "title": "API Regulatory Dossier",
        "dossier_type": "REGULATORY_SUBMISSION",
        "executive_summary": "Executive statement",
    }
    res = client.post("/api/v1/executive/dossiers", json=payload, headers=mgr_headers)
    assert res.status_code == 201
    dossier = res.json()
    dossier_id = dossier["id"]
    assert dossier["status"] == "DRAFT"

    # 2. Update Dossier
    patch_res = client.patch(
        f"/api/v1/executive/dossiers/{dossier_id}",
        json={"title": "Updated API Regulatory Dossier"},
        headers=mgr_headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["title"] == "Updated API Regulatory Dossier"

    # 3. Compile Dossier
    comp_res = client.post(f"/api/v1/executive/dossiers/{dossier_id}/compile", headers=mgr_headers)
    assert comp_res.status_code == 200
    assert comp_res.json()["status"] == "COMPILED"

    # 4. Self-finalization by Manager -> 400 Bad Request (Four-Eyes violation)
    self_fin = client.post(f"/api/v1/executive/dossiers/{dossier_id}/finalize", headers=mgr_headers)
    assert self_fin.status_code == 400
    assert "Four-Eyes violation" in self_fin.json()["detail"]

    # 5. Independent Admin finalizes Dossier -> 200 OK
    admin_fin = client.post(f"/api/v1/executive/dossiers/{dossier_id}/finalize", headers=admin_headers)
    assert admin_fin.status_code == 200
    assert admin_fin.json()["status"] == "FINALIZED"


def test_briefing_full_api_workflow(client: TestClient, exec_api_fixture):
    admin_headers = exec_api_fixture["admin_headers"]
    mgr_headers = exec_api_fixture["mgr_headers"]

    # Snapshot first
    snap_res = client.post(
        "/api/v1/executive/snapshots",
        json={"snapshot_code": "SNAP-FOR-BRF"},
        headers=mgr_headers,
    )
    snap_id = snap_res.json()["id"]

    # 1. Create briefing by Manager
    briefing_payload = {
        "briefing_code": "BRF-API-Q3",
        "title": "Q3 Executive Briefing API",
        "reporting_period_start": "2026-07-01",
        "reporting_period_end": "2026-09-30",
        "snapshot_id": snap_id,
        "executive_summary": "Comprehensive Q3 Cyber Risk Briefing for Executive Leadership.",
        "key_achievements": ["Zero open critical exposures"],
        "emerging_risks": ["Third party cloud dependency"],
    }
    res = client.post("/api/v1/executive/briefings", json=briefing_payload, headers=mgr_headers)
    assert res.status_code == 201
    briefing_id = res.json()["id"]
    assert res.json()["status"] == "DRAFT"

    # 2. Submit briefing
    sub_res = client.post(f"/api/v1/executive/briefings/{briefing_id}/submit", headers=mgr_headers)
    assert sub_res.status_code == 200
    assert sub_res.json()["status"] == "SUBMITTED_FOR_REVIEW"

    # 3. Manager self-approval blocked -> 400 Bad Request (Four-Eyes violation)
    self_rev = client.post(
        f"/api/v1/executive/briefings/{briefing_id}/review",
        json={"approved": True},
        headers=mgr_headers,
    )
    assert self_rev.status_code == 400
    assert "Four-Eyes violation" in self_rev.json()["detail"]

    # 4. Independent Admin reviews & approves -> 200 OK
    admin_rev = client.post(
        f"/api/v1/executive/briefings/{briefing_id}/review",
        json={"approved": True, "review_notes": "Approved for board review"},
        headers=admin_headers,
    )
    assert admin_rev.status_code == 200
    assert admin_rev.json()["status"] == "APPROVED"


def test_exports_and_download_api(client: TestClient, exec_api_fixture):
    analyst_headers = exec_api_fixture["analyst_headers"]

    snap_res = client.post(
        "/api/v1/executive/snapshots",
        json={"snapshot_code": "SNAP-FOR-EXP"},
        headers=analyst_headers,
    )
    snap_id = snap_res.json()["id"]

    # 1. Export PDF
    pdf_res = client.post(f"/api/v1/executive/exports/snapshot/{snap_id}?format=PDF", headers=analyst_headers)
    assert pdf_res.status_code == 201
    pdf_data = pdf_res.json()
    assert pdf_data["export_format"] == "PDF"
    export_id = pdf_data["id"]

    # 2. Export JSON
    json_res = client.post(f"/api/v1/executive/exports/snapshot/{snap_id}?format=JSON", headers=analyst_headers)
    assert json_res.status_code == 201
    assert json_res.json()["export_format"] == "JSON"

    # 3. List exports
    list_res = client.get("/api/v1/executive/exports", headers=analyst_headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 2

    # 4. Download Export Stream
    dl_res = client.get(f"/api/v1/executive/exports/{export_id}/download", headers=analyst_headers)
    assert dl_res.status_code == 200
    assert dl_res.headers["content-type"] == "application/pdf"
    assert len(dl_res.content) > 0

from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.permissions import RoleEnum
from app.core.security import get_password_hash
from app.models.control import OrganizationControl, ImplementationStatusEnum, PriorityEnum
from app.models.exposure import (
    AssetTypeEnum,
    EnvironmentEnum,
    ExceptionApprovalStatusEnum,
    ExposureSeverityEnum,
    ExposureStatusEnum,
    VulnerabilityExposure,
)
from app.models.organization import Organization
from app.models.resilience import BusinessProcess, CriticalityTierEnum
from app.models.tprm import Vendor, VendorStatusEnum, VendorTierEnum
from app.models.user import User
from tests.conftest import get_token_headers


@pytest.fixture
def exposure_api_setup(db: Session, org_apex: Organization, org_meridian: Organization):
    """Setup multi-role users and foundational GRC entities for Phase 14 API tests."""
    admin = User(
        email="exp_admin@apex.com",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Exposure Admin",
        role=RoleEnum.ADMIN,
        is_active=True,
        organization_id=org_apex.id,
    )
    manager = User(
        email="exp_manager@apex.com",
        hashed_password=get_password_hash("ManagerPass123!"),
        full_name="Exposure Manager",
        role=RoleEnum.MANAGER,
        is_active=True,
        organization_id=org_apex.id,
    )
    sec_analyst = User(
        email="exp_sec_analyst@apex.com",
        hashed_password=get_password_hash("SecAnalystPass123!"),
        full_name="Exposure Sec Analyst",
        role=RoleEnum.SECURITY_ANALYST,
        is_active=True,
        organization_id=org_apex.id,
    )
    grc_analyst = User(
        email="exp_grc_analyst@apex.com",
        hashed_password=get_password_hash("GrcAnalystPass123!"),
        full_name="Exposure GRC Analyst",
        role=RoleEnum.GRC_ANALYST,
        is_active=True,
        organization_id=org_apex.id,
    )
    auditor = User(
        email="exp_auditor@apex.com",
        hashed_password=get_password_hash("AuditorPass123!"),
        full_name="Exposure Auditor",
        role=RoleEnum.AUDITOR,
        is_active=True,
        organization_id=org_apex.id,
    )
    viewer = User(
        email="exp_viewer@apex.com",
        hashed_password=get_password_hash("ViewerPass123!"),
        full_name="Exposure Viewer",
        role=RoleEnum.VIEWER,
        is_active=True,
        organization_id=org_apex.id,
    )

    # Foreign Meridian users
    foreign_admin = User(
        email="foreign_admin@meridian.com",
        hashed_password=get_password_hash("ForeignAdmin123!"),
        full_name="Meridian Admin",
        role=RoleEnum.ADMIN,
        is_active=True,
        organization_id=org_meridian.id,
    )

    db.add_all([admin, manager, sec_analyst, grc_analyst, auditor, viewer, foreign_admin])
    db.commit()

    # Phase 13 Process in Apex
    proc_apex = BusinessProcess(
        organization_id=org_apex.id,
        name="Apex Settlement Gateway",
        owner_id=admin.id,
        criticality_tier=CriticalityTierEnum.TIER_1,
    )
    # Phase 9 Vendor in Apex
    vendor_apex = Vendor(
        organization_id=org_apex.id,
        legal_name="Apex Cloud Provider",
        vendor_code="VND-APX-01",
        vendor_status=VendorStatusEnum.ACTIVE,
        calculated_tier=VendorTierEnum.TIER_1_CRITICAL,
    )
    # Phase 2 Control in Apex
    ctrl_apex = OrganizationControl(
        organization_id=org_apex.id,
        subcategory_id=1,
        status=ImplementationStatusEnum.IMPLEMENTED,
        priority=PriorityEnum.HIGH,
    )

    # Foreign entities in Meridian
    proc_meridian = BusinessProcess(
        organization_id=org_meridian.id,
        name="Meridian Patient Record System",
        owner_id=foreign_admin.id,
        criticality_tier=CriticalityTierEnum.TIER_1,
    )

    db.add_all([proc_apex, vendor_apex, ctrl_apex, proc_meridian])
    db.commit()

    return {
        "org_apex": org_apex,
        "org_meridian": org_meridian,
        "admin": admin,
        "manager": manager,
        "sec_analyst": sec_analyst,
        "grc_analyst": grc_analyst,
        "auditor": auditor,
        "viewer": viewer,
        "foreign_admin": foreign_admin,
        "proc_apex": proc_apex,
        "vendor_apex": vendor_apex,
        "ctrl_apex": ctrl_apex,
        "proc_meridian": proc_meridian,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 1. EXPOSURE CATALOG ENDPOINTS TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_create_exposure_admin_success(client: TestClient, exposure_api_setup):
    """Admin creates a vulnerability exposure (201 Created)."""
    s = exposure_api_setup
    payload = {
        "cve_id": "CVE-2026-9001",
        "cwe_id": "CWE-89",
        "title": "SQL Injection in Authentication Microservice",
        "description": "Exploitable SQLi via user-agent header.",
        "cvss_score": 9.8,
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "epss_score": 0.82,
        "cisa_kev": True,
        "severity": "CRITICAL",
    }
    response = client.post(
        "/api/v1/exposures",
        json=payload,
        headers=get_token_headers(s["admin"]),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["cve_id"] == "CVE-2026-9001"
    assert data["status"] == "OPEN"
    assert data["exposure_index"] > 0
    assert data["organization_id"] == s["org_apex"].id


def test_create_exposure_security_analyst_success(client: TestClient, exposure_api_setup):
    """Security Analyst creates exposure (201 Created)."""
    s = exposure_api_setup
    payload = {
        "cve_id": "CVE-2026-9002",
        "title": "Remote Buffer Overflow",
        "cvss_score": 8.0,
        "epss_score": 0.5,
        "cisa_kev": False,
        "severity": "HIGH",
    }
    response = client.post(
        "/api/v1/exposures",
        json=payload,
        headers=get_token_headers(s["sec_analyst"]),
    )
    assert response.status_code == 201


def test_create_exposure_viewer_forbidden(client: TestClient, exposure_api_setup):
    """Viewer cannot create exposure (403 Forbidden)."""
    s = exposure_api_setup
    payload = {
        "cve_id": "CVE-2026-9003",
        "title": "Unauthorized Write Test",
        "cvss_score": 5.0,
    }
    response = client.post(
        "/api/v1/exposures",
        json=payload,
        headers=get_token_headers(s["viewer"]),
    )
    assert response.status_code == 403


def test_list_exposures_with_filters(client: TestClient, exposure_api_setup):
    """List exposures with severity and search filters."""
    s = exposure_api_setup
    # Create two exposures
    client.post(
        "/api/v1/exposures",
        json={"cve_id": "CVE-2026-9101", "title": "Critical Exposure Alpha", "cvss_score": 9.5, "severity": "CRITICAL", "cisa_kev": True},
        headers=get_token_headers(s["admin"]),
    )
    client.post(
        "/api/v1/exposures",
        json={"cve_id": "CVE-2026-9102", "title": "Medium Exposure Beta", "cvss_score": 5.0, "severity": "MEDIUM", "cisa_kev": False},
        headers=get_token_headers(s["admin"]),
    )

    # Filter by severity
    res_crit = client.get(
        "/api/v1/exposures?severity=CRITICAL",
        headers=get_token_headers(s["viewer"]),
    )
    assert res_crit.status_code == 200
    crit_items = res_crit.json()
    assert any(e["cve_id"] == "CVE-2026-9101" for e in crit_items)
    assert not any(e["cve_id"] == "CVE-2026-9102" for e in crit_items)

    # Search filter
    res_search = client.get(
        "/api/v1/exposures?search=Beta",
        headers=get_token_headers(s["viewer"]),
    )
    assert res_search.status_code == 200
    search_items = res_search.json()
    assert len(search_items) == 1
    assert search_items[0]["cve_id"] == "CVE-2026-9102"


def test_get_exposure_detail(client: TestClient, exposure_api_setup):
    """Retrieve single exposure detail."""
    s = exposure_api_setup
    create_res = client.post(
        "/api/v1/exposures",
        json={"cve_id": "CVE-2026-9201", "title": "Exposure Detail Test", "cvss_score": 7.5},
        headers=get_token_headers(s["admin"]),
    )
    exp_id = create_res.json()["id"]

    res = client.get(
        f"/api/v1/exposures/{exp_id}",
        headers=get_token_headers(s["auditor"]),
    )
    assert res.status_code == 200
    assert res.json()["id"] == exp_id


def test_get_exposure_not_found(client: TestClient, exposure_api_setup):
    """Non-existent exposure returns 404."""
    s = exposure_api_setup
    res = client.get(
        "/api/v1/exposures/999999",
        headers=get_token_headers(s["viewer"]),
    )
    assert res.status_code == 404


def test_update_exposure_telemetry(client: TestClient, exposure_api_setup):
    """Update CVSS/EPSS on exposure and verify score recalculation."""
    s = exposure_api_setup
    create_res = client.post(
        "/api/v1/exposures",
        json={"cve_id": "CVE-2026-9301", "title": "Telemetry Update Test", "cvss_score": 5.0, "epss_score": 0.1},
        headers=get_token_headers(s["admin"]),
    )
    exp_id = create_res.json()["id"]

    update_res = client.put(
        f"/api/v1/exposures/{exp_id}",
        json={"cvss_score": 8.5, "epss_score": 0.6, "cisa_kev": True},
        headers=get_token_headers(s["sec_analyst"]),
    )
    assert update_res.status_code == 200
    data = update_res.json()
    assert data["cvss_score"] == 8.5
    assert data["cisa_kev"] is True
    assert data["exposure_index"] > create_res.json()["exposure_index"]


def test_lifecycle_status_transition(client: TestClient, exposure_api_setup):
    """Transition exposure status OPEN -> UNDER_INVESTIGATION -> REMEDIATING -> RESOLVED."""
    s = exposure_api_setup
    create_res = client.post(
        "/api/v1/exposures",
        json={"cve_id": "CVE-2026-9401", "title": "Lifecycle Test", "cvss_score": 7.0},
        headers=get_token_headers(s["admin"]),
    )
    exp_id = create_res.json()["id"]

    # 1. UNDER_INVESTIGATION
    res1 = client.put(
        f"/api/v1/exposures/{exp_id}/status",
        json={"status": "UNDER_INVESTIGATION", "notes": "Triaging"},
        headers=get_token_headers(s["sec_analyst"]),
    )
    assert res1.status_code == 200
    assert res1.json()["status"] == "UNDER_INVESTIGATION"

    # 2. REMEDIATING
    res2 = client.put(
        f"/api/v1/exposures/{exp_id}/status",
        json={"status": "REMEDIATING"},
        headers=get_token_headers(s["sec_analyst"]),
    )
    assert res2.status_code == 200
    assert res2.json()["status"] == "REMEDIATING"

    # 3. RESOLVED
    res3 = client.put(
        f"/api/v1/exposures/{exp_id}/status",
        json={"status": "RESOLVED"},
        headers=get_token_headers(s["manager"]),
    )
    assert res3.status_code == 200
    assert res3.json()["status"] == "RESOLVED"
    assert res3.json()["resolved_at"] is not None


def test_lifecycle_illegal_transition_conflict(client: TestClient, exposure_api_setup):
    """Illegal status transition returns 409 Conflict."""
    s = exposure_api_setup
    create_res = client.post(
        "/api/v1/exposures",
        json={"cve_id": "CVE-2026-9501", "title": "Illegal Transition Test", "cvss_score": 6.0},
        headers=get_token_headers(s["admin"]),
    )
    exp_id = create_res.json()["id"]

    # OPEN -> EXCEPTION_APPROVED directly (illegal, only allowed via Exception review)
    res = client.put(
        f"/api/v1/exposures/{exp_id}/status",
        json={"status": "EXCEPTION_APPROVED"},
        headers=get_token_headers(s["manager"]),
    )
    assert res.status_code == 409


def test_modify_resolved_record_conflict(client: TestClient, exposure_api_setup):
    """Mutating or transitioning a RESOLVED exposure returns 409 Conflict."""
    s = exposure_api_setup
    create_res = client.post(
        "/api/v1/exposures",
        json={"cve_id": "CVE-2026-9601", "title": "Resolved Immutability Test", "cvss_score": 6.0},
        headers=get_token_headers(s["admin"]),
    )
    exp_id = create_res.json()["id"]

    # Transition to RESOLVED
    client.put(
        f"/api/v1/exposures/{exp_id}/status",
        json={"status": "RESOLVED"},
        headers=get_token_headers(s["admin"]),
    )

    # Attempt update
    res_update = client.put(
        f"/api/v1/exposures/{exp_id}",
        json={"title": "Hacked Title"},
        headers=get_token_headers(s["admin"]),
    )
    assert res_update.status_code == 409

    # Attempt status rollback
    res_status = client.put(
        f"/api/v1/exposures/{exp_id}/status",
        json={"status": "OPEN"},
        headers=get_token_headers(s["admin"]),
    )
    assert res_status.status_code == 409

    # Attempt delete
    res_del = client.delete(
        f"/api/v1/exposures/{exp_id}",
        headers=get_token_headers(s["admin"]),
    )
    assert res_del.status_code == 409


def test_delete_exposure_non_resolved(client: TestClient, exposure_api_setup):
    """Non-resolved exposure can be deleted (204 No Content)."""
    s = exposure_api_setup
    create_res = client.post(
        "/api/v1/exposures",
        json={"cve_id": "CVE-2026-9701", "title": "Deletable Exposure", "cvss_score": 4.0},
        headers=get_token_headers(s["admin"]),
    )
    exp_id = create_res.json()["id"]

    res_del = client.delete(
        f"/api/v1/exposures/{exp_id}",
        headers=get_token_headers(s["admin"]),
    )
    assert res_del.status_code == 204

    # Verify 404 on subsequent get
    res_get = client.get(
        f"/api/v1/exposures/{exp_id}",
        headers=get_token_headers(s["admin"]),
    )
    assert res_get.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# 2. ASSET & BLAST RADIUS LINKAGE TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_link_and_unlink_asset(client: TestClient, exposure_api_setup):
    """Link asset to exposure, verify blast radius increase, and unlink."""
    s = exposure_api_setup
    create_res = client.post(
        "/api/v1/exposures",
        json={"cve_id": "CVE-2026-9801", "title": "Blast Radius Link Test", "cvss_score": 8.0, "epss_score": 0.5},
        headers=get_token_headers(s["admin"]),
    )
    exp_id = create_res.json()["id"]
    initial_index = create_res.json()["exposure_index"]

    # Link Tier 1 process
    link_res = client.post(
        f"/api/v1/exposures/{exp_id}/assets",
        json={
            "asset_identifier": "srv-prod-settlement",
            "asset_type": "SERVER",
            "environment": "PRODUCTION",
            "process_id": s["proc_apex"].id,
        },
        headers=get_token_headers(s["sec_analyst"]),
    )
    assert link_res.status_code == 201
    link_id = link_res.json()["id"]

    # Verify exposure index increased with 1.25x multiplier
    get_exp = client.get(f"/api/v1/exposures/{exp_id}", headers=get_token_headers(s["viewer"]))
    assert get_exp.json()["exposure_index"] > initial_index

    # Unlink asset
    del_link = client.delete(f"/api/v1/exposures/assets/{link_id}", headers=get_token_headers(s["sec_analyst"]))
    assert del_link.status_code == 204

    # Verify exposure index reduced back
    get_exp_after = client.get(f"/api/v1/exposures/{exp_id}", headers=get_token_headers(s["viewer"]))
    assert get_exp_after.json()["exposure_index"] == initial_index


# ─────────────────────────────────────────────────────────────────────────────
# 3. FOUR-EYES EXCEPTION & DEFERRAL TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_four_eyes_exception_workflow(client: TestClient, exposure_api_setup):
    """Analyst requests exception, Manager approves (requester != approver)."""
    s = exposure_api_setup
    create_res = client.post(
        "/api/v1/exposures",
        json={"cve_id": "CVE-2026-9901", "title": "Exception Flow Test", "cvss_score": 8.0, "severity": "HIGH"},
        headers=get_token_headers(s["admin"]),
    )
    exp_id = create_res.json()["id"]
    current_sla = datetime.fromisoformat(create_res.json()["remediation_sla_due"].replace("Z", "+00:00"))
    requested_sla = (current_sla + timedelta(days=30)).isoformat()

    # 1. Analyst requests SLA extension
    exc_res = client.post(
        f"/api/v1/exposures/{exp_id}/exceptions",
        json={
            "requested_sla_due": requested_sla,
            "justification": "Vendor patch delayed to next sprint.",
            "compensating_controls": "WAF rate limit configured.",
        },
        headers=get_token_headers(s["sec_analyst"]),
    )
    assert exc_res.status_code == 201
    exc_id = exc_res.json()["id"]

    # 2. Requester attempting self-approval returns 403 Forbidden
    self_approve_res = client.post(
        f"/api/v1/exposures/exceptions/{exc_id}/review",
        json={"decision": "APPROVED"},
        headers=get_token_headers(s["sec_analyst"]),
    )
    assert self_approve_res.status_code == 403

    # 3. Manager approves
    manager_approve_res = client.post(
        f"/api/v1/exposures/exceptions/{exc_id}/review",
        json={"decision": "APPROVED", "review_notes": "Compensating control verified."},
        headers=get_token_headers(s["manager"]),
    )
    assert manager_approve_res.status_code == 200
    assert manager_approve_res.json()["status"] == "APPROVED"

    # Verify exposure SLA was extended and status updated
    exp_after = client.get(f"/api/v1/exposures/{exp_id}", headers=get_token_headers(s["viewer"])).json()
    assert exp_after["status"] == "EXCEPTION_APPROVED"


def test_four_eyes_exception_rejection(client: TestClient, exposure_api_setup):
    """Manager rejects exception request."""
    s = exposure_api_setup
    create_res = client.post(
        "/api/v1/exposures",
        json={"cve_id": "CVE-2026-9902", "title": "Exception Rejection Test", "cvss_score": 7.0},
        headers=get_token_headers(s["admin"]),
    )
    exp_id = create_res.json()["id"]
    current_sla = datetime.fromisoformat(create_res.json()["remediation_sla_due"].replace("Z", "+00:00"))
    requested_sla = (current_sla + timedelta(days=15)).isoformat()

    exc_res = client.post(
        f"/api/v1/exposures/{exp_id}/exceptions",
        json={"requested_sla_due": requested_sla, "justification": "Delay in testing."},
        headers=get_token_headers(s["sec_analyst"]),
    )
    exc_id = exc_res.json()["id"]

    # Manager rejects
    reject_res = client.post(
        f"/api/v1/exposures/exceptions/{exc_id}/review",
        json={"decision": "REJECTED", "review_notes": "SLA extension not justified."},
        headers=get_token_headers(s["manager"]),
    )
    assert reject_res.status_code == 200
    assert reject_res.json()["status"] == "REJECTED"


# ─────────────────────────────────────────────────────────────────────────────
# 4. CROSS-MODULE REMEDIATION & PREVIEWS
# ─────────────────────────────────────────────────────────────────────────────

def test_spawn_remediation_plan_api(client: TestClient, exposure_api_setup):
    """Instantiate Phase 11 RemediationPlan via Exposure endpoint."""
    s = exposure_api_setup
    create_res = client.post(
        "/api/v1/exposures",
        json={"cve_id": "CVE-2026-9903", "title": "Remediation Spawn Test", "cvss_score": 9.0, "severity": "CRITICAL"},
        headers=get_token_headers(s["admin"]),
    )
    exp_id = create_res.json()["id"]

    rem_res = client.post(
        f"/api/v1/exposures/{exp_id}/remediate",
        headers=get_token_headers(s["admin"]),
    )
    assert rem_res.status_code == 201
    assert "CVE-2026-9903" in rem_res.json()["plan_code"]


def test_executive_posture_summary_api(client: TestClient, exposure_api_setup):
    """GET /exposures/summary/posture returns aggregated posture."""
    s = exposure_api_setup
    res = client.get("/api/v1/exposures/summary/posture", headers=get_token_headers(s["viewer"]))
    assert res.status_code == 200
    data = res.json()
    assert "total_exposures" in data
    assert "average_exposure_index" in data


def test_calculate_index_preview_api(client: TestClient, exposure_api_setup):
    """POST /exposures/calculate-index returns preview calculation."""
    s = exposure_api_setup
    res = client.post(
        "/api/v1/exposures/calculate-index",
        json={"cvss_score": 8.0, "epss_score": 0.5, "cisa_kev": True, "highest_process_tier": "TIER_1"},
        headers=get_token_headers(s["viewer"]),
    )
    assert res.status_code == 200
    data = res.json()
    assert data["blast_radius_multiplier"] == 1.25
    assert data["exposure_index"] > 0

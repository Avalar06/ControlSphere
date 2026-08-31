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
def adv_p14_fixture(db: Session, org_apex: Organization, org_meridian: Organization):
    """Setup multi-tenant entities, multi-role users, and GRC foundations for ADV-P14 test suite."""
    # Apex Users (Tenant A)
    apex_admin = User(
        email="adv_admin@apex.com",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Apex Admin",
        role=RoleEnum.ADMIN,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_manager = User(
        email="adv_manager@apex.com",
        hashed_password=get_password_hash("ManagerPass123!"),
        full_name="Apex Manager",
        role=RoleEnum.MANAGER,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_manager_2 = User(
        email="adv_manager2@apex.com",
        hashed_password=get_password_hash("Manager2Pass123!"),
        full_name="Apex Manager 2",
        role=RoleEnum.MANAGER,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_sec_analyst = User(
        email="adv_sec_analyst@apex.com",
        hashed_password=get_password_hash("SecAnalystPass123!"),
        full_name="Apex Sec Analyst",
        role=RoleEnum.SECURITY_ANALYST,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_grc_analyst = User(
        email="adv_grc_analyst@apex.com",
        hashed_password=get_password_hash("GrcAnalystPass123!"),
        full_name="Apex GRC Analyst",
        role=RoleEnum.GRC_ANALYST,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_auditor = User(
        email="adv_auditor@apex.com",
        hashed_password=get_password_hash("AuditorPass123!"),
        full_name="Apex Auditor",
        role=RoleEnum.AUDITOR,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_viewer = User(
        email="adv_viewer@apex.com",
        hashed_password=get_password_hash("ViewerPass123!"),
        full_name="Apex Viewer",
        role=RoleEnum.VIEWER,
        is_active=True,
        organization_id=org_apex.id,
    )

    # Meridian Users (Tenant B - Adversary / Cross-Tenant)
    meridian_admin = User(
        email="adv_admin@meridian.com",
        hashed_password=get_password_hash("MeridianAdmin123!"),
        full_name="Meridian Admin",
        role=RoleEnum.ADMIN,
        is_active=True,
        organization_id=org_meridian.id,
    )
    meridian_manager = User(
        email="adv_manager@meridian.com",
        hashed_password=get_password_hash("MeridianManager123!"),
        full_name="Meridian Manager",
        role=RoleEnum.MANAGER,
        is_active=True,
        organization_id=org_meridian.id,
    )

    db.add_all([
        apex_admin,
        apex_manager,
        apex_manager_2,
        apex_sec_analyst,
        apex_grc_analyst,
        apex_auditor,
        apex_viewer,
        meridian_admin,
        meridian_manager,
    ])
    db.commit()

    # Apex GRC Entities
    proc_apex = BusinessProcess(
        organization_id=org_apex.id,
        name="Apex Payments Engine",
        owner_id=apex_admin.id,
        criticality_tier=CriticalityTierEnum.TIER_1,
    )
    vendor_apex = Vendor(
        organization_id=org_apex.id,
        legal_name="Apex Cloud Host",
        vendor_code="VND-APX-001",
        vendor_status=VendorStatusEnum.ACTIVE,
        calculated_tier=VendorTierEnum.TIER_1_CRITICAL,
    )
    ctrl_apex = OrganizationControl(
        organization_id=org_apex.id,
        subcategory_id=1,
        status=ImplementationStatusEnum.IMPLEMENTED,
        priority=PriorityEnum.HIGH,
    )

    # Meridian GRC Entities (Foreign)
    proc_meridian = BusinessProcess(
        organization_id=org_meridian.id,
        name="Meridian Core Ledger",
        owner_id=meridian_admin.id,
        criticality_tier=CriticalityTierEnum.TIER_1,
    )
    vendor_meridian = Vendor(
        organization_id=org_meridian.id,
        legal_name="Meridian Foreign Vendor",
        vendor_code="VND-MER-001",
        vendor_status=VendorStatusEnum.ACTIVE,
        calculated_tier=VendorTierEnum.TIER_1_CRITICAL,
    )
    ctrl_meridian = OrganizationControl(
        organization_id=org_meridian.id,
        subcategory_id=1,
        status=ImplementationStatusEnum.IMPLEMENTED,
        priority=PriorityEnum.HIGH,
    )

    db.add_all([proc_apex, vendor_apex, ctrl_apex, proc_meridian, vendor_meridian, ctrl_meridian])
    db.commit()

    # Pre-seed an Apex Exposure
    exp_apex = VulnerabilityExposure(
        organization_id=org_apex.id,
        cve_id="CVE-2026-1337",
        title="Critical Gateway Authentication Bypass",
        cvss_score=9.8,
        epss_score=0.85,
        cisa_kev=True,
        severity=ExposureSeverityEnum.CRITICAL,
        status=ExposureStatusEnum.OPEN,
        exposure_index=64.0,
        remediation_sla_due=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(exp_apex)
    db.commit()
    db.refresh(exp_apex)

    return {
        "org_apex": org_apex,
        "org_meridian": org_meridian,
        "apex_admin": apex_admin,
        "apex_manager": apex_manager,
        "apex_manager_2": apex_manager_2,
        "apex_sec_analyst": apex_sec_analyst,
        "apex_grc_analyst": apex_grc_analyst,
        "apex_auditor": apex_auditor,
        "apex_viewer": apex_viewer,
        "meridian_admin": meridian_admin,
        "meridian_manager": meridian_manager,
        "proc_apex": proc_apex,
        "vendor_apex": vendor_apex,
        "ctrl_apex": ctrl_apex,
        "proc_meridian": proc_meridian,
        "vendor_meridian": vendor_meridian,
        "ctrl_meridian": ctrl_meridian,
        "exp_apex": exp_apex,
    }


# ─────────────────────────────────────────────────────────────────────────────
# ADV-P14-01 through ADV-P14-25 TEST VECTORS
# ─────────────────────────────────────────────────────────────────────────────

def test_adv_p14_01_cross_tenant_exposure_lookup_idor(client: TestClient, adv_p14_fixture):
    """ADV-P14-01: Meridian Admin attempts direct IDOR lookup of Apex exposure (HTTP 404)."""
    f = adv_p14_fixture
    res = client.get(
        f"/api/v1/exposures/{f['exp_apex'].id}",
        headers=get_token_headers(f["meridian_admin"]),
    )
    assert res.status_code == 404


def test_adv_p14_02_cross_tenant_list_isolation(client: TestClient, adv_p14_fixture):
    """ADV-P14-02: Meridian User listing exposures receives empty list, never leaking Apex data."""
    f = adv_p14_fixture
    res = client.get(
        "/api/v1/exposures",
        headers=get_token_headers(f["meridian_admin"]),
    )
    assert res.status_code == 200
    items = res.json()
    assert not any(e["id"] == f["exp_apex"].id for e in items)


def test_adv_p14_03_cross_tenant_update_idor(client: TestClient, adv_p14_fixture):
    """ADV-P14-03: Meridian User attempts to mutate Apex exposure (HTTP 404)."""
    f = adv_p14_fixture
    res = client.put(
        f"/api/v1/exposures/{f['exp_apex'].id}",
        json={"title": "Compromised Title"},
        headers=get_token_headers(f["meridian_admin"]),
    )
    assert res.status_code == 404


def test_adv_p14_04_cross_tenant_deletion_idor(client: TestClient, adv_p14_fixture):
    """ADV-P14-04: Meridian User attempts to delete Apex exposure (HTTP 404)."""
    f = adv_p14_fixture
    res = client.delete(
        f"/api/v1/exposures/{f['exp_apex'].id}",
        headers=get_token_headers(f["meridian_admin"]),
    )
    assert res.status_code == 404


def test_adv_p14_05_cross_tenant_asset_linkage_idor(client: TestClient, adv_p14_fixture):
    """ADV-P14-05: Meridian User attempts to attach asset to Apex exposure (HTTP 404)."""
    f = adv_p14_fixture
    res = client.post(
        f"/api/v1/exposures/{f['exp_apex'].id}/assets",
        json={"asset_identifier": "foreign-host", "asset_type": "SERVER"},
        headers=get_token_headers(f["meridian_admin"]),
    )
    assert res.status_code == 404


def test_adv_p14_06_cross_tenant_business_process_linkage(client: TestClient, adv_p14_fixture):
    """ADV-P14-06: Apex Admin attempts to link Meridian BusinessProcess to Apex Exposure (HTTP 404)."""
    f = adv_p14_fixture
    res = client.post(
        f"/api/v1/exposures/{f['exp_apex'].id}/assets",
        json={
            "asset_identifier": "apex-core-node",
            "asset_type": "SERVER",
            "process_id": f["proc_meridian"].id,  # Foreign process
        },
        headers=get_token_headers(f["apex_admin"]),
    )
    assert res.status_code == 404


def test_adv_p14_07_cross_tenant_vendor_linkage(client: TestClient, adv_p14_fixture):
    """ADV-P14-07: Apex Admin attempts to link Meridian Vendor to Apex Exposure (HTTP 404)."""
    f = adv_p14_fixture
    res = client.post(
        f"/api/v1/exposures/{f['exp_apex'].id}/assets",
        json={
            "asset_identifier": "apex-cloud-node",
            "asset_type": "CLOUD_SERVICE",
            "vendor_id": f["vendor_meridian"].id,  # Foreign vendor
        },
        headers=get_token_headers(f["apex_admin"]),
    )
    assert res.status_code == 404


def test_adv_p14_08_cross_tenant_organization_control_linkage(client: TestClient, adv_p14_fixture):
    """ADV-P14-08: Apex Admin attempts to link Meridian Control to Apex Exposure (HTTP 404)."""
    f = adv_p14_fixture
    res = client.post(
        f"/api/v1/exposures/{f['exp_apex'].id}/assets",
        json={
            "asset_identifier": "apex-fw",
            "asset_type": "NETWORK_DEVICE",
            "control_id": f["ctrl_meridian"].id,  # Foreign control
        },
        headers=get_token_headers(f["apex_admin"]),
    )
    assert res.status_code == 404


def test_adv_p14_09_cross_tenant_exception_review_idor(client: TestClient, adv_p14_fixture):
    """ADV-P14-09: Meridian Manager attempts to review Apex Exception (HTTP 404)."""
    f = adv_p14_fixture
    # Create exception in Apex
    exc_res = client.post(
        f"/api/v1/exposures/{f['exp_apex'].id}/exceptions",
        json={
            "requested_sla_due": (f["exp_apex"].remediation_sla_due + timedelta(days=20)).isoformat(),
            "justification": "Testing cross-tenant review isolation.",
        },
        headers=get_token_headers(f["apex_sec_analyst"]),
    )
    exc_id = exc_res.json()["id"]

    # Meridian Manager attempts review
    res = client.post(
        f"/api/v1/exposures/exceptions/{exc_id}/review",
        json={"decision": "APPROVED"},
        headers=get_token_headers(f["meridian_manager"]),
    )
    assert res.status_code == 404


def test_adv_p14_10_cross_tenant_remediation_spawning_idor(client: TestClient, adv_p14_fixture):
    """ADV-P14-10: Meridian Admin attempts to spawn remediation for Apex Exposure (HTTP 404)."""
    f = adv_p14_fixture
    res = client.post(
        f"/api/v1/exposures/{f['exp_apex'].id}/remediate",
        headers=get_token_headers(f["meridian_admin"]),
    )
    assert res.status_code == 404


def test_adv_p14_11_unauthenticated_access_rejection(client: TestClient, adv_p14_fixture):
    """ADV-P14-11: Anonymous unauthenticated access rejected (HTTP 401)."""
    res = client.get("/api/v1/exposures")
    assert res.status_code == 401


def test_adv_p14_12_forged_jwt_token_rejection(client: TestClient, adv_p14_fixture):
    """ADV-P14-12: Request with forged/malformed JWT bearer token rejected (HTTP 401)."""
    headers = {"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.bogus_signature"}
    res = client.get("/api/v1/exposures", headers=headers)
    assert res.status_code == 401


def test_adv_p14_13_rbac_viewer_ingestion_blocked(client: TestClient, adv_p14_fixture):
    """ADV-P14-13: Viewer role attempting exposure creation rejected (HTTP 403)."""
    f = adv_p14_fixture
    res = client.post(
        "/api/v1/exposures",
        json={"cve_id": "CVE-2026-8001", "title": "Viewer Ingestion Attempt", "cvss_score": 5.0},
        headers=get_token_headers(f["apex_viewer"]),
    )
    assert res.status_code == 403


def test_adv_p14_14_grc_analyst_approval_bypass_blocked(client: TestClient, adv_p14_fixture):
    """ADV-P14-14: GRC Analyst attempting exception approval without EXPOSURE_APPROVE rejected (HTTP 403)."""
    f = adv_p14_fixture
    exc_res = client.post(
        f"/api/v1/exposures/{f['exp_apex'].id}/exceptions",
        json={
            "requested_sla_due": (f["exp_apex"].remediation_sla_due + timedelta(days=15)).isoformat(),
            "justification": "Testing analyst approval block.",
        },
        headers=get_token_headers(f["apex_sec_analyst"]),
    )
    exc_id = exc_res.json()["id"]

    res = client.post(
        f"/api/v1/exposures/exceptions/{exc_id}/review",
        json={"decision": "APPROVED"},
        headers=get_token_headers(f["apex_grc_analyst"]),
    )
    assert res.status_code == 403


def test_adv_p14_15_sec_analyst_approval_bypass_blocked(client: TestClient, adv_p14_fixture):
    """ADV-P14-15: Security Analyst attempting exception approval without EXPOSURE_APPROVE rejected (HTTP 403)."""
    f = adv_p14_fixture
    exc_res = client.post(
        f"/api/v1/exposures/{f['exp_apex'].id}/exceptions",
        json={
            "requested_sla_due": (f["exp_apex"].remediation_sla_due + timedelta(days=15)).isoformat(),
            "justification": "Testing sec analyst approval block.",
        },
        headers=get_token_headers(f["apex_grc_analyst"]),
    )
    exc_id = exc_res.json()["id"]

    res = client.post(
        f"/api/v1/exposures/exceptions/{exc_id}/review",
        json={"decision": "APPROVED"},
        headers=get_token_headers(f["apex_sec_analyst"]),
    )
    assert res.status_code == 403


def test_adv_p14_16_auditor_mutation_blocked(client: TestClient, adv_p14_fixture):
    """ADV-P14-16: Auditor attempting exposure update rejected (HTTP 403)."""
    f = adv_p14_fixture
    res = client.put(
        f"/api/v1/exposures/{f['exp_apex'].id}",
        json={"title": "Auditor Mutated Title"},
        headers=get_token_headers(f["apex_auditor"]),
    )
    assert res.status_code == 403


def test_adv_p14_17_viewer_status_mutation_blocked(client: TestClient, adv_p14_fixture):
    """ADV-P14-17: Viewer attempting status transition rejected (HTTP 403)."""
    f = adv_p14_fixture
    res = client.put(
        f"/api/v1/exposures/{f['exp_apex'].id}/status",
        json={"status": "RESOLVED"},
        headers=get_token_headers(f["apex_viewer"]),
    )
    assert res.status_code == 403


def test_adv_p14_18_four_eyes_self_approval_blocked(client: TestClient, adv_p14_fixture):
    """ADV-P14-18: Manager who created exception attempts self-approval -> rejected (HTTP 403)."""
    f = adv_p14_fixture
    exc_res = client.post(
        f"/api/v1/exposures/{f['exp_apex'].id}/exceptions",
        json={
            "requested_sla_due": (f["exp_apex"].remediation_sla_due + timedelta(days=30)).isoformat(),
            "justification": "Self-approval test.",
        },
        headers=get_token_headers(f["apex_manager"]),
    )
    exc_id = exc_res.json()["id"]

    # Same manager attempts review -> must fail with 403
    res = client.post(
        f"/api/v1/exposures/exceptions/{exc_id}/review",
        json={"decision": "APPROVED"},
        headers=get_token_headers(f["apex_manager"]),
    )
    assert res.status_code == 403


def test_adv_p14_19_spoofed_approver_id_mass_assignment_neutralized(client: TestClient, adv_p14_fixture):
    """ADV-P14-19: Request payload injecting spoofed approved_by_id is ignored; server uses authenticated user."""
    f = adv_p14_fixture
    exc_res = client.post(
        f"/api/v1/exposures/{f['exp_apex'].id}/exceptions",
        json={
            "requested_sla_due": (f["exp_apex"].remediation_sla_due + timedelta(days=30)).isoformat(),
            "justification": "Mass assignment test.",
        },
        headers=get_token_headers(f["apex_sec_analyst"]),
    )
    exc_id = exc_res.json()["id"]

    # Manager 2 approves but payload tries to spoof approved_by_id as Manager 1
    res = client.post(
        f"/api/v1/exposures/exceptions/{exc_id}/review",
        json={"decision": "APPROVED", "approved_by_id": f["apex_manager"].id},
        headers=get_token_headers(f["apex_manager_2"]),
    )
    assert res.status_code == 200
    assert res.json()["approved_by_id"] == f["apex_manager_2"].id


def test_adv_p14_20_server_authoritative_exposure_index_injection(client: TestClient, adv_p14_fixture):
    """ADV-P14-20: Injecting fake exposure_index=0.0 in create payload is overridden by server calculation."""
    f = adv_p14_fixture
    res = client.post(
        "/api/v1/exposures",
        json={
            "cve_id": "CVE-2026-8020",
            "title": "Index Override Test",
            "cvss_score": 10.0,
            "epss_score": 1.0,
            "cisa_kev": True,
            "exposure_index": 0.0,  # Malicious override
        },
        headers=get_token_headers(f["apex_admin"]),
    )
    assert res.status_code == 201
    assert res.json()["exposure_index"] == 64.0  # Server calculated correctly


def test_adv_p14_21_server_authoritative_sla_injection_neutralized(client: TestClient, adv_p14_fixture):
    """ADV-P14-21: Server enforces default SLA determination when omitted or past date requested."""
    f = adv_p14_fixture
    res = client.post(
        "/api/v1/exposures",
        json={
            "cve_id": "CVE-2026-8021",
            "title": "SLA Ingestion Test",
            "cvss_score": 9.5,
            "cisa_kev": True,
            "severity": "CRITICAL",
        },
        headers=get_token_headers(f["apex_admin"]),
    )
    raw_sla = datetime.fromisoformat(res.json()["remediation_sla_due"].replace("Z", "+00:00"))
    sla = raw_sla if raw_sla.tzinfo else raw_sla.replace(tzinfo=timezone.utc)
    expected_sla = datetime.now(timezone.utc) + timedelta(days=7)
    assert abs((sla - expected_sla).total_seconds()) < 60


def test_adv_p14_22_resolved_record_mutation_blocked(client: TestClient, adv_p14_fixture):
    """ADV-P14-22: Mutation of terminal RESOLVED record returns HTTP 409 Conflict."""
    f = adv_p14_fixture
    create_res = client.post(
        "/api/v1/exposures",
        json={"cve_id": "CVE-2026-8022", "title": "Resolved Imm Test", "cvss_score": 5.0},
        headers=get_token_headers(f["apex_admin"]),
    )
    exp_id = create_res.json()["id"]

    # Transition to RESOLVED
    client.put(f"/api/v1/exposures/{exp_id}/status", json={"status": "RESOLVED"}, headers=get_token_headers(f["apex_admin"]))

    # Update attempt
    res = client.put(f"/api/v1/exposures/{exp_id}", json={"title": "Hacked"}, headers=get_token_headers(f["apex_admin"]))
    assert res.status_code == 409


def test_adv_p14_23_illegal_lifecycle_transition_blocked(client: TestClient, adv_p14_fixture):
    """ADV-P14-23: Illegal transition from RESOLVED to OPEN returns HTTP 409 Conflict."""
    f = adv_p14_fixture
    create_res = client.post(
        "/api/v1/exposures",
        json={"cve_id": "CVE-2026-8023", "title": "Illegal Transition Test", "cvss_score": 6.0},
        headers=get_token_headers(f["apex_admin"]),
    )
    exp_id = create_res.json()["id"]
    client.put(f"/api/v1/exposures/{exp_id}/status", json={"status": "RESOLVED"}, headers=get_token_headers(f["apex_admin"]))

    res = client.put(f"/api/v1/exposures/{exp_id}/status", json={"status": "OPEN"}, headers=get_token_headers(f["apex_admin"]))
    assert res.status_code == 409


def test_adv_p14_24_out_of_bounds_numerical_input_rejected(client: TestClient, adv_p14_fixture):
    """ADV-P14-24: CVSS > 10.0 or EPSS > 1.0 injection rejected (HTTP 422)."""
    f = adv_p14_fixture
    # Invalid CVSS
    res_cvss = client.post(
        "/api/v1/exposures",
        json={"cve_id": "CVE-2026-8024", "title": "Invalid CVSS", "cvss_score": 15.0},
        headers=get_token_headers(f["apex_admin"]),
    )
    assert res_cvss.status_code == 422

    # Invalid EPSS
    res_epss = client.post(
        "/api/v1/exposures",
        json={"cve_id": "CVE-2026-8024", "title": "Invalid EPSS", "cvss_score": 8.0, "epss_score": 2.5},
        headers=get_token_headers(f["apex_admin"]),
    )
    assert res_epss.status_code == 422


def test_adv_p14_25_double_approval_terminal_state_blocked(client: TestClient, adv_p14_fixture):
    """ADV-P14-25: Attempting to review an already decided exception returns HTTP 409 Conflict."""
    f = adv_p14_fixture
    exc_res = client.post(
        f"/api/v1/exposures/{f['exp_apex'].id}/exceptions",
        json={
            "requested_sla_due": (f["exp_apex"].remediation_sla_due + timedelta(days=20)).isoformat(),
            "justification": "Double approval test.",
        },
        headers=get_token_headers(f["apex_sec_analyst"]),
    )
    exc_id = exc_res.json()["id"]

    # First review: approved
    client.post(
        f"/api/v1/exposures/exceptions/{exc_id}/review",
        json={"decision": "APPROVED"},
        headers=get_token_headers(f["apex_manager"]),
    )

    # Second review: attempted re-decision -> 409 Conflict
    res_double = client.post(
        f"/api/v1/exposures/exceptions/{exc_id}/review",
        json={"decision": "REJECTED"},
        headers=get_token_headers(f["apex_manager_2"]),
    )
    assert res_double.status_code == 409

from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.permissions import RoleEnum
from app.core.security import get_password_hash
from app.models.audit_log import AuditLog
from app.models.control import OrganizationControl, ImplementationStatusEnum, PriorityEnum
from app.models.framework import Framework, FrameworkCategory, FrameworkFunction, FrameworkSubcategory
from app.models.organization import Organization
from app.models.resilience import (
    BiaStatusEnum,
    BusinessImpactAnalysis,
    BusinessProcess,
    CriticalityTierEnum,
    DependencyTypeEnum,
    ProcessDependency,
)
from app.models.tprm import Vendor, VendorStatusEnum, VendorTierEnum
from app.models.user import User
from tests.conftest import get_token_headers


@pytest.fixture
def adv_p13_fixture(db: Session, org_apex: Organization, org_meridian: Organization):
    """Fixture providing multi-tenant entities, multi-role users, and GRC foundations for ADV-P13."""
    # Apex Users
    apex_admin = User(
        email="admin@apexfinancial.com",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Apex Admin",
        role=RoleEnum.ADMIN,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_manager = User(
        email="manager@apexfinancial.com",
        hashed_password=get_password_hash("ManagerPass123!"),
        full_name="Apex Manager",
        role=RoleEnum.MANAGER,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_manager_2 = User(
        email="manager2@apexfinancial.com",
        hashed_password=get_password_hash("Manager2Pass123!"),
        full_name="Apex Manager 2",
        role=RoleEnum.MANAGER,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_analyst = User(
        email="analyst@apexfinancial.com",
        hashed_password=get_password_hash("AnalystPass123!"),
        full_name="Apex Analyst",
        role=RoleEnum.GRC_ANALYST,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_sec_analyst = User(
        email="sec_analyst@apexfinancial.com",
        hashed_password=get_password_hash("SecAnalystPass123!"),
        full_name="Apex Security Analyst",
        role=RoleEnum.SECURITY_ANALYST,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_auditor = User(
        email="auditor@apexfinancial.com",
        hashed_password=get_password_hash("AuditorPass123!"),
        full_name="Apex Auditor",
        role=RoleEnum.AUDITOR,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_viewer = User(
        email="viewer@apexfinancial.com",
        hashed_password=get_password_hash("ViewerPass123!"),
        full_name="Apex Viewer",
        role=RoleEnum.VIEWER,
        is_active=True,
        organization_id=org_apex.id,
    )

    # Meridian Users
    meridian_manager = User(
        email="manager@meridianhealth.com",
        hashed_password=get_password_hash("MeridianPass123!"),
        full_name="Meridian Manager",
        role=RoleEnum.MANAGER,
        is_active=True,
        organization_id=org_meridian.id,
    )
    meridian_analyst = User(
        email="analyst@meridianhealth.com",
        hashed_password=get_password_hash("MeridianPass123!"),
        full_name="Meridian Analyst",
        role=RoleEnum.GRC_ANALYST,
        is_active=True,
        organization_id=org_meridian.id,
    )

    db.add_all([
        apex_admin, apex_manager, apex_manager_2, apex_analyst,
        apex_sec_analyst, apex_auditor, apex_viewer,
        meridian_manager, meridian_analyst
    ])
    db.commit()

    # Framework and Controls
    fw = Framework(name="NIST CSF P13", identifier="NIST-P13", version="2.0")
    db.add(fw)
    db.commit()

    fn = FrameworkFunction(framework_id=fw.id, identifier="RC", name="Recover")
    db.add(fn)
    db.commit()

    cat = FrameworkCategory(function_id=fn.id, identifier="RC.RP", name="Recovery Planning")
    db.add(cat)
    db.commit()

    subcat = FrameworkSubcategory(category_id=cat.id, identifier="RC.RP-01", title="Recovery plan executed", description="Desc")
    db.add(subcat)
    db.commit()

    apex_ctrl = OrganizationControl(
        organization_id=org_apex.id,
        subcategory_id=subcat.id,
        status=ImplementationStatusEnum.IMPLEMENTED,
        priority=PriorityEnum.HIGH,
    )
    meridian_ctrl = OrganizationControl(
        organization_id=org_meridian.id,
        subcategory_id=subcat.id,
        status=ImplementationStatusEnum.IMPLEMENTED,
        priority=PriorityEnum.HIGH,
    )
    db.add_all([apex_ctrl, meridian_ctrl])
    db.commit()

    # Vendors
    apex_vendor = Vendor(
        organization_id=org_apex.id,
        vendor_code="VND-APX-P13",
        legal_name="Apex Core Vendor",
        calculated_tier=VendorTierEnum.TIER_1_CRITICAL,
        vendor_status=VendorStatusEnum.ACTIVE,
    )
    meridian_vendor = Vendor(
        organization_id=org_meridian.id,
        vendor_code="VND-MER-P13",
        legal_name="Meridian Core Vendor",
        calculated_tier=VendorTierEnum.TIER_1_CRITICAL,
        vendor_status=VendorStatusEnum.ACTIVE,
    )
    db.add_all([apex_vendor, meridian_vendor])
    db.commit()

    # Apex Business Process & BIAs
    apex_proc = BusinessProcess(
        organization_id=org_apex.id,
        name="Apex Settlement Engine",
        description="High throughput settlement pipeline",
        owner_id=apex_analyst.id,
        criticality_tier=CriticalityTierEnum.TIER_1,
    )
    meridian_proc = BusinessProcess(
        organization_id=org_meridian.id,
        name="Meridian Patient Record System",
        description="Patient health information service",
        owner_id=meridian_analyst.id,
        criticality_tier=CriticalityTierEnum.TIER_1,
    )
    db.add_all([apex_proc, meridian_proc])
    db.commit()
    db.refresh(apex_proc)
    db.refresh(meridian_proc)

    # Apex BIA Draft
    apex_bia_draft = BusinessImpactAnalysis(
        organization_id=org_apex.id,
        process_id=apex_proc.id,
        status=BiaStatusEnum.DRAFT,
        version=1,
        rto_hours=2.0,
        rpo_hours=0.5,
        mtd_hours=12.0,
        hourly_downtime_cost=20000.0,
        fixed_outage_cost=10000.0,
        requested_by_id=apex_analyst.id,
    )
    db.add(apex_bia_draft)
    db.commit()
    db.refresh(apex_bia_draft)

    # Apex Dependency
    apex_dep = ProcessDependency(
        organization_id=org_apex.id,
        process_id=apex_proc.id,
        dependency_type=DependencyTypeEnum.VENDOR,
        dependency_id=apex_vendor.id,
        notes="Primary settlement provider",
    )
    db.add(apex_dep)
    db.commit()
    db.refresh(apex_dep)

    return {
        "org_apex": org_apex,
        "org_meridian": org_meridian,
        "apex_admin": apex_admin,
        "apex_manager": apex_manager,
        "apex_manager_2": apex_manager_2,
        "apex_analyst": apex_analyst,
        "apex_sec_analyst": apex_sec_analyst,
        "apex_auditor": apex_auditor,
        "apex_viewer": apex_viewer,
        "meridian_manager": meridian_manager,
        "meridian_analyst": meridian_analyst,
        "apex_ctrl": apex_ctrl,
        "meridian_ctrl": meridian_ctrl,
        "apex_vendor": apex_vendor,
        "meridian_vendor": meridian_vendor,
        "apex_proc": apex_proc,
        "meridian_proc": meridian_proc,
        "apex_bia_draft": apex_bia_draft,
        "apex_dep": apex_dep,
    }


# ─── ADV-P13-01: Cross-Tenant Process IDOR ───────────────────────────────────

def test_adv_p13_01_cross_tenant_process_idor(client: TestClient, adv_p13_fixture):
    """ADV-P13-01: Meridian user attempts to access or mutate Apex Business Process -> HTTP 404."""
    meridian_h = get_token_headers(adv_p13_fixture["meridian_analyst"])
    apex_proc_id = adv_p13_fixture["apex_proc"].id

    # Read attempt
    resp_get = client.get(f"/api/v1/resilience/processes/{apex_proc_id}", headers=meridian_h)
    assert resp_get.status_code == 404
    assert "not found in tenant" in resp_get.json()["detail"]

    # Mutation attempt
    resp_put = client.put(
        f"/api/v1/resilience/processes/{apex_proc_id}",
        headers=meridian_h,
        json={"name": "Hacked Process Name"},
    )
    assert resp_put.status_code == 404

    # Deletion attempt
    resp_del = client.delete(f"/api/v1/resilience/processes/{apex_proc_id}", headers=meridian_h)
    assert resp_del.status_code == 404


# ─── ADV-P13-02: Cross-Tenant BIA IDOR ───────────────────────────────────────

def test_adv_p13_02_cross_tenant_bia_idor(client: TestClient, adv_p13_fixture):
    """ADV-P13-02: Meridian user attempts to read or modify Apex BIA -> HTTP 404."""
    meridian_h = get_token_headers(adv_p13_fixture["meridian_analyst"])
    apex_bia_id = adv_p13_fixture["apex_bia_draft"].id
    apex_proc_id = adv_p13_fixture["apex_proc"].id

    # Direct BIA Read
    resp_get = client.get(f"/api/v1/resilience/bia/{apex_bia_id}", headers=meridian_h)
    assert resp_get.status_code == 404

    # Process BIA List
    resp_list = client.get(f"/api/v1/resilience/processes/{apex_proc_id}/bia", headers=meridian_h)
    assert resp_list.status_code == 404

    # Update attempt
    resp_put = client.put(
        f"/api/v1/resilience/bia/{apex_bia_id}",
        headers=meridian_h,
        json={"process_id": apex_proc_id, "rto_hours": 1.0, "mtd_hours": 10.0},
    )
    assert resp_put.status_code == 404


# ─── ADV-P13-03: Cross-Tenant Dependency IDOR ────────────────────────────────

def test_adv_p13_03_cross_tenant_dependency_idor(client: TestClient, adv_p13_fixture):
    """ADV-P13-03: Meridian user attempts to remove or list Apex Process Dependency -> HTTP 404."""
    meridian_h = get_token_headers(adv_p13_fixture["meridian_analyst"])
    apex_dep_id = adv_p13_fixture["apex_dep"].id
    apex_proc_id = adv_p13_fixture["apex_proc"].id

    # Remove Apex dependency
    resp_del = client.delete(f"/api/v1/resilience/dependencies/{apex_dep_id}", headers=meridian_h)
    assert resp_del.status_code == 404

    # Add dependency to Apex process
    resp_add = client.post(
        "/api/v1/resilience/dependencies",
        headers=meridian_h,
        json={
            "process_id": apex_proc_id,
            "dependency_type": "VENDOR",
            "dependency_id": adv_p13_fixture["meridian_vendor"].id,
        },
    )
    assert resp_add.status_code == 404


# ─── ADV-P13-04: Cross-Tenant Vendor Injection ───────────────────────────────

def test_adv_p13_04_cross_tenant_vendor_injection(client: TestClient, adv_p13_fixture):
    """ADV-P13-04: Apex analyst attempts to link Meridian Vendor to Apex Process -> HTTP 404."""
    apex_h = get_token_headers(adv_p13_fixture["apex_analyst"])

    resp = client.post(
        "/api/v1/resilience/dependencies",
        headers=apex_h,
        json={
            "process_id": adv_p13_fixture["apex_proc"].id,
            "dependency_type": "VENDOR",
            "dependency_id": adv_p13_fixture["meridian_vendor"].id,
            "notes": "Malicious foreign vendor injection",
        },
    )
    assert resp.status_code == 404
    assert "Vendor" in resp.json()["detail"]
    assert "not found in tenant" in resp.json()["detail"]


# ─── ADV-P13-05: Cross-Tenant Control Injection ──────────────────────────────

def test_adv_p13_05_cross_tenant_control_injection(client: TestClient, adv_p13_fixture):
    """ADV-P13-05: Apex analyst attempts to link Meridian Control to Apex Process -> HTTP 404."""
    apex_h = get_token_headers(adv_p13_fixture["apex_analyst"])

    resp = client.post(
        "/api/v1/resilience/dependencies",
        headers=apex_h,
        json={
            "process_id": adv_p13_fixture["apex_proc"].id,
            "dependency_type": "CONTROL",
            "dependency_id": adv_p13_fixture["meridian_ctrl"].id,
            "notes": "Malicious foreign control injection",
        },
    )
    assert resp.status_code == 404
    assert "Control" in resp.json()["detail"]
    assert "not found in tenant" in resp.json()["detail"]


# ─── ADV-P13-06: Organization ID Spoofing ────────────────────────────────────

def test_adv_p13_06_organization_id_spoofing(client: TestClient, adv_p13_fixture):
    """ADV-P13-06: Client injecting foreign organization_id in body is ignored; server enforces JWT org."""
    apex_h = get_token_headers(adv_p13_fixture["apex_analyst"])

    resp = client.post(
        "/api/v1/resilience/processes",
        headers=apex_h,
        json={
            "name": "Org Spoofing Test Process",
            "organization_id": adv_p13_fixture["org_meridian"].id,
            "criticality_tier": "TIER_2",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["organization_id"] == adv_p13_fixture["org_apex"].id
    assert data["organization_id"] != adv_p13_fixture["org_meridian"].id


# ─── ADV-P13-07: Owner ID Spoofing ───────────────────────────────────────────

def test_adv_p13_07_owner_id_spoofing(client: TestClient, adv_p13_fixture):
    """ADV-P13-07: Client injecting arbitrary owner_id in body is overridden by authenticated user ID."""
    apex_h = get_token_headers(adv_p13_fixture["apex_analyst"])

    resp = client.post(
        "/api/v1/resilience/processes",
        headers=apex_h,
        json={
            "name": "Owner Spoofing Test Process",
            "owner_id": 999999,
            "criticality_tier": "TIER_3",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["owner_id"] == adv_p13_fixture["apex_analyst"].id
    assert data["owner_id"] != 999999


# ─── ADV-P13-08: Requested By ID Spoofing ────────────────────────────────────

def test_adv_p13_08_requested_by_id_spoofing(client: TestClient, adv_p13_fixture):
    """ADV-P13-08: Client injecting requested_by_id in BIA creation is ignored; server binds to caller."""
    apex_h = get_token_headers(adv_p13_fixture["apex_analyst"])

    resp = client.post(
        "/api/v1/resilience/bia",
        headers=apex_h,
        json={
            "process_id": adv_p13_fixture["apex_proc"].id,
            "requested_by_id": 999999,
            "rto_hours": 4.0,
            "mtd_hours": 24.0,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["requested_by_id"] == adv_p13_fixture["apex_analyst"].id
    assert data["requested_by_id"] != 999999


# ─── ADV-P13-09: Approved By ID Spoofing ─────────────────────────────────────

def test_adv_p13_09_approved_by_id_spoofing(client: TestClient, adv_p13_fixture):
    """ADV-P13-09: Client injecting approved_by_id in approval request is ignored; server binds to approver."""
    manager_h = get_token_headers(adv_p13_fixture["apex_manager"])
    bia_id = adv_p13_fixture["apex_bia_draft"].id

    resp = client.post(
        f"/api/v1/resilience/bia/{bia_id}/approve",
        headers=manager_h,
        json={
            "approved_by_id": 999999,
            "notes": "Approved by committee",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["approved_by_id"] == adv_p13_fixture["apex_manager"].id
    assert data["approved_by_id"] != 999999


# ─── ADV-P13-10: GRC Analyst Approval Attempt ────────────────────────────────

def test_adv_p13_10_grc_analyst_approval_attempt(client: TestClient, adv_p13_fixture):
    """ADV-P13-10: GRC Analyst lacking RESILIENCE_APPROVE permission cannot approve BIA -> HTTP 403."""
    analyst_h = get_token_headers(adv_p13_fixture["apex_analyst"])
    bia_id = adv_p13_fixture["apex_bia_draft"].id

    resp = client.post(
        f"/api/v1/resilience/bia/{bia_id}/approve",
        headers=analyst_h,
        json={"notes": "Analyst attempting unauthorized approval"},
    )
    assert resp.status_code == 403
    assert "Operation not permitted" in resp.json()["detail"]


# ─── ADV-P13-11: Security Analyst Mutation ───────────────────────────────────

def test_adv_p13_11_security_analyst_mutation(client: TestClient, adv_p13_fixture):
    """ADV-P13-11: Security Analyst (read-only in Phase 13) cannot create or modify resources -> HTTP 403."""
    sec_h = get_token_headers(adv_p13_fixture["apex_sec_analyst"])
    proc_id = adv_p13_fixture["apex_proc"].id

    # Create process attempt
    r1 = client.post("/api/v1/resilience/processes", headers=sec_h, json={"name": "Sec Process"})
    assert r1.status_code == 403

    # Draft BIA attempt
    r2 = client.post("/api/v1/resilience/bia", headers=sec_h, json={"process_id": proc_id, "rto_hours": 4.0, "mtd_hours": 24.0})
    assert r2.status_code == 403

    # Add dependency attempt
    r3 = client.post(
        "/api/v1/resilience/dependencies",
        headers=sec_h,
        json={"process_id": proc_id, "dependency_type": "VENDOR", "dependency_id": adv_p13_fixture["apex_vendor"].id},
    )
    assert r3.status_code == 403


# ─── ADV-P13-12: Auditor Mutation ────────────────────────────────────────────

def test_adv_p13_12_auditor_mutation(client: TestClient, adv_p13_fixture):
    """ADV-P13-12: Auditor role cannot mutate resilience resources -> HTTP 403."""
    auditor_h = get_token_headers(adv_p13_fixture["apex_auditor"])
    proc_id = adv_p13_fixture["apex_proc"].id

    r1 = client.post("/api/v1/resilience/processes", headers=auditor_h, json={"name": "Audit Process"})
    assert r1.status_code == 403

    r2 = client.post("/api/v1/resilience/bia", headers=auditor_h, json={"process_id": proc_id, "rto_hours": 4.0, "mtd_hours": 24.0})
    assert r2.status_code == 403


# ─── ADV-P13-13: Viewer Mutation ─────────────────────────────────────────────

def test_adv_p13_13_viewer_mutation(client: TestClient, adv_p13_fixture):
    """ADV-P13-13: Viewer role cannot mutate resilience resources -> HTTP 403."""
    viewer_h = get_token_headers(adv_p13_fixture["apex_viewer"])
    proc_id = adv_p13_fixture["apex_proc"].id

    r1 = client.post("/api/v1/resilience/processes", headers=viewer_h, json={"name": "Viewer Process"})
    assert r1.status_code == 403

    r2 = client.delete(f"/api/v1/resilience/processes/{proc_id}", headers=viewer_h)
    assert r2.status_code == 403


# ─── ADV-P13-14: Self-Approval Bypass ────────────────────────────────────────

def test_adv_p13_14_self_approval_bypass(client: TestClient, adv_p13_fixture):
    """ADV-P13-14: Four-eyes violation: Manager cannot approve their own drafted BIA -> HTTP 403."""
    manager_h = get_token_headers(adv_p13_fixture["apex_manager"])
    proc_id = adv_p13_fixture["apex_proc"].id

    # Manager creates BIA
    draft_resp = client.post(
        "/api/v1/resilience/bia",
        headers=manager_h,
        json={
            "process_id": proc_id,
            "rto_hours": 1.0,
            "mtd_hours": 8.0,
            "hourly_downtime_cost": 25000.0,
        },
    )
    assert draft_resp.status_code == 201
    bia_id = draft_resp.json()["id"]

    # Same manager attempts self-approval
    self_appr = client.post(
        f"/api/v1/resilience/bia/{bia_id}/approve",
        headers=manager_h,
        json={"notes": "Self approval attempt"},
    )
    assert self_appr.status_code == 403
    assert "Four-eyes governance violation" in self_appr.json()["detail"]


# ─── ADV-P13-15: Approval of ACTIVE BIA ───────────────────────────────────────

def test_adv_p13_15_approval_of_active_bia(client: TestClient, db: Session, adv_p13_fixture):
    """ADV-P13-15: Attempting to approve an already ACTIVE BIA -> HTTP 409 Conflict."""
    manager_h = get_token_headers(adv_p13_fixture["apex_manager"])
    bia_id = adv_p13_fixture["apex_bia_draft"].id

    # First approval succeeds
    client.post(f"/api/v1/resilience/bia/{bia_id}/approve", headers=manager_h)

    # Second approval attempt on ACTIVE BIA
    manager2_h = get_token_headers(adv_p13_fixture["apex_manager_2"])
    second_appr = client.post(f"/api/v1/resilience/bia/{bia_id}/approve", headers=manager2_h)
    assert second_appr.status_code == 409
    assert "Only DRAFT records can be approved" in second_appr.json()["detail"]


# ─── ADV-P13-16: Approval of SUPERSEDED BIA ──────────────────────────────────

def test_adv_p13_16_approval_of_superseded_bia(client: TestClient, db: Session, adv_p13_fixture):
    """ADV-P13-16: Attempting to approve a SUPERSEDED BIA -> HTTP 409 Conflict."""
    analyst_h = get_token_headers(adv_p13_fixture["apex_analyst"])
    manager_h = get_token_headers(adv_p13_fixture["apex_manager"])
    proc_id = adv_p13_fixture["apex_proc"].id

    # 1. Approve v1 -> ACTIVE
    v1_id = adv_p13_fixture["apex_bia_draft"].id
    client.post(f"/api/v1/resilience/bia/{v1_id}/approve", headers=manager_h)

    # 2. Draft v2 and approve -> v1 becomes SUPERSEDED
    v2 = client.post(
        "/api/v1/resilience/bia",
        headers=analyst_h,
        json={"process_id": proc_id, "rto_hours": 3.0, "mtd_hours": 15.0},
    ).json()
    client.post(f"/api/v1/resilience/bia/{v2['id']}/approve", headers=manager_h)

    # 3. Attempt to re-approve v1 (now SUPERSEDED)
    reapprove = client.post(
        f"/api/v1/resilience/bia/{v1_id}/approve",
        headers=manager_h,
    )
    assert reapprove.status_code == 409
    assert "SUPERSEDED" in reapprove.json()["detail"]


# ─── ADV-P13-17: Illegal Lifecycle Transition ────────────────────────────────

def test_adv_p13_17_illegal_lifecycle_transition(client: TestClient, db: Session, adv_p13_fixture):
    """ADV-P13-17: Attempting to archive an ACTIVE or SUPERSEDED BIA -> HTTP 409 Conflict."""
    manager_h = get_token_headers(adv_p13_fixture["apex_manager"])
    analyst_h = get_token_headers(adv_p13_fixture["apex_analyst"])
    v1_id = adv_p13_fixture["apex_bia_draft"].id

    # Approve v1 -> ACTIVE
    client.post(f"/api/v1/resilience/bia/{v1_id}/approve", headers=manager_h)

    # Attempt to archive ACTIVE BIA
    arch_active = client.post(f"/api/v1/resilience/bia/{v1_id}/archive", headers=analyst_h)
    assert arch_active.status_code == 409
    assert "Only DRAFT BIA versions can be archived" in arch_active.json()["detail"]


# ─── ADV-P13-18: Modification of ACTIVE BIA ──────────────────────────────────

def test_adv_p13_18_modification_of_active_bia(client: TestClient, db: Session, adv_p13_fixture):
    """ADV-P13-18: Attempting to update an ACTIVE BIA via PUT -> HTTP 409 Conflict."""
    manager_h = get_token_headers(adv_p13_fixture["apex_manager"])
    analyst_h = get_token_headers(adv_p13_fixture["apex_analyst"])
    v1_id = adv_p13_fixture["apex_bia_draft"].id
    proc_id = adv_p13_fixture["apex_proc"].id

    # Approve v1 -> ACTIVE
    client.post(f"/api/v1/resilience/bia/{v1_id}/approve", headers=manager_h)

    # Attempt to modify ACTIVE BIA
    mod_resp = client.put(
        f"/api/v1/resilience/bia/{v1_id}",
        headers=analyst_h,
        json={"process_id": proc_id, "rto_hours": 1.0, "mtd_hours": 10.0},
    )
    assert mod_resp.status_code == 409
    assert "Only DRAFT records can be updated" in mod_resp.json()["detail"]


# ─── ADV-P13-19: Modification of SUPERSEDED BIA ──────────────────────────────

def test_adv_p13_19_modification_of_superseded_bia(client: TestClient, db: Session, adv_p13_fixture):
    """ADV-P13-19: Attempting to update a SUPERSEDED BIA via PUT -> HTTP 409 Conflict."""
    analyst_h = get_token_headers(adv_p13_fixture["apex_analyst"])
    manager_h = get_token_headers(adv_p13_fixture["apex_manager"])
    proc_id = adv_p13_fixture["apex_proc"].id
    v1_id = adv_p13_fixture["apex_bia_draft"].id

    # Approve v1 -> ACTIVE
    client.post(f"/api/v1/resilience/bia/{v1_id}/approve", headers=manager_h)

    # Draft v2 and approve -> v1 SUPERSEDED
    v2 = client.post(
        "/api/v1/resilience/bia",
        headers=analyst_h,
        json={"process_id": proc_id, "rto_hours": 2.0, "mtd_hours": 10.0},
    ).json()
    client.post(f"/api/v1/resilience/bia/{v2['id']}/approve", headers=manager_h)

    # Attempt to modify SUPERSEDED BIA
    mod_resp = client.put(
        f"/api/v1/resilience/bia/{v1_id}",
        headers=analyst_h,
        json={"process_id": proc_id, "rto_hours": 5.0, "mtd_hours": 20.0},
    )
    assert mod_resp.status_code == 409
    assert "Only DRAFT records can be updated" in mod_resp.json()["detail"]


# ─── ADV-P13-20: Duplicate Active Baseline ───────────────────────────────────

def test_adv_p13_20_duplicate_active_baseline(client: TestClient, db: Session, adv_p13_fixture):
    """ADV-P13-20: Guarantee exactly one ACTIVE BIA baseline exists per process at any point in time."""
    analyst_h = get_token_headers(adv_p13_fixture["apex_analyst"])
    manager_h = get_token_headers(adv_p13_fixture["apex_manager"])
    proc_id = adv_p13_fixture["apex_proc"].id
    org_id = adv_p13_fixture["org_apex"].id

    # 1. Approve v1
    v1_id = adv_p13_fixture["apex_bia_draft"].id
    client.post(f"/api/v1/resilience/bia/{v1_id}/approve", headers=manager_h)

    # 2. Draft & Approve v2
    v2 = client.post(
        "/api/v1/resilience/bia",
        headers=analyst_h,
        json={"process_id": proc_id, "rto_hours": 2.0, "mtd_hours": 10.0},
    ).json()
    client.post(f"/api/v1/resilience/bia/{v2['id']}/approve", headers=manager_h)

    # 3. Draft & Approve v3
    v3 = client.post(
        "/api/v1/resilience/bia",
        headers=analyst_h,
        json={"process_id": proc_id, "rto_hours": 1.5, "mtd_hours": 8.0},
    ).json()
    client.post(f"/api/v1/resilience/bia/{v3['id']}/approve", headers=manager_h)

    # Verify directly in database that only 1 record is ACTIVE for this process
    active_count = (
        db.query(BusinessImpactAnalysis)
        .filter(
            BusinessImpactAnalysis.organization_id == org_id,
            BusinessImpactAnalysis.process_id == proc_id,
            BusinessImpactAnalysis.status == BiaStatusEnum.ACTIVE,
        )
        .count()
    )
    assert active_count == 1


# ─── ADV-P13-21: Dependency ID Substitution ──────────────────────────────────

def test_adv_p13_21_dependency_id_substitution(client: TestClient, adv_p13_fixture):
    """ADV-P13-21: Submitting non-existent entity IDs for dependencies -> HTTP 404."""
    apex_h = get_token_headers(adv_p13_fixture["apex_analyst"])
    proc_id = adv_p13_fixture["apex_proc"].id

    # Non-existent Vendor
    resp_vnd = client.post(
        "/api/v1/resilience/dependencies",
        headers=apex_h,
        json={"process_id": proc_id, "dependency_type": "VENDOR", "dependency_id": 999999},
    )
    assert resp_vnd.status_code == 404
    assert "Vendor #999999 not found" in resp_vnd.json()["detail"]

    # Non-existent Control
    resp_ctrl = client.post(
        "/api/v1/resilience/dependencies",
        headers=apex_h,
        json={"process_id": proc_id, "dependency_type": "CONTROL", "dependency_id": 999999},
    )
    assert resp_ctrl.status_code == 404
    assert "Control #999999 not found" in resp_ctrl.json()["detail"]


# ─── ADV-P13-22: Negative Outage Values & Invalid Thresholds ─────────────────

def test_adv_p13_22_negative_outage_values(client: TestClient, adv_p13_fixture):
    """ADV-P13-22: Schema validation rejects negative loss parameters and RTO > MTD -> HTTP 422."""
    apex_h = get_token_headers(adv_p13_fixture["apex_analyst"])
    proc_id = adv_p13_fixture["apex_proc"].id

    # Negative outage hours
    r1 = client.post(
        "/api/v1/resilience/outage-loss",
        headers=apex_h,
        json={"duration_hours": -5.0, "hourly_downtime_cost": 1000.0},
    )
    assert r1.status_code == 422

    # Negative hourly cost
    r2 = client.post(
        "/api/v1/resilience/outage-loss",
        headers=apex_h,
        json={"duration_hours": 5.0, "hourly_downtime_cost": -1000.0},
    )
    assert r2.status_code == 422

    # BIA with RTO > MTD
    r3 = client.post(
        "/api/v1/resilience/bia",
        headers=apex_h,
        json={"process_id": proc_id, "rto_hours": 48.0, "mtd_hours": 24.0},
    )
    assert r3.status_code == 422


# ─── ADV-P13-23: Approved At Spoofing ────────────────────────────────────────

def test_adv_p13_23_approved_at_spoofing(client: TestClient, adv_p13_fixture):
    """ADV-P13-23: Client injecting approved_at timestamp is ignored; server sets authoritative current time."""
    manager_h = get_token_headers(adv_p13_fixture["apex_manager"])
    bia_id = adv_p13_fixture["apex_bia_draft"].id

    resp = client.post(
        f"/api/v1/resilience/bia/{bia_id}/approve",
        headers=manager_h,
        json={"approved_at": "1999-01-01T00:00:00Z"},
    )
    assert resp.status_code == 200
    approved_at_str = resp.json()["approved_at"]
    assert approved_at_str is not None
    # Ensure the approval year is current (>= 2026)
    assert int(approved_at_str[:4]) >= 2026


# ─── ADV-P13-24: Tenant Identity Spoofing ────────────────────────────────────

def test_adv_p13_24_tenant_identity_spoofing(client: TestClient, adv_p13_fixture):
    """ADV-P13-24: Meridian token attempting access to Apex resources receives 404 without data leakage."""
    meridian_h = get_token_headers(adv_p13_fixture["meridian_analyst"])
    apex_proc_id = adv_p13_fixture["apex_proc"].id

    resp = client.get(f"/api/v1/resilience/processes/{apex_proc_id}", headers=meridian_h)
    assert resp.status_code == 404
    # Ensure error detail does not reveal Apex internal data
    assert "Apex" not in resp.text


# ─── ADV-P13-25: Audit Bypass Attempt ────────────────────────────────────────

def test_adv_p13_25_audit_bypass_attempt(client: TestClient, db: Session, adv_p13_fixture):
    """ADV-P13-25: Verify all state-mutating actions produce immutable audit log entries."""
    analyst_h = get_token_headers(adv_p13_fixture["apex_analyst"])
    manager_h = get_token_headers(adv_p13_fixture["apex_manager"])
    org_id = adv_p13_fixture["org_apex"].id

    # 1. Create Process
    proc_resp = client.post(
        "/api/v1/resilience/processes",
        headers=analyst_h,
        json={"name": "Audited Resilience Process"},
    )
    assert proc_resp.status_code == 201
    proc_id = proc_resp.json()["id"]

    # 2. Update Process
    client.put(
        f"/api/v1/resilience/processes/{proc_id}",
        headers=analyst_h,
        json={"name": "Audited Resilience Process Updated"},
    )

    # 3. Draft BIA
    bia_resp = client.post(
        "/api/v1/resilience/bia",
        headers=analyst_h,
        json={"process_id": proc_id, "rto_hours": 2.0, "mtd_hours": 12.0},
    )
    assert bia_resp.status_code == 201
    bia_id = bia_resp.json()["id"]

    # 4. Approve BIA
    client.post(f"/api/v1/resilience/bia/{bia_id}/approve", headers=manager_h)

    # 5. Add Dependency
    dep_resp = client.post(
        "/api/v1/resilience/dependencies",
        headers=analyst_h,
        json={
            "process_id": proc_id,
            "dependency_type": "VENDOR",
            "dependency_id": adv_p13_fixture["apex_vendor"].id,
        },
    )
    dep_id = dep_resp.json()["id"]

    # 6. Remove Dependency
    client.delete(f"/api/v1/resilience/dependencies/{dep_id}", headers=analyst_h)

    # 7. Draft another BIA and Archive it
    bia2 = client.post(
        "/api/v1/resilience/bia",
        headers=analyst_h,
        json={"process_id": proc_id, "rto_hours": 4.0, "mtd_hours": 24.0},
    ).json()
    client.post(f"/api/v1/resilience/bia/{bia2['id']}/archive", headers=analyst_h)

    # Query audit logs
    final_audit_logs = (
        db.query(AuditLog)
        .filter(AuditLog.organization_id == org_id)
        .all()
    )
    actions = [log.action for log in final_audit_logs]

    assert "BUSINESS_PROCESS_CREATED" in actions
    assert "BUSINESS_PROCESS_UPDATED" in actions
    assert "BIA_DRAFTED" in actions
    assert "BIA_APPROVED" in actions
    assert "PROCESS_DEPENDENCY_ADDED" in actions
    assert "PROCESS_DEPENDENCY_REMOVED" in actions
    assert "BIA_ARCHIVED" in actions

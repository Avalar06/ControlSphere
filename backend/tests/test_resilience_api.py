from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.permissions import RoleEnum
from app.core.security import get_password_hash
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
def resilience_api_setup(db: Session, org_apex: Organization):
    """Setup multi-role users and foundational GRC data for Phase 13 API tests."""
    admin = User(
        email="res_admin@apex.com",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Resilience Admin",
        role=RoleEnum.ADMIN,
        is_active=True,
        organization_id=org_apex.id,
    )
    manager = User(
        email="res_manager@apex.com",
        hashed_password=get_password_hash("ManagerPass123!"),
        full_name="Resilience Manager",
        role=RoleEnum.MANAGER,
        is_active=True,
        organization_id=org_apex.id,
    )
    analyst = User(
        email="res_analyst@apex.com",
        hashed_password=get_password_hash("AnalystPass123!"),
        full_name="Resilience Analyst",
        role=RoleEnum.GRC_ANALYST,
        is_active=True,
        organization_id=org_apex.id,
    )
    viewer = User(
        email="res_viewer@apex.com",
        hashed_password=get_password_hash("ViewerPass123!"),
        full_name="Resilience Viewer",
        role=RoleEnum.VIEWER,
        is_active=True,
        organization_id=org_apex.id,
    )

    db.add_all([admin, manager, analyst, viewer])
    db.commit()

    # Framework and Control for dependency tests
    fw = Framework(name="NIST CSF Res", identifier="NIST-RES", version="2.0")
    db.add(fw)
    db.commit()

    fn = FrameworkFunction(framework_id=fw.id, identifier="PR", name="Protect")
    db.add(fn)
    db.commit()

    cat = FrameworkCategory(function_id=fn.id, identifier="PR.DS", name="Data Security")
    db.add(cat)
    db.commit()

    subcat = FrameworkSubcategory(category_id=cat.id, identifier="PR.DS-01", title="Data at rest protected", description="Desc")
    db.add(subcat)
    db.commit()

    ctrl = OrganizationControl(
        organization_id=org_apex.id,
        subcategory_id=subcat.id,
        status=ImplementationStatusEnum.IMPLEMENTED,
        priority=PriorityEnum.HIGH,
    )
    db.add(ctrl)
    db.commit()

    # Phase 9 Vendor for dependency tests
    vendor = Vendor(
        organization_id=org_apex.id,
        vendor_code="VND-RES-01",
        legal_name="Resilience Cloud Provider",
        calculated_tier=VendorTierEnum.TIER_1_CRITICAL,
        vendor_status=VendorStatusEnum.ACTIVE,
    )
    db.add(vendor)
    db.commit()

    return {
        "org_apex": org_apex,
        "admin": admin,
        "manager": manager,
        "analyst": analyst,
        "viewer": viewer,
        "control": ctrl,
        "vendor": vendor,
    }


# ─── 1. BUSINESS PROCESS CRUD ────────────────────────────────────────────────

def test_business_process_crud_api(client: TestClient, resilience_api_setup):
    """Test Create, List, Get, Update, Delete for business processes."""
    headers = get_token_headers(resilience_api_setup["analyst"])

    # 1. Create Process
    create_resp = client.post(
        "/api/v1/resilience/processes",
        headers=headers,
        json={
            "name": "Payment Processing",
            "description": "Core payment gateway operations",
            "criticality_tier": "TIER_1",
        },
    )
    assert create_resp.status_code == 201
    proc_data = create_resp.json()
    proc_id = proc_data["id"]
    assert proc_data["name"] == "Payment Processing"
    assert proc_data["criticality_tier"] == "TIER_1"

    # 2. List Processes
    list_resp = client.get("/api/v1/resilience/processes", headers=headers)
    assert list_resp.status_code == 200
    assert any(p["id"] == proc_id for p in list_resp.json())

    # 3. Get Process
    get_resp = client.get(f"/api/v1/resilience/processes/{proc_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Payment Processing"

    # 4. Update Process
    update_resp = client.put(
        f"/api/v1/resilience/processes/{proc_id}",
        headers=headers,
        json={"name": "Payment Processing v2", "criticality_tier": "TIER_2"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Payment Processing v2"
    assert update_resp.json()["criticality_tier"] == "TIER_2"

    # 5. Delete Process
    del_resp = client.delete(f"/api/v1/resilience/processes/{proc_id}", headers=headers)
    assert del_resp.status_code == 204

    # 6. Verify deleted
    get_deleted = client.get(f"/api/v1/resilience/processes/{proc_id}", headers=headers)
    assert get_deleted.status_code == 404


# ─── 2. BIA LIFECYCLE & FOUR-EYES APPROVAL ───────────────────────────────────

def test_bia_lifecycle_and_four_eyes_api(client: TestClient, resilience_api_setup):
    """Test BIA draft, approve (four-eyes), archive, and active baseline."""
    analyst_h = get_token_headers(resilience_api_setup["analyst"])
    manager_h = get_token_headers(resilience_api_setup["manager"])

    # Create process first
    proc = client.post(
        "/api/v1/resilience/processes",
        headers=analyst_h,
        json={"name": "Customer Onboarding", "criticality_tier": "TIER_1"},
    ).json()
    proc_id = proc["id"]

    # 1. Draft BIA v1
    draft_resp = client.post(
        "/api/v1/resilience/bia",
        headers=analyst_h,
        json={
            "process_id": proc_id,
            "rto_hours": 4.0,
            "rpo_hours": 1.0,
            "mtd_hours": 24.0,
            "hourly_downtime_cost": 10000.0,
            "fixed_outage_cost": 5000.0,
            "notes": "Initial BIA draft",
        },
    )
    assert draft_resp.status_code == 201
    bia_data = draft_resp.json()
    bia_id = bia_data["id"]
    assert bia_data["status"] == "DRAFT"
    assert bia_data["version"] == 1

    # 2. Get BIA
    get_bia = client.get(f"/api/v1/resilience/bia/{bia_id}", headers=analyst_h)
    assert get_bia.status_code == 200
    assert get_bia.json()["rto_hours"] == 4.0

    # 3. List BIAs for process
    list_bia = client.get(f"/api/v1/resilience/processes/{proc_id}/bia", headers=analyst_h)
    assert list_bia.status_code == 200
    assert len(list_bia.json()) >= 1

    # 4. Manager approves BIA (four-eyes: analyst drafted, manager approves)
    approve_resp = client.post(
        f"/api/v1/resilience/bia/{bia_id}/approve",
        headers=manager_h,
        json={"notes": "Approved by resilience committee"},
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "ACTIVE"
    assert approve_resp.json()["approved_by_id"] == resilience_api_setup["manager"].id

    # 5. Verify active baseline
    active_resp = client.get(f"/api/v1/resilience/processes/{proc_id}/bia/active", headers=analyst_h)
    assert active_resp.status_code == 200
    assert active_resp.json()["id"] == bia_id

    # 6. Draft BIA v2 and approve -> v1 superseded
    draft_v2 = client.post(
        "/api/v1/resilience/bia",
        headers=analyst_h,
        json={
            "process_id": proc_id,
            "rto_hours": 2.0,
            "rpo_hours": 0.5,
            "mtd_hours": 12.0,
            "hourly_downtime_cost": 15000.0,
            "fixed_outage_cost": 8000.0,
        },
    )
    assert draft_v2.status_code == 201
    v2_id = draft_v2.json()["id"]
    assert draft_v2.json()["version"] == 2

    # Approve v2 -> v1 superseded
    appr_v2 = client.post(
        f"/api/v1/resilience/bia/{v2_id}/approve",
        headers=manager_h,
    )
    assert appr_v2.status_code == 200
    assert appr_v2.json()["status"] == "ACTIVE"

    # Verify v1 is now SUPERSEDED
    v1_check = client.get(f"/api/v1/resilience/bia/{bia_id}", headers=analyst_h)
    assert v1_check.json()["status"] == "SUPERSEDED"


# ─── 3. BIA ARCHIVE ──────────────────────────────────────────────────────────

def test_bia_archive_api(client: TestClient, resilience_api_setup):
    """Test archiving a draft BIA and rejecting archive of non-draft."""
    analyst_h = get_token_headers(resilience_api_setup["analyst"])
    manager_h = get_token_headers(resilience_api_setup["manager"])

    # Create process
    proc = client.post(
        "/api/v1/resilience/processes",
        headers=analyst_h,
        json={"name": "Data Archival Process"},
    ).json()

    # Draft BIA
    draft = client.post(
        "/api/v1/resilience/bia",
        headers=analyst_h,
        json={"process_id": proc["id"], "rto_hours": 8.0, "mtd_hours": 48.0},
    ).json()

    # Archive draft -> success
    archive_resp = client.post(
        f"/api/v1/resilience/bia/{draft['id']}/archive",
        headers=analyst_h,
    )
    assert archive_resp.status_code == 200
    assert archive_resp.json()["status"] == "ARCHIVED"

    # Cannot archive again (no longer DRAFT)
    archive_again = client.post(
        f"/api/v1/resilience/bia/{draft['id']}/archive",
        headers=analyst_h,
    )
    assert archive_again.status_code == 409


# ─── 4. CROSS-MODULE DEPENDENCIES ────────────────────────────────────────────

def test_process_dependencies_api(client: TestClient, resilience_api_setup):
    """Test adding, listing, and removing Vendor and Control dependencies."""
    headers = get_token_headers(resilience_api_setup["analyst"])

    # Create process
    proc = client.post(
        "/api/v1/resilience/processes",
        headers=headers,
        json={"name": "Supply Chain Logistics"},
    ).json()
    proc_id = proc["id"]

    # 1. Add Vendor dependency
    vendor_dep = client.post(
        "/api/v1/resilience/dependencies",
        headers=headers,
        json={
            "process_id": proc_id,
            "dependency_type": "VENDOR",
            "dependency_id": resilience_api_setup["vendor"].id,
            "notes": "Primary cloud provider",
        },
    )
    assert vendor_dep.status_code == 201
    dep_id = vendor_dep.json()["id"]

    # 2. Add Control dependency
    ctrl_dep = client.post(
        "/api/v1/resilience/dependencies",
        headers=headers,
        json={
            "process_id": proc_id,
            "dependency_type": "CONTROL",
            "dependency_id": resilience_api_setup["control"].id,
        },
    )
    assert ctrl_dep.status_code == 201

    # 3. List dependencies
    list_deps = client.get(f"/api/v1/resilience/processes/{proc_id}/dependencies", headers=headers)
    assert list_deps.status_code == 200
    assert len(list_deps.json()) == 2

    # 4. Remove vendor dependency
    del_resp = client.delete(f"/api/v1/resilience/dependencies/{dep_id}", headers=headers)
    assert del_resp.status_code == 204

    # Verify removed
    list_after = client.get(f"/api/v1/resilience/processes/{proc_id}/dependencies", headers=headers)
    assert len(list_after.json()) == 1


# ─── 5. OUTAGE LOSS CALCULATION ──────────────────────────────────────────────

def test_outage_loss_calculation_api(client: TestClient, resilience_api_setup):
    """Test deterministic outage loss calculation endpoint."""
    headers = get_token_headers(resilience_api_setup["analyst"])

    resp = client.post(
        "/api/v1/resilience/outage-loss",
        headers=headers,
        json={
            "duration_hours": 8.0,
            "hourly_downtime_cost": 10000.0,
            "fixed_outage_cost": 5000.0,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_projected_loss"] == 85000.0
    assert data["variable_outage_cost"] == 80000.0
    assert data["fixed_outage_cost"] == 5000.0
    assert data["duration_hours"] == 8.0


# ─── 6. RBAC PERMISSION MATRIX ───────────────────────────────────────────────

def test_resilience_rbac_permissions_api(client: TestClient, resilience_api_setup):
    """Test RBAC across roles for Phase 13 endpoints."""
    analyst_h = get_token_headers(resilience_api_setup["analyst"])
    manager_h = get_token_headers(resilience_api_setup["manager"])
    viewer_h = get_token_headers(resilience_api_setup["viewer"])

    # VIEWER can read processes
    assert client.get("/api/v1/resilience/processes", headers=viewer_h).status_code == 200

    # VIEWER cannot create process (403)
    assert client.post(
        "/api/v1/resilience/processes",
        headers=viewer_h,
        json={"name": "Viewer Test Process"},
    ).status_code == 403

    # ANALYST can create process
    proc = client.post(
        "/api/v1/resilience/processes",
        headers=analyst_h,
        json={"name": "RBAC Test Process"},
    )
    assert proc.status_code == 201
    proc_id = proc.json()["id"]

    # ANALYST drafts BIA
    bia = client.post(
        "/api/v1/resilience/bia",
        headers=analyst_h,
        json={"process_id": proc_id, "rto_hours": 4.0, "mtd_hours": 24.0},
    )
    assert bia.status_code == 201
    bia_id = bia.json()["id"]

    # ANALYST cannot approve BIA (no RESILIENCE_APPROVE permission)
    assert client.post(
        f"/api/v1/resilience/bia/{bia_id}/approve",
        headers=analyst_h,
    ).status_code == 403

    # MANAGER can approve BIA
    assert client.post(
        f"/api/v1/resilience/bia/{bia_id}/approve",
        headers=manager_h,
    ).status_code == 200

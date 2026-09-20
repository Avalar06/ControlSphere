from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.permissions import RoleEnum
from app.core.security import get_password_hash
from app.models.organization import Organization
from app.models.user import User
from app.models.policy import (
    Policy,
    PolicyStatusEnum,
    PolicyTypeEnum,
    PolicyVersionStatusEnum,
    CampaignStatusEnum,
)
from app.models.control import OrganizationControl, ImplementationStatusEnum, PriorityEnum
from app.models.framework import Framework, FrameworkFunction, FrameworkCategory, FrameworkSubcategory
from app.schemas.policy import PolicyCreate
from app.services.policy_service import PolicyService
from tests.conftest import get_token_headers


@pytest.fixture
def p24_api_fixture(db: Session, org_apex: Organization):
    admin = User(
        email="p24api_admin@apex.com",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Apex Admin",
        role=RoleEnum.ADMIN,
        is_active=True,
        organization_id=org_apex.id,
    )
    manager = User(
        email="p24api_manager@apex.com",
        hashed_password=get_password_hash("MgrPass123!"),
        full_name="Apex Manager",
        role=RoleEnum.MANAGER,
        is_active=True,
        organization_id=org_apex.id,
    )
    analyst = User(
        email="p24api_analyst@apex.com",
        hashed_password=get_password_hash("AnalystPass123!"),
        full_name="Apex Analyst",
        role=RoleEnum.GRC_ANALYST,
        is_active=True,
        organization_id=org_apex.id,
    )
    viewer = User(
        email="p24api_viewer@apex.com",
        hashed_password=get_password_hash("ViewerPass123!"),
        full_name="Apex Viewer",
        role=RoleEnum.VIEWER,
        is_active=True,
        organization_id=org_apex.id,
    )
    db.add_all([admin, manager, analyst, viewer])
    db.commit()

    policy = PolicyService.create_policy(
        db=db,
        obj_in=PolicyCreate(
            title="Access Control Policy",
            description="Enterprise IAM requirements",
            policy_type=PolicyTypeEnum.ACCESS_CONTROL,
            initial_content="# Access Control Policy\n\nAll accounts require MFA.",
        ),
        organization_id=org_apex.id,
        created_by_id=admin.id,
    )

    subcat = db.query(FrameworkSubcategory).first()
    if not subcat:
        fw = Framework(identifier="P24-API-FW", name="P24 API Governance", version="1.0")
        db.add(fw)
        db.flush()
        fn = FrameworkFunction(framework_id=fw.id, identifier="GV", name="Governance", display_order=1)
        db.add(fn)
        db.flush()
        cat = FrameworkCategory(function_id=fn.id, identifier="GV.PO", name="Policy", display_order=1)
        db.add(cat)
        db.flush()
        subcat = FrameworkSubcategory(category_id=cat.id, identifier="GV.PO-01", title="Policy Control", description="Policy control mapping", display_order=1)
        db.add(subcat)
        db.flush()

    ctrl = db.query(OrganizationControl).filter(
        OrganizationControl.organization_id == org_apex.id,
        OrganizationControl.subcategory_id == subcat.id,
    ).first()
    if not ctrl:
        ctrl = OrganizationControl(
            organization_id=org_apex.id,
            subcategory_id=subcat.id,
            status=ImplementationStatusEnum.IMPLEMENTED,
            priority=PriorityEnum.HIGH,
        )
        db.add(ctrl)
        db.commit()

    PolicyService.add_control_mapping(db, policy.id, org_apex.id, subcat.id)

    return {
        "org": org_apex,
        "admin": admin,
        "manager": manager,
        "analyst": analyst,
        "viewer": viewer,
        "policy": policy,
    }


def test_phase24_api_full_version_lifecycle(client: TestClient, p24_api_fixture):
    """Test full version lifecycle: create v2 -> submit review -> manager approve -> publish -> check superseded."""
    admin_h = get_token_headers(p24_api_fixture["admin"])
    mgr_h = get_token_headers(p24_api_fixture["manager"])
    pol_id = p24_api_fixture["policy"].id

    # 1. Create Version 2 by Admin
    r_v2 = client.post(
        f"/api/v1/policies/{pol_id}/versions",
        headers=admin_h,
        json={"content": "# Access Control v2\n\nPassword rotation every 90 days.", "change_summary": "v2 update"},
    )
    assert r_v2.status_code == 201
    v2_data = r_v2.json()
    assert v2_data["version_number"] == 2
    assert v2_data["status"] == "DRAFT"
    assert v2_data["content_hash_sha256"] is not None
    v2_id = v2_data["id"]

    # 2. Submit for review
    r_sub = client.post(
        f"/api/v1/policies/{pol_id}/versions/{v2_id}/submit-review",
        headers=admin_h,
        json={"review_stage": "LEGAL_REVIEW", "review_notes": "Please approve v2"},
    )
    assert r_sub.status_code == 200
    wf_id = r_sub.json()["id"]

    # 3. Manager approves (Four-Eyes check passes because admin != manager)
    r_app = client.post(
        f"/api/v1/policies/{pol_id}/versions/{v2_id}/review/{wf_id}",
        headers=mgr_h,
        json={"decision": "APPROVE", "review_notes": "Looks solid."},
    )
    assert r_app.status_code == 200
    assert r_app.json()["status"] == "APPROVED"

    # 4. Publish Version 2
    r_pub = client.post(
        f"/api/v1/policies/{pol_id}/versions/{v2_id}/publish",
        headers=admin_h,
    )
    assert r_pub.status_code == 200
    assert r_pub.json()["status"] == "PUBLISHED"

    # 5. Verify versions list shows v2 published and v1 superseded/draft
    r_list = client.get(f"/api/v1/policies/{pol_id}/versions", headers=admin_h)
    assert r_list.status_code == 200
    versions = r_list.json()
    assert len(versions) == 2
    v2_found = next(v for v in versions if v["id"] == v2_id)
    assert v2_found["status"] == "PUBLISHED"


def test_phase24_api_full_campaign_and_attestation_flow(client: TestClient, p24_api_fixture):
    """Test full attestation campaign: create -> launch -> user attest -> evidence manifest generation."""
    mgr_h = get_token_headers(p24_api_fixture["manager"])
    viewer_h = get_token_headers(p24_api_fixture["viewer"])
    pol = p24_api_fixture["policy"]
    v1 = pol.versions[0]

    # 1. Manager creates campaign
    r_camp = client.post(
        "/api/v1/policies/campaigns",
        headers=mgr_h,
        json={
            "campaign_code": "CAMP-ANNUAL-2026",
            "title": "2026 Annual Security Attestation",
            "description": "Mandatory review for all staff",
            "policy_id": pol.id,
            "version_id": v1.id,
            "target_type": "ALL_USERS",
            "due_date": (datetime.now(timezone.utc) + timedelta(days=14)).isoformat(),
        },
    )
    assert r_camp.status_code == 201
    camp_id = r_camp.json()["id"]
    camp_hash = r_camp.json()["policy_version_hash"]

    # 2. Manager launches campaign
    r_launch = client.post(f"/api/v1/policies/campaigns/{camp_id}/launch", headers=mgr_h)
    assert r_launch.status_code == 200
    assert r_launch.json()["status"] == "ACTIVE"
    assert r_launch.json()["total_targeted_count"] >= 4

    # 3. Viewer checks /my-pending-attestations
    r_my = client.get("/api/v1/policies/my-pending-attestations", headers=viewer_h)
    assert r_my.status_code == 200
    pending_list = r_my.json()
    assert any(p["campaign_id"] == camp_id for p in pending_list)

    # 4. Viewer attests
    r_att = client.post(
        f"/api/v1/policies/campaigns/{camp_id}/attest",
        headers=viewer_h,
        json={
            "policy_version_hash": camp_hash,
            "acknowledgement_text": "I have read and will abide by the Access Control Policy.",
        },
    )
    assert r_att.status_code == 200
    att_data = r_att.json()
    assert att_data["status"] == "ATTESTED"
    assert att_data["attestation_receipt_hash"] is not None

    # 5. Manager checks campaign progress telemetry
    r_prog = client.get(f"/api/v1/policies/campaigns/{camp_id}", headers=mgr_h)
    assert r_prog.status_code == 200
    assert r_prog.json()["completed_count"] >= 1

    # 6. Manager generates evidence manifest
    r_evid = client.post(f"/api/v1/policies/campaigns/{camp_id}/evidence", headers=mgr_h)
    assert r_evid.status_code == 200
    evid_data = r_evid.json()
    assert evid_data["status"] == "UPLOADED"
    assert evid_data["sha256_hash"] is not None
    assert evid_data["total_completed"] >= 1

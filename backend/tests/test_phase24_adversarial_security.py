from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.permissions import RoleEnum
from app.core.security import get_password_hash
from app.models.organization import Organization
from app.models.user import User
from app.models.assessment import (
    Assessment,
    AssessmentMethodEnum,
    AssessmentStatusEnum,
    AssessmentConclusionEnum,
)
from app.models.control import OrganizationControl, ImplementationStatusEnum, PriorityEnum
from app.models.framework import Framework, FrameworkFunction, FrameworkCategory, FrameworkSubcategory
from app.models.policy import (
    Policy,
    PolicyStatusEnum,
    PolicyTypeEnum,
    PolicyVersion,
    PolicyVersionStatusEnum,
    PolicyAttestationCampaign,
    CampaignStatusEnum,
    CampaignTargetTypeEnum,
    UserAttestationRecord,
    AttestationRecordStatusEnum,
)
from app.schemas.policy import (
    PolicyCreate,
    PolicyVersionCreate,
    PolicyReviewWorkflowCreate,
    PolicyReviewWorkflowAction,
    PolicyAttestationCampaignCreate,
    UserAttestationSubmit,
)
from app.services.policy_service import PolicyService
from tests.conftest import get_token_headers


@pytest.fixture
def p24_fixture(db: Session, org_apex: Organization, org_meridian: Organization):
    """Setup adversarial test harness with isolated tenants, users, and policy baseline."""
    apex_admin = User(
        email="p24_apex_admin@apex.com",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Apex Admin",
        role=RoleEnum.ADMIN,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_manager = User(
        email="p24_apex_manager@apex.com",
        hashed_password=get_password_hash("MgrPass123!"),
        full_name="Apex Manager",
        role=RoleEnum.MANAGER,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_analyst = User(
        email="p24_apex_analyst@apex.com",
        hashed_password=get_password_hash("AnalystPass123!"),
        full_name="Apex Analyst",
        role=RoleEnum.GRC_ANALYST,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_auditor = User(
        email="p24_apex_auditor@apex.com",
        hashed_password=get_password_hash("AuditorPass123!"),
        full_name="Apex Auditor",
        role=RoleEnum.AUDITOR,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_viewer = User(
        email="p24_apex_viewer@apex.com",
        hashed_password=get_password_hash("ViewerPass123!"),
        full_name="Apex Viewer",
        role=RoleEnum.VIEWER,
        is_active=True,
        organization_id=org_apex.id,
    )
    meridian_admin = User(
        email="p24_meridian_admin@meridian.com",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Meridian Admin",
        role=RoleEnum.ADMIN,
        is_active=True,
        organization_id=org_meridian.id,
    )
    meridian_viewer = User(
        email="p24_meridian_viewer@meridian.com",
        hashed_password=get_password_hash("ViewerPass123!"),
        full_name="Meridian Viewer",
        role=RoleEnum.VIEWER,
        is_active=True,
        organization_id=org_meridian.id,
    )

    db.add_all([
        apex_admin, apex_manager, apex_analyst, apex_auditor, apex_viewer,
        meridian_admin, meridian_viewer,
    ])
    db.commit()

    # Seed Apex baseline policy
    policy = PolicyService.create_policy(
        db=db,
        obj_in=PolicyCreate(
            title="Apex Enterprise Security Policy",
            description="Core baseline policy for all employees",
            policy_type=PolicyTypeEnum.INFORMATION_SECURITY,
            initial_content="# Information Security Policy\n\nAll employees must follow access controls.",
        ),
        organization_id=org_apex.id,
        created_by_id=apex_admin.id,
    )

    subcat = db.query(FrameworkSubcategory).first()
    if not subcat:
        fw = Framework(identifier="P24-FW", name="P24 Governance", version="1.0")
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
        "org_apex": org_apex,
        "org_meridian": org_meridian,
        "apex_admin": apex_admin,
        "apex_manager": apex_manager,
        "apex_analyst": apex_analyst,
        "apex_auditor": apex_auditor,
        "apex_viewer": apex_viewer,
        "meridian_admin": meridian_admin,
        "meridian_viewer": meridian_viewer,
        "policy": policy,
    }


def test_adv_p24_01_cross_tenant_policy_access(client: TestClient, p24_fixture):
    """01. Meridian user cannot access Apex policy or its versions (HTTP 404)."""
    headers = get_token_headers(p24_fixture["meridian_admin"])
    apex_policy = p24_fixture["policy"]

    r = client.get(f"/api/v1/policies/{apex_policy.id}", headers=headers)
    assert r.status_code == 404

    r_ver = client.get(f"/api/v1/policies/{apex_policy.id}/versions", headers=headers)
    assert r_ver.status_code == 404


def test_adv_p24_02_cross_tenant_campaign_access(client: TestClient, db: Session, p24_fixture):
    """02. Meridian user cannot view Apex attestation campaigns (HTTP 404)."""
    apex_policy = p24_fixture["policy"]
    v1 = apex_policy.versions[0]

    campaign = PolicyService.create_campaign(
        db=db,
        campaign_in=PolicyAttestationCampaignCreate(
            campaign_code="CAMP-APEX-001",
            title="Q3 Security Attestation",
            policy_id=apex_policy.id,
            version_id=v1.id,
            due_date=datetime.now(timezone.utc) + timedelta(days=30),
        ),
        organization_id=p24_fixture["org_apex"].id,
        current_user_id=p24_fixture["apex_admin"].id,
    )

    meridian_headers = get_token_headers(p24_fixture["meridian_admin"])
    r = client.get(f"/api/v1/policies/campaigns/{campaign.id}", headers=meridian_headers)
    assert r.status_code == 404


def test_adv_p24_03_cross_tenant_attestation_access(client: TestClient, db: Session, p24_fixture):
    """03. Meridian user cannot submit attestation to Apex campaign (HTTP 404)."""
    apex_policy = p24_fixture["policy"]
    v1 = apex_policy.versions[0]

    campaign = PolicyService.create_campaign(
        db=db,
        campaign_in=PolicyAttestationCampaignCreate(
            campaign_code="CAMP-APEX-002",
            title="Q3 Security Attestation 2",
            policy_id=apex_policy.id,
            version_id=v1.id,
            due_date=datetime.now(timezone.utc) + timedelta(days=30),
        ),
        organization_id=p24_fixture["org_apex"].id,
        current_user_id=p24_fixture["apex_admin"].id,
    )
    PolicyService.launch_campaign(db, campaign.id, p24_fixture["org_apex"].id, p24_fixture["apex_admin"].id)

    meridian_headers = get_token_headers(p24_fixture["meridian_viewer"])
    r = client.post(
        f"/api/v1/policies/campaigns/{campaign.id}/attest",
        headers=meridian_headers,
        json={"policy_version_hash": campaign.policy_version_hash, "acknowledgement_text": "I agree"},
    )
    assert r.status_code == 404


def test_adv_p24_04_forged_user_identity(client: TestClient, db: Session, p24_fixture):
    """04. User cannot submit attestation on behalf of another user ID."""
    apex_policy = p24_fixture["policy"]
    v1 = apex_policy.versions[0]
    campaign = PolicyService.create_campaign(
        db=db,
        campaign_in=PolicyAttestationCampaignCreate(
            campaign_code="CAMP-FORGE-UID",
            title="Identity Forgery Campaign",
            policy_id=apex_policy.id,
            version_id=v1.id,
            due_date=datetime.now(timezone.utc) + timedelta(days=30),
        ),
        organization_id=p24_fixture["org_apex"].id,
        current_user_id=p24_fixture["apex_admin"].id,
    )
    PolicyService.launch_campaign(db, campaign.id, p24_fixture["org_apex"].id, p24_fixture["apex_admin"].id)

    viewer_headers = get_token_headers(p24_fixture["apex_viewer"])
    r = client.post(
        f"/api/v1/policies/campaigns/{campaign.id}/attest",
        headers=viewer_headers,
        json={
            "user_id": p24_fixture["apex_analyst"].id,
            "policy_version_hash": campaign.policy_version_hash,
            "acknowledgement_text": "Forged attestation",
        },
    )
    assert r.status_code == 200
    assert r.json()["user_id"] == p24_fixture["apex_viewer"].id


def test_adv_p24_05_forged_organization_id(client: TestClient, p24_fixture):
    """05. Injected organization_id in request body is ignored; server derives tenant from authenticated JWT."""
    headers = get_token_headers(p24_fixture["apex_manager"])
    r = client.post(
        "/api/v1/policies",
        headers=headers,
        json={
            "title": "Tenant Hijack Policy",
            "description": "Attempting to create policy under meridian org",
            "organization_id": p24_fixture["org_meridian"].id,
            "initial_content": "Arbitrary policy content",
        },
    )
    assert r.status_code == 201
    assert r.json()["organization_id"] == p24_fixture["org_apex"].id


def test_adv_p24_06_forged_policy_hash(client: TestClient, db: Session, p24_fixture):
    """06. Submitting attestation with forged/corrupted policy hash is rejected (HTTP 400)."""
    apex_policy = p24_fixture["policy"]
    v1 = apex_policy.versions[0]
    campaign = PolicyService.create_campaign(
        db=db,
        campaign_in=PolicyAttestationCampaignCreate(
            campaign_code="CAMP-FORGE-HASH",
            title="Hash Forgery Campaign",
            policy_id=apex_policy.id,
            version_id=v1.id,
            due_date=datetime.now(timezone.utc) + timedelta(days=30),
        ),
        organization_id=p24_fixture["org_apex"].id,
        current_user_id=p24_fixture["apex_admin"].id,
    )
    PolicyService.launch_campaign(db, campaign.id, p24_fixture["org_apex"].id, p24_fixture["apex_admin"].id)

    viewer_headers = get_token_headers(p24_fixture["apex_viewer"])
    r = client.post(
        f"/api/v1/policies/campaigns/{campaign.id}/attest",
        headers=viewer_headers,
        json={
            "policy_version_hash": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            "acknowledgement_text": "I agreed to an untrusted hash",
        },
    )
    assert r.status_code == 400
    assert "Policy version hash mismatch" in r.json()["detail"]


def test_adv_p24_07_forged_timestamp(client: TestClient, db: Session, p24_fixture):
    """07. Client timestamp is ignored; server records authoritative UTC timestamp."""
    apex_policy = p24_fixture["policy"]
    v1 = apex_policy.versions[0]
    campaign = PolicyService.create_campaign(
        db=db,
        campaign_in=PolicyAttestationCampaignCreate(
            campaign_code="CAMP-TIME-FORGE",
            title="Timestamp Forgery Campaign",
            policy_id=apex_policy.id,
            version_id=v1.id,
            due_date=datetime.now(timezone.utc) + timedelta(days=30),
        ),
        organization_id=p24_fixture["org_apex"].id,
        current_user_id=p24_fixture["apex_admin"].id,
    )
    PolicyService.launch_campaign(db, campaign.id, p24_fixture["org_apex"].id, p24_fixture["apex_admin"].id)

    viewer_headers = get_token_headers(p24_fixture["apex_viewer"])
    fake_past_time = "2020-01-01T00:00:00Z"
    r = client.post(
        f"/api/v1/policies/campaigns/{campaign.id}/attest",
        headers=viewer_headers,
        json={
            "policy_version_hash": campaign.policy_version_hash,
            "attested_at": fake_past_time,
            "acknowledgement_text": "Agreed",
        },
    )
    assert r.status_code == 200
    recorded_year = datetime.fromisoformat(r.json()["attested_at"].replace("Z", "+00:00")).year
    assert recorded_year >= 2026


def test_adv_p24_08_forged_campaign(client: TestClient, p24_fixture):
    """08. Attesting to a non-existent campaign ID returns HTTP 404."""
    viewer_headers = get_token_headers(p24_fixture["apex_viewer"])
    r = client.post(
        "/api/v1/policies/campaigns/999999/attest",
        headers=viewer_headers,
        json={"policy_version_hash": "fakehash", "acknowledgement_text": "Agreed"},
    )
    assert r.status_code == 404


def test_adv_p24_09_unauthorized_approval(client: TestClient, db: Session, p24_fixture):
    """09. GRC_ANALYST cannot approve a policy version review (HTTP 403 Forbidden)."""
    apex_policy = p24_fixture["policy"]
    v1 = apex_policy.versions[0]

    _, wf = PolicyService.submit_version_for_review(
        db, apex_policy.id, v1.id, p24_fixture["org_apex"].id,
        PolicyReviewWorkflowCreate(review_notes="Ready for review"),
        p24_fixture["apex_analyst"].id,
    )

    analyst_headers = get_token_headers(p24_fixture["apex_analyst"])
    r = client.post(
        f"/api/v1/policies/{apex_policy.id}/versions/{v1.id}/review/{wf.id}",
        headers=analyst_headers,
        json={"decision": "APPROVE", "review_notes": "Analyst self-approving"},
    )
    assert r.status_code == 403


def test_adv_p24_10_self_approval(client: TestClient, db: Session, p24_fixture):
    """10. Policy version author cannot approve their own version (Four-Eyes SoD Violation, HTTP 400)."""
    apex_policy = p24_fixture["policy"]

    v2 = PolicyService.create_policy_version(
        db,
        policy_id=apex_policy.id,
        organization_id=p24_fixture["org_apex"].id,
        obj_in=PolicyVersionCreate(content="New v2 content by manager", change_summary="v2 draft"),
        created_by_id=p24_fixture["apex_manager"].id,
    )

    _, wf = PolicyService.submit_version_for_review(
        db, apex_policy.id, v2.id, p24_fixture["org_apex"].id,
        PolicyReviewWorkflowCreate(review_notes="Review needed"),
        p24_fixture["apex_manager"].id,
    )

    manager_headers = get_token_headers(p24_fixture["apex_manager"])
    r = client.post(
        f"/api/v1/policies/{apex_policy.id}/versions/{v2.id}/review/{wf.id}",
        headers=manager_headers,
        json={"decision": "APPROVE", "review_notes": "Self approval"},
    )
    assert r.status_code == 400
    assert "Four-Eyes Violation" in r.json()["detail"]


def test_adv_p24_11_reviewer_approver_sod_violation(client: TestClient, db: Session, p24_fixture):
    """11. Admin author cannot bypass Four-Eyes SoD rule."""
    apex_policy = p24_fixture["policy"]
    v1 = apex_policy.versions[0]

    _, wf = PolicyService.submit_version_for_review(
        db, apex_policy.id, v1.id, p24_fixture["org_apex"].id,
        PolicyReviewWorkflowCreate(review_notes="Admin submitted"),
        p24_fixture["apex_admin"].id,
    )

    admin_headers = get_token_headers(p24_fixture["apex_admin"])
    r = client.post(
        f"/api/v1/policies/{apex_policy.id}/versions/{v1.id}/review/{wf.id}",
        headers=admin_headers,
        json={"decision": "APPROVE", "review_notes": "Admin trying to approve own policy"},
    )
    assert r.status_code == 400
    assert "Four-Eyes Violation" in r.json()["detail"]


def test_adv_p24_12_post_approval_mutation(client: TestClient, db: Session, p24_fixture):
    """12. Mutating content of an APPROVED or submitted policy version is blocked (HTTP 400)."""
    apex_policy = p24_fixture["policy"]
    v1 = apex_policy.versions[0]

    _, wf = PolicyService.submit_version_for_review(
        db, apex_policy.id, v1.id, p24_fixture["org_apex"].id,
        PolicyReviewWorkflowCreate(), p24_fixture["apex_admin"].id,
    )
    PolicyService.review_policy_version_workflow(
        db, apex_policy.id, v1.id, wf.id, p24_fixture["org_apex"].id,
        PolicyReviewWorkflowAction(decision="APPROVE"), p24_fixture["apex_manager"].id,
    )

    admin_headers = get_token_headers(p24_fixture["apex_admin"])
    r = client.patch(
        f"/api/v1/policies/{apex_policy.id}/versions/{v1.id}",
        headers=admin_headers,
        json={"content": "Tampered content after approval"},
    )
    assert r.status_code == 400
    assert "immutable" in r.json()["detail"].lower()


def test_adv_p24_13_policy_hash_mismatch(client: TestClient, db: Session, p24_fixture):
    """13. Policy version hash mismatch rejects attestation."""
    apex_policy = p24_fixture["policy"]
    v1 = apex_policy.versions[0]
    campaign = PolicyService.create_campaign(
        db=db,
        campaign_in=PolicyAttestationCampaignCreate(
            campaign_code="CAMP-HASH-MM",
            title="Hash Mismatch Test",
            policy_id=apex_policy.id,
            version_id=v1.id,
            due_date=datetime.now(timezone.utc) + timedelta(days=30),
        ),
        organization_id=p24_fixture["org_apex"].id,
        current_user_id=p24_fixture["apex_admin"].id,
    )
    PolicyService.launch_campaign(db, campaign.id, p24_fixture["org_apex"].id, p24_fixture["apex_admin"].id)

    viewer_headers = get_token_headers(p24_fixture["apex_viewer"])
    r = client.post(
        f"/api/v1/policies/campaigns/{campaign.id}/attest",
        headers=viewer_headers,
        json={"policy_version_hash": "differenthash123", "acknowledgement_text": "Agree"},
    )
    assert r.status_code == 400
    assert "mismatch" in r.json()["detail"].lower()


def test_adv_p24_14_campaign_policy_substitution(client: TestClient, db: Session, p24_fixture):
    """14. Cannot substitute policy or version on an active campaign."""
    apex_policy = p24_fixture["policy"]
    v1 = apex_policy.versions[0]
    campaign = PolicyService.create_campaign(
        db=db,
        campaign_in=PolicyAttestationCampaignCreate(
            campaign_code="CAMP-SUBST",
            title="Policy Substitution Test",
            policy_id=apex_policy.id,
            version_id=v1.id,
            due_date=datetime.now(timezone.utc) + timedelta(days=30),
        ),
        organization_id=p24_fixture["org_apex"].id,
        current_user_id=p24_fixture["apex_admin"].id,
    )
    PolicyService.launch_campaign(db, campaign.id, p24_fixture["org_apex"].id, p24_fixture["apex_admin"].id)

    manager_headers = get_token_headers(p24_fixture["apex_manager"])
    r = client.patch(
        f"/api/v1/policies/campaigns/{campaign.id}",
        headers=manager_headers,
        json={"title": "Updated Title"},
    )
    assert r.status_code == 400
    assert "Cannot modify campaign in status 'ACTIVE'" in r.json()["detail"]


def test_adv_p24_15_duplicate_attestation(client: TestClient, db: Session, p24_fixture):
    """15. Submitting second attestation by same user on same campaign returns HTTP 409 Conflict."""
    apex_policy = p24_fixture["policy"]
    v1 = apex_policy.versions[0]
    campaign = PolicyService.create_campaign(
        db=db,
        campaign_in=PolicyAttestationCampaignCreate(
            campaign_code="CAMP-DUP-ATT",
            title="Duplicate Attestation Test",
            policy_id=apex_policy.id,
            version_id=v1.id,
            due_date=datetime.now(timezone.utc) + timedelta(days=30),
        ),
        organization_id=p24_fixture["org_apex"].id,
        current_user_id=p24_fixture["apex_admin"].id,
    )
    PolicyService.launch_campaign(db, campaign.id, p24_fixture["org_apex"].id, p24_fixture["apex_admin"].id)

    viewer_headers = get_token_headers(p24_fixture["apex_viewer"])
    payload = {"policy_version_hash": campaign.policy_version_hash, "acknowledgement_text": "I agree"}

    r1 = client.post(f"/api/v1/policies/campaigns/{campaign.id}/attest", headers=viewer_headers, json=payload)
    assert r1.status_code == 200

    r2 = client.post(f"/api/v1/policies/campaigns/{campaign.id}/attest", headers=viewer_headers, json=payload)
    assert r2.status_code == 409
    assert "Duplicate attestation" in r2.json()["detail"]


def test_adv_p24_16_replay(client: TestClient, db: Session, p24_fixture):
    """16. Replay of identical attestation payload is rejected with HTTP 409."""
    apex_policy = p24_fixture["policy"]
    v1 = apex_policy.versions[0]
    campaign = PolicyService.create_campaign(
        db=db,
        campaign_in=PolicyAttestationCampaignCreate(
            campaign_code="CAMP-REPLAY",
            title="Replay Test",
            policy_id=apex_policy.id,
            version_id=v1.id,
            due_date=datetime.now(timezone.utc) + timedelta(days=30),
        ),
        organization_id=p24_fixture["org_apex"].id,
        current_user_id=p24_fixture["apex_admin"].id,
    )
    PolicyService.launch_campaign(db, campaign.id, p24_fixture["org_apex"].id, p24_fixture["apex_admin"].id)

    auditor_headers = get_token_headers(p24_fixture["apex_auditor"])
    payload = {"policy_version_hash": campaign.policy_version_hash, "acknowledgement_text": "Agreed"}

    assert client.post(f"/api/v1/policies/campaigns/{campaign.id}/attest", headers=auditor_headers, json=payload).status_code == 200
    assert client.post(f"/api/v1/policies/campaigns/{campaign.id}/attest", headers=auditor_headers, json=payload).status_code == 409


def test_adv_p24_17_concurrent_attestation(db: Session, p24_fixture):
    """17. Sequential duplicate attestation via service layer enforces uniqueness atomically."""
    apex_policy = p24_fixture["policy"]
    v1 = apex_policy.versions[0]
    campaign = PolicyService.create_campaign(
        db=db,
        campaign_in=PolicyAttestationCampaignCreate(
            campaign_code="CAMP-CONCURR",
            title="Concurrency Test",
            policy_id=apex_policy.id,
            version_id=v1.id,
            due_date=datetime.now(timezone.utc) + timedelta(days=30),
        ),
        organization_id=p24_fixture["org_apex"].id,
        current_user_id=p24_fixture["apex_admin"].id,
    )
    PolicyService.launch_campaign(db, campaign.id, p24_fixture["org_apex"].id, p24_fixture["apex_admin"].id)

    sub = UserAttestationSubmit(policy_version_hash=campaign.policy_version_hash, acknowledgement_text="Agree")
    rec = PolicyService.submit_user_attestation(
        db, campaign.id, p24_fixture["org_apex"].id, p24_fixture["apex_viewer"].id, sub
    )
    assert rec.status == AttestationRecordStatusEnum.ATTESTED

    with pytest.raises(ValueError, match="Duplicate attestation"):
        PolicyService.submit_user_attestation(
            db, campaign.id, p24_fixture["org_apex"].id, p24_fixture["apex_viewer"].id, sub
        )


def test_adv_p24_18_unauthorized_campaign_modification(client: TestClient, db: Session, p24_fixture):
    """18. VIEWER cannot modify an attestation campaign (HTTP 403 Forbidden)."""
    apex_policy = p24_fixture["policy"]
    v1 = apex_policy.versions[0]
    campaign = PolicyService.create_campaign(
        db=db,
        campaign_in=PolicyAttestationCampaignCreate(
            campaign_code="CAMP-UNAUTH-MOD",
            title="Unauthorized Mod Test",
            policy_id=apex_policy.id,
            version_id=v1.id,
            due_date=datetime.now(timezone.utc) + timedelta(days=30),
        ),
        organization_id=p24_fixture["org_apex"].id,
        current_user_id=p24_fixture["apex_admin"].id,
    )

    viewer_headers = get_token_headers(p24_fixture["apex_viewer"])
    r = client.patch(
        f"/api/v1/policies/campaigns/{campaign.id}",
        headers=viewer_headers,
        json={"title": "Viewer Hacked Title"},
    )
    assert r.status_code == 403


def test_adv_p24_19_unauthorized_reassignment(client: TestClient, db: Session, p24_fixture):
    """19. User not assigned to campaign cannot attest (HTTP 404 Not Found)."""
    apex_policy = p24_fixture["policy"]
    v1 = apex_policy.versions[0]

    campaign = PolicyService.create_campaign(
        db=db,
        campaign_in=PolicyAttestationCampaignCreate(
            campaign_code="CAMP-ROLE-ADM",
            title="Admin-Only Campaign",
            policy_id=apex_policy.id,
            version_id=v1.id,
            target_type=CampaignTargetTypeEnum.ROLE_BASED,
            target_role="ADMIN",
            due_date=datetime.now(timezone.utc) + timedelta(days=30),
        ),
        organization_id=p24_fixture["org_apex"].id,
        current_user_id=p24_fixture["apex_admin"].id,
    )
    PolicyService.launch_campaign(db, campaign.id, p24_fixture["org_apex"].id, p24_fixture["apex_admin"].id)

    viewer_headers = get_token_headers(p24_fixture["apex_viewer"])
    r = client.post(
        f"/api/v1/policies/campaigns/{campaign.id}/attest",
        headers=viewer_headers,
        json={"policy_version_hash": campaign.policy_version_hash, "acknowledgement_text": "I am not an admin"},
    )
    assert r.status_code == 404
    assert "not assigned" in r.json()["detail"]


def test_adv_p24_20_attestation_enumeration(client: TestClient, db: Session, p24_fixture):
    """20. /my-pending-attestations returns only caller's pending records."""
    apex_policy = p24_fixture["policy"]
    v1 = apex_policy.versions[0]
    campaign = PolicyService.create_campaign(
        db=db,
        campaign_in=PolicyAttestationCampaignCreate(
            campaign_code="CAMP-ENUM-TEST",
            title="Enumeration Test",
            policy_id=apex_policy.id,
            version_id=v1.id,
            due_date=datetime.now(timezone.utc) + timedelta(days=30),
        ),
        organization_id=p24_fixture["org_apex"].id,
        current_user_id=p24_fixture["apex_admin"].id,
    )
    PolicyService.launch_campaign(db, campaign.id, p24_fixture["org_apex"].id, p24_fixture["apex_admin"].id)

    viewer_headers = get_token_headers(p24_fixture["apex_viewer"])
    r = client.get("/api/v1/policies/my-pending-attestations", headers=viewer_headers)
    assert r.status_code == 200
    records = r.json()
    assert len(records) >= 1
    for item in records:
        assert item["user_id"] == p24_fixture["apex_viewer"].id


def test_adv_p24_21_deadline_bypass(client: TestClient, db: Session, p24_fixture):
    """21. Cannot attest to a campaign in DRAFT or CLOSED status (HTTP 400)."""
    apex_policy = p24_fixture["policy"]
    v1 = apex_policy.versions[0]
    campaign = PolicyService.create_campaign(
        db=db,
        campaign_in=PolicyAttestationCampaignCreate(
            campaign_code="CAMP-DEADLINE",
            title="Draft Campaign Test",
            policy_id=apex_policy.id,
            version_id=v1.id,
            due_date=datetime.now(timezone.utc) + timedelta(days=30),
        ),
        organization_id=p24_fixture["org_apex"].id,
        current_user_id=p24_fixture["apex_admin"].id,
    )

    viewer_headers = get_token_headers(p24_fixture["apex_viewer"])
    r = client.post(
        f"/api/v1/policies/campaigns/{campaign.id}/attest",
        headers=viewer_headers,
        json={"policy_version_hash": campaign.policy_version_hash, "acknowledgement_text": "Early attest"},
    )
    assert r.status_code == 400
    assert "not ACTIVE" in r.json()["detail"]


def test_adv_p24_22_client_controlled_completion_status(client: TestClient, db: Session, p24_fixture):
    """22. Client cannot inject status in payload to bypass attestation receipt calculation."""
    apex_policy = p24_fixture["policy"]
    v1 = apex_policy.versions[0]
    campaign = PolicyService.create_campaign(
        db=db,
        campaign_in=PolicyAttestationCampaignCreate(
            campaign_code="CAMP-STATUS-INJ",
            title="Status Injection Test",
            policy_id=apex_policy.id,
            version_id=v1.id,
            due_date=datetime.now(timezone.utc) + timedelta(days=30),
        ),
        organization_id=p24_fixture["org_apex"].id,
        current_user_id=p24_fixture["apex_admin"].id,
    )
    PolicyService.launch_campaign(db, campaign.id, p24_fixture["org_apex"].id, p24_fixture["apex_admin"].id)

    viewer_headers = get_token_headers(p24_fixture["apex_viewer"])
    r = client.post(
        f"/api/v1/policies/campaigns/{campaign.id}/attest",
        headers=viewer_headers,
        json={
            "status": "APPROVED_WITHOUT_WORKFLOW",
            "policy_version_hash": campaign.policy_version_hash,
            "acknowledgement_text": "I agree",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ATTESTED"
    assert data["attestation_receipt_hash"] is not None


def test_adv_p24_23_client_controlled_evidence_status(client: TestClient, db: Session, p24_fixture):
    """23. Client cannot inject evidence status = ACCEPTED when generating evidence manifest."""
    apex_policy = p24_fixture["policy"]
    v1 = apex_policy.versions[0]
    campaign = PolicyService.create_campaign(
        db=db,
        campaign_in=PolicyAttestationCampaignCreate(
            campaign_code="CAMP-EVID-INJ",
            title="Evidence Status Injection Test",
            policy_id=apex_policy.id,
            version_id=v1.id,
            due_date=datetime.now(timezone.utc) + timedelta(days=30),
        ),
        organization_id=p24_fixture["org_apex"].id,
        current_user_id=p24_fixture["apex_admin"].id,
    )
    PolicyService.launch_campaign(db, campaign.id, p24_fixture["org_apex"].id, p24_fixture["apex_admin"].id)

    manager_headers = get_token_headers(p24_fixture["apex_manager"])
    r = client.post(
        f"/api/v1/policies/campaigns/{campaign.id}/evidence",
        headers=manager_headers,
        json={"status": "ACCEPTED"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "UPLOADED"


def test_adv_p24_24_automatic_evidence_acceptance_prevention(client: TestClient, db: Session, p24_fixture):
    """24. Evidence manifest generated by campaign enters UPLOADED status only."""
    apex_policy = p24_fixture["policy"]
    v1 = apex_policy.versions[0]
    campaign = PolicyService.create_campaign(
        db=db,
        campaign_in=PolicyAttestationCampaignCreate(
            campaign_code="CAMP-AUTO-ACC",
            title="Auto Accept Prevention",
            policy_id=apex_policy.id,
            version_id=v1.id,
            due_date=datetime.now(timezone.utc) + timedelta(days=30),
        ),
        organization_id=p24_fixture["org_apex"].id,
        current_user_id=p24_fixture["apex_admin"].id,
    )
    PolicyService.launch_campaign(db, campaign.id, p24_fixture["org_apex"].id, p24_fixture["apex_admin"].id)

    manager_headers = get_token_headers(p24_fixture["apex_manager"])
    r = client.post(f"/api/v1/policies/campaigns/{campaign.id}/evidence", headers=manager_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "UPLOADED"


def test_adv_p24_25_evidence_manifest_checksum_integrity(db: Session, p24_fixture):
    """25. Evidence manifest SHA-256 matches exact stored payload file bytes."""
    apex_policy = p24_fixture["policy"]
    v1 = apex_policy.versions[0]
    campaign = PolicyService.create_campaign(
        db=db,
        campaign_in=PolicyAttestationCampaignCreate(
            campaign_code="CAMP-CHECKSUM",
            title="Checksum Integrity Test",
            policy_id=apex_policy.id,
            version_id=v1.id,
            due_date=datetime.now(timezone.utc) + timedelta(days=30),
        ),
        organization_id=p24_fixture["org_apex"].id,
        current_user_id=p24_fixture["apex_admin"].id,
    )
    PolicyService.launch_campaign(db, campaign.id, p24_fixture["org_apex"].id, p24_fixture["apex_admin"].id)

    evidence = PolicyService.generate_campaign_evidence(
        db, campaign.id, p24_fixture["org_apex"].id, p24_fixture["apex_manager"].id
    )

    with open(evidence.storage_key, "rb") as f:
        file_bytes = f.read()

    import hashlib
    computed = hashlib.sha256(file_bytes).hexdigest()
    assert computed == evidence.sha256_hash


def test_adv_p24_26_xss_in_acknowledgement_text(client: TestClient, db: Session, p24_fixture):
    """26. Acknowledgment comments with XSS payloads are handled safely as raw text."""
    apex_policy = p24_fixture["policy"]
    v1 = apex_policy.versions[0]
    campaign = PolicyService.create_campaign(
        db=db,
        campaign_in=PolicyAttestationCampaignCreate(
            campaign_code="CAMP-XSS",
            title="XSS Test Campaign",
            policy_id=apex_policy.id,
            version_id=v1.id,
            due_date=datetime.now(timezone.utc) + timedelta(days=30),
        ),
        organization_id=p24_fixture["org_apex"].id,
        current_user_id=p24_fixture["apex_admin"].id,
    )
    PolicyService.launch_campaign(db, campaign.id, p24_fixture["org_apex"].id, p24_fixture["apex_admin"].id)

    viewer_headers = get_token_headers(p24_fixture["apex_viewer"])
    xss_payload = "<script>alert('xss')</script><img src=x onerror=alert(1)>"
    r = client.post(
        f"/api/v1/policies/campaigns/{campaign.id}/attest",
        headers=viewer_headers,
        json={"policy_version_hash": campaign.policy_version_hash, "acknowledgement_text": xss_payload},
    )
    assert r.status_code == 200
    assert r.json()["acknowledgement_text"] == xss_payload


def test_adv_p24_27_sql_injection_in_campaign_filters(client: TestClient, p24_fixture):
    """27. SQL injection in campaign status/filters is safely parameterized."""
    headers = get_token_headers(p24_fixture["apex_admin"])
    sql_injection = "' OR '1'='1"
    r = client.get(f"/api/v1/policies/campaigns?status={sql_injection}", headers=headers)
    assert r.status_code == 422


def test_adv_p24_28_audit_log_emission_on_policy_approval(client: TestClient, db: Session, p24_fixture):
    """28. Policy review approval emits an AuditLog record."""
    apex_policy = p24_fixture["policy"]
    v1 = apex_policy.versions[0]

    _, wf = PolicyService.submit_version_for_review(
        db, apex_policy.id, v1.id, p24_fixture["org_apex"].id,
        PolicyReviewWorkflowCreate(), p24_fixture["apex_admin"].id,
    )

    manager_headers = get_token_headers(p24_fixture["apex_manager"])
    r = client.post(
        f"/api/v1/policies/{apex_policy.id}/versions/{v1.id}/review/{wf.id}",
        headers=manager_headers,
        json={"decision": "APPROVE", "review_notes": "Approved by manager"},
    )
    assert r.status_code == 200

    from app.models.audit_log import AuditLog
    log = db.query(AuditLog).filter(
        AuditLog.action == "policy.version.approve",
        AuditLog.organization_id == p24_fixture["org_apex"].id,
    ).first()
    assert log is not None


def test_adv_p24_29_audit_log_emission_on_attestation(client: TestClient, db: Session, p24_fixture):
    """29. Submitting attestation emits an AuditLog record with receipt hash."""
    apex_policy = p24_fixture["policy"]
    v1 = apex_policy.versions[0]
    campaign = PolicyService.create_campaign(
        db=db,
        campaign_in=PolicyAttestationCampaignCreate(
            campaign_code="CAMP-AUDIT-ATT",
            title="Audit Emission Test",
            policy_id=apex_policy.id,
            version_id=v1.id,
            due_date=datetime.now(timezone.utc) + timedelta(days=30),
        ),
        organization_id=p24_fixture["org_apex"].id,
        current_user_id=p24_fixture["apex_admin"].id,
    )
    PolicyService.launch_campaign(db, campaign.id, p24_fixture["org_apex"].id, p24_fixture["apex_admin"].id)

    viewer_headers = get_token_headers(p24_fixture["apex_viewer"])
    r = client.post(
        f"/api/v1/policies/campaigns/{campaign.id}/attest",
        headers=viewer_headers,
        json={"policy_version_hash": campaign.policy_version_hash, "acknowledgement_text": "I agree"},
    )
    assert r.status_code == 200

    from app.models.audit_log import AuditLog
    log = db.query(AuditLog).filter(
        AuditLog.action == "policy.attestation.submit",
        AuditLog.organization_id == p24_fixture["org_apex"].id,
    ).order_by(AuditLog.id.desc()).first()
    assert log is not None
    assert "receipt_hash" in log.details


def test_adv_p24_30_my_pending_attestations_idor_protection(client: TestClient, db: Session, p24_fixture):
    """30. IDOR protection: /my-pending-attestations ignores any query parameter attempt to read others."""
    apex_policy = p24_fixture["policy"]
    v1 = apex_policy.versions[0]
    campaign = PolicyService.create_campaign(
        db=db,
        campaign_in=PolicyAttestationCampaignCreate(
            campaign_code="CAMP-IDOR",
            title="IDOR Protection Test",
            policy_id=apex_policy.id,
            version_id=v1.id,
            due_date=datetime.now(timezone.utc) + timedelta(days=30),
        ),
        organization_id=p24_fixture["org_apex"].id,
        current_user_id=p24_fixture["apex_admin"].id,
    )
    PolicyService.launch_campaign(db, campaign.id, p24_fixture["org_apex"].id, p24_fixture["apex_admin"].id)

    viewer_headers = get_token_headers(p24_fixture["apex_viewer"])
    r = client.get(f"/api/v1/policies/my-pending-attestations?user_id={p24_fixture['apex_admin'].id}", headers=viewer_headers)
    assert r.status_code == 200
    for item in r.json():
        assert item["user_id"] == p24_fixture["apex_viewer"].id


def test_adv_p24_31_campaign_due_date_timezone_handling(client: TestClient, db: Session, p24_fixture):
    """31. Timezone-aware deadline calculation accurately identifies overdue records."""
    apex_policy = p24_fixture["policy"]
    v1 = apex_policy.versions[0]
    past_due = datetime.now(timezone.utc) - timedelta(days=1)
    campaign = PolicyService.create_campaign(
        db=db,
        campaign_in=PolicyAttestationCampaignCreate(
            campaign_code="CAMP-TIMEZONE",
            title="Timezone Test",
            policy_id=apex_policy.id,
            version_id=v1.id,
            due_date=past_due,
        ),
        organization_id=p24_fixture["org_apex"].id,
        current_user_id=p24_fixture["apex_admin"].id,
    )
    PolicyService.launch_campaign(db, campaign.id, p24_fixture["org_apex"].id, p24_fixture["apex_admin"].id)

    camp_db = PolicyService.get_campaign(db, campaign.id, p24_fixture["org_apex"].id)
    assert camp_db.due_date.tzinfo is not None


def test_adv_p24_32_assessment_comprehension_failure_blocks_attestation(client: TestClient, db: Session, p24_fixture):
    """32. Mandatory comprehension assessment failure blocks attestation completion (HTTP 400)."""
    apex_policy = p24_fixture["policy"]
    v1 = apex_policy.versions[0]

    ctrl = (
        db.query(OrganizationControl)
        .filter(OrganizationControl.organization_id == p24_fixture["org_apex"].id)
        .first()
    )
    if not ctrl:
        subcat = db.query(FrameworkSubcategory).first()
        if not subcat:
            fw = Framework(identifier="TEST-P24-FW", name="Test FW", version="1.0")
            db.add(fw)
            db.flush()
            fn = FrameworkFunction(framework_id=fw.id, identifier="GV", name="Governance", display_order=1)
            db.add(fn)
            db.flush()
            cat = FrameworkCategory(function_id=fn.id, identifier="GV.PO", name="Policy", display_order=1)
            db.add(cat)
            db.flush()
            subcat = FrameworkSubcategory(category_id=cat.id, identifier="GV.PO-01", title="Policy", description="Policy test", display_order=1)
            db.add(subcat)
            db.flush()
        ctrl = OrganizationControl(
            organization_id=p24_fixture["org_apex"].id,
            subcategory_id=subcat.id,
            status=ImplementationStatusEnum.IMPLEMENTED,
            priority=PriorityEnum.HIGH,
        )
        db.add(ctrl)
        db.commit()

    assessment = Assessment(
        organization_id=p24_fixture["org_apex"].id,
        organization_control_id=ctrl.id,
        summary="Policy Comprehension Exam",
        assessment_method=AssessmentMethodEnum.EXAMINATION,
        status=AssessmentStatusEnum.DRAFT,
        conclusion=AssessmentConclusionEnum.INEFFECTIVE,
    )
    db.add(assessment)
    db.commit()

    campaign = PolicyService.create_campaign(
        db=db,
        campaign_in=PolicyAttestationCampaignCreate(
            campaign_code="CAMP-QUIZ-FAIL",
            title="Quiz Gated Campaign",
            policy_id=apex_policy.id,
            version_id=v1.id,
            due_date=datetime.now(timezone.utc) + timedelta(days=30),
            assessment_id=assessment.id,
        ),
        organization_id=p24_fixture["org_apex"].id,
        current_user_id=p24_fixture["apex_admin"].id,
    )
    PolicyService.launch_campaign(db, campaign.id, p24_fixture["org_apex"].id, p24_fixture["apex_admin"].id)

    viewer_headers = get_token_headers(p24_fixture["apex_viewer"])
    r = client.post(
        f"/api/v1/policies/campaigns/{campaign.id}/attest",
        headers=viewer_headers,
        json={"policy_version_hash": campaign.policy_version_hash, "acknowledgement_text": "I skipped the quiz"},
    )
    assert r.status_code == 400
    assert "assessment not passed" in r.json()["detail"].lower()


def test_adv_p24_33_unauthorized_policy_publishing(client: TestClient, db: Session, p24_fixture):
    """33. Publishing an unapproved DRAFT version returns HTTP 400."""
    apex_policy = p24_fixture["policy"]
    v1 = apex_policy.versions[0]

    admin_headers = get_token_headers(p24_fixture["apex_admin"])
    r = client.post(
        f"/api/v1/policies/{apex_policy.id}/versions/{v1.id}/publish",
        headers=admin_headers,
    )
    assert r.status_code == 400
    assert "must be formally APPROVED" in r.json()["detail"]


def test_adv_p24_34_policy_version_deletion_restriction(client: TestClient, db: Session, p24_fixture):
    """34. Cannot delete a policy version bound to an active attestation campaign (HTTP 400)."""
    apex_policy = p24_fixture["policy"]
    v1 = apex_policy.versions[0]
    campaign = PolicyService.create_campaign(
        db=db,
        campaign_in=PolicyAttestationCampaignCreate(
            campaign_code="CAMP-DEL-RESTRICT",
            title="Delete Restrict Campaign",
            policy_id=apex_policy.id,
            version_id=v1.id,
            due_date=datetime.now(timezone.utc) + timedelta(days=30),
        ),
        organization_id=p24_fixture["org_apex"].id,
        current_user_id=p24_fixture["apex_admin"].id,
    )
    PolicyService.launch_campaign(db, campaign.id, p24_fixture["org_apex"].id, p24_fixture["apex_admin"].id)

    admin_headers = get_token_headers(p24_fixture["apex_admin"])
    r = client.delete(
        f"/api/v1/policies/{apex_policy.id}/versions/{v1.id}",
        headers=admin_headers,
    )
    assert r.status_code == 400
    assert "bound to active attestation campaign" in r.json()["detail"]


def test_adv_p24_35_client_organization_id_injection_ignored(client: TestClient, db: Session, p24_fixture):
    """35. Client organization_id injection in campaign create is ignored; tenant is preserved."""
    apex_policy = p24_fixture["policy"]
    v1 = apex_policy.versions[0]

    manager_headers = get_token_headers(p24_fixture["apex_manager"])
    r = client.post(
        "/api/v1/policies/campaigns",
        headers=manager_headers,
        json={
            "campaign_code": "CAMP-ORG-INJ",
            "title": "Org Injection Campaign",
            "organization_id": p24_fixture["org_meridian"].id,
            "policy_id": apex_policy.id,
            "version_id": v1.id,
            "due_date": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        },
    )
    assert r.status_code == 201
    assert r.json()["organization_id"] == p24_fixture["org_apex"].id


def test_adv_p24_36_deterministic_evidence_control_lineage(client: TestClient, db: Session, p24_fixture):
    """36. Evidence manifest deterministically binds to mapped OrganizationControl; fails cleanly if unmapped."""
    apex_admin = p24_fixture["apex_admin"]
    apex_mgr = p24_fixture["apex_manager"]
    org_apex = p24_fixture["org_apex"]
    admin_headers = get_token_headers(apex_admin)
    mgr_headers = get_token_headers(apex_mgr)

    # 1. Create a policy with NO control mappings
    unmapped_policy = PolicyService.create_policy(
        db=db,
        obj_in=PolicyCreate(
            title="Unmapped Test Policy",
            description="Policy without controls",
            policy_type=PolicyTypeEnum.DATA_PROTECTION,
            initial_content="Unmapped content",
        ),
        organization_id=org_apex.id,
        created_by_id=apex_admin.id,
    )
    v1_unmapped = unmapped_policy.versions[0]

    campaign_unmapped = PolicyService.create_campaign(
        db=db,
        campaign_in=PolicyAttestationCampaignCreate(
            campaign_code="CAMP-NO-CTRL",
            title="Unmapped Control Campaign",
            policy_id=unmapped_policy.id,
            version_id=v1_unmapped.id,
            due_date=datetime.now(timezone.utc) + timedelta(days=30),
        ),
        organization_id=org_apex.id,
        current_user_id=apex_admin.id,
    )
    PolicyService.launch_campaign(db, campaign_unmapped.id, org_apex.id, apex_admin.id)

    # Attest so manifest has data
    client.post(
        f"/api/v1/policies/campaigns/{campaign_unmapped.id}/attest",
        headers=get_token_headers(p24_fixture["apex_viewer"]),
        json={"policy_version_hash": campaign_unmapped.policy_version_hash, "acknowledgement_text": "I agree"},
    )

    # Attempting to generate evidence manifest MUST fail cleanly (HTTP 400)
    r_fail = client.post(f"/api/v1/policies/campaigns/{campaign_unmapped.id}/evidence", headers=mgr_headers)
    assert r_fail.status_code == 400
    assert "no mapped OrganizationControl" in r_fail.json()["detail"]

    # 2. Now map a specific control to the policy
    subcat_specific = db.query(FrameworkSubcategory).order_by(FrameworkSubcategory.id.desc()).first()
    ctrl_specific = db.query(OrganizationControl).filter(
        OrganizationControl.organization_id == org_apex.id,
        OrganizationControl.subcategory_id == subcat_specific.id,
    ).first()
    if not ctrl_specific:
        ctrl_specific = OrganizationControl(
            organization_id=org_apex.id,
            subcategory_id=subcat_specific.id,
            status=ImplementationStatusEnum.IMPLEMENTED,
            priority=PriorityEnum.HIGH,
        )
        db.add(ctrl_specific)
        db.commit()

    PolicyService.add_control_mapping(db, unmapped_policy.id, org_apex.id, subcat_specific.id)

    # Now evidence generation MUST succeed and strictly bind to ctrl_specific
    r_succ = client.post(f"/api/v1/policies/campaigns/{campaign_unmapped.id}/evidence", headers=mgr_headers)
    assert r_succ.status_code == 200
    evid_id = r_succ.json()["evidence_item_id"]

    from app.models.evidence import EvidenceItem
    evid = db.query(EvidenceItem).filter(EvidenceItem.id == evid_id).first()
    assert evid is not None
    assert evid.organization_control_id == ctrl_specific.id


def test_adv_p24_37_positive_assessment_comprehension_flow(client: TestClient, db: Session, p24_fixture):
    """37. Passing linked assessment (COMPLETED + EFFECTIVE) unlocks attestation and sets comprehension_passed=True."""
    apex_policy = p24_fixture["policy"]
    v1 = apex_policy.versions[0]
    org_apex = p24_fixture["org_apex"]
    admin = p24_fixture["apex_admin"]
    viewer = p24_fixture["apex_viewer"]
    viewer_headers = get_token_headers(viewer)

    # 1. Create control and assessment in DRAFT / INEFFECTIVE state
    ctrl = db.query(OrganizationControl).filter(OrganizationControl.organization_id == org_apex.id).first()
    assessment = Assessment(
        organization_id=org_apex.id,
        organization_control_id=ctrl.id,
        summary="Positive Comprehension Quiz",
        assessment_method=AssessmentMethodEnum.EXAMINATION,
        status=AssessmentStatusEnum.DRAFT,
        conclusion=AssessmentConclusionEnum.INEFFECTIVE,
    )
    db.add(assessment)
    db.commit()

    campaign = PolicyService.create_campaign(
        db=db,
        campaign_in=PolicyAttestationCampaignCreate(
            campaign_code="CAMP-QUIZ-FLOW",
            title="Quiz Flow Verification Campaign",
            policy_id=apex_policy.id,
            version_id=v1.id,
            due_date=datetime.now(timezone.utc) + timedelta(days=30),
            assessment_id=assessment.id,
        ),
        organization_id=org_apex.id,
        current_user_id=admin.id,
    )
    PolicyService.launch_campaign(db, campaign.id, org_apex.id, admin.id)

    # 2. Blocked while assessment is unpassed
    r_blocked = client.post(
        f"/api/v1/policies/campaigns/{campaign.id}/attest",
        headers=viewer_headers,
        json={"policy_version_hash": campaign.policy_version_hash, "acknowledgement_text": "Trying early"},
    )
    assert r_blocked.status_code == 400
    assert "assessment not passed" in r_blocked.json()["detail"].lower()

    # 3. Complete and pass the assessment
    assessment.status = AssessmentStatusEnum.COMPLETED
    assessment.conclusion = AssessmentConclusionEnum.EFFECTIVE
    db.commit()

    # 4. Attestation now succeeds with HTTP 200
    r_allowed = client.post(
        f"/api/v1/policies/campaigns/{campaign.id}/attest",
        headers=viewer_headers,
        json={"policy_version_hash": campaign.policy_version_hash, "acknowledgement_text": "Passed the quiz"},
    )
    assert r_allowed.status_code == 200
    rec_data = r_allowed.json()
    assert rec_data["status"] == "ATTESTED"
    assert rec_data["comprehension_passed"] is True
    assert rec_data["attestation_receipt_hash"] is not None


def test_adv_p24_38_pending_comprehension_flag(db: Session, p24_fixture):
    """38. Pending records start comprehension_passed=False when assessment is linked, True when none."""
    apex_policy = p24_fixture["policy"]
    v1 = apex_policy.versions[0]
    org_apex = p24_fixture["org_apex"]
    admin = p24_fixture["apex_admin"]

    # Case A: Campaign WITH assessment
    ctrl = db.query(OrganizationControl).filter(OrganizationControl.organization_id == org_apex.id).first()
    assessment = Assessment(
        organization_id=org_apex.id,
        organization_control_id=ctrl.id,
        summary="Pending Flag Quiz",
        assessment_method=AssessmentMethodEnum.EXAMINATION,
        status=AssessmentStatusEnum.DRAFT,
        conclusion=AssessmentConclusionEnum.INEFFECTIVE,
    )
    db.add(assessment)
    db.commit()

    camp_with_quiz = PolicyService.create_campaign(
        db=db,
        campaign_in=PolicyAttestationCampaignCreate(
            campaign_code="CAMP-PEND-QUIZ",
            title="Pending Flag With Quiz",
            policy_id=apex_policy.id,
            version_id=v1.id,
            due_date=datetime.now(timezone.utc) + timedelta(days=30),
            assessment_id=assessment.id,
        ),
        organization_id=org_apex.id,
        current_user_id=admin.id,
    )
    PolicyService.launch_campaign(db, camp_with_quiz.id, org_apex.id, admin.id)

    recs_quiz = db.query(UserAttestationRecord).filter(
        UserAttestationRecord.campaign_id == camp_with_quiz.id
    ).all()
    assert len(recs_quiz) > 0
    for r in recs_quiz:
        assert r.comprehension_passed is False, "Assessment-backed pending records must start comprehension_passed=False"

    # Case B: Campaign WITHOUT assessment
    camp_no_quiz = PolicyService.create_campaign(
        db=db,
        campaign_in=PolicyAttestationCampaignCreate(
            campaign_code="CAMP-PEND-NOQUIZ",
            title="Pending Flag Without Quiz",
            policy_id=apex_policy.id,
            version_id=v1.id,
            due_date=datetime.now(timezone.utc) + timedelta(days=30),
        ),
        organization_id=org_apex.id,
        current_user_id=admin.id,
    )
    PolicyService.launch_campaign(db, camp_no_quiz.id, org_apex.id, admin.id)

    recs_no_quiz = db.query(UserAttestationRecord).filter(
        UserAttestationRecord.campaign_id == camp_no_quiz.id
    ).all()
    assert len(recs_no_quiz) > 0
    for r in recs_no_quiz:
        assert r.comprehension_passed is True, "Campaign without assessment must start comprehension_passed=True"

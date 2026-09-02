import pytest
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.identity_governance import (
    AccessCertificationCampaign,
    AccessCertificationItem,
    AssignmentTypeEnum,
    CampaignStatusEnum,
    CampaignTypeEnum,
    CertificationDecisionEnum,
    EmploymentStatusEnum,
    GovernedIdentity,
    IdentityEntitlement,
    IdentityEntitlementAssignment,
    IdentityRiskBandEnum,
    IdentityTypeEnum,
    JITAccessRequest,
    JITApprovalStatusEnum,
    SoDConflictPolicy,
    SoDConflictViolation,
    SoDPolicySeverityEnum,
    SoDViolationStatusEnum,
    SystemTypeEnum,
    TrustLevelEnum,
    ZeroTrustAssessment,
)
from app.models.organization import Organization
from app.models.user import User, RoleEnum
from app.schemas.identity_governance import (
    AccessCertificationCampaignCreate,
    AccessCertificationItemReview,
    EntitlementAssignmentCreate,
    GovernedIdentityCreate,
    IdentityEntitlementCreate,
    JITAccessRequestCreate,
    JITAccessReviewRequest,
    SoDConflictPolicyCreate,
    ZeroTrustAssessmentCreate,
)
from app.services.identity_governance_service import IdentityGovernanceService


@pytest.fixture
def org_and_users(db: Session):
    ts = datetime.now().timestamp()
    org = Organization(name=f"Identity Test Org {ts}", slug=f"identity-test-org-{ts}")
    db.add(org)
    db.commit()
    db.refresh(org)

    admin = User(
        email=f"id_admin_{datetime.now().timestamp()}@example.com",
        hashed_password="hashed_pwd",
        full_name="Identity Admin",
        role=RoleEnum.ADMIN,
        organization_id=org.id,
        is_active=True,
    )
    user2 = User(
        email=f"id_user2_{datetime.now().timestamp()}@example.com",
        hashed_password="hashed_pwd",
        full_name="Identity Reviewer",
        role=RoleEnum.MANAGER,
        organization_id=org.id,
        is_active=True,
    )
    db.add(admin)
    db.add(user2)
    db.commit()
    db.refresh(admin)
    db.refresh(user2)
    return org, admin, user2


def test_identity_risk_score_calculation():
    """Test deterministic Identity Risk Score calculation."""
    e1 = IdentityEntitlement(risk_weight=2.0)  # 10.0
    e2 = IdentityEntitlement(risk_weight=4.0)  # 20.0

    # 30.0 (entitlements) + 30.0 (privileged) - 20.0 (MFA) + 0.0 (No SoD) = 40.0
    score, band = IdentityGovernanceService.calculate_identity_risk_score(
        entitlements=[e1, e2],
        is_privileged=True,
        mfa_enabled=True,
        has_sod_violation=False,
    )
    assert score == 40.00
    assert band == IdentityRiskBandEnum.MODERATE


def test_zero_trust_assurance_formula():
    """Test Zero Trust score calculation and trust level categorization."""
    score, level, bd = IdentityGovernanceService.calculate_zero_trust_assurance(
        device_health=100.0,
        auth_strength=100.0,
        context_risk=0.0,
        anomaly_score=0.0,
    )
    assert score == 100.00
    assert level == TrustLevelEnum.HIGH_TRUST

    score_untrusted, level_untrusted, _ = IdentityGovernanceService.calculate_zero_trust_assurance(
        device_health=10.0,
        auth_strength=20.0,
        context_risk=90.0,
        anomaly_score=80.0,
    )
    # (20 * 0.35) + (10 * 0.30) + (10 * 0.20) + (20 * 0.15) = 7 + 3 + 2 + 3 = 15.0
    assert score_untrusted == 15.00
    assert level_untrusted == TrustLevelEnum.UNTRUSTED


def test_sod_conflict_detection_on_assignment(db: Session, org_and_users):
    """Assigning toxic combinations triggers automatic SoD violation record creation."""
    org, admin, _ = org_and_users

    # Create 2 entitlements
    e1 = IdentityGovernanceService.create_entitlement(
        db,
        org.id,
        admin.id,
        IdentityEntitlementCreate(
            entitlement_code="ENT-AP-CREATE",
            name="Create Accounts Payable Vendor",
            system_type=SystemTypeEnum.SAAS_APPLICATION,
            resource_name="ERP System",
            permission_scope="AP_Vendor_Write",
        ),
    )
    e2 = IdentityGovernanceService.create_entitlement(
        db,
        org.id,
        admin.id,
        IdentityEntitlementCreate(
            entitlement_code="ENT-AP-DISBURSE",
            name="Disburse Accounts Payable Payments",
            system_type=SystemTypeEnum.SAAS_APPLICATION,
            resource_name="ERP System",
            permission_scope="AP_Payment_Execute",
        ),
    )

    # Configure SoD policy
    policy = IdentityGovernanceService.create_sod_policy(
        db,
        org.id,
        admin.id,
        SoDConflictPolicyCreate(
            policy_code="SOD-POL-001",
            name="AP Vendor Creation vs Payment Disbursement",
            entitlement_a_id=e1.id,
            entitlement_b_id=e2.id,
            severity=SoDPolicySeverityEnum.CRITICAL,
        ),
    )

    # Create identity
    ident = IdentityGovernanceService.create_identity(
        db,
        org.id,
        admin.id,
        GovernedIdentityCreate(
            identity_code="ID-FIN-001",
            email="fin.clerk@example.com",
            full_name="Finance Clerk",
        ),
    )

    # Assign e1
    IdentityGovernanceService.assign_entitlement(
        db, org.id, admin.id, ident.id, EntitlementAssignmentCreate(entitlement_id=e1.id)
    )
    assert len(IdentityGovernanceService.list_sod_violations(db, org.id, ident.id)) == 0

    # Assign e2 -> Triggers SoD conflict!
    IdentityGovernanceService.assign_entitlement(
        db, org.id, admin.id, ident.id, EntitlementAssignmentCreate(entitlement_id=e2.id)
    )
    violations = IdentityGovernanceService.list_sod_violations(db, org.id, ident.id)
    assert len(violations) == 1
    assert violations[0].status == SoDViolationStatusEnum.ACTIVE_VIOLATION


def test_four_eyes_self_certification_prevention(db: Session, org_and_users):
    """Four-Eyes SoD rule prevents users from certifying their own access entitlements."""
    org, admin, reviewer = org_and_users

    # Create identity bound to admin User ID
    ident = IdentityGovernanceService.create_identity(
        db,
        org.id,
        admin.id,
        GovernedIdentityCreate(
            identity_code="ID-ADMIN-001",
            email="admin.person@example.com",
            full_name="Admin Person",
            user_id=admin.id,
        ),
    )
    ent = IdentityGovernanceService.create_entitlement(
        db,
        org.id,
        admin.id,
        IdentityEntitlementCreate(
            entitlement_code="ENT-ROOT",
            name="Root Access",
            resource_name="AWS Core",
            permission_scope="FullAdmin",
        ),
    )
    IdentityGovernanceService.assign_entitlement(
        db, org.id, admin.id, ident.id, EntitlementAssignmentCreate(entitlement_id=ent.id)
    )

    # Launch UAR campaign
    campaign = IdentityGovernanceService.create_campaign(
        db,
        org.id,
        admin.id,
        AccessCertificationCampaignCreate(
            campaign_code="UAR-Q3-2026",
            title="Q3 2026 Access Review",
            deadline=datetime.now(timezone.utc) + timedelta(days=30),
        ),
    )
    items = IdentityGovernanceService.list_campaign_items(db, org.id, campaign.id)
    assert len(items) == 1

    # Admin attempts to certify their own access -> 422 Blocked
    with pytest.raises(HTTPException) as exc:
        IdentityGovernanceService.review_certification_item(
            db,
            org.id,
            reviewer_id=admin.id,
            item_id=items[0].id,
            review=AccessCertificationItemReview(decision=CertificationDecisionEnum.CERTIFIED),
        )
    assert exc.value.status_code == 422

    # Independent Manager reviews -> Success
    item = IdentityGovernanceService.review_certification_item(
        db,
        org.id,
        reviewer_id=reviewer.id,
        item_id=items[0].id,
        review=AccessCertificationItemReview(decision=CertificationDecisionEnum.CERTIFIED),
    )
    assert item.decision == CertificationDecisionEnum.CERTIFIED


def test_four_eyes_jit_self_approval_prevention(db: Session, org_and_users):
    """Requesters cannot approve their own Just-In-Time privilege elevation requests."""
    org, admin, reviewer = org_and_users

    ident = IdentityGovernanceService.create_identity(
        db,
        org.id,
        admin.id,
        GovernedIdentityCreate(
            identity_code="ID-ENG-001",
            email="engineer@example.com",
            full_name="Software Engineer",
        ),
    )
    ent = IdentityGovernanceService.create_entitlement(
        db,
        org.id,
        admin.id,
        IdentityEntitlementCreate(
            entitlement_code="ENT-PROD-DB-WRITE",
            name="Prod DB Direct Write",
            resource_name="RDS Prod",
            permission_scope="DB_Writer",
            is_privileged=True,
        ),
    )

    jit_req = IdentityGovernanceService.create_jit_request(
        db,
        org.id,
        admin.id,
        JITAccessRequestCreate(
            request_code="JIT-REQ-001",
            identity_id=ident.id,
            entitlement_id=ent.id,
            requested_duration_minutes=60,
            business_justification="Hotfix customer data corruption incident INC-492",
        ),
    )
    assert jit_req.approval_status == JITApprovalStatusEnum.PENDING

    # Admin self-approval -> 422 Blocked
    with pytest.raises(HTTPException) as exc:
        IdentityGovernanceService.review_jit_request(
            db,
            org.id,
            reviewer_id=admin.id,
            request_id=jit_req.id,
            review=JITAccessReviewRequest(approved=True),
        )
    assert exc.value.status_code == 422

    # Manager approves -> Success
    approved_req = IdentityGovernanceService.review_jit_request(
        db,
        org.id,
        reviewer_id=reviewer.id,
        request_id=jit_req.id,
        review=JITAccessReviewRequest(approved=True),
    )
    assert approved_req.approval_status == JITApprovalStatusEnum.APPROVED
    assert approved_req.is_active == True

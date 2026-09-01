from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.permissions import RoleEnum
from app.core.security import get_password_hash
from app.models.privacy import (
    DataAsset,
    DataSensitivityLevel,
    DataTransferAssessment,
    DPIAAssessment,
    DPIARiskBand,
    JurisdictionRiskTier,
    PrivacyApprovalStatus,
    ProcessingActivity,
    ProcessingLegalBasis,
    ProcessingLifecycleState,
    TransferMechanism,
)
from app.models.organization import Organization
from app.models.resilience import BusinessProcess, CriticalityTierEnum
from app.models.ai_governance import AISystem, AISystemTypeEnum, AIRegulatoryTierEnum, AIHostingTypeEnum
from app.models.tprm import Vendor, VendorTierEnum, VendorStatusEnum
from app.models.remediation import (
    RemediationPlan,
    RemediationRootCauseClassificationEnum,
    RemediationSeverityEnum,
    RemediationSourceTypeEnum,
)
from app.models.audit_engagement import Audit, AuditTypeEnum, AuditStatusEnum
from app.models.user import User
from tests.conftest import get_token_headers


@pytest.fixture
def privacy_api_fixture(db: Session, org_apex: Organization, org_meridian: Organization):
    """Setup multi-tenant entities and multi-role users for PRIVACY-GRC API tests."""
    admin = User(
        email="privacy_admin@apex.com",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Privacy Admin",
        role=RoleEnum.ADMIN,
        is_active=True,
        organization_id=org_apex.id,
    )
    manager = User(
        email="privacy_manager@apex.com",
        hashed_password=get_password_hash("ManagerPass123!"),
        full_name="Privacy Manager DPO",
        role=RoleEnum.MANAGER,
        is_active=True,
        organization_id=org_apex.id,
    )
    grc_analyst = User(
        email="privacy_grc_analyst@apex.com",
        hashed_password=get_password_hash("GrcAnalystPass123!"),
        full_name="Privacy GRC Analyst",
        role=RoleEnum.GRC_ANALYST,
        is_active=True,
        organization_id=org_apex.id,
    )
    sec_analyst = User(
        email="privacy_sec_analyst@apex.com",
        hashed_password=get_password_hash("SecAnalystPass123!"),
        full_name="Privacy Sec Analyst",
        role=RoleEnum.SECURITY_ANALYST,
        is_active=True,
        organization_id=org_apex.id,
    )
    auditor = User(
        email="privacy_auditor@apex.com",
        hashed_password=get_password_hash("AuditorPass123!"),
        full_name="Privacy Auditor",
        role=RoleEnum.AUDITOR,
        is_active=True,
        organization_id=org_apex.id,
    )
    viewer = User(
        email="privacy_viewer@apex.com",
        hashed_password=get_password_hash("ViewerPass123!"),
        full_name="Privacy Viewer",
        role=RoleEnum.VIEWER,
        is_active=True,
        organization_id=org_apex.id,
    )

    # Meridian User (Tenant B)
    foreign_admin = User(
        email="foreign_privacy_admin@meridian.com",
        hashed_password=get_password_hash("ForeignPass123!"),
        full_name="Foreign Privacy Admin",
        role=RoleEnum.ADMIN,
        is_active=True,
        organization_id=org_meridian.id,
    )

    db.add_all([admin, manager, grc_analyst, sec_analyst, auditor, viewer, foreign_admin])
    db.commit()

    # Cross-Module Entities in Apex (Tenant A)
    bp_apex = BusinessProcess(
        organization_id=org_apex.id,
        name="Customer Checkout Process",
        description="Core customer ordering and payment flow",
        criticality_tier=CriticalityTierEnum.TIER_1,
        owner_id=admin.id,
    )
    ai_sys_apex = AISystem(
        organization_id=org_apex.id,
        system_code="AI-APEX-001",
        name="Customer Fraud Detection AI",
        system_type=AISystemTypeEnum.PREDICTIVE_ANALYTICS,
        regulatory_tier=AIRegulatoryTierEnum.HIGH_RISK,
        hosting_type=AIHostingTypeEnum.ON_PREMISE_SELF_HOSTED,
        owner_id=admin.id,
    )
    vendor_apex = Vendor(
        organization_id=org_apex.id,
        legal_name="Apex Cloud Services",
        vendor_code="VND-APX-01",
        calculated_tier=VendorTierEnum.TIER_1_CRITICAL,
        vendor_status=VendorStatusEnum.APPROVED,
    )
    audit_apex = Audit(
        organization_id=org_apex.id,
        title="Apex Privacy Compliance Audit",
        objective="Validate GDPR compliance",
        audit_type=AuditTypeEnum.INTERNAL,
        status=AuditStatusEnum.PLANNED,
    )
    db.add_all([bp_apex, ai_sys_apex, vendor_apex, audit_apex])
    db.commit()

    rem_plan_apex = RemediationPlan(
        organization_id=org_apex.id,
        plan_code="REM-APX-01",
        title="GDPR Encryption Hardening CAPA",
        problem_statement="Harden database encryption at rest and in transit",
        root_cause_classification=RemediationRootCauseClassificationEnum.CONTROL_DEFICIENCY,
        source_type=RemediationSourceTypeEnum.AUDIT,
        audit_id=audit_apex.id,
        severity=RemediationSeverityEnum.HIGH,
        plan_owner_id=admin.id,
    )
    db.add(rem_plan_apex)
    db.commit()

    return {
        "admin": admin,
        "manager": manager,
        "grc_analyst": grc_analyst,
        "sec_analyst": sec_analyst,
        "auditor": auditor,
        "viewer": viewer,
        "foreign_admin": foreign_admin,
        "bp": bp_apex,
        "ai_sys": ai_sys_apex,
        "vendor": vendor_apex,
        "rem_plan": rem_plan_apex,
    }


# ─── 1. DATA ASSETS API TESTS ─────────────────────────────────────────────────

def test_create_data_asset_api(client: TestClient, privacy_api_fixture):
    """Test POST /api/v1/privacy/data-assets creation with valid payload."""
    user = privacy_api_fixture["admin"]
    headers = get_token_headers(user)

    payload = {
        "asset_code": "DA-TEST-001",
        "name": "Customer Master DB",
        "description": "Primary Postgres database for customer records",
        "data_sensitivity_level": "RESTRICTED_PII",
        "data_volume_range": "HIGH",
        "storage_type": "POSTGRES_DB",
        "hosting_jurisdiction": "EU_EEA",
        "is_encrypted_at_rest": True,
        "is_encrypted_in_transit": True,
        "is_pseudonymized": False,
        "retention_period_months": 36,
    }

    res = client.post("/api/v1/privacy/data-assets", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["asset_code"] == "DA-TEST-001"
    assert data["data_sensitivity_level"] == "RESTRICTED_PII"
    assert data["organization_id"] == user.organization_id


def test_list_and_filter_data_assets_api(client: TestClient, privacy_api_fixture):
    """Test GET /api/v1/privacy/data-assets with sensitivity filtering."""
    user = privacy_api_fixture["viewer"]
    headers = get_token_headers(user)

    res = client.get("/api/v1/privacy/data-assets?sensitivity=RESTRICTED_PII", headers=headers)
    assert res.status_code == 200
    items = res.json()
    assert isinstance(items, list)
    for item in items:
        assert item["data_sensitivity_level"] == "RESTRICTED_PII"


def test_get_and_update_data_asset_api(client: TestClient, privacy_api_fixture):
    """Test GET and PUT /api/v1/privacy/data-assets/{asset_id}."""
    admin = privacy_api_fixture["admin"]
    headers = get_token_headers(admin)

    # Create asset
    create_res = client.post(
        "/api/v1/privacy/data-assets",
        json={"asset_code": "DA-UPD-001", "name": "Pre-Update Asset", "data_sensitivity_level": "INTERNAL"},
        headers=headers,
    )
    assert create_res.status_code == 201
    asset_id = create_res.json()["id"]

    # Get asset
    get_res = client.get(f"/api/v1/privacy/data-assets/{asset_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Pre-Update Asset"

    # Update asset
    update_res = client.put(
        f"/api/v1/privacy/data-assets/{asset_id}",
        json={"name": "Post-Update Asset", "retention_period_months": 48},
        headers=headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Post-Update Asset"
    assert update_res.json()["retention_period_months"] == 48


def test_delete_data_asset_api(client: TestClient, privacy_api_fixture):
    """Test DELETE /api/v1/privacy/data-assets/{asset_id}."""
    admin = privacy_api_fixture["admin"]
    headers = get_token_headers(admin)

    create_res = client.post(
        "/api/v1/privacy/data-assets",
        json={"asset_code": "DA-DEL-001", "name": "Asset to Delete"},
        headers=headers,
    )
    asset_id = create_res.json()["id"]

    del_res = client.delete(f"/api/v1/privacy/data-assets/{asset_id}", headers=headers)
    assert del_res.status_code == 204

    # Verify not found
    get_res = client.get(f"/api/v1/privacy/data-assets/{asset_id}", headers=headers)
    assert get_res.status_code == 404


# ─── 2. PROCESSING ACTIVITIES / RoPA API TESTS ─────────────────────────────────

def test_create_processing_activity_api(client: TestClient, privacy_api_fixture):
    """Test POST /api/v1/privacy/activities for GDPR Art 30 RoPA."""
    analyst = privacy_api_fixture["grc_analyst"]
    headers = get_token_headers(analyst)

    payload = {
        "activity_code": "ROPA-HR-001",
        "name": "Global Payroll & Benefits",
        "purpose_description": "Processing employee compensation and tax reporting",
        "legal_basis": "CONTRACT_PERFORMANCE",
        "data_subject_categories": "EMPLOYEES",
        "personal_data_categories": "IDENTIFIERS,FINANCIAL",
        "is_special_category_data": False,
    }

    res = client.post("/api/v1/privacy/activities", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["activity_code"] == "ROPA-HR-001"
    assert data["lifecycle_state"] == "DRAFT"
    assert data["dpo_approval_status"] == "PENDING"


def test_list_and_filter_processing_activities_api(client: TestClient, privacy_api_fixture):
    """Test GET /api/v1/privacy/activities with filters."""
    viewer = privacy_api_fixture["viewer"]
    headers = get_token_headers(viewer)

    res = client.get("/api/v1/privacy/activities?legal_basis=CONTRACT_PERFORMANCE", headers=headers)
    assert res.status_code == 200
    items = res.json()
    assert isinstance(items, list)


def test_processing_activity_lifecycle_transitions_api(client: TestClient, privacy_api_fixture):
    """Test PATCH /api/v1/privacy/activities/{id}/status state machine."""
    admin = privacy_api_fixture["admin"]
    headers = get_token_headers(admin)

    create_res = client.post(
        "/api/v1/privacy/activities",
        json={
            "activity_code": "ROPA-LIFE-001",
            "name": "Lifecycle Test Activity",
            "purpose_description": "Validating state machine flow",
            "legal_basis": "CONSENT",
            "data_subject_categories": "CUSTOMERS",
            "personal_data_categories": "IDENTIFIERS",
        },
        headers=headers,
    )
    act_id = create_res.json()["id"]

    # 1. DRAFT -> DPO_REVIEW
    patch_res = client.patch(
        f"/api/v1/privacy/activities/{act_id}/status",
        json={"lifecycle_state": "DPO_REVIEW"},
        headers=headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["lifecycle_state"] == "DPO_REVIEW"

    # 2. DPO_REVIEW -> DRAFT
    patch_res2 = client.patch(
        f"/api/v1/privacy/activities/{act_id}/status",
        json={"lifecycle_state": "DRAFT"},
        headers=headers,
    )
    assert patch_res2.status_code == 200
    assert patch_res2.json()["lifecycle_state"] == "DRAFT"

    # 3. DRAFT -> ARCHIVED -> RETIRED
    client.patch(
        f"/api/v1/privacy/activities/{act_id}/status",
        json={"lifecycle_state": "ARCHIVED"},
        headers=headers,
    )
    retired_res = client.patch(
        f"/api/v1/privacy/activities/{act_id}/status",
        json={"lifecycle_state": "RETIRED"},
        headers=headers,
    )
    assert retired_res.status_code == 200
    assert retired_res.json()["lifecycle_state"] == "RETIRED"


def test_illegal_lifecycle_transition_api(client: TestClient, privacy_api_fixture):
    """Test illegal state transition without prior DPO review/approval returns HTTP 400."""
    admin = privacy_api_fixture["admin"]
    headers = get_token_headers(admin)

    create_res = client.post(
        "/api/v1/privacy/activities",
        json={
            "activity_code": "ROPA-ILLEGAL-001",
            "name": "Illegal State Activity",
            "purpose_description": "Testing illegal transition",
            "legal_basis": "CONSENT",
            "data_subject_categories": "CUSTOMERS",
            "personal_data_categories": "IDENTIFIERS",
        },
        headers=headers,
    )
    act_id = create_res.json()["id"]

    # Direct DRAFT -> ACTIVE without review/approval
    res = client.patch(
        f"/api/v1/privacy/activities/{act_id}/status",
        json={"lifecycle_state": "ACTIVE"},
        headers=headers,
    )
    assert res.status_code == 400
    assert "Illegal lifecycle transition" in res.json()["detail"]


def test_active_activity_deletion_block_api(client: TestClient, privacy_api_fixture, db: Session):
    """Test that deleting an ACTIVE processing activity is blocked."""
    admin = privacy_api_fixture["admin"]
    headers = get_token_headers(admin)

    create_res = client.post(
        "/api/v1/privacy/activities",
        json={
            "activity_code": "ROPA-ACTIVE-DEL-001",
            "name": "Active Activity",
            "purpose_description": "Testing active delete block",
            "legal_basis": "CONSENT",
            "data_subject_categories": "CUSTOMERS",
            "personal_data_categories": "IDENTIFIERS",
        },
        headers=headers,
    )
    act_id = create_res.json()["id"]

    # Simulate active approved state
    act = db.query(ProcessingActivity).filter(ProcessingActivity.id == act_id).first()
    act.dpo_approval_status = PrivacyApprovalStatus.APPROVED
    act.lifecycle_state = ProcessingLifecycleState.ACTIVE
    db.commit()

    del_res = client.delete(f"/api/v1/privacy/activities/{act_id}", headers=headers)
    assert del_res.status_code == 400
    assert "Cannot delete an ACTIVE processing activity" in del_res.json()["detail"]


def test_retired_activity_immutability_api(client: TestClient, privacy_api_fixture, db: Session):
    """Test that RETIRED processing activities reject mutations."""
    admin = privacy_api_fixture["admin"]
    headers = get_token_headers(admin)

    create_res = client.post(
        "/api/v1/privacy/activities",
        json={
            "activity_code": "ROPA-RETIRED-IMM-001",
            "name": "Retired Activity",
            "purpose_description": "Testing retired immutability",
            "legal_basis": "CONSENT",
            "data_subject_categories": "CUSTOMERS",
            "personal_data_categories": "IDENTIFIERS",
        },
        headers=headers,
    )
    act_id = create_res.json()["id"]

    act = db.query(ProcessingActivity).filter(ProcessingActivity.id == act_id).first()
    act.lifecycle_state = ProcessingLifecycleState.RETIRED
    db.commit()

    # Attempt update
    upd_res = client.put(
        f"/api/v1/privacy/activities/{act_id}",
        json={"name": "Mutated Retired Name"},
        headers=headers,
    )
    assert upd_res.status_code == 400
    assert "permanently immutable" in upd_res.json()["detail"]


# ─── 3. DPIA ASSESSMENTS API TESTS ─────────────────────────────────────────────

def test_create_dpia_assessment_api(client: TestClient, privacy_api_fixture):
    """Test POST /api/v1/privacy/dpia with server-authoritative score calculation."""
    analyst = privacy_api_fixture["grc_analyst"]
    headers = get_token_headers(analyst)

    # Create activity
    act_res = client.post(
        "/api/v1/privacy/activities",
        json={
            "activity_code": "ROPA-DPIA-001",
            "name": "DPIA Target RoPA",
            "purpose_description": "Target for DPIA assessment",
            "legal_basis": "CONSENT",
            "data_subject_categories": "CUSTOMERS",
            "personal_data_categories": "IDENTIFIERS",
            "is_special_category_data": True,
            "is_large_scale_monitoring": True,
        },
        headers=headers,
    )
    act_id = act_res.json()["id"]

    dpia_payload = {
        "assessment_code": "DPIA-API-001",
        "processing_activity_id": act_id,
        "necessity_proportionality_score": 80.0,
        "data_subject_rights_score": 85.0,
        "safeguards_mitigation_score": 50.0,
        "automated_decision_making_risk": True,
        "large_scale_monitoring_risk": True,
    }

    res = client.post("/api/v1/privacy/dpia", json=dpia_payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["assessment_code"] == "DPIA-API-001"
    assert data["inherent_risk_score"] > 0.0
    assert data["residual_risk_score"] > 0.0
    assert data["dpo_consultation_status"] == "PENDING"


def test_update_dpia_assessment_api(client: TestClient, privacy_api_fixture):
    """Test PUT /api/v1/privacy/dpia/{id} recalculates scores server-side."""
    analyst = privacy_api_fixture["grc_analyst"]
    headers = get_token_headers(analyst)

    act_res = client.post(
        "/api/v1/privacy/activities",
        json={
            "activity_code": "ROPA-DPIA-UPD-001",
            "name": "DPIA Upd RoPA",
            "purpose_description": "Target for DPIA update",
            "legal_basis": "CONSENT",
            "data_subject_categories": "CUSTOMERS",
            "personal_data_categories": "IDENTIFIERS",
        },
        headers=headers,
    )
    act_id = act_res.json()["id"]

    dpia_res = client.post(
        "/api/v1/privacy/dpia",
        json={"assessment_code": "DPIA-UPD-002", "processing_activity_id": act_id, "safeguards_mitigation_score": 10.0},
        headers=headers,
    )
    dpia_id = dpia_res.json()["id"]
    old_rrs = dpia_res.json()["residual_risk_score"]

    # Update safeguards to 80%
    upd_res = client.put(
        f"/api/v1/privacy/dpia/{dpia_id}",
        json={"safeguards_mitigation_score": 80.0},
        headers=headers,
    )
    assert upd_res.status_code == 200
    new_rrs = upd_res.json()["residual_risk_score"]
    assert new_rrs < old_rrs


def test_four_eyes_dpia_review_workflow_api(client: TestClient, privacy_api_fixture):
    """Test Four-Eyes Segregation of Duties during DPIA review."""
    analyst = privacy_api_fixture["grc_analyst"]
    manager = privacy_api_fixture["manager"]
    analyst_headers = get_token_headers(analyst)
    manager_headers = get_token_headers(manager)

    # 1. Analyst creates activity and DPIA
    act_res = client.post(
        "/api/v1/privacy/activities",
        json={
            "activity_code": "ROPA-FOUR-EYES-001",
            "name": "Four-Eyes Target Activity",
            "purpose_description": "RoPA for Four-Eyes SoD testing",
            "legal_basis": "CONSENT",
            "data_subject_categories": "CUSTOMERS",
            "personal_data_categories": "IDENTIFIERS",
        },
        headers=analyst_headers,
    )
    act_id = act_res.json()["id"]

    # Put activity in DPO_REVIEW
    client.patch(f"/api/v1/privacy/activities/{act_id}/status", json={"lifecycle_state": "DPO_REVIEW"}, headers=analyst_headers)

    dpia_res = client.post(
        "/api/v1/privacy/dpia",
        json={"assessment_code": "DPIA-SOD-001", "processing_activity_id": act_id},
        headers=analyst_headers,
    )
    dpia_id = dpia_res.json()["id"]

    # 2. Analyst attempts to self-approve DPIA -> HTTP 403 Forbidden
    self_rev_res = client.post(
        f"/api/v1/privacy/dpia/{dpia_id}/review",
        json={"decision": "APPROVED", "recommendation_notes": "Self review attempt"},
        headers=analyst_headers,
    )
    assert self_rev_res.status_code == 403

    # 3. Manager (independent DPO) approves DPIA -> HTTP 200 OK
    dpo_res = client.post(
        f"/api/v1/privacy/dpia/{dpia_id}/review",
        json={"decision": "APPROVED", "recommendation_notes": "Legitimate DPO consultation signoff"},
        headers=manager_headers,
    )
    assert dpo_res.status_code == 200
    assert dpo_res.json()["dpo_consultation_status"] == "APPROVED"

    # Verify parent activity transitioned to ACTIVE
    get_act_res = client.get(f"/api/v1/privacy/activities/{act_id}", headers=manager_headers)
    assert get_act_res.json()["lifecycle_state"] == "ACTIVE"


def test_dpia_re_review_conflict_api(client: TestClient, privacy_api_fixture):
    """Test re-review of finalized DPIA returns HTTP 409 Conflict."""
    analyst = privacy_api_fixture["grc_analyst"]
    manager = privacy_api_fixture["manager"]
    analyst_headers = get_token_headers(analyst)
    manager_headers = get_token_headers(manager)

    act_res = client.post(
        "/api/v1/privacy/activities",
        json={
            "activity_code": "ROPA-REPLAY-001",
            "name": "Replay Activity",
            "purpose_description": "RoPA for replay testing",
            "legal_basis": "CONSENT",
            "data_subject_categories": "CUSTOMERS",
            "personal_data_categories": "IDENTIFIERS",
        },
        headers=analyst_headers,
    )
    act_id = act_res.json()["id"]

    dpia_res = client.post(
        "/api/v1/privacy/dpia",
        json={"assessment_code": "DPIA-REPLAY-001", "processing_activity_id": act_id},
        headers=analyst_headers,
    )
    dpia_id = dpia_res.json()["id"]

    # Approve DPIA
    client.post(
        f"/api/v1/privacy/dpia/{dpia_id}/review",
        json={"decision": "APPROVED", "recommendation_notes": "First approval"},
        headers=manager_headers,
    )

    # Re-review attempt
    replay_res = client.post(
        f"/api/v1/privacy/dpia/{dpia_id}/review",
        json={"decision": "REJECTED", "recommendation_notes": "Attempted replay rejection"},
        headers=manager_headers,
    )
    assert replay_res.status_code == 409


def test_dpia_calculate_preview_api(client: TestClient, privacy_api_fixture):
    """Test POST /api/v1/privacy/dpia/calculate-preview endpoint."""
    user = privacy_api_fixture["viewer"]
    headers = get_token_headers(user)

    payload = {
        "sensitivity_level": "RESTRICTED_PII",
        "volume_tier": "HIGH",
        "is_special_category": True,
        "automated_decision_making_risk": True,
        "large_scale_monitoring_risk": True,
        "vulnerable_subjects_risk": True,
        "safeguards_mitigation_score": 50.0,
    }

    res = client.post("/api/v1/privacy/dpia/calculate-preview", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["inherent_risk_score"] == 95.00
    assert data["residual_risk_score"] > 0.0
    assert data["risk_band"] in ["LOW", "MODERATE", "HIGH", "VERY_HIGH", "CRITICAL"]


# ─── 4. DATA TRANSFER ASSESSMENTS API TESTS ───────────────────────────────────

def test_create_and_review_data_transfer_api(client: TestClient, privacy_api_fixture):
    """Test create TIA assessment and Four-Eyes manager review."""
    analyst = privacy_api_fixture["grc_analyst"]
    manager = privacy_api_fixture["manager"]
    analyst_headers = get_token_headers(analyst)
    manager_headers = get_token_headers(manager)

    # 1. Create RoPA activity
    act_res = client.post(
        "/api/v1/privacy/activities",
        json={
            "activity_code": "ROPA-TRANSFER-001",
            "name": "Cross-Border Analytics",
            "purpose_description": "Data transfer testing",
            "legal_basis": "LEGITIMATE_INTERESTS",
            "data_subject_categories": "CUSTOMERS",
            "personal_data_categories": "IDENTIFIERS",
            "is_cross_border_transfer": True,
        },
        headers=analyst_headers,
    )
    act_id = act_res.json()["id"]

    # 2. Create TIA
    tia_payload = {
        "transfer_code": "TIA-API-001",
        "processing_activity_id": act_id,
        "source_country": "EU_EEA",
        "destination_country": "United States",
        "destination_jurisdiction_tier": "MODERATE_SAFEGUARDS_REQUIRED",
        "transfer_mechanism": "STANDARD_CONTRACTUAL_CLAUSES_SCC",
        "supplementary_measures_score": 10.0,
    }
    tia_res = client.post("/api/v1/privacy/transfers", json=tia_payload, headers=analyst_headers)
    assert tia_res.status_code == 201
    transfer_id = tia_res.json()["id"]
    assert tia_res.json()["transfer_risk_index"] == 30.00
    assert tia_res.json()["approval_status"] == "PENDING"

    # 3. Analyst self-approval -> HTTP 403 Forbidden
    self_appr_res = client.post(
        f"/api/v1/privacy/transfers/{transfer_id}/review",
        json={"decision": "APPROVED", "reviewer_notes": "Self approval attempt"},
        headers=analyst_headers,
    )
    assert self_appr_res.status_code == 403

    # 4. Manager approvals -> HTTP 200 OK
    appr_res = client.post(
        f"/api/v1/privacy/transfers/{transfer_id}/review",
        json={"decision": "APPROVED", "reviewer_notes": "Verified SCCs and supplementary measures"},
        headers=manager_headers,
    )
    assert appr_res.status_code == 200
    assert appr_res.json()["approval_status"] == "APPROVED"


def test_transfer_re_review_conflict_api(client: TestClient, privacy_api_fixture):
    """Test re-review of finalized data transfer returns HTTP 409 Conflict."""
    analyst = privacy_api_fixture["grc_analyst"]
    manager = privacy_api_fixture["manager"]
    analyst_headers = get_token_headers(analyst)
    manager_headers = get_token_headers(manager)

    act_res = client.post(
        "/api/v1/privacy/activities",
        json={
            "activity_code": "ROPA-TIA-REPLAY-001",
            "name": "TIA Replay RoPA",
            "purpose_description": "RoPA for transfer replay test",
            "legal_basis": "CONSENT",
            "data_subject_categories": "CUSTOMERS",
            "personal_data_categories": "IDENTIFIERS",
        },
        headers=analyst_headers,
    )
    act_id = act_res.json()["id"]

    tia_res = client.post(
        "/api/v1/privacy/transfers",
        json={"transfer_code": "TIA-REPLAY-001", "processing_activity_id": act_id, "destination_country": "UK"},
        headers=analyst_headers,
    )
    transfer_id = tia_res.json()["id"]

    # Approve transfer
    client.post(
        f"/api/v1/privacy/transfers/{transfer_id}/review",
        json={"decision": "APPROVED", "reviewer_notes": "Approved"},
        headers=manager_headers,
    )

    # Re-review attempt
    replay_res = client.post(
        f"/api/v1/privacy/transfers/{transfer_id}/review",
        json={"decision": "REJECTED", "reviewer_notes": "Replay attempt"},
        headers=manager_headers,
    )
    assert replay_res.status_code == 409


def test_transfer_calculate_preview_api(client: TestClient, privacy_api_fixture):
    """Test POST /api/v1/privacy/transfers/calculate-preview."""
    user = privacy_api_fixture["viewer"]
    headers = get_token_headers(user)

    payload = {
        "destination_jurisdiction_tier": "HIGH_RISK_SURVEILLANCE",
        "transfer_mechanism": "STANDARD_CONTRACTUAL_CLAUSES_SCC",
        "supplementary_measures_score": 20.0,
    }
    res = client.post("/api/v1/privacy/transfers/calculate-preview", json=payload, headers=headers)
    assert res.status_code == 200
    assert res.json()["transfer_risk_index"] == 55.00


# ─── 5. POSTURE SUMMARY & CROSS-MODULE INTEGRATION API TESTS ──────────────────

def test_privacy_posture_summary_api(client: TestClient, privacy_api_fixture):
    """Test GET /api/v1/privacy/summary/posture and /api/v1/privacy/posture/summary."""
    viewer = privacy_api_fixture["viewer"]
    headers = get_token_headers(viewer)

    res1 = client.get("/api/v1/privacy/summary/posture", headers=headers)
    assert res1.status_code == 200
    data1 = res1.json()
    assert "total_data_assets" in data1
    assert "total_processing_activities" in data1
    assert "risk_band_distribution" in data1

    res2 = client.get("/api/v1/privacy/posture/summary", headers=headers)
    assert res2.status_code == 200
    assert res2.json() == data1


def test_cross_module_linkage_api(client: TestClient, privacy_api_fixture):
    """Test creating DataAsset and ProcessingActivity with valid same-tenant cross-module links."""
    admin = privacy_api_fixture["admin"]
    bp = privacy_api_fixture["bp"]
    ai_sys = privacy_api_fixture["ai_sys"]
    vendor = privacy_api_fixture["vendor"]
    rem_plan = privacy_api_fixture["rem_plan"]
    headers = get_token_headers(admin)

    # 1. Create DataAsset linked to BP, AI System, and Vendor
    asset_res = client.post(
        "/api/v1/privacy/data-assets",
        json={
            "asset_code": "DA-LINKED-001",
            "name": "Linked AI Data Store",
            "business_process_id": bp.id,
            "ai_system_id": ai_sys.id,
            "vendor_id": vendor.id,
        },
        headers=headers,
    )
    assert asset_res.status_code == 201
    asset_data = asset_res.json()
    assert asset_data["business_process_id"] == bp.id
    assert asset_data["ai_system_id"] == ai_sys.id
    assert asset_data["vendor_id"] == vendor.id

    # 2. Create ProcessingActivity linked to BP, AI System, and Vendor
    act_res = client.post(
        "/api/v1/privacy/activities",
        json={
            "activity_code": "ROPA-LINKED-001",
            "name": "Linked RoPA Flow",
            "purpose_description": "Cross-module linked processing flow",
            "legal_basis": "CONSENT",
            "data_subject_categories": "CUSTOMERS",
            "personal_data_categories": "IDENTIFIERS",
            "business_process_id": bp.id,
            "ai_system_id": ai_sys.id,
            "vendor_id": vendor.id,
        },
        headers=headers,
    )
    assert act_res.status_code == 201
    act_id = act_res.json()["id"]

    # 3. Create DPIA linked to RemediationPlan
    dpia_res = client.post(
        "/api/v1/privacy/dpia",
        json={
            "assessment_code": "DPIA-LINKED-001",
            "processing_activity_id": act_id,
            "remediation_plan_id": rem_plan.id,
        },
        headers=headers,
    )
    assert dpia_res.status_code == 201
    assert dpia_res.json()["remediation_plan_id"] == rem_plan.id

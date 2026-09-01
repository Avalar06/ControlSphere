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
def adv_p16_fixture(db: Session, org_apex: Organization, org_meridian: Organization):
    """Setup multi-tenant entities and adversarial actors for Phase 16 ADV test suite."""
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
        full_name="Apex Manager DPO",
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
    apex_grc_analyst = User(
        email="adv_grc_analyst@apex.com",
        hashed_password=get_password_hash("GrcAnalystPass123!"),
        full_name="Apex GRC Analyst",
        role=RoleEnum.GRC_ANALYST,
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

    # Meridian Users (Tenant B - Adversary)
    meridian_admin = User(
        email="adv_admin@meridian.com",
        hashed_password=get_password_hash("MeridianAdmin123!"),
        full_name="Meridian Admin",
        role=RoleEnum.ADMIN,
        is_active=True,
        organization_id=org_meridian.id,
    )

    db.add_all([
        apex_admin, apex_manager, apex_manager_2, apex_grc_analyst,
        apex_sec_analyst, apex_auditor, apex_viewer, meridian_admin,
    ])
    db.commit()

    # Audits
    audit_apex = Audit(
        organization_id=org_apex.id,
        title="Apex Privacy Audit",
        objective="Validate GDPR compliance",
        audit_type=AuditTypeEnum.INTERNAL,
        status=AuditStatusEnum.PLANNED,
    )
    audit_meridian = Audit(
        organization_id=org_meridian.id,
        title="Meridian Privacy Audit",
        objective="Validate GDPR compliance",
        audit_type=AuditTypeEnum.INTERNAL,
        status=AuditStatusEnum.PLANNED,
    )
    db.add_all([audit_apex, audit_meridian])
    db.commit()

    # Cross-Module Entities Apex (Tenant A)
    proc_apex = BusinessProcess(
        organization_id=org_apex.id,
        name="Apex Payments Engine",
        owner_id=apex_admin.id,
        criticality_tier=CriticalityTierEnum.TIER_1,
    )
    ai_sys_apex = AISystem(
        organization_id=org_apex.id,
        system_code="AI-APX-001",
        name="Apex Fraud ML",
        system_type=AISystemTypeEnum.PREDICTIVE_ANALYTICS,
        regulatory_tier=AIRegulatoryTierEnum.HIGH_RISK,
        hosting_type=AIHostingTypeEnum.ON_PREMISE_SELF_HOSTED,
        owner_id=apex_admin.id,
    )
    vendor_apex = Vendor(
        organization_id=org_apex.id,
        legal_name="Apex Cloud Provider",
        vendor_code="VND-APX-01",
        calculated_tier=VendorTierEnum.TIER_1_CRITICAL,
        vendor_status=VendorStatusEnum.APPROVED,
    )
    remediation_apex = RemediationPlan(
        organization_id=org_apex.id,
        plan_code="REM-APX-01",
        title="Apex Encryption Hardening Plan",
        problem_statement="Mitigate plaintext PII storage risk",
        root_cause_classification=RemediationRootCauseClassificationEnum.CONTROL_DEFICIENCY,
        source_type=RemediationSourceTypeEnum.AUDIT,
        audit_id=audit_apex.id,
        severity=RemediationSeverityEnum.CRITICAL,
        plan_owner_id=apex_admin.id,
    )

    # Cross-Module Entities Meridian (Tenant B)
    proc_meridian = BusinessProcess(
        organization_id=org_meridian.id,
        name="Meridian Patient Record Flow",
        owner_id=meridian_admin.id,
        criticality_tier=CriticalityTierEnum.TIER_1,
    )
    ai_sys_meridian = AISystem(
        organization_id=org_meridian.id,
        system_code="AI-MER-001",
        name="Meridian Diagnostics AI",
        system_type=AISystemTypeEnum.COMPUTER_VISION,
        regulatory_tier=AIRegulatoryTierEnum.HIGH_RISK,
        hosting_type=AIHostingTypeEnum.CLOUD_THIRD_PARTY,
        owner_id=meridian_admin.id,
    )
    vendor_meridian = Vendor(
        organization_id=org_meridian.id,
        legal_name="Meridian Cloud Host",
        vendor_code="VND-MER-01",
        calculated_tier=VendorTierEnum.TIER_1_CRITICAL,
        vendor_status=VendorStatusEnum.APPROVED,
    )
    remediation_meridian = RemediationPlan(
        organization_id=org_meridian.id,
        plan_code="REM-MER-01",
        title="Meridian Foreign Remediation",
        problem_statement="Foreign remediation plan",
        root_cause_classification=RemediationRootCauseClassificationEnum.CONTROL_DEFICIENCY,
        source_type=RemediationSourceTypeEnum.AUDIT,
        audit_id=audit_meridian.id,
        severity=RemediationSeverityEnum.HIGH,
        plan_owner_id=meridian_admin.id,
    )

    db.add_all([
        proc_apex, ai_sys_apex, vendor_apex, remediation_apex,
        proc_meridian, ai_sys_meridian, vendor_meridian, remediation_meridian,
    ])
    db.commit()

    return {
        "apex_admin": apex_admin,
        "apex_manager": apex_manager,
        "apex_manager_2": apex_manager_2,
        "apex_grc_analyst": apex_grc_analyst,
        "apex_sec_analyst": apex_sec_analyst,
        "apex_auditor": apex_auditor,
        "apex_viewer": apex_viewer,
        "meridian_admin": meridian_admin,
        "proc_apex": proc_apex,
        "ai_sys_apex": ai_sys_apex,
        "vendor_apex": vendor_apex,
        "remediation_apex": remediation_apex,
        "proc_meridian": proc_meridian,
        "ai_sys_meridian": ai_sys_meridian,
        "vendor_meridian": vendor_meridian,
        "remediation_meridian": remediation_meridian,
    }


# ─── 1. TENANT ISOLATION VECTORS (ADV-P16-01 to ADV-P16-08) ───────────────────

def test_adv_p16_01_cross_tenant_data_asset_access(client: TestClient, adv_p16_fixture):
    """ADV-P16-01: Cross-tenant data asset access returns HTTP 404."""
    apex_headers = get_token_headers(adv_p16_fixture["apex_admin"])
    meridian_headers = get_token_headers(adv_p16_fixture["meridian_admin"])

    create_res = client.post(
        "/api/v1/privacy/data-assets",
        json={"asset_code": "DA-ADV-01", "name": "Apex Asset"},
        headers=apex_headers,
    )
    asset_id = create_res.json()["id"]

    # Foreign tenant attempts GET, PUT, DELETE
    assert client.get(f"/api/v1/privacy/data-assets/{asset_id}", headers=meridian_headers).status_code == 404
    assert client.put(f"/api/v1/privacy/data-assets/{asset_id}", json={"name": "Attacker"}, headers=meridian_headers).status_code == 404
    assert client.delete(f"/api/v1/privacy/data-assets/{asset_id}", headers=meridian_headers).status_code == 404


def test_adv_p16_02_cross_tenant_processing_activity_access(client: TestClient, adv_p16_fixture):
    """ADV-P16-02: Cross-tenant processing activity access returns HTTP 404."""
    apex_headers = get_token_headers(adv_p16_fixture["apex_admin"])
    meridian_headers = get_token_headers(adv_p16_fixture["meridian_admin"])

    create_res = client.post(
        "/api/v1/privacy/activities",
        json={
            "activity_code": "ROPA-ADV-02",
            "name": "Apex Activity",
            "purpose_description": "Apex RoPA",
            "legal_basis": "CONSENT",
            "data_subject_categories": "CUSTOMERS",
            "personal_data_categories": "IDENTIFIERS",
        },
        headers=apex_headers,
    )
    act_id = create_res.json()["id"]

    assert client.get(f"/api/v1/privacy/activities/{act_id}", headers=meridian_headers).status_code == 404
    assert client.put(f"/api/v1/privacy/activities/{act_id}", json={"name": "Attacker"}, headers=meridian_headers).status_code == 404
    assert client.patch(f"/api/v1/privacy/activities/{act_id}/status", json={"lifecycle_state": "DPO_REVIEW"}, headers=meridian_headers).status_code == 404


def test_adv_p16_03_cross_tenant_dpia_access(client: TestClient, adv_p16_fixture):
    """ADV-P16-03: Cross-tenant DPIA assessment access returns HTTP 404."""
    apex_headers = get_token_headers(adv_p16_fixture["apex_admin"])
    meridian_headers = get_token_headers(adv_p16_fixture["meridian_admin"])

    act_res = client.post(
        "/api/v1/privacy/activities",
        json={
            "activity_code": "ROPA-ADV-03",
            "name": "Apex Activity 3",
            "purpose_description": "RoPA for DPIA test",
            "legal_basis": "CONSENT",
            "data_subject_categories": "CUSTOMERS",
            "personal_data_categories": "IDENTIFIERS",
        },
        headers=apex_headers,
    )
    act_id = act_res.json()["id"]

    dpia_res = client.post(
        "/api/v1/privacy/dpia",
        json={"assessment_code": "DPIA-ADV-03", "processing_activity_id": act_id},
        headers=apex_headers,
    )
    dpia_id = dpia_res.json()["id"]

    assert client.get(f"/api/v1/privacy/dpia/{dpia_id}", headers=meridian_headers).status_code == 404
    assert client.put(f"/api/v1/privacy/dpia/{dpia_id}", json={"safeguards_mitigation_score": 90.0}, headers=meridian_headers).status_code == 404
    assert client.post(f"/api/v1/privacy/dpia/{dpia_id}/review", json={"decision": "APPROVED", "recommendation_notes": "Foreign DPO review notes"}, headers=meridian_headers).status_code == 404


def test_adv_p16_04_cross_tenant_transfer_assessment_access(client: TestClient, adv_p16_fixture):
    """ADV-P16-04: Cross-tenant data transfer assessment access returns HTTP 404."""
    apex_headers = get_token_headers(adv_p16_fixture["apex_admin"])
    meridian_headers = get_token_headers(adv_p16_fixture["meridian_admin"])

    act_res = client.post(
        "/api/v1/privacy/activities",
        json={
            "activity_code": "ROPA-ADV-04",
            "name": "Apex Activity 4",
            "purpose_description": "RoPA for TIA test",
            "legal_basis": "CONSENT",
            "data_subject_categories": "CUSTOMERS",
            "personal_data_categories": "IDENTIFIERS",
        },
        headers=apex_headers,
    )
    act_id = act_res.json()["id"]

    tia_res = client.post(
        "/api/v1/privacy/transfers",
        json={"transfer_code": "TIA-ADV-04", "processing_activity_id": act_id, "destination_country": "Japan"},
        headers=apex_headers,
    )
    tia_id = tia_res.json()["id"]

    assert client.get(f"/api/v1/privacy/transfers/{tia_id}", headers=meridian_headers).status_code == 404
    assert client.post(f"/api/v1/privacy/transfers/{tia_id}/review", json={"decision": "APPROVED", "reviewer_notes": "Foreign transfer review notes"}, headers=meridian_headers).status_code == 404


def test_adv_p16_05_cross_tenant_business_process_linkage(client: TestClient, adv_p16_fixture):
    """ADV-P16-05: Linking a foreign tenant's BusinessProcess returns HTTP 404."""
    apex_headers = get_token_headers(adv_p16_fixture["apex_admin"])
    foreign_bp_id = adv_p16_fixture["proc_meridian"].id

    res = client.post(
        "/api/v1/privacy/data-assets",
        json={"asset_code": "DA-ADV-05", "name": "Illegal BP Link", "business_process_id": foreign_bp_id},
        headers=apex_headers,
    )
    assert res.status_code == 404
    assert "Business process" in res.json()["detail"]


def test_adv_p16_06_cross_tenant_ai_system_linkage(client: TestClient, adv_p16_fixture):
    """ADV-P16-06: Linking a foreign tenant's AISystem returns HTTP 404."""
    apex_headers = get_token_headers(adv_p16_fixture["apex_admin"])
    foreign_ai_id = adv_p16_fixture["ai_sys_meridian"].id

    res = client.post(
        "/api/v1/privacy/activities",
        json={
            "activity_code": "ROPA-ADV-06",
            "name": "Illegal AI Link",
            "purpose_description": "Attempting cross-tenant AI link",
            "legal_basis": "CONSENT",
            "data_subject_categories": "CUSTOMERS",
            "personal_data_categories": "IDENTIFIERS",
            "ai_system_id": foreign_ai_id,
        },
        headers=apex_headers,
    )
    assert res.status_code == 404
    assert "AI system" in res.json()["detail"]


def test_adv_p16_07_cross_tenant_vendor_linkage(client: TestClient, adv_p16_fixture):
    """ADV-P16-07: Linking a foreign tenant's Vendor returns HTTP 404."""
    apex_headers = get_token_headers(adv_p16_fixture["apex_admin"])
    foreign_vendor_id = adv_p16_fixture["vendor_meridian"].id

    res = client.post(
        "/api/v1/privacy/data-assets",
        json={"asset_code": "DA-ADV-07", "name": "Illegal Vendor Link", "vendor_id": foreign_vendor_id},
        headers=apex_headers,
    )
    assert res.status_code == 404
    assert "Vendor" in res.json()["detail"]


def test_adv_p16_08_cross_tenant_remediation_plan_linkage(client: TestClient, adv_p16_fixture):
    """ADV-P16-08: Linking a foreign tenant's RemediationPlan returns HTTP 404."""
    apex_headers = get_token_headers(adv_p16_fixture["apex_admin"])
    foreign_rem_id = adv_p16_fixture["remediation_meridian"].id

    act_res = client.post(
        "/api/v1/privacy/activities",
        json={
            "activity_code": "ROPA-ADV-08",
            "name": "RoPA for DPIA Link Test",
            "purpose_description": "Valid RoPA",
            "legal_basis": "CONSENT",
            "data_subject_categories": "CUSTOMERS",
            "personal_data_categories": "IDENTIFIERS",
        },
        headers=apex_headers,
    )
    act_id = act_res.json()["id"]

    res = client.post(
        "/api/v1/privacy/dpia",
        json={"assessment_code": "DPIA-ADV-08", "processing_activity_id": act_id, "remediation_plan_id": foreign_rem_id},
        headers=apex_headers,
    )
    assert res.status_code == 404
    assert "Remediation plan" in res.json()["detail"]


# ─── 2. INJECTION & PRIVILEGE ESCALATION VECTORS (ADV-P16-09 to ADV-P16-15) ────

def test_adv_p16_09_spoofed_organization_id(client: TestClient, adv_p16_fixture):
    """ADV-P16-09: Spoofed organization_id in body is ignored; uses caller tenant."""
    apex_user = adv_p16_fixture["apex_admin"]
    apex_headers = get_token_headers(apex_user)

    res = client.post(
        "/api/v1/privacy/data-assets",
        json={"asset_code": "DA-ADV-09", "name": "Spoofed Org Asset", "organization_id": 99999},
        headers=apex_headers,
    )
    assert res.status_code == 201
    assert res.json()["organization_id"] == apex_user.organization_id


def test_adv_p16_10_calculated_irs_injection(client: TestClient, adv_p16_fixture):
    """ADV-P16-10: Attempted client injection of inherent_risk_score is overwritten by server."""
    apex_headers = get_token_headers(adv_p16_fixture["apex_admin"])

    act_res = client.post(
        "/api/v1/privacy/activities",
        json={
            "activity_code": "ROPA-ADV-10",
            "name": "RoPA for IRS Injection",
            "purpose_description": "Testing IRS injection",
            "legal_basis": "CONSENT",
            "data_subject_categories": "CUSTOMERS",
            "personal_data_categories": "IDENTIFIERS",
            "is_special_category_data": True,
        },
        headers=apex_headers,
    )
    act_id = act_res.json()["id"]

    dpia_res = client.post(
        "/api/v1/privacy/dpia",
        json={
            "assessment_code": "DPIA-ADV-10",
            "processing_activity_id": act_id,
            "inherent_risk_score": 0.00,  # Malicious attempt to force zero inherent risk
        },
        headers=apex_headers,
    )
    assert dpia_res.status_code == 201
    assert dpia_res.json()["inherent_risk_score"] > 0.00


def test_adv_p16_11_calculated_rrs_injection(client: TestClient, adv_p16_fixture):
    """ADV-P16-11: Attempted client injection of residual_risk_score is overwritten by server."""
    apex_headers = get_token_headers(adv_p16_fixture["apex_admin"])

    act_res = client.post(
        "/api/v1/privacy/activities",
        json={
            "activity_code": "ROPA-ADV-11",
            "name": "RoPA for RRS Injection",
            "purpose_description": "Testing RRS injection",
            "legal_basis": "CONSENT",
            "data_subject_categories": "CUSTOMERS",
            "personal_data_categories": "IDENTIFIERS",
        },
        headers=apex_headers,
    )
    act_id = act_res.json()["id"]

    dpia_res = client.post(
        "/api/v1/privacy/dpia",
        json={
            "assessment_code": "DPIA-ADV-11",
            "processing_activity_id": act_id,
            "residual_risk_score": 0.00,  # Malicious attempt to force zero residual risk
        },
        headers=apex_headers,
    )
    assert dpia_res.status_code == 201
    assert dpia_res.json()["residual_risk_score"] > 0.00


def test_adv_p16_12_calculated_tri_injection(client: TestClient, adv_p16_fixture):
    """ADV-P16-12: Attempted client injection of transfer_risk_index is overwritten by server."""
    apex_headers = get_token_headers(adv_p16_fixture["apex_admin"])

    act_res = client.post(
        "/api/v1/privacy/activities",
        json={
            "activity_code": "ROPA-ADV-12",
            "name": "RoPA for TRI Injection",
            "purpose_description": "Testing TRI injection",
            "legal_basis": "CONSENT",
            "data_subject_categories": "CUSTOMERS",
            "personal_data_categories": "IDENTIFIERS",
        },
        headers=apex_headers,
    )
    act_id = act_res.json()["id"]

    tia_res = client.post(
        "/api/v1/privacy/transfers",
        json={
            "transfer_code": "TIA-ADV-12",
            "processing_activity_id": act_id,
            "destination_country": "Russia",
            "destination_jurisdiction_tier": "HIGH_RISK_SURVEILLANCE",
            "transfer_mechanism": "STANDARD_CONTRACTUAL_CLAUSES_SCC",
            "transfer_risk_index": 0.00,  # Malicious attempt to bypass transfer risk
        },
        headers=apex_headers,
    )
    assert tia_res.status_code == 201
    assert tia_res.json()["transfer_risk_index"] == 75.00  # True calculated score


def test_adv_p16_13_spoofed_risk_band(client: TestClient, adv_p16_fixture):
    """ADV-P16-13: Spoofed risk band in payload is overwritten by server-determined tier."""
    apex_headers = get_token_headers(adv_p16_fixture["apex_admin"])

    act_res = client.post(
        "/api/v1/privacy/activities",
        json={
            "activity_code": "ROPA-ADV-13",
            "name": "RoPA for Risk Band Injection",
            "purpose_description": "Testing risk band",
            "legal_basis": "CONSENT",
            "data_subject_categories": "CUSTOMERS",
            "personal_data_categories": "IDENTIFIERS",
            "is_special_category_data": True,
        },
        headers=apex_headers,
    )
    act_id = act_res.json()["id"]

    dpia_res = client.post(
        "/api/v1/privacy/dpia",
        json={
            "assessment_code": "DPIA-ADV-13",
            "processing_activity_id": act_id,
            "risk_band": "LOW",  # Attacker attempts to spoof LOW risk band
        },
        headers=apex_headers,
    )
    assert dpia_res.status_code == 201
    assert dpia_res.json()["risk_band"] in ["HIGH", "VERY_HIGH", "CRITICAL", "MODERATE"]


def test_adv_p16_14_spoofed_approval_status(client: TestClient, adv_p16_fixture):
    """ADV-P16-14: Spoofed approval status on entity creation is rejected/overridden to PENDING."""
    apex_headers = get_token_headers(adv_p16_fixture["apex_admin"])

    act_res = client.post(
        "/api/v1/privacy/activities",
        json={
            "activity_code": "ROPA-ADV-14",
            "name": "RoPA for Approval Status Injection",
            "purpose_description": "Testing approval injection",
            "legal_basis": "CONSENT",
            "data_subject_categories": "CUSTOMERS",
            "personal_data_categories": "IDENTIFIERS",
            "dpo_approval_status": "APPROVED",  # Attacker attempts self-approval
        },
        headers=apex_headers,
    )
    assert act_res.status_code == 201
    assert act_res.json()["dpo_approval_status"] == "PENDING"


def test_adv_p16_15_spoofed_reviewer_identity(client: TestClient, adv_p16_fixture):
    """ADV-P16-15: Spoofed reviewer identity in review request is overridden by authenticated user."""
    manager = adv_p16_fixture["apex_manager"]
    manager_headers = get_token_headers(manager)
    analyst = adv_p16_fixture["apex_grc_analyst"]
    analyst_headers = get_token_headers(analyst)

    act_res = client.post(
        "/api/v1/privacy/activities",
        json={
            "activity_code": "ROPA-ADV-15",
            "name": "RoPA for Reviewer ID Spoof",
            "purpose_description": "Testing reviewer ID spoof",
            "legal_basis": "CONSENT",
            "data_subject_categories": "CUSTOMERS",
            "personal_data_categories": "IDENTIFIERS",
        },
        headers=analyst_headers,
    )
    act_id = act_res.json()["id"]

    dpia_res = client.post(
        "/api/v1/privacy/dpia",
        json={"assessment_code": "DPIA-ADV-15", "processing_activity_id": act_id},
        headers=analyst_headers,
    )
    dpia_id = dpia_res.json()["id"]

    # Manager approves but payload specifies a spoofed reviewer ID
    rev_res = client.post(
        f"/api/v1/privacy/dpia/{dpia_id}/review",
        json={"decision": "APPROVED", "recommendation_notes": "Legitimate notes", "dpo_reviewed_by_id": 99999},
        headers=manager_headers,
    )
    assert rev_res.status_code == 200
    assert rev_res.json()["dpo_reviewed_by_id"] == manager.id  # Server correctly used authenticated user ID


# ─── 3. FOUR-EYES & REPLAY VECTORS (ADV-P16-16 to ADV-P16-19) ──────────────────

def test_adv_p16_16_dpia_creator_self_review(client: TestClient, adv_p16_fixture):
    """ADV-P16-16: DPIA creator self-review attempt returns HTTP 403 Forbidden."""
    manager = adv_p16_fixture["apex_manager"]
    manager_headers = get_token_headers(manager)

    act_res = client.post(
        "/api/v1/privacy/activities",
        json={
            "activity_code": "ROPA-ADV-16",
            "name": "RoPA for DPIA Self Review",
            "purpose_description": "Testing self review block",
            "legal_basis": "CONSENT",
            "data_subject_categories": "CUSTOMERS",
            "personal_data_categories": "IDENTIFIERS",
        },
        headers=manager_headers,
    )
    act_id = act_res.json()["id"]

    dpia_res = client.post(
        "/api/v1/privacy/dpia",
        json={"assessment_code": "DPIA-ADV-16", "processing_activity_id": act_id},
        headers=manager_headers,
    )
    dpia_id = dpia_res.json()["id"]

    # Manager (creator) tries to approve own DPIA
    res = client.post(
        f"/api/v1/privacy/dpia/{dpia_id}/review",
        json={"decision": "APPROVED", "recommendation_notes": "Self approval attempt"},
        headers=manager_headers,
    )
    assert res.status_code == 403
    assert "Segregation of Duties" in res.json()["detail"]


def test_adv_p16_17_transfer_requester_self_approval(client: TestClient, adv_p16_fixture):
    """ADV-P16-17: Transfer requester self-approval attempt returns HTTP 403 Forbidden."""
    manager = adv_p16_fixture["apex_manager"]
    manager_headers = get_token_headers(manager)

    act_res = client.post(
        "/api/v1/privacy/activities",
        json={
            "activity_code": "ROPA-ADV-17",
            "name": "RoPA for Transfer Self Review",
            "purpose_description": "Testing transfer self review block",
            "legal_basis": "CONSENT",
            "data_subject_categories": "CUSTOMERS",
            "personal_data_categories": "IDENTIFIERS",
        },
        headers=manager_headers,
    )
    act_id = act_res.json()["id"]

    tia_res = client.post(
        "/api/v1/privacy/transfers",
        json={"transfer_code": "TIA-ADV-17", "processing_activity_id": act_id, "destination_country": "UK"},
        headers=manager_headers,
    )
    tia_id = tia_res.json()["id"]

    # Manager (requester) tries to approve own transfer
    res = client.post(
        f"/api/v1/privacy/transfers/{tia_id}/review",
        json={"decision": "APPROVED", "reviewer_notes": "Self approval attempt"},
        headers=manager_headers,
    )
    assert res.status_code == 403
    assert "Segregation of Duties" in res.json()["detail"]


def test_adv_p16_18_dpia_approval_replay(client: TestClient, adv_p16_fixture):
    """ADV-P16-18: Replaying review on finalized DPIA returns HTTP 409 Conflict."""
    analyst = adv_p16_fixture["apex_grc_analyst"]
    manager = adv_p16_fixture["apex_manager"]
    analyst_headers = get_token_headers(analyst)
    manager_headers = get_token_headers(manager)

    act_res = client.post(
        "/api/v1/privacy/activities",
        json={
            "activity_code": "ROPA-ADV-18",
            "name": "RoPA for Replay Test",
            "purpose_description": "Testing DPIA replay",
            "legal_basis": "CONSENT",
            "data_subject_categories": "CUSTOMERS",
            "personal_data_categories": "IDENTIFIERS",
        },
        headers=analyst_headers,
    )
    act_id = act_res.json()["id"]

    dpia_res = client.post(
        "/api/v1/privacy/dpia",
        json={"assessment_code": "DPIA-ADV-18", "processing_activity_id": act_id},
        headers=analyst_headers,
    )
    dpia_id = dpia_res.json()["id"]

    # First review (APPROVED)
    client.post(
        f"/api/v1/privacy/dpia/{dpia_id}/review",
        json={"decision": "APPROVED", "recommendation_notes": "Initial signoff"},
        headers=manager_headers,
    )

    # Replay review
    replay_res = client.post(
        f"/api/v1/privacy/dpia/{dpia_id}/review",
        json={"decision": "REJECTED", "recommendation_notes": "Replay attempt"},
        headers=manager_headers,
    )
    assert replay_res.status_code == 409


def test_adv_p16_19_transfer_approval_replay(client: TestClient, adv_p16_fixture):
    """ADV-P16-19: Replaying review on finalized transfer returns HTTP 409 Conflict."""
    analyst = adv_p16_fixture["apex_grc_analyst"]
    manager = adv_p16_fixture["apex_manager"]
    analyst_headers = get_token_headers(analyst)
    manager_headers = get_token_headers(manager)

    act_res = client.post(
        "/api/v1/privacy/activities",
        json={
            "activity_code": "ROPA-ADV-19",
            "name": "RoPA for Transfer Replay",
            "purpose_description": "Testing TIA replay",
            "legal_basis": "CONSENT",
            "data_subject_categories": "CUSTOMERS",
            "personal_data_categories": "IDENTIFIERS",
        },
        headers=analyst_headers,
    )
    act_id = act_res.json()["id"]

    tia_res = client.post(
        "/api/v1/privacy/transfers",
        json={"transfer_code": "TIA-ADV-19", "processing_activity_id": act_id, "destination_country": "UK"},
        headers=analyst_headers,
    )
    tia_id = tia_res.json()["id"]

    # Approve transfer
    client.post(
        f"/api/v1/privacy/transfers/{tia_id}/review",
        json={"decision": "APPROVED", "reviewer_notes": "Initial signoff"},
        headers=manager_headers,
    )

    # Replay review
    replay_res = client.post(
        f"/api/v1/privacy/transfers/{tia_id}/review",
        json={"decision": "REJECTED", "reviewer_notes": "Replay attempt"},
        headers=manager_headers,
    )
    assert replay_res.status_code == 409


# ─── 4. RBAC & PRIVILEGE BOUNDARY VECTORS (ADV-P16-20 to ADV-P16-23) ───────────

def test_adv_p16_20_unauthorized_grc_approval(client: TestClient, adv_p16_fixture):
    """ADV-P16-20: GRC Analyst attempting approval review returns HTTP 403 Forbidden."""
    analyst_headers = get_token_headers(adv_p16_fixture["apex_grc_analyst"])

    res = client.post(
        "/api/v1/privacy/dpia/1/review",
        json={"decision": "APPROVED", "recommendation_notes": "Unauthorized approval"},
        headers=analyst_headers,
    )
    assert res.status_code == 403


def test_adv_p16_21_unauthorized_security_analyst_mutation(client: TestClient, adv_p16_fixture):
    """ADV-P16-21: Security Analyst attempting RoPA creation returns HTTP 403 Forbidden."""
    sec_headers = get_token_headers(adv_p16_fixture["apex_sec_analyst"])

    res = client.post(
        "/api/v1/privacy/activities",
        json={
            "activity_code": "ROPA-ADV-21",
            "name": "Sec Analyst Activity",
            "purpose_description": "Unauthorized creation",
            "legal_basis": "CONSENT",
            "data_subject_categories": "CUSTOMERS",
            "personal_data_categories": "IDENTIFIERS",
        },
        headers=sec_headers,
    )
    assert res.status_code == 403


def test_adv_p16_22_auditor_mutation_attempt(client: TestClient, adv_p16_fixture):
    """ADV-P16-22: Auditor attempting data asset creation returns HTTP 403 Forbidden."""
    auditor_headers = get_token_headers(adv_p16_fixture["apex_auditor"])

    res = client.post(
        "/api/v1/privacy/data-assets",
        json={"asset_code": "DA-ADV-22", "name": "Auditor Asset"},
        headers=auditor_headers,
    )
    assert res.status_code == 403


def test_adv_p16_23_viewer_mutation_attempt(client: TestClient, adv_p16_fixture):
    """ADV-P16-23: Viewer attempting DPIA creation returns HTTP 403 Forbidden."""
    viewer_headers = get_token_headers(adv_p16_fixture["apex_viewer"])

    res = client.post(
        "/api/v1/privacy/dpia",
        json={"assessment_code": "DPIA-ADV-23", "processing_activity_id": 1},
        headers=viewer_headers,
    )
    assert res.status_code == 403


# ─── 5. STATE MACHINE & BOUNDARY VECTORS (ADV-P16-24 to ADV-P16-25) ─────────────

def test_adv_p16_24_illegal_lifecycle_and_retired_mutation(client: TestClient, adv_p16_fixture):
    """ADV-P16-24: Illegal lifecycle jumps and mutations on RETIRED records return HTTP 400."""
    admin_headers = get_token_headers(adv_p16_fixture["apex_admin"])

    create_res = client.post(
        "/api/v1/privacy/activities",
        json={
            "activity_code": "ROPA-ADV-24",
            "name": "State Machine Activity",
            "purpose_description": "Testing illegal jumps",
            "legal_basis": "CONSENT",
            "data_subject_categories": "CUSTOMERS",
            "personal_data_categories": "IDENTIFIERS",
        },
        headers=admin_headers,
    )
    act_id = create_res.json()["id"]

    # 1. Illegal jump: DRAFT -> ACTIVE
    jump_res = client.patch(
        f"/api/v1/privacy/activities/{act_id}/status",
        json={"lifecycle_state": "ACTIVE"},
        headers=admin_headers,
    )
    assert jump_res.status_code == 400

    # 2. Retire activity
    client.patch(f"/api/v1/privacy/activities/{act_id}/status", json={"lifecycle_state": "ARCHIVED"}, headers=admin_headers)
    client.patch(f"/api/v1/privacy/activities/{act_id}/status", json={"lifecycle_state": "RETIRED"}, headers=admin_headers)

    # 3. Mutating RETIRED activity
    mut_res = client.put(
        f"/api/v1/privacy/activities/{act_id}",
        json={"name": "Attacker Trying to Modify Retired Record"},
        headers=admin_headers,
    )
    assert mut_res.status_code == 400


def test_adv_p16_25_malicious_boundary_and_mass_assignment(client: TestClient, adv_p16_fixture):
    """ADV-P16-25: Out-of-bounds numbers rejected (422) and mass-assignment fields ignored."""
    admin_headers = get_token_headers(adv_p16_fixture["apex_admin"])

    # 1. Out of bounds score (> 100.0) -> HTTP 422 Unprocessable Entity
    bad_score_res = client.post(
        "/api/v1/privacy/dpia",
        json={
            "assessment_code": "DPIA-ADV-25-BAD",
            "processing_activity_id": 1,
            "necessity_proportionality_score": 999.0,  # Violates le=100.0
        },
        headers=admin_headers,
    )
    assert bad_score_res.status_code == 422

    # 2. Mass-assignment attack with extra injection fields
    payload = {
        "asset_code": "DA-ADV-25-MASS",
        "name": "Mass Assignment Asset",
        "__proto__": "admin",
        "is_admin": True,
        "role": "SUPERUSER",
        "organization_id": 999,
    }
    good_res = client.post("/api/v1/privacy/data-assets", json=payload, headers=admin_headers)
    assert good_res.status_code == 201
    data = good_res.json()
    assert data["asset_code"] == "DA-ADV-25-MASS"
    assert "role" not in data
    assert "is_admin" not in data

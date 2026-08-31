import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.permissions import RoleEnum
from app.core.security import get_password_hash
from app.models.ai_governance import (
    AIApprovalStatusEnum,
    AIAutonomyLevelEnum,
    AIDataSensitivityEnum,
    AIHostingTypeEnum,
    AILifecycleStateEnum,
    AIRegulatoryTierEnum,
    AISystem,
    AISystemTypeEnum,
)
from app.models.audit_engagement import Audit, AuditTypeEnum, AuditStatusEnum
from app.models.organization import Organization
from app.models.remediation import (
    RemediationPlan,
    RemediationRootCauseClassificationEnum,
    RemediationSeverityEnum,
    RemediationSourceTypeEnum,
)
from app.models.resilience import BusinessProcess, CriticalityTierEnum
from app.models.tprm import Vendor, VendorStatusEnum, VendorTierEnum
from app.models.user import User
from tests.conftest import get_token_headers


@pytest.fixture
def adv_p15_fixture(db: Session, org_apex: Organization, org_meridian: Organization):
    """Setup multi-tenant entities and adversarial actors for ADV-P15 test suite."""
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
        apex_admin, apex_manager, apex_manager_2, apex_sec_analyst,
        apex_grc_analyst, apex_auditor, apex_viewer, meridian_admin,
    ])
    db.commit()

    # Audits
    audit_apex = Audit(
        organization_id=org_apex.id,
        title="Apex Audit",
        objective="Validate controls",
        audit_type=AuditTypeEnum.INTERNAL,
        status=AuditStatusEnum.PLANNED,
    )
    audit_meridian = Audit(
        organization_id=org_meridian.id,
        title="Meridian Audit",
        objective="Validate controls",
        audit_type=AuditTypeEnum.INTERNAL,
        status=AuditStatusEnum.PLANNED,
    )
    db.add_all([audit_apex, audit_meridian])
    db.commit()

    # Apex GRC Entities
    proc_apex = BusinessProcess(
        organization_id=org_apex.id,
        name="Apex Trading Gateway",
        owner_id=apex_admin.id,
        criticality_tier=CriticalityTierEnum.TIER_1,
    )
    vendor_apex = Vendor(
        organization_id=org_apex.id,
        legal_name="Apex AI Vendor",
        vendor_code="VND-ADV-APX",
        calculated_tier=VendorTierEnum.TIER_1_CRITICAL,
        vendor_status=VendorStatusEnum.APPROVED,
    )
    remediation_apex = RemediationPlan(
        organization_id=org_apex.id,
        plan_code="REM-ADV-APX",
        title="Apex Safety Plan",
        problem_statement="Mitigate prompt injection and alignment drift",
        root_cause_classification=RemediationRootCauseClassificationEnum.CONTROL_DEFICIENCY,
        source_type=RemediationSourceTypeEnum.AUDIT,
        audit_id=audit_apex.id,
        severity=RemediationSeverityEnum.CRITICAL,
        plan_owner_id=apex_admin.id,
    )

    # Meridian GRC Entities (Tenant B)
    proc_meridian = BusinessProcess(
        organization_id=org_meridian.id,
        name="Meridian Critical Process",
        owner_id=meridian_admin.id,
        criticality_tier=CriticalityTierEnum.TIER_1,
    )
    vendor_meridian = Vendor(
        organization_id=org_meridian.id,
        legal_name="Meridian Foreign Vendor",
        vendor_code="VND-ADV-MER",
        calculated_tier=VendorTierEnum.TIER_1_CRITICAL,
        vendor_status=VendorStatusEnum.APPROVED,
    )
    remediation_meridian = RemediationPlan(
        organization_id=org_meridian.id,
        plan_code="REM-ADV-MER",
        title="Meridian Foreign Remediation",
        problem_statement="Foreign remediation plan",
        root_cause_classification=RemediationRootCauseClassificationEnum.CONTROL_DEFICIENCY,
        source_type=RemediationSourceTypeEnum.AUDIT,
        audit_id=audit_meridian.id,
        severity=RemediationSeverityEnum.HIGH,
        plan_owner_id=meridian_admin.id,
    )

    db.add_all([proc_apex, vendor_apex, remediation_apex, proc_meridian, vendor_meridian, remediation_meridian])
    db.commit()

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
        "proc_apex": proc_apex,
        "vendor_apex": vendor_apex,
        "remediation_apex": remediation_apex,
        "proc_meridian": proc_meridian,
        "vendor_meridian": vendor_meridian,
        "remediation_meridian": remediation_meridian,
    }


# ─── ADV-P15-01 to ADV-P15-03: Cross-Tenant System Operations ────────────────

def test_adv_p15_01_cross_tenant_ai_system_get(client: TestClient, adv_p15_fixture):
    """ADV-P15-01: Cross-tenant AI system GET returns 404 Not Found."""
    headers_apex = get_token_headers(adv_p15_fixture["apex_admin"])
    headers_meridian = get_token_headers(adv_p15_fixture["meridian_admin"])

    create_res = client.post(
        "/api/v1/ai-governance/systems",
        json={"system_code": "ADV-SYS-01", "name": "Apex AI", "system_type": "LLM_APPLICATION", "regulatory_tier": "HIGH_RISK", "hosting_type": "CLOUD_THIRD_PARTY"},
        headers=headers_apex,
    )
    apex_sys_id = create_res.json()["id"]

    res = client.get(f"/api/v1/ai-governance/systems/{apex_sys_id}", headers=headers_meridian)
    assert res.status_code == 404


def test_adv_p15_02_cross_tenant_ai_system_update(client: TestClient, adv_p15_fixture):
    """ADV-P15-02: Cross-tenant AI system UPDATE returns 404 Not Found."""
    headers_apex = get_token_headers(adv_p15_fixture["apex_admin"])
    headers_meridian = get_token_headers(adv_p15_fixture["meridian_admin"])

    create_res = client.post(
        "/api/v1/ai-governance/systems",
        json={"system_code": "ADV-SYS-02", "name": "Apex AI", "system_type": "LLM_APPLICATION", "regulatory_tier": "HIGH_RISK", "hosting_type": "CLOUD_THIRD_PARTY"},
        headers=headers_apex,
    )
    apex_sys_id = create_res.json()["id"]

    res = client.put(f"/api/v1/ai-governance/systems/{apex_sys_id}", json={"name": "Attacker Name"}, headers=headers_meridian)
    assert res.status_code == 404


def test_adv_p15_03_cross_tenant_ai_system_delete(client: TestClient, adv_p15_fixture):
    """ADV-P15-03: Cross-tenant AI system DELETE returns 404 Not Found."""
    headers_apex = get_token_headers(adv_p15_fixture["apex_admin"])
    headers_meridian = get_token_headers(adv_p15_fixture["meridian_admin"])

    create_res = client.post(
        "/api/v1/ai-governance/systems",
        json={"system_code": "ADV-SYS-03", "name": "Apex AI", "system_type": "LLM_APPLICATION", "regulatory_tier": "MINIMAL_RISK", "hosting_type": "CLOUD_THIRD_PARTY"},
        headers=headers_apex,
    )
    apex_sys_id = create_res.json()["id"]

    res = client.delete(f"/api/v1/ai-governance/systems/{apex_sys_id}", headers=headers_meridian)
    assert res.status_code == 404


# ─── ADV-P15-04 to ADV-P15-06: Cross-Tenant Model Cards & Approvals ───────────

def test_adv_p15_04_cross_tenant_model_card_access(client: TestClient, adv_p15_fixture):
    """ADV-P15-04: Cross-tenant model-card access returns 404 Not Found."""
    headers_apex = get_token_headers(adv_p15_fixture["apex_admin"])
    headers_meridian = get_token_headers(adv_p15_fixture["meridian_admin"])

    create_res = client.post(
        "/api/v1/ai-governance/systems",
        json={"system_code": "ADV-SYS-04", "name": "Apex AI", "system_type": "LLM_APPLICATION", "regulatory_tier": "LIMITED_RISK", "hosting_type": "CLOUD_THIRD_PARTY"},
        headers=headers_apex,
    )
    apex_sys_id = create_res.json()["id"]

    card_res = client.post(
        f"/api/v1/ai-governance/systems/{apex_sys_id}/model-cards",
        json={"version": "1.0.0", "intended_use": "Classified trading signals"},
        headers=headers_apex,
    )
    card_id = card_res.json()["id"]

    res = client.get(f"/api/v1/ai-governance/model-cards/{card_id}", headers=headers_meridian)
    assert res.status_code == 404


def test_adv_p15_05_cross_tenant_model_card_creation(client: TestClient, adv_p15_fixture):
    """ADV-P15-05: Cross-tenant model-card creation on foreign AI system returns 404 Not Found."""
    headers_apex = get_token_headers(adv_p15_fixture["apex_admin"])
    headers_meridian = get_token_headers(adv_p15_fixture["meridian_admin"])

    create_res = client.post(
        "/api/v1/ai-governance/systems",
        json={"system_code": "ADV-SYS-05", "name": "Apex AI", "system_type": "LLM_APPLICATION", "regulatory_tier": "LIMITED_RISK", "hosting_type": "CLOUD_THIRD_PARTY"},
        headers=headers_apex,
    )
    apex_sys_id = create_res.json()["id"]

    res = client.post(
        f"/api/v1/ai-governance/systems/{apex_sys_id}/model-cards",
        json={"version": "1.0.0", "intended_use": "Poisoned model card"},
        headers=headers_meridian,
    )
    assert res.status_code == 404


def test_adv_p15_06_cross_tenant_deployment_approval_access(client: TestClient, adv_p15_fixture):
    """ADV-P15-06: Cross-tenant deployment approval access returns 404 Not Found."""
    headers_apex = get_token_headers(adv_p15_fixture["apex_admin"])
    headers_meridian = get_token_headers(adv_p15_fixture["meridian_admin"])

    create_res = client.post(
        "/api/v1/ai-governance/systems",
        json={"system_code": "ADV-SYS-06", "name": "Apex AI", "system_type": "LLM_APPLICATION", "regulatory_tier": "HIGH_RISK", "hosting_type": "CLOUD_THIRD_PARTY"},
        headers=headers_apex,
    )
    apex_sys_id = create_res.json()["id"]

    app_res = client.post(
        f"/api/v1/ai-governance/systems/{apex_sys_id}/approvals",
        json={"target_environment": "STAGING", "risk_acceptance_justification": "Approved", "human_oversight_measures": "Supervision"},
        headers=headers_apex,
    )
    approval_id = app_res.json()["id"]

    res = client.get(f"/api/v1/ai-governance/approvals/{approval_id}", headers=headers_meridian)
    assert res.status_code == 404


# ─── ADV-P15-07 to ADV-P15-09: Cross-Tenant Linkage Attacks ──────────────────

def test_adv_p15_07_cross_tenant_business_process_linkage(client: TestClient, adv_p15_fixture):
    """ADV-P15-07: Linking a foreign tenant's BusinessProcess returns 404 Not Found."""
    headers_apex = get_token_headers(adv_p15_fixture["apex_admin"])
    foreign_proc_id = adv_p15_fixture["proc_meridian"].id

    res = client.post(
        "/api/v1/ai-governance/systems",
        json={
            "system_code": "ADV-SYS-07",
            "name": "IDOR Process AI",
            "system_type": "LLM_APPLICATION",
            "regulatory_tier": "HIGH_RISK",
            "hosting_type": "CLOUD_THIRD_PARTY",
            "business_process_id": foreign_proc_id,
        },
        headers=headers_apex,
    )
    assert res.status_code == 404
    assert "not found" in res.json()["detail"]


def test_adv_p15_08_cross_tenant_vendor_linkage(client: TestClient, adv_p15_fixture):
    """ADV-P15-08: Linking a foreign tenant's Vendor returns 404 Not Found."""
    headers_apex = get_token_headers(adv_p15_fixture["apex_admin"])
    foreign_vendor_id = adv_p15_fixture["vendor_meridian"].id

    res = client.post(
        "/api/v1/ai-governance/systems",
        json={
            "system_code": "ADV-SYS-08",
            "name": "IDOR Vendor AI",
            "system_type": "LLM_APPLICATION",
            "regulatory_tier": "HIGH_RISK",
            "hosting_type": "CLOUD_THIRD_PARTY",
            "vendor_id": foreign_vendor_id,
        },
        headers=headers_apex,
    )
    assert res.status_code == 404
    assert "not found" in res.json()["detail"]


def test_adv_p15_09_cross_tenant_remediation_plan_linkage(client: TestClient, adv_p15_fixture):
    """ADV-P15-09: Linking a foreign tenant's RemediationPlan returns 404 Not Found."""
    headers_apex = get_token_headers(adv_p15_fixture["apex_admin"])
    foreign_plan_id = adv_p15_fixture["remediation_meridian"].id

    res = client.post(
        "/api/v1/ai-governance/systems",
        json={
            "system_code": "ADV-SYS-09",
            "name": "IDOR Remediation AI",
            "system_type": "LLM_APPLICATION",
            "regulatory_tier": "HIGH_RISK",
            "hosting_type": "CLOUD_THIRD_PARTY",
            "remediation_plan_id": foreign_plan_id,
        },
        headers=headers_apex,
    )
    assert res.status_code == 404
    assert "not found" in res.json()["detail"]


# ─── ADV-P15-10 to ADV-P15-11: Authentication & Token Security ────────────────

def test_adv_p15_10_forged_unauthenticated_jwt(client: TestClient, adv_p15_fixture):
    """ADV-P15-10: Forged/unauthenticated JWT returns 401 Unauthorized."""
    headers = {"Authorization": "Bearer forged.token.signature"}
    res = client.get("/api/v1/ai-governance/systems", headers=headers)
    assert res.status_code == 401


def test_adv_p15_11_invalid_jwt(client: TestClient, adv_p15_fixture):
    """ADV-P15-11: Invalid/malformed JWT header returns 401 Unauthorized."""
    headers = {"Authorization": "Basic invalid_format"}
    res = client.get("/api/v1/ai-governance/systems", headers=headers)
    assert res.status_code == 401


# ─── ADV-P15-12 to ADV-P15-15: RBAC Boundary Violations ──────────────────────

def test_adv_p15_12_viewer_mutation_attempt(client: TestClient, adv_p15_fixture):
    """ADV-P15-12: Viewer attempting system mutation returns 403 Forbidden."""
    headers = get_token_headers(adv_p15_fixture["apex_viewer"])
    res = client.post(
        "/api/v1/ai-governance/systems",
        json={"system_code": "ADV-SYS-12", "name": "Viewer Sys", "system_type": "LLM_APPLICATION", "regulatory_tier": "MINIMAL_RISK", "hosting_type": "CLOUD_THIRD_PARTY"},
        headers=headers,
    )
    assert res.status_code == 403


def test_adv_p15_13_auditor_mutation_attempt(client: TestClient, adv_p15_fixture):
    """ADV-P15-13: Auditor attempting system deletion returns 403 Forbidden."""
    headers_admin = get_token_headers(adv_p15_fixture["apex_admin"])
    headers_auditor = get_token_headers(adv_p15_fixture["apex_auditor"])

    create_res = client.post(
        "/api/v1/ai-governance/systems",
        json={"system_code": "ADV-SYS-13", "name": "Audit Target", "system_type": "LLM_APPLICATION", "regulatory_tier": "MINIMAL_RISK", "hosting_type": "CLOUD_THIRD_PARTY"},
        headers=headers_admin,
    )
    sys_id = create_res.json()["id"]

    res = client.delete(f"/api/v1/ai-governance/systems/{sys_id}", headers=headers_auditor)
    assert res.status_code == 403


def test_adv_p15_14_grc_analyst_approval_attempt(client: TestClient, adv_p15_fixture):
    """ADV-P15-14: GRC Analyst attempting to approve deployment returns 403 Forbidden."""
    headers_admin = get_token_headers(adv_p15_fixture["apex_admin"])
    headers_grc = get_token_headers(adv_p15_fixture["apex_grc_analyst"])

    create_res = client.post(
        "/api/v1/ai-governance/systems",
        json={"system_code": "ADV-SYS-14", "name": "Approval Target", "system_type": "LLM_APPLICATION", "regulatory_tier": "HIGH_RISK", "hosting_type": "CLOUD_THIRD_PARTY"},
        headers=headers_admin,
    )
    sys_id = create_res.json()["id"]

    app_res = client.post(
        f"/api/v1/ai-governance/systems/{sys_id}/approvals",
        json={"target_environment": "STAGING", "risk_acceptance_justification": "Ready", "human_oversight_measures": "Control verified"},
        headers=headers_admin,
    )
    approval_id = app_res.json()["id"]

    res = client.post(
        f"/api/v1/ai-governance/approvals/{approval_id}/review",
        json={"decision": "APPROVED"},
        headers=headers_grc,
    )
    assert res.status_code == 403


def test_adv_p15_15_security_analyst_unauthorized_mutation(client: TestClient, adv_p15_fixture):
    """ADV-P15-15: Security Analyst attempting to create an AI system returns 403 Forbidden."""
    headers = get_token_headers(adv_p15_fixture["apex_sec_analyst"])
    res = client.post(
        "/api/v1/ai-governance/systems",
        json={"system_code": "ADV-SYS-15", "name": "SecAnalyst AI", "system_type": "LLM_APPLICATION", "regulatory_tier": "MINIMAL_RISK", "hosting_type": "CLOUD_THIRD_PARTY"},
        headers=headers,
    )
    assert res.status_code == 403


# ─── ADV-P15-16 to ADV-P15-21: Four-Eyes & Mass-Assignment Invariants ─────────

def test_adv_p15_16_requester_self_approval(client: TestClient, adv_p15_fixture):
    """ADV-P15-16: Requester attempting self-approval (even as Manager) returns 403 Forbidden."""
    headers_mgr = get_token_headers(adv_p15_fixture["apex_manager"])

    create_res = client.post(
        "/api/v1/ai-governance/systems",
        json={"system_code": "ADV-SYS-16", "name": "Self Review Sys", "system_type": "AGENTIC_WORKFLOW", "regulatory_tier": "HIGH_RISK", "hosting_type": "CLOUD_THIRD_PARTY"},
        headers=headers_mgr,
    )
    sys_id = create_res.json()["id"]

    app_res = client.post(
        f"/api/v1/ai-governance/systems/{sys_id}/approvals",
        json={"target_environment": "STAGING", "risk_acceptance_justification": "Self request", "human_oversight_measures": "None required"},
        headers=headers_mgr,
    )
    approval_id = app_res.json()["id"]

    # Manager attempts to review own request
    res = client.post(
        f"/api/v1/ai-governance/approvals/{approval_id}/review",
        json={"decision": "APPROVED", "reviewer_notes": "Self approved"},
        headers=headers_mgr,
    )
    assert res.status_code == 403
    assert "Segregation of Duties" in res.json()["detail"]


def test_adv_p15_17_spoofed_reviewer_identity(client: TestClient, adv_p15_fixture):
    """ADV-P15-17: Spoofed reviewed_by_id in payload is ignored; server uses authenticated user."""
    headers_mgr1 = get_token_headers(adv_p15_fixture["apex_manager"])
    headers_mgr2 = get_token_headers(adv_p15_fixture["apex_manager_2"])

    create_res = client.post(
        "/api/v1/ai-governance/systems",
        json={"system_code": "ADV-SYS-17", "name": "Spoof Reviewer", "system_type": "LLM_APPLICATION", "regulatory_tier": "HIGH_RISK", "hosting_type": "CLOUD_THIRD_PARTY"},
        headers=headers_mgr1,
    )
    sys_id = create_res.json()["id"]

    app_res = client.post(
        f"/api/v1/ai-governance/systems/{sys_id}/approvals",
        json={"target_environment": "STAGING", "risk_acceptance_justification": "Justification", "human_oversight_measures": "Measures"},
        headers=headers_mgr1,
    )
    approval_id = app_res.json()["id"]

    # Manager 2 reviews, trying to spoof reviewed_by_id = admin
    res = client.post(
        f"/api/v1/ai-governance/approvals/{approval_id}/review",
        json={"decision": "APPROVED", "reviewed_by_id": adv_p15_fixture["apex_admin"].id},
        headers=headers_mgr2,
    )
    assert res.status_code == 200
    assert res.json()["reviewed_by_id"] == adv_p15_fixture["apex_manager_2"].id


def test_adv_p15_18_spoofed_requester_identity(client: TestClient, adv_p15_fixture):
    """ADV-P15-18: Spoofed requested_by_id in payload is ignored; server uses authenticated user."""
    headers_mgr = get_token_headers(adv_p15_fixture["apex_manager"])

    create_res = client.post(
        "/api/v1/ai-governance/systems",
        json={"system_code": "ADV-SYS-18", "name": "Spoof Requester", "system_type": "LLM_APPLICATION", "regulatory_tier": "HIGH_RISK", "hosting_type": "CLOUD_THIRD_PARTY"},
        headers=headers_mgr,
    )
    sys_id = create_res.json()["id"]

    res = client.post(
        f"/api/v1/ai-governance/systems/{sys_id}/approvals",
        json={
            "target_environment": "STAGING",
            "risk_acceptance_justification": "Justification",
            "human_oversight_measures": "Measures",
            "requested_by_id": adv_p15_fixture["apex_admin"].id,
        },
        headers=headers_mgr,
    )
    assert res.status_code == 201
    assert res.json()["requested_by_id"] == adv_p15_fixture["apex_manager"].id


def test_adv_p15_19_spoofed_organization_id(client: TestClient, adv_p15_fixture):
    """ADV-P15-19: Spoofed organization_id in payload is ignored; server scopes to user's org."""
    headers = get_token_headers(adv_p15_fixture["apex_admin"])
    foreign_org_id = adv_p15_fixture["org_meridian"].id

    res = client.post(
        "/api/v1/ai-governance/systems",
        json={
            "system_code": "ADV-SYS-19",
            "name": "Org Spoof Model",
            "system_type": "LLM_APPLICATION",
            "regulatory_tier": "MINIMAL_RISK",
            "hosting_type": "CLOUD_THIRD_PARTY",
            "organization_id": foreign_org_id,
        },
        headers=headers,
    )
    assert res.status_code == 201
    assert res.json()["organization_id"] == adv_p15_fixture["org_apex"].id


def test_adv_p15_20_spoofed_lifecycle_state(client: TestClient, adv_p15_fixture):
    """ADV-P15-20: Spoofed lifecycle_state in create payload is ignored; initialized to DEVELOPMENT."""
    headers = get_token_headers(adv_p15_fixture["apex_admin"])

    res = client.post(
        "/api/v1/ai-governance/systems",
        json={
            "system_code": "ADV-SYS-20",
            "name": "State Spoof Model",
            "system_type": "LLM_APPLICATION",
            "regulatory_tier": "HIGH_RISK",
            "hosting_type": "CLOUD_THIRD_PARTY",
            "lifecycle_state": "PRODUCTION",
        },
        headers=headers,
    )
    assert res.status_code == 201
    assert res.json()["lifecycle_state"] == "DEVELOPMENT"


def test_adv_p15_21_spoofed_ari_and_compliance_score(client: TestClient, adv_p15_fixture):
    """ADV-P15-21: Spoofed ARI and compliance score in payload are ignored; calculated server-side."""
    headers = get_token_headers(adv_p15_fixture["apex_admin"])

    res = client.post(
        "/api/v1/ai-governance/systems",
        json={
            "system_code": "ADV-SYS-21",
            "name": "Score Spoof Model",
            "system_type": "LLM_APPLICATION",
            "regulatory_tier": "HIGH_RISK",
            "autonomy_level": "HUMAN_IN_THE_LOOP",
            "data_sensitivity": "INTERNAL",
            "hosting_type": "CLOUD_THIRD_PARTY",
            "algorithmic_risk_index": 0.0,
            "eu_compliance_score": 100.0,
        },
        headers=headers,
    )
    assert res.status_code == 201
    # 65 * 1.0 + 2.0 = 67.00
    assert res.json()["algorithmic_risk_index"] == 67.00
    assert res.json()["eu_compliance_score"] != 100.00


# ─── ADV-P15-22 to ADV-P15-25: Guardrails, Immutability & Replays ─────────────

def test_adv_p15_22_prohibited_ai_production_promotion(client: TestClient, adv_p15_fixture):
    """ADV-P15-22: Prohibited AI system cannot be promoted to PRODUCTION (EU AI Act Art 5)."""
    headers = get_token_headers(adv_p15_fixture["apex_admin"])

    create_res = client.post(
        "/api/v1/ai-governance/systems",
        json={
            "system_code": "ADV-SYS-22",
            "name": "Social Scoring AI",
            "system_type": "PREDICTIVE_ANALYTICS",
            "regulatory_tier": "PROHIBITED",
            "hosting_type": "CLOUD_THIRD_PARTY",
        },
        headers=headers,
    )
    sys_id = create_res.json()["id"]

    client.post(f"/api/v1/ai-governance/systems/{sys_id}/lifecycle", json={"lifecycle_state": "VALIDATION"}, headers=headers)
    client.post(f"/api/v1/ai-governance/systems/{sys_id}/lifecycle", json={"lifecycle_state": "ETHICAL_REVIEW"}, headers=headers)

    # Attempt deployment request -> 409 Conflict
    res = client.post(
        f"/api/v1/ai-governance/systems/{sys_id}/approvals",
        json={"target_environment": "PRODUCTION", "risk_acceptance_justification": "Bypassing EU AI Act", "human_oversight_measures": "No oversight measures"},
        headers=headers,
    )
    assert res.status_code == 409
    assert "prohibited" in res.json()["detail"].lower()


def test_adv_p15_23_decommissioned_system_mutation(client: TestClient, adv_p15_fixture):
    """ADV-P15-23: Decommissioned system is permanently locked against mutations and model cards."""
    headers = get_token_headers(adv_p15_fixture["apex_admin"])

    create_res = client.post(
        "/api/v1/ai-governance/systems",
        json={"system_code": "ADV-SYS-23", "name": "Decom Target", "system_type": "LLM_APPLICATION", "regulatory_tier": "MINIMAL_RISK", "hosting_type": "CLOUD_THIRD_PARTY"},
        headers=headers,
    )
    sys_id = create_res.json()["id"]

    client.post(f"/api/v1/ai-governance/systems/{sys_id}/lifecycle", json={"lifecycle_state": "DECOMMISSIONED"}, headers=headers)

    # Mutation attempt -> 409
    r_put = client.put(f"/api/v1/ai-governance/systems/{sys_id}", json={"name": "Reactivated"}, headers=headers)
    assert r_put.status_code == 409

    # State transition attempt -> 409
    r_state = client.post(f"/api/v1/ai-governance/systems/{sys_id}/lifecycle", json={"lifecycle_state": "DEVELOPMENT"}, headers=headers)
    assert r_state.status_code == 409

    # Model card attachment attempt -> 409
    r_card = client.post(
        f"/api/v1/ai-governance/systems/{sys_id}/model-cards",
        json={"version": "1.0.0", "intended_use": "Post decom use"},
        headers=headers,
    )
    assert r_card.status_code == 409


def test_adv_p15_24_deployment_approval_replay_re_review(client: TestClient, adv_p15_fixture):
    """ADV-P15-24: Replay/re-review of an already decided deployment approval returns 409 Conflict."""
    headers_mgr1 = get_token_headers(adv_p15_fixture["apex_manager"])
    headers_mgr2 = get_token_headers(adv_p15_fixture["apex_manager_2"])

    create_res = client.post(
        "/api/v1/ai-governance/systems",
        json={"system_code": "ADV-SYS-24", "name": "Replay Sys", "system_type": "LLM_APPLICATION", "regulatory_tier": "HIGH_RISK", "hosting_type": "CLOUD_THIRD_PARTY"},
        headers=headers_mgr1,
    )
    sys_id = create_res.json()["id"]

    app_res = client.post(
        f"/api/v1/ai-governance/systems/{sys_id}/approvals",
        json={"target_environment": "STAGING", "risk_acceptance_justification": "Valid justification", "human_oversight_measures": "Supervised HITL"},
        headers=headers_mgr1,
    )
    approval_id = app_res.json()["id"]

    # Manager 2 approves
    r1 = client.post(f"/api/v1/ai-governance/approvals/{approval_id}/review", json={"decision": "APPROVED"}, headers=headers_mgr2)
    assert r1.status_code == 200

    # Attacker attempts to replay/override to REJECTED -> 409 Conflict
    r2 = client.post(f"/api/v1/ai-governance/approvals/{approval_id}/review", json={"decision": "REJECTED"}, headers=headers_mgr2)
    assert r2.status_code == 409


def test_adv_p15_25_invalid_environment_and_illegal_lifecycle_transition(client: TestClient, adv_p15_fixture):
    """ADV-P15-25: Invalid environment raises 422, and promotion without required approval raises 409."""
    headers = get_token_headers(adv_p15_fixture["apex_admin"])

    create_res = client.post(
        "/api/v1/ai-governance/systems",
        json={"system_code": "ADV-SYS-25", "name": "Gate Sys", "system_type": "LLM_APPLICATION", "regulatory_tier": "HIGH_RISK", "hosting_type": "CLOUD_THIRD_PARTY"},
        headers=headers,
    )
    sys_id = create_res.json()["id"]

    # 1. Invalid target environment -> 422
    r_inv = client.post(
        f"/api/v1/ai-governance/systems/{sys_id}/approvals",
        json={"target_environment": "HACKED_ENV", "risk_acceptance_justification": "Valid justification", "human_oversight_measures": "Supervised HITL"},
        headers=headers,
    )
    assert r_inv.status_code == 422

    # 2. Advance to ETHICAL_REVIEW
    client.post(f"/api/v1/ai-governance/systems/{sys_id}/lifecycle", json={"lifecycle_state": "VALIDATION"}, headers=headers)
    client.post(f"/api/v1/ai-governance/systems/{sys_id}/lifecycle", json={"lifecycle_state": "ETHICAL_REVIEW"}, headers=headers)

    # 3. Attempt transition to APPROVED_STAGING without approved deployment request -> 409 Conflict
    r_gate = client.post(
        f"/api/v1/ai-governance/systems/{sys_id}/lifecycle",
        json={"lifecycle_state": "APPROVED_STAGING"},
        headers=headers,
    )
    assert r_gate.status_code == 409
    assert "without an independent APPROVED deployment approval" in r_gate.json()["detail"]

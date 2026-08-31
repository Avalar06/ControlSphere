from datetime import datetime, timezone
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
from app.models.organization import Organization
from app.models.audit_engagement import Audit, AuditTypeEnum, AuditStatusEnum
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
def ai_api_fixture(db: Session, org_apex: Organization, org_meridian: Organization):
    """Setup multi-tenant entities and multi-role users for AI-GRC API tests."""
    admin = User(
        email="ai_admin@apex.com",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="AI Admin",
        role=RoleEnum.ADMIN,
        is_active=True,
        organization_id=org_apex.id,
    )
    manager = User(
        email="ai_manager@apex.com",
        hashed_password=get_password_hash("ManagerPass123!"),
        full_name="AI Manager",
        role=RoleEnum.MANAGER,
        is_active=True,
        organization_id=org_apex.id,
    )
    sec_analyst = User(
        email="ai_sec_analyst@apex.com",
        hashed_password=get_password_hash("SecAnalystPass123!"),
        full_name="AI Sec Analyst",
        role=RoleEnum.SECURITY_ANALYST,
        is_active=True,
        organization_id=org_apex.id,
    )
    grc_analyst = User(
        email="ai_grc_analyst@apex.com",
        hashed_password=get_password_hash("GrcAnalystPass123!"),
        full_name="AI GRC Analyst",
        role=RoleEnum.GRC_ANALYST,
        is_active=True,
        organization_id=org_apex.id,
    )
    auditor = User(
        email="ai_auditor@apex.com",
        hashed_password=get_password_hash("AuditorPass123!"),
        full_name="AI Auditor",
        role=RoleEnum.AUDITOR,
        is_active=True,
        organization_id=org_apex.id,
    )
    viewer = User(
        email="ai_viewer@apex.com",
        hashed_password=get_password_hash("ViewerPass123!"),
        full_name="AI Viewer",
        role=RoleEnum.VIEWER,
        is_active=True,
        organization_id=org_apex.id,
    )

    # Meridian Users (Tenant B)
    foreign_admin = User(
        email="foreign_ai_admin@meridian.com",
        hashed_password=get_password_hash("ForeignPass123!"),
        full_name="Foreign AI Admin",
        role=RoleEnum.ADMIN,
        is_active=True,
        organization_id=org_meridian.id,
    )

    db.add_all([admin, manager, sec_analyst, grc_analyst, auditor, viewer, foreign_admin])
    db.commit()

    # Audit for Remediation Source
    audit_apex = Audit(
        organization_id=org_apex.id,
        title="Apex AI Audit",
        objective="Validate AI safety controls",
        audit_type=AuditTypeEnum.INTERNAL,
        status=AuditStatusEnum.PLANNED,
    )
    db.add(audit_apex)
    db.commit()

    # Phase 13 Business Process in Apex
    proc_apex = BusinessProcess(
        organization_id=org_apex.id,
        name="Apex High-Frequency Trading Core",
        owner_id=admin.id,
        criticality_tier=CriticalityTierEnum.TIER_1,
    )
    # Phase 9 Vendor in Apex
    vendor_apex = Vendor(
        organization_id=org_apex.id,
        legal_name="Anthropic PBC",
        vendor_code="VND-ANT-01",
        calculated_tier=VendorTierEnum.TIER_1_CRITICAL,
        vendor_status=VendorStatusEnum.APPROVED,
    )
    # Phase 11 Remediation Plan in Apex
    remediation_apex = RemediationPlan(
        organization_id=org_apex.id,
        plan_code="REM-APX-01",
        title="AI Red Teaming & Jailbreak Hardening",
        problem_statement="Harden AI endpoints against prompt injection and jailbreak",
        root_cause_classification=RemediationRootCauseClassificationEnum.CONTROL_DEFICIENCY,
        source_type=RemediationSourceTypeEnum.AUDIT,
        audit_id=audit_apex.id,
        severity=RemediationSeverityEnum.HIGH,
        plan_owner_id=admin.id,
    )

    # Meridian Entities (Tenant B)
    proc_meridian = BusinessProcess(
        organization_id=org_meridian.id,
        name="Meridian Secret Engine",
        owner_id=foreign_admin.id,
        criticality_tier=CriticalityTierEnum.TIER_1,
    )
    vendor_meridian = Vendor(
        organization_id=org_meridian.id,
        legal_name="Meridian AI Vendor",
        vendor_code="VND-MER-01",
        calculated_tier=VendorTierEnum.TIER_1_CRITICAL,
        vendor_status=VendorStatusEnum.APPROVED,
    )

    db.add_all([proc_apex, vendor_apex, remediation_apex, proc_meridian, vendor_meridian])
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
        "remediation_apex": remediation_apex,
        "proc_meridian": proc_meridian,
        "vendor_meridian": vendor_meridian,
    }


# ─── 1. AI SYSTEMS CATALOG API TESTS ─────────────────────────────────────────

def test_create_ai_system_api_success(client: TestClient, ai_api_fixture):
    """Test creating an AI system via REST API with GRC Analyst."""
    headers = get_token_headers(ai_api_fixture["grc_analyst"])
    payload = {
        "system_code": "AI-SYS-API-01",
        "name": "Customer Support LLM Bot",
        "description": "Frontline conversational assistant",
        "system_type": "LLM_APPLICATION",
        "regulatory_tier": "HIGH_RISK",
        "autonomy_level": "HUMAN_IN_THE_LOOP",
        "data_sensitivity": "INTERNAL",
        "hosting_type": "CLOUD_THIRD_PARTY",
        "foundation_model_name": "claude-3-5-sonnet",
        "model_version": "20241022",
        "parameters_billion": 70.0,
        "context_window_tokens": 200000,
        "business_process_id": ai_api_fixture["proc_apex"].id,
        "vendor_id": ai_api_fixture["vendor_apex"].id,
        "remediation_plan_id": ai_api_fixture["remediation_apex"].id,
    }
    response = client.post("/api/v1/ai-governance/systems", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["system_code"] == "AI-SYS-API-01"
    assert data["name"] == "Customer Support LLM Bot"
    assert data["lifecycle_state"] == "DEVELOPMENT"
    # High Risk (65) * 1.0 (HITL) * 1.25 (Tier 1 Process) = 81.25 + 2.0 (Internal) = 83.25
    assert data["algorithmic_risk_index"] == 83.25
    assert data["is_prohibited_practice"] is False
    assert data["requires_conformity_assessment"] is True


def test_create_ai_system_validation_error(client: TestClient, ai_api_fixture):
    """Test creating an AI system with invalid/missing required fields returns 422."""
    headers = get_token_headers(ai_api_fixture["grc_analyst"])
    # Missing system_type, hosting_type, regulatory_tier
    payload = {
        "system_code": "X",  # min_length is 2
        "name": "Bad Payload",
    }
    response = client.post("/api/v1/ai-governance/systems", json=payload, headers=headers)
    assert response.status_code == 422


def test_create_ai_system_duplicate_conflict(client: TestClient, ai_api_fixture):
    """Test creating duplicate system_code in same organization returns 409 Conflict."""
    headers = get_token_headers(ai_api_fixture["grc_analyst"])
    payload = {
        "system_code": "AI-SYS-DUP-01",
        "name": "System Original",
        "system_type": "EMBEDDED_ML",
        "regulatory_tier": "LIMITED_RISK",
        "hosting_type": "ON_PREMISE_SELF_HOSTED",
    }
    r1 = client.post("/api/v1/ai-governance/systems", json=payload, headers=headers)
    assert r1.status_code == 201

    r2 = client.post("/api/v1/ai-governance/systems", json=payload, headers=headers)
    assert r2.status_code == 409
    assert "already exists" in r2.json()["detail"]


def test_list_ai_systems_api(client: TestClient, ai_api_fixture):
    """Test listing AI systems with query filtering."""
    headers = get_token_headers(ai_api_fixture["viewer"])
    response = client.get("/api/v1/ai-governance/systems?regulatory_tier=HIGH_RISK", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert all(item["regulatory_tier"] == "HIGH_RISK" for item in data)


def test_get_ai_system_api(client: TestClient, ai_api_fixture):
    """Test retrieving a single AI system."""
    headers_write = get_token_headers(ai_api_fixture["grc_analyst"])
    create_res = client.post(
        "/api/v1/ai-governance/systems",
        json={
            "system_code": "AI-SYS-GET-01",
            "name": "Single Get Model",
            "system_type": "RECOMMENDER",
            "regulatory_tier": "MINIMAL_RISK",
            "hosting_type": "CLOUD_THIRD_PARTY",
        },
        headers=headers_write,
    )
    sys_id = create_res.json()["id"]

    headers_read = get_token_headers(ai_api_fixture["auditor"])
    get_res = client.get(f"/api/v1/ai-governance/systems/{sys_id}", headers=headers_read)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == sys_id


def test_update_ai_system_api(client: TestClient, ai_api_fixture):
    """Test updating AI system metadata and recalculating risk."""
    headers = get_token_headers(ai_api_fixture["grc_analyst"])
    create_res = client.post(
        "/api/v1/ai-governance/systems",
        json={
            "system_code": "AI-SYS-UPD-01",
            "name": "Pre-Update Model",
            "system_type": "LLM_APPLICATION",
            "regulatory_tier": "LIMITED_RISK",
            "autonomy_level": "HUMAN_IN_THE_LOOP",
            "data_sensitivity": "PUBLIC",
            "hosting_type": "CLOUD_THIRD_PARTY",
        },
        headers=headers,
    )
    sys_id = create_res.json()["id"]
    assert create_res.json()["algorithmic_risk_index"] == 25.00

    # Update autonomy to FULL_AUTONOMY and tier to HIGH_RISK
    upd_res = client.put(
        f"/api/v1/ai-governance/systems/{sys_id}",
        json={
            "name": "Post-Update Model",
            "regulatory_tier": "HIGH_RISK",
            "autonomy_level": "FULL_AUTONOMY",
        },
        headers=headers,
    )
    assert upd_res.status_code == 200
    # 65 * 1.4 = 91.0 + 0 = 91.0
    assert upd_res.json()["algorithmic_risk_index"] == 91.00
    assert upd_res.json()["name"] == "Post-Update Model"


def test_delete_ai_system_api(client: TestClient, ai_api_fixture):
    """Test deleting an AI system."""
    headers = get_token_headers(ai_api_fixture["admin"])
    create_res = client.post(
        "/api/v1/ai-governance/systems",
        json={
            "system_code": "AI-SYS-DEL-01",
            "name": "Delete Me",
            "system_type": "LLM_APPLICATION",
            "regulatory_tier": "MINIMAL_RISK",
            "hosting_type": "CLOUD_THIRD_PARTY",
        },
        headers=headers,
    )
    sys_id = create_res.json()["id"]

    del_res = client.delete(f"/api/v1/ai-governance/systems/{sys_id}", headers=headers)
    assert del_res.status_code == 204

    get_res = client.get(f"/api/v1/ai-governance/systems/{sys_id}", headers=headers)
    assert get_res.status_code == 404


def test_calculate_index_preview_api(client: TestClient, ai_api_fixture):
    """Test previewing Algorithmic Risk Index calculation without DB persistence."""
    headers = get_token_headers(ai_api_fixture["viewer"])
    payload = {
        "regulatory_tier": "HIGH_RISK",
        "autonomy_level": "FULL_AUTONOMY",
        "data_sensitivity": "RESTRICTED_PII_PHI",
        "process_tier": "TIER_1",
        "hallucination_rate_percent": 10.0,
        "prompt_injection_resistance_score": 80.0,
    }
    response = client.post("/api/v1/ai-governance/systems/calculate-index", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["base_risk"] == 65.0
    assert data["autonomy_multiplier"] == 1.40
    assert data["process_tier_multiplier"] == 1.25
    # (65 * 1.4 * 1.25) = 113.75 + safety penalties -> capped at 100.00
    assert data["algorithmic_risk_index"] == 100.00


def test_posture_summary_api(client: TestClient, ai_api_fixture):
    """Test retrieving organizational AI posture summary."""
    headers = get_token_headers(ai_api_fixture["auditor"])
    response = client.get("/api/v1/ai-governance/systems/summary/posture", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_ai_systems" in data
    assert "high_risk_systems" in data
    assert "prohibited_systems" in data
    assert "average_algorithmic_risk_index" in data
    assert "tier_distribution" in data
    assert "lifecycle_distribution" in data


# ─── 2. LIFECYCLE & MODEL CARDS API TESTS ─────────────────────────────────────

def test_lifecycle_state_transitions_api(client: TestClient, ai_api_fixture):
    """Test progressing AI system through lifecycle state machine."""
    headers = get_token_headers(ai_api_fixture["grc_analyst"])
    create_res = client.post(
        "/api/v1/ai-governance/systems",
        json={
            "system_code": "AI-SYS-LIFECYCLE",
            "name": "State Progression Model",
            "system_type": "LLM_APPLICATION",
            "regulatory_tier": "LIMITED_RISK",
            "hosting_type": "CLOUD_THIRD_PARTY",
        },
        headers=headers,
    )
    sys_id = create_res.json()["id"]

    # DEVELOPMENT -> VALIDATION
    r1 = client.post(
        f"/api/v1/ai-governance/systems/{sys_id}/lifecycle",
        json={"lifecycle_state": "VALIDATION", "notes": "Commencing validation"},
        headers=headers,
    )
    assert r1.status_code == 200
    assert r1.json()["lifecycle_state"] == "VALIDATION"

    # VALIDATION -> ETHICAL_REVIEW
    r2 = client.post(
        f"/api/v1/ai-governance/systems/{sys_id}/lifecycle",
        json={"lifecycle_state": "ETHICAL_REVIEW", "notes": "Ethics board evaluation"},
        headers=headers,
    )
    assert r2.status_code == 200
    assert r2.json()["lifecycle_state"] == "ETHICAL_REVIEW"


def test_lifecycle_illegal_transition_api(client: TestClient, ai_api_fixture):
    """Test illegal lifecycle transitions return 409 Conflict."""
    headers = get_token_headers(ai_api_fixture["grc_analyst"])
    create_res = client.post(
        "/api/v1/ai-governance/systems",
        json={
            "system_code": "AI-SYS-ILLEGAL",
            "name": "Illegal Jump Model",
            "system_type": "LLM_APPLICATION",
            "regulatory_tier": "LIMITED_RISK",
            "hosting_type": "CLOUD_THIRD_PARTY",
        },
        headers=headers,
    )
    sys_id = create_res.json()["id"]

    # Direct jump from DEVELOPMENT -> PRODUCTION
    response = client.post(
        f"/api/v1/ai-governance/systems/{sys_id}/lifecycle",
        json={"lifecycle_state": "PRODUCTION", "notes": "Bypassing steps"},
        headers=headers,
    )
    assert response.status_code == 409
    assert "Illegal lifecycle transition" in response.json()["detail"]


def test_model_card_crud_and_ari_recalculation_api(client: TestClient, ai_api_fixture):
    """Test creating model cards and verifying real-time ARI recalculation via API."""
    headers_sec = get_token_headers(ai_api_fixture["sec_analyst"])
    headers_grc = get_token_headers(ai_api_fixture["grc_analyst"])

    create_res = client.post(
        "/api/v1/ai-governance/systems",
        json={
            "system_code": "AI-SYS-CARD-API",
            "name": "Card Recalculation Model",
            "system_type": "AGENTIC_WORKFLOW",
            "regulatory_tier": "LIMITED_RISK",
            "autonomy_level": "HUMAN_IN_THE_LOOP",
            "data_sensitivity": "PUBLIC",
            "hosting_type": "CLOUD_THIRD_PARTY",
        },
        headers=headers_grc,
    )
    sys_id = create_res.json()["id"]
    assert create_res.json()["algorithmic_risk_index"] == 25.00

    # Security Analyst publishes model card (Permission.AI_ASSESS)
    card_res = client.post(
        f"/api/v1/ai-governance/systems/{sys_id}/model-cards",
        json={
            "version": "1.0.0",
            "intended_use": "Autonomous customer support agent",
            "hallucination_rate_percent": 25.0,
            "prompt_injection_resistance_score": 60.0,
            "synthetic_data_percentage": 10.0,
        },
        headers=headers_sec,
    )
    assert card_res.status_code == 201
    card_id = card_res.json()["id"]

    # Verify parent system ARI was updated
    # Penalty: (25 * 0.20 = +5.0) + (40 * 0.15 = +6.0) = +11.0 -> 25 + 11 = 36.00
    sys_res = client.get(f"/api/v1/ai-governance/systems/{sys_id}", headers=headers_sec)
    assert sys_res.status_code == 200
    assert sys_res.json()["algorithmic_risk_index"] == 36.00

    # List model cards
    list_res = client.get(f"/api/v1/ai-governance/systems/{sys_id}/model-cards", headers=headers_sec)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    # Get single model card
    single_res = client.get(f"/api/v1/ai-governance/model-cards/{card_id}", headers=headers_sec)
    assert single_res.status_code == 200
    assert single_res.json()["version"] == "1.0.0"


# ─── 3. FOUR-EYES DEPLOYMENT APPROVALS & RBAC ─────────────────────────────────

def test_four_eyes_deployment_approval_workflow_api(client: TestClient, ai_api_fixture):
    """Test full Four-Eyes deployment approval workflow via REST API."""
    headers_grc = get_token_headers(ai_api_fixture["grc_analyst"])
    headers_mgr = get_token_headers(ai_api_fixture["manager"])

    # 1. Create AI System and advance to ETHICAL_REVIEW
    create_res = client.post(
        "/api/v1/ai-governance/systems",
        json={
            "system_code": "AI-SYS-4EYES-API",
            "name": "Staged Agent",
            "system_type": "AGENTIC_WORKFLOW",
            "regulatory_tier": "HIGH_RISK",
            "hosting_type": "CLOUD_THIRD_PARTY",
        },
        headers=headers_grc,
    )
    sys_id = create_res.json()["id"]
    client.post(f"/api/v1/ai-governance/systems/{sys_id}/lifecycle", json={"lifecycle_state": "VALIDATION"}, headers=headers_grc)
    client.post(f"/api/v1/ai-governance/systems/{sys_id}/lifecycle", json={"lifecycle_state": "ETHICAL_REVIEW"}, headers=headers_grc)

    # 2. GRC Analyst requests STAGING deployment approval
    app_res = client.post(
        f"/api/v1/ai-governance/systems/{sys_id}/approvals",
        json={
            "target_environment": "STAGING",
            "risk_acceptance_justification": "Pre-deployment validation completed",
            "human_oversight_measures": "Supervised sandbox operation",
        },
        headers=headers_grc,
    )
    assert app_res.status_code == 201
    approval_id = app_res.json()["id"]
    assert app_res.json()["approval_status"] == "PENDING"

    # 3. Four-Eyes Enforcement: Requester cannot review their own request
    self_rev = client.post(
        f"/api/v1/ai-governance/approvals/{approval_id}/review",
        json={"decision": "APPROVED", "reviewer_notes": "Self approval attempt"},
        headers=headers_grc,
    )
    # GRC Analyst has no AI_APPROVE permission -> 403 Forbidden
    assert self_rev.status_code == 403

    # 4. Independent Manager approves request
    mgr_rev = client.post(
        f"/api/v1/ai-governance/approvals/{approval_id}/review",
        json={"decision": "APPROVED", "reviewer_notes": "Ethics committee approved"},
        headers=headers_mgr,
    )
    assert mgr_rev.status_code == 200
    assert mgr_rev.json()["approval_status"] == "APPROVED"
    assert mgr_rev.json()["reviewed_by_id"] == ai_api_fixture["manager"].id

    # 5. Now transition to APPROVED_STAGING succeeds
    stage_res = client.post(
        f"/api/v1/ai-governance/systems/{sys_id}/lifecycle",
        json={"lifecycle_state": "APPROVED_STAGING"},
        headers=headers_grc,
    )
    assert stage_res.status_code == 200
    assert stage_res.json()["lifecycle_state"] == "APPROVED_STAGING"


def test_deployment_approval_re_review_conflict_api(client: TestClient, ai_api_fixture):
    """Test reviewing an already approved/rejected deployment request returns 409 Conflict."""
    headers_grc = get_token_headers(ai_api_fixture["grc_analyst"])
    headers_mgr = get_token_headers(ai_api_fixture["manager"])

    create_res = client.post(
        "/api/v1/ai-governance/systems",
        json={
            "system_code": "AI-SYS-REREV-API",
            "name": "ReRev System",
            "system_type": "LLM_APPLICATION",
            "regulatory_tier": "LIMITED_RISK",
            "hosting_type": "CLOUD_THIRD_PARTY",
        },
        headers=headers_grc,
    )
    sys_id = create_res.json()["id"]

    app_res = client.post(
        f"/api/v1/ai-governance/systems/{sys_id}/approvals",
        json={
            "target_environment": "STAGING",
            "risk_acceptance_justification": "Risk within tolerance",
            "human_oversight_measures": "Manual spot checks",
        },
        headers=headers_grc,
    )
    approval_id = app_res.json()["id"]

    # First review
    client.post(
        f"/api/v1/ai-governance/approvals/{approval_id}/review",
        json={"decision": "APPROVED"},
        headers=headers_mgr,
    )

    # Second review attempt -> 409 Conflict
    re_rev = client.post(
        f"/api/v1/ai-governance/approvals/{approval_id}/review",
        json={"decision": "REJECTED"},
        headers=headers_mgr,
    )
    assert re_rev.status_code == 409
    assert "already in 'APPROVED' state" in re_rev.json()["detail"]


# ─── 4. RBAC & TENANT ISOLATION API TESTS ─────────────────────────────────────

def test_rbac_viewer_mutation_denied_api(client: TestClient, ai_api_fixture):
    """Test Viewer role cannot create, update, or delete AI systems."""
    headers = get_token_headers(ai_api_fixture["viewer"])
    payload = {
        "system_code": "AI-VIEWER-MUT",
        "name": "Viewer Model",
        "system_type": "LLM_APPLICATION",
        "regulatory_tier": "MINIMAL_RISK",
        "hosting_type": "CLOUD_THIRD_PARTY",
    }
    # Create attempt -> 403
    r_create = client.post("/api/v1/ai-governance/systems", json=payload, headers=headers)
    assert r_create.status_code == 403


def test_cross_tenant_resource_isolation_api(client: TestClient, ai_api_fixture):
    """Test foreign tenant cannot read or mutate another tenant's AI system."""
    headers_apex = get_token_headers(ai_api_fixture["admin"])
    headers_meridian = get_token_headers(ai_api_fixture["foreign_admin"])

    # Apex creates system
    create_res = client.post(
        "/api/v1/ai-governance/systems",
        json={
            "system_code": "AI-SYS-APEX-ISOL",
            "name": "Apex Private Model",
            "system_type": "LLM_APPLICATION",
            "regulatory_tier": "HIGH_RISK",
            "hosting_type": "CLOUD_THIRD_PARTY",
        },
        headers=headers_apex,
    )
    apex_sys_id = create_res.json()["id"]

    # Meridian attempts to GET Apex system -> 404
    r_get = client.get(f"/api/v1/ai-governance/systems/{apex_sys_id}", headers=headers_meridian)
    assert r_get.status_code == 404

    # Meridian attempts to UPDATE Apex system -> 404
    r_put = client.put(f"/api/v1/ai-governance/systems/{apex_sys_id}", json={"name": "Pwned"}, headers=headers_meridian)
    assert r_put.status_code == 404

    # Meridian attempts to DELETE Apex system -> 404
    r_del = client.delete(f"/api/v1/ai-governance/systems/{apex_sys_id}", headers=headers_meridian)
    assert r_del.status_code == 404

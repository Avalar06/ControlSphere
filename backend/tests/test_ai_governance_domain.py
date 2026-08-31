from datetime import datetime
import pytest
from fastapi import HTTPException

from app.core.permissions import RoleEnum
from app.models.ai_governance import (
    AIApprovalStatusEnum,
    AIAutonomyLevelEnum,
    AIDataSensitivityEnum,
    AIDeploymentApproval,
    AIHostingTypeEnum,
    AILifecycleStateEnum,
    AIModelCard,
    AIRegulatoryTierEnum,
    AISystem,
    AISystemTypeEnum,
)
from app.models.resilience import BusinessProcess, CriticalityTierEnum
from app.models.organization import Organization
from app.models.remediation import RemediationPlan, RemediationSeverityEnum, RemediationSourceTypeEnum
from app.models.user import User
from app.models.tprm import Vendor, VendorTierEnum
from app.schemas.ai_governance import (
    AIDeploymentApprovalCreate,
    AIDeploymentApprovalReviewRequest,
    AIModelCardCreate,
    AISystemCreate,
    AISystemUpdate,
)
from app.services.ai_governance_service import AIGovernanceService


@pytest.fixture
def org_a(db):
    org = Organization(name="AI Tenant A", slug="ai-tenant-a", is_active=True)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


@pytest.fixture
def org_b(db):
    org = Organization(name="AI Tenant B", slug="ai-tenant-b", is_active=True)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


@pytest.fixture
def user_analyst(db, org_a):
    user = User(
        email="analyst@tenant-a.com",
        hashed_password="hash",
        full_name="AI Analyst",
        role=RoleEnum.GRC_ANALYST,
        organization_id=org_a.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def user_manager(db, org_a):
    user = User(
        email="manager@tenant-a.com",
        hashed_password="hash",
        full_name="AI Ethics Manager",
        role=RoleEnum.MANAGER,
        organization_id=org_a.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def user_tenant_b(db, org_b):
    user = User(
        email="user@tenant-b.com",
        hashed_password="hash",
        full_name="Tenant B User",
        role=RoleEnum.MANAGER,
        organization_id=org_b.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def sample_process_tier1(db, org_a, user_manager):
    bp = BusinessProcess(
        organization_id=org_a.id,
        name="Real-Time Payments Core",
        criticality_tier=CriticalityTierEnum.TIER_1,
        owner_id=user_manager.id,
    )
    db.add(bp)
    db.commit()
    db.refresh(bp)
    return bp


@pytest.fixture
def sample_vendor(db, org_a):
    v = Vendor(
        organization_id=org_a.id,
        vendor_code="VND-OAI-01",
        legal_name="OpenAI LLM API",
        tier=VendorTierEnum.TIER_1,
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


# ─── 1. Mathematical Model Unit Tests ─────────────────────────────────────────

def test_ari_calculation_base_risks():
    """Verify ARI calculates expected base risks across all 5 regulatory tiers."""
    # Base: Prohibited = 100 * 1.0 * 1.0 + 2.0 (internal) = 100 capped
    ari_prohibited = AIGovernanceService.calculate_algorithmic_risk_index(
        regulatory_tier=AIRegulatoryTierEnum.PROHIBITED,
        autonomy_level=AIAutonomyLevelEnum.HUMAN_IN_THE_LOOP,
        data_sensitivity=AIDataSensitivityEnum.INTERNAL,
    )
    assert ari_prohibited == 100.00

    # High Risk = 65 * 1.0 * 1.0 + 2.0 = 67.0
    ari_high = AIGovernanceService.calculate_algorithmic_risk_index(
        regulatory_tier=AIRegulatoryTierEnum.HIGH_RISK,
        autonomy_level=AIAutonomyLevelEnum.HUMAN_IN_THE_LOOP,
        data_sensitivity=AIDataSensitivityEnum.INTERNAL,
    )
    assert ari_high == 67.00

    # GPAI = 50 * 1.0 * 1.0 + 2.0 = 52.0
    ari_gpai = AIGovernanceService.calculate_algorithmic_risk_index(
        regulatory_tier=AIRegulatoryTierEnum.GPAI_SYSTEMIC_RISK,
        autonomy_level=AIAutonomyLevelEnum.HUMAN_IN_THE_LOOP,
        data_sensitivity=AIDataSensitivityEnum.INTERNAL,
    )
    assert ari_gpai == 52.00

    # Limited = 25 * 1.0 * 1.0 + 2.0 = 27.0
    ari_limited = AIGovernanceService.calculate_algorithmic_risk_index(
        regulatory_tier=AIRegulatoryTierEnum.LIMITED_RISK,
        autonomy_level=AIAutonomyLevelEnum.HUMAN_IN_THE_LOOP,
        data_sensitivity=AIDataSensitivityEnum.INTERNAL,
    )
    assert ari_limited == 27.00

    # Minimal = 5 * 1.0 * 1.0 + 2.0 = 7.0
    ari_minimal = AIGovernanceService.calculate_algorithmic_risk_index(
        regulatory_tier=AIRegulatoryTierEnum.MINIMAL_RISK,
        autonomy_level=AIAutonomyLevelEnum.HUMAN_IN_THE_LOOP,
        data_sensitivity=AIDataSensitivityEnum.INTERNAL,
    )
    assert ari_minimal == 7.00


def test_ari_autonomy_multipliers():
    """Verify autonomy multipliers scale base risk correctly."""
    # High Risk (65) with FULL_AUTONOMY (1.40) -> 65 * 1.4 = 91.0 + 0 (public) = 91.0
    ari_full = AIGovernanceService.calculate_algorithmic_risk_index(
        regulatory_tier=AIRegulatoryTierEnum.HIGH_RISK,
        autonomy_level=AIAutonomyLevelEnum.FULL_AUTONOMY,
        data_sensitivity=AIDataSensitivityEnum.PUBLIC,
    )
    assert ari_full == 91.00

    # High Risk (65) with NO_AUTONOMY (0.80) -> 65 * 0.8 = 52.0 + 0 (public) = 52.0
    ari_none = AIGovernanceService.calculate_algorithmic_risk_index(
        regulatory_tier=AIRegulatoryTierEnum.HIGH_RISK,
        autonomy_level=AIAutonomyLevelEnum.NO_AUTONOMY,
        data_sensitivity=AIDataSensitivityEnum.PUBLIC,
    )
    assert ari_none == 52.00


def test_ari_process_tier_multipliers():
    """Verify linked process tier multipliers scale base risk correctly."""
    # Limited Risk (25) * 1.0 (HITL) * 1.25 (Tier 1) = 31.25 + 0 (public) = 31.25
    ari_tier1 = AIGovernanceService.calculate_algorithmic_risk_index(
        regulatory_tier=AIRegulatoryTierEnum.LIMITED_RISK,
        autonomy_level=AIAutonomyLevelEnum.HUMAN_IN_THE_LOOP,
        data_sensitivity=AIDataSensitivityEnum.PUBLIC,
        process_tier="TIER_1",
    )
    assert ari_tier1 == 31.25

    # Tier 2 (1.15) -> 25 * 1.15 = 28.75
    ari_tier2 = AIGovernanceService.calculate_algorithmic_risk_index(
        regulatory_tier=AIRegulatoryTierEnum.LIMITED_RISK,
        autonomy_level=AIAutonomyLevelEnum.HUMAN_IN_THE_LOOP,
        data_sensitivity=AIDataSensitivityEnum.PUBLIC,
        process_tier="TIER_2",
    )
    assert ari_tier2 == 28.75


def test_ari_safety_penalties():
    """Verify hallucination, prompt injection vulnerability, and data sensitivity add-ons."""
    # Limited Risk (25) + Hallucination (10% * 0.20 = +2.0) + Injection (80% res -> 20 unres * 0.15 = +3.0) + PII (+15.0)
    # Total = 25 + 2 + 3 + 15 = 45.0
    ari = AIGovernanceService.calculate_algorithmic_risk_index(
        regulatory_tier=AIRegulatoryTierEnum.LIMITED_RISK,
        autonomy_level=AIAutonomyLevelEnum.HUMAN_IN_THE_LOOP,
        data_sensitivity=AIDataSensitivityEnum.RESTRICTED_PII_PHI,
        process_tier="TIER_4",
        hallucination_rate_percent=10.0,
        prompt_injection_resistance_score=80.0,
    )
    assert ari == 45.00


def test_ari_cap_at_100():
    """Verify that extreme parameters cap ARI at exactly 100.00."""
    ari_max = AIGovernanceService.calculate_algorithmic_risk_index(
        regulatory_tier=AIRegulatoryTierEnum.PROHIBITED,
        autonomy_level=AIAutonomyLevelEnum.FULL_AUTONOMY,
        data_sensitivity=AIDataSensitivityEnum.RESTRICTED_PII_PHI,
        process_tier="TIER_1",
        hallucination_rate_percent=100.0,
        prompt_injection_resistance_score=0.0,
    )
    assert ari_max == 100.00


def test_ari_deterministic_calculation():
    """Verify deterministic mathematical calculation across multiple runs."""
    res1 = AIGovernanceService.calculate_algorithmic_risk_index(
        regulatory_tier=AIRegulatoryTierEnum.HIGH_RISK,
        autonomy_level=AIAutonomyLevelEnum.HUMAN_ON_THE_LOOP,
        data_sensitivity=AIDataSensitivityEnum.CONFIDENTIAL,
        process_tier="TIER_2",
        hallucination_rate_percent=5.5,
        prompt_injection_resistance_score=95.0,
    )
    res2 = AIGovernanceService.calculate_algorithmic_risk_index(
        regulatory_tier=AIRegulatoryTierEnum.HIGH_RISK,
        autonomy_level=AIAutonomyLevelEnum.HUMAN_ON_THE_LOOP,
        data_sensitivity=AIDataSensitivityEnum.CONFIDENTIAL,
        process_tier="TIER_2",
        hallucination_rate_percent=5.5,
        prompt_injection_resistance_score=95.0,
    )
    assert res1 == res2


def test_eu_compliance_score_calculation():
    """Verify EU AI Act compliance conformity readiness score."""
    # Prohibited -> 0.00%
    score_prohib = AIGovernanceService.calculate_eu_compliance_score(
        regulatory_tier=AIRegulatoryTierEnum.PROHIBITED,
        autonomy_level=AIAutonomyLevelEnum.FULL_AUTONOMY,
    )
    assert score_prohib == 0.00

    # Minimal Risk (100) + HITL bonus (10) = 100 (capped)
    score_minimal = AIGovernanceService.calculate_eu_compliance_score(
        regulatory_tier=AIRegulatoryTierEnum.MINIMAL_RISK,
        autonomy_level=AIAutonomyLevelEnum.HUMAN_IN_THE_LOOP,
    )
    assert score_minimal == 100.00

    # High Risk (50) - Hallucination (10 * 0.25 = 2.5) - Injection (20 * 0.20 = 4.0) + HITL (10) = 53.50%
    score_high = AIGovernanceService.calculate_eu_compliance_score(
        regulatory_tier=AIRegulatoryTierEnum.HIGH_RISK,
        autonomy_level=AIAutonomyLevelEnum.HUMAN_IN_THE_LOOP,
        hallucination_rate_percent=10.0,
        prompt_injection_resistance_score=80.0,
    )
    assert score_high == 53.50


# ─── 2. AI System Domain CRUD & Business Logic ───────────────────────────────

def test_create_ai_system_domain(db, org_a, user_analyst):
    """Test creating an AI system with automatic ARI and EU compliance scores."""
    payload = AISystemCreate(
        system_code="AI-SYS-001",
        name="Customer Triage Assistant",
        description="Autonomous LLM triage agent",
        system_type=AISystemTypeEnum.AGENTIC_WORKFLOW,
        regulatory_tier=AIRegulatoryTierEnum.HIGH_RISK,
        autonomy_level=AIAutonomyLevelEnum.HUMAN_IN_THE_LOOP,
        data_sensitivity=AIDataSensitivityEnum.INTERNAL,
        hosting_type=AIHostingTypeEnum.CLOUD_THIRD_PARTY,
        foundation_model_name="claude-3-7-sonnet",
    )
    system = AIGovernanceService.create_ai_system(
        db=db,
        organization_id=org_a.id,
        data=payload,
        current_user=user_analyst,
    )
    assert system.id is not None
    assert system.system_code == "AI-SYS-001"
    assert system.algorithmic_risk_index == 67.00
    assert system.is_prohibited_practice is False
    assert system.requires_conformity_assessment is True
    assert system.lifecycle_state == AILifecycleStateEnum.DEVELOPMENT


def test_create_ai_system_duplicate_code_conflict(db, org_a, user_analyst):
    """Verify duplicate system_code in same org raises HTTP 409."""
    payload = AISystemCreate(
        system_code="AI-SYS-DUP",
        name="System 1",
        system_type=AISystemTypeEnum.LLM_APPLICATION,
        regulatory_tier=AIRegulatoryTierEnum.LIMITED_RISK,
        hosting_type=AIHostingTypeEnum.CLOUD_THIRD_PARTY,
    )
    AIGovernanceService.create_ai_system(db, org_a.id, payload, user_analyst)

    with pytest.raises(HTTPException) as exc_info:
        AIGovernanceService.create_ai_system(db, org_a.id, payload, user_analyst)
    assert exc_info.value.status_code == 409


def test_create_ai_system_prohibited_practice_flag(db, org_a, user_analyst):
    """Verify PROHIBITED tier automatically sets is_prohibited_practice = True and ARI = 100."""
    payload = AISystemCreate(
        system_code="AI-SYS-PROHIB",
        name="Subliminal Behavioral Manipulation",
        system_type=AISystemTypeEnum.RECOMMENDER,
        regulatory_tier=AIRegulatoryTierEnum.PROHIBITED,
        hosting_type=AIHostingTypeEnum.CLOUD_THIRD_PARTY,
    )
    system = AIGovernanceService.create_ai_system(db, org_a.id, payload, user_analyst)
    assert system.is_prohibited_practice is True
    assert system.algorithmic_risk_index == 100.00
    assert system.eu_compliance_score == 0.00


def test_create_ai_system_cross_module_process(db, org_a, user_analyst, sample_process_tier1):
    """Verify linking a Tier 1 Business Process scales ARI via multiplier."""
    payload = AISystemCreate(
        system_code="AI-SYS-PAY",
        name="Payment Fraud Predictor",
        system_type=AISystemTypeEnum.PREDICTIVE_ANALYTICS,
        regulatory_tier=AIRegulatoryTierEnum.HIGH_RISK,
        autonomy_level=AIAutonomyLevelEnum.HUMAN_IN_THE_LOOP,
        data_sensitivity=AIDataSensitivityEnum.PUBLIC,
        hosting_type=AIHostingTypeEnum.CLOUD_THIRD_PARTY,
        business_process_id=sample_process_tier1.id,
    )
    system = AIGovernanceService.create_ai_system(db, org_a.id, payload, user_analyst)
    # High Risk (65) * 1.0 (HITL) * 1.25 (Tier 1) = 81.25 + 0 (public) = 81.25
    assert system.algorithmic_risk_index == 81.25


def test_create_ai_system_cross_tenant_process_block(db, org_a, org_b, user_analyst, user_tenant_b):
    """Verify linking a Business Process belonging to another tenant raises HTTP 404."""
    # Create process in Tenant B
    bp_b = BusinessProcess(
        organization_id=org_b.id,
        name="Tenant B Process",
        criticality_tier=CriticalityTierEnum.TIER_1,
        owner_id=user_tenant_b.id,
    )
    db.add(bp_b)
    db.commit()
    db.refresh(bp_b)

    payload = AISystemCreate(
        system_code="AI-SYS-IDOR",
        name="IDOR Tester",
        system_type=AISystemTypeEnum.LLM_APPLICATION,
        regulatory_tier=AIRegulatoryTierEnum.LIMITED_RISK,
        hosting_type=AIHostingTypeEnum.CLOUD_THIRD_PARTY,
        business_process_id=bp_b.id,  # Process belongs to Tenant B!
    )
    with pytest.raises(HTTPException) as exc_info:
        AIGovernanceService.create_ai_system(db, org_a.id, payload, user_analyst)
    assert exc_info.value.status_code == 404


def test_update_ai_system_domain(db, org_a, user_analyst):
    """Test updating AI system fields and automatic recalculation."""
    payload = AISystemCreate(
        system_code="AI-SYS-UPD",
        name="Original Name",
        system_type=AISystemTypeEnum.LLM_APPLICATION,
        regulatory_tier=AIRegulatoryTierEnum.LIMITED_RISK,
        autonomy_level=AIAutonomyLevelEnum.HUMAN_IN_THE_LOOP,
        data_sensitivity=AIDataSensitivityEnum.INTERNAL,
        hosting_type=AIHostingTypeEnum.CLOUD_THIRD_PARTY,
    )
    system = AIGovernanceService.create_ai_system(db, org_a.id, payload, user_analyst)
    assert system.algorithmic_risk_index == 27.00

    # Update to HIGH_RISK + FULL_AUTONOMY
    update_payload = AISystemUpdate(
        name="Updated Name",
        regulatory_tier=AIRegulatoryTierEnum.HIGH_RISK,
        autonomy_level=AIAutonomyLevelEnum.FULL_AUTONOMY,
    )
    updated = AIGovernanceService.update_ai_system(db, org_a.id, system.id, update_payload, user_analyst)
    assert updated.name == "Updated Name"
    assert updated.regulatory_tier == AIRegulatoryTierEnum.HIGH_RISK
    # 65 * 1.4 = 91.0 + 2.0 (internal) = 93.00
    assert updated.algorithmic_risk_index == 93.00


def test_delete_ai_system_domain(db, org_a, user_analyst):
    """Test deleting non-production AI system."""
    payload = AISystemCreate(
        system_code="AI-SYS-DEL",
        name="To Be Deleted",
        system_type=AISystemTypeEnum.LLM_APPLICATION,
        regulatory_tier=AIRegulatoryTierEnum.MINIMAL_RISK,
        hosting_type=AIHostingTypeEnum.CLOUD_THIRD_PARTY,
    )
    system = AIGovernanceService.create_ai_system(db, org_a.id, payload, user_analyst)
    AIGovernanceService.delete_ai_system(db, org_a.id, system.id, user_analyst)

    with pytest.raises(HTTPException) as exc_info:
        AIGovernanceService.get_ai_system(db, org_a.id, system.id)
    assert exc_info.value.status_code == 404


# ─── 3. Lifecycle State Machine & Immutability ────────────────────────────────

def test_lifecycle_state_machine_legal_progression(db, org_a, user_analyst):
    """Verify legal step-by-step lifecycle transitions."""
    payload = AISystemCreate(
        system_code="AI-SYS-LIFE",
        name="Lifecycle Model",
        system_type=AISystemTypeEnum.LLM_APPLICATION,
        regulatory_tier=AIRegulatoryTierEnum.LIMITED_RISK,
        hosting_type=AIHostingTypeEnum.CLOUD_THIRD_PARTY,
    )
    system = AIGovernanceService.create_ai_system(db, org_a.id, payload, user_analyst)
    assert system.lifecycle_state == AILifecycleStateEnum.DEVELOPMENT

    # Transition to VALIDATION
    s1 = AIGovernanceService.update_lifecycle_state(
        db, org_a.id, system.id, AILifecycleStateEnum.VALIDATION, "Validation testing", user_analyst
    )
    assert s1.lifecycle_state == AILifecycleStateEnum.VALIDATION

    # Transition to ETHICAL_REVIEW
    s2 = AIGovernanceService.update_lifecycle_state(
        db, org_a.id, system.id, AILifecycleStateEnum.ETHICAL_REVIEW, "Review board", user_analyst
    )
    assert s2.lifecycle_state == AILifecycleStateEnum.ETHICAL_REVIEW


def test_lifecycle_state_machine_illegal_transition_block(db, org_a, user_analyst):
    """Verify direct illegal transition (e.g. DEVELOPMENT -> PRODUCTION) raises HTTP 409."""
    payload = AISystemCreate(
        system_code="AI-SYS-ILL",
        name="Illegal Transition Model",
        system_type=AISystemTypeEnum.LLM_APPLICATION,
        regulatory_tier=AIRegulatoryTierEnum.LIMITED_RISK,
        hosting_type=AIHostingTypeEnum.CLOUD_THIRD_PARTY,
    )
    system = AIGovernanceService.create_ai_system(db, org_a.id, payload, user_analyst)

    with pytest.raises(HTTPException) as exc_info:
        AIGovernanceService.update_lifecycle_state(
            db, org_a.id, system.id, AILifecycleStateEnum.PRODUCTION, "Skip steps", user_analyst
        )
    assert exc_info.value.status_code == 409


def test_lifecycle_prohibited_production_block(db, org_a, user_analyst, user_manager):
    """Verify prohibited AI can never be promoted to PRODUCTION."""
    payload = AISystemCreate(
        system_code="AI-SYS-PROH-GATE",
        name="Prohibited Social Scorer",
        system_type=AISystemTypeEnum.PREDICTIVE_ANALYTICS,
        regulatory_tier=AIRegulatoryTierEnum.PROHIBITED,
        hosting_type=AIHostingTypeEnum.CLOUD_THIRD_PARTY,
    )
    system = AIGovernanceService.create_ai_system(db, org_a.id, payload, user_analyst)
    AIGovernanceService.update_lifecycle_state(db, org_a.id, system.id, AILifecycleStateEnum.VALIDATION, "val", user_analyst)
    AIGovernanceService.update_lifecycle_state(db, org_a.id, system.id, AILifecycleStateEnum.ETHICAL_REVIEW, "rev", user_analyst)

    # Attempting to request and approve deployment for prohibited AI is rejected
    with pytest.raises(HTTPException) as exc_info:
        AIGovernanceService.request_deployment_approval(
            db=db,
            organization_id=org_a.id,
            system_id=system.id,
            data=AIDeploymentApprovalCreate(
                target_environment="PRODUCTION",
                risk_acceptance_justification="Overriding EU AI Act",
                human_oversight_measures="No human oversight available",
            ),
            current_user=user_analyst,
        )
    assert exc_info.value.status_code == 409


def test_lifecycle_decommissioned_immutability(db, org_a, user_analyst):
    """Verify decommissioned systems are permanently locked against modifications."""
    payload = AISystemCreate(
        system_code="AI-SYS-DECOM",
        name="Decommission Test",
        system_type=AISystemTypeEnum.LLM_APPLICATION,
        regulatory_tier=AIRegulatoryTierEnum.MINIMAL_RISK,
        hosting_type=AIHostingTypeEnum.CLOUD_THIRD_PARTY,
    )
    system = AIGovernanceService.create_ai_system(db, org_a.id, payload, user_analyst)
    AIGovernanceService.update_lifecycle_state(db, org_a.id, system.id, AILifecycleStateEnum.DECOMMISSIONED, "End of life", user_analyst)

    # Attempt update
    with pytest.raises(HTTPException) as exc_info:
        AIGovernanceService.update_ai_system(db, org_a.id, system.id, AISystemUpdate(name="New Name"), user_analyst)
    assert exc_info.value.status_code == 409

    # Attempt state change
    with pytest.raises(HTTPException) as exc_info2:
        AIGovernanceService.update_lifecycle_state(db, org_a.id, system.id, AILifecycleStateEnum.DEVELOPMENT, "Reopen", user_analyst)
    assert exc_info2.value.status_code == 409


# ─── 4. Model Cards & Safety Ingestion ───────────────────────────────────────

def test_model_card_creation_and_ari_recalculation(db, org_a, user_analyst):
    """Verify creating a model card updates parent AI system's safety metrics and ARI."""
    payload = AISystemCreate(
        system_code="AI-SYS-CARD",
        name="Card Model",
        system_type=AISystemTypeEnum.LLM_APPLICATION,
        regulatory_tier=AIRegulatoryTierEnum.LIMITED_RISK,
        autonomy_level=AIAutonomyLevelEnum.HUMAN_IN_THE_LOOP,
        data_sensitivity=AIDataSensitivityEnum.PUBLIC,
        hosting_type=AIHostingTypeEnum.CLOUD_THIRD_PARTY,
    )
    system = AIGovernanceService.create_ai_system(db, org_a.id, payload, user_analyst)
    assert system.algorithmic_risk_index == 25.00

    # Attach model card with 20% hallucination rate and 70% prompt injection resistance
    # Penalty: (20 * 0.20 = +4.0) + (30 * 0.15 = +4.5) = +8.5 -> Total ARI = 33.50
    card_payload = AIModelCardCreate(
        version="1.0.0",
        intended_use="Summarization of internal wiki pages",
        hallucination_rate_percent=20.0,
        prompt_injection_resistance_score=70.0,
        synthetic_data_percentage=15.0,
    )
    card = AIGovernanceService.create_model_card(db, org_a.id, system.id, card_payload, user_analyst)
    assert card.id is not None

    db.refresh(system)
    assert system.algorithmic_risk_index == 33.50


# ─── 5. Four-Eyes Deployment Approvals ────────────────────────────────────────

def test_four_eyes_deployment_approval_workflow(db, org_a, user_analyst, user_manager):
    """Test full four-eyes workflow: request -> independent review -> staging promotion."""
    payload = AISystemCreate(
        system_code="AI-SYS-4EYES",
        name="Production Triage AI",
        system_type=AISystemTypeEnum.AGENTIC_WORKFLOW,
        regulatory_tier=AIRegulatoryTierEnum.HIGH_RISK,
        autonomy_level=AIAutonomyLevelEnum.HUMAN_IN_THE_LOOP,
        hosting_type=AIHostingTypeEnum.CLOUD_THIRD_PARTY,
    )
    system = AIGovernanceService.create_ai_system(db, org_a.id, payload, user_analyst)
    AIGovernanceService.update_lifecycle_state(db, org_a.id, system.id, AILifecycleStateEnum.VALIDATION, "val", user_analyst)
    AIGovernanceService.update_lifecycle_state(db, org_a.id, system.id, AILifecycleStateEnum.ETHICAL_REVIEW, "eth", user_analyst)

    # 1. Analyst requests staging deployment
    req_payload = AIDeploymentApprovalCreate(
        target_environment="STAGING",
        risk_acceptance_justification="Safety benchmarks verified > 95%",
        human_oversight_measures="Human verification on all output actions",
    )
    approval = AIGovernanceService.request_deployment_approval(
        db, org_a.id, system.id, req_payload, user_analyst
    )
    assert approval.approval_status == AIApprovalStatusEnum.PENDING

    # 2. Four-Eyes Invariant: Requester CANNOT review their own request
    with pytest.raises(HTTPException) as exc_info:
        AIGovernanceService.review_deployment_approval(
            db, org_a.id, approval.id, AIDeploymentApprovalReviewRequest(decision="APPROVED"), user_analyst
        )
    assert exc_info.value.status_code == 403

    # 3. Independent Manager approves request
    reviewed = AIGovernanceService.review_deployment_approval(
        db, org_a.id, approval.id, AIDeploymentApprovalReviewRequest(decision="APPROVED", reviewer_notes="Approved by Ethics Board"), user_manager
    )
    assert reviewed.approval_status == AIApprovalStatusEnum.APPROVED
    assert reviewed.reviewed_by_id == user_manager.id

    # 4. Now transition to APPROVED_STAGING succeeds
    staged = AIGovernanceService.update_lifecycle_state(
        db, org_a.id, system.id, AILifecycleStateEnum.APPROVED_STAGING, "Staged", user_analyst
    )
    assert staged.lifecycle_state == AILifecycleStateEnum.APPROVED_STAGING


# ─── 6. Posture Summary & Tenant Isolation ────────────────────────────────────

def test_posture_summary_and_tenant_isolation(db, org_a, org_b, user_analyst, user_tenant_b):
    """Test posture summary counts and verify Tenant A cannot view Tenant B records."""
    # Create 2 systems in Tenant A
    AIGovernanceService.create_ai_system(
        db, org_a.id, AISystemCreate(
            system_code="AI-A-1", name="Sys A1", system_type=AISystemTypeEnum.LLM_APPLICATION,
            regulatory_tier=AIRegulatoryTierEnum.HIGH_RISK, hosting_type=AIHostingTypeEnum.CLOUD_THIRD_PARTY
        ), user_analyst
    )
    AIGovernanceService.create_ai_system(
        db, org_a.id, AISystemCreate(
            system_code="AI-A-2", name="Sys A2", system_type=AISystemTypeEnum.RECOMMENDER,
            regulatory_tier=AIRegulatoryTierEnum.MINIMAL_RISK, hosting_type=AIHostingTypeEnum.CLOUD_THIRD_PARTY
        ), user_analyst
    )

    # Create 1 system in Tenant B
    sys_b = AIGovernanceService.create_ai_system(
        db, org_b.id, AISystemCreate(
            system_code="AI-B-1", name="Sys B1", system_type=AISystemTypeEnum.COMPUTER_VISION,
            regulatory_tier=AIRegulatoryTierEnum.GPAI_SYSTEMIC_RISK, hosting_type=AIHostingTypeEnum.CLOUD_THIRD_PARTY
        ), user_tenant_b
    )

    # Posture summary for Tenant A
    summary_a = AIGovernanceService.get_posture_summary(db, org_a.id)
    assert summary_a.total_ai_systems == 2
    assert summary_a.high_risk_systems == 1
    assert summary_a.prohibited_systems == 0

    # Tenant A cannot fetch Tenant B's system
    with pytest.raises(HTTPException) as exc_info:
        AIGovernanceService.get_ai_system(db, org_a.id, sys_b.id)
    assert exc_info.value.status_code == 404


def test_list_ai_systems_filters(db, org_a, user_analyst):
    """Test filtering AI systems by regulatory tier, lifecycle state, and search keyword."""
    AIGovernanceService.create_ai_system(
        db, org_a.id, AISystemCreate(
            system_code="AI-FILTER-1", name="Alpha High Risk", system_type=AISystemTypeEnum.LLM_APPLICATION,
            regulatory_tier=AIRegulatoryTierEnum.HIGH_RISK, hosting_type=AIHostingTypeEnum.CLOUD_THIRD_PARTY
        ), user_analyst
    )
    AIGovernanceService.create_ai_system(
        db, org_a.id, AISystemCreate(
            system_code="AI-FILTER-2", name="Beta Minimal", system_type=AISystemTypeEnum.RECOMMENDER,
            regulatory_tier=AIRegulatoryTierEnum.MINIMAL_RISK, hosting_type=AIHostingTypeEnum.CLOUD_THIRD_PARTY
        ), user_analyst
    )

    # List filtered by HIGH_RISK
    high_systems = AIGovernanceService.list_ai_systems(
        db, org_a.id, regulatory_tier=AIRegulatoryTierEnum.HIGH_RISK
    )
    assert len(high_systems) == 1
    assert high_systems[0].system_code == "AI-FILTER-1"

    # Search keyword
    search_results = AIGovernanceService.list_ai_systems(db, org_a.id, search="Alpha High")
    assert len(search_results) == 1
    assert search_results[0].system_code == "AI-FILTER-1"


def test_model_card_duplicate_version_conflict(db, org_a, user_analyst):
    """Test creating duplicate version for same AI system raises HTTP 409."""
    sys = AIGovernanceService.create_ai_system(
        db, org_a.id, AISystemCreate(
            system_code="AI-CARD-DUP", name="Card DUP", system_type=AISystemTypeEnum.LLM_APPLICATION,
            regulatory_tier=AIRegulatoryTierEnum.LIMITED_RISK, hosting_type=AIHostingTypeEnum.CLOUD_THIRD_PARTY
        ), user_analyst
    )
    card_payload = AIModelCardCreate(version="1.0.0", intended_use="Test intended use")
    AIGovernanceService.create_model_card(db, org_a.id, sys.id, card_payload, user_analyst)

    with pytest.raises(HTTPException) as exc_info:
        AIGovernanceService.create_model_card(db, org_a.id, sys.id, card_payload, user_analyst)
    assert exc_info.value.status_code == 409


def test_model_card_list(db, org_a, user_analyst):
    """Test listing model cards for an AI system."""
    sys = AIGovernanceService.create_ai_system(
        db, org_a.id, AISystemCreate(
            system_code="AI-CARD-LIST", name="Card List", system_type=AISystemTypeEnum.LLM_APPLICATION,
            regulatory_tier=AIRegulatoryTierEnum.LIMITED_RISK, hosting_type=AIHostingTypeEnum.CLOUD_THIRD_PARTY
        ), user_analyst
    )
    AIGovernanceService.create_model_card(db, org_a.id, sys.id, AIModelCardCreate(version="1.0.0", intended_use="v1 intended use"), user_analyst)
    AIGovernanceService.create_model_card(db, org_a.id, sys.id, AIModelCardCreate(version="2.0.0", intended_use="v2 intended use"), user_analyst)

    cards = AIGovernanceService.list_model_cards(db, org_a.id, sys.id)
    assert len(cards) == 2


def test_deployment_approval_re_review_conflict(db, org_a, user_analyst, user_manager):
    """Test reviewing an already reviewed deployment approval raises HTTP 409."""
    sys = AIGovernanceService.create_ai_system(
        db, org_a.id, AISystemCreate(
            system_code="AI-REREV", name="ReRev Test", system_type=AISystemTypeEnum.LLM_APPLICATION,
            regulatory_tier=AIRegulatoryTierEnum.LIMITED_RISK, hosting_type=AIHostingTypeEnum.CLOUD_THIRD_PARTY
        ), user_analyst
    )
    req = AIGovernanceService.request_deployment_approval(
        db, org_a.id, sys.id,
        AIDeploymentApprovalCreate(target_environment="STAGING", risk_acceptance_justification="Safety validated", human_oversight_measures="Manual verification"),
        user_analyst
    )
    AIGovernanceService.review_deployment_approval(db, org_a.id, req.id, AIDeploymentApprovalReviewRequest(decision="APPROVED"), user_manager)

    with pytest.raises(HTTPException) as exc_info:
        AIGovernanceService.review_deployment_approval(db, org_a.id, req.id, AIDeploymentApprovalReviewRequest(decision="REJECTED"), user_manager)
    assert exc_info.value.status_code == 409


def test_deployment_approval_invalid_target_env(db, org_a, user_analyst):
    """Test requesting approval for invalid target env raises HTTP 422."""
    sys = AIGovernanceService.create_ai_system(
        db, org_a.id, AISystemCreate(
            system_code="AI-INV-ENV", name="Inv Env", system_type=AISystemTypeEnum.LLM_APPLICATION,
            regulatory_tier=AIRegulatoryTierEnum.LIMITED_RISK, hosting_type=AIHostingTypeEnum.CLOUD_THIRD_PARTY
        ), user_analyst
    )
    with pytest.raises(HTTPException) as exc_info:
        AIGovernanceService.request_deployment_approval(
            db, org_a.id, sys.id,
            AIDeploymentApprovalCreate(target_environment="INVALID_ENV", risk_acceptance_justification="Safety validated", human_oversight_measures="Manual verification"),
            user_analyst
        )
    assert exc_info.value.status_code == 422


def test_delete_production_system_block(db, org_a, user_analyst, user_manager):
    """Test attempting to delete a PRODUCTION AI system raises HTTP 409."""
    sys = AIGovernanceService.create_ai_system(
        db, org_a.id, AISystemCreate(
            system_code="AI-DEL-PROD", name="Prod Del", system_type=AISystemTypeEnum.LLM_APPLICATION,
            regulatory_tier=AIRegulatoryTierEnum.LIMITED_RISK, hosting_type=AIHostingTypeEnum.CLOUD_THIRD_PARTY
        ), user_analyst
    )
    AIGovernanceService.update_lifecycle_state(db, org_a.id, sys.id, AILifecycleStateEnum.VALIDATION, "val", user_analyst)
    AIGovernanceService.update_lifecycle_state(db, org_a.id, sys.id, AILifecycleStateEnum.ETHICAL_REVIEW, "eth", user_analyst)
    
    # Request & approve staging
    req_stage = AIGovernanceService.request_deployment_approval(
        db, org_a.id, sys.id,
        AIDeploymentApprovalCreate(target_environment="STAGING", risk_acceptance_justification="Safety validated", human_oversight_measures="Manual verification"),
        user_analyst
    )
    AIGovernanceService.review_deployment_approval(db, org_a.id, req_stage.id, AIDeploymentApprovalReviewRequest(decision="APPROVED"), user_manager)
    AIGovernanceService.update_lifecycle_state(db, org_a.id, sys.id, AILifecycleStateEnum.APPROVED_STAGING, "stage", user_analyst)

    # Request & approve prod
    req_prod = AIGovernanceService.request_deployment_approval(
        db, org_a.id, sys.id,
        AIDeploymentApprovalCreate(target_environment="PRODUCTION", risk_acceptance_justification="Safety validated", human_oversight_measures="Manual verification"),
        user_analyst
    )
    AIGovernanceService.review_deployment_approval(db, org_a.id, req_prod.id, AIDeploymentApprovalReviewRequest(decision="APPROVED"), user_manager)
    AIGovernanceService.update_lifecycle_state(db, org_a.id, sys.id, AILifecycleStateEnum.PRODUCTION, "prod", user_analyst)

    with pytest.raises(HTTPException) as exc_info:
        AIGovernanceService.delete_ai_system(db, org_a.id, sys.id, user_analyst)
    assert exc_info.value.status_code == 409


from datetime import datetime, timezone
import pytest
from fastapi import HTTPException

from app.core.permissions import RoleEnum
from app.models.supply_chain import (
    ComponentEcosystemEnum,
    ComponentVulnerabilityLink,
    ExemptionApprovalStatusEnum,
    LicenseCategoryEnum,
    LicenseCompliancePolicy,
    ProductCriticalityTierEnum,
    ProductLifecycleStateEnum,
    SBOMDocument,
    SBOMFormatStandardEnum,
    SBOMStatusEnum,
    SoftwareComponent,
    SoftwareProduct,
    SoftwareProductTypeEnum,
    SupplyChainExemption,
    SupplyChainRiskBandEnum,
)
from app.models.organization import Organization
from app.models.user import User
from app.models.resilience import BusinessProcess, CriticalityTierEnum
from app.models.ai_governance import AISystem, AISystemTypeEnum, AIRegulatoryTierEnum, AIHostingTypeEnum
from app.models.tprm import Vendor, VendorTierEnum
from app.models.remediation import RemediationPlan, RemediationSourceTypeEnum
from app.models.exposure import VulnerabilityExposure, ExposureSeverityEnum
from app.schemas.supply_chain import (
    ComponentVulnerabilityLinkCreate,
    LicenseCompliancePolicyCreate,
    SBOMDocumentCreate,
    SoftwareComponentCreate,
    SoftwareProductCreate,
    SoftwareProductStatusUpdate,
    SoftwareProductUpdate,
    SupplyChainExemptionCreate,
    SupplyChainExemptionReviewRequest,
)
from app.services.supply_chain_service import SupplyChainService


# ─── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def org_a(db):
    org = Organization(name="SupplyChain Org A", slug="supplychain-org-a", is_active=True)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


@pytest.fixture
def org_b(db):
    org = Organization(name="SupplyChain Org B", slug="supplychain-org-b", is_active=True)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


@pytest.fixture
def user_analyst(db, org_a):
    user = User(
        email="sc_analyst@example.com",
        full_name="SC Analyst",
        hashed_password="hash",
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
        email="sc_manager@example.com",
        full_name="SC Manager",
        hashed_password="hash",
        role=RoleEnum.MANAGER,
        organization_id=org_a.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def user_org_b(db, org_b):
    user = User(
        email="sc_user_b@example.com",
        full_name="Org B User",
        hashed_password="hash",
        role=RoleEnum.GRC_ANALYST,
        organization_id=org_b.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ─── 1. Mathematical Formulas & Calculation Engine Tests ────────────────────────

def test_vulnerability_score_calculation():
    assert SupplyChainService.calculate_vulnerability_score([]) == 0.0
    assert SupplyChainService.calculate_vulnerability_score([8.0], False) == 80.0
    assert SupplyChainService.calculate_vulnerability_score([6.0, 4.0], False) == 66.0


def test_exploitability_multiplier():
    # Non-exploitable CVSS 8.0 = 80.0; Exploitable CVSS 8.0 * 10 * 1.25 = 100.0
    assert SupplyChainService.calculate_vulnerability_score([8.0], False) == 80.0
    assert SupplyChainService.calculate_vulnerability_score([8.0], True) == 100.0


def test_kev_epss_behavior():
    # Active KEV / high EPSS triggers 1.25x multiplier on primary CVE
    vscore_normal = SupplyChainService.calculate_vulnerability_score([7.0], is_any_exploitable=False)
    vscore_kev = SupplyChainService.calculate_vulnerability_score([7.0], is_any_exploitable=True)
    assert vscore_normal == 70.0
    assert vscore_kev == 87.5


def test_dependency_depth_calculation():
    assert SupplyChainService.calculate_depth_penalty(1) == 1.00
    assert SupplyChainService.calculate_depth_penalty(2) == 1.10
    assert SupplyChainService.calculate_depth_penalty(3) == 1.20
    assert SupplyChainService.calculate_depth_penalty(4) == 1.30
    assert SupplyChainService.calculate_depth_penalty(8) == 1.30  # Max penalty cap


def test_license_risk_scoring():
    assert SupplyChainService.calculate_license_risk_points(LicenseCategoryEnum.PERMISSIVE) == 0.0
    assert SupplyChainService.calculate_license_risk_points(LicenseCategoryEnum.WEAK_COPYLEFT) == 10.0
    assert SupplyChainService.calculate_license_risk_points(LicenseCategoryEnum.STRONG_COPYLEFT) == 25.0
    assert SupplyChainService.calculate_license_risk_points(LicenseCategoryEnum.PROHIBITED) == 30.0
    assert SupplyChainService.calculate_license_risk_points(LicenseCategoryEnum.UNCLASSIFIED) == 15.0


def test_cri_calculation():
    cri = SupplyChainService.calculate_component_risk_index(50.0, 10.0, 1.10, False)
    assert cri == 66.0


def test_exemption_factor():
    cri_unexempted = SupplyChainService.calculate_component_risk_index(60.0, 20.0, 1.0, False)
    cri_exempted = SupplyChainService.calculate_component_risk_index(60.0, 20.0, 1.0, True)
    assert cri_unexempted == 80.0
    assert cri_exempted == 40.0


def test_scei_calculation():
    assert SupplyChainService.calculate_supply_chain_exposure_index([]) == 0.0
    # [80.0, 40.0] -> Max: 80*0.6=48, Avg: 60*0.4=24 -> Total 72.0
    assert SupplyChainService.calculate_supply_chain_exposure_index([80.0, 40.0]) == 72.0


def test_severity_bands():
    assert SupplyChainService.get_risk_band(15.0) == SupplyChainRiskBandEnum.LOW
    assert SupplyChainService.get_risk_band(35.0) == SupplyChainRiskBandEnum.MODERATE
    assert SupplyChainService.get_risk_band(60.0) == SupplyChainRiskBandEnum.HIGH
    assert SupplyChainService.get_risk_band(80.0) == SupplyChainRiskBandEnum.VERY_HIGH
    assert SupplyChainService.get_risk_band(95.0) == SupplyChainRiskBandEnum.CRITICAL


def test_score_boundary_clamping():
    # Vscore clamped to 100.0
    assert SupplyChainService.calculate_vulnerability_score([10.0, 10.0, 10.0], True) == 100.0
    # CRI clamped to 100.0
    assert SupplyChainService.calculate_component_risk_index(100.0, 30.0, 1.30, False) == 100.0
    # SCEI clamped to 100.0
    assert SupplyChainService.calculate_supply_chain_exposure_index([100.0, 100.0]) == 100.0


# ─── 2. Product Domain & Lifecycle Tests ────────────────────────────────────────

def test_product_creation(db, org_a, user_analyst):
    data = SoftwareProductCreate(
        product_code="PROD-TEST-001",
        name="Trading Gateway",
        description="Low latency order router",
        product_type=SoftwareProductTypeEnum.MICROSERVICE,
        criticality_tier=ProductCriticalityTierEnum.TIER_1_CRITICAL,
    )
    product = SupplyChainService.create_product(db, org_a.id, user_analyst.id, data)
    assert product.id is not None
    assert product.product_code == "PROD-TEST-001"
    assert product.lifecycle_state == ProductLifecycleStateEnum.DRAFT
    assert product.supply_chain_exposure_index == 0.0


def test_product_lifecycle_transitions(db, org_a, user_analyst):
    product = SupplyChainService.create_product(
        db, org_a.id, user_analyst.id, SoftwareProductCreate(product_code="PROD-LIFECYCLE", name="Test App")
    )
    # DRAFT -> ACTIVE
    p_act = SupplyChainService.update_product_status(
        db, org_a.id, user_analyst.id, product.id, SoftwareProductStatusUpdate(lifecycle_state=ProductLifecycleStateEnum.ACTIVE)
    )
    assert p_act.lifecycle_state == ProductLifecycleStateEnum.ACTIVE

    # ACTIVE -> DEPRECATED
    p_dep = SupplyChainService.update_product_status(
        db, org_a.id, user_analyst.id, product.id, SoftwareProductStatusUpdate(lifecycle_state=ProductLifecycleStateEnum.DEPRECATED)
    )
    assert p_dep.lifecycle_state == ProductLifecycleStateEnum.DEPRECATED

    # DEPRECATED -> RETIRED
    p_ret = SupplyChainService.update_product_status(
        db, org_a.id, user_analyst.id, product.id, SoftwareProductStatusUpdate(lifecycle_state=ProductLifecycleStateEnum.RETIRED)
    )
    assert p_ret.lifecycle_state == ProductLifecycleStateEnum.RETIRED


def test_retired_immutability(db, org_a, user_analyst):
    product = SupplyChainService.create_product(
        db, org_a.id, user_analyst.id, SoftwareProductCreate(product_code="PROD-RETIRE-LOCK", name="Legacy App")
    )
    SupplyChainService.update_product_status(
        db, org_a.id, user_analyst.id, product.id, SoftwareProductStatusUpdate(lifecycle_state=ProductLifecycleStateEnum.ACTIVE)
    )
    SupplyChainService.update_product_status(
        db, org_a.id, user_analyst.id, product.id, SoftwareProductStatusUpdate(lifecycle_state=ProductLifecycleStateEnum.RETIRED)
    )

    # Mutation rejected on retired product
    with pytest.raises(HTTPException) as exc_info:
        SupplyChainService.update_product(
            db, org_a.id, user_analyst.id, product.id, SoftwareProductUpdate(name="New Mutated Name")
        )
    assert exc_info.value.status_code == 400

    # Status transition rejected on retired product
    with pytest.raises(HTTPException) as exc_info:
        SupplyChainService.update_product_status(
            db, org_a.id, user_analyst.id, product.id, SoftwareProductStatusUpdate(lifecycle_state=ProductLifecycleStateEnum.ACTIVE)
        )
    assert exc_info.value.status_code == 400


def test_invalid_input_rejection(db, org_a, user_analyst):
    data = SoftwareProductCreate(product_code="PROD-DUP-CODE", name="App 1")
    SupplyChainService.create_product(db, org_a.id, user_analyst.id, data)

    # Duplicate product code rejected with 409
    with pytest.raises(HTTPException) as exc_info:
        SupplyChainService.create_product(db, org_a.id, user_analyst.id, data)
    assert exc_info.value.status_code == 409

    # Illegal transition directly from DRAFT to RETIRED
    product = SupplyChainService.create_product(
        db, org_a.id, user_analyst.id, SoftwareProductCreate(product_code="PROD-ILLEGAL", name="Illegal App")
    )
    with pytest.raises(HTTPException) as exc_info:
        SupplyChainService.update_product_status(
            db, org_a.id, user_analyst.id, product.id, SoftwareProductStatusUpdate(lifecycle_state=ProductLifecycleStateEnum.RETIRED)
        )
    assert exc_info.value.status_code == 422


# ─── 3. SBOM & Component Governance Tests ──────────────────────────────────────

def test_sbom_lifecycle_and_sha256_validation(db, org_a, user_analyst):
    product = SupplyChainService.create_product(
        db, org_a.id, user_analyst.id, SoftwareProductCreate(product_code="PROD-SBOM-001", name="Payment Microservice")
    )
    valid_sha1 = "1" * 64
    valid_sha2 = "2" * 64

    sbom1 = SupplyChainService.ingest_sbom(
        db,
        org_a.id,
        user_analyst.id,
        product.id,
        SBOMDocumentCreate(
            software_product_id=product.id,
            sbom_code="SBOM-PAY-1",
            version="1.0.0",
            sha256_hash=valid_sha1,
        ),
    )
    assert sbom1.status == SBOMStatusEnum.ACTIVE

    # Ingesting version 2 supersedes version 1
    sbom2 = SupplyChainService.ingest_sbom(
        db,
        org_a.id,
        user_analyst.id,
        product.id,
        SBOMDocumentCreate(
            software_product_id=product.id,
            sbom_code="SBOM-PAY-2",
            version="1.1.0",
            sha256_hash=valid_sha2,
        ),
    )
    assert sbom2.status == SBOMStatusEnum.ACTIVE

    # Check that sbom1 was superseded
    db.refresh(sbom1)
    assert sbom1.status == SBOMStatusEnum.SUPERSEDED

    # Non-hex SHA-256 rejected
    with pytest.raises(HTTPException) as exc_info:
        SupplyChainService.ingest_sbom(
            db,
            org_a.id,
            user_analyst.id,
            product.id,
            SBOMDocumentCreate(
                software_product_id=product.id,
                sbom_code="SBOM-PAY-3",
                version="1.2.0",
                sha256_hash="g" * 64,  # 'g' is non-hex
            ),
        )
    assert exc_info.value.status_code == 422


def test_component_creation_and_prohibited_license_detection(db, org_a, user_analyst):
    # Set up prohibited license policy in Org A
    policy = SupplyChainService.create_license_policy(
        db,
        org_a.id,
        user_analyst.id,
        LicenseCompliancePolicyCreate(
            license_identifier="GPL-3.0-only",
            name="GNU GPL v3",
            category=LicenseCategoryEnum.STRONG_COPYLEFT,
            is_prohibited=True,
            risk_penalty_points=25.0,
        ),
    )
    assert policy.id is not None

    product = SupplyChainService.create_product(
        db, org_a.id, user_analyst.id, SoftwareProductCreate(product_code="PROD-COMP-001", name="API Gateway")
    )
    sbom = SupplyChainService.ingest_sbom(
        db,
        org_a.id,
        user_analyst.id,
        product.id,
        SBOMDocumentCreate(
            software_product_id=product.id,
            sbom_code="SBOM-API-1",
            version="1.0",
            sha256_hash="e" * 64,
        ),
    )

    comp = SupplyChainService.add_component_to_sbom(
        db,
        org_a.id,
        user_analyst.id,
        sbom.id,
        SoftwareComponentCreate(
            sbom_document_id=sbom.id,
            component_name="gpl-parser",
            version="2.0.1",
            purl="pkg:npm/gpl-parser@2.0.1",
            ecosystem=ComponentEcosystemEnum.NPM,
            dependency_depth=1,
            declared_license="GPL-3.0-only",
            license_category=LicenseCategoryEnum.STRONG_COPYLEFT,
        ),
    )
    # Automatically flagged as prohibited by organizational policy
    assert comp.is_license_prohibited is True
    assert comp.component_risk_index == 25.0


# ─── 4. Four-Eyes Exemption Governance & Self-Approval Prevention ───────────────

def test_exemption_lifecycle_and_self_approval_prevention(db, org_a, user_analyst, user_manager):
    product = SupplyChainService.create_product(
        db, org_a.id, user_analyst.id, SoftwareProductCreate(product_code="PROD-EX-GOV", name="Auth Service")
    )
    sbom = SupplyChainService.ingest_sbom(
        db,
        org_a.id,
        user_analyst.id,
        product.id,
        SBOMDocumentCreate(software_product_id=product.id, sbom_code="SBOM-AUTH-1", version="1.0", sha256_hash="f" * 64),
    )
    comp = SupplyChainService.add_component_to_sbom(
        db,
        org_a.id,
        user_analyst.id,
        sbom.id,
        SoftwareComponentCreate(
            sbom_document_id=sbom.id,
            component_name="legacy-auth",
            version="1.0.0",
            purl="pkg:pypi/legacy-auth@1.0.0",
            declared_license="Proprietary",
            license_category=LicenseCategoryEnum.PROHIBITED,
        ),
    )

    # 1. Analyst requests exemption
    exemption = SupplyChainService.request_exemption(
        db,
        org_a.id,
        user_analyst.id,
        SupplyChainExemptionCreate(
            exemption_code="EX-AUTH-001",
            software_product_id=product.id,
            component_id=comp.id,
            reason="Legacy single-sign-on protocol integration required",
            compensating_controls="Network isolation and mutual TLS termination",
        ),
    )
    assert exemption.approval_status == ExemptionApprovalStatusEnum.PENDING

    # 2. Self-approval blocked (Four-Eyes SoD violation)
    with pytest.raises(HTTPException) as exc_info:
        SupplyChainService.review_exemption(
            db,
            org_a.id,
            user_analyst.id,  # Requester attempting approval!
            exemption.id,
            SupplyChainExemptionReviewRequest(decision=ExemptionApprovalStatusEnum.APPROVED, reviewer_notes="Self-approval"),
        )
    assert exc_info.value.status_code == 422
    assert "Segregation of Duties" in str(exc_info.value.detail)

    # 3. Manager approves
    approved = SupplyChainService.review_exemption(
        db,
        org_a.id,
        user_manager.id,
        exemption.id,
        SupplyChainExemptionReviewRequest(decision=ExemptionApprovalStatusEnum.APPROVED, reviewer_notes="Approved with mitigation"),
    )
    assert approved.approval_status == ExemptionApprovalStatusEnum.APPROVED
    assert approved.reviewed_by_id == user_manager.id

    # 4. Finalized replay blocked
    with pytest.raises(HTTPException) as exc_info:
        SupplyChainService.review_exemption(
            db,
            org_a.id,
            user_manager.id,
            exemption.id,
            SupplyChainExemptionReviewRequest(decision=ExemptionApprovalStatusEnum.REJECTED, reviewer_notes="Replay attempt"),
        )
    assert exc_info.value.status_code == 409


# ─── 5. Cross-Tenant Relationship Protection ───────────────────────────────────

def test_cross_tenant_relationship_protection(db, org_a, org_b, user_analyst, user_org_b):
    # Org A product
    prod_a = SupplyChainService.create_product(
        db, org_a.id, user_analyst.id, SoftwareProductCreate(product_code="PROD-TENANT-A", name="App A")
    )

    # Org B cannot access Org A product
    with pytest.raises(HTTPException) as exc_info:
        SupplyChainService.get_product(db, org_b.id, prod_a.id)
    assert exc_info.value.status_code == 404

    # Org A cannot link Org B's business process
    bp_b = BusinessProcess(
        organization_id=org_b.id,
        owner_id=user_org_b.id,
        name="Org B Process",
        criticality_tier=CriticalityTierEnum.TIER_1,
    )
    db.add(bp_b)
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        SupplyChainService.create_product(
            db,
            org_a.id,
            user_analyst.id,
            SoftwareProductCreate(
                product_code="PROD-ESCAPE",
                name="Escaping App",
                business_process_id=bp_b.id,
            ),
        )
    assert exc_info.value.status_code == 404

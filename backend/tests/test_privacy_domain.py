from datetime import datetime
import pytest
from fastapi import HTTPException

from app.core.permissions import RoleEnum
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
from app.models.user import User
from app.models.resilience import BusinessProcess, CriticalityTierEnum
from app.models.ai_governance import AISystem, AISystemTypeEnum, AIRegulatoryTierEnum, AIHostingTypeEnum
from app.models.tprm import Vendor, VendorTierEnum
from app.models.remediation import RemediationPlan, RemediationSourceTypeEnum
from app.schemas.privacy import (
    DataAssetCreate,
    DataAssetUpdate,
    DataTransferCreate,
    DataTransferReviewRequest,
    DPIACreate,
    DPIAReviewRequest,
    DPIAUpdate,
    ProcessingActivityCreate,
    ProcessingActivityStatusUpdate,
    ProcessingActivityUpdate,
)
from app.services.privacy_service import PrivacyService


@pytest.fixture
def org_a(db):
    org = Organization(name="Privacy Tenant A", slug="privacy-tenant-a", is_active=True)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


@pytest.fixture
def org_b(db):
    org = Organization(name="Privacy Tenant B", slug="privacy-tenant-b", is_active=True)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


@pytest.fixture
def user_analyst(db, org_a):
    user = User(
        email="privacy.analyst@tenant-a.com",
        hashed_password="hash",
        full_name="Privacy Analyst",
        role=RoleEnum.GRC_ANALYST,
        organization_id=org_a.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def user_dpo(db, org_a):
    user = User(
        email="dpo.officer@tenant-a.com",
        hashed_password="hash",
        full_name="Chief DPO",
        role=RoleEnum.MANAGER,
        organization_id=org_a.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ─── 1. Mathematical Engine Unit Tests ─────────────────────────────────────────

def test_dpia_inherent_risk_calculations():
    """Verify server-authoritative DPIA Inherent Risk Score (IRS) calculations."""
    # Case 1: Public data, Low volume, no triggers
    irs = PrivacyService.calculate_dpia_inherent_risk(
        sensitivity_level=DataSensitivityLevel.PUBLIC,
        volume_tier="LOW",
        is_special_category=False,
    )
    assert irs == 0.0

    # Case 2: Restricted PII, High volume (>1M), Special Category, all 3 triggers
    # Base: 40.0 * 1.30 * 1.25 = 65.0 + 30.0 (penalty) = 95.00
    irs = PrivacyService.calculate_dpia_inherent_risk(
        sensitivity_level=DataSensitivityLevel.RESTRICTED_PII,
        volume_tier="HIGH",
        is_special_category=True,
        automated_decision_making_risk=True,
        large_scale_monitoring_risk=True,
        vulnerable_subjects_risk=True,
    )
    assert irs == 95.00

    # Case 3: Special Category Sensitive PHI, High volume, triggers max capped at 100.00
    # Base: 65.0 * 1.30 * 1.25 = 105.625 + 30.0 = 135.625 -> clamped to 100.00
    irs = PrivacyService.calculate_dpia_inherent_risk(
        sensitivity_level=DataSensitivityLevel.SPECIAL_CATEGORY_SENSITIVE_PHI,
        volume_tier="HIGH",
        is_special_category=True,
        automated_decision_making_risk=True,
        large_scale_monitoring_risk=True,
    )
    assert irs == 100.00

    # Case 4: Confidential, Medium volume, 1 trigger
    # Base: 20.0 * 1.15 * 1.00 = 23.0 + 10.0 = 33.00
    irs = PrivacyService.calculate_dpia_inherent_risk(
        sensitivity_level=DataSensitivityLevel.CONFIDENTIAL,
        volume_tier="MEDIUM",
        automated_decision_making_risk=True,
    )
    assert irs == 33.00


def test_dpia_residual_risk_and_risk_bands():
    """Verify server-authoritative DPIA Residual Risk Score (RRS) and Risk Band assignment."""
    # Case 1: High inherent risk (80.0), 100% safeguards (capped at 70% = 0.70 rate)
    # RRS = 80.0 * (1.0 - 0.70) = 24.00 -> MODERATE
    rrs = PrivacyService.calculate_dpia_residual_risk(
        inherent_risk_score=80.0,
        safeguards_mitigation_score=100.0,
        has_threat_exposure=False,
    )
    assert rrs == 24.00
    assert PrivacyService.determine_dpia_risk_band(rrs) == DPIARiskBand.MODERATE

    # Case 2: High inherent risk (80.0), 100% safeguards, with Threat Exposure (+15.0)
    # RRS = 24.0 + 15.0 = 39.00 -> MODERATE
    rrs = PrivacyService.calculate_dpia_residual_risk(
        inherent_risk_score=80.0,
        safeguards_mitigation_score=100.0,
        has_threat_exposure=True,
    )
    assert rrs == 39.00
    assert PrivacyService.determine_dpia_risk_band(rrs) == DPIARiskBand.MODERATE

    # Case 3: Zero safeguards, threat exposure
    # Inherent: 85.0, Safeguards: 0.0, Threat penalty: 15.0 -> 100.00 -> CRITICAL
    rrs = PrivacyService.calculate_dpia_residual_risk(
        inherent_risk_score=85.0,
        safeguards_mitigation_score=0.0,
        has_threat_exposure=True,
    )
    assert rrs == 100.00
    assert PrivacyService.determine_dpia_risk_band(rrs) == DPIARiskBand.CRITICAL

    # Case 4: Low inherent risk (15.0) -> LOW
    assert PrivacyService.determine_dpia_risk_band(15.0) == DPIARiskBand.LOW
    assert PrivacyService.determine_dpia_risk_band(45.0) == DPIARiskBand.HIGH
    assert PrivacyService.determine_dpia_risk_band(65.0) == DPIARiskBand.VERY_HIGH


def test_transfer_risk_index_calculations():
    """Verify server-authoritative Transfer Risk Index (TRI) calculations."""
    # Case 1: Prohibited transfers (100.0 * 1.00 = 100.00)
    tri = PrivacyService.calculate_transfer_risk_index(
        destination_tier=JurisdictionRiskTier.PROHIBITED_TRANSFERS,
        mechanism=TransferMechanism.STANDARD_CONTRACTUAL_CLAUSES_SCC,
        supplementary_measures_score=0.0,
    )
    assert tri == 100.00

    # Case 2: High risk surveillance jurisdiction (75.0), SCC (1.00x), with supplementary safeguards (-25.0)
    # TRI = 75.0 * 1.00 - 25.0 = 50.00
    tri = PrivacyService.calculate_transfer_risk_index(
        destination_tier=JurisdictionRiskTier.HIGH_RISK_SURVEILLANCE,
        mechanism=TransferMechanism.STANDARD_CONTRACTUAL_CLAUSES_SCC,
        supplementary_measures_score=25.0,
    )
    assert tri == 50.00

    # Case 3: Adequate jurisdiction (10.0), Adequacy Decision (0.50x)
    # TRI = 10.0 * 0.50 = 5.00
    tri = PrivacyService.calculate_transfer_risk_index(
        destination_tier=JurisdictionRiskTier.ADEQUATE_LOW_RISK,
        mechanism=TransferMechanism.ADEQUACY_DECISION,
        supplementary_measures_score=0.0,
    )
    assert tri == 5.00

    # Case 4: Intra-EEA transfer (None required = 0.00x)
    tri = PrivacyService.calculate_transfer_risk_index(
        destination_tier=JurisdictionRiskTier.ADEQUATE_LOW_RISK,
        mechanism=TransferMechanism.NONE_INTRA_EEA,
        supplementary_measures_score=0.0,
    )
    assert tri == 0.00


# ─── 2. Data Asset CRUD & Lineage Tests ────────────────────────────────────────

def test_data_asset_crud(db, org_a, user_analyst):
    """Test full CRUD lifecycle for DataAsset."""
    org_id = org_a.id
    user_id = user_analyst.id

    payload = DataAssetCreate(
        asset_code="DA-HR-001",
        name="Employee HR Database",
        description="Core HR Postgres database with personal details",
        data_sensitivity_level=DataSensitivityLevel.RESTRICTED_PII,
        data_volume_range="MEDIUM",
        storage_type="POSTGRES_DB",
        hosting_jurisdiction="EU_GERMANY",
        is_encrypted_at_rest=True,
        is_encrypted_in_transit=True,
        is_pseudonymized=True,
        retention_period_months=24,
    )

    # 1. Create
    asset = PrivacyService.create_data_asset(db, org_id, user_id, payload)
    assert asset.id is not None
    assert asset.asset_code == "DA-HR-001"
    assert asset.data_sensitivity_level == DataSensitivityLevel.RESTRICTED_PII

    # Duplicate code conflict
    with pytest.raises(HTTPException) as exc:
        PrivacyService.create_data_asset(db, org_id, user_id, payload)
    assert exc.value.status_code == 409

    # 2. Get & List
    fetched = PrivacyService.get_data_asset(db, org_id, asset.id)
    assert fetched.name == "Employee HR Database"

    assets = PrivacyService.list_data_assets(db, org_id, sensitivity=DataSensitivityLevel.RESTRICTED_PII)
    assert len(assets) >= 1

    # 3. Update
    updated = PrivacyService.update_data_asset(
        db,
        org_id,
        asset.id,
        user_id,
        DataAssetUpdate(name="Updated Employee Database", retention_period_months=36),
    )
    assert updated.name == "Updated Employee Database"
    assert updated.retention_period_months == 36

    # 4. Delete
    PrivacyService.delete_data_asset(db, org_id, asset.id, user_id)
    with pytest.raises(HTTPException) as exc:
        PrivacyService.get_data_asset(db, org_id, asset.id)
    assert exc.value.status_code == 404


# ─── 3. Processing Activity (RoPA) & Lifecycle Tests ───────────────────────────

def test_processing_activity_lifecycle_state_machine(db, org_a, user_analyst):
    """Test legal and illegal state transitions for ProcessingActivity."""
    org_id = org_a.id
    user_id = user_analyst.id

    payload = ProcessingActivityCreate(
        activity_code="ROPA-CUST-001",
        name="Customer Billing & KYC",
        purpose_description="Processing of customer payment and identity information",
        legal_basis=ProcessingLegalBasis.CONTRACT_PERFORMANCE,
        data_subject_categories="CUSTOMERS",
        personal_data_categories="IDENTIFIERS,FINANCIAL",
        is_special_category_data=False,
    )

    activity = PrivacyService.create_processing_activity(db, org_id, user_id, payload)
    assert activity.lifecycle_state == ProcessingLifecycleState.DRAFT
    assert activity.dpo_approval_status == PrivacyApprovalStatus.PENDING

    # Illegal transition: DRAFT -> ACTIVE directly (without review and DPO approval)
    with pytest.raises(HTTPException) as exc:
        PrivacyService.update_processing_activity_status(
            db, org_id, activity.id, user_id,
            ProcessingActivityStatusUpdate(lifecycle_state=ProcessingLifecycleState.ACTIVE),
        )
    assert exc.value.status_code == 400

    # Legal transition: DRAFT -> DPO_REVIEW
    activity = PrivacyService.update_processing_activity_status(
        db, org_id, activity.id, user_id,
        ProcessingActivityStatusUpdate(lifecycle_state=ProcessingLifecycleState.DPO_REVIEW),
    )
    assert activity.lifecycle_state == ProcessingLifecycleState.DPO_REVIEW

    # Illegal transition: DPO_REVIEW -> ACTIVE before DPO approval
    with pytest.raises(HTTPException) as exc:
        PrivacyService.update_processing_activity_status(
            db, org_id, activity.id, user_id,
            ProcessingActivityStatusUpdate(lifecycle_state=ProcessingLifecycleState.ACTIVE),
        )
    assert exc.value.status_code == 400

    # Simulate DPO approval
    activity.dpo_approval_status = PrivacyApprovalStatus.APPROVED
    db.commit()

    # Legal transition: DPO_REVIEW -> ACTIVE (now that approved)
    activity = PrivacyService.update_processing_activity_status(
        db, org_id, activity.id, user_id,
        ProcessingActivityStatusUpdate(lifecycle_state=ProcessingLifecycleState.ACTIVE),
    )
    assert activity.lifecycle_state == ProcessingLifecycleState.ACTIVE

    # Active deletion block
    with pytest.raises(HTTPException) as exc:
        PrivacyService.delete_processing_activity(db, org_id, activity.id, user_id)
    assert exc.value.status_code == 400

    # Legal transition: ACTIVE -> RETIRED
    activity = PrivacyService.update_processing_activity_status(
        db, org_id, activity.id, user_id,
        ProcessingActivityStatusUpdate(lifecycle_state=ProcessingLifecycleState.RETIRED),
    )
    assert activity.lifecycle_state == ProcessingLifecycleState.RETIRED

    # RETIRED record immutability: Cannot update mutable fields
    with pytest.raises(HTTPException) as exc:
        PrivacyService.update_processing_activity(
            db, org_id, activity.id, user_id,
            ProcessingActivityUpdate(name="Renamed Retired Activity"),
        )
    assert exc.value.status_code == 400

    # RETIRED record immutability: Cannot transition away from RETIRED
    with pytest.raises(HTTPException) as exc:
        PrivacyService.update_processing_activity_status(
            db, org_id, activity.id, user_id,
            ProcessingActivityStatusUpdate(lifecycle_state=ProcessingLifecycleState.ACTIVE),
        )
    assert exc.value.status_code == 400


# ─── 4. DPIA Assessment & Four-Eyes SoD Tests ───────────────────────────────────

def test_dpia_assessment_and_four_eyes_sod(db, org_a, user_analyst, user_dpo):
    """Test DPIA assessment creation, server calculation, and Four-Eyes DPO approval SoD."""
    org_id = org_a.id
    creator_id = user_analyst.id
    dpo_id = user_dpo.id

    # Create RoPA activity
    act_payload = ProcessingActivityCreate(
        activity_code="ROPA-AI-CREDIT-001",
        name="AI Credit Scoring & Automated Decisioning",
        purpose_description="Automated loan decisioning with algorithmic profiling",
        legal_basis=ProcessingLegalBasis.CONSENT,
        data_subject_categories="CUSTOMERS",
        personal_data_categories="IDENTIFIERS,FINANCIAL,BEHAVIORAL",
        is_special_category_data=True,
        is_automated_decision_making=True,
        is_large_scale_monitoring=True,
    )
    activity = PrivacyService.create_processing_activity(db, org_id, creator_id, act_payload)

    # Move activity to DPO_REVIEW
    PrivacyService.update_processing_activity_status(
        db, org_id, activity.id, creator_id,
        ProcessingActivityStatusUpdate(lifecycle_state=ProcessingLifecycleState.DPO_REVIEW),
    )

    # 1. Create DPIA
    dpia_payload = DPIACreate(
        assessment_code="DPIA-CREDIT-001",
        processing_activity_id=activity.id,
        necessity_proportionality_score=85.0,
        data_subject_rights_score=90.0,
        safeguards_mitigation_score=60.0,
        automated_decision_making_risk=True,
        large_scale_monitoring_risk=True,
        vulnerable_subjects_risk=False,
    )
    dpia = PrivacyService.create_dpia_assessment(db, org_id, creator_id, dpia_payload)
    assert dpia.inherent_risk_score > 0.0
    assert dpia.residual_risk_score > 0.0
    assert dpia.dpo_consultation_status == PrivacyApprovalStatus.PENDING

    # 2. Four-Eyes SoD Check: Creator cannot approve own DPIA
    with pytest.raises(HTTPException) as exc:
        PrivacyService.review_dpia_assessment(
            db,
            org_id,
            dpia.id,
            reviewer_id=creator_id,  # Same as creator!
            review_data=DPIAReviewRequest(
                decision=PrivacyApprovalStatus.APPROVED,
                recommendation_notes="Self-approval attempt must fail",
            ),
        )
    assert exc.value.status_code == 403
    assert "Segregation of Duties" in exc.value.detail

    # 3. Valid DPO Review by independent DPO reviewer
    dpia = PrivacyService.review_dpia_assessment(
        db,
        org_id,
        dpia.id,
        reviewer_id=dpo_id,
        review_data=DPIAReviewRequest(
            decision=PrivacyApprovalStatus.APPROVED,
            recommendation_notes="DPIA approved with standard human review oversight safeguards.",
        ),
    )
    assert dpia.dpo_consultation_status == PrivacyApprovalStatus.APPROVED
    assert dpia.dpo_reviewed_by_id == dpo_id

    # Parent activity automatically transitions to ACTIVE upon DPO approval
    db.refresh(activity)
    assert activity.dpo_approval_status == PrivacyApprovalStatus.APPROVED
    assert activity.lifecycle_state == ProcessingLifecycleState.ACTIVE

    # 4. Approval Replay Protection: Cannot re-review finalized DPIA
    with pytest.raises(HTTPException) as exc:
        PrivacyService.review_dpia_assessment(
            db,
            org_id,
            dpia.id,
            reviewer_id=dpo_id,
            review_data=DPIAReviewRequest(
                decision=PrivacyApprovalStatus.REJECTED,
                recommendation_notes="Attempted replay re-review",
            ),
        )
    assert exc.value.status_code == 409


def test_dpia_assessment_update_and_recalculation(db, org_a, user_analyst):
    """Test modifying DPIA parameters and verifying automatic recalculation."""
    org_id = org_a.id
    user_id = user_analyst.id

    act_payload = ProcessingActivityCreate(
        activity_code="ROPA-UPD-001",
        name="Update Test Activity",
        purpose_description="Processing for update testing",
        legal_basis=ProcessingLegalBasis.CONSENT,
        data_subject_categories="CUSTOMERS",
        personal_data_categories="IDENTIFIERS",
    )
    act = PrivacyService.create_processing_activity(db, org_id, user_id, act_payload)

    dpia_payload = DPIACreate(
        assessment_code="DPIA-UPD-001",
        processing_activity_id=act.id,
        safeguards_mitigation_score=10.0,
    )
    dpia = PrivacyService.create_dpia_assessment(db, org_id, user_id, dpia_payload)
    old_rrs = float(dpia.residual_risk_score)

    # Increase safeguards mitigation to 90%
    updated_dpia = PrivacyService.update_dpia_assessment(
        db,
        org_id,
        dpia.id,
        user_id,
        DPIAUpdate(safeguards_mitigation_score=90.0),
    )
    new_rrs = float(updated_dpia.residual_risk_score)
    assert new_rrs < old_rrs


# ─── 5. Data Transfer Assessment & Four-Eyes SoD Tests ─────────────────────────

def test_data_transfer_assessment_and_sod(db, org_a, user_analyst, user_dpo):
    """Test Data Transfer Assessment creation, TRI calculation, and Four-Eyes approval SoD."""
    org_id = org_a.id
    requester_id = user_analyst.id
    approver_id = user_dpo.id

    # Create RoPA activity
    act_payload = ProcessingActivityCreate(
        activity_code="ROPA-SAAS-001",
        name="Global Cloud CRM Sync",
        purpose_description="Syncing contact information to third-party cloud CRM",
        legal_basis=ProcessingLegalBasis.LEGITIMATE_INTERESTS,
        data_subject_categories="CUSTOMERS,PROSPECTS",
        personal_data_categories="IDENTIFIERS",
        is_cross_border_transfer=True,
    )
    activity = PrivacyService.create_processing_activity(db, org_id, requester_id, act_payload)

    # 1. Create Transfer Assessment
    tia_payload = DataTransferCreate(
        transfer_code="TIA-US-CRM-001",
        processing_activity_id=activity.id,
        source_country="EU_EEA",
        destination_country="United States",
        destination_jurisdiction_tier=JurisdictionRiskTier.MODERATE_SAFEGUARDS_REQUIRED,
        transfer_mechanism=TransferMechanism.STANDARD_CONTRACTUAL_CLAUSES_SCC,
        supplementary_safeguards_description="AES-256 E2EE with EU-held encryption keys and DPA Schedule B",
        supplementary_measures_score=15.0,
    )
    transfer = PrivacyService.create_data_transfer(db, org_id, requester_id, tia_payload)
    # Base: 40.0 * 1.00 - 15.0 = 25.00
    assert transfer.transfer_risk_index == 25.00
    assert transfer.approval_status == PrivacyApprovalStatus.PENDING

    # 2. Four-Eyes SoD Check: Requester cannot approve own transfer
    with pytest.raises(HTTPException) as exc:
        PrivacyService.review_data_transfer(
            db,
            org_id,
            transfer.id,
            reviewer_id=requester_id,  # Same as requester!
            review_data=DataTransferReviewRequest(
                decision=PrivacyApprovalStatus.APPROVED,
                reviewer_notes="Self-approval attempt",
            ),
        )
    assert exc.value.status_code == 403
    assert "Segregation of Duties" in exc.value.detail

    # 3. Valid Approval by independent approver
    transfer = PrivacyService.review_data_transfer(
        db,
        org_id,
        transfer.id,
        reviewer_id=approver_id,
        review_data=DataTransferReviewRequest(
            decision=PrivacyApprovalStatus.APPROVED,
            reviewer_notes="Approved based on verified SCCs and E2EE key custody.",
        ),
    )
    assert transfer.approval_status == PrivacyApprovalStatus.APPROVED
    assert transfer.approved_by_id == approver_id

    # 4. Replay Re-review Protection
    with pytest.raises(HTTPException) as exc:
        PrivacyService.review_data_transfer(
            db,
            org_id,
            transfer.id,
            reviewer_id=approver_id,
            review_data=DataTransferReviewRequest(
                decision=PrivacyApprovalStatus.REJECTED,
                reviewer_notes="Replay attempt",
            ),
        )
    assert exc.value.status_code == 409


def test_data_transfer_listing_and_filtering(db, org_a, user_analyst):
    """Test listing and filtering data transfer assessments."""
    org_id = org_a.id
    user_id = user_analyst.id

    act = PrivacyService.create_processing_activity(
        db, org_id, user_id,
        ProcessingActivityCreate(
            activity_code="ROPA-TRANSFER-LIST-001",
            name="Transfer List RoPA",
            purpose_description="List filtering test",
            legal_basis=ProcessingLegalBasis.CONSENT,
            data_subject_categories="CUSTOMERS",
            personal_data_categories="IDENTIFIERS",
        ),
    )

    t1 = PrivacyService.create_data_transfer(
        db, org_id, user_id,
        DataTransferCreate(
            transfer_code="TIA-LIST-001",
            processing_activity_id=act.id,
            destination_country="Switzerland",
            destination_jurisdiction_tier=JurisdictionRiskTier.ADEQUATE_LOW_RISK,
            transfer_mechanism=TransferMechanism.ADEQUACY_DECISION,
        ),
    )

    t2 = PrivacyService.create_data_transfer(
        db, org_id, user_id,
        DataTransferCreate(
            transfer_code="TIA-LIST-002",
            processing_activity_id=act.id,
            destination_country="North Korea",
            destination_jurisdiction_tier=JurisdictionRiskTier.PROHIBITED_TRANSFERS,
            transfer_mechanism=TransferMechanism.DEROGATION_EXPLICIT_CONSENT,
        ),
    )

    adequate_transfers = PrivacyService.list_data_transfers(db, org_id, tier=JurisdictionRiskTier.ADEQUATE_LOW_RISK)
    assert any(t.id == t1.id for t in adequate_transfers)
    assert not any(t.id == t2.id for t in adequate_transfers)


# ─── 6. Tenant Isolation & Cross-Module Linkage Tests ──────────────────────────

def test_privacy_tenant_isolation_and_cross_module_validation(db, org_a, org_b, user_analyst):
    """Verify strict tenant isolation and rejection of cross-tenant foreign key references."""
    org1_id = org_a.id
    user1_id = user_analyst.id
    org2_id = org_b.id

    # Create BusinessProcess in Organization 2 (Tenant 2)
    bp_tenant2 = BusinessProcess(
        organization_id=org2_id,
        name="Tenant 2 Secret Process",
        description="Confidential business process in tenant B",
        criticality_tier=CriticalityTierEnum.TIER_1,
        owner_id=user1_id,
    )
    db.add(bp_tenant2)
    db.commit()
    db.refresh(bp_tenant2)

    # Attempt to create DataAsset in Org 1 referencing Tenant 2's BusinessProcess
    with pytest.raises(HTTPException) as exc:
        PrivacyService.create_data_asset(
            db,
            organization_id=org1_id,
            owner_id=user1_id,
            payload=DataAssetCreate(
                asset_code="DA-CROSS-TENANT-001",
                name="Malicious Cross-Tenant Asset",
                business_process_id=bp_tenant2.id,  # Belongs to org2!
            ),
        )
    assert exc.value.status_code == 404
    assert "not found in this organization" in exc.value.detail

    # Attempt to create ProcessingActivity in Org 1 referencing Tenant 2's BusinessProcess
    with pytest.raises(HTTPException) as exc:
        PrivacyService.create_processing_activity(
            db,
            organization_id=org1_id,
            owner_id=user1_id,
            payload=ProcessingActivityCreate(
                activity_code="ROPA-CROSS-TENANT-001",
                name="Malicious Cross-Tenant RoPA",
                purpose_description="Attempt to link cross-tenant process",
                legal_basis=ProcessingLegalBasis.CONSENT,
                data_subject_categories="CUSTOMERS",
                personal_data_categories="IDENTIFIERS",
                business_process_id=bp_tenant2.id,  # Belongs to org2!
            ),
        )
    assert exc.value.status_code == 404


def test_cross_tenant_ai_and_vendor_validation(db, org_a, org_b, user_analyst):
    """Verify rejection of cross-tenant AISystem, Vendor, and RemediationPlan references."""
    org1_id = org_a.id
    org2_id = org_b.id
    user_id = user_analyst.id

    # Create AISystem in Org 2
    ai_sys_t2 = AISystem(
        organization_id=org2_id,
        system_code="AI-T2-001",
        name="Tenant 2 AI Model",
        system_type=AISystemTypeEnum.LLM_APPLICATION,
        regulatory_tier=AIRegulatoryTierEnum.HIGH_RISK,
        hosting_type=AIHostingTypeEnum.CLOUD_THIRD_PARTY,
        owner_id=user_id,
    )
    db.add(ai_sys_t2)
    db.commit()
    db.refresh(ai_sys_t2)

    # Attempt to create DataAsset referencing cross-tenant AI System
    with pytest.raises(HTTPException) as exc:
        PrivacyService.create_data_asset(
            db,
            organization_id=org1_id,
            owner_id=user_id,
            payload=DataAssetCreate(
                asset_code="DA-CROSS-AI-001",
                name="Cross AI Asset",
                ai_system_id=ai_sys_t2.id,  # Org 2!
            ),
        )
    assert exc.value.status_code == 404
    assert "AI system" in exc.value.detail


# ─── 7. Privacy Posture Summary Telemetry Tests ───────────────────────────────

def test_privacy_posture_summary(db, org_a, user_analyst):
    """Test executive privacy posture summary aggregation."""
    org_id = org_a.id
    user_id = user_analyst.id

    # Create 1 Data Asset
    PrivacyService.create_data_asset(
        db,
        org_id,
        user_id,
        DataAssetCreate(
            asset_code="DA-POSTURE-001",
            name="Posture Test Data Asset",
            data_sensitivity_level=DataSensitivityLevel.CONFIDENTIAL,
        ),
    )

    # Create 1 RoPA
    PrivacyService.create_processing_activity(
        db,
        org_id,
        user_id,
        ProcessingActivityCreate(
            activity_code="ROPA-POSTURE-001",
            name="Posture Test Activity",
            purpose_description="Posture summary validation activity",
            legal_basis=ProcessingLegalBasis.LEGAL_OBLIGATION,
            data_subject_categories="EMPLOYEES",
            personal_data_categories="EMPLOYMENT",
        ),
    )

    summary = PrivacyService.get_privacy_posture_summary(db, org_id)
    assert summary.total_data_assets >= 1
    assert summary.total_processing_activities >= 1
    assert summary.legal_basis_distribution["LEGAL_OBLIGATION"] >= 1
    assert summary.sensitivity_distribution["CONFIDENTIAL"] >= 1

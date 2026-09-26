from datetime import datetime, timezone
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.cloudsec import (
    CloudAsset,
    CloudAssetTypeEnum,
    CloudCriticalityEnum,
    CloudEnvironmentEnum,
    CloudLifecycleStateEnum,
    CloudPostureStatusEnum,
    CloudProviderEnum,
)
from app.models.control import ImplementationStatusEnum, OrganizationControl
from app.models.data_governance import (
    DataAssetLifecycleEnum,
    DataAssetTypeEnum,
    DataClassificationApprovalStatusEnum,
    DataClassificationChangeTypeEnum,
    DataClassificationRecordStatusEnum,
    DataClassificationSchemeStatusEnum,
    DataCloudHostingRoleEnum,
    DataControlObjectiveEnum,
    DataDisposalMethodEnum,
    DataEvidencePurposeEnum,
    DataLineageRelationshipTypeEnum,
    DataLineageStatusEnum,
    DataOwnerTransferStatusEnum,
    DataProcessingUsageRoleEnum,
)
from app.models.evidence import EvidenceItem, EvidenceStatusEnum
from app.models.framework import (
    Framework,
    FrameworkCategory,
    FrameworkFunction,
    FrameworkSubcategory,
)
from app.models.organization import Organization
from app.models.privacy import (
    DataSensitivityLevel,
    ProcessingActivity,
    ProcessingLegalBasis,
    ProcessingLifecycleState,
)
from app.models.regulatory import (
    RegulatoryApplicabilityEnum,
    RegulatoryComplianceStatusEnum,
    RegulatoryMandate,
    RegulatoryObligation,
    RegulatorySource,
)
from app.models.user import User
from app.schemas.data_governance import (
    DataAssetCloudLinkCreate,
    DataAssetControlLinkCreate,
    DataAssetDeprecateRequest,
    DataAssetEvidenceLinkCreate,
    DataAssetProcessingLinkCreate,
    DataAssetRegisterRequest,
    DataAssetRestoreRequest,
    DataAssetRetireRequest,
    DataClassificationLevelCreate,
    DataClassificationRejectRequest,
    DataClassificationRequestCreate,
    DataClassificationSchemeCreate,
    DataLineageEdgeCreate,
    DataLineageEdgeRevokeRequest,
    DataOwnershipUpdateRequest,
    GovernedDataAssetCreate,
)
from app.services.data_governance_service import DataGovernanceService


@pytest.fixture
def dg_domain_env(db: Session):
    org = Organization(name="DataGov Enterprise", slug="datagov-ent")
    db.add(org)
    db.flush()

    analyst = User(
        organization_id=org.id,
        email="analyst@datagov.example.com",
        full_name="Data Analyst",
        hashed_password="hash",
        role="GRC_ANALYST",
        is_active=True,
    )
    steward = User(
        organization_id=org.id,
        email="steward@datagov.example.com",
        full_name="Data Steward",
        hashed_password="hash",
        role="GRC_ANALYST",
        is_active=True,
    )
    manager = User(
        organization_id=org.id,
        email="manager@datagov.example.com",
        full_name="Governance Manager",
        hashed_password="hash",
        role="MANAGER",
        is_active=True,
    )
    admin = User(
        organization_id=org.id,
        email="admin@datagov.example.com",
        full_name="Platform Admin",
        hashed_password="hash",
        role="ADMIN",
        is_active=True,
    )
    inactive_user = User(
        organization_id=org.id,
        email="inactive@datagov.example.com",
        full_name="Former Employee",
        hashed_password="hash",
        role="GRC_ANALYST",
        is_active=False,
    )
    db.add_all([analyst, steward, manager, admin, inactive_user])
    db.flush()

    # Create Framework & Control for Evidence and Regulatory Obligation
    fw = Framework(identifier="ISO27001-DG", name="ISO 27001 Data Gov", version="2022")
    db.add(fw)
    db.flush()
    fn = FrameworkFunction(framework_id=fw.id, identifier="PR", name="Protect")
    db.add(fn)
    db.flush()
    cat = FrameworkCategory(function_id=fn.id, identifier="PR.DS", name="Data Security")
    db.add(cat)
    db.flush()
    sub = FrameworkSubcategory(
        category_id=cat.id,
        identifier="PR.DS-01",
        title="Data-at-rest is protected",
        description="Encryption at rest",
    )
    db.add(sub)
    db.flush()

    ctrl = OrganizationControl(
        organization_id=org.id,
        subcategory_id=sub.id,
        status=ImplementationStatusEnum.IMPLEMENTED,
        owner_id=manager.id,
    )
    db.add(ctrl)
    db.flush()

    evidence = EvidenceItem(
        organization_id=org.id,
        organization_control_id=ctrl.id,
        uploaded_by_id=analyst.id,
        title="Cryptographic Erasure Certificate",
        original_filename="erasure_cert.pdf",
        stored_filename="stored_erasure_cert.pdf",
        file_extension="pdf",
        content_type="application/pdf",
        file_size=2048,
        sha256_hash="a" * 64,
        storage_key="evidence/erasure_cert.pdf",
        status=EvidenceStatusEnum.ACCEPTED,
    )
    rejected_evidence = EvidenceItem(
        organization_id=org.id,
        organization_control_id=ctrl.id,
        uploaded_by_id=analyst.id,
        title="Rejected Disposal Note",
        original_filename="rejected.pdf",
        stored_filename="stored_rejected.pdf",
        file_extension="pdf",
        content_type="application/pdf",
        file_size=1024,
        sha256_hash="b" * 64,
        storage_key="evidence/rejected.pdf",
        status=EvidenceStatusEnum.REJECTED,
    )
    db.add_all([evidence, rejected_evidence])
    db.flush()

    # Create CloudAssets (one compliant, one misconfigured)
    cloud_compliant = CloudAsset(
        organization_id=org.id,
        asset_code="CLD-S3-ENC-01",
        provider=CloudProviderEnum.AWS,
        account_id="123456789012",
        region="eu-central-1",
        resource_type=CloudAssetTypeEnum.S3_BUCKET,
        resource_arn="arn:aws:s3:::dg-compliant-lake",
        resource_name="dg-compliant-lake",
        environment=CloudEnvironmentEnum.PRODUCTION,
        criticality=CloudCriticalityEnum.CRITICAL,
        posture_status=CloudPostureStatusEnum.COMPLIANT,
        posture_score=100.0,
        blast_radius_score=10.0,
        lifecycle_state=CloudLifecycleStateEnum.ACTIVE,
        is_internet_facing=False,
        encryption_enabled=True,
        owner_id=admin.id,
    )
    cloud_drifted = CloudAsset(
        organization_id=org.id,
        asset_code="CLD-S3-PUB-02",
        provider=CloudProviderEnum.AWS,
        account_id="123456789012",
        region="us-east-1",
        resource_type=CloudAssetTypeEnum.S3_BUCKET,
        resource_arn="arn:aws:s3:::dg-public-unencrypted",
        resource_name="dg-public-unencrypted",
        environment=CloudEnvironmentEnum.PRODUCTION,
        criticality=CloudCriticalityEnum.HIGH,
        posture_status=CloudPostureStatusEnum.NON_COMPLIANT,
        posture_score=30.0,
        blast_radius_score=85.0,
        lifecycle_state=CloudLifecycleStateEnum.ACTIVE,
        is_internet_facing=True,
        encryption_enabled=False,
        owner_id=admin.id,
    )
    db.add_all([cloud_compliant, cloud_drifted])
    db.flush()

    # Create ProcessingActivity (RoPA)
    ropa = ProcessingActivity(
        organization_id=org.id,
        activity_code="ROPA-DG-001",
        name="Customer Analytics & Billing",
        purpose_description="Billing and contractual service analytics",
        legal_basis=ProcessingLegalBasis.CONTRACT_PERFORMANCE,
        data_subject_categories="CUSTOMERS",
        personal_data_categories="FINANCIAL,CONTACT",
        lifecycle_state=ProcessingLifecycleState.ACTIVE,
        owner_id=manager.id,
    )
    db.add(ropa)
    db.flush()

    # Create Regulatory Obligation mapped to ctrl
    reg_src = RegulatorySource(
        organization_id=org.id,
        source_code="EU-GDPR-DG",
        name="European Data Protection Board",
        jurisdiction="EU",
    )
    db.add(reg_src)
    db.flush()
    mandate = RegulatoryMandate(
        organization_id=org.id,
        source_id=reg_src.id,
        mandate_code="GDPR-2016-679",
        title="General Data Protection Regulation",
        short_name="GDPR",
        jurisdiction="EU",
    )
    db.add(mandate)
    db.flush()
    obligation = RegulatoryObligation(
        organization_id=org.id,
        mandate_id=mandate.id,
        obligation_code="GDPR-ART-32",
        title="Security of Processing (Encryption & Pseudonymisation)",
        description="Implement appropriate technical and organisational measures.",
        article_reference="Article 32",
        applicability=RegulatoryApplicabilityEnum.APPLICABLE,
        organization_control_id=ctrl.id,
        compliance_status=RegulatoryComplianceStatusEnum.COMPLIANT,
    )
    db.add(obligation)
    db.commit()

    return {
        "org": org,
        "analyst": analyst,
        "steward": steward,
        "manager": manager,
        "admin": admin,
        "inactive_user": inactive_user,
        "control": ctrl,
        "evidence": evidence,
        "rejected_evidence": rejected_evidence,
        "cloud_compliant": cloud_compliant,
        "cloud_drifted": cloud_drifted,
        "ropa": ropa,
        "obligation": obligation,
    }


def _create_active_scheme(db: Session, env: dict):
    org_id = env["org"].id
    scheme = DataGovernanceService.create_scheme(
        db=db,
        organization_id=org_id,
        actor_id=env["analyst"].id,
        payload=DataClassificationSchemeCreate(
            scheme_code="CS-ENT-2026",
            name="Enterprise Data Classification Standard",
            version=1,
            is_default=True,
        ),
    )
    lvl_pub = DataGovernanceService.add_level_to_scheme(
        db=db,
        organization_id=org_id,
        scheme_id=scheme.id,
        actor_id=env["analyst"].id,
        payload=DataClassificationLevelCreate(
            level_code="L1-PUBLIC",
            name="Public Data",
            ordinal_rank=1,
            mapped_sensitivity_level=DataSensitivityLevel.PUBLIC,
            requires_encryption_at_rest=False,
            requires_encryption_in_transit=True,
            requires_four_eyes_approval=False,
            default_retention_months=6,
        ),
    )
    lvl_int = DataGovernanceService.add_level_to_scheme(
        db=db,
        organization_id=org_id,
        scheme_id=scheme.id,
        actor_id=env["analyst"].id,
        payload=DataClassificationLevelCreate(
            level_code="L2-INTERNAL",
            name="Internal Business Data",
            ordinal_rank=2,
            mapped_sensitivity_level=DataSensitivityLevel.INTERNAL,
            requires_encryption_at_rest=True,
            requires_encryption_in_transit=True,
            requires_four_eyes_approval=False,
            default_retention_months=24,
        ),
    )
    lvl_conf = DataGovernanceService.add_level_to_scheme(
        db=db,
        organization_id=org_id,
        scheme_id=scheme.id,
        actor_id=env["analyst"].id,
        payload=DataClassificationLevelCreate(
            level_code="L3-CONFIDENTIAL",
            name="Confidential Data",
            ordinal_rank=3,
            mapped_sensitivity_level=DataSensitivityLevel.CONFIDENTIAL,
            requires_encryption_at_rest=True,
            requires_encryption_in_transit=True,
            requires_four_eyes_approval=False,
            default_retention_months=36,
        ),
    )
    lvl_rest = DataGovernanceService.add_level_to_scheme(
        db=db,
        organization_id=org_id,
        scheme_id=scheme.id,
        actor_id=env["analyst"].id,
        payload=DataClassificationLevelCreate(
            level_code="L4-RESTRICTED-PII",
            name="Restricted PII",
            ordinal_rank=4,
            mapped_sensitivity_level=DataSensitivityLevel.RESTRICTED_PII,
            requires_encryption_at_rest=True,
            requires_encryption_in_transit=True,
            requires_four_eyes_approval=True,
            default_retention_months=60,
        ),
    )
    lvl_phi = DataGovernanceService.add_level_to_scheme(
        db=db,
        organization_id=org_id,
        scheme_id=scheme.id,
        actor_id=env["analyst"].id,
        payload=DataClassificationLevelCreate(
            level_code="L5-SPECIAL-PHI",
            name="Special Category / PHI",
            ordinal_rank=5,
            mapped_sensitivity_level=DataSensitivityLevel.SPECIAL_CATEGORY_SENSITIVE_PHI,
            requires_encryption_at_rest=True,
            requires_encryption_in_transit=True,
            requires_four_eyes_approval=True,
            default_retention_months=84,
        ),
    )
    DataGovernanceService.submit_scheme(db, org_id, scheme.id, env["analyst"].id)
    scheme = DataGovernanceService.approve_scheme(db, org_id, scheme.id, env["manager"].id)
    return {
        "scheme": scheme,
        "L1": lvl_pub,
        "L2": lvl_int,
        "L3": lvl_conf,
        "L4": lvl_rest,
        "L5": lvl_phi,
    }


def test_scheme_lifecycle_and_monotonic_rank_validation(db: Session, dg_domain_env: dict):
    org_id = dg_domain_env["org"].id
    scheme = DataGovernanceService.create_scheme(
        db=db,
        organization_id=org_id,
        actor_id=dg_domain_env["analyst"].id,
        payload=DataClassificationSchemeCreate(
            scheme_code="CS-MONO-01",
            name="Monotonic Test Scheme",
            version=1,
        ),
    )

    # Cannot submit scheme with < 2 levels (SEC-B3-44)
    with pytest.raises(HTTPException) as exc1:
        DataGovernanceService.submit_scheme(db, org_id, scheme.id, dg_domain_env["analyst"].id)
    assert exc1.value.status_code == 422

    # Add rank 2 mapped to RESTRICTED_PII
    DataGovernanceService.add_level_to_scheme(
        db=db,
        organization_id=org_id,
        scheme_id=scheme.id,
        actor_id=dg_domain_env["analyst"].id,
        payload=DataClassificationLevelCreate(
            level_code="LVL-2",
            name="Rank 2 Restricted",
            ordinal_rank=2,
            mapped_sensitivity_level=DataSensitivityLevel.RESTRICTED_PII,
        ),
    )

    # Attempting to add rank 3 with lower sensitivity (PUBLIC) violates monotonic rule (SEC-B3-43)
    with pytest.raises(HTTPException) as exc2:
        DataGovernanceService.add_level_to_scheme(
            db=db,
            organization_id=org_id,
            scheme_id=scheme.id,
            actor_id=dg_domain_env["analyst"].id,
            payload=DataClassificationLevelCreate(
                level_code="LVL-3-BAD",
                name="Contradictory Rank 3",
                ordinal_rank=3,
                mapped_sensitivity_level=DataSensitivityLevel.PUBLIC,
            ),
        )
    assert exc2.value.status_code == 422

    # Add valid rank 1 (INTERNAL)
    DataGovernanceService.add_level_to_scheme(
        db=db,
        organization_id=org_id,
        scheme_id=scheme.id,
        actor_id=dg_domain_env["analyst"].id,
        payload=DataClassificationLevelCreate(
            level_code="LVL-1",
            name="Rank 1 Internal",
            ordinal_rank=1,
            mapped_sensitivity_level=DataSensitivityLevel.INTERNAL,
        ),
    )

    DataGovernanceService.submit_scheme(db, org_id, scheme.id, dg_domain_env["analyst"].id)

    # Creator cannot self-approve scheme (SEC-B3-41)
    with pytest.raises(HTTPException) as exc3:
        DataGovernanceService.approve_scheme(db, org_id, scheme.id, dg_domain_env["analyst"].id)
    assert exc3.value.status_code == 403

    approved = DataGovernanceService.approve_scheme(db, org_id, scheme.id, dg_domain_env["manager"].id)
    assert approved.status == DataClassificationSchemeStatusEnum.ACTIVE.value
    assert approved.approved_by_id == dg_domain_env["manager"].id


def test_classification_upgrade_downgrade_and_four_eyes_lock(db: Session, dg_domain_env: dict):
    org_id = dg_domain_env["org"].id
    tax = _create_active_scheme(db, dg_domain_env)

    asset = DataGovernanceService.create_governed_asset(
        db=db,
        organization_id=org_id,
        actor_id=dg_domain_env["analyst"].id,
        payload=GovernedDataAssetCreate(
            asset_code="DA-CUST-LEDGER",
            name="Customer Ledger Dataset",
            asset_type=DataAssetTypeEnum.DATABASE_TABLE,
            initial_lifecycle_state=DataAssetLifecycleEnum.REGISTERED,
            steward_id=dg_domain_env["steward"].id,
        ),
    )
    assert asset.lifecycle_state == DataAssetLifecycleEnum.REGISTERED.value
    assert asset.classification_status == DataClassificationApprovalStatusEnum.UNCLASSIFIED.value

    # 1. Initial classification to L3-CONFIDENTIAL (upgrade from default INTERNAL, no 4-eyes required)
    rec1 = DataGovernanceService.request_classification(
        db=db,
        organization_id=org_id,
        asset_id=asset.id,
        actor_id=dg_domain_env["analyst"].id,
        payload=DataClassificationRequestCreate(
            scheme_id=tax["scheme"].id,
            level_id=tax["L3"].id,
            justification="Initial confidential business ledger classification",
        ),
    )
    assert rec1.status == DataClassificationRecordStatusEnum.APPROVED.value
    assert rec1.change_type == DataClassificationChangeTypeEnum.INITIAL.value
    db.refresh(asset)
    assert asset.data_sensitivity_level == DataSensitivityLevel.CONFIDENTIAL
    assert asset.lifecycle_state == DataAssetLifecycleEnum.CLASSIFIED.value

    # 2. Upgrade to L4-RESTRICTED-PII -> forces PENDING_APPROVAL (SEC-B3-16)
    rec2 = DataGovernanceService.request_classification(
        db=db,
        organization_id=org_id,
        asset_id=asset.id,
        actor_id=dg_domain_env["analyst"].id,
        payload=DataClassificationRequestCreate(
            scheme_id=tax["scheme"].id,
            level_id=tax["L4"].id,
            justification="Contains customer national IDs and billing PII",
        ),
    )
    assert rec2.status == DataClassificationRecordStatusEnum.PENDING_APPROVAL.value
    assert rec2.change_type == DataClassificationChangeTypeEnum.UPGRADE.value
    db.refresh(asset)
    # Sensitivity remains CONFIDENTIAL until approved!
    assert asset.data_sensitivity_level == DataSensitivityLevel.CONFIDENTIAL
    assert asset.classification_status == DataClassificationApprovalStatusEnum.PENDING_APPROVAL.value

    # Self-approval by requester blocked (SEC-B3-07)
    with pytest.raises(HTTPException) as exc_self:
        DataGovernanceService.approve_classification(db, org_id, rec2.id, dg_domain_env["analyst"].id)
    assert exc_self.value.status_code == 403

    # Manager approves L4-RESTRICTED-PII
    rec2_approved = DataGovernanceService.approve_classification(db, org_id, rec2.id, dg_domain_env["manager"].id)
    assert rec2_approved.status == DataClassificationRecordStatusEnum.APPROVED.value
    db.refresh(rec1)
    db.refresh(asset)
    assert rec1.status == DataClassificationRecordStatusEnum.SUPERSEDED.value
    assert asset.data_sensitivity_level == DataSensitivityLevel.RESTRICTED_PII

    # 3. Downgrade attempt from L4-RESTRICTED-PII -> L1-PUBLIC (Section 6 Downgrade Attack Defense)
    rec3_down = DataGovernanceService.request_classification(
        db=db,
        organization_id=org_id,
        asset_id=asset.id,
        actor_id=dg_domain_env["admin"].id,
        payload=DataClassificationRequestCreate(
            scheme_id=tax["scheme"].id,
            level_id=tax["L1"].id,
            justification="Attempting to downgrade restricted PII to public",
        ),
    )
    assert rec3_down.change_type == DataClassificationChangeTypeEnum.DOWNGRADE.value
    assert rec3_down.status == DataClassificationRecordStatusEnum.PENDING_APPROVAL.value
    db.refresh(asset)
    # Authoritative sensitivity MUST remain RESTRICTED_PII while pending!
    assert asset.data_sensitivity_level == DataSensitivityLevel.RESTRICTED_PII

    # Manager rejects the downgrade
    rec3_rej = DataGovernanceService.reject_classification(
        db=db,
        organization_id=org_id,
        record_id=rec3_down.id,
        reviewer_id=dg_domain_env["manager"].id,
        payload=DataClassificationRejectRequest(
            rejection_reason="Dataset still contains unmasked customer PII; downgrade denied",
        ),
    )
    assert rec3_rej.status == DataClassificationRecordStatusEnum.REJECTED.value
    db.refresh(asset)
    assert asset.data_sensitivity_level == DataSensitivityLevel.RESTRICTED_PII
    assert asset.classification_status == DataClassificationApprovalStatusEnum.APPROVED.value


def test_lineage_dag_cycle_prevention_and_provenance_hash(db: Session, dg_domain_env: dict):
    org_id = dg_domain_env["org"].id
    a = DataGovernanceService.create_governed_asset(
        db, org_id, dg_domain_env["analyst"].id,
        GovernedDataAssetCreate(asset_code="DA-NODE-A", name="Node A"),
    )
    b = DataGovernanceService.create_governed_asset(
        db, org_id, dg_domain_env["analyst"].id,
        GovernedDataAssetCreate(asset_code="DA-NODE-B", name="Node B"),
    )
    c = DataGovernanceService.create_governed_asset(
        db, org_id, dg_domain_env["analyst"].id,
        GovernedDataAssetCreate(asset_code="DA-NODE-C", name="Node C"),
    )
    d = DataGovernanceService.create_governed_asset(
        db, org_id, dg_domain_env["analyst"].id,
        GovernedDataAssetCreate(asset_code="DA-NODE-D", name="Node D"),
    )

    # 1. Self-loop A -> A rejected (SEC-B3-10)
    with pytest.raises(HTTPException) as exc_loop:
        DataGovernanceService.create_or_version_lineage_edge(
            db, org_id, dg_domain_env["analyst"].id,
            DataLineageEdgeCreate(
                edge_code="LIN-SELF",
                source_data_asset_id=a.id,
                target_data_asset_id=a.id,
            ),
        )
    assert exc_loop.value.status_code == 422

    # 2. Create valid chain A -> B -> C -> D
    e_ab = DataGovernanceService.create_or_version_lineage_edge(
        db, org_id, dg_domain_env["analyst"].id,
        DataLineageEdgeCreate(edge_code="LIN-AB", source_data_asset_id=a.id, target_data_asset_id=b.id),
    )
    assert len(e_ab.provenance_hash) == 64

    DataGovernanceService.create_or_version_lineage_edge(
        db, org_id, dg_domain_env["analyst"].id,
        DataLineageEdgeCreate(edge_code="LIN-BC", source_data_asset_id=b.id, target_data_asset_id=c.id),
    )
    DataGovernanceService.create_or_version_lineage_edge(
        db, org_id, dg_domain_env["analyst"].id,
        DataLineageEdgeCreate(edge_code="LIN-CD", source_data_asset_id=c.id, target_data_asset_id=d.id),
    )

    # 3. 2-node cycle B -> A rejected
    with pytest.raises(HTTPException) as exc_2cycle:
        DataGovernanceService.create_or_version_lineage_edge(
            db, org_id, dg_domain_env["analyst"].id,
            DataLineageEdgeCreate(edge_code="LIN-BA", source_data_asset_id=b.id, target_data_asset_id=a.id),
        )
    assert exc_2cycle.value.status_code == 422

    # 4. 3-node cycle C -> A rejected (SEC-B3-11)
    with pytest.raises(HTTPException) as exc_3cycle:
        DataGovernanceService.create_or_version_lineage_edge(
            db, org_id, dg_domain_env["analyst"].id,
            DataLineageEdgeCreate(edge_code="LIN-CA", source_data_asset_id=c.id, target_data_asset_id=a.id),
        )
    assert exc_3cycle.value.status_code == 422

    # 5. 4-node multi-hop cycle D -> A rejected (SEC-B3-12)
    with pytest.raises(HTTPException) as exc_4cycle:
        DataGovernanceService.create_or_version_lineage_edge(
            db, org_id, dg_domain_env["analyst"].id,
            DataLineageEdgeCreate(edge_code="LIN-DA", source_data_asset_id=d.id, target_data_asset_id=a.id),
        )
    assert exc_4cycle.value.status_code == 422


def test_lineage_sensitivity_flow_gating(db: Session, dg_domain_env: dict):
    org_id = dg_domain_env["org"].id
    tax = _create_active_scheme(db, dg_domain_env)

    src_restricted = DataGovernanceService.create_governed_asset(
        db, org_id, dg_domain_env["analyst"].id,
        GovernedDataAssetCreate(
            asset_code="DA-SRC-REST",
            name="Restricted Source",
            data_sensitivity_level=DataSensitivityLevel.RESTRICTED_PII,
        ),
    )
    dst_public = DataGovernanceService.create_governed_asset(
        db, org_id, dg_domain_env["analyst"].id,
        GovernedDataAssetCreate(
            asset_code="DA-DST-PUB",
            name="Public Target",
            data_sensitivity_level=DataSensitivityLevel.PUBLIC,
        ),
    )
    dst_internal = DataGovernanceService.create_governed_asset(
        db, org_id, dg_domain_env["analyst"].id,
        GovernedDataAssetCreate(
            asset_code="DA-DST-INT",
            name="Internal Analytics Target",
            data_sensitivity_level=DataSensitivityLevel.INTERNAL,
        ),
    )

    # 1. Unmasked RESTRICTED_PII -> PUBLIC is strictly prohibited (SEC-B3-40)
    with pytest.raises(HTTPException) as exc_pub:
        DataGovernanceService.create_or_version_lineage_edge(
            db, org_id, dg_domain_env["analyst"].id,
            DataLineageEdgeCreate(
                edge_code="LIN-REST-PUB-RAW",
                source_data_asset_id=src_restricted.id,
                target_data_asset_id=dst_public.id,
                is_masked_or_anonymized=False,
                transformation_summary="Raw export to public portal",
            ),
        )
    assert exc_pub.value.status_code == 422

    # 2. RESTRICTED_PII -> INTERNAL without transformation_summary is rejected (422)
    with pytest.raises(HTTPException) as exc_no_tx:
        DataGovernanceService.create_or_version_lineage_edge(
            db, org_id, dg_domain_env["analyst"].id,
            DataLineageEdgeCreate(
                edge_code="LIN-REST-INT-NOTX",
                source_data_asset_id=src_restricted.id,
                target_data_asset_id=dst_internal.id,
                is_masked_or_anonymized=True,
            ),
        )
    assert exc_no_tx.value.status_code == 422

    # 3. RESTRICTED_PII -> INTERNAL with documented transformation forces PENDING_APPROVAL
    edge_pending = DataGovernanceService.create_or_version_lineage_edge(
        db, org_id, dg_domain_env["analyst"].id,
        DataLineageEdgeCreate(
            edge_code="LIN-REST-INT-MASKED",
            source_data_asset_id=src_restricted.id,
            target_data_asset_id=dst_internal.id,
            is_masked_or_anonymized=True,
            transformation_summary="SHA-256 salted hashing of all PII fields before analytics load",
        ),
    )
    assert edge_pending.status == DataLineageStatusEnum.PENDING_APPROVAL.value

    # Creator cannot self-approve lineage edge (SEC-B3-42)
    with pytest.raises(HTTPException) as exc_self:
        DataGovernanceService.approve_lineage_edge(db, org_id, edge_pending.id, dg_domain_env["analyst"].id)
    assert exc_self.value.status_code == 403

    edge_approved = DataGovernanceService.approve_lineage_edge(
        db, org_id, edge_pending.id, dg_domain_env["manager"].id
    )
    assert edge_approved.status == DataLineageStatusEnum.ACTIVE.value


def test_cloud_alignment_and_governed_retirement_lifecycle(db: Session, dg_domain_env: dict):
    org_id = dg_domain_env["org"].id
    tax = _create_active_scheme(db, dg_domain_env)

    # 1. DISCOVERED asset cannot skip directly to ACTIVE (SEC-B3-37)
    disc_asset = DataGovernanceService.create_governed_asset(
        db, org_id, dg_domain_env["analyst"].id,
        GovernedDataAssetCreate(
            asset_code="DA-CLOUD-DISC-01",
            name="Discovered S3 Dataset",
            initial_lifecycle_state=DataAssetLifecycleEnum.DISCOVERED,
            cloud_asset_id=dg_domain_env["cloud_drifted"].id,
        ),
    )
    with pytest.raises(HTTPException) as exc_skip:
        DataGovernanceService.activate_asset(db, org_id, disc_asset.id, dg_domain_env["analyst"].id)
    assert exc_skip.value.status_code == 422

    # 2. Register -> Classify -> Activate
    DataGovernanceService.register_discovered_asset(
        db, org_id, disc_asset.id, dg_domain_env["analyst"].id,
        DataAssetRegisterRequest(steward_id=dg_domain_env["steward"].id),
    )
    rec = DataGovernanceService.request_classification(
        db, org_id, disc_asset.id, dg_domain_env["analyst"].id,
        DataClassificationRequestCreate(
            scheme_id=tax["scheme"].id,
            level_id=tax["L4"].id,
            justification="Contains customer PII discovered in S3",
        ),
    )
    DataGovernanceService.approve_classification(db, org_id, rec.id, dg_domain_env["manager"].id)
    DataGovernanceService.activate_asset(db, org_id, disc_asset.id, dg_domain_env["analyst"].id)

    # 3. Check Cloud Posture Alignment (linked to unencrypted, internet-facing, non-compliant bucket)
    dossier = DataGovernanceService.get_asset_governance_dossier(db, org_id, disc_asset.id)
    assert dossier.cloud_alignment.cloud_posture_aligned is False
    assert "CLOUD_ENCRYPTION_MISMATCH" in dossier.cloud_alignment.mismatch_flags
    assert "CLOUD_PUBLIC_EXPOSURE_MISMATCH" in dossier.cloud_alignment.mismatch_flags
    assert "CLOUD_POSTURE_NON_COMPLIANT" in dossier.cloud_alignment.mismatch_flags
    # Classification was NOT overwritten by cloud telemetry
    assert dossier.asset.data_sensitivity_level == DataSensitivityLevel.RESTRICTED_PII

    # 4. Link Control, Evidence, and Processing Activity
    DataGovernanceService.link_control(
        db, org_id, disc_asset.id, dg_domain_env["analyst"].id,
        DataAssetControlLinkCreate(
            organization_control_id=dg_domain_env["control"].id,
            control_objective=DataControlObjectiveEnum.ENCRYPTION_AT_REST,
        ),
    )
    DataGovernanceService.link_processing_activity(
        db, org_id, disc_asset.id, dg_domain_env["analyst"].id,
        DataAssetProcessingLinkCreate(
            processing_activity_id=dg_domain_env["ropa"].id,
            usage_role=DataProcessingUsageRoleEnum.PRIMARY_SOURCE,
        ),
    )
    DataGovernanceService.link_evidence(
        db, org_id, disc_asset.id, dg_domain_env["analyst"].id,
        DataAssetEvidenceLinkCreate(
            evidence_item_id=dg_domain_env["evidence"].id,
            evidence_purpose=DataEvidencePurposeEnum.ENCRYPTION_ATTESTATION,
        ),
    )
    dossier_with_reg = DataGovernanceService.get_asset_governance_dossier(db, org_id, disc_asset.id)
    assert len(dossier_with_reg.regulatory_obligations) == 1
    assert dossier_with_reg.regulatory_obligations[0].obligation_code == "GDPR-ART-32"

    # 5. Retirement without evidence on RESTRICTED_PII asset fails (SEC-B3-39)
    with pytest.raises(HTTPException) as exc_no_ev:
        DataGovernanceService.finalize_retirement(
            db, org_id, disc_asset.id, dg_domain_env["manager"].id,
            DataAssetRetireRequest(
                disposal_method=DataDisposalMethodEnum.CRYPTOGRAPHIC_ERASURE,
                retirement_notes="Attempting retirement without evidence",
                retirement_evidence_id=None,
            ),
        )
    assert exc_no_ev.value.status_code == 422

    # Retirement with REJECTED evidence fails (SEC-B3-25)
    with pytest.raises(HTTPException) as exc_rej_ev:
        DataGovernanceService.finalize_retirement(
            db, org_id, disc_asset.id, dg_domain_env["manager"].id,
            DataAssetRetireRequest(
                disposal_method=DataDisposalMethodEnum.CRYPTOGRAPHIC_ERASURE,
                retirement_notes="Attempting retirement with rejected evidence",
                retirement_evidence_id=dg_domain_env["rejected_evidence"].id,
            ),
        )
    assert exc_rej_ev.value.status_code == 422

    # Valid Four-Eyes retirement request + approval
    DataGovernanceService.request_retirement(
        db, org_id, disc_asset.id, dg_domain_env["analyst"].id,
        DataAssetRetireRequest(
            disposal_method=DataDisposalMethodEnum.CRYPTOGRAPHIC_ERASURE,
            retirement_notes="KMS key destroyed and verified",
            retirement_evidence_id=dg_domain_env["evidence"].id,
        ),
    )
    # Self-approval of retirement blocked
    with pytest.raises(HTTPException) as exc_ret_self:
        DataGovernanceService.finalize_retirement(
            db, org_id, disc_asset.id, dg_domain_env["analyst"].id,
            DataAssetRetireRequest(
                disposal_method=DataDisposalMethodEnum.CRYPTOGRAPHIC_ERASURE,
                retirement_notes="Self-approving retirement",
                retirement_evidence_id=dg_domain_env["evidence"].id,
            ),
        )
    assert exc_ret_self.value.status_code == 403

    retired = DataGovernanceService.finalize_retirement(
        db, org_id, disc_asset.id, dg_domain_env["manager"].id,
        DataAssetRetireRequest(
            disposal_method=DataDisposalMethodEnum.CRYPTOGRAPHIC_ERASURE,
            retirement_notes="Approved retirement with erasure certificate",
            retirement_evidence_id=dg_domain_env["evidence"].id,
        ),
    )
    assert retired.lifecycle_state == DataAssetLifecycleEnum.RETIRED.value

    # Audit logs recorded (SEC-B3-31)
    logs_count = db.query(AuditLog).filter(AuditLog.organization_id == org_id).count()
    assert logs_count >= 10


def test_lineage_edge_version_superseding_and_revocation(db: Session, dg_domain_env: dict):
    org_id = dg_domain_env["org"].id
    src = DataGovernanceService.create_governed_asset(
        db, org_id, dg_domain_env["analyst"].id,
        GovernedDataAssetCreate(asset_code="DA-VER-SRC", name="Versioned Source"),
    )
    dst = DataGovernanceService.create_governed_asset(
        db, org_id, dg_domain_env["analyst"].id,
        GovernedDataAssetCreate(asset_code="DA-VER-DST", name="Versioned Target"),
    )

    v1 = DataGovernanceService.create_or_version_lineage_edge(
        db, org_id, dg_domain_env["analyst"].id,
        DataLineageEdgeCreate(
            edge_code="LIN-VER-01",
            source_data_asset_id=src.id,
            target_data_asset_id=dst.id,
            transformation_summary="v1 initial ETL mapping",
        ),
    )
    assert v1.version == 1
    assert v1.status == DataLineageStatusEnum.ACTIVE.value

    # Creating a new edge for the same pair supersedes v1 and creates v2
    v2 = DataGovernanceService.create_or_version_lineage_edge(
        db, org_id, dg_domain_env["analyst"].id,
        DataLineageEdgeCreate(
            edge_code="LIN-VER-01",
            source_data_asset_id=src.id,
            target_data_asset_id=dst.id,
            transformation_summary="v2 updated ETL mapping with field tokenization",
            is_masked_or_anonymized=True,
        ),
    )
    db.refresh(v1)
    assert v1.status == DataLineageStatusEnum.SUPERSEDED.value
    assert v1.effective_to is not None
    assert v2.version == 2
    assert v2.status == DataLineageStatusEnum.ACTIVE.value
    assert v1.provenance_hash != v2.provenance_hash

    # Revoke v2
    revoked = DataGovernanceService.revoke_lineage_edge(
        db, org_id, v2.id, dg_domain_env["manager"].id,
        DataLineageEdgeRevokeRequest(revocation_reason="Decommissioned downstream pipeline"),
    )
    assert revoked.status == DataLineageStatusEnum.REVOKED.value
    assert revoked.revoked_by_id == dg_domain_env["manager"].id


def test_ownership_transfer_and_inactive_owner_governance(db: Session, dg_domain_env: dict):
    org_id = dg_domain_env["org"].id
    asset = DataGovernanceService.create_governed_asset(
        db, org_id, dg_domain_env["analyst"].id,
        GovernedDataAssetCreate(
            asset_code="DA-OWN-01",
            name="Ownership Governed Asset",
            data_sensitivity_level=DataSensitivityLevel.RESTRICTED_PII,
        ),
    )

    # Assigning inactive user as owner fails (422)
    with pytest.raises(HTTPException) as exc_inact:
        DataGovernanceService.update_ownership(
            db, org_id, asset.id, dg_domain_env["analyst"].id,
            DataOwnershipUpdateRequest(
                owner_id=dg_domain_env["inactive_user"].id,
                justification="Assigning to inactive employee",
            ),
        )
    assert exc_inact.value.status_code == 422

    # Restricted PII asset forces Four-Eyes ownership transfer approval
    pending = DataGovernanceService.update_ownership(
        db, org_id, asset.id, dg_domain_env["analyst"].id,
        DataOwnershipUpdateRequest(
            owner_id=dg_domain_env["manager"].id,
            steward_id=dg_domain_env["steward"].id,
            justification="Transferring ownership to Governance Manager",
        ),
    )
    assert pending.owner_transfer_status == DataOwnerTransferStatusEnum.PENDING_TRANSFER.value
    assert pending.pending_owner_id == dg_domain_env["manager"].id

    # Requester cannot self-approve ownership transfer
    with pytest.raises(HTTPException) as exc_self:
        DataGovernanceService.approve_ownership_transfer(db, org_id, asset.id, dg_domain_env["analyst"].id)
    assert exc_self.value.status_code == 403

    approved = DataGovernanceService.approve_ownership_transfer(db, org_id, asset.id, dg_domain_env["admin"].id)
    assert approved.owner_id == dg_domain_env["manager"].id
    assert approved.owner_transfer_status == DataOwnerTransferStatusEnum.APPROVED.value


def test_asset_deprecation_and_restoration_from_retired(db: Session, dg_domain_env: dict):
    org_id = dg_domain_env["org"].id
    tax = _create_active_scheme(db, dg_domain_env)
    asset = DataGovernanceService.create_governed_asset(
        db, org_id, dg_domain_env["analyst"].id,
        GovernedDataAssetCreate(asset_code="DA-RESTORE-01", name="Restorable Dataset"),
    )
    DataGovernanceService.request_classification(
        db, org_id, asset.id, dg_domain_env["analyst"].id,
        DataClassificationRequestCreate(
            scheme_id=tax["scheme"].id,
            level_id=tax["L2"].id,
            justification="Internal dataset classification",
        ),
    )
    DataGovernanceService.activate_asset(db, org_id, asset.id, dg_domain_env["analyst"].id)

    deprecated = DataGovernanceService.deprecate_asset(
        db, org_id, asset.id, dg_domain_env["analyst"].id,
        DataAssetDeprecateRequest(deprecation_notes="Replaced by v2 warehouse table"),
    )
    assert deprecated.lifecycle_state == DataAssetLifecycleEnum.DEPRECATED.value

    retired = DataGovernanceService.finalize_retirement(
        db, org_id, asset.id, dg_domain_env["manager"].id,
        DataAssetRetireRequest(
            disposal_method=DataDisposalMethodEnum.SECURE_OVERWRITE,
            retirement_notes="Securely overwritten and archived",
        ),
    )
    assert retired.lifecycle_state == DataAssetLifecycleEnum.RETIRED.value

    # Retirer (manager) cannot self-restore
    with pytest.raises(HTTPException) as exc_self:
        DataGovernanceService.restore_retired_asset(
            db, org_id, asset.id, dg_domain_env["manager"].id,
            DataAssetRestoreRequest(restoration_justification="Self restoration attempt"),
        )
    assert exc_self.value.status_code == 403

    # Admin restores retired classified asset back to ACTIVE
    restored = DataGovernanceService.restore_retired_asset(
        db, org_id, asset.id, dg_domain_env["admin"].id,
        DataAssetRestoreRequest(restoration_justification="Legal hold requires restoring archive"),
    )
    assert restored.lifecycle_state == DataAssetLifecycleEnum.ACTIVE.value


def test_scheme_auto_superseding_and_default_switch(db: Session, dg_domain_env: dict):
    org_id = dg_domain_env["org"].id
    s1 = DataGovernanceService.create_scheme(
        db, org_id, dg_domain_env["analyst"].id,
        DataClassificationSchemeCreate(scheme_code="CS-AUTO-SUP", name="Scheme v1", version=1, is_default=True),
    )
    for rank, code, sens in [(1, "L1", DataSensitivityLevel.PUBLIC), (2, "L2", DataSensitivityLevel.INTERNAL)]:
        DataGovernanceService.add_level_to_scheme(
            db, org_id, s1.id, dg_domain_env["analyst"].id,
            DataClassificationLevelCreate(
                level_code=code, name=code, ordinal_rank=rank, mapped_sensitivity_level=sens
            ),
        )
    DataGovernanceService.submit_scheme(db, org_id, s1.id, dg_domain_env["analyst"].id)
    s1 = DataGovernanceService.approve_scheme(db, org_id, s1.id, dg_domain_env["manager"].id)
    assert s1.status == DataClassificationSchemeStatusEnum.ACTIVE.value

    s2 = DataGovernanceService.create_scheme(
        db, org_id, dg_domain_env["analyst"].id,
        DataClassificationSchemeCreate(scheme_code="CS-AUTO-SUP", name="Scheme v2", version=2, is_default=True),
    )
    for rank, code, sens in [(1, "L1", DataSensitivityLevel.PUBLIC), (2, "L2", DataSensitivityLevel.CONFIDENTIAL)]:
        DataGovernanceService.add_level_to_scheme(
            db, org_id, s2.id, dg_domain_env["analyst"].id,
            DataClassificationLevelCreate(
                level_code=code, name=code, ordinal_rank=rank, mapped_sensitivity_level=sens
            ),
        )
    DataGovernanceService.submit_scheme(db, org_id, s2.id, dg_domain_env["analyst"].id)
    s2 = DataGovernanceService.approve_scheme(db, org_id, s2.id, dg_domain_env["manager"].id)
    db.refresh(s1)
    assert s1.status == DataClassificationSchemeStatusEnum.ARCHIVED.value
    assert s1.is_default is False
    assert s2.status == DataClassificationSchemeStatusEnum.ACTIVE.value
    assert s2.is_default is True


def test_data_governance_posture_summary_scoring(db: Session, dg_domain_env: dict):
    org_id = dg_domain_env["org"].id
    tax = _create_active_scheme(db, dg_domain_env)
    a1 = DataGovernanceService.create_governed_asset(
        db, org_id, dg_domain_env["analyst"].id,
        GovernedDataAssetCreate(
            asset_code="DA-SUM-01",
            name="Summary Asset 1",
            steward_id=dg_domain_env["steward"].id,
            cloud_asset_id=dg_domain_env["cloud_compliant"].id,
        ),
    )
    DataGovernanceService.request_classification(
        db, org_id, a1.id, dg_domain_env["analyst"].id,
        DataClassificationRequestCreate(
            scheme_id=tax["scheme"].id,
            level_id=tax["L3"].id,
            justification="Confidential classification",
        ),
    )
    DataGovernanceService.activate_asset(db, org_id, a1.id, dg_domain_env["analyst"].id)
    summary = DataGovernanceService.get_governance_summary(db, org_id)
    assert summary.total_assets >= 1
    assert summary.classified_assets_count >= 1
    assert 0.0 <= summary.governance_health_score <= 100.0


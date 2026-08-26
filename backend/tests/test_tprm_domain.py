from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.permissions import Permission, RoleEnum, has_permission
from app.models.evidence import EvidenceItem, EvidenceStatusEnum, EvidenceTypeEnum
from app.models.organization import Organization
from app.models.tprm import (
    BusinessCriticalityEnum,
    DataClassificationEnum,
    EngagementStatusEnum,
    HostingModelEnum,
    NetworkConnectivityEnum,
    PiiFinancialAccessEnum,
    Vendor,
    VendorAssessment,
    VendorAssessmentItem,
    VendorAssessmentStatusEnum,
    VendorAssessmentTypeEnum,
    VendorDocumentTypeEnum,
    VendorEngagement,
    VendorEvidenceLink,
    VendorResponseStatusEnum,
    VendorRiskBandEnum,
    VendorStatusEnum,
    VendorTierEnum,
)
from app.models.user import User
from app.services.tprm_service import TPRMService


class TestTPRMDomain:
    """Domain & Lifecycle tests for Phase 9 TPRM."""

    def test_vendor_lifecycle_legal_transitions(self):
        """Legal vendor transitions follow strict state machine."""
        TPRMService.validate_vendor_transition(VendorStatusEnum.PROSPECT, VendorStatusEnum.DUE_DILIGENCE)
        TPRMService.validate_vendor_transition(VendorStatusEnum.DUE_DILIGENCE, VendorStatusEnum.APPROVED)
        TPRMService.validate_vendor_transition(VendorStatusEnum.APPROVED, VendorStatusEnum.ACTIVE)
        TPRMService.validate_vendor_transition(VendorStatusEnum.ACTIVE, VendorStatusEnum.UNDER_REVIEW)
        TPRMService.validate_vendor_transition(VendorStatusEnum.UNDER_REVIEW, VendorStatusEnum.ACTIVE)
        TPRMService.validate_vendor_transition(VendorStatusEnum.ACTIVE, VendorStatusEnum.OFFBOARDED)
        TPRMService.validate_vendor_transition(VendorStatusEnum.OFFBOARDED, VendorStatusEnum.DUE_DILIGENCE)
        TPRMService.validate_vendor_transition(VendorStatusEnum.ACTIVE, VendorStatusEnum.TERMINATED)

    def test_vendor_lifecycle_illegal_transitions_blocked(self):
        """Illegal transitions and transitions out of TERMINATED raise ValueError."""
        with pytest.raises(ValueError, match="Invalid vendor lifecycle transition"):
            TPRMService.validate_vendor_transition(VendorStatusEnum.PROSPECT, VendorStatusEnum.ACTIVE)

        with pytest.raises(ValueError, match="Invalid vendor lifecycle transition"):
            TPRMService.validate_vendor_transition(VendorStatusEnum.TERMINATED, VendorStatusEnum.ACTIVE)

    def test_assessment_lifecycle_legal_transitions(self):
        """Assessment transitions: DRAFT -> SUBMITTED -> IN_REVIEW -> APPROVED -> SUPERSEDED."""
        TPRMService.validate_assessment_transition(VendorAssessmentStatusEnum.DRAFT, VendorAssessmentStatusEnum.SUBMITTED)
        TPRMService.validate_assessment_transition(VendorAssessmentStatusEnum.SUBMITTED, VendorAssessmentStatusEnum.IN_REVIEW)
        TPRMService.validate_assessment_transition(VendorAssessmentStatusEnum.IN_REVIEW, VendorAssessmentStatusEnum.APPROVED)
        TPRMService.validate_assessment_transition(VendorAssessmentStatusEnum.APPROVED, VendorAssessmentStatusEnum.SUPERSEDED)

    def test_assessment_lifecycle_illegal_transitions_blocked(self):
        """Cannot jump from DRAFT directly to APPROVED or mutate SUPERSEDED."""
        with pytest.raises(ValueError, match="Invalid assessment transition"):
            TPRMService.validate_assessment_transition(VendorAssessmentStatusEnum.DRAFT, VendorAssessmentStatusEnum.APPROVED)

        with pytest.raises(ValueError, match="Invalid assessment transition"):
            TPRMService.validate_assessment_transition(VendorAssessmentStatusEnum.SUPERSEDED, VendorAssessmentStatusEnum.DRAFT)

    def test_assessment_approval_separation_of_duties(self, db: Session, org_apex, admin_user, analyst_user):
        """Assessor cannot approve their own assessment."""
        vendor = Vendor(
            organization_id=org_apex.id,
            vendor_code="VND-SOD-01",
            legal_name="Cloud Corp",
            vendor_status=VendorStatusEnum.DUE_DILIGENCE,
        )
        db.add(vendor)
        db.commit()
        db.refresh(vendor)

        assessment = VendorAssessment(
            organization_id=org_apex.id,
            vendor_id=vendor.id,
            assessment_code="ASM-SOD-01",
            title="Initial Due Diligence",
            status=VendorAssessmentStatusEnum.IN_REVIEW,
            assessor_id=analyst_user.id,
        )
        db.add(assessment)
        db.commit()
        db.refresh(assessment)

        # Same assessor attempts to approve -> Must fail
        with pytest.raises(ValueError, match="Separation of duties violation"):
            TPRMService.approve_assessment(
                db=db,
                assessment=assessment,
                reviewer_id=analyst_user.id,
            )

        # Separate reviewer approves -> Succeeds
        approved = TPRMService.approve_assessment(
            db=db,
            assessment=assessment,
            reviewer_id=admin_user.id,
            review_notes="Approved by GRC Manager",
        )
        assert approved.status == VendorAssessmentStatusEnum.APPROVED
        assert approved.reviewer_id == admin_user.id

    def test_new_approved_assessment_supersedes_previous(self, db: Session, org_apex, admin_user, analyst_user):
        """When a new assessment is approved, previous approved assessments become SUPERSEDED."""
        vendor = Vendor(
            organization_id=org_apex.id,
            vendor_code="VND-SUP-01",
            legal_name="SaaS Solutions",
            vendor_status=VendorStatusEnum.ACTIVE,
        )
        db.add(vendor)
        db.commit()
        db.refresh(vendor)

        # Assessment 1: Approved
        asm1 = VendorAssessment(
            organization_id=org_apex.id,
            vendor_id=vendor.id,
            assessment_code="ASM-SUP-01",
            title="2025 Due Diligence",
            status=VendorAssessmentStatusEnum.IN_REVIEW,
            assessor_id=analyst_user.id,
        )
        db.add(asm1)
        db.commit()
        db.refresh(asm1)
        TPRMService.approve_assessment(db, asm1, admin_user.id)
        assert asm1.status == VendorAssessmentStatusEnum.APPROVED

        # Assessment 2: Approved in 2026
        asm2 = VendorAssessment(
            organization_id=org_apex.id,
            vendor_id=vendor.id,
            assessment_code="ASM-SUP-02",
            title="2026 Annual Reassessment",
            status=VendorAssessmentStatusEnum.IN_REVIEW,
            assessor_id=analyst_user.id,
        )
        db.add(asm2)
        db.commit()
        db.refresh(asm2)
        TPRMService.approve_assessment(db, asm2, admin_user.id)

        db.refresh(asm1)
        db.refresh(asm2)
        assert asm1.status == VendorAssessmentStatusEnum.SUPERSEDED
        assert asm2.status == VendorAssessmentStatusEnum.APPROVED

    def test_duplicate_vendor_code_rejected(self, db: Session, org_apex):
        """uq_vendor_org_code prevents duplicate vendor codes within the same organization."""
        v1 = Vendor(
            organization_id=org_apex.id,
            vendor_code="VND-DUP-01",
            legal_name="Vendor A",
        )
        db.add(v1)
        db.commit()

        v2 = Vendor(
            organization_id=org_apex.id,
            vendor_code="VND-DUP-01",  # Duplicate
            legal_name="Vendor B",
        )
        db.add(v2)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    def test_duplicate_evidence_link_rejected(self, db: Session, org_apex, analyst_user, seeded_framework):
        """uq_vendor_evidence_link prevents linking the same EvidenceItem multiple times to a vendor."""
        vendor = Vendor(
            organization_id=org_apex.id,
            vendor_code="VND-EVD-01",
            legal_name="Vendor Evd",
        )
        db.add(vendor)
        db.commit()
        db.refresh(vendor)

        subcat = seeded_framework.functions[0].categories[0].subcategories[0]
        from app.models.control import OrganizationControl, ImplementationStatusEnum
        ctrl = OrganizationControl(
            organization_id=org_apex.id,
            subcategory_id=subcat.id,
            status=ImplementationStatusEnum.IMPLEMENTED,
        )
        db.add(ctrl)
        db.commit()
        db.refresh(ctrl)

        evidence = EvidenceItem(
            organization_id=org_apex.id,
            organization_control_id=ctrl.id,
            title="SOC 2 Report",
            original_filename="soc2.pdf",
            stored_filename="soc2_abc123.pdf",
            file_extension="pdf",
            content_type="application/pdf",
            file_size=1024,
            sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            storage_key="org_1/soc2.pdf",
            uploaded_by_id=analyst_user.id,
            status=EvidenceStatusEnum.ACCEPTED,
        )
        db.add(evidence)
        db.commit()
        db.refresh(evidence)

        now = datetime.now(timezone.utc)
        link1 = VendorEvidenceLink(
            organization_id=org_apex.id,
            vendor_id=vendor.id,
            evidence_id=evidence.id,
            document_type=VendorDocumentTypeEnum.SOC2_TYPE2,
            effective_date=now,
            expiration_date=now + timedelta(days=365),
        )
        db.add(link1)
        db.commit()

        link2 = VendorEvidenceLink(
            organization_id=org_apex.id,
            vendor_id=vendor.id,
            evidence_id=evidence.id,  # Duplicate
            document_type=VendorDocumentTypeEnum.SOC2_TYPE2,
            effective_date=now,
            expiration_date=now + timedelta(days=365),
        )
        db.add(link2)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    def test_tprm_rbac_permission_matrix(self):
        """Verify role permissions for all 5 Phase 9 TPRM permissions across 6 roles."""
        # ADMIN has all
        assert has_permission(RoleEnum.ADMIN, Permission.VENDOR_READ)
        assert has_permission(RoleEnum.ADMIN, Permission.VENDOR_MANAGE)
        assert has_permission(RoleEnum.ADMIN, Permission.VENDOR_ASSESS)
        assert has_permission(RoleEnum.ADMIN, Permission.VENDOR_APPROVE)
        assert has_permission(RoleEnum.ADMIN, Permission.VENDOR_RISK_MANAGE)

        # GRC_ANALYST: read, manage, assess, risk_manage (NO approve)
        assert has_permission(RoleEnum.GRC_ANALYST, Permission.VENDOR_READ)
        assert has_permission(RoleEnum.GRC_ANALYST, Permission.VENDOR_MANAGE)
        assert has_permission(RoleEnum.GRC_ANALYST, Permission.VENDOR_ASSESS)
        assert not has_permission(RoleEnum.GRC_ANALYST, Permission.VENDOR_APPROVE)
        assert has_permission(RoleEnum.GRC_ANALYST, Permission.VENDOR_RISK_MANAGE)

        # SECURITY_ANALYST: read, manage, assess, risk_manage (NO approve)
        assert has_permission(RoleEnum.SECURITY_ANALYST, Permission.VENDOR_READ)
        assert has_permission(RoleEnum.SECURITY_ANALYST, Permission.VENDOR_MANAGE)
        assert has_permission(RoleEnum.SECURITY_ANALYST, Permission.VENDOR_ASSESS)
        assert not has_permission(RoleEnum.SECURITY_ANALYST, Permission.VENDOR_APPROVE)

        # MANAGER: read, manage, approve, risk_manage (NO assess)
        assert has_permission(RoleEnum.MANAGER, Permission.VENDOR_READ)
        assert has_permission(RoleEnum.MANAGER, Permission.VENDOR_MANAGE)
        assert not has_permission(RoleEnum.MANAGER, Permission.VENDOR_ASSESS)
        assert has_permission(RoleEnum.MANAGER, Permission.VENDOR_APPROVE)

        # AUDITOR: read only
        assert has_permission(RoleEnum.AUDITOR, Permission.VENDOR_READ)
        assert not has_permission(RoleEnum.AUDITOR, Permission.VENDOR_MANAGE)
        assert not has_permission(RoleEnum.AUDITOR, Permission.VENDOR_ASSESS)
        assert not has_permission(RoleEnum.AUDITOR, Permission.VENDOR_APPROVE)

        # VIEWER: read only
        assert has_permission(RoleEnum.VIEWER, Permission.VENDOR_READ)
        assert not has_permission(RoleEnum.VIEWER, Permission.VENDOR_MANAGE)
        assert not has_permission(RoleEnum.VIEWER, Permission.VENDOR_APPROVE)

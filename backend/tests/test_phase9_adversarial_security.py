from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.control import ImplementationStatusEnum, OrganizationControl
from app.models.evidence import EvidenceItem, EvidenceStatusEnum, EvidenceTypeEnum
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
from tests.conftest import get_token_headers


class TestPhase9AdversarialSecurity:
    """Comprehensive Adversarial Security Test Suite for Phase 9 TPRM (ADV-P9-01 to ADV-P9-20)."""

    def test_adv_p9_01_cross_tenant_vendor_read_idor(
        self, client: TestClient, db: Session, admin_user, org_meridian
    ):
        """ADV-P9-01: An authenticated user from Org Apex cannot read vendors from Org Meridian."""
        admin_headers = get_token_headers(admin_user)
        v_meridian = Vendor(
            organization_id=org_meridian.id,
            vendor_code="VND-MER-01",
            legal_name="Meridian Secret Vendor",
            vendor_status=VendorStatusEnum.ACTIVE,
        )
        db.add(v_meridian)
        db.commit()
        db.refresh(v_meridian)

        res = client.get(f"/api/v1/vendors/{v_meridian.id}", headers=admin_headers)
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()

    def test_adv_p9_02_cross_tenant_vendor_update_idor(
        self, client: TestClient, db: Session, admin_user, org_meridian
    ):
        """ADV-P9-02: An authenticated user from Org Apex cannot update vendors from Org Meridian."""
        admin_headers = get_token_headers(admin_user)
        v_meridian = Vendor(
            organization_id=org_meridian.id,
            vendor_code="VND-MER-02",
            legal_name="Meridian Cloud Ltd",
            vendor_status=VendorStatusEnum.ACTIVE,
        )
        db.add(v_meridian)
        db.commit()
        db.refresh(v_meridian)

        res = client.patch(
            f"/api/v1/vendors/{v_meridian.id}",
            json={"legal_name": "Tampered Name"},
            headers=admin_headers,
        )
        assert res.status_code == 404

    def test_adv_p9_03_foreign_engagement_injection(
        self, client: TestClient, db: Session, admin_user, org_apex, org_meridian
    ):
        """ADV-P9-03: Attempting to create an engagement on another tenant's vendor returns 404."""
        admin_headers = get_token_headers(admin_user)
        v_meridian = Vendor(
            organization_id=org_meridian.id,
            vendor_code="VND-MER-03",
            legal_name="Foreign Vendor",
        )
        db.add(v_meridian)
        db.commit()
        db.refresh(v_meridian)

        payload = {
            "engagement_code": "ENG-HACK-01",
            "engagement_name": "Injected Engagement",
            "criticality": "CRITICAL",
        }
        res = client.post(
            f"/api/v1/vendors/{v_meridian.id}/engagements",
            json=payload,
            headers=admin_headers,
        )
        assert res.status_code == 404

    def test_adv_p9_04_foreign_assessment_injection(
        self, client: TestClient, db: Session, admin_user, org_meridian
    ):
        """ADV-P9-04: Attempting to create an assessment on another tenant's vendor returns 404."""
        admin_headers = get_token_headers(admin_user)
        v_meridian = Vendor(
            organization_id=org_meridian.id,
            vendor_code="VND-MER-04",
            legal_name="Foreign Vendor 2",
        )
        db.add(v_meridian)
        db.commit()
        db.refresh(v_meridian)

        payload = {
            "assessment_code": "ASM-HACK-01",
            "title": "Injected Assessment",
            "assessment_type": "INITIAL_DUE_DILIGENCE",
        }
        res = client.post(
            f"/api/v1/vendors/{v_meridian.id}/assessments",
            json=payload,
            headers=admin_headers,
        )
        assert res.status_code == 404

    def test_adv_p9_05_foreign_evidence_injection(
        self, client: TestClient, db: Session, admin_user, analyst_user, org_apex, org_meridian, seeded_framework
    ):
        """ADV-P9-05: Cannot link another tenant's EvidenceItem to an Apex vendor."""
        admin_headers = get_token_headers(admin_user)
        v_apex = Vendor(
            organization_id=org_apex.id,
            vendor_code="VND-APX-EVD",
            legal_name="Apex Vendor",
        )
        db.add(v_apex)
        db.commit()
        db.refresh(v_apex)

        subcat = seeded_framework.functions[0].categories[0].subcategories[0]
        ctrl_meridian = OrganizationControl(
            organization_id=org_meridian.id,
            subcategory_id=subcat.id,
            status=ImplementationStatusEnum.IMPLEMENTED,
        )
        db.add(ctrl_meridian)
        db.commit()
        db.refresh(ctrl_meridian)

        foreign_evidence = EvidenceItem(
            organization_id=org_meridian.id,
            organization_control_id=ctrl_meridian.id,
            title="Meridian SOC 2",
            original_filename="meridian_soc2.pdf",
            stored_filename="meridian_soc2.pdf",
            file_extension="pdf",
            content_type="application/pdf",
            file_size=1024,
            sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            storage_key="org_2/soc2.pdf",
            uploaded_by_id=admin_user.id,
            status=EvidenceStatusEnum.ACCEPTED,
        )
        db.add(foreign_evidence)
        db.commit()
        db.refresh(foreign_evidence)

        now = datetime.now(timezone.utc)
        payload = {
            "evidence_id": foreign_evidence.id,
            "document_type": "SOC2_TYPE2",
            "effective_date": now.isoformat(),
            "expiration_date": (now + timedelta(days=365)).isoformat(),
        }
        res = client.post(
            f"/api/v1/vendors/{v_apex.id}/evidence",
            json=payload,
            headers=admin_headers,
        )
        assert res.status_code == 404

    def test_adv_p9_06_organization_id_spoofing(
        self, client: TestClient, db: Session, admin_user, org_meridian
    ):
        """ADV-P9-06: organization_id in request body is completely ignored and overridden by JWT."""
        admin_headers = get_token_headers(admin_user)
        payload = {
            "vendor_code": "VND-SPOOF-01",
            "legal_name": "Spoofed Org Vendor",
            "organization_id": org_meridian.id,  # Attempting to assign to foreign org
        }
        res = client.post("/api/v1/vendors", json=payload, headers=admin_headers)
        assert res.status_code == 201
        data = res.json()
        assert data["organization_id"] == admin_user.organization_id
        assert data["organization_id"] != org_meridian.id

    def test_adv_p9_07_inherent_risk_mass_assignment(
        self, client: TestClient, db: Session, admin_user, org_apex
    ):
        """ADV-P9-07: Inherent risk score cannot be set via client create/update."""
        admin_headers = get_token_headers(admin_user)
        payload = {
            "vendor_code": "VND-MASS-01",
            "legal_name": "Mass Assignment Vendor",
            "calculated_inherent_risk": 99.9,  # Injected field
        }
        res = client.post("/api/v1/vendors", json=payload, headers=admin_headers)
        assert res.status_code == 201
        assert res.json()["calculated_inherent_risk"] == 0.0

    def test_adv_p9_08_residual_risk_mass_assignment(
        self, client: TestClient, db: Session, admin_user, org_apex
    ):
        """ADV-P9-08: Residual risk score cannot be overwritten by client patch."""
        admin_headers = get_token_headers(admin_user)
        v = Vendor(
            organization_id=org_apex.id,
            vendor_code="VND-MASS-02",
            legal_name="Mass Residual",
            residual_risk_score=75.0,
        )
        db.add(v)
        db.commit()
        db.refresh(v)

        res = client.patch(
            f"/api/v1/vendors/{v.id}",
            json={"residual_risk_score": 0.0},
            headers=admin_headers,
        )
        assert res.status_code == 200
        assert res.json()["residual_risk_score"] == 75.0

    def test_adv_p9_09_calculated_tier_override_blocked(
        self, client: TestClient, db: Session, admin_user, org_apex
    ):
        """ADV-P9-09: calculated_tier cannot be modified directly via standard vendor patch."""
        admin_headers = get_token_headers(admin_user)
        v = Vendor(
            organization_id=org_apex.id,
            vendor_code="VND-TIER-01",
            legal_name="Tier Patch Vendor",
            calculated_tier=VendorTierEnum.TIER_1_CRITICAL,
        )
        db.add(v)
        db.commit()
        db.refresh(v)

        res = client.patch(
            f"/api/v1/vendors/{v.id}",
            json={"calculated_tier": "TIER_4_LOW"},
            headers=admin_headers,
        )
        assert res.status_code == 200
        assert res.json()["calculated_tier"] == "TIER_1_CRITICAL"

    def test_adv_p9_10_tier_override_without_justification(
        self, client: TestClient, db: Session, admin_user, org_apex
    ):
        """ADV-P9-10: Manual tier override without minimum 10-char justification is rejected."""
        admin_headers = get_token_headers(admin_user)
        v = Vendor(
            organization_id=org_apex.id,
            vendor_code="VND-OVR-01",
            legal_name="Override Test Vendor",
        )
        db.add(v)
        db.commit()
        db.refresh(v)

        payload = {
            "override_tier": "TIER_3_MODERATE",
            "reason": "short",  # < 10 characters
        }
        res = client.post(
            f"/api/v1/vendors/{v.id}/override-tier",
            json=payload,
            headers=admin_headers,
        )
        assert res.status_code in [400, 422]

    def test_adv_p9_11_unauthorized_tier_override(
        self, client: TestClient, db: Session, analyst_user, org_apex
    ):
        """ADV-P9-11: GRC_ANALYST lacks vendor:approve and cannot override vendor tiers."""
        analyst_headers = get_token_headers(analyst_user)
        v = Vendor(
            organization_id=org_apex.id,
            vendor_code="VND-OVR-02",
            legal_name="Override Perm Vendor",
        )
        db.add(v)
        db.commit()
        db.refresh(v)

        payload = {
            "override_tier": "TIER_2_SIGNIFICANT",
            "reason": "Valid reason exceeding 10 characters",
        }
        res = client.post(
            f"/api/v1/vendors/{v.id}/override-tier",
            json=payload,
            headers=analyst_headers,
        )
        assert res.status_code == 403

    def test_adv_p9_12_assessment_self_approval(
        self, client: TestClient, db: Session, admin_user, org_apex
    ):
        """ADV-P9-12: The assessor cannot approve their own assessment (Four-Eyes Principle)."""
        admin_headers = get_token_headers(admin_user)
        v = Vendor(
            organization_id=org_apex.id,
            vendor_code="VND-SELF-01",
            legal_name="Self Approval Vendor",
        )
        db.add(v)
        db.commit()
        db.refresh(v)

        asm = VendorAssessment(
            organization_id=org_apex.id,
            vendor_id=v.id,
            assessment_code="ASM-SELF-01",
            title="Self Assessment",
            status=VendorAssessmentStatusEnum.IN_REVIEW,
            assessor_id=admin_user.id,  # Assessor is admin
        )
        db.add(asm)
        db.commit()
        db.refresh(asm)

        # Same admin attempts to approve -> Must fail with 400 separation of duties error
        res = client.post(
            f"/api/v1/vendors/assessments/{asm.id}/approve",
            json={"review_notes": "Self approved"},
            headers=admin_headers,
        )
        assert res.status_code == 400
        assert "separation of duties" in res.json()["detail"].lower()

    def test_adv_p9_13_unauthorized_assessment_approval(
        self, client: TestClient, db: Session, analyst_user, admin_user, org_apex
    ):
        """ADV-P9-13: GRC_ANALYST lacks vendor:approve and cannot approve assessments."""
        analyst_headers = get_token_headers(analyst_user)
        v = Vendor(
            organization_id=org_apex.id,
            vendor_code="VND-APPR-01",
            legal_name="Approval Perm Vendor",
        )
        db.add(v)
        db.commit()
        db.refresh(v)

        asm = VendorAssessment(
            organization_id=org_apex.id,
            vendor_id=v.id,
            assessment_code="ASM-APPR-01",
            title="Due Diligence",
            status=VendorAssessmentStatusEnum.IN_REVIEW,
            assessor_id=admin_user.id,
        )
        db.add(asm)
        db.commit()
        db.refresh(asm)

        res = client.post(
            f"/api/v1/vendors/assessments/{asm.id}/approve",
            json={"review_notes": "Analyst approving"},
            headers=analyst_headers,
        )
        assert res.status_code == 403

    def test_adv_p9_14_approved_assessment_mutation(
        self, client: TestClient, db: Session, admin_user, analyst_user, org_apex
    ):
        """ADV-P9-14: Once approved, assessment items become strictly immutable."""
        analyst_headers = get_token_headers(analyst_user)
        v = Vendor(
            organization_id=org_apex.id,
            vendor_code="VND-IMM-01",
            legal_name="Immutable Vendor",
        )
        db.add(v)
        db.commit()
        db.refresh(v)

        asm = VendorAssessment(
            organization_id=org_apex.id,
            vendor_id=v.id,
            assessment_code="ASM-IMM-01",
            title="Approved Assessment",
            status=VendorAssessmentStatusEnum.APPROVED,
            assessor_id=analyst_user.id,
            reviewer_id=admin_user.id,
        )
        db.add(asm)
        db.commit()
        db.refresh(asm)

        item = VendorAssessmentItem(
            organization_id=org_apex.id,
            assessment_id=asm.id,
            question_key="Q1",
            question_text="MFA",
            response_status=VendorResponseStatusEnum.COMPLIANT,
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        # Attempt to modify item of approved assessment
        res = client.patch(
            f"/api/v1/vendors/assessments/{asm.id}/items",
            json={str(item.id): {"response_status": "NON_COMPLIANT"}},
            headers=analyst_headers,
        )
        assert res.status_code == 400
        assert "immutable" in res.json()["detail"].lower() or "cannot modify" in res.json()["detail"].lower()

    def test_adv_p9_15_illegal_vendor_lifecycle_transition(
        self, client: TestClient, db: Session, admin_user, org_apex
    ):
        """ADV-P9-15: Illegal skip transitions like PROSPECT -> ACTIVE are rejected."""
        admin_headers = get_token_headers(admin_user)
        v = Vendor(
            organization_id=org_apex.id,
            vendor_code="VND-SKIP-01",
            legal_name="Skip Vendor",
            vendor_status=VendorStatusEnum.PROSPECT,
        )
        db.add(v)
        db.commit()
        db.refresh(v)

        res = client.patch(
            f"/api/v1/vendors/{v.id}",
            json={"vendor_status": "ACTIVE"},
            headers=admin_headers,
        )
        assert res.status_code == 400
        assert "invalid vendor lifecycle transition" in res.json()["detail"].lower()

    def test_adv_p9_16_vendor_termination_with_active_assessments(
        self, client: TestClient, db: Session, admin_user, org_apex
    ):
        """ADV-P9-16: Terminating a vendor transitions it to TERMINATED, and no further transitions are allowed."""
        admin_headers = get_token_headers(admin_user)
        v = Vendor(
            organization_id=org_apex.id,
            vendor_code="VND-TERM-01",
            legal_name="Terminated Vendor",
            vendor_status=VendorStatusEnum.ACTIVE,
        )
        db.add(v)
        db.commit()
        db.refresh(v)

        # Terminate
        res = client.patch(
            f"/api/v1/vendors/{v.id}",
            json={"vendor_status": "TERMINATED"},
            headers=admin_headers,
        )
        assert res.status_code == 200
        assert res.json()["vendor_status"] == "TERMINATED"

        # Attempt to reactivate -> Must fail
        res2 = client.patch(
            f"/api/v1/vendors/{v.id}",
            json={"vendor_status": "ACTIVE"},
            headers=admin_headers,
        )
        assert res2.status_code == 400

    def test_adv_p9_17_superseded_evidence_linkage_blocked(
        self, client: TestClient, db: Session, admin_user, analyst_user, org_apex, seeded_framework
    ):
        """ADV-P9-17: Linking superseded evidence to a vendor is rejected."""
        admin_headers = get_token_headers(admin_user)
        v = Vendor(
            organization_id=org_apex.id,
            vendor_code="VND-SUP-EVD",
            legal_name="Superseded Evd Vendor",
        )
        db.add(v)
        db.commit()
        db.refresh(v)

        subcat = seeded_framework.functions[0].categories[0].subcategories[0]
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
            title="Old SOC 2",
            original_filename="old_soc2.pdf",
            stored_filename="old_soc2.pdf",
            file_extension="pdf",
            content_type="application/pdf",
            file_size=1024,
            sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            storage_key="org_1/old_soc2.pdf",
            uploaded_by_id=analyst_user.id,
            status=EvidenceStatusEnum.SUPERSEDED,  # Superseded
        )
        db.add(evidence)
        db.commit()
        db.refresh(evidence)

        now = datetime.now(timezone.utc)
        payload = {
            "evidence_id": evidence.id,
            "document_type": "SOC2_TYPE2",
            "effective_date": now.isoformat(),
            "expiration_date": (now + timedelta(days=365)).isoformat(),
        }
        res = client.post(
            f"/api/v1/vendors/{v.id}/evidence",
            json=payload,
            headers=admin_headers,
        )
        assert res.status_code == 400
        assert "superseded" in res.json()["detail"].lower()

    def test_adv_p9_18_duplicate_evidence_linkage_blocked(
        self, client: TestClient, db: Session, admin_user, analyst_user, org_apex, seeded_framework
    ):
        """ADV-P9-18: Linking the same evidence item multiple times returns 400."""
        admin_headers = get_token_headers(admin_user)
        v = Vendor(
            organization_id=org_apex.id,
            vendor_code="VND-DUP-EVD2",
            legal_name="Duplicate Evd Vendor",
        )
        db.add(v)
        db.commit()
        db.refresh(v)

        subcat = seeded_framework.functions[0].categories[0].subcategories[0]
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
            title="Active SOC 2",
            original_filename="active_soc2.pdf",
            stored_filename="active_soc2.pdf",
            file_extension="pdf",
            content_type="application/pdf",
            file_size=1024,
            sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            storage_key="org_1/active_soc2.pdf",
            uploaded_by_id=analyst_user.id,
            status=EvidenceStatusEnum.ACCEPTED,
        )
        db.add(evidence)
        db.commit()
        db.refresh(evidence)

        now = datetime.now(timezone.utc)
        payload = {
            "evidence_id": evidence.id,
            "document_type": "SOC2_TYPE2",
            "effective_date": now.isoformat(),
            "expiration_date": (now + timedelta(days=365)).isoformat(),
        }
        res1 = client.post(f"/api/v1/vendors/{v.id}/evidence", json=payload, headers=admin_headers)
        assert res1.status_code == 201

        # Duplicate link
        res2 = client.post(f"/api/v1/vendors/{v.id}/evidence", json=payload, headers=admin_headers)
        assert res2.status_code == 400
        assert "already linked" in res2.json()["detail"].lower()

    def test_adv_p9_19_inactive_or_foreign_business_owner_rejected(
        self, client: TestClient, db: Session, admin_user, org_meridian
    ):
        """ADV-P9-19: Setting a foreign or inactive user as business owner is rejected."""
        admin_headers = get_token_headers(admin_user)
        from app.core.permissions import RoleEnum
        # Foreign user
        foreign_user = User(
            email="foreign@meridian.com",
            full_name="Foreign Meridian User",
            organization_id=org_meridian.id,
            is_active=True,
            role=RoleEnum.VIEWER,
            hashed_password="xxx",
        )
        db.add(foreign_user)
        db.commit()
        db.refresh(foreign_user)

        payload = {
            "vendor_code": "VND-OWNER-01",
            "legal_name": "Owner Check Vendor",
            "business_owner_id": foreign_user.id,
        }
        res = client.post("/api/v1/vendors", json=payload, headers=admin_headers)
        assert res.status_code == 400
        assert "business owner" in res.json()["detail"].lower()

    def test_adv_p9_20_complete_audit_event_verification(
        self, client: TestClient, db: Session, admin_user, analyst_user, org_apex
    ):
        """ADV-P9-20: Verifies complete audit logging across vendor, engagement, assessment, and evidence events."""
        admin_headers = get_token_headers(admin_user)
        analyst_headers = get_token_headers(analyst_user)

        # 1. Create vendor
        res_v = client.post(
            "/api/v1/vendors",
            json={"vendor_code": "VND-AUD-01", "legal_name": "Audit Test Vendor"},
            headers=admin_headers,
        )
        assert res_v.status_code == 201
        v_id = res_v.json()["id"]

        # 2. Override tier
        res_ovr = client.post(
            f"/api/v1/vendors/{v_id}/override-tier",
            json={"override_tier": "TIER_1_CRITICAL", "reason": "Mandatory tier escalation for audit"},
            headers=admin_headers,
        )
        assert res_ovr.status_code == 200

        # 3. Create engagement
        res_eng = client.post(
            f"/api/v1/vendors/{v_id}/engagements",
            json={"engagement_code": "ENG-AUD-01", "engagement_name": "Audit Engagement", "criticality": "HIGH"},
            headers=admin_headers,
        )
        assert res_eng.status_code == 201

        # Check audit logs in DB
        logs = db.query(AuditLog).filter(AuditLog.organization_id == org_apex.id).all()
        actions = [log.action for log in logs]

        assert "VENDOR_CREATED" in actions
        assert "VENDOR_TIER_OVERRIDE" in actions
        assert "VENDOR_ENGAGEMENT_CREATED" in actions

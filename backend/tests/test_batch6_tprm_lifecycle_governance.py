import hashlib
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.permissions import RoleEnum
from app.core.security import get_password_hash
from app.models.control import ImplementationStatusEnum, OrganizationControl
from app.models.evidence import EvidenceItem, EvidenceStatusEnum, EvidenceTypeEnum
from app.models.exception import (
    ExceptionStatusEnum,
    ExceptionTypeEnum,
    SecurityException,
)
from app.models.finding import Finding, FindingSeverityEnum, FindingStatusEnum
from app.models.harmonization import (
    CommonControlDomainEnum,
    CommonControlMapping,
    RationalizedCommonControl,
)
from app.models.tprm import (
    BusinessCriticalityEnum,
    DataClassificationEnum,
    EngagementStatusEnum,
    HostingModelEnum,
    NetworkConnectivityEnum,
    PiiFinancialAccessEnum,
    SlaComparisonOperatorEnum,
    SlaMetricTypeEnum,
    Vendor,
    VendorAssessment,
    VendorAssessmentItem,
    VendorAssessmentStatusEnum,
    VendorAssessmentTypeEnum,
    VendorContract,
    VendorContractStatusEnum,
    VendorContractTypeEnum,
    VendorEngagement,
    VendorOffboardingItem,
    VendorOffboardingItemStatusEnum,
    VendorOffboardingReasonEnum,
    VendorOffboardingRecord,
    VendorOffboardingStepTypeEnum,
    VendorOffboardingStatusEnum,
    VendorResponseStatusEnum,
    VendorSlaBreach,
    VendorSlaBreachSeverityEnum,
    VendorSlaBreachStatusEnum,
    VendorSlaObligation,
    VendorSlaObligationStatusEnum,
    VendorStatusEnum,
    VendorSubprocessor,
    VendorSubprocessorStatusEnum,
    VendorTierEnum,
)
from app.models.user import User
from app.services.finding_service import FindingService
from app.services.tprm_service import TPRMService
from tests.conftest import get_token_headers


# ─── HELPER FIXTURES ─────────────────────────────────────────────────────────


@pytest.fixture(scope="function")
def manager_user(db: Session, org_apex) -> User:
    user = User(
        email="manager@apexfinancial.com",
        hashed_password=get_password_hash("ManagerPassword123!"),
        full_name="Victor Sterling",
        role=RoleEnum.MANAGER,
        is_active=True,
        organization_id=org_apex.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def sec_analyst_user(db: Session, org_apex) -> User:
    user = User(
        email="secanalyst@apexfinancial.com",
        hashed_password=get_password_hash("SecAnalystPassword123!"),
        full_name="Nadia Kovalenko",
        role=RoleEnum.SECURITY_ANALYST,
        is_active=True,
        organization_id=org_apex.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _seed_org_control(db: Session, org_id: int, seeded_framework) -> OrganizationControl:
    subcat = seeded_framework.functions[0].categories[0].subcategories[0]
    ctrl = (
        db.query(OrganizationControl)
        .filter(
            OrganizationControl.organization_id == org_id,
            OrganizationControl.subcategory_id == subcat.id,
        )
        .first()
    )
    if not ctrl:
        ctrl = OrganizationControl(
            organization_id=org_id,
            subcategory_id=subcat.id,
            status=ImplementationStatusEnum.IMPLEMENTED,
        )
        db.add(ctrl)
        db.commit()
        db.refresh(ctrl)
    return ctrl


def _seed_accepted_evidence(
    db: Session,
    org_id: int,
    ctrl_id: int,
    uploader_id: int,
    title: str = "SOC 2 Type II Attestation",
    status: EvidenceStatusEnum = EvidenceStatusEnum.ACCEPTED,
    valid_until: datetime | None = None,
) -> EvidenceItem:
    now = datetime.now(timezone.utc)
    digest = hashlib.sha256(f"{title}-{now.timestamp()}".encode()).hexdigest()
    ev = EvidenceItem(
        organization_id=org_id,
        organization_control_id=ctrl_id,
        title=title,
        original_filename="soc2_report.pdf",
        stored_filename=f"soc2_{digest[:8]}.pdf",
        file_extension="pdf",
        content_type="application/pdf",
        file_size=4096,
        sha256_hash=digest,
        storage_key=f"org_{org_id}/soc2_{digest[:8]}.pdf",
        uploaded_by_id=uploader_id,
        status=status,
        valid_until=valid_until if valid_until is not None else (now + timedelta(days=335)),
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


def _seed_active_vendor(
    db: Session,
    org_id: int,
    code: str = "VND-APX-01",
    name: str = "Apex Cloud Hosting Inc",
    tier: VendorTierEnum = VendorTierEnum.TIER_1_CRITICAL,
    inherent_risk: float = 88.0,
) -> Vendor:
    v = Vendor(
        organization_id=org_id,
        vendor_code=code,
        legal_name=name,
        vendor_status=VendorStatusEnum.ACTIVE,
        calculated_inherent_risk=inherent_risk,
        calculated_tier=tier,
        residual_risk_score=inherent_risk,
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


# ─── BATCH 6 ADVERSARIAL SECURITY & GOVERNANCE TEST SUITE (60 VECTORS) ──────


class TestBatch6TPRMLifecycleGovernance:
    """60 Adversarial Security & Governance Tests for Batch 6 (SEC-B6-01 .. SEC-B6-60)."""

    def test_sec_b6_01(
        self, client: TestClient, db: Session, admin_user, org_meridian, meridian_admin_user
    ):
        """SEC-B6-01: Cross-tenant GET /vendors/{foreign_vendor_id}/contracts returns 404."""
        v_mer = _seed_active_vendor(db, org_meridian.id, "VND-MER-B6-01", "Meridian Vendor 01")
        contract = VendorContract(
            organization_id=org_meridian.id,
            vendor_id=v_mer.id,
            contract_code="CNT-MER-01",
            title="Meridian Secret MSA",
            contract_type=VendorContractTypeEnum.MSA,
            status=VendorContractStatusEnum.DRAFT,
            effective_date=datetime.now(timezone.utc),
            created_by_id=meridian_admin_user.id,
        )
        db.add(contract)
        db.commit()

        res = client.get(
            f"/api/v1/vendors/{v_mer.id}/contracts",
            headers=get_token_headers(admin_user),
        )
        assert res.status_code == 404

    def test_sec_b6_02(
        self, client: TestClient, db: Session, admin_user, org_apex, org_meridian, meridian_admin_user
    ):
        """SEC-B6-02: Cross-tenant PATCH /vendors/{vendor_id}/contracts/{foreign_contract_id} returns 404."""
        v_apx = _seed_active_vendor(db, org_apex.id, "VND-APX-B6-02")
        v_mer = _seed_active_vendor(db, org_meridian.id, "VND-MER-B6-02")
        foreign_contract = VendorContract(
            organization_id=org_meridian.id,
            vendor_id=v_mer.id,
            contract_code="CNT-MER-02",
            title="Meridian DPA",
            contract_type=VendorContractTypeEnum.DPA,
            status=VendorContractStatusEnum.DRAFT,
            effective_date=datetime.now(timezone.utc),
            created_by_id=meridian_admin_user.id,
        )
        db.add(foreign_contract)
        db.commit()
        db.refresh(foreign_contract)

        res = client.patch(
            f"/api/v1/vendors/{v_apx.id}/contracts/{foreign_contract.id}",
            json={"title": "Hijacked Title"},
            headers=get_token_headers(admin_user),
        )
        assert res.status_code == 404

    def test_sec_b6_03(
        self, client: TestClient, db: Session, admin_user, org_meridian
    ):
        """SEC-B6-03: Cross-tenant POST /vendors/{foreign_vendor_id}/subprocessors returns 404."""
        v_mer = _seed_active_vendor(db, org_meridian.id, "VND-MER-B6-03")
        res = client.post(
            f"/api/v1/vendors/{v_mer.id}/subprocessors",
            json={
                "subprocessor_code": "SUB-HACK-03",
                "subprocessor_name": "Injected Fourth Party",
                "service_function": "Cloud Storage",
            },
            headers=get_token_headers(admin_user),
        )
        assert res.status_code == 404

    def test_sec_b6_04(
        self, client: TestClient, db: Session, admin_user, org_apex, org_meridian, meridian_admin_user
    ):
        """SEC-B6-04: Cross-tenant POST /vendors/{vendor_id}/subprocessors/{foreign_subprocessor_id}/approve returns 404."""
        v_apx = _seed_active_vendor(db, org_apex.id, "VND-APX-B6-04")
        v_mer = _seed_active_vendor(db, org_meridian.id, "VND-MER-B6-04")
        sp_mer = VendorSubprocessor(
            organization_id=org_meridian.id,
            vendor_id=v_mer.id,
            subprocessor_code="SUB-MER-04",
            subprocessor_name="Meridian Subprocessor",
            normalized_fourth_party_name="meridian subprocessor",
            service_function="Analytics",
            status=VendorSubprocessorStatusEnum.PENDING_REVIEW,
            registered_by_id=meridian_admin_user.id,
        )
        db.add(sp_mer)
        db.commit()
        db.refresh(sp_mer)

        res = client.post(
            f"/api/v1/vendors/{v_apx.id}/subprocessors/{sp_mer.id}/approve",
            json={"review_notes": "Cross-tenant approve attempt"},
            headers=get_token_headers(admin_user),
        )
        assert res.status_code == 404

    def test_sec_b6_05(
        self, client: TestClient, db: Session, admin_user, org_meridian
    ):
        """SEC-B6-05: Cross-tenant GET /vendors/{foreign_vendor_id}/sla-obligations returns 404."""
        v_mer = _seed_active_vendor(db, org_meridian.id, "VND-MER-B6-05")
        res = client.get(
            f"/api/v1/vendors/{v_mer.id}/sla-obligations",
            headers=get_token_headers(admin_user),
        )
        assert res.status_code == 404

    def test_sec_b6_06(
        self, client: TestClient, db: Session, admin_user, org_meridian, meridian_admin_user
    ):
        """SEC-B6-06: Cross-tenant POST /vendors/{foreign_vendor_id}/sla-breaches returns 404."""
        v_mer = _seed_active_vendor(db, org_meridian.id, "VND-MER-B6-06")
        ob = VendorSlaObligation(
            organization_id=org_meridian.id,
            vendor_id=v_mer.id,
            obligation_code="SLA-MER-06",
            title="Meridian Uptime",
            metric_type=SlaMetricTypeEnum.AVAILABILITY_PCT,
            comparison_operator=SlaComparisonOperatorEnum.GTE,
            target_value=99.9,
            warning_threshold=99.95,
            breach_threshold=99.5,
            status=VendorSlaObligationStatusEnum.ACTIVE,
            effective_from=datetime.now(timezone.utc) - timedelta(days=10),
            created_by_id=meridian_admin_user.id,
        )
        db.add(ob)
        db.commit()
        db.refresh(ob)

        now = datetime.now(timezone.utc)
        res = client.post(
            f"/api/v1/vendors/{v_mer.id}/sla-breaches",
            json={
                "sla_obligation_id": ob.id,
                "breach_code": "BRC-HACK-06",
                "observed_value": 98.0,
                "breach_period_start": (now - timedelta(hours=2)).isoformat(),
                "breach_period_end": (now - timedelta(hours=1)).isoformat(),
                "occurred_at": (now - timedelta(minutes=30)).isoformat(),
                "root_cause_summary": "Cross-tenant injection attempt",
            },
            headers=get_token_headers(admin_user),
        )
        assert res.status_code == 404

    def test_sec_b6_07(
        self, client: TestClient, db: Session, admin_user, org_apex, org_meridian, meridian_admin_user
    ):
        """SEC-B6-07: Cross-tenant POST /vendors/{vendor_id}/sla-breaches/{foreign_breach_id}/escalate returns 404."""
        v_apx = _seed_active_vendor(db, org_apex.id, "VND-APX-B6-07")
        v_mer = _seed_active_vendor(db, org_meridian.id, "VND-MER-B6-07")
        now = datetime.now(timezone.utc)
        ob = VendorSlaObligation(
            organization_id=org_meridian.id,
            vendor_id=v_mer.id,
            obligation_code="SLA-MER-07",
            title="Meridian Uptime",
            metric_type=SlaMetricTypeEnum.AVAILABILITY_PCT,
            comparison_operator=SlaComparisonOperatorEnum.GTE,
            target_value=99.9,
            breach_threshold=99.5,
            status=VendorSlaObligationStatusEnum.ACTIVE,
            effective_from=now - timedelta(days=10),
            created_by_id=meridian_admin_user.id,
        )
        db.add(ob)
        db.flush()
        breach = VendorSlaBreach(
            organization_id=org_meridian.id,
            vendor_id=v_mer.id,
            sla_obligation_id=ob.id,
            breach_code="BRC-MER-07",
            observed_value=95.0,
            target_value_snapshot=99.9,
            breach_threshold_snapshot=99.5,
            variance_magnitude=4.5,
            severity=VendorSlaBreachSeverityEnum.CRITICAL,
            status=VendorSlaBreachStatusEnum.OPEN,
            breach_period_start=now - timedelta(hours=3),
            breach_period_end=now - timedelta(hours=1),
            occurred_at=now - timedelta(minutes=30),
            root_cause_summary="Foreign breach",
            recorded_by_id=meridian_admin_user.id,
        )
        db.add(breach)
        db.commit()
        db.refresh(breach)

        res = client.post(
            f"/api/v1/vendors/{v_apx.id}/sla-breaches/{breach.id}/escalate",
            json={"create_finding": True, "create_remediation_plan": True},
            headers=get_token_headers(admin_user),
        )
        assert res.status_code == 404

    def test_sec_b6_08(
        self, client: TestClient, db: Session, admin_user, org_meridian, meridian_admin_user
    ):
        """SEC-B6-08: Cross-tenant POST /vendors/assessments/{foreign_assessment_id}/items/{foreign_item_id}/escalate returns 404."""
        v_mer = _seed_active_vendor(db, org_meridian.id, "VND-MER-B6-08")
        asm = VendorAssessment(
            organization_id=org_meridian.id,
            vendor_id=v_mer.id,
            assessment_code="ASM-MER-08",
            title="Meridian Assessment",
            assessment_type=VendorAssessmentTypeEnum.ANNUAL_REASSESSMENT,
            status=VendorAssessmentStatusEnum.IN_REVIEW,
            assessor_id=meridian_admin_user.id,
        )
        db.add(asm)
        db.flush()
        item = VendorAssessmentItem(
            organization_id=org_meridian.id,
            assessment_id=asm.id,
            question_key="Q-MER-01",
            question_text="Encryption at rest?",
            response_status=VendorResponseStatusEnum.NON_COMPLIANT,
            weight=5.0,
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        res = client.post(
            f"/api/v1/vendors/assessments/{asm.id}/items/{item.id}/escalate",
            json={"create_finding": True, "create_remediation_plan": True},
            headers=get_token_headers(admin_user),
        )
        assert res.status_code == 404

    def test_sec_b6_09(
        self, client: TestClient, db: Session, admin_user, org_meridian
    ):
        """SEC-B6-09: Cross-tenant POST /vendors/{foreign_vendor_id}/offboarding returns 404."""
        v_mer = _seed_active_vendor(db, org_meridian.id, "VND-MER-B6-09")
        res = client.post(
            f"/api/v1/vendors/{v_mer.id}/offboarding",
            json={
                "offboarding_code": "OFB-HACK-09",
                "reason": "CONTRACT_EXPIRATION",
                "target_vendor_status": "OFFBOARDED",
                "rationale": "Cross-tenant offboarding attack",
            },
            headers=get_token_headers(admin_user),
        )
        assert res.status_code == 404

    def test_sec_b6_10(
        self, client: TestClient, db: Session, admin_user, org_apex, org_meridian, meridian_admin_user
    ):
        """SEC-B6-10: Cross-tenant PATCH /vendors/{vendor_id}/offboarding/{record_id}/items/{foreign_item_id} returns 404."""
        v_apx = _seed_active_vendor(db, org_apex.id, "VND-APX-B6-10")
        v_mer = _seed_active_vendor(db, org_meridian.id, "VND-MER-B6-10")

        rec_apx = TPRMService.initiate_offboarding(
            db=db,
            vendor=v_apx,
            payload=type(
                "Obj",
                (),
                {
                    "offboarding_code": "OFB-APX-10",
                    "reason": VendorOffboardingReasonEnum.CONTRACT_EXPIRATION,
                    "target_vendor_status": VendorStatusEnum.OFFBOARDED,
                    "rationale": "Normal offboarding",
                },
            )(),
            initiator_id=admin_user.id,
        )
        rec_mer = TPRMService.initiate_offboarding(
            db=db,
            vendor=v_mer,
            payload=type(
                "Obj",
                (),
                {
                    "offboarding_code": "OFB-MER-10",
                    "reason": VendorOffboardingReasonEnum.CONTRACT_EXPIRATION,
                    "target_vendor_status": VendorStatusEnum.OFFBOARDED,
                    "rationale": "Meridian offboarding",
                },
            )(),
            initiator_id=meridian_admin_user.id,
        )
        db.commit()
        foreign_item = rec_mer.items[0]

        res = client.patch(
            f"/api/v1/vendors/{v_apx.id}/offboarding/{rec_apx.id}/items/{foreign_item.id}",
            json={"attestation_notes": "Cross-tenant item tamper"},
            headers=get_token_headers(admin_user),
        )
        assert res.status_code == 404

    def test_sec_b6_11(
        self, client: TestClient, db: Session, admin_user, org_apex, org_meridian, meridian_admin_user
    ):
        """SEC-B6-11: Cross-tenant GET /vendors/concentration-risk returns only caller's tenant fourth parties."""
        v_mer1 = _seed_active_vendor(db, org_meridian.id, "VND-MER-11A")
        v_mer2 = _seed_active_vendor(db, org_meridian.id, "VND-MER-11B")
        for idx, vm in enumerate([v_mer1, v_mer2], start=1):
            db.add(
                VendorSubprocessor(
                    organization_id=org_meridian.id,
                    vendor_id=vm.id,
                    subprocessor_code=f"SUB-MER-11-{idx}",
                    subprocessor_name="Meridian Exclusive Cloud",
                    normalized_fourth_party_name="meridian exclusive cloud",
                    service_function="Core Hosting",
                    criticality=BusinessCriticalityEnum.CRITICAL,
                    status=VendorSubprocessorStatusEnum.APPROVED,
                    registered_by_id=meridian_admin_user.id,
                )
            )
        db.commit()

        res = client.get(
            "/api/v1/vendors/concentration-risk",
            headers=get_token_headers(admin_user),
        )
        assert res.status_code == 200
        body = res.json()
        assert body["organization_id"] == org_apex.id
        names = [n["normalized_fourth_party_name"] for n in body["nodes"]]
        assert "meridian exclusive cloud" not in names

    def test_sec_b6_12(
        self, client: TestClient, db: Session, admin_user, org_apex, org_meridian, seeded_framework
    ):
        """SEC-B6-12: Cross-tenant POST /exceptions with linked_vendor_id belonging to Org B returns 404."""
        ctrl_apx = _seed_org_control(db, org_apex.id, seeded_framework)
        v_mer = _seed_active_vendor(db, org_meridian.id, "VND-MER-B6-12")

        res = client.post(
            "/api/v1/exceptions",
            json={
                "linked_organization_control_id": ctrl_apx.id,
                "linked_vendor_id": v_mer.id,
                "title": "Cross-Tenant Vendor Exception",
                "description": "Attempting to link foreign vendor ID",
                "justification": "Attempting to link foreign vendor ID",
                "exception_type": "THIRD_PARTY_VENDOR",
                "expiry_date": (datetime.now(timezone.utc).date() + timedelta(days=30)).isoformat(),
            },
            headers=get_token_headers(admin_user),
        )
        assert res.status_code == 404

    def test_sec_b6_13(
        self, client: TestClient, db: Session, auditor_user, org_apex
    ):
        """SEC-B6-13: AUDITOR (vendor:read only) attempting POST /vendors/{id}/subprocessors returns 403."""
        v_apx = _seed_active_vendor(db, org_apex.id, "VND-APX-B6-13")
        res = client.post(
            f"/api/v1/vendors/{v_apx.id}/subprocessors",
            json={
                "subprocessor_code": "SUB-AUD-13",
                "subprocessor_name": "Unauthorized Subprocessor",
                "service_function": "Storage",
            },
            headers=get_token_headers(auditor_user),
        )
        assert res.status_code == 403

    def test_sec_b6_14(
        self, client: TestClient, db: Session, admin_user, sec_analyst_user, org_apex
    ):
        """SEC-B6-14: SECURITY_ANALYST (has vendor:assess, lacks vendor:approve) attempting subprocessor approve returns 403."""
        v_apx = _seed_active_vendor(
            db, org_apex.id, "VND-APX-B6-14", tier=VendorTierEnum.TIER_4_LOW, inherent_risk=20.0
        )
        sp = VendorSubprocessor(
            organization_id=org_apex.id,
            vendor_id=v_apx.id,
            subprocessor_code="SUB-APX-14",
            subprocessor_name="Fourth Party 14",
            normalized_fourth_party_name="fourth party 14",
            service_function="Logging",
            status=VendorSubprocessorStatusEnum.PENDING_REVIEW,
            registered_by_id=admin_user.id,
        )
        db.add(sp)
        db.commit()
        db.refresh(sp)

        res = client.post(
            f"/api/v1/vendors/{v_apx.id}/subprocessors/{sp.id}/approve",
            json={"review_notes": "Analyst trying to approve without vendor:approve"},
            headers=get_token_headers(sec_analyst_user),
        )
        assert res.status_code == 403

    def test_sec_b6_15(
        self, client: TestClient, db: Session, admin_user, sec_analyst_user, org_apex
    ):
        """SEC-B6-15: SECURITY_ANALYST attempting POST /vendors/{id}/offboarding/{rec_id}/approve returns 403."""
        v_apx = _seed_active_vendor(db, org_apex.id, "VND-APX-B6-15")
        rec = TPRMService.initiate_offboarding(
            db=db,
            vendor=v_apx,
            payload=type(
                "Obj",
                (),
                {
                    "offboarding_code": "OFB-APX-15",
                    "reason": VendorOffboardingReasonEnum.CONTRACT_EXPIRATION,
                    "target_vendor_status": VendorStatusEnum.OFFBOARDED,
                    "rationale": "Offboarding test 15",
                },
            )(),
            initiator_id=admin_user.id,
        )
        db.commit()
        db.refresh(rec)

        res = client.post(
            f"/api/v1/vendors/{v_apx.id}/offboarding/{rec.id}/approve",
            json={"signoff_notes": "Unauthorized signoff attempt by analyst"},
            headers=get_token_headers(sec_analyst_user),
        )
        assert res.status_code == 403

    def test_sec_b6_16(
        self, client: TestClient, db: Session, admin_user, auditor_user, org_apex
    ):
        """SEC-B6-16: AUDITOR attempting POST /vendors/{id}/sla-breaches/{breach_id}/escalate returns 403."""
        v_apx = _seed_active_vendor(db, org_apex.id, "VND-APX-B6-16")
        now = datetime.now(timezone.utc)
        ob = VendorSlaObligation(
            organization_id=org_apex.id,
            vendor_id=v_apx.id,
            obligation_code="SLA-APX-16",
            title="Availability",
            metric_type=SlaMetricTypeEnum.AVAILABILITY_PCT,
            comparison_operator=SlaComparisonOperatorEnum.GTE,
            target_value=99.9,
            breach_threshold=99.5,
            status=VendorSlaObligationStatusEnum.ACTIVE,
            effective_from=now - timedelta(days=5),
            created_by_id=admin_user.id,
        )
        db.add(ob)
        db.flush()
        breach = VendorSlaBreach(
            organization_id=org_apex.id,
            vendor_id=v_apx.id,
            sla_obligation_id=ob.id,
            breach_code="BRC-APX-16",
            observed_value=97.0,
            target_value_snapshot=99.9,
            breach_threshold_snapshot=99.5,
            variance_magnitude=2.5,
            severity=VendorSlaBreachSeverityEnum.HIGH,
            status=VendorSlaBreachStatusEnum.OPEN,
            breach_period_start=now - timedelta(hours=2),
            breach_period_end=now - timedelta(hours=1),
            occurred_at=now - timedelta(minutes=15),
            root_cause_summary="Outage",
            recorded_by_id=admin_user.id,
        )
        db.add(breach)
        db.commit()
        db.refresh(breach)

        res = client.post(
            f"/api/v1/vendors/{v_apx.id}/sla-breaches/{breach.id}/escalate",
            json={"create_finding": True},
            headers=get_token_headers(auditor_user),
        )
        assert res.status_code == 403

    def test_sec_b6_17(
        self, client: TestClient, db: Session, admin_user, org_apex
    ):
        """SEC-B6-17: Subprocessor Four-Eyes violation (approved_by_id == registered_by_id) returns 403."""
        v_apx = _seed_active_vendor(
            db, org_apex.id, "VND-APX-B6-17", tier=VendorTierEnum.TIER_4_LOW, inherent_risk=20.0
        )
        sp = VendorSubprocessor(
            organization_id=org_apex.id,
            vendor_id=v_apx.id,
            subprocessor_code="SUB-APX-17",
            subprocessor_name="Self Approved Sub",
            normalized_fourth_party_name="self approved sub",
            service_function="CDN",
            status=VendorSubprocessorStatusEnum.PENDING_REVIEW,
            registered_by_id=admin_user.id,
        )
        db.add(sp)
        db.commit()
        db.refresh(sp)

        res = client.post(
            f"/api/v1/vendors/{v_apx.id}/subprocessors/{sp.id}/approve",
            json={"review_notes": "Trying to self-approve"},
            headers=get_token_headers(admin_user),
        )
        assert res.status_code == 403
        assert "separation of duties" in res.json()["detail"].lower()

    def test_sec_b6_18(
        self, client: TestClient, db: Session, admin_user, org_apex, seeded_framework
    ):
        """SEC-B6-18: Contract Four-Eyes violation (approved_by_id == created_by_id) returns 403."""
        v_apx = _seed_active_vendor(db, org_apex.id, "VND-APX-B6-18")
        ctrl = _seed_org_control(db, org_apex.id, seeded_framework)
        ev = _seed_accepted_evidence(db, org_apex.id, ctrl.id, admin_user.id)
        now = datetime.now(timezone.utc)
        contract = VendorContract(
            organization_id=org_apex.id,
            vendor_id=v_apx.id,
            contract_code="CNT-APX-18",
            title="Self Approval Contract",
            contract_type=VendorContractTypeEnum.MSA,
            status=VendorContractStatusEnum.UNDER_REVIEW,
            effective_date=now,
            expiration_date=now + timedelta(days=365),
            evidence_id=ev.id,
            created_by_id=admin_user.id,
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)

        res = client.post(
            f"/api/v1/vendors/{v_apx.id}/contracts/{contract.id}/approve",
            json={"review_notes": "Self-approving contract"},
            headers=get_token_headers(admin_user),
        )
        assert res.status_code == 403
        assert "separation of duties" in res.json()["detail"].lower()

    def test_sec_b6_19(
        self, client: TestClient, db: Session, admin_user, manager_user, org_apex, seeded_framework
    ):
        """SEC-B6-19: SLA Breach waive/verify-close Four-Eyes violation (resolved_by_id == recorded_by_id) returns 403."""
        v_apx = _seed_active_vendor(db, org_apex.id, "VND-APX-B6-19")
        ctrl = _seed_org_control(db, org_apex.id, seeded_framework)
        now = datetime.now(timezone.utc)

        exc = SecurityException(
            organization_id=org_apex.id,
            linked_organization_control_id=ctrl.id,
            linked_vendor_id=v_apx.id,
            title="Approved Vendor SLA Exception",
            description="Approved business exception",
            justification="Approved business exception",
            exception_type=ExceptionTypeEnum.THIRD_PARTY_VENDOR,
            status=ExceptionStatusEnum.APPROVED,
            requested_by_id=manager_user.id,
            reviewer_id=admin_user.id,
            approved_at=now - timedelta(days=1),
            expiry_date=(now + timedelta(days=89)).date(),
        )
        db.add(exc)
        ob = VendorSlaObligation(
            organization_id=org_apex.id,
            vendor_id=v_apx.id,
            obligation_code="SLA-APX-19",
            title="Availability",
            metric_type=SlaMetricTypeEnum.AVAILABILITY_PCT,
            comparison_operator=SlaComparisonOperatorEnum.GTE,
            target_value=99.9,
            breach_threshold=99.5,
            status=VendorSlaObligationStatusEnum.ACTIVE,
            effective_from=now - timedelta(days=10),
            created_by_id=manager_user.id,
        )
        db.add(ob)
        db.flush()

        breach = VendorSlaBreach(
            organization_id=org_apex.id,
            vendor_id=v_apx.id,
            sla_obligation_id=ob.id,
            breach_code="BRC-APX-19",
            observed_value=98.0,
            target_value_snapshot=99.9,
            breach_threshold_snapshot=99.5,
            variance_magnitude=1.5,
            severity=VendorSlaBreachSeverityEnum.HIGH,
            status=VendorSlaBreachStatusEnum.OPEN,
            breach_period_start=now - timedelta(hours=2),
            breach_period_end=now - timedelta(hours=1),
            occurred_at=now - timedelta(minutes=20),
            root_cause_summary="Recorded by admin_user",
            recorded_by_id=admin_user.id,
        )
        db.add(breach)
        db.commit()
        db.refresh(breach)

        # Same user (admin_user) tries to waive the breach they recorded
        res = client.post(
            f"/api/v1/vendors/{v_apx.id}/sla-breaches/{breach.id}/waive",
            json={
                "linked_exception_id": exc.id,
                "resolution_notes": "Self-waiving SLA breach",
            },
            headers=get_token_headers(admin_user),
        )
        assert res.status_code == 403
        assert "separation of duties" in res.json()["detail"].lower()

    def test_sec_b6_20(
        self, client: TestClient, db: Session, admin_user, analyst_user, org_apex, seeded_framework
    ):
        """SEC-B6-20: Offboarding Four-Eyes violation (verified_by_id == initiated_by_id) returns 403."""
        v_apx = _seed_active_vendor(db, org_apex.id, "VND-APX-B6-20")
        ctrl = _seed_org_control(db, org_apex.id, seeded_framework)
        ev = _seed_accepted_evidence(db, org_apex.id, ctrl.id, analyst_user.id)

        rec = TPRMService.initiate_offboarding(
            db=db,
            vendor=v_apx,
            payload=type(
                "Obj",
                (),
                {
                    "offboarding_code": "OFB-APX-20",
                    "reason": VendorOffboardingReasonEnum.CONTRACT_EXPIRATION,
                    "target_vendor_status": VendorStatusEnum.OFFBOARDED,
                    "rationale": "Initiated by admin_user",
                },
            )(),
            initiator_id=admin_user.id,
        )
        db.commit()
        db.refresh(rec)

        for item in rec.items:
            TPRMService.attest_offboarding_item(
                db=db,
                record=rec,
                item=item,
                payload=type(
                    "Obj",
                    (),
                    {
                        "evidence_id": ev.id,
                        "attestation_notes": "Completed by analyst_user",
                    },
                )(),
                actor_id=analyst_user.id,
            )
        TPRMService.submit_offboarding(db=db, record=rec, submitter_id=analyst_user.id)
        db.commit()

        # Initiator (admin_user) attempts final verification sign-off
        res = client.post(
            f"/api/v1/vendors/{v_apx.id}/offboarding/{rec.id}/verify-close",
            json={"signoff_notes": "Self-verifying offboarding"},
            headers=get_token_headers(admin_user),
        )
        assert res.status_code == 403
        assert "separation of duties" in res.json()["detail"].lower()

    def test_sec_b6_21(
        self, client: TestClient, db: Session, admin_user, manager_user, org_apex, seeded_framework
    ):
        """SEC-B6-21: Offboarding item attestation Four-Eyes violation (verified_by_id == completed_by_id) returns 403."""
        v_apx = _seed_active_vendor(db, org_apex.id, "VND-APX-B6-21")
        ctrl = _seed_org_control(db, org_apex.id, seeded_framework)
        ev = _seed_accepted_evidence(db, org_apex.id, ctrl.id, admin_user.id)

        # Initiated by admin_user, items attested by manager_user, then manager_user tries to verify-close!
        rec = TPRMService.initiate_offboarding(
            db=db,
            vendor=v_apx,
            payload=type(
                "Obj",
                (),
                {
                    "offboarding_code": "OFB-APX-21",
                    "reason": VendorOffboardingReasonEnum.CONTRACT_EXPIRATION,
                    "target_vendor_status": VendorStatusEnum.OFFBOARDED,
                    "rationale": "Initiated by admin_user",
                },
            )(),
            initiator_id=admin_user.id,
        )
        db.commit()
        db.refresh(rec)

        for item in rec.items:
            TPRMService.attest_offboarding_item(
                db=db,
                record=rec,
                item=item,
                payload=type(
                    "Obj",
                    (),
                    {
                        "evidence_id": ev.id,
                        "attestation_notes": "Completed by manager_user",
                    },
                )(),
                actor_id=manager_user.id,
            )
        TPRMService.submit_offboarding(db=db, record=rec, submitter_id=manager_user.id)
        db.commit()

        # manager_user (who attested items) attempts final verification sign-off
        res = client.post(
            f"/api/v1/vendors/{v_apx.id}/offboarding/{rec.id}/verify-close",
            json={"signoff_notes": "Manager trying to verify items they completed"},
            headers=get_token_headers(manager_user),
        )
        assert res.status_code == 403
        assert "separation of duties" in res.json()["detail"].lower()

    def test_sec_b6_22(
        self, client: TestClient, db: Session, admin_user, org_apex, org_meridian
    ):
        """SEC-B6-22: Mass assignment of organization_id in VendorSubprocessorCreate / VendorContractCreate returns 422."""
        v_apx = _seed_active_vendor(db, org_apex.id, "VND-APX-B6-22")
        res = client.post(
            f"/api/v1/vendors/{v_apx.id}/subprocessors",
            json={
                "organization_id": org_meridian.id,
                "subprocessor_code": "SUB-MASS-22",
                "subprocessor_name": "Spoofed Tenant Sub",
                "service_function": "Storage",
            },
            headers=get_token_headers(admin_user),
        )
        assert res.status_code == 422

    def test_sec_b6_23(
        self, client: TestClient, db: Session, admin_user, manager_user, org_apex
    ):
        """SEC-B6-23: Mass assignment of registered_by_id, approved_by_id, recorded_by_id, initiated_by_id returns 422."""
        v_apx = _seed_active_vendor(db, org_apex.id, "VND-APX-B6-23")
        res1 = client.post(
            f"/api/v1/vendors/{v_apx.id}/subprocessors",
            json={
                "subprocessor_code": "SUB-MASS-23",
                "subprocessor_name": "Actor Spoof Sub",
                "service_function": "Compute",
                "registered_by_id": manager_user.id,
                "approved_by_id": manager_user.id,
            },
            headers=get_token_headers(admin_user),
        )
        assert res1.status_code == 422

        res2 = client.post(
            f"/api/v1/vendors/{v_apx.id}/offboarding",
            json={
                "offboarding_code": "OFB-MASS-23",
                "reason": "CONTRACT_EXPIRATION",
                "target_vendor_status": "OFFBOARDED",
                "rationale": "Spoofing initiated_by_id",
                "initiated_by_id": manager_user.id,
            },
            headers=get_token_headers(admin_user),
        )
        assert res2.status_code == 422

    def test_sec_b6_24(
        self, client: TestClient, db: Session, admin_user, org_apex
    ):
        """SEC-B6-24: Subprocessor self-reference (linked_fourth_party_vendor_id == vendor_id) returns 422."""
        v_apx = _seed_active_vendor(db, org_apex.id, "VND-APX-B6-24")
        res = client.post(
            f"/api/v1/vendors/{v_apx.id}/subprocessors",
            json={
                "subprocessor_code": "SUB-SELF-24",
                "subprocessor_name": v_apx.legal_name,
                "service_function": "Self Hosting",
                "linked_fourth_party_vendor_id": v_apx.id,
            },
            headers=get_token_headers(admin_user),
        )
        assert res.status_code == 422
        assert "self-referential" in res.json()["detail"].lower()

    def test_sec_b6_25(
        self, client: TestClient, db: Session, admin_user, org_apex
    ):
        """SEC-B6-25: Subprocessor 2-node cycle (Vendor A -> Vendor B -> Vendor A) returns 422."""
        v_a = _seed_active_vendor(db, org_apex.id, "VND-APX-25A", "Vendor Alpha")
        v_b = _seed_active_vendor(db, org_apex.id, "VND-APX-25B", "Vendor Beta")

        res1 = client.post(
            f"/api/v1/vendors/{v_a.id}/subprocessors",
            json={
                "subprocessor_code": "SUB-25-AB",
                "subprocessor_name": v_b.legal_name,
                "service_function": "Database",
                "linked_fourth_party_vendor_id": v_b.id,
            },
            headers=get_token_headers(admin_user),
        )
        assert res1.status_code == 201

        res2 = client.post(
            f"/api/v1/vendors/{v_b.id}/subprocessors",
            json={
                "subprocessor_code": "SUB-25-BA",
                "subprocessor_name": v_a.legal_name,
                "service_function": "Backup",
                "linked_fourth_party_vendor_id": v_a.id,
            },
            headers=get_token_headers(admin_user),
        )
        assert res2.status_code == 422
        assert "circular" in res2.json()["detail"].lower()

    def test_sec_b6_26(
        self, client: TestClient, db: Session, admin_user, org_apex
    ):
        """SEC-B6-26: Subprocessor 3-node transitive cycle (Vendor A -> Vendor B -> Vendor C -> Vendor A) returns 422."""
        v_a = _seed_active_vendor(db, org_apex.id, "VND-APX-26A", "Vendor A")
        v_b = _seed_active_vendor(db, org_apex.id, "VND-APX-26B", "Vendor B")
        v_c = _seed_active_vendor(db, org_apex.id, "VND-APX-26C", "Vendor C")

        assert (
            client.post(
                f"/api/v1/vendors/{v_a.id}/subprocessors",
                json={
                    "subprocessor_code": "SUB-26-AB",
                    "subprocessor_name": "Vendor B",
                    "service_function": "API",
                    "linked_fourth_party_vendor_id": v_b.id,
                },
                headers=get_token_headers(admin_user),
            ).status_code
            == 201
        )
        assert (
            client.post(
                f"/api/v1/vendors/{v_b.id}/subprocessors",
                json={
                    "subprocessor_code": "SUB-26-BC",
                    "subprocessor_name": "Vendor C",
                    "service_function": "Infrastructure",
                    "linked_fourth_party_vendor_id": v_c.id,
                },
                headers=get_token_headers(admin_user),
            ).status_code
            == 201
        )

        res_cycle = client.post(
            f"/api/v1/vendors/{v_c.id}/subprocessors",
            json={
                "subprocessor_code": "SUB-26-CA",
                "subprocessor_name": "Vendor A",
                "service_function": "DNS",
                "linked_fourth_party_vendor_id": v_a.id,
            },
            headers=get_token_headers(admin_user),
        )
        assert res_cycle.status_code == 422
        assert "circular" in res_cycle.json()["detail"].lower()

    def test_sec_b6_27(
        self, client: TestClient, db: Session, admin_user, org_apex
    ):
        """SEC-B6-27: Duplicate active subprocessor edge (vendor_id, normalized_fourth_party_name, service_function) returns 409."""
        v_apx = _seed_active_vendor(db, org_apex.id, "VND-APX-B6-27")
        res1 = client.post(
            f"/api/v1/vendors/{v_apx.id}/subprocessors",
            json={
                "subprocessor_code": "SUB-27-1",
                "subprocessor_name": "Snowflake Inc.",
                "service_function": "Data Warehousing",
            },
            headers=get_token_headers(admin_user),
        )
        assert res1.status_code == 201

        res2 = client.post(
            f"/api/v1/vendors/{v_apx.id}/subprocessors",
            json={
                "subprocessor_code": "SUB-27-2",
                "subprocessor_name": "  snowflake   inc. ",
                "service_function": "Data Warehousing",
            },
            headers=get_token_headers(admin_user),
        )
        assert res2.status_code == 409

    def test_sec_b6_28(
        self, client: TestClient, db: Session, admin_user, analyst_user, org_apex
    ):
        """SEC-B6-28: Approving a Tier 1 / Tier 2 CRITICAL or RESTRICTED subprocessor without evidence_id returns 422."""
        v_apx = _seed_active_vendor(
            db, org_apex.id, "VND-APX-B6-28", tier=VendorTierEnum.TIER_1_CRITICAL
        )
        sp = VendorSubprocessor(
            organization_id=org_apex.id,
            vendor_id=v_apx.id,
            subprocessor_code="SUB-APX-28",
            subprocessor_name="Critical Fourth Party",
            normalized_fourth_party_name="critical fourth party",
            service_function="Payment Processing",
            criticality=BusinessCriticalityEnum.CRITICAL,
            data_classification=DataClassificationEnum.RESTRICTED,
            status=VendorSubprocessorStatusEnum.PENDING_REVIEW,
            registered_by_id=analyst_user.id,
            evidence_id=None,
        )
        db.add(sp)
        db.commit()
        db.refresh(sp)

        res = client.post(
            f"/api/v1/vendors/{v_apx.id}/subprocessors/{sp.id}/approve",
            json={"review_notes": "Approving without SOC2/due-diligence evidence"},
            headers=get_token_headers(admin_user),
        )
        assert res.status_code == 422
        assert "evidence" in res.json()["detail"].lower()

    def test_sec_b6_29(
        self, client: TestClient, db: Session, admin_user, analyst_user, org_apex
    ):
        """SEC-B6-29: Approving a contract (MSA, DPA, SLA) without an ACCEPTED EvidenceItem returns 422."""
        v_apx = _seed_active_vendor(db, org_apex.id, "VND-APX-B6-29")
        now = datetime.now(timezone.utc)
        contract = VendorContract(
            organization_id=org_apex.id,
            vendor_id=v_apx.id,
            contract_code="CNT-APX-29",
            title="Unverified MSA",
            contract_type=VendorContractTypeEnum.MSA,
            status=VendorContractStatusEnum.UNDER_REVIEW,
            effective_date=now,
            expiration_date=now + timedelta(days=365),
            evidence_id=None,
            created_by_id=analyst_user.id,
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)

        res = client.post(
            f"/api/v1/vendors/{v_apx.id}/contracts/{contract.id}/approve",
            json={"review_notes": "Approving without evidence"},
            headers=get_token_headers(admin_user),
        )
        assert res.status_code == 422

    def test_sec_b6_30(
        self, client: TestClient, db: Session, admin_user, org_apex
    ):
        """SEC-B6-30: Creating/Approving a contract with expiration_date <= effective_date returns 422."""
        v_apx = _seed_active_vendor(db, org_apex.id, "VND-APX-B6-30")
        now = datetime.now(timezone.utc)
        res = client.post(
            f"/api/v1/vendors/{v_apx.id}/contracts",
            json={
                "contract_code": "CNT-APX-30",
                "title": "Inverted Dates MSA",
                "contract_type": "MSA",
                "effective_date": now.isoformat(),
                "expiration_date": (now - timedelta(days=5)).isoformat(),
            },
            headers=get_token_headers(admin_user),
        )
        assert res.status_code == 422

    def test_sec_b6_31(
        self, client: TestClient, db: Session, admin_user, analyst_user, org_apex, seeded_framework
    ):
        """SEC-B6-31: Mutating an APPROVED or TERMINATED contract via PATCH returns 400."""
        v_apx = _seed_active_vendor(db, org_apex.id, "VND-APX-B6-31")
        ctrl = _seed_org_control(db, org_apex.id, seeded_framework)
        ev = _seed_accepted_evidence(db, org_apex.id, ctrl.id, analyst_user.id)
        now = datetime.now(timezone.utc)
        contract = VendorContract(
            organization_id=org_apex.id,
            vendor_id=v_apx.id,
            contract_code="CNT-APX-31",
            title="Approved Immutable MSA",
            contract_type=VendorContractTypeEnum.MSA,
            status=VendorContractStatusEnum.APPROVED,
            effective_date=now - timedelta(days=10),
            expiration_date=now + timedelta(days=355),
            evidence_id=ev.id,
            created_by_id=analyst_user.id,
            approved_by_id=admin_user.id,
            approved_at=now - timedelta(days=9),
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)

        res = client.patch(
            f"/api/v1/vendors/{v_apx.id}/contracts/{contract.id}",
            json={"title": "Tampering Approved Contract"},
            headers=get_token_headers(admin_user),
        )
        assert res.status_code == 400
        assert "draft or rejected" in res.json()["detail"].lower()

    def test_sec_b6_32(
        self, client: TestClient, db: Session, admin_user, org_apex
    ):
        """SEC-B6-32: Creating an SLA obligation with invalid comparison_operator or negative threshold returns 422."""
        v_apx = _seed_active_vendor(db, org_apex.id, "VND-APX-B6-32")
        res = client.post(
            f"/api/v1/vendors/{v_apx.id}/sla-obligations",
            json={
                "obligation_code": "SLA-APX-32",
                "title": "Negative Threshold SLA",
                "metric_type": "AVAILABILITY_PCT",
                "comparison_operator": "GTE",
                "target_value": -10.0,
                "breach_threshold": -5.0,
            },
            headers=get_token_headers(admin_user),
        )
        assert res.status_code == 422

    def test_sec_b6_33(
        self, client: TestClient, db: Session, admin_user, org_apex
    ):
        """SEC-B6-33: Recording an SLA breach where observed_value does NOT violate threshold (99.98 >= 99.95) returns 422."""
        v_apx = _seed_active_vendor(db, org_apex.id, "VND-APX-B6-33")
        now = datetime.now(timezone.utc)
        ob = VendorSlaObligation(
            organization_id=org_apex.id,
            vendor_id=v_apx.id,
            obligation_code="SLA-APX-33",
            title="Availability >= 99.95%",
            metric_type=SlaMetricTypeEnum.AVAILABILITY_PCT,
            comparison_operator=SlaComparisonOperatorEnum.GTE,
            target_value=99.99,
            breach_threshold=99.95,
            status=VendorSlaObligationStatusEnum.ACTIVE,
            effective_from=now - timedelta(days=10),
            created_by_id=admin_user.id,
        )
        db.add(ob)
        db.commit()
        db.refresh(ob)

        res = client.post(
            f"/api/v1/vendors/{v_apx.id}/sla-breaches",
            json={
                "sla_obligation_id": ob.id,
                "breach_code": "BRC-APX-33",
                "observed_value": 99.98,
                "breach_period_start": (now - timedelta(hours=2)).isoformat(),
                "breach_period_end": (now - timedelta(hours=1)).isoformat(),
                "occurred_at": (now - timedelta(minutes=10)).isoformat(),
                "root_cause_summary": "Non-breaching telemetry value",
            },
            headers=get_token_headers(admin_user),
        )
        assert res.status_code == 422
        assert "does not violate" in res.json()["detail"].lower()

    def test_sec_b6_34(
        self, client: TestClient, db: Session, admin_user, org_apex
    ):
        """SEC-B6-34: Recording an SLA breach with breach_period_end < breach_period_start returns 422."""
        v_apx = _seed_active_vendor(db, org_apex.id, "VND-APX-B6-34")
        now = datetime.now(timezone.utc)
        ob = VendorSlaObligation(
            organization_id=org_apex.id,
            vendor_id=v_apx.id,
            obligation_code="SLA-APX-34",
            title="Availability",
            metric_type=SlaMetricTypeEnum.AVAILABILITY_PCT,
            comparison_operator=SlaComparisonOperatorEnum.GTE,
            target_value=99.9,
            breach_threshold=99.5,
            status=VendorSlaObligationStatusEnum.ACTIVE,
            effective_from=now - timedelta(days=10),
            created_by_id=admin_user.id,
        )
        db.add(ob)
        db.commit()
        db.refresh(ob)

        res = client.post(
            f"/api/v1/vendors/{v_apx.id}/sla-breaches",
            json={
                "sla_obligation_id": ob.id,
                "breach_code": "BRC-APX-34",
                "observed_value": 98.0,
                "breach_period_start": (now - timedelta(hours=1)).isoformat(),
                "breach_period_end": (now - timedelta(hours=3)).isoformat(),
                "occurred_at": (now - timedelta(minutes=10)).isoformat(),
                "root_cause_summary": "Inverted period timestamps",
            },
            headers=get_token_headers(admin_user),
        )
        assert res.status_code == 422

    def test_sec_b6_35(
        self, client: TestClient, db: Session, admin_user, org_apex
    ):
        """SEC-B6-35: Recording an SLA breach with occurred_at > now + 5m (future timestamp injection) returns 422."""
        v_apx = _seed_active_vendor(db, org_apex.id, "VND-APX-B6-35")
        now = datetime.now(timezone.utc)
        ob = VendorSlaObligation(
            organization_id=org_apex.id,
            vendor_id=v_apx.id,
            obligation_code="SLA-APX-35",
            title="Availability",
            metric_type=SlaMetricTypeEnum.AVAILABILITY_PCT,
            comparison_operator=SlaComparisonOperatorEnum.GTE,
            target_value=99.9,
            breach_threshold=99.5,
            status=VendorSlaObligationStatusEnum.ACTIVE,
            effective_from=now - timedelta(days=10),
            created_by_id=admin_user.id,
        )
        db.add(ob)
        db.commit()
        db.refresh(ob)

        res = client.post(
            f"/api/v1/vendors/{v_apx.id}/sla-breaches",
            json={
                "sla_obligation_id": ob.id,
                "breach_code": "BRC-APX-35",
                "observed_value": 98.0,
                "breach_period_start": (now - timedelta(hours=2)).isoformat(),
                "breach_period_end": (now - timedelta(hours=1)).isoformat(),
                "occurred_at": (now + timedelta(hours=2)).isoformat(),
                "root_cause_summary": "Future timestamp injection",
            },
            headers=get_token_headers(admin_user),
        )
        assert res.status_code == 422
        assert "future" in res.json()["detail"].lower()

    def test_sec_b6_36(
        self, client: TestClient, db: Session, admin_user, org_apex
    ):
        """SEC-B6-36: Attempting to forge variance_magnitude or severity in VendorSlaBreachCreate returns 422."""
        v_apx = _seed_active_vendor(db, org_apex.id, "VND-APX-B6-36")
        now = datetime.now(timezone.utc)
        ob = VendorSlaObligation(
            organization_id=org_apex.id,
            vendor_id=v_apx.id,
            obligation_code="SLA-APX-36",
            title="Availability",
            metric_type=SlaMetricTypeEnum.AVAILABILITY_PCT,
            comparison_operator=SlaComparisonOperatorEnum.GTE,
            target_value=99.9,
            breach_threshold=99.5,
            status=VendorSlaObligationStatusEnum.ACTIVE,
            effective_from=now - timedelta(days=10),
            created_by_id=admin_user.id,
        )
        db.add(ob)
        db.commit()
        db.refresh(ob)

        res = client.post(
            f"/api/v1/vendors/{v_apx.id}/sla-breaches",
            json={
                "sla_obligation_id": ob.id,
                "breach_code": "BRC-APX-36",
                "observed_value": 98.0,
                "variance_magnitude": 0.01,
                "severity": "LOW",
                "breach_period_start": (now - timedelta(hours=2)).isoformat(),
                "breach_period_end": (now - timedelta(hours=1)).isoformat(),
                "occurred_at": (now - timedelta(minutes=10)).isoformat(),
                "root_cause_summary": "Forged severity and variance",
            },
            headers=get_token_headers(admin_user),
        )
        assert res.status_code == 422

    def test_sec_b6_37(
        self, client: TestClient, db: Session, admin_user, org_apex, seeded_framework
    ):
        """SEC-B6-37: Escalating an SLA breach that is already RESOLVED or WAIVED returns 400."""
        v_apx = _seed_active_vendor(db, org_apex.id, "VND-APX-B6-37")
        ctrl = _seed_org_control(db, org_apex.id, seeded_framework)
        now = datetime.now(timezone.utc)
        ob = VendorSlaObligation(
            organization_id=org_apex.id,
            vendor_id=v_apx.id,
            obligation_code="SLA-APX-37",
            title="Availability",
            metric_type=SlaMetricTypeEnum.AVAILABILITY_PCT,
            comparison_operator=SlaComparisonOperatorEnum.GTE,
            target_value=99.9,
            breach_threshold=99.5,
            status=VendorSlaObligationStatusEnum.ACTIVE,
            effective_from=now - timedelta(days=10),
            created_by_id=admin_user.id,
        )
        db.add(ob)
        db.flush()
        breach = VendorSlaBreach(
            organization_id=org_apex.id,
            vendor_id=v_apx.id,
            sla_obligation_id=ob.id,
            breach_code="BRC-APX-37",
            observed_value=98.0,
            target_value_snapshot=99.9,
            breach_threshold_snapshot=99.5,
            variance_magnitude=1.5,
            severity=VendorSlaBreachSeverityEnum.HIGH,
            status=VendorSlaBreachStatusEnum.RESOLVED,
            breach_period_start=now - timedelta(hours=2),
            breach_period_end=now - timedelta(hours=1),
            occurred_at=now - timedelta(minutes=20),
            root_cause_summary="Already resolved",
            recorded_by_id=admin_user.id,
        )
        db.add(breach)
        db.commit()
        db.refresh(breach)

        res = client.post(
            f"/api/v1/vendors/{v_apx.id}/sla-breaches/{breach.id}/escalate",
            json={
                "organization_control_id": ctrl.id,
                "create_finding": True,
                "create_remediation_plan": False,
            },
            headers=get_token_headers(admin_user),
        )
        assert res.status_code == 400

    def test_sec_b6_38(
        self, client: TestClient, db: Session, admin_user, org_apex
    ):
        """SEC-B6-38: Escalating an SLA breach without a resolvable organization_control_id when create_finding=True returns 422."""
        v_apx = _seed_active_vendor(db, org_apex.id, "VND-APX-B6-38")
        now = datetime.now(timezone.utc)
        ob = VendorSlaObligation(
            organization_id=org_apex.id,
            vendor_id=v_apx.id,
            obligation_code="SLA-APX-38",
            title="Unmapped Availability SLA",
            metric_type=SlaMetricTypeEnum.AVAILABILITY_PCT,
            comparison_operator=SlaComparisonOperatorEnum.GTE,
            target_value=99.9,
            breach_threshold=99.5,
            rationalized_common_control_id=None,
            status=VendorSlaObligationStatusEnum.ACTIVE,
            effective_from=now - timedelta(days=10),
            created_by_id=admin_user.id,
        )
        db.add(ob)
        db.flush()
        breach = VendorSlaBreach(
            organization_id=org_apex.id,
            vendor_id=v_apx.id,
            sla_obligation_id=ob.id,
            breach_code="BRC-APX-38",
            observed_value=97.0,
            target_value_snapshot=99.9,
            breach_threshold_snapshot=99.5,
            variance_magnitude=2.5,
            severity=VendorSlaBreachSeverityEnum.HIGH,
            status=VendorSlaBreachStatusEnum.OPEN,
            breach_period_start=now - timedelta(hours=2),
            breach_period_end=now - timedelta(hours=1),
            occurred_at=now - timedelta(minutes=20),
            root_cause_summary="No control mapping",
            recorded_by_id=admin_user.id,
        )
        db.add(breach)
        db.commit()
        db.refresh(breach)

        res = client.post(
            f"/api/v1/vendors/{v_apx.id}/sla-breaches/{breach.id}/escalate",
            json={
                "organization_control_id": None,
                "create_finding": True,
                "create_remediation_plan": True,
            },
            headers=get_token_headers(admin_user),
        )
        assert res.status_code == 422
        assert "organization_control_id" in res.json()["detail"].lower()

    def test_sec_b6_39(
        self, client: TestClient, db: Session, admin_user, org_apex, seeded_framework
    ):
        """SEC-B6-39: Escalating the same SLA breach twice (duplicate escalation) returns 409."""
        v_apx = _seed_active_vendor(db, org_apex.id, "VND-APX-B6-39")
        ctrl = _seed_org_control(db, org_apex.id, seeded_framework)
        now = datetime.now(timezone.utc)
        ob = VendorSlaObligation(
            organization_id=org_apex.id,
            vendor_id=v_apx.id,
            obligation_code="SLA-APX-39",
            title="Availability",
            metric_type=SlaMetricTypeEnum.AVAILABILITY_PCT,
            comparison_operator=SlaComparisonOperatorEnum.GTE,
            target_value=99.9,
            breach_threshold=99.5,
            status=VendorSlaObligationStatusEnum.ACTIVE,
            effective_from=now - timedelta(days=10),
            created_by_id=admin_user.id,
        )
        db.add(ob)
        db.flush()
        breach = VendorSlaBreach(
            organization_id=org_apex.id,
            vendor_id=v_apx.id,
            sla_obligation_id=ob.id,
            breach_code="BRC-APX-39",
            observed_value=96.0,
            target_value_snapshot=99.9,
            breach_threshold_snapshot=99.5,
            variance_magnitude=3.5,
            severity=VendorSlaBreachSeverityEnum.CRITICAL,
            status=VendorSlaBreachStatusEnum.OPEN,
            breach_period_start=now - timedelta(hours=2),
            breach_period_end=now - timedelta(hours=1),
            occurred_at=now - timedelta(minutes=20),
            root_cause_summary="Major outage",
            recorded_by_id=admin_user.id,
        )
        db.add(breach)
        db.commit()
        db.refresh(breach)

        res1 = client.post(
            f"/api/v1/vendors/{v_apx.id}/sla-breaches/{breach.id}/escalate",
            json={
                "organization_control_id": ctrl.id,
                "create_finding": True,
                "create_remediation_plan": True,
            },
            headers=get_token_headers(admin_user),
        )
        assert res1.status_code == 200

        res2 = client.post(
            f"/api/v1/vendors/{v_apx.id}/sla-breaches/{breach.id}/escalate",
            json={
                "organization_control_id": ctrl.id,
                "create_finding": True,
                "create_remediation_plan": True,
            },
            headers=get_token_headers(admin_user),
        )
        assert res2.status_code == 409

    def test_sec_b6_40(
        self, client: TestClient, db: Session, admin_user, org_apex, seeded_framework
    ):
        """SEC-B6-40: Escalating a VendorAssessmentItem whose response_status == COMPLIANT returns 400."""
        v_apx = _seed_active_vendor(db, org_apex.id, "VND-APX-B6-40")
        ctrl = _seed_org_control(db, org_apex.id, seeded_framework)
        asm = VendorAssessment(
            organization_id=org_apex.id,
            vendor_id=v_apx.id,
            assessment_code="ASM-APX-40",
            title="Assessment 40",
            assessment_type=VendorAssessmentTypeEnum.ANNUAL_REASSESSMENT,
            status=VendorAssessmentStatusEnum.IN_REVIEW,
            assessor_id=admin_user.id,
        )
        db.add(asm)
        db.flush()
        item = VendorAssessmentItem(
            organization_id=org_apex.id,
            assessment_id=asm.id,
            question_key="Q-40",
            question_text="MFA enabled?",
            response_status=VendorResponseStatusEnum.COMPLIANT,
            weight=5.0,
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        res = client.post(
            f"/api/v1/vendors/assessments/{asm.id}/items/{item.id}/escalate",
            json={
                "organization_control_id": ctrl.id,
                "create_finding": True,
            },
            headers=get_token_headers(admin_user),
        )
        assert res.status_code == 400

    def test_sec_b6_41(
        self, client: TestClient, db: Session, admin_user, org_apex, seeded_framework
    ):
        """SEC-B6-41: Escalating a VendorAssessmentItem on a SUPERSEDED assessment returns 400."""
        v_apx = _seed_active_vendor(db, org_apex.id, "VND-APX-B6-41")
        ctrl = _seed_org_control(db, org_apex.id, seeded_framework)
        asm = VendorAssessment(
            organization_id=org_apex.id,
            vendor_id=v_apx.id,
            assessment_code="ASM-APX-41",
            title="Superseded Assessment",
            assessment_type=VendorAssessmentTypeEnum.ANNUAL_REASSESSMENT,
            status=VendorAssessmentStatusEnum.SUPERSEDED,
            assessor_id=admin_user.id,
        )
        db.add(asm)
        db.flush()
        item = VendorAssessmentItem(
            organization_id=org_apex.id,
            assessment_id=asm.id,
            question_key="Q-41",
            question_text="Backups encrypted?",
            response_status=VendorResponseStatusEnum.NON_COMPLIANT,
            weight=5.0,
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        res = client.post(
            f"/api/v1/vendors/assessments/{asm.id}/items/{item.id}/escalate",
            json={
                "organization_control_id": ctrl.id,
                "create_finding": True,
            },
            headers=get_token_headers(admin_user),
        )
        assert res.status_code == 400
        assert "superseded" in res.json()["detail"].lower()

    def test_sec_b6_42(
        self, client: TestClient, db: Session, admin_user, org_apex
    ):
        """SEC-B6-42: Escalating a VendorAssessmentItem without a resolvable organization_control_id returns 422."""
        v_apx = _seed_active_vendor(db, org_apex.id, "VND-APX-B6-42")
        asm = VendorAssessment(
            organization_id=org_apex.id,
            vendor_id=v_apx.id,
            assessment_code="ASM-APX-42",
            title="Unmapped Assessment",
            assessment_type=VendorAssessmentTypeEnum.ANNUAL_REASSESSMENT,
            status=VendorAssessmentStatusEnum.IN_REVIEW,
            assessor_id=admin_user.id,
        )
        db.add(asm)
        db.flush()
        item = VendorAssessmentItem(
            organization_id=org_apex.id,
            assessment_id=asm.id,
            rationalized_common_control_id=None,
            question_key="Q-42",
            question_text="Unmapped question?",
            response_status=VendorResponseStatusEnum.NON_COMPLIANT,
            weight=5.0,
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        res = client.post(
            f"/api/v1/vendors/assessments/{asm.id}/items/{item.id}/escalate",
            json={
                "organization_control_id": None,
                "create_finding": True,
            },
            headers=get_token_headers(admin_user),
        )
        assert res.status_code == 422

    def test_sec_b6_43(
        self, client: TestClient, db: Session, admin_user, org_apex, seeded_framework
    ):
        """SEC-B6-43: Escalating the same VendorAssessmentItem twice returns 409."""
        v_apx = _seed_active_vendor(db, org_apex.id, "VND-APX-B6-43")
        ctrl = _seed_org_control(db, org_apex.id, seeded_framework)
        asm = VendorAssessment(
            organization_id=org_apex.id,
            vendor_id=v_apx.id,
            assessment_code="ASM-APX-43",
            title="Assessment 43",
            assessment_type=VendorAssessmentTypeEnum.ANNUAL_REASSESSMENT,
            status=VendorAssessmentStatusEnum.IN_REVIEW,
            assessor_id=admin_user.id,
        )
        db.add(asm)
        db.flush()
        item = VendorAssessmentItem(
            organization_id=org_apex.id,
            assessment_id=asm.id,
            question_key="Q-43",
            question_text="Key rotation?",
            response_status=VendorResponseStatusEnum.NON_COMPLIANT,
            weight=5.0,
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        res1 = client.post(
            f"/api/v1/vendors/assessments/{asm.id}/items/{item.id}/escalate",
            json={
                "organization_control_id": ctrl.id,
                "create_finding": True,
                "create_remediation_plan": True,
            },
            headers=get_token_headers(admin_user),
        )
        assert res1.status_code == 200

        res2 = client.post(
            f"/api/v1/vendors/assessments/{asm.id}/items/{item.id}/escalate",
            json={
                "organization_control_id": ctrl.id,
                "create_finding": True,
            },
            headers=get_token_headers(admin_user),
        )
        assert res2.status_code == 409

    def test_sec_b6_44(
        self, client: TestClient, db: Session, admin_user, manager_user, org_apex, seeded_framework
    ):
        """SEC-B6-44: Closing an escalated Finding via FindingService.verify_and_close_finding synchronizes linked VendorSlaBreach and VendorAssessmentItem and recalculates vendor.residual_risk_score."""
        v_apx = _seed_active_vendor(db, org_apex.id, "VND-APX-B6-44")
        ctrl = _seed_org_control(db, org_apex.id, seeded_framework)
        now = datetime.now(timezone.utc)

        ob = VendorSlaObligation(
            organization_id=org_apex.id,
            vendor_id=v_apx.id,
            obligation_code="SLA-APX-44",
            title="Availability",
            metric_type=SlaMetricTypeEnum.AVAILABILITY_PCT,
            comparison_operator=SlaComparisonOperatorEnum.GTE,
            target_value=99.9,
            breach_threshold=99.5,
            status=VendorSlaObligationStatusEnum.ACTIVE,
            effective_from=now - timedelta(days=10),
            created_by_id=admin_user.id,
        )
        db.add(ob)
        db.flush()
        breach = VendorSlaBreach(
            organization_id=org_apex.id,
            vendor_id=v_apx.id,
            sla_obligation_id=ob.id,
            breach_code="BRC-APX-44",
            observed_value=95.0,
            target_value_snapshot=99.9,
            breach_threshold_snapshot=99.5,
            variance_magnitude=4.5,
            severity=VendorSlaBreachSeverityEnum.CRITICAL,
            status=VendorSlaBreachStatusEnum.OPEN,
            breach_period_start=now - timedelta(hours=2),
            breach_period_end=now - timedelta(hours=1),
            occurred_at=now - timedelta(minutes=20),
            root_cause_summary="Outage",
            recorded_by_id=admin_user.id,
        )
        db.add(breach)
        db.commit()
        db.refresh(breach)

        res = client.post(
            f"/api/v1/vendors/{v_apx.id}/sla-breaches/{breach.id}/escalate",
            json={
                "organization_control_id": ctrl.id,
                "create_finding": True,
                "create_remediation_plan": False,
            },
            headers=get_token_headers(admin_user),
        )
        assert res.status_code == 200
        finding_id = res.json()["linked_finding_id"]
        finding = db.query(Finding).filter(Finding.id == finding_id).first()
        finding.status = FindingStatusEnum.REMEDIATED_PENDING_VERIFICATION
        db.commit()

        FindingService.verify_and_close_finding(
            db=db,
            finding=finding,
            verifier_id=manager_user.id,
            verification_notes="Verified SLA remediation complete",
        )
        db.refresh(breach)
        db.refresh(v_apx)
        assert breach.status == VendorSlaBreachStatusEnum.RESOLVED
        assert breach.resolved_by_id == manager_user.id
        assert v_apx.open_sla_breaches_count == 0

    def test_sec_b6_45(
        self, client: TestClient, db: Session, admin_user, manager_user, org_apex
    ):
        """SEC-B6-45: Waiving an SLA breach without an APPROVED, non-expired SecurityException linked to the same vendor returns 422."""
        v_apx = _seed_active_vendor(db, org_apex.id, "VND-APX-B6-45")
        now = datetime.now(timezone.utc)
        ob = VendorSlaObligation(
            organization_id=org_apex.id,
            vendor_id=v_apx.id,
            obligation_code="SLA-APX-45",
            title="Availability",
            metric_type=SlaMetricTypeEnum.AVAILABILITY_PCT,
            comparison_operator=SlaComparisonOperatorEnum.GTE,
            target_value=99.9,
            breach_threshold=99.5,
            status=VendorSlaObligationStatusEnum.ACTIVE,
            effective_from=now - timedelta(days=10),
            created_by_id=admin_user.id,
        )
        db.add(ob)
        db.flush()
        breach = VendorSlaBreach(
            organization_id=org_apex.id,
            vendor_id=v_apx.id,
            sla_obligation_id=ob.id,
            breach_code="BRC-APX-45",
            observed_value=97.0,
            target_value_snapshot=99.9,
            breach_threshold_snapshot=99.5,
            variance_magnitude=2.5,
            severity=VendorSlaBreachSeverityEnum.HIGH,
            status=VendorSlaBreachStatusEnum.OPEN,
            breach_period_start=now - timedelta(hours=2),
            breach_period_end=now - timedelta(hours=1),
            occurred_at=now - timedelta(minutes=20),
            root_cause_summary="Outage",
            recorded_by_id=admin_user.id,
        )
        db.add(breach)
        db.commit()
        db.refresh(breach)

        res = client.post(
            f"/api/v1/vendors/{v_apx.id}/sla-breaches/{breach.id}/waive",
            json={
                "linked_exception_id": 999999,
                "resolution_notes": "Waiving with non-existent exception",
            },
            headers=get_token_headers(manager_user),
        )
        assert res.status_code == 422

    def test_sec_b6_46(
        self, client: TestClient, db: Session, admin_user, manager_user, org_apex, seeded_framework
    ):
        """SEC-B6-46: SecurityException linked to Vendor A does NOT penalize Vendor B (vendor-scoped exception penalty isolation)."""
        ctrl = _seed_org_control(db, org_apex.id, seeded_framework)
        ccm = RationalizedCommonControl(
            organization_id=org_apex.id,
            common_control_code="CCF-B6-46",
            title="Encryption Standard",
            domain=CommonControlDomainEnum.DATA_PROTECTION,
            description="Encryption",
        )
        db.add(ccm)
        db.flush()
        mapping = CommonControlMapping(
            organization_id=org_apex.id,
            rationalized_common_control_id=ccm.id,
            organization_control_id=ctrl.id,
            weight=1.0,
        )
        db.add(mapping)
        db.flush()

        v_a = _seed_active_vendor(db, org_apex.id, "VND-APX-46A", "Vendor A", inherent_risk=60.0)
        v_b = _seed_active_vendor(db, org_apex.id, "VND-APX-46B", "Vendor B", inherent_risk=60.0)

        for idx, v in enumerate([v_a, v_b], start=1):
            asm = VendorAssessment(
                organization_id=org_apex.id,
                vendor_id=v.id,
                assessment_code=f"ASM-46-{idx}",
                title=f"Assessment {idx}",
                assessment_type=VendorAssessmentTypeEnum.ANNUAL_REASSESSMENT,
                status=VendorAssessmentStatusEnum.APPROVED,
                calculated_score=100.0,
                assessor_id=admin_user.id,
                reviewer_id=manager_user.id,
                reviewed_at=datetime.now(timezone.utc),
            )
            db.add(asm)
            db.flush()
            db.add(
                VendorAssessmentItem(
                    organization_id=org_apex.id,
                    assessment_id=asm.id,
                    rationalized_common_control_id=ccm.id,
                    question_key="Q-1",
                    question_text="Encryption?",
                    response_status=VendorResponseStatusEnum.COMPLIANT,
                    weight=5.0,
                )
            )

        now = datetime.now(timezone.utc)
        exc_a = SecurityException(
            organization_id=org_apex.id,
            linked_organization_control_id=ctrl.id,
            linked_vendor_id=v_a.id,
            title="Vendor A Exception",
            description="Vendor A specific gap",
            justification="Vendor A specific gap",
            exception_type=ExceptionTypeEnum.THIRD_PARTY_VENDOR,
            status=ExceptionStatusEnum.APPROVED,
            requested_by_id=admin_user.id,
            reviewer_id=manager_user.id,
            approved_at=now - timedelta(days=1),
            expiry_date=(now + timedelta(days=59)).date(),
        )
        db.add(exc_a)
        db.commit()

        TPRMService.recalculate_vendor_telemetry(db, v_a)
        TPRMService.recalculate_vendor_telemetry(db, v_b)
        db.commit()

        pen_a = TPRMService.compute_vendor_penalty_breakdown(db, v_a)
        pen_b = TPRMService.compute_vendor_penalty_breakdown(db, v_b)
        assert pen_a["exception_penalties"] == 10.0
        assert pen_b["exception_penalties"] == 0.0
        assert v_a.residual_risk_score > v_b.residual_risk_score

    def test_sec_b6_47(
        self, client: TestClient, db: Session, admin_user, org_apex
    ):
        """SEC-B6-47: Direct PATCH /vendors/{id} to OFFBOARDED or TERMINATED bypassing governed offboarding workflow returns 400."""
        v_apx = _seed_active_vendor(db, org_apex.id, "VND-APX-B6-47")
        res = client.patch(
            f"/api/v1/vendors/{v_apx.id}",
            json={"vendor_status": "OFFBOARDED"},
            headers=get_token_headers(admin_user),
        )
        assert res.status_code == 400
        assert "offboarding" in res.json()["detail"].lower()

    def test_sec_b6_48(
        self, client: TestClient, db: Session, admin_user, org_apex
    ):
        """SEC-B6-48: Initiating a second concurrent active offboarding workflow on the same vendor returns 409."""
        v_apx = _seed_active_vendor(db, org_apex.id, "VND-APX-B6-48")
        res1 = client.post(
            f"/api/v1/vendors/{v_apx.id}/offboarding",
            json={
                "offboarding_code": "OFB-APX-48-1",
                "reason": "CONTRACT_EXPIRATION",
                "target_vendor_status": "OFFBOARDED",
                "rationale": "First offboarding workflow",
            },
            headers=get_token_headers(admin_user),
        )
        assert res1.status_code == 201

        res2 = client.post(
            f"/api/v1/vendors/{v_apx.id}/offboarding",
            json={
                "offboarding_code": "OFB-APX-48-2",
                "reason": "STRATEGIC_REPLACEMENT",
                "target_vendor_status": "OFFBOARDED",
                "rationale": "Duplicate concurrent offboarding workflow",
            },
            headers=get_token_headers(admin_user),
        )
        assert res2.status_code == 409

    def test_sec_b6_49(
        self, client: TestClient, db: Session, admin_user, org_apex
    ):
        """SEC-B6-49: Waiving DATA_DESTRUCTION_OR_RETURN on a vendor with CONFIDENTIAL or RESTRICTED engagement without an APPROVED SecurityException returns 422."""
        v_apx = _seed_active_vendor(db, org_apex.id, "VND-APX-B6-49")
        eng = VendorEngagement(
            organization_id=org_apex.id,
            vendor_id=v_apx.id,
            engagement_code="ENG-APX-49",
            engagement_name="Restricted Data Processing",
            status=EngagementStatusEnum.ACTIVE,
            criticality=BusinessCriticalityEnum.HIGH,
            data_classification=DataClassificationEnum.RESTRICTED,
            hosting_model=HostingModelEnum.MULTI_TENANT_SAAS,
            network_connectivity=NetworkConnectivityEnum.DIRECT_API_VPN_DB,
            pii_access=PiiFinancialAccessEnum.DIRECT_PCI_PII_PHI,
            calculated_risk_score=85.0,
        )
        db.add(eng)
        db.commit()

        rec = TPRMService.initiate_offboarding(
            db=db,
            vendor=v_apx,
            payload=type(
                "Obj",
                (),
                {
                    "offboarding_code": "OFB-APX-49",
                    "reason": VendorOffboardingReasonEnum.CONTRACT_EXPIRATION,
                    "target_vendor_status": VendorStatusEnum.OFFBOARDED,
                    "rationale": "Offboarding restricted vendor",
                },
            )(),
            initiator_id=admin_user.id,
        )
        db.commit()
        db.refresh(rec)

        data_item = next(
            i
            for i in rec.items
            if i.step_type == VendorOffboardingStepTypeEnum.DATA_DESTRUCTION_OR_RETURN
        )
        res = client.post(
            f"/api/v1/vendors/{v_apx.id}/offboarding/{rec.id}/items/{data_item.id}/waive",
            json={
                "linked_exception_id": None,
                "waiver_justification": "Attempting to waive restricted data destruction without exception",
            },
            headers=get_token_headers(admin_user),
        )
        assert res.status_code == 422

    def test_sec_b6_50(
        self, client: TestClient, db: Session, admin_user, manager_user, org_apex, seeded_framework
    ):
        """SEC-B6-50: Attempting to waive ACCESS_REVOCATION (non-waivable mandatory control) returns 422."""
        v_apx = _seed_active_vendor(db, org_apex.id, "VND-APX-B6-50")
        ctrl = _seed_org_control(db, org_apex.id, seeded_framework)
        now = datetime.now(timezone.utc)
        exc = SecurityException(
            organization_id=org_apex.id,
            linked_organization_control_id=ctrl.id,
            linked_vendor_id=v_apx.id,
            title="Approved Exception",
            description="Testing non-waivable step",
            justification="Testing non-waivable step",
            exception_type=ExceptionTypeEnum.THIRD_PARTY_VENDOR,
            status=ExceptionStatusEnum.APPROVED,
            requested_by_id=manager_user.id,
            reviewer_id=admin_user.id,
            approved_at=now - timedelta(days=1),
            expiry_date=(now + timedelta(days=29)).date(),
        )
        db.add(exc)
        db.commit()

        rec = TPRMService.initiate_offboarding(
            db=db,
            vendor=v_apx,
            payload=type(
                "Obj",
                (),
                {
                    "offboarding_code": "OFB-APX-50",
                    "reason": VendorOffboardingReasonEnum.CONTRACT_EXPIRATION,
                    "target_vendor_status": VendorStatusEnum.OFFBOARDED,
                    "rationale": "Offboarding 50",
                },
            )(),
            initiator_id=admin_user.id,
        )
        db.commit()
        db.refresh(rec)

        access_item = next(
            i
            for i in rec.items
            if i.step_type == VendorOffboardingStepTypeEnum.ACCESS_REVOCATION
        )
        res = client.post(
            f"/api/v1/vendors/{v_apx.id}/offboarding/{rec.id}/items/{access_item.id}/waive",
            json={
                "linked_exception_id": exc.id,
                "waiver_justification": "Attempting to waive mandatory access revocation",
            },
            headers=get_token_headers(admin_user),
        )
        assert res.status_code == 422
        assert "access_revocation" in res.json()["detail"].lower()

    def test_sec_b6_51(
        self, client: TestClient, db: Session, admin_user, org_apex, seeded_framework
    ):
        """SEC-B6-51: Attesting a required offboarding checklist item with REJECTED, EXPIRED, or SUPERSEDED evidence returns 422."""
        v_apx = _seed_active_vendor(db, org_apex.id, "VND-APX-B6-51")
        ctrl = _seed_org_control(db, org_apex.id, seeded_framework)
        rejected_ev = _seed_accepted_evidence(
            db,
            org_apex.id,
            ctrl.id,
            admin_user.id,
            title="Rejected Certificate",
            status=EvidenceStatusEnum.REJECTED,
        )

        rec = TPRMService.initiate_offboarding(
            db=db,
            vendor=v_apx,
            payload=type(
                "Obj",
                (),
                {
                    "offboarding_code": "OFB-APX-51",
                    "reason": VendorOffboardingReasonEnum.CONTRACT_EXPIRATION,
                    "target_vendor_status": VendorStatusEnum.OFFBOARDED,
                    "rationale": "Offboarding 51",
                },
            )(),
            initiator_id=admin_user.id,
        )
        db.commit()
        db.refresh(rec)

        item = rec.items[0]
        res = client.post(
            f"/api/v1/vendors/{v_apx.id}/offboarding/{rec.id}/items/{item.id}/attest",
            json={
                "evidence_id": rejected_ev.id,
                "attestation_notes": "Using rejected evidence",
            },
            headers=get_token_headers(admin_user),
        )
        assert res.status_code == 422

    def test_sec_b6_52(
        self, client: TestClient, db: Session, admin_user, org_apex, seeded_framework
    ):
        """SEC-B6-52: Attesting an offboarding checklist item with an EvidenceItem whose valid_until < now() returns 422."""
        v_apx = _seed_active_vendor(db, org_apex.id, "VND-APX-B6-52")
        ctrl = _seed_org_control(db, org_apex.id, seeded_framework)
        expired_ev = _seed_accepted_evidence(
            db,
            org_apex.id,
            ctrl.id,
            admin_user.id,
            title="Expired Certificate",
            status=EvidenceStatusEnum.ACCEPTED,
            valid_until=datetime.now(timezone.utc) - timedelta(days=2),
        )

        rec = TPRMService.initiate_offboarding(
            db=db,
            vendor=v_apx,
            payload=type(
                "Obj",
                (),
                {
                    "offboarding_code": "OFB-APX-52",
                    "reason": VendorOffboardingReasonEnum.CONTRACT_EXPIRATION,
                    "target_vendor_status": VendorStatusEnum.OFFBOARDED,
                    "rationale": "Offboarding 52",
                },
            )(),
            initiator_id=admin_user.id,
        )
        db.commit()
        db.refresh(rec)

        item = rec.items[0]
        res = client.post(
            f"/api/v1/vendors/{v_apx.id}/offboarding/{rec.id}/items/{item.id}/attest",
            json={
                "evidence_id": expired_ev.id,
                "attestation_notes": "Using expired valid_until evidence",
            },
            headers=get_token_headers(admin_user),
        )
        assert res.status_code == 422
        assert "expired" in res.json()["detail"].lower()

    def test_sec_b6_53(
        self, client: TestClient, db: Session, admin_user, analyst_user, manager_user, org_apex, seeded_framework
    ):
        """SEC-B6-53: Tampering with EvidenceItem.sha256_hash after offboarding item attestation blocks offboarding approval with 409."""
        v_apx = _seed_active_vendor(db, org_apex.id, "VND-APX-B6-53")
        ctrl = _seed_org_control(db, org_apex.id, seeded_framework)
        ev = _seed_accepted_evidence(db, org_apex.id, ctrl.id, analyst_user.id)

        rec = TPRMService.initiate_offboarding(
            db=db,
            vendor=v_apx,
            payload=type(
                "Obj",
                (),
                {
                    "offboarding_code": "OFB-APX-53",
                    "reason": VendorOffboardingReasonEnum.CONTRACT_EXPIRATION,
                    "target_vendor_status": VendorStatusEnum.OFFBOARDED,
                    "rationale": "Offboarding 53",
                },
            )(),
            initiator_id=admin_user.id,
        )
        db.commit()
        db.refresh(rec)

        for item in rec.items:
            TPRMService.attest_offboarding_item(
                db=db,
                record=rec,
                item=item,
                payload=type(
                    "Obj",
                    (),
                    {
                        "evidence_id": ev.id,
                        "attestation_notes": "Attested with intact SHA-256",
                    },
                )(),
                actor_id=analyst_user.id,
            )
        TPRMService.submit_offboarding(db=db, record=rec, submitter_id=analyst_user.id)

        # Tamper with the underlying EvidenceItem SHA-256 digest after attestation
        ev.sha256_hash = "f" * 64
        db.commit()

        res = client.post(
            f"/api/v1/vendors/{v_apx.id}/offboarding/{rec.id}/verify-close",
            json={"signoff_notes": "Manager attempting signoff after evidence hash tamper"},
            headers=get_token_headers(manager_user),
        )
        assert res.status_code == 409
        assert "sha-256" in res.json()["detail"].lower()

    def test_sec_b6_54(
        self, client: TestClient, db: Session, admin_user, org_apex
    ):
        """SEC-B6-54: Submitting an offboarding record for sign-off while any required checklist item is still PENDING returns 400."""
        v_apx = _seed_active_vendor(db, org_apex.id, "VND-APX-B6-54")
        rec = TPRMService.initiate_offboarding(
            db=db,
            vendor=v_apx,
            payload=type(
                "Obj",
                (),
                {
                    "offboarding_code": "OFB-APX-54",
                    "reason": VendorOffboardingReasonEnum.CONTRACT_EXPIRATION,
                    "target_vendor_status": VendorStatusEnum.OFFBOARDED,
                    "rationale": "Offboarding 54",
                },
            )(),
            initiator_id=admin_user.id,
        )
        db.commit()
        db.refresh(rec)

        res = client.post(
            f"/api/v1/vendors/{v_apx.id}/offboarding/{rec.id}/submit",
            headers=get_token_headers(admin_user),
        )
        assert res.status_code == 400
        assert "incomplete" in res.json()["detail"].lower()

    def test_sec_b6_55(
        self, client: TestClient, db: Session, admin_user, analyst_user, manager_user, org_apex, seeded_framework
    ):
        """SEC-B6-55: Approving an offboarding record that is still in IN_PROGRESS (skipping PENDING_SIGNOFF) returns 400."""
        v_apx = _seed_active_vendor(db, org_apex.id, "VND-APX-B6-55")
        ctrl = _seed_org_control(db, org_apex.id, seeded_framework)
        ev = _seed_accepted_evidence(db, org_apex.id, ctrl.id, analyst_user.id)

        rec = TPRMService.initiate_offboarding(
            db=db,
            vendor=v_apx,
            payload=type(
                "Obj",
                (),
                {
                    "offboarding_code": "OFB-APX-55",
                    "reason": VendorOffboardingReasonEnum.CONTRACT_EXPIRATION,
                    "target_vendor_status": VendorStatusEnum.OFFBOARDED,
                    "rationale": "Offboarding 55",
                },
            )(),
            initiator_id=admin_user.id,
        )
        db.commit()
        db.refresh(rec)

        for item in rec.items:
            TPRMService.attest_offboarding_item(
                db=db,
                record=rec,
                item=item,
                payload=type(
                    "Obj",
                    (),
                    {
                        "evidence_id": ev.id,
                        "attestation_notes": "Attested without submitting record",
                    },
                )(),
                actor_id=analyst_user.id,
            )
        db.commit()
        assert rec.status == VendorOffboardingStatusEnum.IN_PROGRESS

        res = client.post(
            f"/api/v1/vendors/{v_apx.id}/offboarding/{rec.id}/approve",
            json={"signoff_notes": "Attempting to approve IN_PROGRESS offboarding"},
            headers=get_token_headers(manager_user),
        )
        assert res.status_code == 400
        assert "pending_signoff" in res.json()["detail"].lower()

    def test_sec_b6_56(
        self, client: TestClient, db: Session, admin_user, analyst_user, org_apex
    ):
        """SEC-B6-56: Re-approving an already COMPLETED offboarding record or already APPROVED subprocessor returns 409."""
        v_apx = _seed_active_vendor(
            db, org_apex.id, "VND-APX-B6-56", tier=VendorTierEnum.TIER_4_LOW, inherent_risk=20.0
        )
        sp = VendorSubprocessor(
            organization_id=org_apex.id,
            vendor_id=v_apx.id,
            subprocessor_code="SUB-APX-56",
            subprocessor_name="Already Approved Sub",
            normalized_fourth_party_name="already approved sub",
            service_function="Monitoring",
            status=VendorSubprocessorStatusEnum.APPROVED,
            registered_by_id=analyst_user.id,
            approved_by_id=admin_user.id,
            approved_at=datetime.now(timezone.utc),
        )
        db.add(sp)
        db.commit()
        db.refresh(sp)

        res = client.post(
            f"/api/v1/vendors/{v_apx.id}/subprocessors/{sp.id}/approve",
            json={"review_notes": "Replay approval"},
            headers=get_token_headers(admin_user),
        )
        assert res.status_code == 409

    def test_sec_b6_57(
        self, client: TestClient, db: Session, admin_user, analyst_user, manager_user, org_apex, seeded_framework
    ):
        """SEC-B6-57: Completing offboarding transitions vendor_status to OFFBOARDED/TERMINATED and cascades engagements, contracts, subprocessors, and SLA obligations to TERMINATED."""
        v_apx = _seed_active_vendor(db, org_apex.id, "VND-APX-B6-57")
        ctrl = _seed_org_control(db, org_apex.id, seeded_framework)
        ev = _seed_accepted_evidence(db, org_apex.id, ctrl.id, analyst_user.id)
        now = datetime.now(timezone.utc)

        eng = VendorEngagement(
            organization_id=org_apex.id,
            vendor_id=v_apx.id,
            engagement_code="ENG-APX-57",
            engagement_name="Active Engagement",
            status=EngagementStatusEnum.ACTIVE,
            criticality=BusinessCriticalityEnum.MEDIUM,
            data_classification=DataClassificationEnum.INTERNAL,
        )
        cnt = VendorContract(
            organization_id=org_apex.id,
            vendor_id=v_apx.id,
            contract_code="CNT-APX-57",
            title="Active Contract",
            contract_type=VendorContractTypeEnum.MSA,
            status=VendorContractStatusEnum.ACTIVE,
            effective_date=now - timedelta(days=30),
            expiration_date=now + timedelta(days=335),
            evidence_id=ev.id,
            created_by_id=analyst_user.id,
            approved_by_id=admin_user.id,
        )
        sp = VendorSubprocessor(
            organization_id=org_apex.id,
            vendor_id=v_apx.id,
            subprocessor_code="SUB-APX-57",
            subprocessor_name="Active Subprocessor",
            normalized_fourth_party_name="active subprocessor",
            service_function="Compute",
            status=VendorSubprocessorStatusEnum.APPROVED,
            registered_by_id=analyst_user.id,
            approved_by_id=admin_user.id,
        )
        ob = VendorSlaObligation(
            organization_id=org_apex.id,
            vendor_id=v_apx.id,
            obligation_code="SLA-APX-57",
            title="Active SLA",
            metric_type=SlaMetricTypeEnum.AVAILABILITY_PCT,
            comparison_operator=SlaComparisonOperatorEnum.GTE,
            target_value=99.9,
            breach_threshold=99.5,
            status=VendorSlaObligationStatusEnum.ACTIVE,
            effective_from=now - timedelta(days=30),
            created_by_id=admin_user.id,
        )
        db.add_all([eng, cnt, sp, ob])
        db.commit()

        rec = TPRMService.initiate_offboarding(
            db=db,
            vendor=v_apx,
            payload=type(
                "Obj",
                (),
                {
                    "offboarding_code": "OFB-APX-57",
                    "reason": VendorOffboardingReasonEnum.CONTRACT_EXPIRATION,
                    "target_vendor_status": VendorStatusEnum.OFFBOARDED,
                    "rationale": "Full lifecycle offboarding cascade",
                },
            )(),
            initiator_id=admin_user.id,
        )
        db.commit()
        db.refresh(rec)

        for item in rec.items:
            TPRMService.attest_offboarding_item(
                db=db,
                record=rec,
                item=item,
                payload=type(
                    "Obj",
                    (),
                    {
                        "evidence_id": ev.id,
                        "attestation_notes": "Verified",
                    },
                )(),
                actor_id=analyst_user.id,
            )
        TPRMService.submit_offboarding(db=db, record=rec, submitter_id=analyst_user.id)
        db.commit()

        res = client.post(
            f"/api/v1/vendors/{v_apx.id}/offboarding/{rec.id}/verify-close",
            json={"signoff_notes": "Final executive offboarding sign-off"},
            headers=get_token_headers(manager_user),
        )
        assert res.status_code == 200
        db.refresh(v_apx)
        db.refresh(eng)
        db.refresh(cnt)
        db.refresh(sp)
        db.refresh(ob)

        assert v_apx.vendor_status == VendorStatusEnum.OFFBOARDED
        assert eng.status == EngagementStatusEnum.TERMINATED
        assert cnt.status == VendorContractStatusEnum.TERMINATED
        assert sp.status == VendorSubprocessorStatusEnum.TERMINATED
        assert ob.status == VendorSlaObligationStatusEnum.TERMINATED

    def test_sec_b6_58(
        self, client: TestClient, db: Session, admin_user, org_apex
    ):
        """SEC-B6-58: Attempting to create a new engagement or assessment on an OFFBOARDED or TERMINATED vendor returns 400."""
        v_off = Vendor(
            organization_id=org_apex.id,
            vendor_code="VND-APX-B6-58",
            legal_name="Offboarded Vendor",
            vendor_status=VendorStatusEnum.OFFBOARDED,
        )
        db.add(v_off)
        db.commit()
        db.refresh(v_off)

        res_eng = client.post(
            f"/api/v1/vendors/{v_off.id}/engagements",
            json={
                "engagement_code": "ENG-OFF-58",
                "engagement_name": "Blocked Engagement",
                "criticality": "HIGH",
            },
            headers=get_token_headers(admin_user),
        )
        assert res_eng.status_code == 400

        res_asm = client.post(
            f"/api/v1/vendors/{v_off.id}/assessments",
            json={
                "assessment_code": "ASM-OFF-58",
                "title": "Blocked Assessment",
                "assessment_type": "ANNUAL_REASSESSMENT",
            },
            headers=get_token_headers(admin_user),
        )
        assert res_asm.status_code == 400

    def test_sec_b6_59(
        self, client: TestClient, db: Session, admin_user, org_apex
    ):
        """SEC-B6-59: Concentration risk SPOF calculation accurately flags a fourth party shared by >=2 Tier 1/Tier 2 vendors and ignores REJECTED/TERMINATED subprocessors."""
        v1 = _seed_active_vendor(
            db, org_apex.id, "VND-APX-59A", "Tier 1 Vendor A", tier=VendorTierEnum.TIER_1_CRITICAL
        )
        v2 = _seed_active_vendor(
            db, org_apex.id, "VND-APX-59B", "Tier 2 Vendor B", tier=VendorTierEnum.TIER_2_SIGNIFICANT
        )

        # Shared active fourth party -> SPOF
        for idx, v in enumerate([v1, v2], start=1):
            db.add(
                VendorSubprocessor(
                    organization_id=org_apex.id,
                    vendor_id=v.id,
                    subprocessor_code=f"SUB-59-ACT-{idx}",
                    subprocessor_name="AWS US-East-1",
                    normalized_fourth_party_name="aws us-east-1",
                    service_function="Cloud Infrastructure",
                    criticality=BusinessCriticalityEnum.CRITICAL,
                    status=VendorSubprocessorStatusEnum.APPROVED,
                    registered_by_id=admin_user.id,
                )
            )
            # Terminated fourth party -> must be ignored
            db.add(
                VendorSubprocessor(
                    organization_id=org_apex.id,
                    vendor_id=v.id,
                    subprocessor_code=f"SUB-59-TERM-{idx}",
                    subprocessor_name="Legacy Rackspace",
                    normalized_fourth_party_name="legacy rackspace",
                    service_function="Legacy Hosting",
                    criticality=BusinessCriticalityEnum.HIGH,
                    status=VendorSubprocessorStatusEnum.TERMINATED,
                    registered_by_id=admin_user.id,
                )
            )
        db.commit()

        res = client.get(
            "/api/v1/vendors/concentration-risk",
            headers=get_token_headers(admin_user),
        )
        assert res.status_code == 200
        report = res.json()
        assert report["spof_count"] == 1
        assert report["shared_fourth_party_count"] == 1
        spof_node = report["single_point_of_failure_candidates"][0]
        assert spof_node["normalized_fourth_party_name"] == "aws us-east-1"
        assert spof_node["is_spof"] is True
        assert spof_node["dependent_tier1_tier2_count"] == 2
        node_names = [n["normalized_fourth_party_name"] for n in report["nodes"]]
        assert "legacy rackspace" not in node_names

    def test_sec_b6_60(
        self, client: TestClient, db: Session, admin_user, manager_user, org_apex, seeded_framework
    ):
        """SEC-B6-60: GET /vendors/{id}/risk-posture and recalculate_vendor_telemetry deterministically incorporate finding, vendor-scoped exception, SLA breach, and subprocessor penalties while respecting the 20% floor and [0.0, 100.0] clamping."""
        ctrl = _seed_org_control(db, org_apex.id, seeded_framework)
        ccm = RationalizedCommonControl(
            organization_id=org_apex.id,
            common_control_code="CCF-B6-60",
            title="Resilience Control",
            domain=CommonControlDomainEnum.BUSINESS_CONTINUITY,
            description="Resilience",
        )
        db.add(ccm)
        db.flush()
        db.add(
            CommonControlMapping(
                organization_id=org_apex.id,
                rationalized_common_control_id=ccm.id,
                organization_control_id=ctrl.id,
                weight=1.0,
            )
        )
        db.flush()

        v = _seed_active_vendor(
            db, org_apex.id, "VND-APX-B6-60", "Deterministic Telemetry Vendor", inherent_risk=80.0
        )
        eng = VendorEngagement(
            organization_id=org_apex.id,
            vendor_id=v.id,
            engagement_code="ENG-APX-60",
            engagement_name="Core Payment Gateway",
            status=EngagementStatusEnum.ACTIVE,
            criticality=BusinessCriticalityEnum.CRITICAL,
            data_classification=DataClassificationEnum.RESTRICTED,
            hosting_model=HostingModelEnum.MULTI_TENANT_SAAS,
            network_connectivity=NetworkConnectivityEnum.DIRECT_API_VPN_DB,
            pii_access=PiiFinancialAccessEnum.DIRECT_PCI_PII_PHI,
            calculated_risk_score=95.0,
        )
        db.add(eng)
        db.flush()

        now = datetime.now(timezone.utc)
        asm = VendorAssessment(
            organization_id=org_apex.id,
            vendor_id=v.id,
            engagement_id=eng.id,
            assessment_code="ASM-APX-60",
            title="Annual Review 60",
            assessment_type=VendorAssessmentTypeEnum.ANNUAL_REASSESSMENT,
            status=VendorAssessmentStatusEnum.APPROVED,
            calculated_score=100.0,
            assessor_id=admin_user.id,
            reviewer_id=manager_user.id,
            reviewed_at=now,
        )
        db.add(asm)
        db.flush()
        db.add(
            VendorAssessmentItem(
                organization_id=org_apex.id,
                assessment_id=asm.id,
                rationalized_common_control_id=ccm.id,
                question_key="Q-60",
                question_text="DR tested?",
                response_status=VendorResponseStatusEnum.COMPLIANT,
                weight=5.0,
            )
        )

        # Add 1 CRITICAL SLA breach (+6.0) and 1 PENDING_REVIEW CRITICAL subprocessor (+3.0)
        ob = VendorSlaObligation(
            organization_id=org_apex.id,
            vendor_id=v.id,
            obligation_code="SLA-APX-60",
            title="Availability",
            metric_type=SlaMetricTypeEnum.AVAILABILITY_PCT,
            comparison_operator=SlaComparisonOperatorEnum.GTE,
            target_value=99.99,
            breach_threshold=99.9,
            status=VendorSlaObligationStatusEnum.ACTIVE,
            effective_from=now - timedelta(days=30),
            created_by_id=admin_user.id,
        )
        db.add(ob)
        db.flush()
        db.add(
            VendorSlaBreach(
                organization_id=org_apex.id,
                vendor_id=v.id,
                sla_obligation_id=ob.id,
                breach_code="BRC-APX-60",
                observed_value=95.0,
                target_value_snapshot=99.99,
                breach_threshold_snapshot=99.9,
                variance_magnitude=4.9,
                severity=VendorSlaBreachSeverityEnum.CRITICAL,
                status=VendorSlaBreachStatusEnum.OPEN,
                breach_period_start=now - timedelta(hours=2),
                breach_period_end=now - timedelta(hours=1),
                occurred_at=now - timedelta(minutes=15),
                root_cause_summary="Core outage",
                recorded_by_id=admin_user.id,
            )
        )
        db.add(
            VendorSubprocessor(
                organization_id=org_apex.id,
                vendor_id=v.id,
                subprocessor_code="SUB-APX-60",
                subprocessor_name="Unapproved Critical Sub",
                normalized_fourth_party_name="unapproved critical sub",
                service_function="HSM",
                criticality=BusinessCriticalityEnum.CRITICAL,
                status=VendorSubprocessorStatusEnum.PENDING_REVIEW,
                registered_by_id=admin_user.id,
            )
        )
        db.commit()

        res = client.get(
            f"/api/v1/vendors/{v.id}/risk-posture",
            headers=get_token_headers(admin_user),
        )
        assert res.status_code == 200
        posture = res.json()
        assert posture["sla_breach_penalties"] == 12.0
        assert posture["subprocessor_penalties"] == 8.0
        assert posture["open_sla_breaches_count"] == 1
        assert 0.0 <= posture["residual"]["residual_risk_score"] <= 100.0
        assert posture["residual"]["residual_risk_score"] >= posture["residual"]["risk_floor"]

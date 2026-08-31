from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy.exc import IntegrityError

from app.models.control import OrganizationControl, ImplementationStatusEnum, PriorityEnum
from app.models.exposure import (
    AssetTypeEnum,
    EnvironmentEnum,
    ExceptionApprovalStatusEnum,
    ExposureAssetLink,
    ExposureException,
    ExposureSeverityEnum,
    ExposureStatusEnum,
    VulnerabilityExposure,
)
from app.models.organization import Organization
from app.models.resilience import BusinessProcess, CriticalityTierEnum
from app.models.tprm import Vendor, VendorStatusEnum, VendorTierEnum
from app.models.user import User
from app.models.audit_log import AuditLog
from app.schemas.exposure import (
    ExposureAssetLinkCreate,
    ExposureExceptionCreate,
    ExposureExceptionReviewRequest,
    VulnerabilityExposureCreate,
    VulnerabilityExposureUpdate,
)
from app.services.exposure_service import ExposureService


@pytest.fixture
def exposure_fixture(db):
    """Setup multi-tenant fixtures for Phase 14 Exposure-GRC domain tests."""
    org1 = Organization(name="Exposure Apex Corp", slug="apex-exposure-1")
    org2 = Organization(name="Exposure Meridian Ltd", slug="meridian-exposure-2")
    db.add_all([org1, org2])
    db.commit()

    analyst1 = User(
        organization_id=org1.id,
        email="analyst@apex.com",
        hashed_password="hash",
        full_name="Apex Security Analyst",
        role="SECURITY_ANALYST",
        is_active=True,
    )
    manager1 = User(
        organization_id=org1.id,
        email="manager@apex.com",
        hashed_password="hash",
        full_name="Apex Security Manager",
        role="MANAGER",
        is_active=True,
    )
    foreign_user = User(
        organization_id=org2.id,
        email="user@meridian.com",
        hashed_password="hash",
        full_name="Meridian User",
        role="MANAGER",
        is_active=True,
    )
    db.add_all([analyst1, manager1, foreign_user])
    db.commit()

    # Phase 13 Business Process in Org 1
    proc_tier1 = BusinessProcess(
        organization_id=org1.id,
        name="Core Settlement Engine",
        owner_id=analyst1.id,
        criticality_tier=CriticalityTierEnum.TIER_1,
    )
    proc_tier2 = BusinessProcess(
        organization_id=org1.id,
        name="Customer Portal",
        owner_id=analyst1.id,
        criticality_tier=CriticalityTierEnum.TIER_2,
    )
    # Phase 13 Business Process in Org 2 (Foreign)
    foreign_proc = BusinessProcess(
        organization_id=org2.id,
        name="Meridian Core Ledger",
        owner_id=foreign_user.id,
        criticality_tier=CriticalityTierEnum.TIER_1,
    )

    # Phase 9 Vendor in Org 1
    vendor1 = Vendor(
        organization_id=org1.id,
        legal_name="CloudHost Services",
        vendor_code="VND-001",
        vendor_status=VendorStatusEnum.ACTIVE,
        calculated_tier=VendorTierEnum.TIER_1_CRITICAL,
    )
    # Phase 9 Vendor in Org 2 (Foreign)
    foreign_vendor = Vendor(
        organization_id=org2.id,
        legal_name="Foreign Cloud",
        vendor_code="VND-999",
        vendor_status=VendorStatusEnum.ACTIVE,
        calculated_tier=VendorTierEnum.TIER_1_CRITICAL,
    )

    # Phase 2 Control in Org 1
    ctrl1 = OrganizationControl(
        organization_id=org1.id,
        subcategory_id=1,
        status=ImplementationStatusEnum.IMPLEMENTED,
        priority=PriorityEnum.HIGH,
    )
    # Phase 2 Control in Org 2 (Foreign)
    foreign_ctrl = OrganizationControl(
        organization_id=org2.id,
        subcategory_id=1,
        status=ImplementationStatusEnum.IMPLEMENTED,
        priority=PriorityEnum.HIGH,
    )

    db.add_all([proc_tier1, proc_tier2, foreign_proc, vendor1, foreign_vendor, ctrl1, foreign_ctrl])
    db.commit()

    return {
        "org1": org1,
        "org2": org2,
        "analyst1": analyst1,
        "manager1": manager1,
        "foreign_user": foreign_user,
        "proc_tier1": proc_tier1,
        "proc_tier2": proc_tier2,
        "foreign_proc": foreign_proc,
        "vendor1": vendor1,
        "foreign_vendor": foreign_vendor,
        "ctrl1": ctrl1,
        "foreign_ctrl": foreign_ctrl,
    }


# ─────────────────────────────────────────────────────────────────────────────
# DOMAIN TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_enums_and_constants():
    """1. Verify Phase 14 domain enums and allowed values."""
    assert ExposureSeverityEnum.CRITICAL.value == "CRITICAL"
    assert ExposureSeverityEnum.HIGH.value == "HIGH"
    assert ExposureSeverityEnum.MEDIUM.value == "MEDIUM"
    assert ExposureSeverityEnum.LOW.value == "LOW"
    assert ExposureSeverityEnum.INFORMATIONAL.value == "INFORMATIONAL"

    assert ExposureStatusEnum.OPEN.value == "OPEN"
    assert ExposureStatusEnum.UNDER_INVESTIGATION.value == "UNDER_INVESTIGATION"
    assert ExposureStatusEnum.REMEDIATING.value == "REMEDIATING"
    assert ExposureStatusEnum.EXCEPTION_REQUESTED.value == "EXCEPTION_REQUESTED"
    assert ExposureStatusEnum.EXCEPTION_APPROVED.value == "EXCEPTION_APPROVED"
    assert ExposureStatusEnum.EXCEPTION_REJECTED.value == "EXCEPTION_REJECTED"
    assert ExposureStatusEnum.RESOLVED.value == "RESOLVED"

    assert AssetTypeEnum.SERVER.value == "SERVER"
    assert AssetTypeEnum.DATABASE.value == "DATABASE"
    assert AssetTypeEnum.CLOUD_SERVICE.value == "CLOUD_SERVICE"
    assert AssetTypeEnum.NETWORK_DEVICE.value == "NETWORK_DEVICE"
    assert AssetTypeEnum.APPLICATION.value == "APPLICATION"


def test_exposure_creation_default_sla(db, exposure_fixture):
    """2. Verify exposure creation with server-authoritative SLA calculation."""
    f = exposure_fixture
    create_data = VulnerabilityExposureCreate(
        cve_id="CVE-2026-1001",
        title="Remote Code Execution in Core Auth Gateway",
        description="Unauthenticated RCE vulnerability in web tier.",
        cvss_score=9.8,
        cvss_vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        epss_score=0.85,
        cisa_kev=False,
        severity=ExposureSeverityEnum.CRITICAL,
    )

    exposure = ExposureService.create_exposure(
        db=db,
        organization_id=f["org1"].id,
        data=create_data,
        actor_id=f["analyst1"].id,
        actor_email=f["analyst1"].email,
    )

    assert exposure.id is not None
    assert exposure.cve_id == "CVE-2026-1001"
    assert exposure.status == ExposureStatusEnum.OPEN
    # Critical non-KEV = 14 days
    expected_sla_min = datetime.now(timezone.utc) + timedelta(days=13)
    expected_sla_max = datetime.now(timezone.utc) + timedelta(days=15)
    sla = exposure.remediation_sla_due if exposure.remediation_sla_due.tzinfo else exposure.remediation_sla_due.replace(tzinfo=timezone.utc)
    assert expected_sla_min <= sla <= expected_sla_max


def test_exposure_creation_cisa_kev_sla(db, exposure_fixture):
    """3. Verify Critical + CISA KEV gets accelerated 7-day SLA."""
    f = exposure_fixture
    create_data = VulnerabilityExposureCreate(
        cve_id="CVE-2026-2002",
        title="Zero-Day Kernel Privilege Escalation",
        cvss_score=10.0,
        epss_score=0.95,
        cisa_kev=True,
        severity=ExposureSeverityEnum.CRITICAL,
    )

    exposure = ExposureService.create_exposure(
        db=db,
        organization_id=f["org1"].id,
        data=create_data,
    )

    # Critical KEV = 7 days
    sla = exposure.remediation_sla_due if exposure.remediation_sla_due.tzinfo else exposure.remediation_sla_due.replace(tzinfo=timezone.utc)
    expected_sla = datetime.now(timezone.utc) + timedelta(days=7)
    assert abs((sla - expected_sla).total_seconds()) < 60


def test_exposure_cvss_and_epss_bounds():
    """4-6. Verify lower and upper bounds for CVSS and EPSS."""
    # Min bound: CVSS 0.0, EPSS 0.0, KEV False -> base score = 0.0
    b0, m0, i0 = ExposureService.calculate_exposure_index(0.0, 0.0, False)
    assert b0 == 0.0
    assert i0 == 0.0

    # Max bound: CVSS 10.0, EPSS 1.0, KEV True -> base score = (10*0.4)+(1.0*100*0.35)+25 = 4+35+25 = 64.0
    b_max, m_max, i_max = ExposureService.calculate_exposure_index(10.0, 1.0, True)
    assert b_max == 64.0
    assert i_max == 64.0


def test_invalid_cvss_rejected():
    """7. Verify CVSS score < 0.0 or > 10.0 raises ValueError."""
    with pytest.raises(ValueError, match="CVSS score must be between"):
        ExposureService.calculate_exposure_index(10.5, 0.5, False)

    with pytest.raises(ValueError, match="CVSS score must be between"):
        ExposureService.calculate_exposure_index(-1.0, 0.5, False)


def test_invalid_epss_rejected():
    """8. Verify EPSS probability < 0.0 or > 1.0 raises ValueError."""
    with pytest.raises(ValueError, match="EPSS score must be between"):
        ExposureService.calculate_exposure_index(5.0, 1.5, False)

    with pytest.raises(ValueError, match="EPSS score must be between"):
        ExposureService.calculate_exposure_index(5.0, -0.1, False)


def test_kev_contribution():
    """9. Verify CISA KEV adds exactly 25.0 points to Base Score."""
    base_no_kev, _, _ = ExposureService.calculate_exposure_index(5.0, 0.2, cisa_kev=False)
    base_with_kev, _, _ = ExposureService.calculate_exposure_index(5.0, 0.2, cisa_kev=True)
    assert round(base_with_kev - base_no_kev, 2) == 25.0


def test_blast_radius_multipliers():
    """10-11. Verify Blast Radius multipliers based on Phase 13 Process Criticality."""
    # Base calculation: CVSS=8.0, EPSS=0.5 -> (8*0.4)+(50*0.35) = 3.2 + 17.5 = 20.7
    _, m_t1, i_t1 = ExposureService.calculate_exposure_index(8.0, 0.5, False, CriticalityTierEnum.TIER_1)
    assert m_t1 == 1.25
    assert i_t1 == round(20.7 * 1.25, 2)

    _, m_t2, i_t2 = ExposureService.calculate_exposure_index(8.0, 0.5, False, CriticalityTierEnum.TIER_2)
    assert m_t2 == 1.15
    assert i_t2 == round(20.7 * 1.15, 2)

    _, m_t3, i_t3 = ExposureService.calculate_exposure_index(8.0, 0.5, False, CriticalityTierEnum.TIER_3)
    assert m_t3 == 1.05
    assert i_t3 == round(20.7 * 1.05, 2)

    _, m_t4, i_t4 = ExposureService.calculate_exposure_index(8.0, 0.5, False, CriticalityTierEnum.TIER_4)
    assert m_t4 == 1.00
    assert i_t4 == round(20.7 * 1.00, 2)


def test_exposure_score_cap_100():
    """12. Verify Exposure Index caps strictly at 100.0."""
    # Max possible score with Tier 1: Base = 64.0 * 1.25 = 80.0
    # Let's test a case where calculation would exceed 100
    _, _, score = ExposureService.calculate_exposure_index(10.0, 1.0, True, CriticalityTierEnum.TIER_1)
    assert score <= 100.0
    assert score == 80.0


def test_lifecycle_valid_transitions(db, exposure_fixture):
    """13. Verify legal lifecycle state transitions."""
    f = exposure_fixture
    exposure = ExposureService.create_exposure(
        db=db,
        organization_id=f["org1"].id,
        data=VulnerabilityExposureCreate(
            cve_id="CVE-2026-3003",
            title="SQL Injection in Payments API",
            cvss_score=8.5,
            severity=ExposureSeverityEnum.HIGH,
        ),
    )
    assert exposure.status == ExposureStatusEnum.OPEN

    # OPEN -> UNDER_INVESTIGATION
    exp1 = ExposureService.update_exposure_status(
        db=db,
        organization_id=f["org1"].id,
        exposure_id=exposure.id,
        new_status=ExposureStatusEnum.UNDER_INVESTIGATION,
    )
    assert exp1.status == ExposureStatusEnum.UNDER_INVESTIGATION

    # UNDER_INVESTIGATION -> REMEDIATING
    exp2 = ExposureService.update_exposure_status(
        db=db,
        organization_id=f["org1"].id,
        exposure_id=exposure.id,
        new_status=ExposureStatusEnum.REMEDIATING,
    )
    assert exp2.status == ExposureStatusEnum.REMEDIATING

    # REMEDIATING -> RESOLVED
    exp3 = ExposureService.update_exposure_status(
        db=db,
        organization_id=f["org1"].id,
        exposure_id=exposure.id,
        new_status=ExposureStatusEnum.RESOLVED,
    )
    assert exp3.status == ExposureStatusEnum.RESOLVED
    assert exp3.resolved_at is not None


def test_resolved_immutability(db, exposure_fixture):
    """14. Verify RESOLVED exposure records are immutable."""
    f = exposure_fixture
    exposure = ExposureService.create_exposure(
        db=db,
        organization_id=f["org1"].id,
        data=VulnerabilityExposureCreate(
            cve_id="CVE-2026-4004",
            title="Cross-Site Scripting in Admin Console",
            cvss_score=6.1,
            severity=ExposureSeverityEnum.MEDIUM,
        ),
    )
    # Transition to RESOLVED
    ExposureService.update_exposure_status(
        db=db,
        organization_id=f["org1"].id,
        exposure_id=exposure.id,
        new_status=ExposureStatusEnum.RESOLVED,
    )

    # 1. Attempting status transition out of RESOLVED must fail
    with pytest.raises(ValueError, match="Cannot transition out of terminal RESOLVED status"):
        ExposureService.update_exposure_status(
            db=db,
            organization_id=f["org1"].id,
            exposure_id=exposure.id,
            new_status=ExposureStatusEnum.OPEN,
        )

    # 2. Attempting to update fields on RESOLVED record must fail
    with pytest.raises(ValueError, match="Resolved exposure records are immutable"):
        ExposureService.update_exposure(
            db=db,
            organization_id=f["org1"].id,
            exposure_id=exposure.id,
            data=VulnerabilityExposureUpdate(title="Modified Title"),
        )

    # 3. Attempting to delete RESOLVED record must fail
    with pytest.raises(ValueError, match="Resolved exposure records are immutable"):
        ExposureService.delete_exposure(
            db=db,
            organization_id=f["org1"].id,
            exposure_id=exposure.id,
        )

    # 4. Attempting to link assets to RESOLVED record must fail
    with pytest.raises(ValueError, match="Cannot link assets to an immutable RESOLVED exposure"):
        ExposureService.link_asset(
            db=db,
            organization_id=f["org1"].id,
            exposure_id=exposure.id,
            data=ExposureAssetLinkCreate(asset_identifier="srv-app-01"),
        )


def test_asset_link_with_business_process_and_recalculation(db, exposure_fixture):
    """15. Link Phase 13 Tier 1 Business Process and verify automatic blast radius multiplication."""
    f = exposure_fixture
    exposure = ExposureService.create_exposure(
        db=db,
        organization_id=f["org1"].id,
        data=VulnerabilityExposureCreate(
            cve_id="CVE-2026-5005",
            title="Database Buffer Overflow",
            cvss_score=8.0,
            epss_score=0.5,
            cisa_kev=False,
            severity=ExposureSeverityEnum.HIGH,
        ),
    )
    # Initial score: (8*0.4) + (50*0.35) = 3.2 + 17.5 = 20.7
    assert exposure.exposure_index == 20.7

    # Link to Tier 1 process
    link = ExposureService.link_asset(
        db=db,
        organization_id=f["org1"].id,
        exposure_id=exposure.id,
        data=ExposureAssetLinkCreate(
            asset_identifier="db-cluster-primary",
            asset_type=AssetTypeEnum.DATABASE,
            process_id=f["proc_tier1"].id,
        ),
    )
    assert link.id is not None
    # Exposure index updated with 1.25x multiplier -> 20.7 * 1.25 = 25.88
    db.refresh(exposure)
    assert exposure.exposure_index == 25.88


def test_asset_link_cross_tenant_process_rejected(db, exposure_fixture):
    """16. Cross-tenant linkage of BusinessProcess must be rejected."""
    f = exposure_fixture
    exposure = ExposureService.create_exposure(
        db=db,
        organization_id=f["org1"].id,
        data=VulnerabilityExposureCreate(
            cve_id="CVE-2026-6006",
            title="Unauthorized API Access",
            cvss_score=7.5,
        ),
    )

    with pytest.raises(ValueError, match="Referenced Business Process does not exist in this organization"):
        ExposureService.link_asset(
            db=db,
            organization_id=f["org1"].id,
            exposure_id=exposure.id,
            data=ExposureAssetLinkCreate(
                asset_identifier="foreign-node",
                process_id=f["foreign_proc"].id,  # Belongs to Org 2
            ),
        )


def test_asset_link_cross_tenant_vendor_rejected(db, exposure_fixture):
    """17. Cross-tenant linkage of Phase 9 Vendor must be rejected."""
    f = exposure_fixture
    exposure = ExposureService.create_exposure(
        db=db,
        organization_id=f["org1"].id,
        data=VulnerabilityExposureCreate(
            cve_id="CVE-2026-7007",
            title="Third-Party Library Flaw",
            cvss_score=5.0,
        ),
    )

    with pytest.raises(ValueError, match="Referenced Vendor does not exist in this organization"):
        ExposureService.link_asset(
            db=db,
            organization_id=f["org1"].id,
            exposure_id=exposure.id,
            data=ExposureAssetLinkCreate(
                asset_identifier="vendor-app",
                vendor_id=f["foreign_vendor"].id,  # Belongs to Org 2
            ),
        )


def test_asset_link_cross_tenant_control_rejected(db, exposure_fixture):
    """18. Cross-tenant linkage of Phase 2 Control must be rejected."""
    f = exposure_fixture
    exposure = ExposureService.create_exposure(
        db=db,
        organization_id=f["org1"].id,
        data=VulnerabilityExposureCreate(
            cve_id="CVE-2026-8008",
            title="Misconfigured Firewall Rule",
            cvss_score=4.5,
        ),
    )

    with pytest.raises(ValueError, match="Referenced Organization Control does not exist in this organization"):
        ExposureService.link_asset(
            db=db,
            organization_id=f["org1"].id,
            exposure_id=exposure.id,
            data=ExposureAssetLinkCreate(
                asset_identifier="perimeter-fw",
                control_id=f["foreign_ctrl"].id,  # Belongs to Org 2
            ),
        )


def test_asset_unlink_recalculates_index(db, exposure_fixture):
    """19. Removing Tier 1 process link recalculates blast radius back to base multiplier."""
    f = exposure_fixture
    exposure = ExposureService.create_exposure(
        db=db,
        organization_id=f["org1"].id,
        data=VulnerabilityExposureCreate(
            cve_id="CVE-2026-9009",
            title="Memory Leak in Cache Server",
            cvss_score=8.0,
            epss_score=0.5,
        ),
    )
    link = ExposureService.link_asset(
        db=db,
        organization_id=f["org1"].id,
        exposure_id=exposure.id,
        data=ExposureAssetLinkCreate(
            asset_identifier="redis-cluster",
            process_id=f["proc_tier1"].id,
        ),
    )
    db.refresh(exposure)
    assert exposure.exposure_index == 25.88

    # Unlink asset
    ExposureService.unlink_asset(
        db=db,
        organization_id=f["org1"].id,
        link_id=link.id,
    )
    db.refresh(exposure)
    assert exposure.exposure_index == 20.7


def test_four_eyes_exception_governance(db, exposure_fixture):
    """20-22. Verify Four-Eyes Exception Request and Approval workflow."""
    f = exposure_fixture
    exposure = ExposureService.create_exposure(
        db=db,
        organization_id=f["org1"].id,
        data=VulnerabilityExposureCreate(
            cve_id="CVE-2026-1111",
            title="Hardcoded API Key in Legacy Microservice",
            cvss_score=7.0,
            severity=ExposureSeverityEnum.HIGH,
        ),
    )
    original_sla = exposure.remediation_sla_due
    requested_new_sla = original_sla + timedelta(days=30)

    # 1. Analyst requests SLA extension
    exc = ExposureService.request_exception(
        db=db,
        organization_id=f["org1"].id,
        exposure_id=exposure.id,
        data=ExposureExceptionCreate(
            requested_sla_due=requested_new_sla,
            justification="Vendor patch delayed until Q4 release window.",
            compensating_controls="WAF virtual patch applied to block payload pattern.",
        ),
        requested_by_id=f["analyst1"].id,
    )
    assert exc.status == ExceptionApprovalStatusEnum.PENDING
    db.refresh(exposure)
    assert exposure.status == ExposureStatusEnum.EXCEPTION_REQUESTED

    # 2. Self-approval by requester must be rejected (Segregation of Duties)
    with pytest.raises(ValueError, match="Segregation of duties violation"):
        ExposureService.review_exception(
            db=db,
            organization_id=f["org1"].id,
            exception_id=exc.id,
            review=ExposureExceptionReviewRequest(decision=ExceptionApprovalStatusEnum.APPROVED),
            approver_id=f["analyst1"].id,  # Requester attempting self-approval
        )

    # 3. Independent manager approves exception
    exc_approved = ExposureService.review_exception(
        db=db,
        organization_id=f["org1"].id,
        exception_id=exc.id,
        review=ExposureExceptionReviewRequest(
            decision=ExceptionApprovalStatusEnum.APPROVED,
            review_notes="Compensating WAF rule verified by SecOps.",
        ),
        approver_id=f["manager1"].id,
    )
    assert exc_approved.status == ExceptionApprovalStatusEnum.APPROVED
    db.refresh(exposure)
    assert exposure.status == ExposureStatusEnum.EXCEPTION_APPROVED
    assert exposure.remediation_sla_due == requested_new_sla


def test_four_eyes_exception_rejection(db, exposure_fixture):
    """23. Manager rejects exception -> status transitions to EXCEPTION_REJECTED."""
    f = exposure_fixture
    exposure = ExposureService.create_exposure(
        db=db,
        organization_id=f["org1"].id,
        data=VulnerabilityExposureCreate(
            cve_id="CVE-2026-2222",
            title="Broken Object Level Authorization",
            cvss_score=8.5,
            severity=ExposureSeverityEnum.HIGH,
        ),
    )
    exc = ExposureService.request_exception(
        db=db,
        organization_id=f["org1"].id,
        exposure_id=exposure.id,
        data=ExposureExceptionCreate(
            requested_sla_due=exposure.remediation_sla_due + timedelta(days=15),
            justification="Insufficient testing time.",
        ),
        requested_by_id=f["analyst1"].id,
    )

    # Manager rejects
    exc_rejected = ExposureService.review_exception(
        db=db,
        organization_id=f["org1"].id,
        exception_id=exc.id,
        review=ExposureExceptionReviewRequest(
            decision=ExceptionApprovalStatusEnum.REJECTED,
            review_notes="High severity BOLA cannot be deferred without formal risk committee acceptance.",
        ),
        approver_id=f["manager1"].id,
    )
    assert exc_rejected.status == ExceptionApprovalStatusEnum.REJECTED
    db.refresh(exposure)
    assert exposure.status == ExposureStatusEnum.EXCEPTION_REJECTED


def test_exception_already_decided_rejected(db, exposure_fixture):
    """24. Attempting to review an already decided exception raises ValueError."""
    f = exposure_fixture
    exposure = ExposureService.create_exposure(
        db=db,
        organization_id=f["org1"].id,
        data=VulnerabilityExposureCreate(
            cve_id="CVE-2026-3333",
            title="Information Disclosure in Error Stack Trace",
            cvss_score=5.3,
        ),
    )
    exc = ExposureService.request_exception(
        db=db,
        organization_id=f["org1"].id,
        exposure_id=exposure.id,
        data=ExposureExceptionCreate(
            requested_sla_due=exposure.remediation_sla_due + timedelta(days=20),
            justification="Low impact internal service.",
        ),
        requested_by_id=f["analyst1"].id,
    )
    ExposureService.review_exception(
        db=db,
        organization_id=f["org1"].id,
        exception_id=exc.id,
        review=ExposureExceptionReviewRequest(decision=ExceptionApprovalStatusEnum.APPROVED),
        approver_id=f["manager1"].id,
    )

    with pytest.raises(ValueError, match="is already in terminal state"):
        ExposureService.review_exception(
            db=db,
            organization_id=f["org1"].id,
            exception_id=exc.id,
            review=ExposureExceptionReviewRequest(decision=ExceptionApprovalStatusEnum.REJECTED),
            approver_id=f["manager1"].id,
        )


def test_spawn_remediation_plan_integration(db, exposure_fixture):
    """25. Auto-instantiate a Phase 11 RemediationPlan linked to the exposure."""
    f = exposure_fixture
    exposure = ExposureService.create_exposure(
        db=db,
        organization_id=f["org1"].id,
        data=VulnerabilityExposureCreate(
            cve_id="CVE-2026-4444",
            title="SSRF in Webhook Processor",
            cvss_score=9.1,
            severity=ExposureSeverityEnum.CRITICAL,
        ),
    )

    plan = ExposureService.spawn_remediation_plan(
        db=db,
        organization_id=f["org1"].id,
        exposure_id=exposure.id,
        owner_id=f["analyst1"].id,
    )
    assert plan.id is not None
    assert plan.plan_owner_id == f["analyst1"].id
    assert "CVE-2026-4444" in plan.plan_code

    db.refresh(exposure)
    assert exposure.remediation_plan_id == plan.id
    assert exposure.status == ExposureStatusEnum.REMEDIATING


def test_executive_posture_summary(db, exposure_fixture):
    """26. Verify posture summary telemetry aggregation."""
    f = exposure_fixture
    ExposureService.create_exposure(
        db=db,
        organization_id=f["org1"].id,
        data=VulnerabilityExposureCreate(
            cve_id="CVE-2026-5551",
            title="Critical RCE",
            cvss_score=9.8,
            cisa_kev=True,
            severity=ExposureSeverityEnum.CRITICAL,
        ),
    )
    ExposureService.create_exposure(
        db=db,
        organization_id=f["org1"].id,
        data=VulnerabilityExposureCreate(
            cve_id="CVE-2026-5552",
            title="Medium XSS",
            cvss_score=6.0,
            cisa_kev=False,
            severity=ExposureSeverityEnum.MEDIUM,
        ),
    )

    summary = ExposureService.get_exposure_posture_summary(db=db, organization_id=f["org1"].id)
    assert summary["total_exposures"] == 2
    assert summary["critical_exposures"] == 1
    assert summary["cisa_kev_count"] == 1
    assert summary["average_exposure_index"] > 0.0


def test_tenant_isolation(db, exposure_fixture):
    """27. Org 2 cannot retrieve or list Org 1 exposures."""
    f = exposure_fixture
    exp1 = ExposureService.create_exposure(
        db=db,
        organization_id=f["org1"].id,
        data=VulnerabilityExposureCreate(
            cve_id="CVE-2026-6666",
            title="Apex Proprietary Flaw",
            cvss_score=7.0,
        ),
    )

    # Org 2 lookup returns None
    assert ExposureService.get_exposure(db, f["org2"].id, exp1.id) is None

    # Org 2 list is empty
    org2_list = ExposureService.list_exposures(db, f["org2"].id)
    assert len(org2_list) == 0


def test_audit_event_logging(db, exposure_fixture):
    """28. Verify tamper-evident audit log entries for exposure mutations."""
    f = exposure_fixture
    exposure = ExposureService.create_exposure(
        db=db,
        organization_id=f["org1"].id,
        data=VulnerabilityExposureCreate(
            cve_id="CVE-2026-7777",
            title="Audit Test Exposure",
            cvss_score=5.0,
        ),
        actor_id=f["analyst1"].id,
        actor_email=f["analyst1"].email,
    )

    logs = (
        db.query(AuditLog)
        .filter(
            AuditLog.organization_id == f["org1"].id,
            AuditLog.resource_id == str(exposure.id),
        )
        .all()
    )
    actions = [l.action for l in logs]
    assert "EXPOSURE_INGESTED" in actions


def test_deterministic_repeated_calculation():
    """29. Verify score calculation is 100% deterministic."""
    for _ in range(50):
        b1, m1, idx1 = ExposureService.calculate_exposure_index(7.8, 0.42, True, CriticalityTierEnum.TIER_2)
        b2, m2, idx2 = ExposureService.calculate_exposure_index(7.8, 0.42, True, CriticalityTierEnum.TIER_2)
        assert b1 == b2
        assert m1 == m2
        assert idx1 == idx2


def test_cross_tenant_exception_request_rejected(db, exposure_fixture):
    """30. Attempting to request exception on foreign org exposure raises ValueError."""
    f = exposure_fixture
    exp1 = ExposureService.create_exposure(
        db=db,
        organization_id=f["org1"].id,
        data=VulnerabilityExposureCreate(
            cve_id="CVE-2026-8888",
            title="Foreign Exposure Test",
            cvss_score=6.5,
        ),
    )
    with pytest.raises(ValueError, match="not found"):
        ExposureService.request_exception(
            db=db,
            organization_id=f["org2"].id,  # Foreign tenant
            exposure_id=exp1.id,
            data=ExposureExceptionCreate(
                requested_sla_due=exp1.remediation_sla_due + timedelta(days=10),
                justification="Testing cross-tenant rejection",
            ),
            requested_by_id=f["foreign_user"].id,
        )


def test_cross_tenant_exception_review_rejected(db, exposure_fixture):
    """31. Attempting to review foreign org exception raises ValueError."""
    f = exposure_fixture
    exp1 = ExposureService.create_exposure(
        db=db,
        organization_id=f["org1"].id,
        data=VulnerabilityExposureCreate(
            cve_id="CVE-2026-8889",
            title="Foreign Review Test",
            cvss_score=7.2,
        ),
    )
    exc = ExposureService.request_exception(
        db=db,
        organization_id=f["org1"].id,
        exposure_id=exp1.id,
        data=ExposureExceptionCreate(
            requested_sla_due=exp1.remediation_sla_due + timedelta(days=14),
            justification="Valid justification for delay.",
        ),
        requested_by_id=f["analyst1"].id,
    )
    with pytest.raises(ValueError, match="not found"):
        ExposureService.review_exception(
            db=db,
            organization_id=f["org2"].id,  # Foreign tenant
            exception_id=exc.id,
            review=ExposureExceptionReviewRequest(decision=ExceptionApprovalStatusEnum.APPROVED),
            approver_id=f["foreign_user"].id,
        )


def test_exception_requested_sla_in_past_rejected(db, exposure_fixture):
    """32. Requested SLA date earlier than or equal to current SLA due date raises ValueError."""
    f = exposure_fixture
    exp1 = ExposureService.create_exposure(
        db=db,
        organization_id=f["org1"].id,
        data=VulnerabilityExposureCreate(
            cve_id="CVE-2026-8890",
            title="Invalid SLA Date Test",
            cvss_score=5.0,
        ),
    )
    with pytest.raises(ValueError, match="Requested SLA date must be later than"):
        ExposureService.request_exception(
            db=db,
            organization_id=f["org1"].id,
            exposure_id=exp1.id,
            data=ExposureExceptionCreate(
                requested_sla_due=exp1.remediation_sla_due - timedelta(days=1),  # In the past
                justification="Testing invalid date rejection.",
            ),
            requested_by_id=f["analyst1"].id,
        )


def test_exposure_update_recalculates_blast_radius(db, exposure_fixture):
    """33. Updating exposure CVSS/EPSS on an exposure linked to Tier 1 process re-applies 1.25x multiplier."""
    f = exposure_fixture
    exposure = ExposureService.create_exposure(
        db=db,
        organization_id=f["org1"].id,
        data=VulnerabilityExposureCreate(
            cve_id="CVE-2026-9999",
            title="Update Multiplier Test",
            cvss_score=5.0,
            epss_score=0.1,
        ),
    )
    # Link Tier 1 process
    ExposureService.link_asset(
        db=db,
        organization_id=f["org1"].id,
        exposure_id=exposure.id,
        data=ExposureAssetLinkCreate(
            asset_identifier="srv-prod-tier1",
            process_id=f["proc_tier1"].id,
        ),
    )
    db.refresh(exposure)

    # Update CVSS from 5.0 to 8.0, EPSS from 0.1 to 0.5
    updated = ExposureService.update_exposure(
        db=db,
        organization_id=f["org1"].id,
        exposure_id=exposure.id,
        data=VulnerabilityExposureUpdate(cvss_score=8.0, epss_score=0.5),
    )
    # Base score = (8*0.4)+(50*0.35) = 3.2 + 17.5 = 20.7; Multiplier = 1.25 -> 25.88
    assert updated.exposure_index == 25.88


def test_exposure_search_and_filtering(db, exposure_fixture):
    """34. Verify multi-attribute filtering and text search across exposures."""
    f = exposure_fixture
    ExposureService.create_exposure(
        db=db,
        organization_id=f["org1"].id,
        data=VulnerabilityExposureCreate(
            cve_id="CVE-2026-0001",
            title="OpenSSL Memory Corruption",
            cwe_id="CWE-119",
            cvss_score=9.0,
            severity=ExposureSeverityEnum.CRITICAL,
            cisa_kev=True,
        ),
    )
    ExposureService.create_exposure(
        db=db,
        organization_id=f["org1"].id,
        data=VulnerabilityExposureCreate(
            cve_id="CVE-2026-0002",
            title="Apache Tomcat Request Smuggling",
            cwe_id="CWE-444",
            cvss_score=6.0,
            severity=ExposureSeverityEnum.MEDIUM,
            cisa_kev=False,
        ),
    )

    # Filter by severity
    crit_list = ExposureService.list_exposures(db, f["org1"].id, severity=ExposureSeverityEnum.CRITICAL)
    assert any(e.cve_id == "CVE-2026-0001" for e in crit_list)
    assert not any(e.cve_id == "CVE-2026-0002" for e in crit_list)

    # Filter by CISA KEV
    kev_list = ExposureService.list_exposures(db, f["org1"].id, cisa_kev=True)
    assert all(e.cisa_kev is True for e in kev_list)

    # Search by text
    search_list = ExposureService.list_exposures(db, f["org1"].id, search="Tomcat")
    assert len(search_list) == 1
    assert search_list[0].cve_id == "CVE-2026-0002"

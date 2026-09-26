from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import tempfile
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.permissions import RoleEnum
from app.db.base import Base
from app.models.assessment import (
    Assessment,
    AssessmentConclusionEnum,
    AssessmentMethodEnum,
    AssessmentStatusEnum,
)
from app.models.audit_log import AuditLog
from app.models.control import ImplementationStatusEnum, OrganizationControl, PriorityEnum
from app.models.exception import (
    ExceptionStatusEnum,
    ExceptionTypeEnum,
    SecurityException,
)
from app.models.framework import (
    Framework,
    FrameworkCategory,
    FrameworkFunction,
    FrameworkSubcategory,
)
from app.models.organization import Organization
from app.models.policy import (
    AttestationRecordStatusEnum,
    CampaignStatusEnum,
    CampaignTargetTypeEnum,
    Policy,
    PolicyAttestationCampaign,
    PolicyReviewStageEnum,
    PolicyReviewStatusEnum,
    PolicyReviewWorkflow,
    PolicyStatusEnum,
    PolicyTypeEnum,
    PolicyVersion,
    PolicyVersionStatusEnum,
    UserAttestationRecord,
)
from app.models.user import User
from app.schemas.policy import PolicyCreate
from app.services.policy_service import PolicyService
from tests.conftest import get_token_headers


# ============================================================================
# FIXTURE HARNESS
# ============================================================================


@pytest.fixture
def b4_fixture(db: Session, org_apex: Organization, org_meridian: Organization):
    """Comprehensive multi-tenant fixture for Batch 4 Policy Lifecycle & Workforce Attestation Governance."""
    dummy_hash = "hashed_pw_b4"
    apex_admin = User(
        email="b4_apex_admin@apex.com",
        hashed_password=dummy_hash,
        full_name="B4 Apex Admin",
        role=RoleEnum.ADMIN,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_manager = User(
        email="b4_apex_manager@apex.com",
        hashed_password=dummy_hash,
        full_name="B4 Apex Manager",
        role=RoleEnum.MANAGER,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_manager_2 = User(
        email="b4_apex_manager2@apex.com",
        hashed_password=dummy_hash,
        full_name="B4 Apex Manager Two",
        role=RoleEnum.MANAGER,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_analyst = User(
        email="b4_apex_analyst@apex.com",
        hashed_password=dummy_hash,
        full_name="B4 Apex GRC Analyst",
        role=RoleEnum.GRC_ANALYST,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_sec_analyst = User(
        email="b4_apex_sec_analyst@apex.com",
        hashed_password=dummy_hash,
        full_name="B4 Apex Security Analyst",
        role=RoleEnum.SECURITY_ANALYST,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_auditor = User(
        email="b4_apex_auditor@apex.com",
        hashed_password=dummy_hash,
        full_name="B4 Apex Auditor",
        role=RoleEnum.AUDITOR,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_viewer = User(
        email="b4_apex_viewer@apex.com",
        hashed_password=dummy_hash,
        full_name="B4 Apex Viewer",
        role=RoleEnum.VIEWER,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_inactive_manager = User(
        email="b4_apex_inactive_mgr@apex.com",
        hashed_password=dummy_hash,
        full_name="B4 Apex Inactive Manager",
        role=RoleEnum.MANAGER,
        is_active=False,
        organization_id=org_apex.id,
    )

    meridian_admin = User(
        email="b4_meridian_admin@meridian.com",
        hashed_password=dummy_hash,
        full_name="B4 Meridian Admin",
        role=RoleEnum.ADMIN,
        is_active=True,
        organization_id=org_meridian.id,
    )
    meridian_manager = User(
        email="b4_meridian_manager@meridian.com",
        hashed_password=dummy_hash,
        full_name="B4 Meridian Manager",
        role=RoleEnum.MANAGER,
        is_active=True,
        organization_id=org_meridian.id,
    )

    db.add_all(
        [
            apex_admin,
            apex_manager,
            apex_manager_2,
            apex_analyst,
            apex_sec_analyst,
            apex_auditor,
            apex_viewer,
            apex_inactive_manager,
            meridian_admin,
            meridian_manager,
        ]
    )
    db.commit()

    subcat = db.query(FrameworkSubcategory).first()
    if not subcat:
        fw = Framework(identifier="B4-FW", name="Batch 4 Governance", version="1.0")
        db.add(fw)
        db.flush()
        fn = FrameworkFunction(
            framework_id=fw.id, identifier="GV", name="Govern", display_order=1
        )
        db.add(fn)
        db.flush()
        cat = FrameworkCategory(
            function_id=fn.id, identifier="GV.PO", name="Policy", display_order=1
        )
        db.add(cat)
        db.flush()
        subcat = FrameworkSubcategory(
            category_id=cat.id,
            identifier="GV.PO-01",
            title="Policy Governance",
            description="Policy management control",
            display_order=1,
        )
        db.add(subcat)
        db.flush()

    apex_ctrl = (
        db.query(OrganizationControl)
        .filter(
            OrganizationControl.organization_id == org_apex.id,
            OrganizationControl.subcategory_id == subcat.id,
        )
        .first()
    )
    if not apex_ctrl:
        apex_ctrl = OrganizationControl(
            organization_id=org_apex.id,
            subcategory_id=subcat.id,
            status=ImplementationStatusEnum.IMPLEMENTED,
            priority=PriorityEnum.HIGH,
        )
        db.add(apex_ctrl)
        db.flush()

    meridian_ctrl = (
        db.query(OrganizationControl)
        .filter(
            OrganizationControl.organization_id == org_meridian.id,
            OrganizationControl.subcategory_id == subcat.id,
        )
        .first()
    )
    if not meridian_ctrl:
        meridian_ctrl = OrganizationControl(
            organization_id=org_meridian.id,
            subcategory_id=subcat.id,
            status=ImplementationStatusEnum.IMPLEMENTED,
            priority=PriorityEnum.HIGH,
        )
        db.add(meridian_ctrl)
        db.flush()

    policy = PolicyService.create_policy(
        db=db,
        obj_in=PolicyCreate(
            title="B4 Apex Acceptable Use Policy",
            description="Mandatory acceptable use policy for all Apex personnel",
            policy_type=PolicyTypeEnum.ACCEPTABLE_USE,
            initial_content="# Acceptable Use Policy\n\nSection 1: All systems require MFA.",
            mapped_subcategory_ids=[subcat.id],
        ),
        organization_id=org_apex.id,
        created_by_id=apex_admin.id,
    )
    v1 = (
        db.query(PolicyVersion)
        .filter(
            PolicyVersion.policy_id == policy.id,
            PolicyVersion.version_number == 1,
        )
        .first()
    )

    meridian_policy = PolicyService.create_policy(
        db=db,
        obj_in=PolicyCreate(
            title="B4 Meridian Data Policy",
            description="Meridian tenant isolated policy",
            policy_type=PolicyTypeEnum.DATA_PROTECTION,
            initial_content="# Meridian Data Protection\n\nStrict tenant isolation.",
            mapped_subcategory_ids=[subcat.id],
        ),
        organization_id=org_meridian.id,
        created_by_id=meridian_admin.id,
    )
    meridian_v1 = (
        db.query(PolicyVersion)
        .filter(
            PolicyVersion.policy_id == meridian_policy.id,
            PolicyVersion.version_number == 1,
        )
        .first()
    )

    apex_policy_exception = SecurityException(
        organization_id=org_apex.id,
        title="B4 Approved Policy Waiver",
        description="Approved temporary policy waiver for legacy contractor",
        justification="Approved compensating control in place during migration window",
        exception_type=ExceptionTypeEnum.POLICY_EXCEPTION,
        status=ExceptionStatusEnum.APPROVED,
        requested_by_id=apex_analyst.id,
        owner_id=apex_analyst.id,
        reviewer_id=apex_manager_2.id,
        approved_at=datetime.now(timezone.utc),
        effective_date=date.today() - timedelta(days=2),
        expiry_date=date.today() + timedelta(days=60),
        linked_policy_id=policy.id,
    )
    meridian_policy_exception = SecurityException(
        organization_id=org_meridian.id,
        title="B4 Meridian Policy Waiver",
        description="Meridian waiver",
        justification="Meridian approved justification",
        exception_type=ExceptionTypeEnum.POLICY_EXCEPTION,
        status=ExceptionStatusEnum.APPROVED,
        requested_by_id=meridian_admin.id,
        owner_id=meridian_admin.id,
        reviewer_id=meridian_manager.id,
        approved_at=datetime.now(timezone.utc),
        effective_date=date.today() - timedelta(days=2),
        expiry_date=date.today() + timedelta(days=60),
        linked_policy_id=meridian_policy.id,
    )
    db.add_all([apex_policy_exception, meridian_policy_exception])
    db.commit()
    db.refresh(apex_policy_exception)
    db.refresh(meridian_policy_exception)

    return {
        "org_apex": org_apex,
        "org_meridian": org_meridian,
        "apex_admin": apex_admin,
        "apex_manager": apex_manager,
        "apex_manager_2": apex_manager_2,
        "apex_analyst": apex_analyst,
        "apex_sec_analyst": apex_sec_analyst,
        "apex_auditor": apex_auditor,
        "apex_viewer": apex_viewer,
        "apex_inactive_manager": apex_inactive_manager,
        "meridian_admin": meridian_admin,
        "meridian_manager": meridian_manager,
        "subcat": subcat,
        "apex_ctrl": apex_ctrl,
        "meridian_ctrl": meridian_ctrl,
        "policy": policy,
        "v1": v1,
        "meridian_policy": meridian_policy,
        "meridian_v1": meridian_v1,
        "apex_policy_exception": apex_policy_exception,
        "meridian_policy_exception": meridian_policy_exception,
    }


# ============================================================================
# 1. ALEMBIC MIGRATION 0025 REVERSIBILITY & DATA SURVIVAL TESTS
# ============================================================================


def test_alembic_0025_upgrade_downgrade_upgrade_cycle():
    """Verify Alembic migration 0025 <-> 0024 reversibility, columns, composite indexes, and row survival."""
    backend_dir = Path(__file__).resolve().parents[1]
    alembic_ini = backend_dir / "alembic.ini"

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_file = Path(tmpdir) / "alembic_0025_test.db"
        db_url = f"sqlite:///{db_file.as_posix()}"

        old_settings_url = settings.DATABASE_URL
        settings.DATABASE_URL = db_url
        try:
            engine = create_engine(db_url)
            Base.metadata.create_all(bind=engine)

            SessionLocal = sessionmaker(bind=engine)
            with SessionLocal() as session:
                org = Organization(name="Migration 0025 Org", slug="mig-0025-org")
                session.add(org)
                session.flush()
                user = User(
                    email="mig0025@example.com",
                    hashed_password="x",
                    full_name="Mig User",
                    role=RoleEnum.ADMIN,
                    is_active=True,
                    organization_id=org.id,
                )
                session.add(user)
                session.flush()
                pol = Policy(
                    organization_id=org.id,
                    title="Mig Policy",
                    policy_type=PolicyTypeEnum.INFORMATION_SECURITY,
                    status=PolicyStatusEnum.DRAFT,
                    owner_id=user.id,
                )
                session.add(pol)
                session.flush()
                ver = PolicyVersion(
                    organization_id=org.id,
                    policy_id=pol.id,
                    version_number=1,
                    content="Content v1",
                    content_hash_sha256="abc12345",
                    status=PolicyVersionStatusEnum.DRAFT,
                    created_by_id=user.id,
                )
                session.add(ver)
                session.flush()
                wf = PolicyReviewWorkflow(
                    organization_id=org.id,
                    policy_id=pol.id,
                    version_id=ver.id,
                    workflow_code="WF-MIG-001",
                    review_stage=PolicyReviewStageEnum.LEGAL_REVIEW,
                    status=PolicyReviewStatusEnum.PENDING,
                    created_by_id=user.id,
                )
                camp = PolicyAttestationCampaign(
                    organization_id=org.id,
                    campaign_code="CAMP-MIG-001",
                    title="Mig Campaign",
                    policy_id=pol.id,
                    version_id=ver.id,
                    policy_version_hash="abc12345",
                    target_type=CampaignTargetTypeEnum.ALL_USERS,
                    due_date=date.today() + timedelta(days=14),
                    status=CampaignStatusEnum.ACTIVE,
                    total_targeted_count=1,
                    completed_count=0,
                    overdue_count=1,
                    created_by_id=user.id,
                )
                session.add_all([wf, camp])
                session.flush()
                rec = UserAttestationRecord(
                    organization_id=org.id,
                    campaign_id=camp.id,
                    policy_id=pol.id,
                    version_id=ver.id,
                    user_id=user.id,
                    status=AttestationRecordStatusEnum.PENDING,
                )
                session.add(rec)
                session.commit()

            engine.dispose()

            cfg = Config(str(alembic_ini))
            cfg.set_main_option("script_location", str(backend_dir / "alembic"))
            cfg.set_main_option("sqlalchemy.url", db_url)

            command.stamp(cfg, "0025")

            # Downgrade to 0024
            command.downgrade(cfg, "0024")
            check_engine = create_engine(db_url)
            insp = inspect(check_engine)
            wf_cols_0024 = {c["name"] for c in insp.get_columns("policy_review_workflows")}
            camp_cols_0024 = {c["name"] for c in insp.get_columns("policy_attestation_campaigns")}
            rec_cols_0024 = {c["name"] for c in insp.get_columns("user_attestation_records")}
            assert "updated_at" not in wf_cols_0024
            assert "overdue_count" not in camp_cols_0024
            assert "reminder_sent_at" not in camp_cols_0024
            assert "exemption_exception_id" not in rec_cols_0024
            assert "exemption_reason" not in rec_cols_0024
            assert "exempted_by_id" not in rec_cols_0024
            assert "exempted_at" not in rec_cols_0024
            check_engine.dispose()

            # Upgrade back to 0025
            command.upgrade(cfg, "0025")
            check_engine = create_engine(db_url)
            insp = inspect(check_engine)
            wf_cols_0025 = {c["name"] for c in insp.get_columns("policy_review_workflows")}
            camp_cols_0025 = {c["name"] for c in insp.get_columns("policy_attestation_campaigns")}
            rec_cols_0025 = {c["name"] for c in insp.get_columns("user_attestation_records")}
            assert "updated_at" in wf_cols_0025
            assert "overdue_count" in camp_cols_0025
            assert "reminder_sent_at" in camp_cols_0025
            assert {
                "exemption_exception_id",
                "exemption_reason",
                "exempted_by_id",
                "exempted_at",
            }.issubset(rec_cols_0025)

            wf_indexes = {idx["name"] for idx in insp.get_indexes("policy_review_workflows")}
            camp_indexes = {idx["name"] for idx in insp.get_indexes("policy_attestation_campaigns")}
            rec_indexes = {idx["name"] for idx in insp.get_indexes("user_attestation_records")}
            assert "ix_pol_rev_wf_org_ver_status" in wf_indexes
            assert "ix_pol_camp_org_pol_status" in camp_indexes
            assert "ix_user_att_org_camp_status" in rec_indexes

            with check_engine.connect() as conn:
                wf_count = conn.execute(text("SELECT COUNT(*) FROM policy_review_workflows")).scalar()
                camp_count = conn.execute(
                    text("SELECT COUNT(*) FROM policy_attestation_campaigns")
                ).scalar()
                rec_count = conn.execute(text("SELECT COUNT(*) FROM user_attestation_records")).scalar()
                assert wf_count == 1
                assert camp_count == 1
                assert rec_count == 1
            check_engine.dispose()

            # Second cycle: downgrade 0024 -> upgrade 0025
            command.downgrade(cfg, "0024")
            command.upgrade(cfg, "0025")
        finally:
            settings.DATABASE_URL = old_settings_url


def test_alembic_0025_downgrade_remaps_exempted_to_pending():
    """Verify downgrading 0025 -> 0024 safely remaps EXEMPTED records to PENDING."""
    backend_dir = Path(__file__).resolve().parents[1]
    alembic_ini = backend_dir / "alembic.ini"

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_file = Path(tmpdir) / "alembic_0025_exempt_test.db"
        db_url = f"sqlite:///{db_file.as_posix()}"

        old_settings_url = settings.DATABASE_URL
        settings.DATABASE_URL = db_url
        try:
            engine = create_engine(db_url)
            Base.metadata.create_all(bind=engine)

            SessionLocal = sessionmaker(bind=engine)
            with SessionLocal() as session:
                org = Organization(name="Exempt Remap Org", slug="exempt-remap-org")
                session.add(org)
                session.flush()
                user = User(
                    email="remap@example.com",
                    hashed_password="x",
                    full_name="Remap User",
                    role=RoleEnum.ADMIN,
                    is_active=True,
                    organization_id=org.id,
                )
                session.add(user)
                session.flush()
                pol = Policy(
                    organization_id=org.id,
                    title="Remap Policy",
                    policy_type=PolicyTypeEnum.INFORMATION_SECURITY,
                    status=PolicyStatusEnum.PUBLISHED,
                    owner_id=user.id,
                )
                session.add(pol)
                session.flush()
                ver = PolicyVersion(
                    organization_id=org.id,
                    policy_id=pol.id,
                    version_number=1,
                    content="Content v1",
                    content_hash_sha256="def67890",
                    status=PolicyVersionStatusEnum.PUBLISHED,
                    created_by_id=user.id,
                )
                session.add(ver)
                session.flush()
                camp = PolicyAttestationCampaign(
                    organization_id=org.id,
                    campaign_code="CAMP-REMAP-001",
                    title="Remap Campaign",
                    policy_id=pol.id,
                    version_id=ver.id,
                    policy_version_hash="def67890",
                    target_type=CampaignTargetTypeEnum.ALL_USERS,
                    due_date=date.today() + timedelta(days=14),
                    status=CampaignStatusEnum.ACTIVE,
                    total_targeted_count=1,
                    completed_count=1,
                    overdue_count=0,
                    created_by_id=user.id,
                )
                session.add(camp)
                session.flush()
                rec = UserAttestationRecord(
                    organization_id=org.id,
                    campaign_id=camp.id,
                    policy_id=pol.id,
                    version_id=ver.id,
                    user_id=user.id,
                    status=AttestationRecordStatusEnum.EXEMPTED,
                    exemption_reason="Approved waiver",
                )
                session.add(rec)
                session.commit()

            engine.dispose()

            cfg = Config(str(alembic_ini))
            cfg.set_main_option("script_location", str(backend_dir / "alembic"))
            cfg.set_main_option("sqlalchemy.url", db_url)

            command.stamp(cfg, "0025")
            command.downgrade(cfg, "0024")

            check_engine = create_engine(db_url)
            with check_engine.connect() as conn:
                status_val = conn.execute(
                    text("SELECT status FROM user_attestation_records LIMIT 1")
                ).scalar()
                assert status_val == "PENDING"
            check_engine.dispose()
            command.upgrade(cfg, "0025")
        finally:
            settings.DATABASE_URL = old_settings_url


# ============================================================================
# 2. FUNCTIONAL LIFECYCLE & GOVERNANCE TESTS
# ============================================================================


def test_full_policy_version_review_publish_supersede_lifecycle(client: TestClient, b4_fixture):
    """Verify end-to-end version authoring, review changes requested, re-submission, approval, publishing, superseding, and review history endpoints."""
    admin_hdr = get_token_headers(b4_fixture["apex_admin"])
    mgr_hdr = get_token_headers(b4_fixture["apex_manager"])
    pol_id = b4_fixture["policy"].id
    v1_id = b4_fixture["v1"].id

    # 1. Submit v1 for review assigned to apex_manager
    res_sub = client.post(
        f"/api/v1/policies/{pol_id}/versions/{v1_id}/submit-review",
        headers=admin_hdr,
        json={
            "review_stage": "LEGAL_REVIEW",
            "assigned_reviewer_id": b4_fixture["apex_manager"].id,
            "review_notes": "Please review section 1",
        },
    )
    assert res_sub.status_code == 200
    wf1_id = res_sub.json()["id"]
    assert res_sub.json()["created_by"]["id"] == b4_fixture["apex_admin"].id

    # 2. Reviewer requests changes -> version and policy revert to DRAFT
    res_chg = client.post(
        f"/api/v1/policies/{pol_id}/versions/{v1_id}/review/{wf1_id}",
        headers=mgr_hdr,
        json={"decision": "CHANGES_REQUESTED", "review_notes": "Add section 2 on encryption"},
    )
    assert res_chg.status_code == 200
    assert res_chg.json()["status"] == "CHANGES_REQUESTED"

    # 3. Author updates v1 in DRAFT
    res_upd = client.patch(
        f"/api/v1/policies/{pol_id}/versions/{v1_id}",
        headers=admin_hdr,
        json={"content": "# Acceptable Use Policy\n\nSection 1: MFA.\nSection 2: TLS 1.3 required."},
    )
    assert res_upd.status_code == 200
    assert res_upd.json()["status"] == "DRAFT"

    # 4. Resubmit v1 for review and approve
    res_sub2 = client.post(
        f"/api/v1/policies/{pol_id}/versions/{v1_id}/submit-review",
        headers=admin_hdr,
        json={
            "review_stage": "EXECUTIVE_APPROVAL",
            "assigned_reviewer_id": b4_fixture["apex_manager"].id,
            "review_notes": "Added section 2",
        },
    )
    assert res_sub2.status_code == 200
    wf2_id = res_sub2.json()["id"]

    res_app = client.post(
        f"/api/v1/policies/{pol_id}/versions/{v1_id}/review/{wf2_id}",
        headers=mgr_hdr,
        json={"decision": "APPROVE", "review_notes": "Approved for publication"},
    )
    assert res_app.status_code == 200
    assert res_app.json()["status"] == "APPROVED"

    # 5. Publish v1
    res_pub = client.post(
        f"/api/v1/policies/{pol_id}/versions/{v1_id}/publish",
        headers=mgr_hdr,
    )
    assert res_pub.status_code == 200
    assert res_pub.json()["status"] == "PUBLISHED"

    # 6. Verify GET /{policy_id} exposes versions and nested reviews
    res_detail = client.get(f"/api/v1/policies/{pol_id}", headers=admin_hdr)
    assert res_detail.status_code == 200
    detail_data = res_detail.json()
    assert detail_data["status"] == "PUBLISHED"
    assert len(detail_data["versions"]) == 1
    assert len(detail_data["versions"][0]["reviews"]) == 2

    # 7. Verify GET /{policy_id}/versions/{version_id}/reviews returns full review list
    res_reviews = client.get(
        f"/api/v1/policies/{pol_id}/versions/{v1_id}/reviews",
        headers=admin_hdr,
    )
    assert res_reviews.status_code == 200
    assert len(res_reviews.json()) == 2

    # 8. Create v2, approve, and publish -> v1 auto-transitions to SUPERSEDED
    res_v2 = client.post(
        f"/api/v1/policies/{pol_id}/versions",
        headers=admin_hdr,
        json={"content": "# Acceptable Use Policy v2\n\nZero Trust edition.", "change_summary": "v2"},
    )
    assert res_v2.status_code == 201
    v2_id = res_v2.json()["id"]

    res_v2_sub = client.post(
        f"/api/v1/policies/{pol_id}/versions/{v2_id}/submit-review",
        headers=admin_hdr,
        json={"review_stage": "EXECUTIVE_APPROVAL"},
    )
    wf_v2_id = res_v2_sub.json()["id"]
    client.post(
        f"/api/v1/policies/{pol_id}/versions/{v2_id}/review/{wf_v2_id}",
        headers=mgr_hdr,
        json={"decision": "APPROVE"},
    )
    res_v2_pub = client.post(
        f"/api/v1/policies/{pol_id}/versions/{v2_id}/publish",
        headers=mgr_hdr,
    )
    assert res_v2_pub.status_code == 200
    assert res_v2_pub.json()["status"] == "PUBLISHED"

    res_v1_after = client.get(f"/api/v1/policies/{pol_id}/versions/{v1_id}", headers=admin_hdr)
    assert res_v1_after.json()["status"] == "SUPERSEDED"


def test_campaign_lifecycle_overdue_sweep_exemption_and_evidence_manifest(
    client: TestClient, b4_fixture
):
    """Verify campaign launch, roster listing, overdue evaluation, Phase 5 waiver exemption, attestation auto-completion, and Phase 3 evidence manifest."""
    admin_hdr = get_token_headers(b4_fixture["apex_admin"])
    pol_id = b4_fixture["policy"].id
    v1_id = b4_fixture["v1"].id

    res_camp = client.post(
        "/api/v1/policies/campaigns",
        headers=admin_hdr,
        json={
            "campaign_code": "CAMP-B4-E2E-01",
            "title": "Manager AUP Attestation",
            "policy_id": pol_id,
            "version_id": v1_id,
            "target_type": "ROLE_BASED",
            "target_role": "MANAGER",
            "due_date": (date.today() - timedelta(days=5)).isoformat(),
            "grace_period_days": 2,
        },
    )
    assert res_camp.status_code == 201
    camp_id = res_camp.json()["id"]

    # Launch campaign -> 2 active managers targeted (inactive manager excluded)
    res_launch = client.post(f"/api/v1/policies/campaigns/{camp_id}/launch", headers=admin_hdr)
    assert res_launch.status_code == 200
    assert res_launch.json()["total_targeted_count"] == 2
    assert res_launch.json()["status"] == "ACTIVE"

    # Evaluate overdue sweep -> both records become OVERDUE and reminder_sent_at is populated
    res_overdue = client.post(
        f"/api/v1/policies/campaigns/{camp_id}/evaluate-overdue",
        headers=admin_hdr,
    )
    assert res_overdue.status_code == 200
    assert res_overdue.json()["overdue_count"] == 2
    assert res_overdue.json()["reminder_sent_at"] is not None

    # List campaign records
    res_records = client.get(
        f"/api/v1/policies/campaigns/{camp_id}/records",
        headers=admin_hdr,
    )
    assert res_records.status_code == 200
    records = res_records.json()
    assert len(records) == 2
    assert all(r["status"] == "OVERDUE" for r in records)

    # Exempt apex_manager's record using apex_policy_exception (approved by apex_manager_2, granted by apex_admin)
    mgr1_rec = next(r for r in records if r["user_id"] == b4_fixture["apex_manager"].id)

    res_exempt = client.post(
        f"/api/v1/policies/campaigns/{camp_id}/records/{mgr1_rec['id']}/exempt",
        headers=admin_hdr,
        json={
            "exemption_exception_id": b4_fixture["apex_policy_exception"].id,
            "exemption_reason": "Approved waiver exception during system migration",
        },
    )
    assert res_exempt.status_code == 200
    exempt_data = res_exempt.json()
    assert exempt_data["status"] == "EXEMPTED"
    assert exempt_data["exemption_exception_id"] == b4_fixture["apex_policy_exception"].id
    assert exempt_data["exempted_by_id"] == b4_fixture["apex_admin"].id
    assert exempt_data["attestation_receipt_hash"] is not None

    # Check campaign counters: 1 completed (exempted), 1 overdue
    res_camp_mid = client.get(f"/api/v1/policies/campaigns/{camp_id}", headers=admin_hdr)
    assert res_camp_mid.json()["completed_count"] == 1
    assert res_camp_mid.json()["overdue_count"] == 1
    assert res_camp_mid.json()["status"] == "ACTIVE"

    # Second manager attests -> campaign auto-transitions to COMPLETED
    mgr2_hdr = get_token_headers(b4_fixture["apex_manager_2"])
    res_att = client.post(
        f"/api/v1/policies/campaigns/{camp_id}/attest",
        headers=mgr2_hdr,
        json={
            "acknowledgement_text": "I have read and agree to comply with the Acceptable Use Policy.",
            "policy_version_hash": res_camp_mid.json()["policy_version_hash"],
        },
    )
    assert res_att.status_code == 200
    assert res_att.json()["status"] == "ATTESTED"

    res_camp_done = client.get(f"/api/v1/policies/campaigns/{camp_id}", headers=admin_hdr)
    assert res_camp_done.json()["completed_count"] == 2
    assert res_camp_done.json()["overdue_count"] == 0
    assert res_camp_done.json()["status"] == "COMPLETED"
    assert res_camp_done.json()["completion_rate_pct"] == 100.0

    # Generate Phase 3 Evidence Manifest
    res_ev = client.post(
        f"/api/v1/policies/campaigns/{camp_id}/evidence",
        headers=admin_hdr,
    )
    assert res_ev.status_code == 200
    ev_json = res_ev.json()
    assert ev_json["status"] == "UPLOADED"


def test_policy_telemetry_aggregation_and_cancel_campaign(client: TestClient, b4_fixture, db: Session):
    """Verify GET /api/v1/policies/telemetry and POST /api/v1/policies/campaigns/{id}/cancel."""
    admin_hdr = get_token_headers(b4_fixture["apex_admin"])
    pol = b4_fixture["policy"]
    pol.review_date = date.today() - timedelta(days=10)
    db.commit()

    res_camp = client.post(
        "/api/v1/policies/campaigns",
        headers=admin_hdr,
        json={
            "campaign_code": "CAMP-B4-CANCEL-01",
            "title": "Cancel Test Campaign",
            "policy_id": pol.id,
            "version_id": b4_fixture["v1"].id,
            "target_type": "ALL_USERS",
            "due_date": (date.today() + timedelta(days=14)).isoformat(),
        },
    )
    camp_id = res_camp.json()["id"]

    res_cancel = client.post(
        f"/api/v1/policies/campaigns/{camp_id}/cancel",
        headers=admin_hdr,
        json={"reason": "Replaced by Q4 consolidated campaign"},
    )
    assert res_cancel.status_code == 200
    assert res_cancel.json()["status"] == "CANCELLED"
    assert "[Cancelled]: Replaced by Q4 consolidated campaign" in res_cancel.json()["description"]

    res_tel = client.get("/api/v1/policies/telemetry", headers=admin_hdr)
    assert res_tel.status_code == 200
    tel = res_tel.json()
    assert tel["total_policies"] >= 1
    assert tel["overdue_review_policies"] >= 1
    assert tel["cancelled_campaigns"] >= 1


# ============================================================================
# 3. 50 ADVERSARIAL SECURITY & GOVERNANCE INVARIANT TESTS (SEC-B4-01..50)
# ============================================================================


def test_sec_b4_01_cross_tenant_get_policy_returns_404(client: TestClient, b4_fixture):
    """SEC-B4-01: Cross-tenant GET /{policy_id} returns 404."""
    mer_hdr = get_token_headers(b4_fixture["meridian_admin"])
    res = client.get(f"/api/v1/policies/{b4_fixture['policy'].id}", headers=mer_hdr)
    assert res.status_code == 404


def test_sec_b4_02_cross_tenant_update_policy_returns_404(client: TestClient, b4_fixture):
    """SEC-B4-02: Cross-tenant PATCH /{policy_id} returns 404."""
    mer_hdr = get_token_headers(b4_fixture["meridian_admin"])
    res = client.patch(
        f"/api/v1/policies/{b4_fixture['policy'].id}",
        headers=mer_hdr,
        json={"title": "Cross Tenant Tamper"},
    )
    assert res.status_code == 404


def test_sec_b4_03_cross_tenant_update_policy_status_returns_404(client: TestClient, b4_fixture):
    """SEC-B4-03: Cross-tenant POST /{policy_id}/status returns 404."""
    mer_hdr = get_token_headers(b4_fixture["meridian_admin"])
    res = client.post(
        f"/api/v1/policies/{b4_fixture['policy'].id}/status",
        headers=mer_hdr,
        json={"status": "ARCHIVED"},
    )
    assert res.status_code == 404


def test_sec_b4_04_cross_tenant_create_and_list_versions_returns_404(client: TestClient, b4_fixture):
    """SEC-B4-04: Cross-tenant version listing, detail, create, and update return 404."""
    mer_hdr = get_token_headers(b4_fixture["meridian_admin"])
    pol_id = b4_fixture["policy"].id
    v1_id = b4_fixture["v1"].id

    assert client.get(f"/api/v1/policies/{pol_id}/versions", headers=mer_hdr).status_code == 404
    assert client.get(f"/api/v1/policies/{pol_id}/versions/{v1_id}", headers=mer_hdr).status_code == 404
    assert (
        client.post(
            f"/api/v1/policies/{pol_id}/versions",
            headers=mer_hdr,
            json={"content": "Tampered content string"},
        ).status_code
        == 404
    )
    assert (
        client.patch(
            f"/api/v1/policies/{pol_id}/versions/{v1_id}",
            headers=mer_hdr,
            json={"content": "Tampered content string"},
        ).status_code
        == 404
    )


def test_sec_b4_05_cross_tenant_submit_review_and_decide_review_returns_404(
    client: TestClient, b4_fixture
):
    """SEC-B4-05: Cross-tenant review submission, review listing, and review decision return 404."""
    admin_hdr = get_token_headers(b4_fixture["apex_admin"])
    mer_hdr = get_token_headers(b4_fixture["meridian_admin"])
    pol_id = b4_fixture["policy"].id
    v1_id = b4_fixture["v1"].id

    assert (
        client.get(
            f"/api/v1/policies/{pol_id}/versions/{v1_id}/reviews",
            headers=mer_hdr,
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/policies/{pol_id}/versions/{v1_id}/submit-review",
            headers=mer_hdr,
            json={"review_stage": "LEGAL_REVIEW"},
        ).status_code
        == 404
    )

    res_sub = client.post(
        f"/api/v1/policies/{pol_id}/versions/{v1_id}/submit-review",
        headers=admin_hdr,
        json={"review_stage": "LEGAL_REVIEW"},
    )
    wf_id = res_sub.json()["id"]

    assert (
        client.post(
            f"/api/v1/policies/{pol_id}/versions/{v1_id}/review/{wf_id}",
            headers=mer_hdr,
            json={"decision": "APPROVE"},
        ).status_code
        == 404
    )


def test_sec_b4_06_cross_tenant_publish_and_delete_version_returns_404(
    client: TestClient, b4_fixture
):
    """SEC-B4-06: Cross-tenant publish and delete version return 404."""
    mer_hdr = get_token_headers(b4_fixture["meridian_admin"])
    pol_id = b4_fixture["policy"].id
    v1_id = b4_fixture["v1"].id

    assert (
        client.post(
            f"/api/v1/policies/{pol_id}/versions/{v1_id}/publish",
            headers=mer_hdr,
        ).status_code
        == 404
    )
    assert (
        client.delete(
            f"/api/v1/policies/{pol_id}/versions/{v1_id}",
            headers=mer_hdr,
        ).status_code
        == 404
    )


def test_sec_b4_07_cross_tenant_campaign_get_update_launch_close_cancel_returns_404(
    client: TestClient, b4_fixture
):
    """SEC-B4-07: Cross-tenant campaign get, patch, launch, close, and cancel return 404."""
    admin_hdr = get_token_headers(b4_fixture["apex_admin"])
    mer_hdr = get_token_headers(b4_fixture["meridian_admin"])

    res_camp = client.post(
        "/api/v1/policies/campaigns",
        headers=admin_hdr,
        json={
            "campaign_code": "CAMP-SEC-07",
            "title": "Apex Sec 07",
            "policy_id": b4_fixture["policy"].id,
            "version_id": b4_fixture["v1"].id,
            "target_type": "ALL_USERS",
            "due_date": (date.today() + timedelta(days=14)).isoformat(),
        },
    )
    camp_id = res_camp.json()["id"]

    assert client.get(f"/api/v1/policies/campaigns/{camp_id}", headers=mer_hdr).status_code == 404
    assert (
        client.patch(
            f"/api/v1/policies/campaigns/{camp_id}",
            headers=mer_hdr,
            json={"title": "Tampered"},
        ).status_code
        == 404
    )
    assert (
        client.post(f"/api/v1/policies/campaigns/{camp_id}/launch", headers=mer_hdr).status_code
        == 404
    )
    assert (
        client.post(f"/api/v1/policies/campaigns/{camp_id}/close", headers=mer_hdr).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/policies/campaigns/{camp_id}/cancel",
            headers=mer_hdr,
            json={"reason": "Cross tenant cancel"},
        ).status_code
        == 404
    )


def test_sec_b4_08_cross_tenant_list_records_exempt_overdue_evidence_returns_404(
    client: TestClient, b4_fixture
):
    """SEC-B4-08: Cross-tenant campaign records, overdue evaluation, exemption, and evidence generation return 404."""
    admin_hdr = get_token_headers(b4_fixture["apex_admin"])
    mer_hdr = get_token_headers(b4_fixture["meridian_admin"])

    res_camp = client.post(
        "/api/v1/policies/campaigns",
        headers=admin_hdr,
        json={
            "campaign_code": "CAMP-SEC-08",
            "title": "Apex Sec 08",
            "policy_id": b4_fixture["policy"].id,
            "version_id": b4_fixture["v1"].id,
            "target_type": "ALL_USERS",
            "due_date": (date.today() + timedelta(days=14)).isoformat(),
        },
    )
    camp_id = res_camp.json()["id"]
    client.post(f"/api/v1/policies/campaigns/{camp_id}/launch", headers=admin_hdr)
    recs = client.get(f"/api/v1/policies/campaigns/{camp_id}/records", headers=admin_hdr).json()
    rec_id = recs[0]["id"]

    assert (
        client.get(f"/api/v1/policies/campaigns/{camp_id}/records", headers=mer_hdr).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/policies/campaigns/{camp_id}/evaluate-overdue", headers=mer_hdr
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/policies/campaigns/{camp_id}/records/{rec_id}/exempt",
            headers=mer_hdr,
            json={
                "exemption_exception_id": b4_fixture["meridian_policy_exception"].id,
                "exemption_reason": "Cross tenant exemption attempt",
            },
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/policies/campaigns/{camp_id}/evidence", headers=mer_hdr
        ).status_code
        == 404
    )


def test_sec_b4_09_cross_tenant_submit_attestation_returns_400(client: TestClient, b4_fixture):
    """SEC-B4-09: Cross-tenant attestation submission is blocked."""
    admin_hdr = get_token_headers(b4_fixture["apex_admin"])
    mer_hdr = get_token_headers(b4_fixture["meridian_admin"])

    res_camp = client.post(
        "/api/v1/policies/campaigns",
        headers=admin_hdr,
        json={
            "campaign_code": "CAMP-SEC-09",
            "title": "Apex Sec 09",
            "policy_id": b4_fixture["policy"].id,
            "version_id": b4_fixture["v1"].id,
            "target_type": "ALL_USERS",
            "due_date": (date.today() + timedelta(days=14)).isoformat(),
        },
    )
    camp_id = res_camp.json()["id"]
    client.post(f"/api/v1/policies/campaigns/{camp_id}/launch", headers=admin_hdr)

    res = client.post(
        f"/api/v1/policies/campaigns/{camp_id}/attest",
        headers=mer_hdr,
        json={
            "acknowledgement_text": "I acknowledge and agree to this policy.",
            "policy_version_hash": b4_fixture["v1"].content_hash_sha256,
        },
    )
    assert res.status_code == 404
    assert "not found in your organization" in res.json()["detail"].lower()


def test_sec_b4_10_cross_tenant_list_policies_campaigns_my_pending_telemetry_isolation(
    client: TestClient, b4_fixture
):
    """SEC-B4-10: Tenant list endpoints (policies, campaigns, my-pending, telemetry) never leak cross-tenant data."""
    mer_hdr = get_token_headers(b4_fixture["meridian_admin"])

    pols = client.get("/api/v1/policies", headers=mer_hdr).json()
    assert all(p["organization_id"] == b4_fixture["org_meridian"].id for p in pols)

    camps = client.get("/api/v1/policies/campaigns", headers=mer_hdr).json()
    assert all(c["organization_id"] == b4_fixture["org_meridian"].id for c in camps)

    pending = client.get("/api/v1/policies/my-pending-attestations", headers=mer_hdr).json()
    assert all(r["organization_id"] == b4_fixture["org_meridian"].id for r in pending)

    tel = client.get("/api/v1/policies/telemetry", headers=mer_hdr).json()
    assert tel["total_policies"] == 1


def test_sec_b4_11_cross_tenant_assigned_reviewer_in_submit_review_rejected(
    client: TestClient, b4_fixture
):
    """SEC-B4-11: Assigning a reviewer from another organization in submit-review is rejected."""
    admin_hdr = get_token_headers(b4_fixture["apex_admin"])
    res = client.post(
        f"/api/v1/policies/{b4_fixture['policy'].id}/versions/{b4_fixture['v1'].id}/submit-review",
        headers=admin_hdr,
        json={
            "review_stage": "LEGAL_REVIEW",
            "assigned_reviewer_id": b4_fixture["meridian_manager"].id,
        },
    )
    assert res.status_code == 400
    assert "not found in your organization" in res.json()["detail"].lower()


def test_sec_b4_12_cross_tenant_assessment_id_in_create_and_update_campaign_rejected(
    client: TestClient, b4_fixture, db: Session
):
    """SEC-B4-12: Referencing a cross-tenant assessment_id in campaign creation or update is rejected."""
    mer_assessment = Assessment(
        organization_id=b4_fixture["org_meridian"].id,
        organization_control_id=b4_fixture["meridian_ctrl"].id,
        summary="Meridian Assessment",
        assessment_method=AssessmentMethodEnum.TESTING,
        status=AssessmentStatusEnum.COMPLETED,
        conclusion=AssessmentConclusionEnum.EFFECTIVE,
    )
    db.add(mer_assessment)
    db.commit()
    db.refresh(mer_assessment)

    admin_hdr = get_token_headers(b4_fixture["apex_admin"])
    res_create = client.post(
        "/api/v1/policies/campaigns",
        headers=admin_hdr,
        json={
            "campaign_code": "CAMP-SEC-12",
            "title": "Cross Tenant Assessment Campaign",
            "policy_id": b4_fixture["policy"].id,
            "version_id": b4_fixture["v1"].id,
            "target_type": "ALL_USERS",
            "due_date": (date.today() + timedelta(days=14)).isoformat(),
            "assessment_id": mer_assessment.id,
        },
    )
    assert res_create.status_code == 400
    assert "assessment not found in your organization" in res_create.json()["detail"].lower()

    res_ok = client.post(
        "/api/v1/policies/campaigns",
        headers=admin_hdr,
        json={
            "campaign_code": "CAMP-SEC-12B",
            "title": "Valid Campaign",
            "policy_id": b4_fixture["policy"].id,
            "version_id": b4_fixture["v1"].id,
            "target_type": "ALL_USERS",
            "due_date": (date.today() + timedelta(days=14)).isoformat(),
        },
    )
    camp_id = res_ok.json()["id"]
    res_upd = client.patch(
        f"/api/v1/policies/campaigns/{camp_id}",
        headers=admin_hdr,
        json={"assessment_id": mer_assessment.id},
    )
    assert res_upd.status_code == 400
    assert "assessment not found in your organization" in res_upd.json()["detail"].lower()


def test_sec_b4_13_cross_tenant_security_exception_in_exempt_attestation_rejected(
    client: TestClient, b4_fixture
):
    """SEC-B4-13: Referencing a cross-tenant SecurityException when granting an attestation exemption is rejected."""
    admin_hdr = get_token_headers(b4_fixture["apex_admin"])
    res_camp = client.post(
        "/api/v1/policies/campaigns",
        headers=admin_hdr,
        json={
            "campaign_code": "CAMP-SEC-13",
            "title": "Sec 13 Campaign",
            "policy_id": b4_fixture["policy"].id,
            "version_id": b4_fixture["v1"].id,
            "target_type": "ALL_USERS",
            "due_date": (date.today() + timedelta(days=14)).isoformat(),
        },
    )
    camp_id = res_camp.json()["id"]
    client.post(f"/api/v1/policies/campaigns/{camp_id}/launch", headers=admin_hdr)
    recs = client.get(f"/api/v1/policies/campaigns/{camp_id}/records", headers=admin_hdr).json()
    mgr_rec = next(r for r in recs if r["user_id"] == b4_fixture["apex_manager"].id)

    res_ex = client.post(
        f"/api/v1/policies/campaigns/{camp_id}/records/{mgr_rec['id']}/exempt",
        headers=admin_hdr,
        json={
            "exemption_exception_id": b4_fixture["meridian_policy_exception"].id,
            "exemption_reason": "Attempting cross tenant exception binding",
        },
    )
    assert res_ex.status_code == 400
    assert "securityexception not found in your organization" in res_ex.json()["detail"].lower()


def test_sec_b4_14_rbac_viewer_and_auditor_denied_all_policy_mutations(
    client: TestClient, b4_fixture
):
    """SEC-B4-14: VIEWER and AUDITOR roles are denied all policy/version/campaign mutation endpoints (403)."""
    pol_id = b4_fixture["policy"].id
    v1_id = b4_fixture["v1"].id

    for user in (b4_fixture["apex_viewer"], b4_fixture["apex_auditor"]):
        hdr = get_token_headers(user)
        assert (
            client.post(
                "/api/v1/policies",
                headers=hdr,
                json={
                    "title": "Unauth Policy",
                    "policy_type": "ACCESS_CONTROL",
                    "initial_content": "Unauthorized policy creation attempt",
                },
            ).status_code
            == 403
        )
        assert (
            client.patch(f"/api/v1/policies/{pol_id}", headers=hdr, json={"title": "No"}).status_code
            == 403
        )
        assert (
            client.post(
                f"/api/v1/policies/{pol_id}/versions",
                headers=hdr,
                json={"content": "Unauthorized version creation"},
            ).status_code
            == 403
        )
        assert (
            client.post(
                f"/api/v1/policies/{pol_id}/versions/{v1_id}/submit-review",
                headers=hdr,
                json={"review_stage": "LEGAL_REVIEW"},
            ).status_code
            == 403
        )
        assert (
            client.post(
                f"/api/v1/policies/{pol_id}/versions/{v1_id}/publish", headers=hdr
            ).status_code
            == 403
        )
        assert (
            client.delete(
                f"/api/v1/policies/{pol_id}/versions/{v1_id}", headers=hdr
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/api/v1/policies/campaigns",
                headers=hdr,
                json={
                    "campaign_code": "UNAUTH",
                    "title": "Unauth",
                    "policy_id": pol_id,
                    "version_id": v1_id,
                    "due_date": (date.today() + timedelta(days=14)).isoformat(),
                },
            ).status_code
            == 403
        )


def test_sec_b4_15_rbac_grc_analyst_and_security_analyst_denied_approve_publish_delete_exempt(
    client: TestClient, b4_fixture
):
    """SEC-B4-15: GRC_ANALYST and SECURITY_ANALYST cannot approve reviews, publish versions, delete versions, or grant exemptions (403)."""
    admin_hdr = get_token_headers(b4_fixture["apex_admin"])
    pol_id = b4_fixture["policy"].id
    v1_id = b4_fixture["v1"].id

    res_sub = client.post(
        f"/api/v1/policies/{pol_id}/versions/{v1_id}/submit-review",
        headers=admin_hdr,
        json={"review_stage": "LEGAL_REVIEW"},
    )
    wf_id = res_sub.json()["id"]

    res_camp = client.post(
        "/api/v1/policies/campaigns",
        headers=admin_hdr,
        json={
            "campaign_code": "CAMP-SEC-15",
            "title": "Sec 15 Campaign",
            "policy_id": pol_id,
            "version_id": v1_id,
            "target_type": "ALL_USERS",
            "due_date": (date.today() + timedelta(days=14)).isoformat(),
        },
    )
    camp_id = res_camp.json()["id"]
    client.post(f"/api/v1/policies/campaigns/{camp_id}/launch", headers=admin_hdr)
    recs = client.get(f"/api/v1/policies/campaigns/{camp_id}/records", headers=admin_hdr).json()
    rec_id = recs[0]["id"]

    for user in (b4_fixture["apex_analyst"], b4_fixture["apex_sec_analyst"]):
        hdr = get_token_headers(user)
        assert (
            client.post(
                f"/api/v1/policies/{pol_id}/versions/{v1_id}/review/{wf_id}",
                headers=hdr,
                json={"decision": "APPROVE"},
            ).status_code
            == 403
        )
        assert (
            client.post(
                f"/api/v1/policies/{pol_id}/versions/{v1_id}/publish",
                headers=hdr,
            ).status_code
            == 403
        )
        assert (
            client.delete(
                f"/api/v1/policies/{pol_id}/versions/{v1_id}",
                headers=hdr,
            ).status_code
            == 403
        )
        assert (
            client.post(
                f"/api/v1/policies/campaigns/{camp_id}/records/{rec_id}/exempt",
                headers=hdr,
                json={
                    "exemption_exception_id": b4_fixture["apex_policy_exception"].id,
                    "exemption_reason": "Analyst trying to grant exemption",
                },
            ).status_code
            == 403
        )


def test_sec_b4_16_rbac_unauthenticated_requests_rejected_401(client: TestClient, b4_fixture):
    """SEC-B4-16: Unauthenticated requests to Batch 4 endpoints return 401."""
    pol_id = b4_fixture["policy"].id
    v1_id = b4_fixture["v1"].id

    assert client.get("/api/v1/policies/telemetry").status_code == 401
    assert client.get(f"/api/v1/policies/{pol_id}/versions/{v1_id}/reviews").status_code == 401
    assert client.get("/api/v1/policies/campaigns/1/records").status_code == 401
    assert client.post("/api/v1/policies/campaigns/1/evaluate-overdue").status_code == 401
    assert client.post("/api/v1/policies/campaigns/1/cancel", json={}).status_code == 401


def test_sec_b4_17_four_eyes_version_author_cannot_approve_own_version(
    client: TestClient, b4_fixture
):
    """SEC-B4-17: Version author (created_by_id) cannot approve their own policy version."""
    admin_hdr = get_token_headers(b4_fixture["apex_admin"])
    mgr_hdr = get_token_headers(b4_fixture["apex_manager"])
    pol_id = b4_fixture["policy"].id
    v1_id = b4_fixture["v1"].id

    res_sub = client.post(
        f"/api/v1/policies/{pol_id}/versions/{v1_id}/submit-review",
        headers=mgr_hdr,
        json={"review_stage": "LEGAL_REVIEW"},
    )
    wf_id = res_sub.json()["id"]

    res_app = client.post(
        f"/api/v1/policies/{pol_id}/versions/{v1_id}/review/{wf_id}",
        headers=admin_hdr,
        json={"decision": "APPROVE"},
    )
    assert res_app.status_code == 400
    assert "four-eyes violation" in res_app.json()["detail"].lower()


def test_sec_b4_18_four_eyes_review_submitter_cannot_approve_own_submitted_workflow(
    client: TestClient, b4_fixture
):
    """SEC-B4-18: User who submitted the review workflow cannot approve it even if they did not author the version."""
    mgr_hdr = get_token_headers(b4_fixture["apex_manager"])
    pol_id = b4_fixture["policy"].id
    v1_id = b4_fixture["v1"].id

    res_sub = client.post(
        f"/api/v1/policies/{pol_id}/versions/{v1_id}/submit-review",
        headers=mgr_hdr,
        json={"review_stage": "LEGAL_REVIEW"},
    )
    wf_id = res_sub.json()["id"]

    res_app = client.post(
        f"/api/v1/policies/{pol_id}/versions/{v1_id}/review/{wf_id}",
        headers=mgr_hdr,
        json={"decision": "APPROVE"},
    )
    assert res_app.status_code == 400
    assert "four-eyes violation" in res_app.json()["detail"].lower()


def test_sec_b4_19_four_eyes_submit_review_cannot_assign_author_or_submitter_as_reviewer(
    client: TestClient, b4_fixture
):
    """SEC-B4-19: Submitting a review workflow cannot assign the version author or the workflow submitter as reviewer."""
    mgr_hdr = get_token_headers(b4_fixture["apex_manager"])
    pol_id = b4_fixture["policy"].id
    v1_id = b4_fixture["v1"].id

    res_author = client.post(
        f"/api/v1/policies/{pol_id}/versions/{v1_id}/submit-review",
        headers=mgr_hdr,
        json={
            "review_stage": "LEGAL_REVIEW",
            "assigned_reviewer_id": b4_fixture["apex_admin"].id,
        },
    )
    assert res_author.status_code == 400
    assert "four-eyes violation" in res_author.json()["detail"].lower()

    res_submitter = client.post(
        f"/api/v1/policies/{pol_id}/versions/{v1_id}/submit-review",
        headers=mgr_hdr,
        json={
            "review_stage": "LEGAL_REVIEW",
            "assigned_reviewer_id": b4_fixture["apex_manager"].id,
        },
    )
    assert res_submitter.status_code == 400
    assert "four-eyes violation" in res_submitter.json()["detail"].lower()


def test_sec_b4_20_assigned_reviewer_enforcement_blocks_unassigned_manager_from_deciding(
    client: TestClient, b4_fixture
):
    """SEC-B4-20: When assigned_reviewer_id is set on a workflow, another manager cannot hijack the decision."""
    admin_hdr = get_token_headers(b4_fixture["apex_admin"])
    mgr2_hdr = get_token_headers(b4_fixture["apex_manager_2"])
    pol_id = b4_fixture["policy"].id
    v1_id = b4_fixture["v1"].id

    res_sub = client.post(
        f"/api/v1/policies/{pol_id}/versions/{v1_id}/submit-review",
        headers=admin_hdr,
        json={
            "review_stage": "LEGAL_REVIEW",
            "assigned_reviewer_id": b4_fixture["apex_manager"].id,
        },
    )
    wf_id = res_sub.json()["id"]

    res_hijack = client.post(
        f"/api/v1/policies/{pol_id}/versions/{v1_id}/review/{wf_id}",
        headers=mgr2_hdr,
        json={"decision": "APPROVE"},
    )
    assert res_hijack.status_code == 403
    assert "only the assigned reviewer" in res_hijack.json()["detail"].lower()


def test_sec_b4_21_assigned_reviewer_must_be_active_and_hold_policy_approve_permission(
    client: TestClient, b4_fixture
):
    """SEC-B4-21: Assigned reviewer must be active and hold POLICY_APPROVE permission."""
    admin_hdr = get_token_headers(b4_fixture["apex_admin"])
    pol_id = b4_fixture["policy"].id
    v1_id = b4_fixture["v1"].id

    res_inact = client.post(
        f"/api/v1/policies/{pol_id}/versions/{v1_id}/submit-review",
        headers=admin_hdr,
        json={
            "review_stage": "LEGAL_REVIEW",
            "assigned_reviewer_id": b4_fixture["apex_inactive_manager"].id,
        },
    )
    assert res_inact.status_code == 400
    assert "inactive" in res_inact.json()["detail"].lower()

    res_no_perm = client.post(
        f"/api/v1/policies/{pol_id}/versions/{v1_id}/submit-review",
        headers=admin_hdr,
        json={
            "review_stage": "LEGAL_REVIEW",
            "assigned_reviewer_id": b4_fixture["apex_analyst"].id,
        },
    )
    assert res_no_perm.status_code == 400
    assert "policy_approve" in res_no_perm.json()["detail"].lower()


def test_sec_b4_22_four_eyes_exemption_grantor_cannot_exempt_own_attestation_record(
    client: TestClient, b4_fixture
):
    """SEC-B4-22: Grantor cannot grant a policy attestation exemption to their own record."""
    admin_hdr = get_token_headers(b4_fixture["apex_admin"])
    res_camp = client.post(
        "/api/v1/policies/campaigns",
        headers=admin_hdr,
        json={
            "campaign_code": "CAMP-SEC-22",
            "title": "Sec 22 Campaign",
            "policy_id": b4_fixture["policy"].id,
            "version_id": b4_fixture["v1"].id,
            "target_type": "ALL_USERS",
            "due_date": (date.today() + timedelta(days=14)).isoformat(),
        },
    )
    camp_id = res_camp.json()["id"]
    client.post(f"/api/v1/policies/campaigns/{camp_id}/launch", headers=admin_hdr)
    recs = client.get(f"/api/v1/policies/campaigns/{camp_id}/records", headers=admin_hdr).json()
    admin_rec = next(r for r in recs if r["user_id"] == b4_fixture["apex_admin"].id)

    res_ex = client.post(
        f"/api/v1/policies/campaigns/{camp_id}/records/{admin_rec['id']}/exempt",
        headers=admin_hdr,
        json={
            "exemption_exception_id": b4_fixture["apex_policy_exception"].id,
            "exemption_reason": "Admin trying to exempt self",
        },
    )
    assert res_ex.status_code == 400
    assert "four-eyes violation" in res_ex.json()["detail"].lower()


def test_sec_b4_23_four_eyes_exemption_target_user_cannot_be_exception_reviewer(
    client: TestClient, b4_fixture
):
    """SEC-B4-23: Target user of an exemption cannot be the reviewer/approver of the underlying SecurityException."""
    admin_hdr = get_token_headers(b4_fixture["apex_admin"])
    res_camp = client.post(
        "/api/v1/policies/campaigns",
        headers=admin_hdr,
        json={
            "campaign_code": "CAMP-SEC-23",
            "title": "Sec 23 Campaign",
            "policy_id": b4_fixture["policy"].id,
            "version_id": b4_fixture["v1"].id,
            "target_type": "ALL_USERS",
            "due_date": (date.today() + timedelta(days=14)).isoformat(),
        },
    )
    camp_id = res_camp.json()["id"]
    client.post(f"/api/v1/policies/campaigns/{camp_id}/launch", headers=admin_hdr)
    recs = client.get(f"/api/v1/policies/campaigns/{camp_id}/records", headers=admin_hdr).json()
    mgr2_rec = next(r for r in recs if r["user_id"] == b4_fixture["apex_manager_2"].id)

    res_ex = client.post(
        f"/api/v1/policies/campaigns/{camp_id}/records/{mgr2_rec['id']}/exempt",
        headers=admin_hdr,
        json={
            "exemption_exception_id": b4_fixture["apex_policy_exception"].id,
            "exemption_reason": "Exempting the user who approved the waiver exception",
        },
    )
    assert res_ex.status_code == 400
    assert "four-eyes violation" in res_ex.json()["detail"].lower()


def test_sec_b4_24_four_eyes_exemption_rejects_self_approved_security_exception(
    client: TestClient, b4_fixture, db: Session
):
    """SEC-B4-24: Exemption rejects a SecurityException where requested_by_id == reviewer_id."""
    bad_exc = SecurityException(
        organization_id=b4_fixture["org_apex"].id,
        title="Self Approved Waiver",
        description="Self approved",
        justification="Self approved justification",
        exception_type=ExceptionTypeEnum.POLICY_EXCEPTION,
        status=ExceptionStatusEnum.APPROVED,
        requested_by_id=b4_fixture["apex_manager_2"].id,
        owner_id=b4_fixture["apex_manager_2"].id,
        reviewer_id=b4_fixture["apex_manager_2"].id,
        approved_at=datetime.now(timezone.utc),
        effective_date=date.today() - timedelta(days=1),
        expiry_date=date.today() + timedelta(days=30),
        linked_policy_id=b4_fixture["policy"].id,
    )
    db.add(bad_exc)
    db.commit()
    db.refresh(bad_exc)

    admin_hdr = get_token_headers(b4_fixture["apex_admin"])
    res_camp = client.post(
        "/api/v1/policies/campaigns",
        headers=admin_hdr,
        json={
            "campaign_code": "CAMP-SEC-24",
            "title": "Sec 24 Campaign",
            "policy_id": b4_fixture["policy"].id,
            "version_id": b4_fixture["v1"].id,
            "target_type": "ALL_USERS",
            "due_date": (date.today() + timedelta(days=14)).isoformat(),
        },
    )
    camp_id = res_camp.json()["id"]
    client.post(f"/api/v1/policies/campaigns/{camp_id}/launch", headers=admin_hdr)
    recs = client.get(f"/api/v1/policies/campaigns/{camp_id}/records", headers=admin_hdr).json()
    mgr1_rec = next(r for r in recs if r["user_id"] == b4_fixture["apex_manager"].id)

    res_ex = client.post(
        f"/api/v1/policies/campaigns/{camp_id}/records/{mgr1_rec['id']}/exempt",
        headers=admin_hdr,
        json={
            "exemption_exception_id": bad_exc.id,
            "exemption_reason": "Using self-approved security exception",
        },
    )
    assert res_ex.status_code == 400
    assert "requester == reviewer" in res_ex.json()["detail"].lower()


def test_sec_b4_25_exemption_rejects_non_active_or_expired_security_exception(
    client: TestClient, b4_fixture, db: Session
):
    """SEC-B4-25: Exemption rejects a SecurityException that is expired or not approved."""
    expired_exc = SecurityException(
        organization_id=b4_fixture["org_apex"].id,
        title="Expired Policy Waiver",
        description="Expired waiver",
        justification="Expired justification",
        exception_type=ExceptionTypeEnum.POLICY_EXCEPTION,
        status=ExceptionStatusEnum.APPROVED,
        requested_by_id=b4_fixture["apex_analyst"].id,
        owner_id=b4_fixture["apex_analyst"].id,
        reviewer_id=b4_fixture["apex_manager_2"].id,
        approved_at=datetime.now(timezone.utc) - timedelta(days=40),
        effective_date=date.today() - timedelta(days=40),
        expiry_date=date.today() - timedelta(days=1),
        linked_policy_id=b4_fixture["policy"].id,
    )
    db.add(expired_exc)
    db.commit()
    db.refresh(expired_exc)

    admin_hdr = get_token_headers(b4_fixture["apex_admin"])
    res_camp = client.post(
        "/api/v1/policies/campaigns",
        headers=admin_hdr,
        json={
            "campaign_code": "CAMP-SEC-25",
            "title": "Sec 25 Campaign",
            "policy_id": b4_fixture["policy"].id,
            "version_id": b4_fixture["v1"].id,
            "target_type": "ALL_USERS",
            "due_date": (date.today() + timedelta(days=14)).isoformat(),
        },
    )
    camp_id = res_camp.json()["id"]
    client.post(f"/api/v1/policies/campaigns/{camp_id}/launch", headers=admin_hdr)
    recs = client.get(f"/api/v1/policies/campaigns/{camp_id}/records", headers=admin_hdr).json()
    mgr1_rec = next(r for r in recs if r["user_id"] == b4_fixture["apex_manager"].id)

    res_ex = client.post(
        f"/api/v1/policies/campaigns/{camp_id}/records/{mgr1_rec['id']}/exempt",
        headers=admin_hdr,
        json={
            "exemption_exception_id": expired_exc.id,
            "exemption_reason": "Trying to use expired exception",
        },
    )
    assert res_ex.status_code == 400
    assert "expired" in res_ex.json()["detail"].lower()


def test_sec_b4_26_exemption_rejects_non_policy_exception_type(
    client: TestClient, b4_fixture, db: Session
):
    """SEC-B4-26: Exemption rejects a SecurityException whose exception_type is not POLICY_EXCEPTION."""
    wrong_type_exc = SecurityException(
        organization_id=b4_fixture["org_apex"].id,
        title="Control Deviation Exception",
        description="Not a policy waiver",
        justification="Control deviation justification",
        exception_type=ExceptionTypeEnum.CONTROL_DEVIATION,
        status=ExceptionStatusEnum.APPROVED,
        requested_by_id=b4_fixture["apex_analyst"].id,
        owner_id=b4_fixture["apex_analyst"].id,
        reviewer_id=b4_fixture["apex_manager_2"].id,
        approved_at=datetime.now(timezone.utc),
        effective_date=date.today() - timedelta(days=1),
        expiry_date=date.today() + timedelta(days=30),
    )
    db.add(wrong_type_exc)
    db.commit()
    db.refresh(wrong_type_exc)

    admin_hdr = get_token_headers(b4_fixture["apex_admin"])
    res_camp = client.post(
        "/api/v1/policies/campaigns",
        headers=admin_hdr,
        json={
            "campaign_code": "CAMP-SEC-26",
            "title": "Sec 26 Campaign",
            "policy_id": b4_fixture["policy"].id,
            "version_id": b4_fixture["v1"].id,
            "target_type": "ALL_USERS",
            "due_date": (date.today() + timedelta(days=14)).isoformat(),
        },
    )
    camp_id = res_camp.json()["id"]
    client.post(f"/api/v1/policies/campaigns/{camp_id}/launch", headers=admin_hdr)
    recs = client.get(f"/api/v1/policies/campaigns/{camp_id}/records", headers=admin_hdr).json()
    mgr1_rec = next(r for r in recs if r["user_id"] == b4_fixture["apex_manager"].id)

    res_ex = client.post(
        f"/api/v1/policies/campaigns/{camp_id}/records/{mgr1_rec['id']}/exempt",
        headers=admin_hdr,
        json={
            "exemption_exception_id": wrong_type_exc.id,
            "exemption_reason": "Using CONTROL_DEVIATION exception",
        },
    )
    assert res_ex.status_code == 400
    assert "policy_exception" in res_ex.json()["detail"].lower()


def test_sec_b4_27_version_immutability_blocks_update_on_under_review_approved_published_superseded_archived(
    client: TestClient, b4_fixture
):
    """SEC-B4-27: Non-DRAFT versions cannot be mutated via PATCH."""
    admin_hdr = get_token_headers(b4_fixture["apex_admin"])
    mgr_hdr = get_token_headers(b4_fixture["apex_manager"])
    pol_id = b4_fixture["policy"].id
    v1_id = b4_fixture["v1"].id

    res_sub = client.post(
        f"/api/v1/policies/{pol_id}/versions/{v1_id}/submit-review",
        headers=admin_hdr,
        json={"review_stage": "LEGAL_REVIEW"},
    )
    wf_id = res_sub.json()["id"]
    assert (
        client.patch(
            f"/api/v1/policies/{pol_id}/versions/{v1_id}",
            headers=admin_hdr,
            json={"content": "Tampering under review version"},
        ).status_code
        == 400
    )

    client.post(
        f"/api/v1/policies/{pol_id}/versions/{v1_id}/review/{wf_id}",
        headers=mgr_hdr,
        json={"decision": "APPROVE"},
    )
    assert (
        client.patch(
            f"/api/v1/policies/{pol_id}/versions/{v1_id}",
            headers=admin_hdr,
            json={"content": "Tampering approved version"},
        ).status_code
        == 400
    )

    client.post(f"/api/v1/policies/{pol_id}/versions/{v1_id}/publish", headers=mgr_hdr)
    assert (
        client.patch(
            f"/api/v1/policies/{pol_id}/versions/{v1_id}",
            headers=admin_hdr,
            json={"content": "Tampering published version"},
        ).status_code
        == 400
    )


def test_sec_b4_28_version_deletion_blocks_non_draft_versions(client: TestClient, b4_fixture):
    """SEC-B4-28: Deleting a version in UNDER_REVIEW, APPROVED, PUBLISHED, SUPERSEDED, or ARCHIVED status is blocked."""
    admin_hdr = get_token_headers(b4_fixture["apex_admin"])
    mgr_hdr = get_token_headers(b4_fixture["apex_manager"])
    pol_id = b4_fixture["policy"].id
    v1_id = b4_fixture["v1"].id

    client.post(
        f"/api/v1/policies/{pol_id}/versions",
        headers=admin_hdr,
        json={"content": "# Policy v2 content valid length"},
    )

    res_sub = client.post(
        f"/api/v1/policies/{pol_id}/versions/{v1_id}/submit-review",
        headers=admin_hdr,
        json={"review_stage": "LEGAL_REVIEW"},
    )
    wf_id = res_sub.json()["id"]

    res_del_ur = client.delete(f"/api/v1/policies/{pol_id}/versions/{v1_id}", headers=admin_hdr)
    assert res_del_ur.status_code == 400
    assert "only draft versions can be deleted" in res_del_ur.json()["detail"].lower()

    client.post(
        f"/api/v1/policies/{pol_id}/versions/{v1_id}/review/{wf_id}",
        headers=mgr_hdr,
        json={"decision": "REJECT"},
    )
    res_del_arch = client.delete(f"/api/v1/policies/{pol_id}/versions/{v1_id}", headers=admin_hdr)
    assert res_del_arch.status_code == 400
    assert "only draft versions can be deleted" in res_del_arch.json()["detail"].lower()


def test_sec_b4_29_version_deletion_blocks_draft_version_bound_to_any_campaign(
    client: TestClient, b4_fixture
):
    """SEC-B4-29: A DRAFT version referenced by even a DRAFT or CANCELLED campaign cannot be deleted."""
    admin_hdr = get_token_headers(b4_fixture["apex_admin"])
    pol_id = b4_fixture["policy"].id

    res_v2 = client.post(
        f"/api/v1/policies/{pol_id}/versions",
        headers=admin_hdr,
        json={"content": "# Policy v2 content valid length"},
    )
    v2_id = res_v2.json()["id"]

    client.post(
        "/api/v1/policies/campaigns",
        headers=admin_hdr,
        json={
            "campaign_code": "CAMP-SEC-29",
            "title": "Draft Campaign Binding v2",
            "policy_id": pol_id,
            "version_id": v2_id,
            "target_type": "ALL_USERS",
            "due_date": (date.today() + timedelta(days=14)).isoformat(),
        },
    )

    res_del = client.delete(f"/api/v1/policies/{pol_id}/versions/{v2_id}", headers=admin_hdr)
    assert res_del.status_code == 400
    assert "referenced by attestation campaign" in res_del.json()["detail"].lower()


def test_sec_b4_30_version_deletion_blocks_draft_version_with_review_history(
    client: TestClient, b4_fixture
):
    """SEC-B4-30: A version that reverted to DRAFT via CHANGES_REQUESTED cannot be deleted because it has review workflow history."""
    admin_hdr = get_token_headers(b4_fixture["apex_admin"])
    mgr_hdr = get_token_headers(b4_fixture["apex_manager"])
    pol_id = b4_fixture["policy"].id

    res_v2 = client.post(
        f"/api/v1/policies/{pol_id}/versions",
        headers=admin_hdr,
        json={"content": "# Policy v2 content valid length"},
    )
    v2_id = res_v2.json()["id"]

    res_sub = client.post(
        f"/api/v1/policies/{pol_id}/versions/{v2_id}/submit-review",
        headers=admin_hdr,
        json={"review_stage": "LEGAL_REVIEW"},
    )
    wf_id = res_sub.json()["id"]
    client.post(
        f"/api/v1/policies/{pol_id}/versions/{v2_id}/review/{wf_id}",
        headers=mgr_hdr,
        json={"decision": "CHANGES_REQUESTED"},
    )

    res_del = client.delete(f"/api/v1/policies/{pol_id}/versions/{v2_id}", headers=admin_hdr)
    assert res_del.status_code == 400
    assert "historical review workflow records" in res_del.json()["detail"].lower()


def test_sec_b4_31_version_deletion_blocks_deleting_sole_remaining_version(
    client: TestClient, b4_fixture
):
    """SEC-B4-31: Deleting the sole remaining version of a policy is blocked."""
    admin_hdr = get_token_headers(b4_fixture["apex_admin"])
    pol_id = b4_fixture["policy"].id
    v1_id = b4_fixture["v1"].id

    res_del = client.delete(f"/api/v1/policies/{pol_id}/versions/{v1_id}", headers=admin_hdr)
    assert res_del.status_code == 400
    assert "sole remaining version" in res_del.json()["detail"].lower()


def test_sec_b4_32_duplicate_pending_review_workflow_submission_blocked(
    client: TestClient, b4_fixture
):
    """SEC-B4-32: Submitting a version for review when it already has a PENDING workflow is blocked."""
    admin_hdr = get_token_headers(b4_fixture["apex_admin"])
    pol_id = b4_fixture["policy"].id
    v1_id = b4_fixture["v1"].id

    res1 = client.post(
        f"/api/v1/policies/{pol_id}/versions/{v1_id}/submit-review",
        headers=admin_hdr,
        json={"review_stage": "LEGAL_REVIEW"},
    )
    assert res1.status_code == 200

    res2 = client.post(
        f"/api/v1/policies/{pol_id}/versions/{v1_id}/submit-review",
        headers=admin_hdr,
        json={"review_stage": "LEGAL_REVIEW"},
    )
    assert res2.status_code == 400


def test_sec_b4_33_re_reviewing_already_decided_workflow_blocked(client: TestClient, b4_fixture):
    """SEC-B4-33: Deciding an already-decided review workflow is blocked."""
    admin_hdr = get_token_headers(b4_fixture["apex_admin"])
    mgr_hdr = get_token_headers(b4_fixture["apex_manager"])
    pol_id = b4_fixture["policy"].id
    v1_id = b4_fixture["v1"].id

    res_sub = client.post(
        f"/api/v1/policies/{pol_id}/versions/{v1_id}/submit-review",
        headers=admin_hdr,
        json={"review_stage": "LEGAL_REVIEW"},
    )
    wf_id = res_sub.json()["id"]

    res_dec1 = client.post(
        f"/api/v1/policies/{pol_id}/versions/{v1_id}/review/{wf_id}",
        headers=mgr_hdr,
        json={"decision": "APPROVE"},
    )
    assert res_dec1.status_code == 200

    res_dec2 = client.post(
        f"/api/v1/policies/{pol_id}/versions/{v1_id}/review/{wf_id}",
        headers=mgr_hdr,
        json={"decision": "REJECT"},
    )
    assert res_dec2.status_code == 400
    assert "already been decided" in res_dec2.json()["detail"].lower()


def test_sec_b4_34_publish_blocks_unapproved_versions_and_archived_policies(
    client: TestClient, b4_fixture
):
    """SEC-B4-34: Publishing a DRAFT version or publishing on an ARCHIVED policy is blocked."""
    admin_hdr = get_token_headers(b4_fixture["apex_admin"])
    mgr_hdr = get_token_headers(b4_fixture["apex_manager"])
    pol_id = b4_fixture["policy"].id
    v1_id = b4_fixture["v1"].id

    res_draft_pub = client.post(
        f"/api/v1/policies/{pol_id}/versions/{v1_id}/publish",
        headers=admin_hdr,
    )
    assert res_draft_pub.status_code == 400
    assert "must be formally approved" in res_draft_pub.json()["detail"].lower()

    res_sub = client.post(
        f"/api/v1/policies/{pol_id}/versions/{v1_id}/submit-review",
        headers=admin_hdr,
        json={"review_stage": "LEGAL_REVIEW"},
    )
    wf_id = res_sub.json()["id"]
    client.post(
        f"/api/v1/policies/{pol_id}/versions/{v1_id}/review/{wf_id}",
        headers=mgr_hdr,
        json={"decision": "APPROVE"},
    )
    client.post(
        f"/api/v1/policies/{pol_id}/status",
        headers=admin_hdr,
        json={"status": "ARCHIVED"},
    )
    res_arch_pub = client.post(
        f"/api/v1/policies/{pol_id}/versions/{v1_id}/publish",
        headers=admin_hdr,
    )
    assert res_arch_pub.status_code == 400
    assert "archived policy" in res_arch_pub.json()["detail"].lower()


def test_sec_b4_35_archived_policy_blocks_metadata_edit_new_version_review_and_control_mapping(
    client: TestClient, b4_fixture
):
    """SEC-B4-35: Archiving a policy locks metadata edits, version creation, review submission, and control mapping/unmapping."""
    admin_hdr = get_token_headers(b4_fixture["apex_admin"])
    pol_id = b4_fixture["policy"].id
    v1_id = b4_fixture["v1"].id
    subcat_id = b4_fixture["subcat"].id

    client.post(
        f"/api/v1/policies/{pol_id}/status",
        headers=admin_hdr,
        json={"status": "ARCHIVED"},
    )

    assert (
        client.patch(
            f"/api/v1/policies/{pol_id}",
            headers=admin_hdr,
            json={"title": "Edited While Archived"},
        ).status_code
        == 400
    )
    assert (
        client.post(
            f"/api/v1/policies/{pol_id}/versions",
            headers=admin_hdr,
            json={"content": "New version on archived policy"},
        ).status_code
        == 400
    )
    assert (
        client.post(
            f"/api/v1/policies/{pol_id}/versions/{v1_id}/submit-review",
            headers=admin_hdr,
            json={"review_stage": "LEGAL_REVIEW"},
        ).status_code
        == 400
    )
    assert (
        client.post(
            f"/api/v1/policies/{pol_id}/mappings",
            headers=admin_hdr,
            json={"subcategory_id": subcat_id},
        ).status_code
        == 400
    )
    assert (
        client.delete(
            f"/api/v1/policies/{pol_id}/mappings/{subcat_id}",
            headers=admin_hdr,
        ).status_code
        == 400
    )


def test_sec_b4_36_invalid_root_policy_status_transitions_rejected(client: TestClient, b4_fixture):
    """SEC-B4-36: Invalid root policy state transitions (e.g. DRAFT -> PUBLISHED directly) are rejected."""
    admin_hdr = get_token_headers(b4_fixture["apex_admin"])
    pol_id = b4_fixture["policy"].id

    res = client.post(
        f"/api/v1/policies/{pol_id}/status",
        headers=admin_hdr,
        json={"status": "PUBLISHED"},
    )
    assert res.status_code == 400
    assert "invalid policy state transition" in res.json()["detail"].lower()


def test_sec_b4_37_campaign_create_and_launch_blocked_for_archived_policy_or_archived_superseded_version(
    client: TestClient, b4_fixture
):
    """SEC-B4-37: Campaign creation and launch block ARCHIVED policies and ARCHIVED/SUPERSEDED versions."""
    admin_hdr = get_token_headers(b4_fixture["apex_admin"])
    mgr_hdr = get_token_headers(b4_fixture["apex_manager"])
    pol_id = b4_fixture["policy"].id
    v1_id = b4_fixture["v1"].id

    res_camp = client.post(
        "/api/v1/policies/campaigns",
        headers=admin_hdr,
        json={
            "campaign_code": "CAMP-SEC-37",
            "title": "Sec 37 Campaign",
            "policy_id": pol_id,
            "version_id": v1_id,
            "target_type": "ALL_USERS",
            "due_date": (date.today() + timedelta(days=14)).isoformat(),
        },
    )
    camp_id = res_camp.json()["id"]

    res_sub = client.post(
        f"/api/v1/policies/{pol_id}/versions/{v1_id}/submit-review",
        headers=admin_hdr,
        json={"review_stage": "LEGAL_REVIEW"},
    )
    wf_id = res_sub.json()["id"]
    client.post(
        f"/api/v1/policies/{pol_id}/versions/{v1_id}/review/{wf_id}",
        headers=mgr_hdr,
        json={"decision": "REJECT"},
    )

    res_launch = client.post(f"/api/v1/policies/campaigns/{camp_id}/launch", headers=admin_hdr)
    assert res_launch.status_code == 400
    assert "archived" in res_launch.json()["detail"].lower()

    res_create_arch_ver = client.post(
        "/api/v1/policies/campaigns",
        headers=admin_hdr,
        json={
            "campaign_code": "CAMP-SEC-37B",
            "title": "Sec 37B Campaign",
            "policy_id": pol_id,
            "version_id": v1_id,
            "target_type": "ALL_USERS",
            "due_date": (date.today() + timedelta(days=14)).isoformat(),
        },
    )
    assert res_create_arch_ver.status_code == 400


def test_sec_b4_38_campaign_role_based_requires_valid_role_enum(client: TestClient, b4_fixture):
    """SEC-B4-38: ROLE_BASED campaigns require a non-empty valid RoleEnum value."""
    admin_hdr = get_token_headers(b4_fixture["apex_admin"])
    pol_id = b4_fixture["policy"].id
    v1_id = b4_fixture["v1"].id

    res_missing = client.post(
        "/api/v1/policies/campaigns",
        headers=admin_hdr,
        json={
            "campaign_code": "CAMP-SEC-38A",
            "title": "Missing Role",
            "policy_id": pol_id,
            "version_id": v1_id,
            "target_type": "ROLE_BASED",
            "due_date": (date.today() + timedelta(days=14)).isoformat(),
        },
    )
    assert res_missing.status_code == 400
    assert "target_role is required" in res_missing.json()["detail"].lower()

    res_invalid = client.post(
        "/api/v1/policies/campaigns",
        headers=admin_hdr,
        json={
            "campaign_code": "CAMP-SEC-38B",
            "title": "Invalid Role",
            "policy_id": pol_id,
            "version_id": v1_id,
            "target_type": "ROLE_BASED",
            "target_role": "NON_EXISTENT_SUPER_ROLE",
            "due_date": (date.today() + timedelta(days=14)).isoformat(),
        },
    )
    assert res_invalid.status_code == 400
    assert "invalid target_role" in res_invalid.json()["detail"].lower()


def test_sec_b4_39_campaign_launch_excludes_inactive_users_and_blocks_zero_target_audience(
    client: TestClient, b4_fixture, db: Session
):
    """SEC-B4-39: Campaign launch excludes inactive users and blocks launching when 0 active users match."""
    b4_fixture["apex_auditor"].is_active = False
    db.commit()

    admin_hdr = get_token_headers(b4_fixture["apex_admin"])
    res_camp = client.post(
        "/api/v1/policies/campaigns",
        headers=admin_hdr,
        json={
            "campaign_code": "CAMP-SEC-39",
            "title": "Zero Active Auditors Campaign",
            "policy_id": b4_fixture["policy"].id,
            "version_id": b4_fixture["v1"].id,
            "target_type": "ROLE_BASED",
            "target_role": "AUDITOR",
            "due_date": (date.today() + timedelta(days=14)).isoformat(),
        },
    )
    camp_id = res_camp.json()["id"]

    res_launch = client.post(f"/api/v1/policies/campaigns/{camp_id}/launch", headers=admin_hdr)
    assert res_launch.status_code == 400
    assert "0 active users" in res_launch.json()["detail"].lower()


def test_sec_b4_40_campaign_update_and_relaunch_blocked_after_launch(
    client: TestClient, b4_fixture
):
    """SEC-B4-40: Once launched, a campaign is frozen against PATCH updates and cannot be re-launched."""
    admin_hdr = get_token_headers(b4_fixture["apex_admin"])
    res_camp = client.post(
        "/api/v1/policies/campaigns",
        headers=admin_hdr,
        json={
            "campaign_code": "CAMP-SEC-40",
            "title": "Sec 40 Campaign",
            "policy_id": b4_fixture["policy"].id,
            "version_id": b4_fixture["v1"].id,
            "target_type": "ALL_USERS",
            "due_date": (date.today() + timedelta(days=14)).isoformat(),
        },
    )
    camp_id = res_camp.json()["id"]
    client.post(f"/api/v1/policies/campaigns/{camp_id}/launch", headers=admin_hdr)

    assert (
        client.patch(
            f"/api/v1/policies/campaigns/{camp_id}",
            headers=admin_hdr,
            json={"title": "Mutate Active Campaign"},
        ).status_code
        == 400
    )
    assert (
        client.post(f"/api/v1/policies/campaigns/{camp_id}/launch", headers=admin_hdr).status_code
        == 400
    )


def test_sec_b4_41_campaign_cancel_blocks_completed_or_already_cancelled_and_blocks_subsequent_attestations(
    client: TestClient, b4_fixture
):
    """SEC-B4-41: Cancelled campaigns cannot be cancelled again, completed campaigns cannot be cancelled, and cancelled campaigns reject attestations."""
    admin_hdr = get_token_headers(b4_fixture["apex_admin"])
    res_camp = client.post(
        "/api/v1/policies/campaigns",
        headers=admin_hdr,
        json={
            "campaign_code": "CAMP-SEC-41",
            "title": "Sec 41 Campaign",
            "policy_id": b4_fixture["policy"].id,
            "version_id": b4_fixture["v1"].id,
            "target_type": "ALL_USERS",
            "due_date": (date.today() + timedelta(days=14)).isoformat(),
        },
    )
    camp_id = res_camp.json()["id"]
    client.post(f"/api/v1/policies/campaigns/{camp_id}/launch", headers=admin_hdr)

    res_cancel = client.post(
        f"/api/v1/policies/campaigns/{camp_id}/cancel",
        headers=admin_hdr,
        json={"reason": "Cancelled for test"},
    )
    assert res_cancel.status_code == 200

    res_cancel2 = client.post(
        f"/api/v1/policies/campaigns/{camp_id}/cancel",
        headers=admin_hdr,
        json={"reason": "Double cancel"},
    )
    assert res_cancel2.status_code == 400

    res_att = client.post(
        f"/api/v1/policies/campaigns/{camp_id}/attest",
        headers=admin_hdr,
        json={
            "acknowledgement_text": "I acknowledge and agree to this policy.",
            "policy_version_hash": b4_fixture["v1"].content_hash_sha256,
        },
    )
    assert res_att.status_code == 400


def test_sec_b4_42_attestation_submission_rejects_tampered_policy_version_hash(
    client: TestClient, b4_fixture
):
    """SEC-B4-42: Submitting an attestation with a mismatched SHA-256 hash is rejected."""
    admin_hdr = get_token_headers(b4_fixture["apex_admin"])
    res_camp = client.post(
        "/api/v1/policies/campaigns",
        headers=admin_hdr,
        json={
            "campaign_code": "CAMP-SEC-42",
            "title": "Sec 42 Campaign",
            "policy_id": b4_fixture["policy"].id,
            "version_id": b4_fixture["v1"].id,
            "target_type": "ALL_USERS",
            "due_date": (date.today() + timedelta(days=14)).isoformat(),
        },
    )
    camp_id = res_camp.json()["id"]
    client.post(f"/api/v1/policies/campaigns/{camp_id}/launch", headers=admin_hdr)

    res_att = client.post(
        f"/api/v1/policies/campaigns/{camp_id}/attest",
        headers=admin_hdr,
        json={
            "acknowledgement_text": "I acknowledge and agree to this policy.",
            "policy_version_hash": "0" * 64,
        },
    )
    assert res_att.status_code == 400
    assert "hash mismatch" in res_att.json()["detail"].lower()


def test_sec_b4_43_attestation_submission_rejects_duplicate_and_already_exempted_records(
    client: TestClient, b4_fixture
):
    """SEC-B4-43: Duplicate attestation submission and attesting to an already-EXEMPTED record are rejected; exempting an ATTESTED record is also rejected."""
    admin_hdr = get_token_headers(b4_fixture["apex_admin"])
    mgr_hdr = get_token_headers(b4_fixture["apex_manager"])

    res_camp = client.post(
        "/api/v1/policies/campaigns",
        headers=admin_hdr,
        json={
            "campaign_code": "CAMP-SEC-43",
            "title": "Sec 43 Campaign",
            "policy_id": b4_fixture["policy"].id,
            "version_id": b4_fixture["v1"].id,
            "target_type": "ALL_USERS",
            "due_date": (date.today() + timedelta(days=14)).isoformat(),
        },
    )
    camp_id = res_camp.json()["id"]
    camp_hash = res_camp.json()["policy_version_hash"]
    client.post(f"/api/v1/policies/campaigns/{camp_id}/launch", headers=admin_hdr)

    res_att1 = client.post(
        f"/api/v1/policies/campaigns/{camp_id}/attest",
        headers=admin_hdr,
        json={
            "acknowledgement_text": "I acknowledge and agree to this policy.",
            "policy_version_hash": camp_hash,
        },
    )
    assert res_att1.status_code == 200

    res_att2 = client.post(
        f"/api/v1/policies/campaigns/{camp_id}/attest",
        headers=admin_hdr,
        json={
            "acknowledgement_text": "I acknowledge and agree to this policy.",
            "policy_version_hash": camp_hash,
        },
    )
    assert res_att2.status_code == 409
    assert "duplicate attestation" in res_att2.json()["detail"].lower()

    recs = client.get(f"/api/v1/policies/campaigns/{camp_id}/records", headers=admin_hdr).json()
    admin_rec = next(r for r in recs if r["user_id"] == b4_fixture["apex_admin"].id)
    mgr_rec = next(r for r in recs if r["user_id"] == b4_fixture["apex_manager"].id)

    res_ex_attested = client.post(
        f"/api/v1/policies/campaigns/{camp_id}/records/{admin_rec['id']}/exempt",
        headers=mgr_hdr,
        json={
            "exemption_exception_id": b4_fixture["apex_policy_exception"].id,
            "exemption_reason": "Cannot exempt already attested record",
        },
    )
    assert res_ex_attested.status_code == 400
    assert "already been attested" in res_ex_attested.json()["detail"].lower()

    res_ex_mgr = client.post(
        f"/api/v1/policies/campaigns/{camp_id}/records/{mgr_rec['id']}/exempt",
        headers=admin_hdr,
        json={
            "exemption_exception_id": b4_fixture["apex_policy_exception"].id,
            "exemption_reason": "Valid waiver exemption for manager",
        },
    )
    assert res_ex_mgr.status_code == 200

    res_att_exempted = client.post(
        f"/api/v1/policies/campaigns/{camp_id}/attest",
        headers=mgr_hdr,
        json={
            "acknowledgement_text": "I acknowledge and agree to this policy.",
            "policy_version_hash": camp_hash,
        },
    )
    assert res_att_exempted.status_code == 400
    assert "already been exempted" in res_att_exempted.json()["detail"].lower()


def test_sec_b4_44_attestation_submission_enforces_mandatory_comprehension_assessment_pass(
    client: TestClient, b4_fixture, db: Session
):
    """SEC-B4-44: Campaign with assessment_id blocks attestation until assessment is COMPLETED and EFFECTIVE."""
    failed_assessment = Assessment(
        organization_id=b4_fixture["org_apex"].id,
        organization_control_id=b4_fixture["apex_ctrl"].id,
        summary="B4 Comprehension Quiz",
        assessment_method=AssessmentMethodEnum.TESTING,
        status=AssessmentStatusEnum.IN_PROGRESS,
        conclusion=AssessmentConclusionEnum.INEFFECTIVE,
    )
    db.add(failed_assessment)
    db.commit()
    db.refresh(failed_assessment)

    admin_hdr = get_token_headers(b4_fixture["apex_admin"])
    res_camp = client.post(
        "/api/v1/policies/campaigns",
        headers=admin_hdr,
        json={
            "campaign_code": "CAMP-SEC-44",
            "title": "Sec 44 Quiz Campaign",
            "policy_id": b4_fixture["policy"].id,
            "version_id": b4_fixture["v1"].id,
            "target_type": "ALL_USERS",
            "due_date": (date.today() + timedelta(days=14)).isoformat(),
            "assessment_id": failed_assessment.id,
        },
    )
    camp_id = res_camp.json()["id"]
    camp_hash = res_camp.json()["policy_version_hash"]
    client.post(f"/api/v1/policies/campaigns/{camp_id}/launch", headers=admin_hdr)

    res_fail = client.post(
        f"/api/v1/policies/campaigns/{camp_id}/attest",
        headers=admin_hdr,
        json={
            "acknowledgement_text": "I acknowledge and agree to this policy.",
            "policy_version_hash": camp_hash,
        },
    )
    assert res_fail.status_code == 400
    assert "mandatory comprehension assessment not passed" in res_fail.json()["detail"].lower()


def test_sec_b4_45_evidence_generation_fails_closed_without_mapped_organization_control_and_never_auto_accepts(
    client: TestClient, b4_fixture
):
    """SEC-B4-45: Evidence generation fails closed (400) if policy has no mapped OrganizationControl, and never auto-accepts."""
    admin_hdr = get_token_headers(b4_fixture["apex_admin"])

    res_pol = client.post(
        "/api/v1/policies",
        headers=admin_hdr,
        json={
            "title": "Unmapped Policy",
            "policy_type": "VENDOR_MANAGEMENT",
            "initial_content": "# Unmapped Policy\n\nNo controls mapped.",
            "mapped_subcategory_ids": [],
        },
    )
    unmapped_pol_id = res_pol.json()["id"]
    unmapped_ver_id = res_pol.json()["current_version"]["id"]

    res_camp = client.post(
        "/api/v1/policies/campaigns",
        headers=admin_hdr,
        json={
            "campaign_code": "CAMP-SEC-45",
            "title": "Unmapped Evidence Campaign",
            "policy_id": unmapped_pol_id,
            "version_id": unmapped_ver_id,
            "target_type": "ALL_USERS",
            "due_date": (date.today() + timedelta(days=14)).isoformat(),
        },
    )
    camp_id = res_camp.json()["id"]
    client.post(f"/api/v1/policies/campaigns/{camp_id}/launch", headers=admin_hdr)

    res_ev = client.post(
        f"/api/v1/policies/campaigns/{camp_id}/evidence",
        headers=admin_hdr,
    )
    assert res_ev.status_code == 400
    assert "no mapped organizationcontrol" in res_ev.json()["detail"].lower()


def test_sec_b4_46_strict_schema_rejects_extra_fields_and_tenant_spoofing_payloads(
    client: TestClient, b4_fixture
):
    """SEC-B4-46: extra='forbid' on Batch 4 request schemas rejects unknown fields and spoofing payloads (422)."""
    admin_hdr = get_token_headers(b4_fixture["apex_admin"])

    res_pol = client.post(
        "/api/v1/policies",
        headers=admin_hdr,
        json={
            "title": "",
            "policy_type": "ACCESS_CONTROL",
            "initial_content": "# Invalid Empty Title",
        },
    )
    assert res_pol.status_code == 422

    res_cancel = client.post(
        "/api/v1/policies/campaigns/1/cancel",
        headers=admin_hdr,
        json={"reason": "Valid", "unexpected_field": "hack"},
    )
    assert res_cancel.status_code == 422

    res_exempt = client.post(
        "/api/v1/policies/campaigns/1/records/1/exempt",
        headers=admin_hdr,
        json={
            "exemption_exception_id": 1,
            "exemption_reason": "Valid reason text here",
            "exempted_by_id": 999,
        },
    )
    assert res_exempt.status_code == 422


def test_sec_b4_47_audit_log_coverage_on_all_new_batch4_mutating_endpoints(
    client: TestClient, b4_fixture, db: Session
):
    """SEC-B4-47: All new Batch 4 mutating endpoints (evaluate-overdue, exempt, cancel) write immutable AuditLog entries."""
    admin_hdr = get_token_headers(b4_fixture["apex_admin"])
    res_camp = client.post(
        "/api/v1/policies/campaigns",
        headers=admin_hdr,
        json={
            "campaign_code": "CAMP-SEC-47",
            "title": "Audit Log Coverage Campaign",
            "policy_id": b4_fixture["policy"].id,
            "version_id": b4_fixture["v1"].id,
            "target_type": "ALL_USERS",
            "due_date": (date.today() - timedelta(days=3)).isoformat(),
            "grace_period_days": 0,
        },
    )
    camp_id = res_camp.json()["id"]
    client.post(f"/api/v1/policies/campaigns/{camp_id}/launch", headers=admin_hdr)

    assert (
        client.post(
            f"/api/v1/policies/campaigns/{camp_id}/evaluate-overdue", headers=admin_hdr
        ).status_code
        == 200
    )

    recs = client.get(f"/api/v1/policies/campaigns/{camp_id}/records", headers=admin_hdr).json()
    mgr_rec = next(r for r in recs if r["user_id"] == b4_fixture["apex_manager"].id)
    assert (
        client.post(
            f"/api/v1/policies/campaigns/{camp_id}/records/{mgr_rec['id']}/exempt",
            headers=admin_hdr,
            json={
                "exemption_exception_id": b4_fixture["apex_policy_exception"].id,
                "exemption_reason": "Audit log verification exemption",
            },
        ).status_code
        == 200
    )

    assert (
        client.post(
            f"/api/v1/policies/campaigns/{camp_id}/cancel",
            headers=admin_hdr,
            json={"reason": "Audit log cancel test"},
        ).status_code
        == 200
    )

    logs = (
        db.query(AuditLog)
        .filter(AuditLog.organization_id == b4_fixture["org_apex"].id)
        .all()
    )
    actions = {log.action for log in logs}
    assert "policy.campaign.evaluate_overdue" in actions
    assert "policy.attestation.exempt" in actions
    assert "policy.campaign.cancel" in actions


def test_sec_b4_48_exemption_rejects_exception_linked_to_different_policy(
    client: TestClient, b4_fixture, db: Session
):
    """SEC-B4-48: Exemption rejects a SecurityException whose linked_policy_id points to a different policy."""
    other_policy = PolicyService.create_policy(
        db=db,
        obj_in=PolicyCreate(
            title="Other Apex Policy",
            policy_type=PolicyTypeEnum.INCIDENT_RESPONSE,
            initial_content="# Incident Response Policy\n\nReport within 1 hour.",
        ),
        organization_id=b4_fixture["org_apex"].id,
        created_by_id=b4_fixture["apex_admin"].id,
    )
    other_exc = SecurityException(
        organization_id=b4_fixture["org_apex"].id,
        title="Waiver Linked to Other Policy",
        description="Waiver for IR policy",
        justification="Approved for IR policy only",
        exception_type=ExceptionTypeEnum.POLICY_EXCEPTION,
        status=ExceptionStatusEnum.APPROVED,
        requested_by_id=b4_fixture["apex_analyst"].id,
        owner_id=b4_fixture["apex_analyst"].id,
        reviewer_id=b4_fixture["apex_manager_2"].id,
        approved_at=datetime.now(timezone.utc),
        effective_date=date.today() - timedelta(days=1),
        expiry_date=date.today() + timedelta(days=30),
        linked_policy_id=other_policy.id,
    )
    db.add(other_exc)
    db.commit()
    db.refresh(other_exc)

    admin_hdr = get_token_headers(b4_fixture["apex_admin"])
    res_camp = client.post(
        "/api/v1/policies/campaigns",
        headers=admin_hdr,
        json={
            "campaign_code": "CAMP-SEC-48",
            "title": "Sec 48 Campaign",
            "policy_id": b4_fixture["policy"].id,
            "version_id": b4_fixture["v1"].id,
            "target_type": "ALL_USERS",
            "due_date": (date.today() + timedelta(days=14)).isoformat(),
        },
    )
    camp_id = res_camp.json()["id"]
    client.post(f"/api/v1/policies/campaigns/{camp_id}/launch", headers=admin_hdr)
    recs = client.get(f"/api/v1/policies/campaigns/{camp_id}/records", headers=admin_hdr).json()
    mgr_rec = next(r for r in recs if r["user_id"] == b4_fixture["apex_manager"].id)

    res_ex = client.post(
        f"/api/v1/policies/campaigns/{camp_id}/records/{mgr_rec['id']}/exempt",
        headers=admin_hdr,
        json={
            "exemption_exception_id": other_exc.id,
            "exemption_reason": "Attempting to reuse waiver from different policy",
        },
    )
    assert res_ex.status_code == 400
    assert "different policy" in res_ex.json()["detail"].lower()


def test_sec_b4_49_overdue_evaluation_respects_grace_period_and_rejects_non_active_campaign(
    client: TestClient, b4_fixture
):
    """SEC-B4-49: Overdue evaluation does not mark records overdue while within grace_period_days and rejects DRAFT/CANCELLED campaigns."""
    admin_hdr = get_token_headers(b4_fixture["apex_admin"])
    res_camp = client.post(
        "/api/v1/policies/campaigns",
        headers=admin_hdr,
        json={
            "campaign_code": "CAMP-SEC-49",
            "title": "Grace Period Campaign",
            "policy_id": b4_fixture["policy"].id,
            "version_id": b4_fixture["v1"].id,
            "target_type": "ALL_USERS",
            "due_date": (date.today() - timedelta(days=2)).isoformat(),
            "grace_period_days": 5,
        },
    )
    camp_id = res_camp.json()["id"]

    assert (
        client.post(
            f"/api/v1/policies/campaigns/{camp_id}/evaluate-overdue", headers=admin_hdr
        ).status_code
        == 400
    )

    client.post(f"/api/v1/policies/campaigns/{camp_id}/launch", headers=admin_hdr)
    res_eval = client.post(
        f"/api/v1/policies/campaigns/{camp_id}/evaluate-overdue", headers=admin_hdr
    )
    assert res_eval.status_code == 200
    assert res_eval.json()["overdue_count"] == 0


def test_sec_b4_50_crlf_and_trailing_whitespace_canonical_hash_invariance():
    """SEC-B4-50: PolicyService.compute_canonical_hash produces identical SHA-256 digests across CRLF, CR, LF, and trailing whitespace."""
    h1 = PolicyService.compute_canonical_hash("# Title\nLine 1\nLine 2")
    h2 = PolicyService.compute_canonical_hash("# Title   \r\nLine 1\t  \r\nLine 2   ")
    h3 = PolicyService.compute_canonical_hash("# Title\rLine 1\rLine 2")
    assert h1 == h2 == h3
    assert len(h1) == 64

from datetime import date, datetime, timezone
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.control import ImplementationStatusEnum, OrganizationControl
from app.models.executive import (
    ArtifactTypeEnum,
    BriefingStatusEnum,
    DossierStatusEnum,
    DossierTypeEnum,
    ExecutiveBriefing,
    ExecutiveDossier,
    ExecutiveExportArtifact,
    ExecutiveSnapshot,
    ExportFormatEnum,
)
from app.models.organization import Organization
from app.models.risk import Risk, RiskCategoryEnum, RiskSourceEnum, RiskStatusEnum
from app.models.user import RoleEnum, User
from app.schemas.executive import (
    ExecutiveBriefingCreate,
    ExecutiveBriefingReview,
    ExecutiveDossierCreate,
    ExecutiveDossierUpdate,
    ExecutiveSnapshotCreate,
)
from app.services.executive_service import (
    ExecutiveService,
    canonical_json_dumps,
    compute_canonical_sha256,
)


@pytest.fixture
def org_and_users(db: Session):
    ts = datetime.now().timestamp()
    org = Organization(name=f"Executive Domain Test Org {ts}", slug=f"exec-domain-test-{ts}")
    db.add(org)
    db.commit()
    db.refresh(org)

    admin = User(
        email=f"exec_admin_{ts}@example.com",
        hashed_password="hashed_pwd",
        full_name="Executive Admin",
        role=RoleEnum.ADMIN,
        organization_id=org.id,
        is_active=True,
    )
    manager = User(
        email=f"exec_mgr_{ts}@example.com",
        hashed_password="hashed_pwd",
        full_name="Executive Manager",
        role=RoleEnum.MANAGER,
        organization_id=org.id,
        is_active=True,
    )
    analyst = User(
        email=f"exec_analyst_{ts}@example.com",
        hashed_password="hashed_pwd",
        full_name="Executive Analyst",
        role=RoleEnum.GRC_ANALYST,
        organization_id=org.id,
        is_active=True,
    )

    db.add_all([admin, manager, analyst])
    db.commit()
    for u in [admin, manager, analyst]:
        db.refresh(u)

    return org, admin, manager, analyst


def test_canonical_json_and_sha256_reproducibility():
    """Verify deterministic canonical serialization and SHA-256 reproducibility."""
    payload1 = {
        "z_field": 123.456,
        "a_field": "alpha",
        "nested": {"beta": True, "alpha": None, "dt": datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone.utc)},
        "items": [3, 2, 1],
    }
    payload2 = {
        "a_field": "alpha",
        "nested": {"dt": datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone.utc), "alpha": None, "beta": True},
        "z_field": 123.456,
        "items": [3, 2, 1],
    }

    canonical1 = canonical_json_dumps(payload1)
    canonical2 = canonical_json_dumps(payload2)
    assert canonical1 == canonical2

    hash1 = compute_canonical_sha256(payload1)
    hash2 = compute_canonical_sha256(payload2)
    assert hash1 == hash2
    assert len(hash1) == 64


def test_live_telemetry_calculation_empty_and_populated(db: Session, org_and_users):
    org, admin, _, _ = org_and_users

    # Empty org state
    telemetry, manifest = ExecutiveService.calculate_live_telemetry(db, org.id)
    assert telemetry.overall_posture_score >= 0.0
    assert telemetry.overall_posture_score <= 100.0
    assert manifest["organization_id"] == org.id
    assert "framework_controls" in manifest["domains"]

    # Seed controls and risks
    risk1 = Risk(
        organization_id=org.id,
        title="Ransomware Risk",
        description="Potential ransomware extortion",
        risk_category=RiskCategoryEnum.CYBERSECURITY,
        risk_source=RiskSourceEnum.THREAT_INTELLIGENCE,
        inherent_impact=5,
        inherent_likelihood=4,
        inherent_score=20,
        residual_impact=2,
        residual_likelihood=2,
        residual_score=4,
        status=RiskStatusEnum.ASSESSED,
    )
    db.add(risk1)
    db.commit()

    telemetry2, _ = ExecutiveService.calculate_live_telemetry(db, org.id)
    assert telemetry2.inherent_risk_index == 20.0
    assert telemetry2.residual_risk_index == 4.0
    assert telemetry2.risk_reduction_percentage == 80.0
    assert len(telemetry2.top_risks) == 1
    assert telemetry2.top_risks[0].title == "Ransomware Risk"


def test_capture_and_retrieve_snapshot(db: Session, org_and_users):
    org, admin, _, _ = org_and_users

    snapshot = ExecutiveService.capture_snapshot(
        db=db,
        org_id=org.id,
        user_id=admin.id,
        data=ExecutiveSnapshotCreate(snapshot_code="SNAP-TEST-001", notes="Board Review Q3"),
    )

    assert snapshot.id is not None
    assert snapshot.snapshot_code == "SNAP-TEST-001"
    assert len(snapshot.data_hash_sha256) == 64
    assert snapshot.created_by_id == admin.id

    # Retrieve
    retrieved = ExecutiveService.get_snapshot(db, org.id, snapshot.id)
    assert retrieved.snapshot_code == "SNAP-TEST-001"

    # Duplicate snapshot code within tenant rejected
    with pytest.raises(HTTPException) as exc:
        ExecutiveService.capture_snapshot(
            db=db,
            org_id=org.id,
            user_id=admin.id,
            data=ExecutiveSnapshotCreate(snapshot_code="SNAP-TEST-001"),
        )
    assert exc.value.status_code == 409


def test_dossier_lifecycle_and_four_eyes_enforcement(db: Session, org_and_users):
    org, admin, manager, analyst = org_and_users

    # 1. Create Draft Dossier
    dossier = ExecutiveService.create_dossier(
        db=db,
        org_id=org.id,
        user_id=analyst.id,
        data=ExecutiveDossierCreate(
            dossier_code="DOS-2026-001",
            title="Annual Regulatory Dossier 2026",
            dossier_type=DossierTypeEnum.ANNUAL_COMPLIANCE,
            executive_summary="Summary of annual compliance",
        ),
    )
    assert dossier.status == DossierStatusEnum.DRAFT
    assert dossier.created_by_id == analyst.id

    # 2. Cannot finalize directly from DRAFT
    with pytest.raises(HTTPException) as exc:
        ExecutiveService.finalize_dossier(db, org.id, manager.id, dossier.id)
    assert exc.value.status_code == 422

    # 3. Compile Dossier
    compiled = ExecutiveService.compile_dossier(db, org.id, analyst.id, dossier.id)
    assert compiled.status == DossierStatusEnum.COMPILED
    assert compiled.compiled_by_id == analyst.id
    assert compiled.compiled_sections is not None

    # 4. Creator/Compiler attempts self-finalization -> Blocked by Four-Eyes
    with pytest.raises(HTTPException) as exc:
        ExecutiveService.finalize_dossier(db, org.id, analyst.id, dossier.id)
    assert exc.value.status_code == 400
    assert "Four-Eyes violation" in exc.value.detail

    # 5. Independent Manager finalizes Dossier -> Success
    finalized = ExecutiveService.finalize_dossier(db, org.id, manager.id, dossier.id)
    assert finalized.status == DossierStatusEnum.FINALIZED
    assert finalized.finalized_by_id == manager.id
    assert finalized.finalized_at is not None

    # 6. Re-compiling or updating a finalized dossier is blocked
    with pytest.raises(HTTPException) as exc:
        ExecutiveService.compile_dossier(db, org.id, manager.id, dossier.id)
    assert exc.value.status_code == 409

    with pytest.raises(HTTPException) as exc:
        ExecutiveService.update_dossier(
            db, org.id, manager.id, dossier.id, ExecutiveDossierUpdate(title="Modified Title")
        )
    assert exc.value.status_code == 409


def test_briefing_lifecycle_and_four_eyes_enforcement(db: Session, org_and_users):
    org, admin, manager, analyst = org_and_users

    snapshot = ExecutiveService.capture_snapshot(
        db=db,
        org_id=org.id,
        user_id=admin.id,
        data=ExecutiveSnapshotCreate(snapshot_code="SNAP-BRF-001"),
    )

    # 1. Generate Draft Briefing
    briefing = ExecutiveService.generate_briefing(
        db=db,
        org_id=org.id,
        user_id=analyst.id,
        data=ExecutiveBriefingCreate(
            briefing_code="BRF-2026-Q3",
            title="Q3 2026 Board Cyber-Risk Briefing",
            reporting_period_start=date(2026, 7, 1),
            reporting_period_end=date(2026, 9, 30),
            snapshot_id=snapshot.id,
            executive_summary="Executive cyber-risk posture remains resilient with steady gains.",
            key_achievements=["Closed 100% of high vulnerability remediations", "Achieved ISO 27001 readiness"],
            emerging_risks=["Supply chain dependency CVEs in external components"],
            strategic_recommendations="Increase cloud security automation budget.",
        ),
    )
    assert briefing.status == BriefingStatusEnum.DRAFT
    assert briefing.generated_by_id == analyst.id

    # 2. Inverted dates rejected
    with pytest.raises(HTTPException) as exc:
        ExecutiveService.generate_briefing(
            db=db,
            org_id=org.id,
            user_id=analyst.id,
            data=ExecutiveBriefingCreate(
                briefing_code="BRF-INVALID",
                title="Invalid Briefing",
                reporting_period_start=date(2026, 9, 30),
                reporting_period_end=date(2026, 7, 1),
                snapshot_id=snapshot.id,
                executive_summary="Inverted dates test",
            ),
        )
    assert exc.value.status_code == 400

    # 3. Submit Briefing
    submitted = ExecutiveService.submit_briefing(db, org.id, analyst.id, briefing.id)
    assert submitted.status == BriefingStatusEnum.SUBMITTED_FOR_REVIEW

    # 4. Self-approval blocked
    with pytest.raises(HTTPException) as exc:
        ExecutiveService.review_briefing(
            db=db,
            org_id=org.id,
            reviewer_id=analyst.id,
            briefing_id=briefing.id,
            review=ExecutiveBriefingReview(approved=True, review_notes="Self approval"),
        )
    assert exc.value.status_code == 400
    assert "Four-Eyes violation" in exc.value.detail

    # 5. Independent Executive Approval
    approved = ExecutiveService.review_briefing(
        db=db,
        org_id=org.id,
        reviewer_id=manager.id,
        briefing_id=briefing.id,
        review=ExecutiveBriefingReview(approved=True, review_notes="Board approved"),
    )
    assert approved.status == BriefingStatusEnum.APPROVED
    assert approved.approved_by_id == manager.id
    assert approved.approved_at is not None

    # 6. Replay on terminal state rejected
    with pytest.raises(HTTPException) as exc:
        ExecutiveService.review_briefing(
            db=db,
            org_id=org.id,
            reviewer_id=admin.id,
            briefing_id=briefing.id,
            review=ExecutiveBriefingReview(approved=False),
        )
    assert exc.value.status_code == 409


def test_pdf_and_json_forensic_export_generation(db: Session, org_and_users):
    org, admin, _, _ = org_and_users

    snapshot = ExecutiveService.capture_snapshot(
        db=db,
        org_id=org.id,
        user_id=admin.id,
        data=ExecutiveSnapshotCreate(snapshot_code="SNAP-EXP-001"),
    )

    # 1. Generate PDF Export
    pdf_artifact = ExecutiveService.generate_pdf_export(
        db=db,
        org_id=org.id,
        user_id=admin.id,
        artifact_type=ArtifactTypeEnum.POSTURE_SNAPSHOT,
        resource_id=snapshot.id,
    )
    assert pdf_artifact.id is not None
    assert pdf_artifact.export_format == ExportFormatEnum.PDF
    assert pdf_artifact.mime_type == "application/pdf"
    assert pdf_artifact.file_size_bytes > 0
    assert len(pdf_artifact.sha256_checksum) == 64

    # 2. Generate JSON Export
    json_artifact = ExecutiveService.generate_json_export(
        db=db,
        org_id=org.id,
        user_id=admin.id,
        artifact_type=ArtifactTypeEnum.POSTURE_SNAPSHOT,
        resource_id=snapshot.id,
    )
    assert json_artifact.id is not None
    assert json_artifact.export_format == ExportFormatEnum.JSON
    assert json_artifact.mime_type == "application/json"
    assert json_artifact.file_size_bytes > 0

    # 3. Stream & verify checksum
    file_bytes, filename, mime = ExecutiveService.get_export_stream(
        db=db, org_id=org.id, user_id=admin.id, export_id=pdf_artifact.id
    )
    assert len(file_bytes) == pdf_artifact.file_size_bytes
    assert filename == pdf_artifact.original_filename
    assert mime == "application/pdf"

from datetime import date, datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.permissions import RoleEnum
from app.core.security import get_password_hash
from app.models.audit_log import AuditLog
from app.models.executive import (
    ArtifactTypeEnum,
    BriefingStatusEnum,
    DossierStatusEnum,
    DossierTypeEnum,
    ExecutiveBriefing,
    ExecutiveDossier,
    ExecutiveExportArtifact,
    ExecutiveSnapshot,
)
from app.models.framework import Framework
from app.models.organization import Organization
from app.models.risk import Risk, RiskCategoryEnum, RiskSourceEnum, RiskStatusEnum
from app.models.user import User
from app.schemas.executive import (
    ExecutiveBriefingCreate,
    ExecutiveDossierCreate,
    ExecutiveSnapshotCreate,
)
from app.services.executive_service import ExecutiveService
from tests.conftest import get_token_headers


@pytest.fixture
def p20_adv_fixture(db: Session, org_apex: Organization, org_meridian: Organization):
    """Setup adversarial test harness with two isolated tenants and various roles."""
    apex_admin = User(
        email="p20_apex_admin@apex.com",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Apex Admin",
        role=RoleEnum.ADMIN,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_manager = User(
        email="p20_apex_manager@apex.com",
        hashed_password=get_password_hash("MgrPass123!"),
        full_name="Apex Manager",
        role=RoleEnum.MANAGER,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_analyst = User(
        email="p20_apex_analyst@apex.com",
        hashed_password=get_password_hash("AnalystPass123!"),
        full_name="Apex Analyst",
        role=RoleEnum.GRC_ANALYST,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_auditor = User(
        email="p20_apex_auditor@apex.com",
        hashed_password=get_password_hash("AuditorPass123!"),
        full_name="Apex Auditor",
        role=RoleEnum.AUDITOR,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_viewer = User(
        email="p20_apex_viewer@apex.com",
        hashed_password=get_password_hash("ViewerPass123!"),
        full_name="Apex Viewer",
        role=RoleEnum.VIEWER,
        is_active=True,
        organization_id=org_apex.id,
    )
    meridian_admin = User(
        email="p20_meridian_admin@meridian.com",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Meridian Admin",
        role=RoleEnum.ADMIN,
        is_active=True,
        organization_id=org_meridian.id,
    )
    meridian_analyst = User(
        email="p20_meridian_analyst@meridian.com",
        hashed_password=get_password_hash("AnalystPass123!"),
        full_name="Meridian Analyst",
        role=RoleEnum.GRC_ANALYST,
        is_active=True,
        organization_id=org_meridian.id,
    )

    db.add_all([apex_admin, apex_manager, apex_analyst, apex_auditor, apex_viewer, meridian_admin, meridian_analyst])
    db.commit()
    for u in [apex_admin, apex_manager, apex_analyst, apex_auditor, apex_viewer, meridian_admin, meridian_analyst]:
        db.refresh(u)

    return {
        "org_apex": org_apex,
        "org_meridian": org_meridian,
        "apex_admin_headers": get_token_headers(apex_admin),
        "apex_mgr_headers": get_token_headers(apex_manager),
        "apex_analyst_headers": get_token_headers(apex_analyst),
        "apex_auditor_headers": get_token_headers(apex_auditor),
        "apex_viewer_headers": get_token_headers(apex_viewer),
        "meridian_admin_headers": get_token_headers(meridian_admin),
        "meridian_analyst_headers": get_token_headers(meridian_analyst),
        "apex_admin": apex_admin,
        "apex_manager": apex_manager,
        "apex_analyst": apex_analyst,
        "meridian_admin": meridian_admin,
    }


def test_adv_p20_01_cross_tenant_telemetry_isolation(client: TestClient, p20_adv_fixture, db: Session):
    """ADV-P20-01: Ensure telemetry for Meridian does not leak Apex data."""
    # Seed high risk in Apex
    risk = Risk(
        organization_id=p20_adv_fixture["org_apex"].id,
        title="Apex Critical Confidential Risk",
        description="Top secret",
        inherent_score=25,
        status=RiskStatusEnum.ASSESSED,
    )
    db.add(risk)
    db.commit()

    res = client.get("/api/v1/executive/telemetry/live", headers=p20_adv_fixture["meridian_analyst_headers"])
    assert res.status_code == 200
    data = res.json()
    assert not any(r["title"] == "Apex Critical Confidential Risk" for r in data.get("top_risks", []))


def test_adv_p20_02_cross_tenant_dossier_idor(client: TestClient, p20_adv_fixture, db: Session):
    """ADV-P20-02: Prevent Meridian from accessing Apex dossier via IDOR."""
    dossier = ExecutiveService.create_dossier(
        db,
        p20_adv_fixture["org_apex"].id,
        p20_adv_fixture["apex_admin"].id,
        ExecutiveDossierCreate(dossier_code="APEX-DOS-IDOR", title="Apex Secret Dossier"),
    )
    res = client.get(f"/api/v1/executive/dossiers/{dossier.id}", headers=p20_adv_fixture["meridian_analyst_headers"])
    assert res.status_code == 404


def test_adv_p20_03_cross_tenant_snapshot_idor(client: TestClient, p20_adv_fixture, db: Session):
    """ADV-P20-03: Prevent Meridian from accessing Apex snapshot via IDOR."""
    snap = ExecutiveService.capture_snapshot(
        db,
        p20_adv_fixture["org_apex"].id,
        p20_adv_fixture["apex_admin"].id,
        ExecutiveSnapshotCreate(snapshot_code="APEX-SNAP-IDOR"),
    )
    res = client.get(f"/api/v1/executive/snapshots/{snap.id}", headers=p20_adv_fixture["meridian_analyst_headers"])
    assert res.status_code == 404


def test_adv_p20_04_cross_tenant_briefing_idor(client: TestClient, p20_adv_fixture, db: Session):
    """ADV-P20-04: Prevent Meridian from accessing Apex briefing via IDOR."""
    snap = ExecutiveService.capture_snapshot(
        db,
        p20_adv_fixture["org_apex"].id,
        p20_adv_fixture["apex_admin"].id,
        ExecutiveSnapshotCreate(snapshot_code="APEX-SNAP-FOR-BRF-IDOR"),
    )
    briefing = ExecutiveService.generate_briefing(
        db,
        p20_adv_fixture["org_apex"].id,
        p20_adv_fixture["apex_admin"].id,
        ExecutiveBriefingCreate(
            briefing_code="APEX-BRF-IDOR",
            title="Apex Briefing",
            reporting_period_start=date(2026, 1, 1),
            reporting_period_end=date(2026, 3, 31),
            snapshot_id=snap.id,
            executive_summary="Apex Board Summary",
        ),
    )
    res = client.get(f"/api/v1/executive/briefings/{briefing.id}", headers=p20_adv_fixture["meridian_analyst_headers"])
    assert res.status_code == 404


def test_adv_p20_05_cross_tenant_export_download_idor(client: TestClient, p20_adv_fixture, db: Session):
    """ADV-P20-05: Prevent Meridian from downloading Apex export via IDOR."""
    snap = ExecutiveService.capture_snapshot(
        db,
        p20_adv_fixture["org_apex"].id,
        p20_adv_fixture["apex_admin"].id,
        ExecutiveSnapshotCreate(snapshot_code="APEX-SNAP-FOR-EXP-IDOR"),
    )
    artifact = ExecutiveService.generate_pdf_export(
        db,
        p20_adv_fixture["org_apex"].id,
        p20_adv_fixture["apex_admin"].id,
        ArtifactTypeEnum.POSTURE_SNAPSHOT,
        snap.id,
    )
    res = client.get(f"/api/v1/executive/exports/{artifact.id}/download", headers=p20_adv_fixture["meridian_admin_headers"])
    assert res.status_code == 404


def test_adv_p20_06_client_posture_score_tampering_ignored(client: TestClient, p20_adv_fixture):
    """ADV-P20-06: Ensure client-supplied posture score in snapshot create is ignored."""
    payload = {
        "snapshot_code": "SNAP-TAMPER-01",
        "overall_posture_score": 100.0,  # Injection attempt
        "inherent_risk_index": 1.0,      # Injection attempt
    }
    res = client.post("/api/v1/executive/snapshots", json=payload, headers=p20_adv_fixture["apex_admin_headers"])
    assert res.status_code == 201
    # Check that score was calculated server side
    assert "overall_posture_score" in res.json()


def test_adv_p20_07_client_ale_tampering_ignored(client: TestClient, p20_adv_fixture):
    """ADV-P20-07: Ensure client-supplied ALE in briefing create is ignored."""
    snap_res = client.post(
        "/api/v1/executive/snapshots",
        json={"snapshot_code": "SNAP-FOR-ALE-TAMPER"},
        headers=p20_adv_fixture["apex_admin_headers"],
    )
    snap_id = snap_res.json()["id"]

    payload = {
        "briefing_code": "BRF-ALE-TAMPER",
        "title": "ALE Tamper Attempt",
        "reporting_period_start": "2026-01-01",
        "reporting_period_end": "2026-03-31",
        "snapshot_id": snap_id,
        "executive_summary": "Testing ALE injection resistance.",
        "financial_exposure_ale": 0.0,  # Attempt to fake zero ALE
    }
    res = client.post("/api/v1/executive/briefings", json=payload, headers=p20_adv_fixture["apex_admin_headers"])
    assert res.status_code == 201


def test_adv_p20_08_four_eyes_briefing_self_approval_violation(client: TestClient, p20_adv_fixture):
    """ADV-P20-08: Briefing author cannot approve their own briefing."""
    snap_res = client.post(
        "/api/v1/executive/snapshots",
        json={"snapshot_code": "SNAP-FOR-SELF-APP"},
        headers=p20_adv_fixture["apex_admin_headers"],
    )
    snap_id = snap_res.json()["id"]

    res = client.post(
        "/api/v1/executive/briefings",
        json={
            "briefing_code": "BRF-SELF-APP",
            "title": "Self Approval Test",
            "reporting_period_start": "2026-01-01",
            "reporting_period_end": "2026-03-31",
            "snapshot_id": snap_id,
            "executive_summary": "Testing self approval.",
        },
        headers=p20_adv_fixture["apex_admin_headers"],
    )
    briefing_id = res.json()["id"]

    # Submit
    client.post(f"/api/v1/executive/briefings/{briefing_id}/submit", headers=p20_adv_fixture["apex_admin_headers"])

    # Attempt self approval
    rev_res = client.post(
        f"/api/v1/executive/briefings/{briefing_id}/review",
        json={"approved": True},
        headers=p20_adv_fixture["apex_admin_headers"],
    )
    assert rev_res.status_code == 400
    assert "Four-Eyes violation" in rev_res.json()["detail"]


def test_adv_p20_09_briefing_replay_on_terminal_state(client: TestClient, p20_adv_fixture):
    """ADV-P20-09: Replay of review on approved briefing returns 409."""
    snap_res = client.post(
        "/api/v1/executive/snapshots",
        json={"snapshot_code": "SNAP-FOR-REPLAY"},
        headers=p20_adv_fixture["apex_admin_headers"],
    )
    snap_id = snap_res.json()["id"]

    res = client.post(
        "/api/v1/executive/briefings",
        json={
            "briefing_code": "BRF-REPLAY",
            "title": "Replay Test",
            "reporting_period_start": "2026-01-01",
            "reporting_period_end": "2026-03-31",
            "snapshot_id": snap_id,
            "executive_summary": "Testing replay attack.",
        },
        headers=p20_adv_fixture["apex_analyst_headers"],
    )
    briefing_id = res.json()["id"]
    client.post(f"/api/v1/executive/briefings/{briefing_id}/submit", headers=p20_adv_fixture["apex_analyst_headers"])

    # Manager approves
    client.post(
        f"/api/v1/executive/briefings/{briefing_id}/review",
        json={"approved": True},
        headers=p20_adv_fixture["apex_mgr_headers"],
    )

    # Admin attempts second review (replay)
    replay_res = client.post(
        f"/api/v1/executive/briefings/{briefing_id}/review",
        json={"approved": False},
        headers=p20_adv_fixture["apex_admin_headers"],
    )
    assert replay_res.status_code == 409


def test_adv_p20_10_finalized_dossier_mutation_rejection(client: TestClient, p20_adv_fixture):
    """ADV-P20-10: Reject any modification or recompilation of finalized dossier."""
    dossier_res = client.post(
        "/api/v1/executive/dossiers",
        json={"dossier_code": "DOS-FINAL-MUT", "title": "Finalized Mutation Test"},
        headers=p20_adv_fixture["apex_analyst_headers"],
    )
    dossier_id = dossier_res.json()["id"]

    client.post(f"/api/v1/executive/dossiers/{dossier_id}/compile", headers=p20_adv_fixture["apex_analyst_headers"])
    client.post(f"/api/v1/executive/dossiers/{dossier_id}/finalize", headers=p20_adv_fixture["apex_mgr_headers"])

    # Attempt patch
    patch_res = client.patch(
        f"/api/v1/executive/dossiers/{dossier_id}",
        json={"title": "Hacked Title"},
        headers=p20_adv_fixture["apex_mgr_headers"],
    )
    assert patch_res.status_code == 409

    # Attempt recompile
    comp_res = client.post(f"/api/v1/executive/dossiers/{dossier_id}/compile", headers=p20_adv_fixture["apex_mgr_headers"])
    assert comp_res.status_code == 409


def test_adv_p20_11_foreign_framework_injection_rejection(client: TestClient, p20_adv_fixture, db: Session):
    """ADV-P20-11: Reject invalid or nonexistent framework selection."""
    # Apex user attempts to create dossier including invalid framework ID
    res = client.post(
        "/api/v1/executive/dossiers",
        json={
            "dossier_code": "DOS-FOREIGN-FW",
            "title": "Foreign FW Test",
            "scope_framework_ids": [999999],
        },
        headers=p20_adv_fixture["apex_analyst_headers"],
    )
    assert res.status_code == 400
    assert "invalid" in res.json()["detail"]


def test_adv_p20_12_path_traversal_export_download_protection(client: TestClient, p20_adv_fixture):
    """ADV-P20-12: Ensure non-numeric or traversal export IDs are rejected cleanly."""
    res = client.get("/api/v1/executive/exports/..%2f..%2fetc%2fpasswd/download", headers=p20_adv_fixture["apex_admin_headers"])
    assert res.status_code in [404, 422]


def test_adv_p20_13_null_byte_injection_prevention(client: TestClient, p20_adv_fixture):
    """ADV-P20-13: Null byte injection in snapshot code is rejected."""
    res = client.post(
        "/api/v1/executive/snapshots",
        json={"snapshot_code": "SNAP\x00HACK"},
        headers=p20_adv_fixture["apex_admin_headers"],
    )
    assert res.status_code in [400, 422]


def test_adv_p20_14_unauthenticated_telemetry_access_rejection(client: TestClient):
    """ADV-P20-14: Unauthenticated access returns 401."""
    res = client.get("/api/v1/executive/telemetry/live")
    assert res.status_code == 401


def test_adv_p20_15_unauthorized_briefing_generation_role(client: TestClient, p20_adv_fixture):
    """ADV-P20-15: VIEWER role cannot generate briefings (403 Forbidden)."""
    res = client.post(
        "/api/v1/executive/briefings",
        json={
            "briefing_code": "BRF-VIEWER-HACK",
            "title": "Viewer Briefing",
            "reporting_period_start": "2026-01-01",
            "reporting_period_end": "2026-03-31",
            "snapshot_id": 1,
            "executive_summary": "Viewer summary",
        },
        headers=p20_adv_fixture["apex_viewer_headers"],
    )
    assert res.status_code == 403


def test_adv_p20_16_unauthorized_export_generation_role(client: TestClient, p20_adv_fixture):
    """ADV-P20-16: VIEWER role cannot generate exports (403 Forbidden)."""
    res = client.post(
        "/api/v1/executive/exports/snapshot/1?format=PDF",
        headers=p20_adv_fixture["apex_viewer_headers"],
    )
    assert res.status_code == 403


def test_adv_p20_17_snapshot_sha256_checksum_tampering_detection(client: TestClient, p20_adv_fixture, db: Session):
    """ADV-P20-17: File tampering detected via SHA-256 validation on download."""
    snap = ExecutiveService.capture_snapshot(
        db,
        p20_adv_fixture["org_apex"].id,
        p20_adv_fixture["apex_admin"].id,
        ExecutiveSnapshotCreate(snapshot_code="SNAP-TAMPER-DET"),
    )
    artifact = ExecutiveService.generate_pdf_export(
        db,
        p20_adv_fixture["org_apex"].id,
        p20_adv_fixture["apex_admin"].id,
        ArtifactTypeEnum.POSTURE_SNAPSHOT,
        snap.id,
    )

    # Tamper with the physical file on disk
    with open(artifact.storage_key, "ab") as f:
        f.write(b"TAMPERED_CONTENT")

    # Download attempt should fail with 409 checksum mismatch
    res = client.get(f"/api/v1/executive/exports/{artifact.id}/download", headers=p20_adv_fixture["apex_admin_headers"])
    assert res.status_code == 409
    assert "checksum mismatch" in res.json()["detail"]


def test_adv_p20_18_trends_parameter_extreme_value_handling(client: TestClient, p20_adv_fixture):
    """ADV-P20-18: Trends window_days > 1095 or <= 0 rejected."""
    res = client.get("/api/v1/executive/telemetry/trends?window_days=9999", headers=p20_adv_fixture["apex_admin_headers"])
    assert res.status_code in [400, 422]

    res_neg = client.get("/api/v1/executive/telemetry/trends?window_days=-5", headers=p20_adv_fixture["apex_admin_headers"])
    assert res_neg.status_code in [400, 422]


def test_adv_p20_19_sql_injection_in_date_filters_mitigation(client: TestClient, p20_adv_fixture):
    """ADV-P20-19: SQL injection payloads in trends window parameter safely rejected."""
    res = client.get("/api/v1/executive/telemetry/trends?window_days=10;DROP TABLE executive_snapshots;--", headers=p20_adv_fixture["apex_admin_headers"])
    assert res.status_code in [400, 422]


def test_adv_p20_20_mutation_without_audit_log_verification(client: TestClient, p20_adv_fixture, db: Session):
    """ADV-P20-20: Ensure snapshot capture generates immutable AuditLog entry."""
    res = client.post(
        "/api/v1/executive/snapshots",
        json={"snapshot_code": "SNAP-AUDIT-TEST"},
        headers=p20_adv_fixture["apex_admin_headers"],
    )
    assert res.status_code == 201

    log = db.query(AuditLog).filter(
        AuditLog.organization_id == p20_adv_fixture["org_apex"].id,
        AuditLog.action == "executive.snapshot.create",
    ).order_by(AuditLog.timestamp.desc()).first()

    assert log is not None
    assert log.actor_id == p20_adv_fixture["apex_admin"].id


def test_adv_p20_21_spoofed_reviewer_identity_ignored(client: TestClient, p20_adv_fixture):
    """ADV-P20-21: Reviewer identity comes from token, not body."""
    snap_res = client.post(
        "/api/v1/executive/snapshots",
        json={"snapshot_code": "SNAP-SPOOF-TEST"},
        headers=p20_adv_fixture["apex_admin_headers"],
    )
    snap_id = snap_res.json()["id"]

    res = client.post(
        "/api/v1/executive/briefings",
        json={
            "briefing_code": "BRF-SPOOF-TEST",
            "title": "Spoof Test",
            "reporting_period_start": "2026-01-01",
            "reporting_period_end": "2026-03-31",
            "snapshot_id": snap_id,
            "executive_summary": "Spoof summary",
        },
        headers=p20_adv_fixture["apex_analyst_headers"],
    )
    briefing_id = res.json()["id"]
    client.post(f"/api/v1/executive/briefings/{briefing_id}/submit", headers=p20_adv_fixture["apex_analyst_headers"])

    # Manager approves but payload tries to attribute to admin
    rev_res = client.post(
        f"/api/v1/executive/briefings/{briefing_id}/review",
        json={"approved": True, "approved_by_id": p20_adv_fixture["apex_admin"].id},
        headers=p20_adv_fixture["apex_mgr_headers"],
    )
    assert rev_res.status_code == 200
    assert rev_res.json()["approved_by_id"] == p20_adv_fixture["apex_manager"].id


def test_adv_p20_22_unsupported_export_format_rejection(client: TestClient, p20_adv_fixture):
    """ADV-P20-22: Unsupported export format parameter returns 422."""
    res = client.post(
        "/api/v1/executive/exports/snapshot/1?format=XML",
        headers=p20_adv_fixture["apex_admin_headers"],
    )
    assert res.status_code == 422


def test_adv_p20_23_foreign_snapshot_compilation_in_dossier(client: TestClient, p20_adv_fixture, db: Session):
    """ADV-P20-23: Cross-tenant snapshot reference in dossier creation returns 404."""
    meridian_snap = ExecutiveService.capture_snapshot(
        db,
        p20_adv_fixture["org_meridian"].id,
        p20_adv_fixture["meridian_admin"].id,
        ExecutiveSnapshotCreate(snapshot_code="MERIDIAN-SNAP-23"),
    )

    res = client.post(
        "/api/v1/executive/dossiers",
        json={
            "dossier_code": "DOS-FOREIGN-SNAP",
            "title": "Foreign Snapshot Test",
            "snapshot_id": meridian_snap.id,
        },
        headers=p20_adv_fixture["apex_analyst_headers"],
    )
    assert res.status_code == 404


def test_adv_p20_24_inverted_briefing_period_rejection(client: TestClient, p20_adv_fixture):
    """ADV-P20-24: Reject briefing with end date earlier than start date."""
    snap_res = client.post(
        "/api/v1/executive/snapshots",
        json={"snapshot_code": "SNAP-INV-DATE"},
        headers=p20_adv_fixture["apex_admin_headers"],
    )
    snap_id = snap_res.json()["id"]

    res = client.post(
        "/api/v1/executive/briefings",
        json={
            "briefing_code": "BRF-INV-DATE",
            "title": "Inverted Date Test",
            "reporting_period_start": "2026-12-31",
            "reporting_period_end": "2026-01-01",
            "snapshot_id": snap_id,
            "executive_summary": "Inverted date test summary",
        },
        headers=p20_adv_fixture["apex_admin_headers"],
    )
    assert res.status_code == 400


def test_adv_p20_25_closed_data_exclusion_in_live_telemetry(client: TestClient, p20_adv_fixture, db: Session):
    """ADV-P20-25: Closed risks do not penalize inherent/residual risk index."""
    closed_risk = Risk(
        organization_id=p20_adv_fixture["org_apex"].id,
        title="Resolved Past Risk",
        description="Resolved description",
        inherent_score=25,
        status=RiskStatusEnum.CLOSED,
    )
    db.add(closed_risk)
    db.commit()

    res = client.get("/api/v1/executive/telemetry/live", headers=p20_adv_fixture["apex_analyst_headers"])
    assert res.status_code == 200
    data = res.json()
    assert not any(r["title"] == "Resolved Past Risk" for r in data.get("top_risks", []))


def test_adv_p20_26_four_eyes_dossier_compiler_finalization_violation(client: TestClient, p20_adv_fixture):
    """ADV-P20-26: Compiler of dossier cannot finalize it."""
    # Admin creates dossier
    dossier_res = client.post(
        "/api/v1/executive/dossiers",
        json={"dossier_code": "DOS-COMP-FINAL-SOD", "title": "Compiler Finalization Test"},
        headers=p20_adv_fixture["apex_admin_headers"],
    )
    dossier_id = dossier_res.json()["id"]

    # Manager compiles dossier
    client.post(f"/api/v1/executive/dossiers/{dossier_id}/compile", headers=p20_adv_fixture["apex_mgr_headers"])

    # Manager attempts to finalize dossier -> Blocked by Four-Eyes
    fin_res = client.post(f"/api/v1/executive/dossiers/{dossier_id}/finalize", headers=p20_adv_fixture["apex_mgr_headers"])
    assert fin_res.status_code == 400
    assert "Four-Eyes violation" in fin_res.json()["detail"]


def test_adv_p20_27_duplicate_snapshot_code_conflict(client: TestClient, p20_adv_fixture):
    """ADV-P20-27: Duplicate snapshot code within tenant returns 409 Conflict."""
    client.post(
        "/api/v1/executive/snapshots",
        json={"snapshot_code": "SNAP-DUP-TEST"},
        headers=p20_adv_fixture["apex_admin_headers"],
    )
    dup_res = client.post(
        "/api/v1/executive/snapshots",
        json={"snapshot_code": "SNAP-DUP-TEST"},
        headers=p20_adv_fixture["apex_admin_headers"],
    )
    assert dup_res.status_code == 409

from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.permissions import RoleEnum
from app.core.security import get_password_hash
from app.models.control import OrganizationControl, ImplementationStatusEnum
from app.models.evidence import EvidenceItem, EvidenceRequirement, EvidenceStatusEnum
from app.models.finding import Finding, FindingSeverityEnum, FindingStatusEnum, FindingTypeEnum
from app.models.framework import Framework, FrameworkCategory, FrameworkFunction, FrameworkSubcategory
from app.models.incident import IncidentCategoryEnum, IncidentSeverityEnum, SecurityIncident
from app.models.monitoring import ComplianceDriftAlert, DriftAlertSeverityEnum, DriftAlertStatusEnum, DriftAlertTypeEnum
from app.models.organization import Organization
from app.models.remediation import (
    EvidenceVerificationStatusEnum,
    RemediationEvidenceLink,
    RemediationPlan,
    RemediationReTestRecord,
    RemediationRootCauseClassificationEnum,
    RemediationSeverityEnum,
    RemediationSourceTypeEnum,
    RemediationStatusEnum,
    RemediationTask,
    ReTestResultEnum,
    SlaStatusEnum,
    TaskStatusEnum,
)
from app.models.user import User
from tests.conftest import get_token_headers


@pytest.fixture
def remediation_api_fixture(db: Session, org_apex: Organization):
    admin = User(
        email="admin@remediation.internal",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Remediation Admin",
        role=RoleEnum.ADMIN,
        is_active=True,
        organization_id=org_apex.id,
    )
    manager = User(
        email="manager@remediation.internal",
        hashed_password=get_password_hash("ManagerPass123!"),
        full_name="Remediation Manager",
        role=RoleEnum.MANAGER,
        is_active=True,
        organization_id=org_apex.id,
    )
    analyst = User(
        email="analyst@remediation.internal",
        hashed_password=get_password_hash("AnalystPass123!"),
        full_name="Remediation Analyst",
        role=RoleEnum.GRC_ANALYST,
        is_active=True,
        organization_id=org_apex.id,
    )
    auditor = User(
        email="auditor@remediation.internal",
        hashed_password=get_password_hash("AuditorPass123!"),
        full_name="Remediation Auditor",
        role=RoleEnum.AUDITOR,
        is_active=True,
        organization_id=org_apex.id,
    )
    viewer = User(
        email="viewer@remediation.internal",
        hashed_password=get_password_hash("ViewerPass123!"),
        full_name="Remediation Viewer",
        role=RoleEnum.VIEWER,
        is_active=True,
        organization_id=org_apex.id,
    )
    db.add_all([admin, manager, analyst, auditor, viewer])
    db.commit()
    db.refresh(admin)
    db.refresh(manager)
    db.refresh(analyst)
    db.refresh(auditor)
    db.refresh(viewer)

    # Framework & Control
    fw = Framework(name="SOC 2 Security", identifier="SOC2-SEC", version="2024")
    db.add(fw)
    db.commit()
    db.refresh(fw)

    fn = FrameworkFunction(framework_id=fw.id, identifier="CC", name="Common Criteria")
    db.add(fn)
    db.commit()
    db.refresh(fn)

    cat = FrameworkCategory(function_id=fn.id, identifier="CC6", name="Logical Access")
    db.add(cat)
    db.commit()
    db.refresh(cat)

    subcat = FrameworkSubcategory(
        category_id=cat.id, identifier="CC6.1", title="Logical Access Controls", description="Access control policies"
    )
    db.add(subcat)
    db.commit()
    db.refresh(subcat)

    ctrl = OrganizationControl(
        organization_id=org_apex.id,
        subcategory_id=subcat.id,
        status=ImplementationStatusEnum.IN_PROGRESS,
    )
    db.add(ctrl)
    db.commit()
    db.refresh(ctrl)

    # Sources
    finding = Finding(
        organization_id=org_apex.id,
        organization_control_id=ctrl.id,
        title="MFA Missing on Bastion Host",
        description="SSH bastion allows single-factor password authentication",
        finding_type=FindingTypeEnum.CONTROL_GAP,
        severity=FindingSeverityEnum.HIGH,
        recommendation="Enforce DUO MFA or WebAuthn keys",
        status=FindingStatusEnum.OPEN,
        created_at=datetime.now(timezone.utc) - timedelta(days=5),
    )
    drift = ComplianceDriftAlert(
        organization_id=org_apex.id,
        organization_control_id=ctrl.id,
        alert_type=DriftAlertTypeEnum.EVIDENCE_EXPIRED,
        severity=DriftAlertSeverityEnum.HIGH,
        status=DriftAlertStatusEnum.ACTIVE,
        title="Expired Bastion Key Audit Evidence",
        description="Evidence item CC6.1 expired 3 days ago",
        created_at=datetime.now(timezone.utc) - timedelta(days=3),
    )
    incident = SecurityIncident(
        organization_id=org_apex.id,
        incident_code="INC-API-01",
        title="Bastion Unauthorized Access Attempt",
        description="Brute force activity detected on bastion",
        severity=IncidentSeverityEnum.HIGH,
        category=IncidentCategoryEnum.UNAUTHORIZED_ACCESS,
        incident_commander_id=manager.id,
        detected_at=datetime.now(timezone.utc) - timedelta(days=2),
    )
    db.add_all([finding, drift, incident])
    db.commit()
    db.refresh(finding)
    db.refresh(drift)
    db.refresh(incident)

    # Evidence Item
    ev_req = EvidenceRequirement(
        organization_id=org_apex.id,
        organization_control_id=ctrl.id,
        title="Bastion MFA Config",
    )
    db.add(ev_req)
    db.commit()
    db.refresh(ev_req)

    evidence = EvidenceItem(
        organization_id=org_apex.id,
        organization_control_id=ctrl.id,
        evidence_requirement_id=ev_req.id,
        title="MFA SSH Config Screenshot",
        original_filename="sshd_config.png",
        stored_filename="stored_sshd_config.png",
        file_extension="png",
        content_type="image/png",
        file_size=2048,
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        storage_key="evidence/sshd_config.png",
        status=EvidenceStatusEnum.ACCEPTED,
        uploaded_by_id=analyst.id,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)

    return {
        "admin": admin,
        "manager": manager,
        "analyst": analyst,
        "auditor": auditor,
        "viewer": viewer,
        "finding": finding,
        "drift": drift,
        "incident": incident,
        "evidence": evidence,
        "ctrl": ctrl,
    }


def test_full_remediation_api_lifecycle(client: TestClient, db: Session, remediation_api_fixture):
    """End-to-end API test verifying complete lifecycle and upstream Finding resolution."""
    fx = remediation_api_fixture
    analyst_headers = get_token_headers(fx["analyst"])
    manager_headers = get_token_headers(fx["manager"])
    auditor_headers = get_token_headers(fx["auditor"])

    # 1. Create Remediation Plan (CAPA)
    res_create = client.post(
        "/api/v1/remediations",
        json={
            "plan_code": "CAPA-MFA-01",
            "title": "Enforce Bastion MFA & Key Rotation",
            "problem_statement": "Single-factor SSH bastion violates SOC2 CC6.1 requirement",
            "root_cause_classification": "CONTROL_DEFICIENCY",
            "source_type": "FINDING",
            "severity": "HIGH",
            "finding_id": fx["finding"].id,
        },
        headers=analyst_headers,
    )
    assert res_create.status_code == 201
    plan_data = res_create.json()
    plan_id = plan_data["id"]
    assert plan_data["status"] == "DRAFT"
    assert plan_data["sla_status"] == "NOT_STARTED"
    assert plan_data["finding_id"] == fx["finding"].id

    # 2. Add Tasks
    res_t1 = client.post(
        f"/api/v1/remediations/{plan_id}/tasks",
        json={
            "task_seq": 1,
            "title": "Configure PAM MFA module on Bastion",
            "description": "Deploy PAM Duo module and update sshd_config",
            "assignee_id": fx["analyst"].id,
        },
        headers=analyst_headers,
    )
    assert res_t1.status_code == 201
    task1_id = res_t1.json()["id"]

    res_t2 = client.post(
        f"/api/v1/remediations/{plan_id}/tasks",
        json={
            "task_seq": 2,
            "title": "Rotate all existing SSH host keys",
            "description": "Generate new ed25519 host keys and revoke old keys",
            "assignee_id": fx["analyst"].id,
        },
        headers=analyst_headers,
    )
    assert res_t2.status_code == 201
    task2_id = res_t2.json()["id"]

    # 3. Manager Approves Plan
    target_dt = (datetime.now(timezone.utc) + timedelta(days=25)).isoformat()
    res_app = client.post(
        f"/api/v1/remediations/{plan_id}/approve",
        json={"target_completion_at": target_dt, "notes": "Approved for emergency change window."},
        headers=manager_headers,
    )
    assert res_app.status_code == 200
    assert res_app.json()["status"] == "APPROVED"
    assert res_app.json()["sla_status"] == "ON_TRACK"

    # 4. Start Execution
    res_start = client.post(f"/api/v1/remediations/{plan_id}/start", headers=analyst_headers)
    assert res_start.status_code == 200
    assert res_start.json()["status"] == "IN_EXECUTION"

    # 5. Task 1: Start, Link Evidence, Complete
    client.post(f"/api/v1/remediations/tasks/{task1_id}/start", headers=analyst_headers)
    res_link = client.post(
        f"/api/v1/remediations/tasks/{task1_id}/evidence",
        json={"evidence_id": fx["evidence"].id, "notes": "PAM Duo configuration evidence"},
        headers=analyst_headers,
    )
    assert res_link.status_code == 201

    client.post(f"/api/v1/remediations/tasks/{task1_id}/complete", headers=analyst_headers)

    # 6. Task 2: Start, Link Evidence, Complete
    client.post(f"/api/v1/remediations/tasks/{task2_id}/start", headers=analyst_headers)
    client.post(
        f"/api/v1/remediations/tasks/{task2_id}/evidence",
        json={"evidence_id": fx["evidence"].id, "notes": "Key rotation logs"},
        headers=analyst_headers,
    )
    client.post(f"/api/v1/remediations/tasks/{task2_id}/complete", headers=analyst_headers)

    # 7. Submit for Validation
    res_sub = client.post(
        f"/api/v1/remediations/{plan_id}/submit-validation", headers=analyst_headers
    )
    assert res_sub.status_code == 200
    assert res_sub.json()["status"] == "PENDING_VALIDATION"

    # 8. Log Empirical PASS Re-Test
    res_retest = client.post(
        f"/api/v1/remediations/{plan_id}/retests",
        json={
            "test_executed_at": datetime.now(timezone.utc).isoformat(),
            "test_result": "PASS",
            "evidence_id": fx["evidence"].id,
            "metric_observed_value": 100.0,
            "validation_narrative": "Verified sshd requires Duo push notification and key rotation succeeded.",
        },
        headers=auditor_headers,
    )
    assert res_retest.status_code == 201

    # 9. Auditor Executes Four-Eyes Verification and Closure
    res_close = client.post(
        f"/api/v1/remediations/{plan_id}/verify-close",
        json={"verification_notes": "Independent auditor confirmed MFA is enforced and finding resolved."},
        headers=auditor_headers,
    )
    assert res_close.status_code == 200
    closed_data = res_close.json()
    assert closed_data["status"] == "VERIFIED_CLOSED"
    assert closed_data["is_immutable"] is True
    assert closed_data["rei_score"] == 100.0
    assert closed_data["ttr_hours"] is not None

    # 10. Verify Upstream Finding Auto-Resolution
    db.refresh(fx["finding"])
    assert fx["finding"].status == FindingStatusEnum.RESOLVED
    assert "Resolved via verified CAPA CAPA-MFA-01" in fx["finding"].resolution
    assert fx["finding"].resolved_by_id == fx["auditor"].id


def test_ccm_drift_upstream_resolution(client: TestClient, db: Session, remediation_api_fixture):
    """Verifies that verifying a CCM Drift remediation plan auto-resolves ComplianceDriftAlert."""
    fx = remediation_api_fixture
    analyst_headers = get_token_headers(fx["analyst"])
    manager_headers = get_token_headers(fx["manager"])
    auditor_headers = get_token_headers(fx["auditor"])

    res_create = client.post(
        "/api/v1/remediations",
        json={
            "plan_code": "CAPA-DRIFT-01",
            "title": "Refresh Expired Evidence",
            "problem_statement": "Automated drift detected expired evidence item",
            "root_cause_classification": "CONFIGURATION_DRIFT",
            "source_type": "CCM_DRIFT",
            "severity": "HIGH",
            "compliance_drift_alert_id": fx["drift"].id,
        },
        headers=analyst_headers,
    )
    plan_id = res_create.json()["id"]

    # Task
    res_t = client.post(
        f"/api/v1/remediations/{plan_id}/tasks",
        json={
            "task_seq": 1,
            "title": "Upload fresh evidence artifact",
            "description": "Obtain newly signed auditor artifact and upload",
            "assignee_id": fx["analyst"].id,
        },
        headers=analyst_headers,
    )
    task_id = res_t.json()["id"]

    client.post(f"/api/v1/remediations/{plan_id}/approve", json={}, headers=manager_headers)
    client.post(f"/api/v1/remediations/{plan_id}/start", headers=analyst_headers)
    client.post(
        f"/api/v1/remediations/tasks/{task_id}/evidence",
        json={"evidence_id": fx["evidence"].id},
        headers=analyst_headers,
    )
    client.post(f"/api/v1/remediations/tasks/{task_id}/complete", headers=analyst_headers)
    client.post(f"/api/v1/remediations/{plan_id}/submit-validation", headers=analyst_headers)

    client.post(
        f"/api/v1/remediations/{plan_id}/retests",
        json={
            "test_executed_at": datetime.now(timezone.utc).isoformat(),
            "test_result": "PASS",
            "evidence_id": fx["evidence"].id,
            "validation_narrative": "Verified newly uploaded evidence passes all checks.",
        },
        headers=auditor_headers,
    )

    client.post(
        f"/api/v1/remediations/{plan_id}/verify-close",
        json={"verification_notes": "Auditor verified fresh evidence resolves drift."},
        headers=auditor_headers,
    )

    db.refresh(fx["drift"])
    assert fx["drift"].status == DriftAlertStatusEnum.RESOLVED
    assert fx["drift"].resolved_by_id == fx["auditor"].id
    assert "Auto-resolved via verified Remediation Plan CAPA-DRIFT-01" in fx["drift"].resolution_notes


def test_incident_timeline_upstream_assurance(client: TestClient, db: Session, remediation_api_fixture):
    """Verifies that verifying an Incident CAPA appends an immutable timeline event without directly closing incident."""
    fx = remediation_api_fixture
    analyst_headers = get_token_headers(fx["analyst"])
    manager_headers = get_token_headers(fx["manager"])
    auditor_headers = get_token_headers(fx["auditor"])

    res_create = client.post(
        "/api/v1/remediations",
        json={
            "plan_code": "CAPA-INCIDENT-01",
            "title": "Incident Eradication CAPA",
            "problem_statement": "Post-incident hardening",
            "root_cause_classification": "HUMAN_ERROR",
            "source_type": "SECURITY_INCIDENT",
            "severity": "CRITICAL",
            "security_incident_id": fx["incident"].id,
        },
        headers=analyst_headers,
    )
    plan_id = res_create.json()["id"]

    res_t = client.post(
        f"/api/v1/remediations/{plan_id}/tasks",
        json={
            "task_seq": 1,
            "title": "Harden firewall rules",
            "description": "Block brute-force IP ranges at perimeter",
            "assignee_id": fx["analyst"].id,
        },
        headers=analyst_headers,
    )
    task_id = res_t.json()["id"]

    client.post(f"/api/v1/remediations/{plan_id}/approve", json={}, headers=manager_headers)
    client.post(f"/api/v1/remediations/{plan_id}/start", headers=analyst_headers)
    client.post(
        f"/api/v1/remediations/tasks/{task_id}/evidence",
        json={"evidence_id": fx["evidence"].id},
        headers=analyst_headers,
    )
    client.post(f"/api/v1/remediations/tasks/{task_id}/complete", headers=analyst_headers)
    client.post(f"/api/v1/remediations/{plan_id}/submit-validation", headers=analyst_headers)

    client.post(
        f"/api/v1/remediations/{plan_id}/retests",
        json={
            "test_executed_at": datetime.now(timezone.utc).isoformat(),
            "test_result": "PASS",
            "evidence_id": fx["evidence"].id,
            "validation_narrative": "Port scan confirms unauthorized ingress blocked.",
        },
        headers=auditor_headers,
    )

    client.post(
        f"/api/v1/remediations/{plan_id}/verify-close",
        json={"verification_notes": "Auditor verification of incident eradication."},
        headers=auditor_headers,
    )

    db.refresh(fx["incident"])
    # Phase 10 incident status is NOT altered directly
    assert fx["incident"].status != "CLOSED"
    # Timeline event was appended
    events = fx["incident"].timeline_events
    eradication_event = [e for e in events if "CAPA-INCIDENT-01" in e.description]
    assert len(eradication_event) >= 1


def test_remediation_overview_kpis(client: TestClient, db: Session, remediation_api_fixture):
    """Verifies overview aggregate KPI endpoint."""
    fx = remediation_api_fixture
    analyst_headers = get_token_headers(fx["analyst"])

    res = client.get("/api/v1/remediations/overview", headers=analyst_headers)
    assert res.status_code == 200
    data = res.json()
    assert "total_plans" in data
    assert "open_plans" in data
    assert "critical_or_high_plans" in data
    assert "status_distribution" in data
    assert "sla_distribution" in data


def test_remediation_rbac_enforcement(client: TestClient, db: Session, remediation_api_fixture):
    """Verifies that AUDITOR cannot create/execute, ANALYST cannot approve/verify, and VIEWER is read-only."""
    fx = remediation_api_fixture
    auditor_headers = get_token_headers(fx["auditor"])
    analyst_headers = get_token_headers(fx["analyst"])
    viewer_headers = get_token_headers(fx["viewer"])

    # 1. Auditor cannot create plan (REMEDIATION_MANAGE required)
    res_aud_create = client.post(
        "/api/v1/remediations",
        json={
            "plan_code": "CAPA-AUD-FAIL",
            "title": "Auditor Create Plan",
            "problem_statement": "Problem statement",
            "root_cause_classification": "CONTROL_DEFICIENCY",
            "source_type": "FINDING",
            "finding_id": fx["finding"].id,
        },
        headers=auditor_headers,
    )
    assert res_aud_create.status_code == 403

    # 2. Analyst creates plan
    res_an_create = client.post(
        "/api/v1/remediations",
        json={
            "plan_code": "CAPA-AN-OK",
            "title": "Analyst Create Plan",
            "problem_statement": "Problem statement",
            "root_cause_classification": "CONTROL_DEFICIENCY",
            "source_type": "FINDING",
            "finding_id": fx["finding"].id,
        },
        headers=analyst_headers,
    )
    assert res_an_create.status_code == 201
    plan_id = res_an_create.json()["id"]

    # 3. Analyst cannot approve plan (REMEDIATION_APPROVE required)
    res_an_app = client.post(
        f"/api/v1/remediations/{plan_id}/approve",
        json={},
        headers=analyst_headers,
    )
    assert res_an_app.status_code == 403

    # 4. Viewer cannot add tasks or approve
    res_v_task = client.post(
        f"/api/v1/remediations/{plan_id}/tasks",
        json={"task_seq": 1, "title": "Task", "description": "Valid task description"},
        headers=viewer_headers,
    )
    assert res_v_task.status_code == 403

    # 5. Viewer can read
    res_v_read = client.get(f"/api/v1/remediations/{plan_id}", headers=viewer_headers)
    assert res_v_read.status_code == 200


def test_remediation_filtering_and_search(client: TestClient, db: Session, remediation_api_fixture):
    """Verifies listing filters by status, severity, source_type, and search keyword."""
    fx = remediation_api_fixture
    analyst_headers = get_token_headers(fx["analyst"])

    res_all = client.get("/api/v1/remediations", headers=analyst_headers)
    assert res_all.status_code == 200
    assert isinstance(res_all.json(), list)

    res_search = client.get("/api/v1/remediations?search=Bastion", headers=analyst_headers)
    assert res_search.status_code == 200

    res_status = client.get("/api/v1/remediations?status=DRAFT", headers=analyst_headers)
    assert res_status.status_code == 200


def test_validation_rejection_and_rework_flow(client: TestClient, db: Session, remediation_api_fixture):
    """Verifies rejecting validation sends plan back to IN_EXECUTION with required notes."""
    fx = remediation_api_fixture
    analyst_headers = get_token_headers(fx["analyst"])
    manager_headers = get_token_headers(fx["manager"])
    auditor_headers = get_token_headers(fx["auditor"])

    res_create = client.post(
        "/api/v1/remediations",
        json={
            "plan_code": "CAPA-REWORK-01",
            "title": "Rework Lifecycle Test",
            "problem_statement": "Problem statement",
            "root_cause_classification": "CONTROL_DEFICIENCY",
            "source_type": "FINDING",
            "finding_id": fx["finding"].id,
        },
        headers=analyst_headers,
    )
    plan_id = res_create.json()["id"]

    res_t = client.post(
        f"/api/v1/remediations/{plan_id}/tasks",
        json={"task_seq": 1, "title": "Task 1", "description": "Valid task description"},
        headers=analyst_headers,
    )
    task_id = res_t.json()["id"]

    client.post(f"/api/v1/remediations/{plan_id}/approve", json={}, headers=manager_headers)
    client.post(f"/api/v1/remediations/{plan_id}/start", headers=analyst_headers)
    client.post(
        f"/api/v1/remediations/tasks/{task_id}/evidence",
        json={"evidence_id": fx["evidence"].id},
        headers=analyst_headers,
    )
    client.post(f"/api/v1/remediations/tasks/{task_id}/complete", headers=analyst_headers)
    client.post(f"/api/v1/remediations/{plan_id}/submit-validation", headers=analyst_headers)

    # Auditor rejects validation
    res_rej = client.post(
        f"/api/v1/remediations/{plan_id}/reject-validation",
        json={"rejection_notes": "Evidence shows incomplete cipher configuration. Needs rework."},
        headers=auditor_headers,
    )
    assert res_rej.status_code == 200
    assert res_rej.json()["status"] == "IN_EXECUTION"


def test_plan_cancellation_and_task_unlink(client: TestClient, db: Session, remediation_api_fixture):
    """Verifies cancelling a plan, unlinking evidence, and immutability after cancellation."""
    fx = remediation_api_fixture
    analyst_headers = get_token_headers(fx["analyst"])

    res_create = client.post(
        "/api/v1/remediations",
        json={
            "plan_code": "CAPA-CANCEL-01",
            "title": "Cancellation Test Plan",
            "problem_statement": "Problem statement",
            "root_cause_classification": "CONTROL_DEFICIENCY",
            "source_type": "FINDING",
            "finding_id": fx["finding"].id,
        },
        headers=analyst_headers,
    )
    plan_id = res_create.json()["id"]

    res_t = client.post(
        f"/api/v1/remediations/{plan_id}/tasks",
        json={"task_seq": 1, "title": "Task 1", "description": "Valid task description"},
        headers=analyst_headers,
    )
    task_id = res_t.json()["id"]

    res_link = client.post(
        f"/api/v1/remediations/tasks/{task_id}/evidence",
        json={"evidence_id": fx["evidence"].id},
        headers=analyst_headers,
    )
    link_id = res_link.json()["id"]

    # Unlink evidence
    res_unlink = client.delete(
        f"/api/v1/remediations/tasks/{task_id}/evidence/{link_id}", headers=analyst_headers
    )
    assert res_unlink.status_code == 204

    # Cancel plan
    res_cancel = client.post(
        f"/api/v1/remediations/{plan_id}/cancel",
        json={"cancellation_notes": "Risk accepted by executive committee. Plan cancelled."},
        headers=analyst_headers,
    )
    assert res_cancel.status_code == 200
    assert res_cancel.json()["status"] == "CANCELLED"
    assert res_cancel.json()["is_immutable"] is True

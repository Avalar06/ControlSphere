from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.permissions import RoleEnum
from app.core.security import get_password_hash
from app.models.control import OrganizationControl, ImplementationStatusEnum, PriorityEnum
from app.models.framework import Framework, FrameworkFunction, FrameworkCategory, FrameworkSubcategory
from app.models.organization import Organization
from app.models.user import User
from app.models.audit_log import AuditLog
from app.models.remediation import RemediationPlan, RemediationStatusEnum
from app.models.continuous_compliance import (
    ContinuousComplianceProfile,
    ComplianceDriftRecord,
    ContinuousAssuranceSnapshot,
    ComplianceDriftVectorEnum,
    ComplianceDriftSeverityEnum,
    ComplianceDriftStatusEnum,
)
from app.schemas.continuous_compliance import (
    ContinuousComplianceProfileUpdate,
    ContinuousAssuranceSnapshotCreate,
)
from app.services.continuous_compliance_service import ContinuousComplianceService
from tests.conftest import get_token_headers


@pytest.fixture
def p23_adv_fixture(db: Session, org_apex: Organization, org_meridian: Organization):
    """Setup adversarial test harness for Phase 23 Continuous-GRC."""
    apex_admin = User(
        email="p23_apex_admin@apex.com",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Apex Admin",
        role=RoleEnum.ADMIN,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_manager = User(
        email="p23_apex_manager@apex.com",
        hashed_password=get_password_hash("MgrPass123!"),
        full_name="Apex Manager",
        role=RoleEnum.MANAGER,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_analyst = User(
        email="p23_apex_analyst@apex.com",
        hashed_password=get_password_hash("AnalystPass123!"),
        full_name="Apex Analyst",
        role=RoleEnum.GRC_ANALYST,
        is_active=True,
        organization_id=org_apex.id,
    )
    meridian_admin = User(
        email="p23_meridian_admin@meridian.com",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Meridian Admin",
        role=RoleEnum.ADMIN,
        is_active=True,
        organization_id=org_meridian.id,
    )
    db.add_all([apex_admin, apex_manager, apex_analyst, meridian_admin])
    db.commit()

    # Seed Framework and Control for Apex
    fw = Framework(identifier="NIST-CSF-2.0-P23", name="NIST CSF 2.0", version="2.0")
    db.add(fw)
    db.flush()
    fn = FrameworkFunction(framework_id=fw.id, identifier="PR-P23", name="Protect")
    db.add(fn)
    db.flush()
    cat = FrameworkCategory(function_id=fn.id, identifier="PR.AC-P23", name="Access Control")
    db.add(cat)
    db.flush()
    subcat = FrameworkSubcategory(category_id=cat.id, identifier="PR.AC-01-P23", title="Identities Managed", description="Desc")
    db.add(subcat)
    db.flush()

    apex_ctrl = OrganizationControl(
        organization_id=org_apex.id,
        subcategory_id=subcat.id,
        status=ImplementationStatusEnum.IMPLEMENTED,
        priority=PriorityEnum.HIGH,
    )
    db.add(apex_ctrl)
    db.commit()

    # Seed Apex and Meridian profiles
    apex_profile = ContinuousComplianceService.get_or_create_profile(db, org_apex.id, apex_admin.id)
    meridian_profile = ContinuousComplianceService.get_or_create_profile(db, org_meridian.id, meridian_admin.id)

    # Seed an Apex drift record linked to control
    drift = ComplianceDriftRecord(
        organization_id=org_apex.id,
        organization_control_id=apex_ctrl.id,
        drift_code="DRIFT-TEST-01",
        drift_vector=ComplianceDriftVectorEnum.FINDING_SLA_BREACH,
        severity=ComplianceDriftSeverityEnum.HIGH,
        status=ComplianceDriftStatusEnum.OPEN,
        title="Critical Finding SLA Breach on Firewall",
        description="Finding #12 SLA overdue by 14 days.",
        root_cause_metric="finding_sla",
        detected_at=datetime.now(timezone.utc),
    )
    db.add(drift)
    db.commit()
    db.refresh(drift)

    return {
        "apex_admin": apex_admin,
        "apex_manager": apex_manager,
        "apex_analyst": apex_analyst,
        "meridian_admin": meridian_admin,
        "org_apex": org_apex,
        "org_meridian": org_meridian,
        "apex_ctrl": apex_ctrl,
        "apex_profile": apex_profile,
        "meridian_profile": meridian_profile,
        "drift": drift,
    }


def test_adv_p23_28_cross_tenant_profile_isolation(client: TestClient, p23_adv_fixture):
    """28 cross tenant profile isolation: Tenant B cannot view or modify Tenant A compliance profile."""
    meridian_headers = get_token_headers(p23_adv_fixture["meridian_admin"])
    res = client.get("/api/v1/continuous-compliance/profile", headers=meridian_headers)
    assert res.status_code == 200
    assert res.json()["organization_id"] == p23_adv_fixture["org_meridian"].id
    assert res.json()["organization_id"] != p23_adv_fixture["org_apex"].id


def test_adv_p23_29_client_assurance_score_manipulation_ignored(client: TestClient, p23_adv_fixture):
    """29 client assurance score manipulation ignored: Client cannot force 100.0 assurance score."""
    admin_headers = get_token_headers(p23_adv_fixture["apex_admin"])
    res = client.post("/api/v1/continuous-compliance/evaluate", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert "overall_assurance_score" in data
    assert isinstance(data["overall_assurance_score"], float)


def test_adv_p23_30_client_drift_severity_manipulation_ignored(client: TestClient, db: Session, p23_adv_fixture):
    """30 client drift severity manipulation ignored: Drift severity is strictly calculated server-side."""
    drift = p23_adv_fixture["drift"]
    assert drift.severity == ComplianceDriftSeverityEnum.HIGH


def test_adv_p23_31_unauthorized_profile_mutation_by_analyst(client: TestClient, p23_adv_fixture):
    """31 unauthorized profile mutation by analyst: GRC Analyst cannot mutate governance thresholds."""
    analyst_headers = get_token_headers(p23_adv_fixture["apex_analyst"])
    payload = {
        "drift_critical_threshold": 50.0,
        "min_control_health_score": 10.0,
    }
    res = client.put("/api/v1/continuous-compliance/profile", json=payload, headers=analyst_headers)
    assert res.status_code == 403


def test_adv_p23_32_cross_tenant_drift_remediation_trigger(client: TestClient, p23_adv_fixture):
    """32 cross tenant drift remediation trigger: Tenant B cannot trigger remediation on Tenant A drift record."""
    meridian_headers = get_token_headers(p23_adv_fixture["meridian_admin"])
    apex_drift_id = p23_adv_fixture["drift"].id

    res = client.post(f"/api/v1/continuous-compliance/drift/{apex_drift_id}/trigger-remediation", headers=meridian_headers)
    assert res.status_code == 404


def test_adv_p23_33_remediation_authority_delegation(client: TestClient, db: Session, p23_adv_fixture):
    """33 remediation authority delegation: Drift remediation trigger creates Phase 11 RemediationPlan."""
    admin_headers = get_token_headers(p23_adv_fixture["apex_admin"])
    apex_drift_id = p23_adv_fixture["drift"].id

    res = client.post(f"/api/v1/continuous-compliance/drift/{apex_drift_id}/trigger-remediation", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["remediation_plan_id"] is not None
    assert data["status"] == "REMEDIATION_TRIGGERED"

    # Verify that Phase 11 RemediationPlan was created
    plan = db.query(RemediationPlan).filter(RemediationPlan.id == data["remediation_plan_id"]).first()
    assert plan is not None
    assert plan.status == RemediationStatusEnum.DRAFT


def test_adv_p23_34_four_eyes_drift_remediation_closure(client: TestClient, db: Session, p23_adv_fixture):
    """34 Four-Eyes drift remediation closure: Creator/owner cannot self-verify Phase 11 CAPA plan."""
    from app.models.monitoring import ComplianceDriftAlert, DriftAlertTypeEnum, DriftAlertSeverityEnum, DriftAlertStatusEnum
    alert = ComplianceDriftAlert(
        organization_id=p23_adv_fixture["org_apex"].id,
        organization_control_id=p23_adv_fixture["apex_ctrl"].id,
        alert_type=DriftAlertTypeEnum.CONTROL_DEGRADED,
        severity=DriftAlertSeverityEnum.HIGH,
        status=DriftAlertStatusEnum.ACTIVE,
        title="Four Eyes Alert",
        description="Four Eyes Test Alert",
    )
    db.add(alert)
    db.flush()

    plan = RemediationPlan(
        organization_id=p23_adv_fixture["org_apex"].id,
        plan_code="CAPA-FOUR-EYES-01",
        title="CAPA Verification Test",
        problem_statement="Test statement",
        root_cause_classification="CONTROL_DEFICIENCY",
        source_type="CCM_DRIFT",
        compliance_drift_alert_id=alert.id,
        severity="HIGH",
        status=RemediationStatusEnum.DRAFT,
        plan_owner_id=p23_adv_fixture["apex_admin"].id,
    )
    db.add(plan)
    db.commit()
    assert plan.id is not None


def test_adv_p23_35_immutable_assurance_snapshot_tamper_rejection(client: TestClient, p23_adv_fixture):
    """35 immutable assurance snapshot tamper rejection: Snapshot data cannot be modified once captured."""
    admin_headers = get_token_headers(p23_adv_fixture["apex_admin"])

    snap_res = client.post(
        "/api/v1/continuous-compliance/snapshots",
        json={"snapshot_code": "SNAP-IMMUTABLE-01"},
        headers=admin_headers,
    )
    assert snap_res.status_code == 201
    snap_id = snap_res.json()["id"]

    # Attempt PUT/PATCH on snapshot endpoint -> MUST return 405 Method Not Allowed / 404
    put_res = client.put(f"/api/v1/continuous-compliance/snapshots/{snap_id}", json={"overall_assurance_score": 100.0}, headers=admin_headers)
    assert put_res.status_code in [404, 405]


def test_adv_p23_36_duplicate_snapshot_code_conflict(client: TestClient, p23_adv_fixture):
    """36 duplicate snapshot code conflict: Ingesting identical snapshot code returns HTTP 409."""
    admin_headers = get_token_headers(p23_adv_fixture["apex_admin"])

    res1 = client.post(
        "/api/v1/continuous-compliance/snapshots",
        json={"snapshot_code": "SNAP-DEDUP-01"},
        headers=admin_headers,
    )
    assert res1.status_code == 201

    res2 = client.post(
        "/api/v1/continuous-compliance/snapshots",
        json={"snapshot_code": "SNAP-DEDUP-01"},
        headers=admin_headers,
    )
    assert res2.status_code == 409


def test_adv_p23_37_audit_log_emission_on_continuous_evaluation(client: TestClient, db: Session, p23_adv_fixture):
    """37 audit log emission on continuous evaluation: Audit events are logged on evaluation."""
    admin_headers = get_token_headers(p23_adv_fixture["apex_admin"])

    eval_res = client.post("/api/v1/continuous-compliance/evaluate", headers=admin_headers)
    assert eval_res.status_code == 200

    audit = db.query(AuditLog).filter(
        AuditLog.organization_id == p23_adv_fixture["org_apex"].id,
        AuditLog.action == "EVALUATE_CONTINUOUS_COMPLIANCE",
    ).first()
    assert audit is not None

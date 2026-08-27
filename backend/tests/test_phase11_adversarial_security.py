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
    RemediationEvidenceLink,
    RemediationPlan,
    RemediationReTestRecord,
    RemediationRootCauseClassificationEnum,
    RemediationSeverityEnum,
    RemediationSourceTypeEnum,
    RemediationStatusEnum,
    RemediationTask,
    ReTestResultEnum,
    TaskStatusEnum,
)
from app.models.tprm import (
    BusinessCriticalityEnum,
    DataClassificationEnum,
    HostingModelEnum,
    NetworkConnectivityEnum,
    PiiFinancialAccessEnum,
    Vendor,
    VendorAssessment,
    VendorAssessmentStatusEnum,
    VendorAssessmentTypeEnum,
    VendorRiskBandEnum,
    VendorStatusEnum,
    VendorTierEnum,
)
from app.models.user import User
from tests.conftest import get_token_headers


@pytest.fixture
def adv_p11_fixture(db: Session, org_apex: Organization, org_meridian: Organization):
    # Apex users
    apex_manager = User(
        email="manager@apexfinancial.com",
        hashed_password=get_password_hash("ManagerPass123!"),
        full_name="Apex Manager",
        role=RoleEnum.MANAGER,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_analyst = User(
        email="analyst_p11@apexfinancial.com",
        hashed_password=get_password_hash("AnalystPass123!"),
        full_name="Apex Analyst",
        role=RoleEnum.GRC_ANALYST,
        is_active=True,
        organization_id=org_apex.id,
    )
    apex_auditor = User(
        email="auditor_p11@apexfinancial.com",
        hashed_password=get_password_hash("AuditorPass123!"),
        full_name="Apex Auditor",
        role=RoleEnum.AUDITOR,
        is_active=True,
        organization_id=org_apex.id,
    )
    # Meridian user
    meridian_analyst = User(
        email="analyst@meridianhealth.com",
        hashed_password=get_password_hash("MeridianPass123!"),
        full_name="Meridian Analyst",
        role=RoleEnum.GRC_ANALYST,
        is_active=True,
        organization_id=org_meridian.id,
    )
    db.add_all([apex_manager, apex_analyst, apex_auditor, meridian_analyst])
    db.commit()
    db.refresh(apex_manager)
    db.refresh(apex_analyst)
    db.refresh(apex_auditor)
    db.refresh(meridian_analyst)

    # Framework & Control for Apex
    fw = Framework(name="NIST CSF Apex", identifier="NIST-APEX", version="2.0")
    db.add(fw)
    db.commit()
    db.refresh(fw)

    fn = FrameworkFunction(framework_id=fw.id, identifier="PR", name="Protect")
    db.add(fn)
    db.commit()
    db.refresh(fn)

    cat = FrameworkCategory(function_id=fn.id, identifier="PR.DS", name="Data Security")
    db.add(cat)
    db.commit()
    db.refresh(cat)

    subcat = FrameworkSubcategory(
        category_id=cat.id, identifier="PR.DS-01", title="Data Protection", description="Data-at-rest is protected"
    )
    db.add(subcat)
    db.commit()
    db.refresh(subcat)

    ctrl_apex = OrganizationControl(
        organization_id=org_apex.id,
        subcategory_id=subcat.id,
        status=ImplementationStatusEnum.IN_PROGRESS,
    )
    ctrl_meridian = OrganizationControl(
        organization_id=org_meridian.id,
        subcategory_id=subcat.id,
        status=ImplementationStatusEnum.IN_PROGRESS,
    )
    db.add_all([ctrl_apex, ctrl_meridian])
    db.commit()
    db.refresh(ctrl_apex)
    db.refresh(ctrl_meridian)

    # Sources
    finding_apex = Finding(
        organization_id=org_apex.id,
        organization_control_id=ctrl_apex.id,
        title="Unencrypted DB",
        description="DB lacking AES-256",
        finding_type=FindingTypeEnum.CONTROL_GAP,
        severity=FindingSeverityEnum.HIGH,
        recommendation="Enable KMS",
        status=FindingStatusEnum.OPEN,
    )
    finding_meridian = Finding(
        organization_id=org_meridian.id,
        organization_control_id=ctrl_meridian.id,
        title="Meridian Unencrypted DB",
        description="DB lacking AES-256",
        finding_type=FindingTypeEnum.CONTROL_GAP,
        severity=FindingSeverityEnum.HIGH,
        recommendation="Enable KMS",
        status=FindingStatusEnum.OPEN,
    )
    db.add_all([finding_apex, finding_meridian])
    db.commit()
    db.refresh(finding_apex)
    db.refresh(finding_meridian)

    # Accepted Evidence for Apex & Meridian
    ev_req_apex = EvidenceRequirement(
        organization_id=org_apex.id,
        organization_control_id=ctrl_apex.id,
        title="Apex DB Encryption Evidence",
    )
    ev_req_meridian = EvidenceRequirement(
        organization_id=org_meridian.id,
        organization_control_id=ctrl_meridian.id,
        title="Meridian DB Encryption Evidence",
    )
    db.add_all([ev_req_apex, ev_req_meridian])
    db.commit()
    db.refresh(ev_req_apex)
    db.refresh(ev_req_meridian)

    evidence_apex = EvidenceItem(
        organization_id=org_apex.id,
        organization_control_id=ctrl_apex.id,
        evidence_requirement_id=ev_req_apex.id,
        title="KMS Screenshot",
        original_filename="kms.png",
        stored_filename="stored_kms.png",
        file_extension="png",
        content_type="image/png",
        file_size=1024,
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        storage_key="evidence/kms.png",
        status=EvidenceStatusEnum.ACCEPTED,
        uploaded_by_id=apex_analyst.id,
    )
    evidence_meridian = EvidenceItem(
        organization_id=org_meridian.id,
        organization_control_id=ctrl_meridian.id,
        evidence_requirement_id=ev_req_meridian.id,
        title="Meridian Screenshot",
        original_filename="meridian.png",
        stored_filename="stored_meridian.png",
        file_extension="png",
        content_type="image/png",
        file_size=1024,
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        storage_key="evidence/meridian.png",
        status=EvidenceStatusEnum.ACCEPTED,
        uploaded_by_id=meridian_analyst.id,
    )
    db.add_all([evidence_apex, evidence_meridian])
    db.commit()
    db.refresh(evidence_apex)
    db.refresh(evidence_meridian)

    return {
        "apex_manager": apex_manager,
        "apex_analyst": apex_analyst,
        "apex_auditor": apex_auditor,
        "meridian_analyst": meridian_analyst,
        "ctrl_apex": ctrl_apex,
        "finding_apex": finding_apex,
        "finding_meridian": finding_meridian,
        "evidence_apex": evidence_apex,
        "evidence_meridian": evidence_meridian,
    }


class TestPhase11AdversarialSecurity:
    """Authoritative 20-Test Adversarial Security Suite (ADV-P11-01 to ADV-P11-20)."""

    # ── ADV-P11-01: Cross-Tenant Remediation Plan Read IDOR ──────────────────
    def test_adv_p11_01_cross_tenant_plan_read_idor(
        self, client: TestClient, db: Session, adv_p11_fixture
    ):
        """ADV-P11-01: Tenant Meridian cannot read Tenant Apex's remediation plan."""
        fx = adv_p11_fixture
        apex_headers = get_token_headers(fx["apex_analyst"])
        meridian_headers = get_token_headers(fx["meridian_analyst"])

        res_create = client.post(
            "/api/v1/remediations",
            json={
                "plan_code": "CAPA-ADV-01",
                "title": "Apex Confidential CAPA",
                "problem_statement": "Confidential vulnerability remediation",
                "root_cause_classification": "CONTROL_DEFICIENCY",
                "source_type": "FINDING",
                "finding_id": fx["finding_apex"].id,
                "severity": "HIGH",
            },
            headers=apex_headers,
        )
        assert res_create.status_code == 201
        plan_id = res_create.json()["id"]

        # Meridian attempts to read Apex plan
        res_idor = client.get(f"/api/v1/remediations/{plan_id}", headers=meridian_headers)
        assert res_idor.status_code == 404

    # ── ADV-P11-02: Cross-Tenant Plan Update IDOR ────────────────────────────
    def test_adv_p11_02_cross_tenant_plan_update_idor(
        self, client: TestClient, db: Session, adv_p11_fixture
    ):
        """ADV-P11-02: Tenant Meridian cannot update Tenant Apex's remediation plan."""
        fx = adv_p11_fixture
        apex_headers = get_token_headers(fx["apex_analyst"])
        meridian_headers = get_token_headers(fx["meridian_analyst"])

        res_create = client.post(
            "/api/v1/remediations",
            json={
                "plan_code": "CAPA-ADV-02",
                "title": "Apex CAPA 02",
                "problem_statement": "Statement description",
                "root_cause_classification": "CONFIGURATION_DRIFT",
                "source_type": "FINDING",
                "finding_id": fx["finding_apex"].id,
                "severity": "MEDIUM",
            },
            headers=apex_headers,
        )
        plan_id = res_create.json()["id"]

        res_update = client.patch(
            f"/api/v1/remediations/{plan_id}",
            json={"title": "Hacked Title"},
            headers=meridian_headers,
        )
        assert res_update.status_code == 404

    # ── ADV-P11-03: Cross-Tenant Task Injection ──────────────────────────────
    def test_adv_p11_03_cross_tenant_task_injection(
        self, client: TestClient, db: Session, adv_p11_fixture
    ):
        """ADV-P11-03: Tenant Meridian cannot add tasks into Tenant Apex's plan."""
        fx = adv_p11_fixture
        apex_headers = get_token_headers(fx["apex_analyst"])
        meridian_headers = get_token_headers(fx["meridian_analyst"])

        res_create = client.post(
            "/api/v1/remediations",
            json={
                "plan_code": "CAPA-ADV-03",
                "title": "Apex CAPA 03",
                "problem_statement": "Statement description",
                "root_cause_classification": "HUMAN_ERROR",
                "source_type": "FINDING",
                "finding_id": fx["finding_apex"].id,
            },
            headers=apex_headers,
        )
        plan_id = res_create.json()["id"]

        res_task = client.post(
            f"/api/v1/remediations/{plan_id}/tasks",
            json={
                "task_seq": 1,
                "title": "Injected Task",
                "description": "Foreign task description",
            },
            headers=meridian_headers,
        )
        assert res_task.status_code == 404

    # ── ADV-P11-04: Cross-Tenant Evidence Linking ────────────────────────────
    def test_adv_p11_04_cross_tenant_evidence_linking(
        self, client: TestClient, db: Session, adv_p11_fixture
    ):
        """ADV-P11-04: Cannot link Meridian's EvidenceItem into Apex's task."""
        fx = adv_p11_fixture
        apex_headers = get_token_headers(fx["apex_analyst"])

        res_create = client.post(
            "/api/v1/remediations",
            json={
                "plan_code": "CAPA-ADV-04",
                "title": "Apex CAPA 04",
                "problem_statement": "Statement description",
                "root_cause_classification": "CONTROL_DEFICIENCY",
                "source_type": "FINDING",
                "finding_id": fx["finding_apex"].id,
            },
            headers=apex_headers,
        )
        plan_id = res_create.json()["id"]

        res_task = client.post(
            f"/api/v1/remediations/{plan_id}/tasks",
            json={"task_seq": 1, "title": "Task 1", "description": "Valid task description"},
            headers=apex_headers,
        )
        assert res_task.status_code == 201
        task_id = res_task.json()["id"]

        # Link Meridian's evidence item into Apex's task
        res_link = client.post(
            f"/api/v1/remediations/tasks/{task_id}/evidence",
            json={"evidence_id": fx["evidence_meridian"].id},
            headers=apex_headers,
        )
        assert res_link.status_code == 404

    # ── ADV-P11-05: Cross-Tenant Finding Ingestion ───────────────────────────
    def test_adv_p11_05_cross_tenant_finding_ingestion(
        self, client: TestClient, db: Session, adv_p11_fixture
    ):
        """ADV-P11-05: Cannot create a CAPA referencing a foreign Finding."""
        fx = adv_p11_fixture
        apex_headers = get_token_headers(fx["apex_analyst"])

        res = client.post(
            "/api/v1/remediations",
            json={
                "plan_code": "CAPA-ADV-05",
                "title": "Foreign Finding Link Attack",
                "problem_statement": "Statement description",
                "root_cause_classification": "CONTROL_DEFICIENCY",
                "source_type": "FINDING",
                "finding_id": fx["finding_meridian"].id,
            },
            headers=apex_headers,
        )
        assert res.status_code == 404

    # ── ADV-P11-06: Cross-Tenant CCM Alert Ingestion ──────────────────────────
    def test_adv_p11_06_cross_tenant_ccm_alert_ingestion(
        self, client: TestClient, db: Session, adv_p11_fixture, org_meridian
    ):
        """ADV-P11-06: Cannot link a foreign ComplianceDriftAlert."""
        fx = adv_p11_fixture
        apex_headers = get_token_headers(fx["apex_analyst"])

        foreign_alert = ComplianceDriftAlert(
            organization_id=org_meridian.id,
            organization_control_id=fx["ctrl_apex"].id,
            alert_type=DriftAlertTypeEnum.EVIDENCE_EXPIRED,
            severity=DriftAlertSeverityEnum.HIGH,
            status=DriftAlertStatusEnum.ACTIVE,
            title="Meridian Drift Alert",
            description="Foreign alert description",
        )
        db.add(foreign_alert)
        db.commit()

        res = client.post(
            "/api/v1/remediations",
            json={
                "plan_code": "CAPA-ADV-06",
                "title": "Foreign Alert Link Attack",
                "problem_statement": "Statement description",
                "root_cause_classification": "CONFIGURATION_DRIFT",
                "source_type": "CCM_DRIFT",
                "compliance_drift_alert_id": foreign_alert.id,
            },
            headers=apex_headers,
        )
        assert res.status_code == 404

    # ── ADV-P11-07: Cross-Tenant Incident Ingestion ──────────────────────────
    def test_adv_p11_07_cross_tenant_incident_ingestion(
        self, client: TestClient, db: Session, adv_p11_fixture, org_meridian
    ):
        """ADV-P11-07: Cannot link a foreign SecurityIncident."""
        fx = adv_p11_fixture
        apex_headers = get_token_headers(fx["apex_analyst"])

        foreign_inc = SecurityIncident(
            organization_id=org_meridian.id,
            incident_code="INC-MERIDIAN-99",
            title="Meridian Breach",
            description="Foreign breach description",
            severity=IncidentSeverityEnum.HIGH,
            category=IncidentCategoryEnum.DATA_BREACH,
            incident_commander_id=fx["meridian_analyst"].id,
            detected_at=datetime.now(timezone.utc),
        )
        db.add(foreign_inc)
        db.commit()

        res = client.post(
            "/api/v1/remediations",
            json={
                "plan_code": "CAPA-ADV-07",
                "title": "Foreign Incident Attack",
                "problem_statement": "Statement description",
                "root_cause_classification": "HUMAN_ERROR",
                "source_type": "SECURITY_INCIDENT",
                "security_incident_id": foreign_inc.id,
            },
            headers=apex_headers,
        )
        assert res.status_code == 404

    # ── ADV-P11-08: Cross-Tenant Vendor Assessment Ingestion ─────────────────
    def test_adv_p11_08_cross_tenant_vendor_assessment_ingestion(
        self, client: TestClient, db: Session, adv_p11_fixture, org_meridian
    ):
        """ADV-P11-08: Cannot link a foreign VendorAssessment."""
        fx = adv_p11_fixture
        apex_headers = get_token_headers(fx["apex_analyst"])

        v_foreign = Vendor(
            organization_id=org_meridian.id,
            vendor_code="VEND-FOREIGN-01",
            legal_name="Meridian Vendor LLC",
            calculated_tier=VendorTierEnum.TIER_2_SIGNIFICANT,
            vendor_status=VendorStatusEnum.ACTIVE,
        )
        db.add(v_foreign)
        db.commit()

        va_foreign = VendorAssessment(
            organization_id=org_meridian.id,
            vendor_id=v_foreign.id,
            assessment_code="ASSESS-FOREIGN-01",
            assessment_type=VendorAssessmentTypeEnum.INITIAL_DUE_DILIGENCE,
            title="Foreign Assessment",
            status=VendorAssessmentStatusEnum.DRAFT,
            assessor_id=fx["meridian_analyst"].id,
        )
        db.add(va_foreign)
        db.commit()

        res = client.post(
            "/api/v1/remediations",
            json={
                "plan_code": "CAPA-ADV-08",
                "title": "Foreign Vendor Attack",
                "problem_statement": "Statement description",
                "root_cause_classification": "VENDOR_DEFAULT",
                "source_type": "TPRM_ASSESSMENT",
                "vendor_assessment_id": va_foreign.id,
            },
            headers=apex_headers,
        )
        assert res.status_code == 404

    # ── ADV-P11-09: Organization ID Spoofing ─────────────────────────────────
    def test_adv_p11_09_organization_id_spoofing(
        self, client: TestClient, db: Session, adv_p11_fixture, org_apex, org_meridian
    ):
        """ADV-P11-09: Client cannot spoof organization_id in request payload."""
        fx = adv_p11_fixture
        apex_headers = get_token_headers(fx["apex_analyst"])

        res = client.post(
            "/api/v1/remediations",
            json={
                "organization_id": org_meridian.id,  # Spoofing attempt
                "plan_code": "CAPA-ADV-09",
                "title": "Org Spoof Attack",
                "problem_statement": "Statement description",
                "root_cause_classification": "CONTROL_DEFICIENCY",
                "source_type": "FINDING",
                "finding_id": fx["finding_apex"].id,
            },
            headers=apex_headers,
        )
        assert res.status_code == 201
        # Created plan must belong to Apex, not Meridian
        assert res.json()["organization_id"] == org_apex.id

    # ── ADV-P11-10: Plan Owner Spoofing ──────────────────────────────────────
    def test_adv_p11_10_plan_owner_id_spoofing(
        self, client: TestClient, db: Session, adv_p11_fixture
    ):
        """ADV-P11-10: Client cannot spoof plan_owner_id; must derive from JWT."""
        fx = adv_p11_fixture
        apex_headers = get_token_headers(fx["apex_analyst"])

        res = client.post(
            "/api/v1/remediations",
            json={
                "plan_owner_id": fx["apex_manager"].id,  # Spoofing attempt
                "plan_code": "CAPA-ADV-10",
                "title": "Owner Spoof Attack",
                "problem_statement": "Statement description",
                "root_cause_classification": "CONTROL_DEFICIENCY",
                "source_type": "FINDING",
                "finding_id": fx["finding_apex"].id,
            },
            headers=apex_headers,
        )
        assert res.status_code == 201
        assert res.json()["plan_owner_id"] == fx["apex_analyst"].id

    # ── ADV-P11-11: Plan Owner Self-Approval ─────────────────────────────────
    def test_adv_p11_11_plan_owner_self_approval(
        self, client: TestClient, db: Session, adv_p11_fixture
    ):
        """ADV-P11-11: Plan owner cannot approve their own remediation plan (HTTP 403)."""
        fx = adv_p11_fixture
        manager_headers = get_token_headers(fx["apex_manager"])

        # Manager creates plan
        res_create = client.post(
            "/api/v1/remediations",
            json={
                "plan_code": "CAPA-ADV-11",
                "title": "Self Approval Plan",
                "problem_statement": "Statement description",
                "root_cause_classification": "CONTROL_DEFICIENCY",
                "source_type": "FINDING",
                "finding_id": fx["finding_apex"].id,
            },
            headers=manager_headers,
        )
        plan_id = res_create.json()["id"]

        # Add task
        client.post(
            f"/api/v1/remediations/{plan_id}/tasks",
            json={"task_seq": 1, "title": "Task", "description": "Valid task description"},
            headers=manager_headers,
        )

        # Manager tries to approve own plan
        res_approve = client.post(
            f"/api/v1/remediations/{plan_id}/approve",
            json={},
            headers=manager_headers,
        )
        assert res_approve.status_code == 403
        assert "separation of duties" in res_approve.json()["detail"].lower()

    # ── ADV-P11-12: Plan Owner Self-Verification ─────────────────────────────
    def test_adv_p11_12_plan_owner_self_verification(
        self, client: TestClient, db: Session, adv_p11_fixture
    ):
        """ADV-P11-12: Plan owner cannot verify and close their own plan (HTTP 403)."""
        fx = adv_p11_fixture
        manager_headers = get_token_headers(fx["apex_manager"])
        auditor_headers = get_token_headers(fx["apex_auditor"])

        # Manager creates plan
        res_create = client.post(
            "/api/v1/remediations",
            json={
                "plan_code": "CAPA-ADV-12",
                "title": "Self Verification Plan",
                "problem_statement": "Statement description",
                "root_cause_classification": "CONTROL_DEFICIENCY",
                "source_type": "FINDING",
                "finding_id": fx["finding_apex"].id,
            },
            headers=manager_headers,
        )
        plan_id = res_create.json()["id"]

        # Add & complete task
        res_t = client.post(
            f"/api/v1/remediations/{plan_id}/tasks",
            json={"task_seq": 1, "title": "Task", "description": "Valid task description", "assignee_id": fx["apex_analyst"].id},
            headers=manager_headers,
        )
        task_id = res_t.json()["id"]

        # Approve using service layer
        plan = db.query(RemediationPlan).filter(RemediationPlan.id == plan_id).first()
        plan.status = RemediationStatusEnum.APPROVED
        plan.approved_by_id = fx["apex_auditor"].id
        plan.approved_at = datetime.now(timezone.utc)
        plan.target_completion_at = datetime.now(timezone.utc) + timedelta(days=30)
        db.commit()

        client.post(f"/api/v1/remediations/{plan_id}/start", headers=manager_headers)
        client.post(
            f"/api/v1/remediations/tasks/{task_id}/evidence",
            json={"evidence_id": fx["evidence_apex"].id},
            headers=manager_headers,
        )
        client.post(f"/api/v1/remediations/tasks/{task_id}/complete", headers=manager_headers)
        client.post(f"/api/v1/remediations/{plan_id}/submit-validation", headers=manager_headers)

        # Log PASS re-test
        client.post(
            f"/api/v1/remediations/{plan_id}/retests",
            json={
                "test_executed_at": datetime.now(timezone.utc).isoformat(),
                "test_result": "PASS",
                "evidence_id": fx["evidence_apex"].id,
                "validation_narrative": "Empirical re-test passed successfully.",
            },
            headers=auditor_headers,
        )

        # Plan Owner (Manager) attempts to verify-close
        res_close = client.post(
            f"/api/v1/remediations/{plan_id}/verify-close",
            json={"verification_notes": "Manager self-closing own plan."},
            headers=manager_headers,
        )
        assert res_close.status_code == 403
        assert "separation of duties" in res_close.json()["detail"].lower()

    # ── ADV-P11-13: Task Assignee Final Verification ─────────────────────────
    def test_adv_p11_13_task_assignee_final_verification(
        self, client: TestClient, db: Session, adv_p11_fixture
    ):
        """ADV-P11-13: Task assignee cannot execute final verification (HTTP 403)."""
        fx = adv_p11_fixture
        manager_headers = get_token_headers(fx["apex_manager"])
        analyst_headers = get_token_headers(fx["apex_analyst"])

        # Analyst creates plan
        res_create = client.post(
            "/api/v1/remediations",
            json={
                "plan_code": "CAPA-ADV-13",
                "title": "Assignee Conflict Plan",
                "problem_statement": "Statement description",
                "root_cause_classification": "CONTROL_DEFICIENCY",
                "source_type": "FINDING",
                "finding_id": fx["finding_apex"].id,
            },
            headers=analyst_headers,
        )
        plan_id = res_create.json()["id"]

        # Add task assigned to Manager
        res_t = client.post(
            f"/api/v1/remediations/{plan_id}/tasks",
            json={"task_seq": 1, "title": "Task", "description": "Valid task description", "assignee_id": fx["apex_manager"].id},
            headers=analyst_headers,
        )
        task_id = res_t.json()["id"]

        plan = db.query(RemediationPlan).filter(RemediationPlan.id == plan_id).first()
        plan.status = RemediationStatusEnum.APPROVED
        plan.approved_by_id = fx["apex_auditor"].id
        plan.approved_at = datetime.now(timezone.utc)
        plan.target_completion_at = datetime.now(timezone.utc) + timedelta(days=30)
        db.commit()

        client.post(f"/api/v1/remediations/{plan_id}/start", headers=manager_headers)
        client.post(
            f"/api/v1/remediations/tasks/{task_id}/evidence",
            json={"evidence_id": fx["evidence_apex"].id},
            headers=manager_headers,
        )
        client.post(f"/api/v1/remediations/tasks/{task_id}/complete", headers=manager_headers)
        client.post(f"/api/v1/remediations/{plan_id}/submit-validation", headers=manager_headers)

        # Log PASS re-test
        client.post(
            f"/api/v1/remediations/{plan_id}/retests",
            json={
                "test_executed_at": datetime.now(timezone.utc).isoformat(),
                "test_result": "PASS",
                "evidence_id": fx["evidence_apex"].id,
                "validation_narrative": "Empirical re-test passed successfully.",
            },
            headers=manager_headers,
        )

        # Task implementer (Manager) attempts to verify-close
        res_close = client.post(
            f"/api/v1/remediations/{plan_id}/verify-close",
            json={"verification_notes": "Implementer verifying own work."},
            headers=manager_headers,
        )
        assert res_close.status_code == 403
        assert "task implementers cannot verify" in res_close.json()["detail"].lower()

    # ── ADV-P11-14: Past Target Completion Date Injection ────────────────────
    def test_adv_p11_14_past_target_completion_at_injection(
        self, client: TestClient, db: Session, adv_p11_fixture
    ):
        """ADV-P11-14: Attempting to approve with past target completion date fails with 422."""
        fx = adv_p11_fixture
        analyst_headers = get_token_headers(fx["apex_analyst"])
        manager_headers = get_token_headers(fx["apex_manager"])

        res_create = client.post(
            "/api/v1/remediations",
            json={
                "plan_code": "CAPA-ADV-14",
                "title": "Past Target Plan",
                "problem_statement": "Statement description",
                "root_cause_classification": "CONTROL_DEFICIENCY",
                "source_type": "FINDING",
                "finding_id": fx["finding_apex"].id,
            },
            headers=analyst_headers,
        )
        plan_id = res_create.json()["id"]

        client.post(
            f"/api/v1/remediations/{plan_id}/tasks",
            json={"task_seq": 1, "title": "Task", "description": "Valid task description"},
            headers=analyst_headers,
        )

        past_iso = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        res_app = client.post(
            f"/api/v1/remediations/{plan_id}/approve",
            json={"target_completion_at": past_iso},
            headers=manager_headers,
        )
        assert res_app.status_code == 422

    # ── ADV-P11-15: SLA Status Injection ─────────────────────────────────────
    def test_adv_p11_15_sla_status_injection(
        self, client: TestClient, db: Session, adv_p11_fixture
    ):
        """ADV-P11-15: Client-supplied sla_status in create/patch is ignored/computed."""
        fx = adv_p11_fixture
        analyst_headers = get_token_headers(fx["apex_analyst"])

        res = client.post(
            "/api/v1/remediations",
            json={
                "sla_status": "COMPLETED_ON_TIME",  # Malicious injection
                "plan_code": "CAPA-ADV-15",
                "title": "SLA Spoof Plan",
                "problem_statement": "Statement description",
                "root_cause_classification": "CONTROL_DEFICIENCY",
                "source_type": "FINDING",
                "finding_id": fx["finding_apex"].id,
            },
            headers=analyst_headers,
        )
        assert res.status_code == 201
        # In DRAFT status, SLA status must be NOT_STARTED
        assert res.json()["sla_status"] == "NOT_STARTED"

    # ── ADV-P11-16: REI Score Injection ──────────────────────────────────────
    def test_adv_p11_16_rei_score_injection(
        self, client: TestClient, db: Session, adv_p11_fixture
    ):
        """ADV-P11-16: Client-supplied rei_score in payload is ignored."""
        fx = adv_p11_fixture
        analyst_headers = get_token_headers(fx["apex_analyst"])

        res = client.post(
            "/api/v1/remediations",
            json={
                "rei_score": 100.0,  # Malicious injection
                "plan_code": "CAPA-ADV-16",
                "title": "REI Spoof Plan",
                "problem_statement": "Statement description",
                "root_cause_classification": "CONTROL_DEFICIENCY",
                "source_type": "FINDING",
                "finding_id": fx["finding_apex"].id,
            },
            headers=analyst_headers,
        )
        assert res.status_code == 201
        assert res.json()["rei_score"] is None

    # ── ADV-P11-17: TTR Hours Injection ──────────────────────────────────────
    def test_adv_p11_17_ttr_hours_injection(
        self, client: TestClient, db: Session, adv_p11_fixture
    ):
        """ADV-P11-17: Client-supplied ttr_hours is ignored."""
        fx = adv_p11_fixture
        analyst_headers = get_token_headers(fx["apex_analyst"])

        res = client.post(
            "/api/v1/remediations",
            json={
                "ttr_hours": 0.5,  # Malicious injection
                "plan_code": "CAPA-ADV-17",
                "title": "TTR Spoof Plan",
                "problem_statement": "Statement description",
                "root_cause_classification": "CONTROL_DEFICIENCY",
                "source_type": "FINDING",
                "finding_id": fx["finding_apex"].id,
            },
            headers=analyst_headers,
        )
        assert res.status_code == 201
        assert res.json()["ttr_hours"] is None

    # ── ADV-P11-18: Illegal State Jump ───────────────────────────────────────
    def test_adv_p11_18_illegal_state_jump(
        self, client: TestClient, db: Session, adv_p11_fixture
    ):
        """ADV-P11-18: Attempting to jump directly from DRAFT to VERIFIED_CLOSED fails with 400."""
        fx = adv_p11_fixture
        analyst_headers = get_token_headers(fx["apex_analyst"])
        auditor_headers = get_token_headers(fx["apex_auditor"])

        res_create = client.post(
            "/api/v1/remediations",
            json={
                "plan_code": "CAPA-ADV-18",
                "title": "Illegal Jump Plan",
                "problem_statement": "Statement description",
                "root_cause_classification": "CONTROL_DEFICIENCY",
                "source_type": "FINDING",
                "finding_id": fx["finding_apex"].id,
            },
            headers=analyst_headers,
        )
        plan_id = res_create.json()["id"]

        res_jump = client.post(
            f"/api/v1/remediations/{plan_id}/verify-close",
            json={"verification_notes": "Attempting illegal direct closure."},
            headers=auditor_headers,
        )
        assert res_jump.status_code == 400
        assert "illegal lifecycle transition" in res_jump.json()["detail"].lower()

    # ── ADV-P11-19: Mutation of VERIFIED_CLOSED Plan ─────────────────────────
    def test_adv_p11_19_verified_closed_mutation(
        self, client: TestClient, db: Session, adv_p11_fixture
    ):
        """ADV-P11-19: Closed plans are permanently immutable (HTTP 409)."""
        fx = adv_p11_fixture
        analyst_headers = get_token_headers(fx["apex_analyst"])
        manager_headers = get_token_headers(fx["apex_manager"])
        auditor_headers = get_token_headers(fx["apex_auditor"])

        res_create = client.post(
            "/api/v1/remediations",
            json={
                "plan_code": "CAPA-ADV-19",
                "title": "Immutable Plan",
                "problem_statement": "Statement description",
                "root_cause_classification": "CONTROL_DEFICIENCY",
                "source_type": "FINDING",
                "finding_id": fx["finding_apex"].id,
            },
            headers=analyst_headers,
        )
        plan_id = res_create.json()["id"]

        res_t = client.post(
            f"/api/v1/remediations/{plan_id}/tasks",
            json={"task_seq": 1, "title": "Task", "description": "Valid task description", "assignee_id": fx["apex_analyst"].id},
            headers=analyst_headers,
        )
        task_id = res_t.json()["id"]

        client.post(f"/api/v1/remediations/{plan_id}/approve", json={}, headers=manager_headers)
        client.post(f"/api/v1/remediations/{plan_id}/start", headers=analyst_headers)
        client.post(
            f"/api/v1/remediations/tasks/{task_id}/evidence",
            json={"evidence_id": fx["evidence_apex"].id},
            headers=analyst_headers,
        )
        client.post(f"/api/v1/remediations/tasks/{task_id}/complete", headers=analyst_headers)
        client.post(f"/api/v1/remediations/{plan_id}/submit-validation", headers=analyst_headers)

        client.post(
            f"/api/v1/remediations/{plan_id}/retests",
            json={
                "test_executed_at": datetime.now(timezone.utc).isoformat(),
                "test_result": "PASS",
                "evidence_id": fx["evidence_apex"].id,
                "validation_narrative": "Empirical re-test passed.",
            },
            headers=auditor_headers,
        )

        # Verify close
        client.post(
            f"/api/v1/remediations/{plan_id}/verify-close",
            json={"verification_notes": "Auditor full verification complete."},
            headers=auditor_headers,
        )

        # Mutation attempts return HTTP 409
        res_mut = client.patch(
            f"/api/v1/remediations/{plan_id}",
            json={"title": "Tampered Title"},
            headers=analyst_headers,
        )
        assert res_mut.status_code == 409

    # ── ADV-P11-20: Premature Closure with Incomplete Tasks ──────────────────
    def test_adv_p11_20_premature_closure_incomplete_tasks(
        self, client: TestClient, db: Session, adv_p11_fixture
    ):
        """ADV-P11-20: Cannot submit for validation or close while tasks remain incomplete."""
        fx = adv_p11_fixture
        analyst_headers = get_token_headers(fx["apex_analyst"])
        manager_headers = get_token_headers(fx["apex_manager"])

        res_create = client.post(
            "/api/v1/remediations",
            json={
                "plan_code": "CAPA-ADV-20",
                "title": "Incomplete Tasks Plan",
                "problem_statement": "Statement description",
                "root_cause_classification": "CONTROL_DEFICIENCY",
                "source_type": "FINDING",
                "finding_id": fx["finding_apex"].id,
            },
            headers=analyst_headers,
        )
        plan_id = res_create.json()["id"]

        client.post(
            f"/api/v1/remediations/{plan_id}/tasks",
            json={"task_seq": 1, "title": "Task 1", "description": "Valid task description"},
            headers=analyst_headers,
        )
        client.post(f"/api/v1/remediations/{plan_id}/approve", json={}, headers=manager_headers)
        client.post(f"/api/v1/remediations/{plan_id}/start", headers=analyst_headers)

        # Submit validation while task 1 is still PENDING -> HTTP 400
        res_sub = client.post(
            f"/api/v1/remediations/{plan_id}/submit-validation", headers=analyst_headers
        )
        assert res_sub.status_code == 400
        assert "not completed" in res_sub.json()["detail"].lower()

    # ── BONUS: Source-Type Contradiction Defense ─────────────────────────────
    def test_adv_p11_source_type_contradiction(
        self, client: TestClient, db: Session, adv_p11_fixture
    ):
        """Rejects contradictory source_type vs populated foreign key."""
        fx = adv_p11_fixture
        apex_headers = get_token_headers(fx["apex_analyst"])

        res = client.post(
            "/api/v1/remediations",
            json={
                "plan_code": "CAPA-CONTRADICTION",
                "title": "Contradiction Plan",
                "problem_statement": "Statement description",
                "root_cause_classification": "CONTROL_DEFICIENCY",
                "source_type": "SECURITY_INCIDENT",  # Contradicts finding_id
                "finding_id": fx["finding_apex"].id,
            },
            headers=apex_headers,
        )
        assert res.status_code == 422

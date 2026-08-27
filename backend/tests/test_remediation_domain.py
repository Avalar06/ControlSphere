from datetime import datetime, timedelta, timezone
import pytest
from fastapi import HTTPException

from app.core.permissions import Permission, RoleEnum, has_permission
from app.models.control import OrganizationControl, ImplementationStatusEnum, PriorityEnum
from app.models.evidence import (
    EvidenceItem,
    EvidenceRequirement,
    EvidenceStatusEnum,
    EvidenceTypeEnum,
)
from app.models.finding import (
    Finding,
    FindingSeverityEnum,
    FindingStatusEnum,
    FindingTypeEnum,
)
from app.models.framework import (
    Framework,
    FrameworkCategory,
    FrameworkFunction,
    FrameworkSubcategory,
)
from app.models.incident import (
    IncidentCategoryEnum,
    IncidentSeverityEnum,
    SecurityIncident,
)
from app.models.monitoring import (
    ComplianceDriftAlert,
    DriftAlertSeverityEnum,
    DriftAlertStatusEnum,
    DriftAlertTypeEnum,
)
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
from app.services.remediation_service import RemediationService


@pytest.fixture
def remediation_fixture(db):
    org = Organization(name="ROC-V Defense Corp", slug="rocv-defense")
    db.add(org)
    db.commit()
    db.refresh(org)

    owner = User(
        email="owner@rocv.internal",
        hashed_password="hash",
        full_name="Plan Owner",
        organization_id=org.id,
        role=RoleEnum.GRC_ANALYST,
        is_active=True,
    )
    approver = User(
        email="manager@rocv.internal",
        hashed_password="hash",
        full_name="Governance Manager",
        organization_id=org.id,
        role=RoleEnum.MANAGER,
        is_active=True,
    )
    assignee = User(
        email="engineer@rocv.internal",
        hashed_password="hash",
        full_name="Remediation Engineer",
        organization_id=org.id,
        role=RoleEnum.SECURITY_ANALYST,
        is_active=True,
    )
    verifier = User(
        email="auditor@rocv.internal",
        hashed_password="hash",
        full_name="Independent Auditor",
        organization_id=org.id,
        role=RoleEnum.AUDITOR,
        is_active=True,
    )
    db.add_all([owner, approver, assignee, verifier])
    db.commit()
    db.refresh(owner)
    db.refresh(approver)
    db.refresh(assignee)
    db.refresh(verifier)

    # Framework structure for OrganizationControl
    fw = Framework(name="NIST CSF Test", identifier="NIST-TEST", version="2.0")
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
        category_id=cat.id,
        identifier="PR.DS-01",
        title="Data Protection",
        description="Data-at-rest is protected",
    )
    db.add(subcat)
    db.commit()
    db.refresh(subcat)

    ctrl = OrganizationControl(
        organization_id=org.id,
        subcategory_id=subcat.id,
        status=ImplementationStatusEnum.IN_PROGRESS,
        priority=PriorityEnum.HIGH,
    )
    db.add(ctrl)
    db.commit()
    db.refresh(ctrl)

    # Finding source
    finding = Finding(
        organization_id=org.id,
        organization_control_id=ctrl.id,
        title="Unencrypted S3 Bucket",
        description="Publicly accessible bucket storing logs",
        finding_type=FindingTypeEnum.CONTROL_GAP,
        severity=FindingSeverityEnum.HIGH,
        recommendation="Enable default KMS encryption and block public access",
        status=FindingStatusEnum.OPEN,
        created_at=datetime.now(timezone.utc) - timedelta(days=10),
    )
    db.add(finding)
    db.commit()
    db.refresh(finding)

    # Accepted Evidence Item
    req = EvidenceRequirement(
        organization_id=org.id,
        organization_control_id=ctrl.id,
        title="Encryption Config Evidence",
        description="Evidence of TLS/AES encryption",
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    evidence = EvidenceItem(
        organization_id=org.id,
        organization_control_id=ctrl.id,
        evidence_requirement_id=req.id,
        title="S3 Bucket KMS Policy Screenshot",
        original_filename="s3_kms.png",
        stored_filename="stored_s3_kms.png",
        file_extension="png",
        content_type="image/png",
        file_size=1024,
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        storage_key="evidence/s3_kms.png",
        status=EvidenceStatusEnum.ACCEPTED,
        uploaded_by_id=assignee.id,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)

    # Incident source
    incident = SecurityIncident(
        organization_id=org.id,
        incident_code="INC-2026-001",
        title="Ransomware Outbreak",
        description="Encrypted file shares detected",
        severity=IncidentSeverityEnum.CRITICAL,
        category=IncidentCategoryEnum.RANSOMWARE,
        incident_commander_id=owner.id,
        detected_at=datetime.now(timezone.utc) - timedelta(days=5),
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)

    return {
        "org": org,
        "owner": owner,
        "approver": approver,
        "assignee": assignee,
        "verifier": verifier,
        "ctrl": ctrl,
        "finding": finding,
        "evidence": evidence,
        "incident": incident,
    }


# ─── 1. ENUM AND RBAC PERMISSION VERIFICATION ────────────────────────────────

def test_remediation_permissions_matrix():
    assert has_permission(RoleEnum.ADMIN, Permission.REMEDIATION_READ)
    assert has_permission(RoleEnum.ADMIN, Permission.REMEDIATION_APPROVE)
    assert has_permission(RoleEnum.ADMIN, Permission.REMEDIATION_VERIFY)

    assert has_permission(RoleEnum.MANAGER, Permission.REMEDIATION_APPROVE)
    assert has_permission(RoleEnum.MANAGER, Permission.REMEDIATION_VERIFY)

    assert has_permission(RoleEnum.GRC_ANALYST, Permission.REMEDIATION_MANAGE)
    assert has_permission(RoleEnum.GRC_ANALYST, Permission.REMEDIATION_EXECUTE)
    assert not has_permission(RoleEnum.GRC_ANALYST, Permission.REMEDIATION_APPROVE)
    assert not has_permission(RoleEnum.GRC_ANALYST, Permission.REMEDIATION_VERIFY)

    assert has_permission(RoleEnum.AUDITOR, Permission.REMEDIATION_READ)
    assert has_permission(RoleEnum.AUDITOR, Permission.REMEDIATION_VERIFY)
    assert not has_permission(RoleEnum.AUDITOR, Permission.REMEDIATION_APPROVE)
    assert not has_permission(RoleEnum.AUDITOR, Permission.REMEDIATION_MANAGE)

    assert has_permission(RoleEnum.VIEWER, Permission.REMEDIATION_READ)
    assert not has_permission(RoleEnum.VIEWER, Permission.REMEDIATION_MANAGE)


# ─── 2. PLAN CREATION AND SOURCE LINKAGE ─────────────────────────────────────

def test_plan_creation_defaults(db, remediation_fixture):
    fx = remediation_fixture
    plan = RemediationService.create_plan(
        db=db,
        organization_id=fx["org"].id,
        plan_owner_id=fx["owner"].id,
        plan_code="CAPA-2026-0001",
        title="Remediate S3 Public Access",
        problem_statement="Storage bucket lacks bucket policy enforcement",
        root_cause_classification=RemediationRootCauseClassificationEnum.CONFIGURATION_DRIFT,
        source_type=RemediationSourceTypeEnum.FINDING,
        severity=RemediationSeverityEnum.HIGH,
        finding_id=fx["finding"].id,
    )
    assert plan.id is not None
    assert plan.status == RemediationStatusEnum.DRAFT
    assert plan.validation_attempts_count == 0
    assert not plan.is_immutable
    assert plan.finding_id == fx["finding"].id


def test_plan_creation_duplicate_code_fails(db, remediation_fixture):
    fx = remediation_fixture
    RemediationService.create_plan(
        db=db,
        organization_id=fx["org"].id,
        plan_owner_id=fx["owner"].id,
        plan_code="CAPA-DUPLICATE",
        title="Plan A",
        problem_statement="Problem A",
        root_cause_classification=RemediationRootCauseClassificationEnum.CONTROL_DEFICIENCY,
        source_type=RemediationSourceTypeEnum.FINDING,
        severity=RemediationSeverityEnum.MEDIUM,
        finding_id=fx["finding"].id,
    )
    with pytest.raises(HTTPException) as exc:
        RemediationService.create_plan(
            db=db,
            organization_id=fx["org"].id,
            plan_owner_id=fx["owner"].id,
            plan_code="CAPA-DUPLICATE",
            title="Plan B",
            problem_statement="Problem B",
            root_cause_classification=RemediationRootCauseClassificationEnum.CONTROL_DEFICIENCY,
            source_type=RemediationSourceTypeEnum.FINDING,
            severity=RemediationSeverityEnum.MEDIUM,
            finding_id=fx["finding"].id,
        )
    assert exc.value.status_code == 409


def test_cross_tenant_source_linking_rejected(db, remediation_fixture):
    fx = remediation_fixture
    foreign_org = Organization(name="Foreign Corp", slug="foreign-corp")
    db.add(foreign_org)
    db.commit()

    foreign_ctrl = OrganizationControl(
        organization_id=foreign_org.id,
        subcategory_id=fx["ctrl"].subcategory_id,
        status=ImplementationStatusEnum.NOT_STARTED,
    )
    db.add(foreign_ctrl)
    db.commit()

    foreign_finding = Finding(
        organization_id=foreign_org.id,
        organization_control_id=foreign_ctrl.id,
        title="Foreign Defect",
        description="Foreign",
        finding_type=FindingTypeEnum.CONTROL_GAP,
        severity=FindingSeverityEnum.LOW,
        recommendation="Fix foreign defect",
        status=FindingStatusEnum.OPEN,
    )
    db.add(foreign_finding)
    db.commit()

    with pytest.raises(HTTPException) as exc:
        RemediationService.create_plan(
            db=db,
            organization_id=fx["org"].id,
            plan_owner_id=fx["owner"].id,
            plan_code="CAPA-CROSS-TENANT",
            title="Invalid Link",
            problem_statement="Foreign attempt",
            root_cause_classification=RemediationRootCauseClassificationEnum.HUMAN_ERROR,
            source_type=RemediationSourceTypeEnum.FINDING,
            severity=RemediationSeverityEnum.LOW,
            finding_id=foreign_finding.id,
        )
    assert exc.value.status_code == 404


# ─── 3. LIFECYCLE TRANSITIONS AND FOUR-EYES GOVERNANCE ────────────────────────

def test_full_governed_lifecycle_flow(db, remediation_fixture):
    fx = remediation_fixture
    plan = RemediationService.create_plan(
        db=db,
        organization_id=fx["org"].id,
        plan_owner_id=fx["owner"].id,
        plan_code="CAPA-LIFECYCLE-01",
        title="Enable GuardDuty",
        problem_statement="Threat detection is missing",
        root_cause_classification=RemediationRootCauseClassificationEnum.CONTROL_DEFICIENCY,
        source_type=RemediationSourceTypeEnum.FINDING,
        severity=RemediationSeverityEnum.CRITICAL,
        finding_id=fx["finding"].id,
    )

    # 1. Approval fails without task
    with pytest.raises(HTTPException) as exc:
        RemediationService.approve_plan(db=db, plan=plan, approver_id=fx["approver"].id)
    assert exc.value.status_code == 400

    # Add task
    task = RemediationService.add_task(
        db=db,
        plan=plan,
        actor_id=fx["owner"].id,
        task_seq=1,
        title="Deploy GuardDuty Terraform",
        description="Enable multi-account GuardDuty via IaC",
        assignee_id=fx["assignee"].id,
        due_date=datetime.now(timezone.utc) + timedelta(days=3),
    )

    # 2. Approval fails if Plan Owner attempts self-approval (Four-Eyes Violation)
    with pytest.raises(HTTPException) as exc:
        RemediationService.approve_plan(db=db, plan=plan, approver_id=fx["owner"].id)
    assert exc.value.status_code == 403

    # 3. Manager approves
    plan = RemediationService.approve_plan(db=db, plan=plan, approver_id=fx["approver"].id)
    assert plan.status == RemediationStatusEnum.APPROVED
    assert plan.approved_at is not None
    assert plan.target_completion_at is not None

    # 4. Start execution
    plan = RemediationService.start_execution(db=db, plan=plan, actor_id=fx["assignee"].id)
    assert plan.status == RemediationStatusEnum.IN_EXECUTION

    # 5. Validation submission fails if task is not completed or missing evidence
    with pytest.raises(HTTPException) as exc:
        RemediationService.submit_for_validation(db=db, plan=plan, actor_id=fx["assignee"].id)
    assert exc.value.status_code == 400

    # Link evidence and complete task
    RemediationService.link_evidence_to_task(
        db=db, task=task, actor_id=fx["assignee"].id, evidence_id=fx["evidence"].id
    )
    RemediationService.update_task(
        db=db, task=task, actor_id=fx["assignee"].id, status=TaskStatusEnum.COMPLETED
    )

    # 6. Submit for validation
    plan = RemediationService.submit_for_validation(db=db, plan=plan, actor_id=fx["assignee"].id)
    assert plan.status == RemediationStatusEnum.PENDING_VALIDATION
    assert plan.validation_attempts_count == 1

    # 7. Final closure fails without PASS re-test
    with pytest.raises(HTTPException) as exc:
        RemediationService.verify_and_close_plan(
            db=db,
            plan=plan,
            verifier_id=fx["verifier"].id,
            verification_notes="Tested and approved in prod environment.",
        )
    assert exc.value.status_code == 400

    # 8. Record PASS re-test
    retest = RemediationService.record_retest(
        db=db,
        plan=plan,
        tester_id=fx["verifier"].id,
        test_executed_at=datetime.now(timezone.utc),
        test_result=ReTestResultEnum.PASS,
        evidence_id=fx["evidence"].id,
        validation_narrative="Verified GuardDuty detectors active across all accounts.",
    )
    assert retest.id is not None

    # 9. Verification fails if Plan Owner attempts to close
    with pytest.raises(HTTPException) as exc:
        RemediationService.verify_and_close_plan(
            db=db,
            plan=plan,
            verifier_id=fx["owner"].id,
            verification_notes="Self-verification attempt notes.",
        )
    assert exc.value.status_code == 403

    # 10. Verification fails if Task Assignee attempts to close
    with pytest.raises(HTTPException) as exc:
        RemediationService.verify_and_close_plan(
            db=db,
            plan=plan,
            verifier_id=fx["assignee"].id,
            verification_notes="Implementer verification attempt.",
        )
    assert exc.value.status_code == 403

    # 11. Independent auditor verifies and closes
    plan = RemediationService.verify_and_close_plan(
        db=db,
        plan=plan,
        verifier_id=fx["verifier"].id,
        verification_notes="Full independent verification completed and validated.",
    )
    assert plan.status == RemediationStatusEnum.VERIFIED_CLOSED
    assert plan.is_immutable
    assert plan.rei_score is not None
    assert plan.ttr_hours is not None

    # 12. Post-closure mutation is permanently blocked (HTTP 409)
    with pytest.raises(HTTPException) as exc:
        RemediationService.update_plan(db=db, plan=plan, actor_id=fx["owner"].id, title="Tamper")
    assert exc.value.status_code == 409


def test_retest_failure_reverts_to_in_execution(db, remediation_fixture):
    fx = remediation_fixture
    plan = RemediationService.create_plan(
        db=db,
        organization_id=fx["org"].id,
        plan_owner_id=fx["owner"].id,
        plan_code="CAPA-RETEST-FAIL",
        title="Fix Vulnerability",
        problem_statement="CVE in container image",
        root_cause_classification=RemediationRootCauseClassificationEnum.CONTROL_DEFICIENCY,
        source_type=RemediationSourceTypeEnum.FINDING,
        severity=RemediationSeverityEnum.HIGH,
        finding_id=fx["finding"].id,
    )
    task = RemediationService.add_task(
        db=db,
        plan=plan,
        actor_id=fx["owner"].id,
        task_seq=1,
        title="Patch Dockerfile",
        description="Bump base image",
        assignee_id=fx["assignee"].id,
    )
    RemediationService.approve_plan(db=db, plan=plan, approver_id=fx["approver"].id)
    RemediationService.start_execution(db=db, plan=plan, actor_id=fx["assignee"].id)
    RemediationService.link_evidence_to_task(
        db=db, task=task, actor_id=fx["assignee"].id, evidence_id=fx["evidence"].id
    )
    RemediationService.update_task(
        db=db, task=task, actor_id=fx["assignee"].id, status=TaskStatusEnum.COMPLETED
    )
    RemediationService.submit_for_validation(db=db, plan=plan, actor_id=fx["assignee"].id)
    assert plan.status == RemediationStatusEnum.PENDING_VALIDATION

    # Log FAIL re-test -> auto-reverts to IN_EXECUTION
    RemediationService.record_retest(
        db=db,
        plan=plan,
        tester_id=fx["verifier"].id,
        test_executed_at=datetime.now(timezone.utc),
        test_result=ReTestResultEnum.FAIL,
        validation_narrative="Vulnerability still detected on scanning image.",
    )
    assert plan.status == RemediationStatusEnum.IN_EXECUTION


def test_cancellation_rules_and_immutability(db, remediation_fixture):
    fx = remediation_fixture
    plan = RemediationService.create_plan(
        db=db,
        organization_id=fx["org"].id,
        plan_owner_id=fx["owner"].id,
        plan_code="CAPA-CANCEL-01",
        title="Cancel Plan",
        problem_statement="Test",
        root_cause_classification=RemediationRootCauseClassificationEnum.ARCHITECTURAL_GAP,
        source_type=RemediationSourceTypeEnum.FINDING,
        severity=RemediationSeverityEnum.LOW,
        finding_id=fx["finding"].id,
    )
    # Cancel from DRAFT
    cancelled = RemediationService.cancel_plan(
        db=db,
        plan=plan,
        actor_id=fx["approver"].id,
        cancellation_notes="Superseded by cloud migration strategy.",
    )
    assert cancelled.status == RemediationStatusEnum.CANCELLED
    assert cancelled.is_immutable

    # Attempting to mutate cancelled plan returns HTTP 409
    with pytest.raises(HTTPException) as exc:
        RemediationService.update_plan(
            db=db, plan=cancelled, actor_id=fx["owner"].id, title="New Title"
        )
    assert exc.value.status_code == 409


# ─── 4. MATHEMATICAL ENGINES (SLA, REI, TTR) ─────────────────────────────────

def test_sla_calculation_engine(db, remediation_fixture):
    fx = remediation_fixture
    now = datetime.now(timezone.utc)
    plan = RemediationPlan(
        organization_id=fx["org"].id,
        plan_code="CAPA-SLA-TEST",
        title="SLA Test",
        problem_statement="Test",
        root_cause_classification=RemediationRootCauseClassificationEnum.HUMAN_ERROR,
        source_type=RemediationSourceTypeEnum.FINDING,
        finding_id=fx["finding"].id,
        severity=RemediationSeverityEnum.CRITICAL,  # 7 days
        status=RemediationStatusEnum.IN_EXECUTION,
        plan_owner_id=fx["owner"].id,
        approved_at=now - timedelta(days=2),
        target_completion_at=now + timedelta(days=5),
    )

    # 1. On Track (5 days remaining out of 7)
    sla_status, remaining = RemediationService.calculate_sla_status(plan, now_utc=now)
    assert sla_status == SlaStatusEnum.ON_TRACK
    assert remaining > 100

    # 2. At Risk (1 day remaining out of 7 = 14.3% <= 20%)
    sla_status, remaining = RemediationService.calculate_sla_status(
        plan, now_utc=now + timedelta(days=4)
    )
    assert sla_status == SlaStatusEnum.AT_RISK

    # 3. Breached (6 days past approved + 5 days target = overdue)
    sla_status, remaining = RemediationService.calculate_sla_status(
        plan, now_utc=now + timedelta(days=6)
    )
    assert sla_status == SlaStatusEnum.BREACHED
    assert remaining < 0

    # 4. Completed on time vs late
    plan.status = RemediationStatusEnum.VERIFIED_CLOSED
    plan.verified_at = now + timedelta(days=3)
    sla_status, _ = RemediationService.calculate_sla_status(plan, now_utc=now)
    assert sla_status == SlaStatusEnum.COMPLETED_ON_TIME

    plan.verified_at = now + timedelta(days=6)
    sla_status, _ = RemediationService.calculate_sla_status(plan, now_utc=now)
    assert sla_status == SlaStatusEnum.COMPLETED_LATE


def test_rei_calculation_engine(db, remediation_fixture):
    fx = remediation_fixture
    now = datetime.now(timezone.utc)
    plan = RemediationPlan(
        organization_id=fx["org"].id,
        plan_code="CAPA-REI-TEST",
        title="REI Test",
        problem_statement="Test",
        root_cause_classification=RemediationRootCauseClassificationEnum.CONTROL_DEFICIENCY,
        source_type=RemediationSourceTypeEnum.FINDING,
        finding_id=fx["finding"].id,
        severity=RemediationSeverityEnum.MEDIUM,
        status=RemediationStatusEnum.IN_EXECUTION,
        plan_owner_id=fx["owner"].id,
        validation_attempts_count=1,
    )
    db.add(plan)
    db.commit()

    # Case A: Zero tasks -> REI = 100.0
    assert RemediationService.calculate_rei(plan) == 100.0

    # Case B: 2 tasks completed on time, 0 failed tests -> REI = 100.0
    t1 = RemediationTask(
        organization_id=fx["org"].id,
        remediation_plan_id=plan.id,
        task_seq=1,
        title="Task 1",
        description="Desc",
        status=TaskStatusEnum.COMPLETED,
        due_date=now + timedelta(days=1),
        completed_at=now,
    )
    t2 = RemediationTask(
        organization_id=fx["org"].id,
        remediation_plan_id=plan.id,
        task_seq=2,
        title="Task 2",
        description="Desc",
        status=TaskStatusEnum.COMPLETED,
        due_date=now + timedelta(days=2),
        completed_at=now,
    )
    db.add_all([t1, t2])
    db.commit()
    db.refresh(plan)
    assert RemediationService.calculate_rei(plan) == 100.0

    # Case C: 1 overdue task out of 2 (Penalty = 0.5 * 35 = 17.5) -> REI = 82.5
    t1.completed_at = now + timedelta(days=5)  # completed late
    db.commit()
    assert RemediationService.calculate_rei(plan) == 82.5

    # Case D: Failed re-tests + churn (2 failed retests = 40 penalty, attempt count 3 = 25 penalty)
    r1 = RemediationReTestRecord(
        organization_id=fx["org"].id,
        remediation_plan_id=plan.id,
        test_executed_at=now,
        tester_id=fx["verifier"].id,
        test_result=ReTestResultEnum.FAIL,
        validation_narrative="Failed test 1",
    )
    r2 = RemediationReTestRecord(
        organization_id=fx["org"].id,
        remediation_plan_id=plan.id,
        test_executed_at=now,
        tester_id=fx["verifier"].id,
        test_result=ReTestResultEnum.FAIL,
        validation_narrative="Failed test 2",
    )
    db.add_all([r1, r2])
    plan.validation_attempts_count = 3
    db.commit()
    # REI = clamp(100 - 17.5 - 40.0 - 25.0, 0, 100) = 17.5
    assert RemediationService.calculate_rei(plan) == 17.5


def test_ttr_calculation_engine(db, remediation_fixture):
    fx = remediation_fixture
    detected = datetime.now(timezone.utc) - timedelta(hours=48)
    verified = datetime.now(timezone.utc)

    plan = RemediationPlan(
        organization_id=fx["org"].id,
        plan_code="CAPA-TTR",
        title="TTR",
        problem_statement="Test",
        root_cause_classification=RemediationRootCauseClassificationEnum.HUMAN_ERROR,
        source_type=RemediationSourceTypeEnum.FINDING,
        finding_id=fx["finding"].id,
        severity=RemediationSeverityEnum.LOW,
        status=RemediationStatusEnum.VERIFIED_CLOSED,
        plan_owner_id=fx["owner"].id,
        verified_at=verified,
    )
    ttr = RemediationService.calculate_ttr_hours(plan, source_detected_at=detected)
    assert ttr == 48.0

    # Missing detected timestamp returns None
    assert RemediationService.calculate_ttr_hours(plan, source_detected_at=None) is None


def test_incident_source_remediation_plan(db, remediation_fixture):
    fx = remediation_fixture
    plan = RemediationService.create_plan(
        db=db,
        organization_id=fx["org"].id,
        plan_owner_id=fx["owner"].id,
        plan_code="CAPA-INCIDENT-01",
        title="Ransomware Recovery CAPA",
        problem_statement="Eradicate malware persistence and rebuild systems",
        root_cause_classification=RemediationRootCauseClassificationEnum.ARCHITECTURAL_GAP,
        source_type=RemediationSourceTypeEnum.SECURITY_INCIDENT,
        severity=RemediationSeverityEnum.CRITICAL,
        security_incident_id=fx["incident"].id,
    )
    assert plan.security_incident_id == fx["incident"].id
    assert plan.finding_id is None
    source_ts = RemediationService.get_source_detected_timestamp(plan)
    assert source_ts == fx["incident"].detected_at


def test_unaccepted_evidence_link_rejected(db, remediation_fixture):
    fx = remediation_fixture
    plan = RemediationService.create_plan(
        db=db,
        organization_id=fx["org"].id,
        plan_owner_id=fx["owner"].id,
        plan_code="CAPA-EVID-TEST",
        title="Evidence Validation",
        problem_statement="Test",
        root_cause_classification=RemediationRootCauseClassificationEnum.CONTROL_DEFICIENCY,
        source_type=RemediationSourceTypeEnum.FINDING,
        severity=RemediationSeverityEnum.MEDIUM,
        finding_id=fx["finding"].id,
    )
    task = RemediationService.add_task(
        db=db,
        plan=plan,
        actor_id=fx["owner"].id,
        task_seq=1,
        title="Implement Control",
        description="Desc",
    )
    # Pending evidence item
    pending_ev = EvidenceItem(
        organization_id=fx["org"].id,
        organization_control_id=fx["ctrl"].id,
        title="Pending Item",
        original_filename="pending.pdf",
        stored_filename="stored_pending.pdf",
        file_extension="pdf",
        content_type="application/pdf",
        file_size=500,
        sha256_hash="1111111111111111111111111111111111111111111111111111111111111111",
        storage_key="evidence/pending.pdf",
        status=EvidenceStatusEnum.UPLOADED,
    )
    db.add(pending_ev)
    db.commit()

    with pytest.raises(HTTPException) as exc:
        RemediationService.link_evidence_to_task(
            db=db, task=task, actor_id=fx["owner"].id, evidence_id=pending_ev.id
        )
    assert exc.value.status_code == 400


def test_retest_pass_without_evidence_rejected(db, remediation_fixture):
    fx = remediation_fixture
    plan = RemediationService.create_plan(
        db=db,
        organization_id=fx["org"].id,
        plan_owner_id=fx["owner"].id,
        plan_code="CAPA-RETEST-NO-EVID",
        title="ReTest Validation",
        problem_statement="Test",
        root_cause_classification=RemediationRootCauseClassificationEnum.HUMAN_ERROR,
        source_type=RemediationSourceTypeEnum.FINDING,
        severity=RemediationSeverityEnum.LOW,
        finding_id=fx["finding"].id,
    )
    with pytest.raises(HTTPException) as exc:
        RemediationService.record_retest(
            db=db,
            plan=plan,
            tester_id=fx["verifier"].id,
            test_executed_at=datetime.now(timezone.utc),
            test_result=ReTestResultEnum.PASS,
            evidence_id=None,  # Missing evidence
            validation_narrative="Passed validation test narrative.",
        )
    assert exc.value.status_code == 400

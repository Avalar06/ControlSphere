from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.finding import Finding, FindingStatusEnum
from app.models.audit_engagement import Audit
from app.models.evidence import EvidenceItem, EvidenceStatusEnum
from app.models.incident import SecurityIncident
from app.models.monitoring import ComplianceDriftAlert, DriftAlertStatusEnum
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
from app.models.tprm import VendorAssessment
from app.models.user import User
from app.services.audit_service import AuditService


class RemediationService:
    """Authoritative Domain Service for Phase 11 Governed Remediation & Corrective Actions."""

    @staticmethod
    def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
        """Normalizes any datetime to a timezone-aware UTC datetime."""
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    @classmethod
    def _get_actor_email(cls, db: Session, user_id: int) -> str:
        u = db.query(User).filter(User.id == user_id).first()
        return u.email if u else "system@controlsphere.internal"

    # ─── 1. DETERMINISTIC CALCULATION ENGINES ────────────────────────────────

    @classmethod
    def calculate_default_sla_duration_days(cls, severity: RemediationSeverityEnum) -> int:
        """Returns authoritative statutory/risk SLA durations in calendar days."""
        if severity == RemediationSeverityEnum.CRITICAL:
            return 7
        elif severity == RemediationSeverityEnum.HIGH:
            return 30
        elif severity == RemediationSeverityEnum.MEDIUM:
            return 60
        elif severity == RemediationSeverityEnum.LOW:
            return 90
        return 60

    @classmethod
    def calculate_sla_status(
        cls, plan: RemediationPlan, now_utc: Optional[datetime] = None
    ) -> Tuple[SlaStatusEnum, Optional[float]]:
        """
        Deterministically evaluates SLA status and remaining hours.
        Returns: (SlaStatusEnum, remaining_hours)
        """
        now = cls._ensure_utc(now_utc) or datetime.now(timezone.utc)

        if plan.status in (RemediationStatusEnum.DRAFT, RemediationStatusEnum.CANCELLED):
            return SlaStatusEnum.NOT_STARTED, None

        if plan.status == RemediationStatusEnum.VERIFIED_CLOSED:
            if plan.verified_at and plan.target_completion_at:
                v_at = cls._ensure_utc(plan.verified_at)
                t_at = cls._ensure_utc(plan.target_completion_at)
                if v_at <= t_at:
                    return SlaStatusEnum.COMPLETED_ON_TIME, 0.0
                else:
                    return SlaStatusEnum.COMPLETED_LATE, 0.0
            return SlaStatusEnum.COMPLETED_ON_TIME, 0.0

        # In-Progress states (APPROVED, IN_EXECUTION, PENDING_VALIDATION)
        if not plan.target_completion_at:
            return SlaStatusEnum.NOT_STARTED, None

        target = cls._ensure_utc(plan.target_completion_at)
        approved = cls._ensure_utc(plan.approved_at) or cls._ensure_utc(plan.created_at)
        total_window_sec = max((target - approved).total_seconds(), 1.0)
        remaining_sec = (target - now).total_seconds()
        remaining_hours = round(remaining_sec / 3600.0, 2)

        if remaining_sec < 0:
            return SlaStatusEnum.BREACHED, remaining_hours
        elif remaining_sec <= 0.20 * total_window_sec:
            return SlaStatusEnum.AT_RISK, remaining_hours
        else:
            return SlaStatusEnum.ON_TRACK, remaining_hours

    @classmethod
    def calculate_rei(cls, plan: RemediationPlan) -> float:
        """
        Calculates the Remediation Effectiveness Index (REI) on a 0.0 - 100.0 scale.
        REI = clamp(100 - Penalty_overdue - Penalty_retest - Penalty_churn, 0.0, 100.0)
        """
        tasks = [t for t in plan.tasks if t.status != TaskStatusEnum.CANCELLED]
        total_tasks = len(tasks)
        now_utc = datetime.now(timezone.utc)

        overdue_tasks = 0
        for task in tasks:
            if task.due_date:
                t_due = cls._ensure_utc(task.due_date)
                if task.status in (TaskStatusEnum.PENDING, TaskStatusEnum.IN_PROGRESS):
                    if t_due < now_utc:
                        overdue_tasks += 1
                elif task.status == TaskStatusEnum.COMPLETED and task.completed_at:
                    t_comp = cls._ensure_utc(task.completed_at)
                    if t_comp > t_due:
                        overdue_tasks += 1

        penalty_overdue = (overdue_tasks / total_tasks) * 35.0 if total_tasks > 0 else 0.0

        failed_retests = len(
            [r for r in plan.retest_records if r.test_result == ReTestResultEnum.FAIL]
        )
        penalty_retest = min(failed_retests * 20.0, 40.0)

        churn_attempts = max(0, plan.validation_attempts_count - 1)
        penalty_churn = min(churn_attempts * 12.5, 25.0)

        rei = max(0.0, min(100.0, 100.0 - penalty_overdue - penalty_retest - penalty_churn))
        return round(rei, 2)

    @classmethod
    def get_source_detected_timestamp(cls, plan: RemediationPlan) -> Optional[datetime]:
        """Resolves authoritative deficiency detection timestamp from upstream entity."""
        if plan.finding:
            return plan.finding.created_at
        elif plan.compliance_drift_alert:
            return plan.compliance_drift_alert.created_at
        elif plan.security_incident:
            return plan.security_incident.detected_at
        elif plan.vendor_assessment:
            return plan.vendor_assessment.created_at
        elif plan.audit:
            return plan.audit.created_at
        return None

    @classmethod
    def calculate_ttr_hours(
        cls, plan: RemediationPlan, source_detected_at: Optional[datetime]
    ) -> Optional[float]:
        """
        Calculates Time to Remediate (TTR) in hours from initial detection to verified closure.
        """
        if plan.status != RemediationStatusEnum.VERIFIED_CLOSED or not plan.verified_at:
            return None
        if not source_detected_at:
            return None

        v_at = cls._ensure_utc(plan.verified_at)
        s_at = cls._ensure_utc(source_detected_at)
        elapsed_sec = max(0.0, (v_at - s_at).total_seconds())
        return round(elapsed_sec / 3600.0, 2)

    # ─── 2. LIFECYCLE TRANSITION VALIDATION ──────────────────────────────────

    @classmethod
    def validate_lifecycle_transition(
        cls, current_status: RemediationStatusEnum, target_status: RemediationStatusEnum
    ) -> None:
        """Enforces canonical progressive state machine and rejects illegal jumps."""
        allowed_transitions = {
            RemediationStatusEnum.DRAFT: [
                RemediationStatusEnum.APPROVED,
                RemediationStatusEnum.CANCELLED,
            ],
            RemediationStatusEnum.APPROVED: [
                RemediationStatusEnum.IN_EXECUTION,
                RemediationStatusEnum.CANCELLED,
            ],
            RemediationStatusEnum.IN_EXECUTION: [
                RemediationStatusEnum.PENDING_VALIDATION,
                RemediationStatusEnum.CANCELLED,
            ],
            RemediationStatusEnum.PENDING_VALIDATION: [
                RemediationStatusEnum.IN_EXECUTION,  # Rework on failed validation/test
                RemediationStatusEnum.VERIFIED_CLOSED,
            ],
            RemediationStatusEnum.VERIFIED_CLOSED: [],  # Terminal immutable
            RemediationStatusEnum.CANCELLED: [],  # Terminal
        }

        if target_status not in allowed_transitions.get(current_status, []):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Illegal lifecycle transition from '{current_status}' to '{target_status}'.",
            )

    # ─── 3. REMEDIATION PLAN DOMAIN OPERATIONS ───────────────────────────────

    @classmethod
    def create_plan(
        cls,
        db: Session,
        organization_id: int,
        plan_owner_id: int,
        plan_code: str,
        title: str,
        problem_statement: str,
        root_cause_classification: RemediationRootCauseClassificationEnum,
        source_type: RemediationSourceTypeEnum,
        severity: RemediationSeverityEnum,
        finding_id: Optional[int] = None,
        compliance_drift_alert_id: Optional[int] = None,
        security_incident_id: Optional[int] = None,
        vendor_assessment_id: Optional[int] = None,
        audit_id: Optional[int] = None,
        target_completion_at: Optional[datetime] = None,
    ) -> RemediationPlan:
        # Check plan code uniqueness within tenant
        existing = (
            db.query(RemediationPlan)
            .filter(
                RemediationPlan.organization_id == organization_id,
                RemediationPlan.plan_code == plan_code,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Remediation plan code '{plan_code}' already exists in your organization.",
            )

        # Validate source existence and tenant isolation
        if source_type == RemediationSourceTypeEnum.FINDING:
            if not finding_id:
                raise HTTPException(status_code=400, detail="finding_id is required for FINDING source")
            f = db.query(Finding).filter(Finding.id == finding_id, Finding.organization_id == organization_id).first()
            if not f:
                raise HTTPException(status_code=404, detail="Finding not found in your organization")
        elif source_type == RemediationSourceTypeEnum.CCM_DRIFT:
            if not compliance_drift_alert_id:
                raise HTTPException(status_code=400, detail="compliance_drift_alert_id is required for CCM_DRIFT source")
            a = db.query(ComplianceDriftAlert).filter(ComplianceDriftAlert.id == compliance_drift_alert_id, ComplianceDriftAlert.organization_id == organization_id).first()
            if not a:
                raise HTTPException(status_code=404, detail="Compliance drift alert not found in your organization")
        elif source_type == RemediationSourceTypeEnum.SECURITY_INCIDENT:
            if not security_incident_id:
                raise HTTPException(status_code=400, detail="security_incident_id is required for SECURITY_INCIDENT source")
            inc = db.query(SecurityIncident).filter(SecurityIncident.id == security_incident_id, SecurityIncident.organization_id == organization_id).first()
            if not inc:
                raise HTTPException(status_code=404, detail="Security incident not found in your organization")
        elif source_type == RemediationSourceTypeEnum.TPRM_ASSESSMENT:
            if not vendor_assessment_id:
                raise HTTPException(status_code=400, detail="vendor_assessment_id is required for TPRM_ASSESSMENT source")
            va = db.query(VendorAssessment).filter(VendorAssessment.id == vendor_assessment_id, VendorAssessment.organization_id == organization_id).first()
            if not va:
                raise HTTPException(status_code=404, detail="Vendor assessment not found in your organization")
        elif source_type == RemediationSourceTypeEnum.AUDIT:
            if not audit_id:
                raise HTTPException(status_code=400, detail="audit_id is required for AUDIT source")
            aud = db.query(Audit).filter(Audit.id == audit_id, Audit.organization_id == organization_id).first()
            if not aud:
                raise HTTPException(status_code=404, detail="Audit not found in your organization")

        plan = RemediationPlan(
            organization_id=organization_id,
            plan_code=plan_code,
            title=title,
            problem_statement=problem_statement,
            root_cause_classification=root_cause_classification,
            source_type=source_type,
            finding_id=finding_id,
            compliance_drift_alert_id=compliance_drift_alert_id,
            security_incident_id=security_incident_id,
            vendor_assessment_id=vendor_assessment_id,
            audit_id=audit_id,
            severity=severity,
            status=RemediationStatusEnum.DRAFT,
            plan_owner_id=plan_owner_id,
            target_completion_at=cls._ensure_utc(target_completion_at),
            validation_attempts_count=0,
            is_immutable=False,
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)

        actor_email = cls._get_actor_email(db, plan_owner_id)
        AuditService.log(
            db=db,
            organization_id=organization_id,
            action="REMEDIATION_PLAN_CREATED",
            resource_type="REMEDIATION_PLAN",
            actor_email=actor_email,
            actor_id=plan_owner_id,
            resource_id=str(plan.id),
            details={"plan_code": plan_code, "source_type": source_type.value, "severity": severity.value},
        )
        return plan

    @classmethod
    def update_plan(
        cls,
        db: Session,
        plan: RemediationPlan,
        actor_id: int,
        title: Optional[str] = None,
        problem_statement: Optional[str] = None,
        root_cause_classification: Optional[RemediationRootCauseClassificationEnum] = None,
        severity: Optional[RemediationSeverityEnum] = None,
        target_completion_at: Optional[datetime] = None,
    ) -> RemediationPlan:
        if plan.is_immutable or plan.status == RemediationStatusEnum.VERIFIED_CLOSED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Remediation plan is closed and permanently immutable.",
            )

        if title is not None:
            plan.title = title
        if problem_statement is not None:
            plan.problem_statement = problem_statement
        if root_cause_classification is not None:
            plan.root_cause_classification = root_cause_classification
        if severity is not None:
            plan.severity = severity
        if target_completion_at is not None:
            plan.target_completion_at = cls._ensure_utc(target_completion_at)

        plan.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(plan)

        actor_email = cls._get_actor_email(db, actor_id)
        AuditService.log(
            db=db,
            organization_id=plan.organization_id,
            action="REMEDIATION_PLAN_UPDATED",
            resource_type="REMEDIATION_PLAN",
            actor_email=actor_email,
            actor_id=actor_id,
            resource_id=str(plan.id),
            details={"plan_code": plan.plan_code},
        )
        return plan

    @classmethod
    def approve_plan(
        cls,
        db: Session,
        plan: RemediationPlan,
        approver_id: int,
        custom_target_completion_at: Optional[datetime] = None,
        notes: Optional[str] = None,
    ) -> RemediationPlan:
        """Approves a DRAFT plan. Enforces four-eyes separation and task existence."""
        if plan.is_immutable or plan.status == RemediationStatusEnum.VERIFIED_CLOSED:
            raise HTTPException(status_code=409, detail="Plan is immutable.")

        cls.validate_lifecycle_transition(plan.status, RemediationStatusEnum.APPROVED)

        # Four-Eyes Separation: Approver != Plan Owner
        if approver_id == plan.plan_owner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Separation of duties violation: Plan Owner cannot approve their own remediation plan.",
            )

        # Precondition: At least 1 task must exist
        if not plan.tasks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Remediation plan cannot be approved without at least one defined remediation task.",
            )

        now = datetime.now(timezone.utc)
        plan.approved_by_id = approver_id
        plan.approved_at = now
        plan.status = RemediationStatusEnum.APPROVED

        # Calculate authoritative target completion deadline
        if custom_target_completion_at:
            target = cls._ensure_utc(custom_target_completion_at)
            if target <= now:
                raise HTTPException(status_code=422, detail="Target completion date must be in the future.")
            plan.target_completion_at = target
        else:
            sla_days = cls.calculate_default_sla_duration_days(plan.severity)
            plan.target_completion_at = now + timedelta(days=sla_days)

        plan.updated_at = now
        db.commit()
        db.refresh(plan)

        actor_email = cls._get_actor_email(db, approver_id)
        AuditService.log(
            db=db,
            organization_id=plan.organization_id,
            action="REMEDIATION_PLAN_APPROVED",
            resource_type="REMEDIATION_PLAN",
            actor_email=actor_email,
            actor_id=approver_id,
            resource_id=str(plan.id),
            details={"plan_code": plan.plan_code, "target_completion_at": plan.target_completion_at.isoformat()},
        )
        return plan

    @classmethod
    def start_execution(cls, db: Session, plan: RemediationPlan, actor_id: int) -> RemediationPlan:
        """Transitions plan from APPROVED to IN_EXECUTION."""
        if plan.is_immutable or plan.status == RemediationStatusEnum.VERIFIED_CLOSED:
            raise HTTPException(status_code=409, detail="Plan is immutable.")

        cls.validate_lifecycle_transition(plan.status, RemediationStatusEnum.IN_EXECUTION)

        now = datetime.now(timezone.utc)
        plan.status = RemediationStatusEnum.IN_EXECUTION
        plan.started_at = now
        plan.updated_at = now
        db.commit()
        db.refresh(plan)

        actor_email = cls._get_actor_email(db, actor_id)
        AuditService.log(
            db=db,
            organization_id=plan.organization_id,
            action="REMEDIATION_STARTED",
            resource_type="REMEDIATION_PLAN",
            actor_email=actor_email,
            actor_id=actor_id,
            resource_id=str(plan.id),
            details={"plan_code": plan.plan_code},
        )
        return plan

    @classmethod
    def submit_for_validation(cls, db: Session, plan: RemediationPlan, actor_id: int) -> RemediationPlan:
        """Transitions plan from IN_EXECUTION to PENDING_VALIDATION once all tasks are completed."""
        if plan.is_immutable or plan.status == RemediationStatusEnum.VERIFIED_CLOSED:
            raise HTTPException(status_code=409, detail="Plan is immutable.")

        cls.validate_lifecycle_transition(plan.status, RemediationStatusEnum.PENDING_VALIDATION)

        active_tasks = [t for t in plan.tasks if t.status != TaskStatusEnum.CANCELLED]
        if not active_tasks:
            raise HTTPException(status_code=400, detail="Cannot submit for validation without active tasks.")

        # Precondition: 100% of non-cancelled tasks must be COMPLETED
        for t in active_tasks:
            if t.status != TaskStatusEnum.COMPLETED:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot submit for validation: Task #{t.task_seq} '{t.title}' is not completed ({t.status}).",
                )
            if not t.evidence_links:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot submit for validation: Task #{t.task_seq} '{t.title}' lacks required evidence.",
                )

        now = datetime.now(timezone.utc)
        plan.status = RemediationStatusEnum.PENDING_VALIDATION
        plan.validation_attempts_count += 1
        plan.updated_at = now
        db.commit()
        db.refresh(plan)

        actor_email = cls._get_actor_email(db, actor_id)
        AuditService.log(
            db=db,
            organization_id=plan.organization_id,
            action="REMEDIATION_SUBMITTED_VALIDATION",
            resource_type="REMEDIATION_PLAN",
            actor_email=actor_email,
            actor_id=actor_id,
            resource_id=str(plan.id),
            details={"plan_code": plan.plan_code, "attempt": plan.validation_attempts_count},
        )
        return plan

    @classmethod
    def reject_validation(
        cls, db: Session, plan: RemediationPlan, verifier_id: int, rejection_notes: str
    ) -> RemediationPlan:
        """Rejects validation during review/re-test, sending plan back to IN_EXECUTION."""
        if plan.is_immutable or plan.status == RemediationStatusEnum.VERIFIED_CLOSED:
            raise HTTPException(status_code=409, detail="Plan is immutable.")

        cls.validate_lifecycle_transition(plan.status, RemediationStatusEnum.IN_EXECUTION)

        if not rejection_notes or len(rejection_notes.strip()) < 15:
            raise HTTPException(status_code=400, detail="Mandatory rejection notes must be at least 15 characters.")

        now = datetime.now(timezone.utc)
        plan.status = RemediationStatusEnum.IN_EXECUTION
        plan.updated_at = now
        db.commit()
        db.refresh(plan)

        actor_email = cls._get_actor_email(db, verifier_id)
        AuditService.log(
            db=db,
            organization_id=plan.organization_id,
            action="REMEDIATION_VALIDATION_REJECTED",
            resource_type="REMEDIATION_PLAN",
            actor_email=actor_email,
            actor_id=verifier_id,
            resource_id=str(plan.id),
            details={"plan_code": plan.plan_code, "rejection_notes": rejection_notes},
        )
        return plan

    @classmethod
    def verify_and_close_plan(
        cls, db: Session, plan: RemediationPlan, verifier_id: int, verification_notes: str
    ) -> RemediationPlan:
        """
        Executes Four-Eyes Verification and permanent closure of the remediation plan.
        Requires:
        1. status == PENDING_VALIDATION
        2. verifier != plan_owner
        3. verifier != any task assignee
        4. at least 1 PASS re-test record
        5. verification notes >= 15 characters
        """
        if plan.is_immutable or plan.status == RemediationStatusEnum.VERIFIED_CLOSED:
            raise HTTPException(status_code=409, detail="Plan is already verified and closed.")

        cls.validate_lifecycle_transition(plan.status, RemediationStatusEnum.VERIFIED_CLOSED)

        if not verification_notes or len(verification_notes.strip()) < 15:
            raise HTTPException(status_code=400, detail="Mandatory verification notes must be at least 15 characters.")

        # Four-Eyes Separation: Verifier != Plan Owner
        if verifier_id == plan.plan_owner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Separation of duties violation: Plan Owner cannot verify their own remediation plan.",
            )

        # Four-Eyes Separation: Verifier != Any Task Assignee
        task_assignee_ids = {t.assignee_id for t in plan.tasks if t.assignee_id is not None}
        if verifier_id in task_assignee_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Separation of duties violation: Task implementers cannot verify this remediation plan.",
            )

        # Precondition: At least 1 PASS Re-Test Record
        pass_retest = any(r.test_result == ReTestResultEnum.PASS for r in plan.retest_records)
        if not pass_retest:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Remediation plan cannot be verified and closed without at least one empirical 'PASS' re-test record.",
            )

        now = datetime.now(timezone.utc)
        plan.status = RemediationStatusEnum.VERIFIED_CLOSED
        plan.verified_by_id = verifier_id
        plan.verified_at = now
        plan.verification_notes = verification_notes.strip()
        plan.is_immutable = True

        # Calculate authoritative REI and TTR metrics
        plan.rei_score = cls.calculate_rei(plan)
        source_ts = cls.get_source_detected_timestamp(plan)
        plan.ttr_hours = cls.calculate_ttr_hours(plan, source_ts)

        # ─── ATOMIC UPSTREAM SOURCE RESOLUTION ────────────────────────────────
        actor_email = cls._get_actor_email(db, verifier_id)

        if plan.finding_id and plan.finding:
            finding = plan.finding
            if finding.status in (
                FindingStatusEnum.OPEN,
                FindingStatusEnum.IN_REMEDIATION,
                FindingStatusEnum.PENDING_VALIDATION,
            ):
                finding.status = FindingStatusEnum.RESOLVED
                finding.resolved_at = now
                finding.resolved_by_id = verifier_id
                finding.resolution = f"Resolved via verified CAPA {plan.plan_code}"
                finding.updated_at = now
                AuditService.log(
                    db=db,
                    organization_id=plan.organization_id,
                    action="UPSTREAM_SOURCE_RESOLVED",
                    resource_type="FINDING",
                    actor_email=actor_email,
                    actor_id=verifier_id,
                    resource_id=str(finding.id),
                    details={"plan_code": plan.plan_code, "new_status": finding.status.value},
                )
            else:
                AuditService.log(
                    db=db,
                    organization_id=plan.organization_id,
                    action="UPSTREAM_SOURCE_RESOLUTION_SKIPPED",
                    resource_type="FINDING",
                    actor_email=actor_email,
                    actor_id=verifier_id,
                    resource_id=str(finding.id),
                    details={"plan_code": plan.plan_code, "status": finding.status.value},
                )

        elif plan.compliance_drift_alert_id and plan.compliance_drift_alert:
            alert = plan.compliance_drift_alert
            if alert.status == DriftAlertStatusEnum.ACTIVE:
                alert.status = DriftAlertStatusEnum.RESOLVED
                alert.resolved_at = now
                alert.resolved_by_id = verifier_id
                alert.resolution_notes = f"Auto-resolved via verified Remediation Plan {plan.plan_code}"
                alert.updated_at = now
                AuditService.log(
                    db=db,
                    organization_id=plan.organization_id,
                    action="UPSTREAM_SOURCE_RESOLVED",
                    resource_type="COMPLIANCE_DRIFT_ALERT",
                    actor_email=actor_email,
                    actor_id=verifier_id,
                    resource_id=str(alert.id),
                    details={"plan_code": plan.plan_code, "new_status": alert.status.value},
                )
            else:
                AuditService.log(
                    db=db,
                    organization_id=plan.organization_id,
                    action="UPSTREAM_SOURCE_RESOLUTION_SKIPPED",
                    resource_type="COMPLIANCE_DRIFT_ALERT",
                    actor_email=actor_email,
                    actor_id=verifier_id,
                    resource_id=str(alert.id),
                    details={"plan_code": plan.plan_code, "status": alert.status.value},
                )

        elif plan.security_incident_id and plan.security_incident:
            incident = plan.security_incident
            # Non-invasive assurance: Append immutable timeline event rather than mutating incident status directly
            from app.models.incident import IncidentTimelineEvent, TimelineEventTypeEnum, TimelineEventSourceEnum
            ev = IncidentTimelineEvent(
                organization_id=plan.organization_id,
                incident_id=incident.id,
                event_type=TimelineEventTypeEnum.ERADICATION_STEP,
                event_occurred_at=now,
                actor_id=verifier_id,
                description=f"Verified remediation CAPA '{plan.plan_code}' completed. REI: {plan.rei_score} / 100.0.",
                source=TimelineEventSourceEnum.SYSTEM_AUTOMATION,
            )
            db.add(ev)
            AuditService.log(
                db=db,
                organization_id=plan.organization_id,
                action="UPSTREAM_SOURCE_RESOLVED",
                resource_type="SECURITY_INCIDENT",
                actor_email=actor_email,
                actor_id=verifier_id,
                resource_id=str(incident.id),
                details={"plan_code": plan.plan_code, "event_type": "ERADICATION_STEP"},
            )

        elif plan.vendor_assessment_id and plan.vendor_assessment:
            AuditService.log(
                db=db,
                organization_id=plan.organization_id,
                action="UPSTREAM_SOURCE_RESOLVED",
                resource_type="VENDOR_ASSESSMENT",
                actor_email=actor_email,
                actor_id=verifier_id,
                resource_id=str(plan.vendor_assessment_id),
                details={"plan_code": plan.plan_code},
            )

        elif plan.audit_id and plan.audit:
            AuditService.log(
                db=db,
                organization_id=plan.organization_id,
                action="UPSTREAM_SOURCE_RESOLVED",
                resource_type="AUDIT",
                actor_email=actor_email,
                actor_id=verifier_id,
                resource_id=str(plan.audit_id),
                details={"plan_code": plan.plan_code},
            )

        plan.updated_at = now
        db.commit()
        db.refresh(plan)

        AuditService.log(
            db=db,
            organization_id=plan.organization_id,
            action="REMEDIATION_VERIFIED_CLOSED",
            resource_type="REMEDIATION_PLAN",
            actor_email=actor_email,
            actor_id=verifier_id,
            resource_id=str(plan.id),
            details={
                "plan_code": plan.plan_code,
                "rei_score": plan.rei_score,
                "ttr_hours": plan.ttr_hours,
            },
        )
        return plan

    @classmethod
    def cancel_plan(
        cls, db: Session, plan: RemediationPlan, actor_id: int, cancellation_notes: str
    ) -> RemediationPlan:
        """Cancels a plan from DRAFT or APPROVED states."""
        if plan.is_immutable or plan.status == RemediationStatusEnum.VERIFIED_CLOSED:
            raise HTTPException(status_code=409, detail="Closed plan cannot be cancelled.")

        cls.validate_lifecycle_transition(plan.status, RemediationStatusEnum.CANCELLED)

        if not cancellation_notes or len(cancellation_notes.strip()) < 10:
            raise HTTPException(status_code=400, detail="Mandatory cancellation notes must be at least 10 characters.")

        now = datetime.now(timezone.utc)
        plan.status = RemediationStatusEnum.CANCELLED
        plan.cancellation_notes = cancellation_notes.strip()
        plan.is_immutable = True
        plan.updated_at = now
        db.commit()
        db.refresh(plan)

        actor_email = cls._get_actor_email(db, actor_id)
        AuditService.log(
            db=db,
            organization_id=plan.organization_id,
            action="REMEDIATION_CANCELLED",
            resource_type="REMEDIATION_PLAN",
            actor_email=actor_email,
            actor_id=actor_id,
            resource_id=str(plan.id),
            details={"plan_code": plan.plan_code, "cancellation_notes": cancellation_notes},
        )
        return plan

    # ─── 4. REMEDIATION TASK OPERATIONS ──────────────────────────────────────

    @classmethod
    def add_task(
        cls,
        db: Session,
        plan: RemediationPlan,
        actor_id: int,
        task_seq: int,
        title: str,
        description: str,
        assignee_id: Optional[int] = None,
        due_date: Optional[datetime] = None,
    ) -> RemediationTask:
        if plan.is_immutable or plan.status in (RemediationStatusEnum.VERIFIED_CLOSED, RemediationStatusEnum.CANCELLED):
            raise HTTPException(status_code=409, detail="Cannot add tasks to a closed or cancelled plan.")

        # Check assignee tenant if provided
        if assignee_id:
            u = db.query(User).filter(User.id == assignee_id, User.organization_id == plan.organization_id).first()
            if not u:
                raise HTTPException(status_code=404, detail="Assignee user not found in your organization.")

        # Check sequence uniqueness
        existing = (
            db.query(RemediationTask)
            .filter(RemediationTask.remediation_plan_id == plan.id, RemediationTask.task_seq == task_seq)
            .first()
        )
        if existing:
            raise HTTPException(status_code=409, detail=f"Task sequence {task_seq} already exists in this plan.")

        task = RemediationTask(
            organization_id=plan.organization_id,
            remediation_plan_id=plan.id,
            task_seq=task_seq,
            title=title,
            description=description,
            assignee_id=assignee_id,
            due_date=cls._ensure_utc(due_date),
            status=TaskStatusEnum.PENDING,
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        actor_email = cls._get_actor_email(db, actor_id)
        AuditService.log(
            db=db,
            organization_id=plan.organization_id,
            action="REMEDIATION_TASK_CREATED",
            resource_type="REMEDIATION_TASK",
            actor_email=actor_email,
            actor_id=actor_id,
            resource_id=str(task.id),
            details={"plan_code": plan.plan_code, "task_seq": task_seq, "title": title},
        )
        return task

    @classmethod
    def update_task(
        cls,
        db: Session,
        task: RemediationTask,
        actor_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        assignee_id: Optional[int] = None,
        due_date: Optional[datetime] = None,
        status: Optional[TaskStatusEnum] = None,
        implementation_notes: Optional[str] = None,
    ) -> RemediationTask:
        plan = task.remediation_plan
        if plan.is_immutable or plan.status in (RemediationStatusEnum.VERIFIED_CLOSED, RemediationStatusEnum.CANCELLED):
            raise HTTPException(status_code=409, detail="Parent plan is immutable.")

        if title is not None:
            task.title = title
        if description is not None:
            task.description = description
        if assignee_id is not None:
            u = db.query(User).filter(User.id == assignee_id, User.organization_id == task.organization_id).first()
            if not u:
                raise HTTPException(status_code=404, detail="Assignee user not found in your organization.")
            task.assignee_id = assignee_id
        if due_date is not None:
            task.due_date = cls._ensure_utc(due_date)
        if implementation_notes is not None:
            task.implementation_notes = implementation_notes

        if status is not None:
            task.status = status
            if status == TaskStatusEnum.COMPLETED:
                task.completed_at = datetime.now(timezone.utc)
            elif status in (TaskStatusEnum.PENDING, TaskStatusEnum.IN_PROGRESS):
                task.completed_at = None

        task.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(task)

        actor_email = cls._get_actor_email(db, actor_id)
        AuditService.log(
            db=db,
            organization_id=task.organization_id,
            action="REMEDIATION_TASK_UPDATED",
            resource_type="REMEDIATION_TASK",
            actor_email=actor_email,
            actor_id=actor_id,
            resource_id=str(task.id),
            details={"task_seq": task.task_seq, "status": task.status.value},
        )
        return task

    # ─── 5. EVIDENCE BINDING OPERATIONS ──────────────────────────────────────

    @classmethod
    def link_evidence_to_task(
        cls,
        db: Session,
        task: RemediationTask,
        actor_id: int,
        evidence_id: int,
        notes: Optional[str] = None,
    ) -> RemediationEvidenceLink:
        plan = task.remediation_plan
        if plan.is_immutable or plan.status in (RemediationStatusEnum.VERIFIED_CLOSED, RemediationStatusEnum.CANCELLED):
            raise HTTPException(status_code=409, detail="Parent plan is immutable.")

        # Verify evidence existence and tenant isolation
        ev = (
            db.query(EvidenceItem)
            .filter(
                EvidenceItem.id == evidence_id,
                EvidenceItem.organization_id == task.organization_id,
            )
            .first()
        )
        if not ev:
            raise HTTPException(status_code=404, detail="Evidence item not found in your organization.")

        # Verify evidence is ACCEPTED and not superseded
        if ev.status != EvidenceStatusEnum.ACCEPTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Only ACCEPTED evidence items can be bound to remediation tasks (current: {ev.status}).",
            )
        if getattr(ev, "is_superseded", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Superseded evidence items cannot be used for remediation verification.",
            )

        existing = (
            db.query(RemediationEvidenceLink)
            .filter(
                RemediationEvidenceLink.remediation_task_id == task.id,
                RemediationEvidenceLink.evidence_id == evidence_id,
            )
            .first()
        )
        if existing:
            raise HTTPException(status_code=409, detail="Evidence item is already linked to this task.")

        link = RemediationEvidenceLink(
            organization_id=task.organization_id,
            remediation_task_id=task.id,
            evidence_id=evidence_id,
            verification_status=EvidenceVerificationStatusEnum.SUBMITTED,
            notes=notes,
        )
        db.add(link)
        db.commit()
        db.refresh(link)

        actor_email = cls._get_actor_email(db, actor_id)
        AuditService.log(
            db=db,
            organization_id=task.organization_id,
            action="REMEDIATION_EVIDENCE_LINKED",
            resource_type="REMEDIATION_EVIDENCE_LINK",
            actor_email=actor_email,
            actor_id=actor_id,
            resource_id=str(link.id),
            details={"task_id": task.id, "evidence_id": evidence_id},
        )
        return link

    # ─── 6. RE-TEST RECORD OPERATIONS ────────────────────────────────────────

    @classmethod
    def record_retest(
        cls,
        db: Session,
        plan: RemediationPlan,
        tester_id: int,
        test_executed_at: datetime,
        test_result: ReTestResultEnum,
        validation_narrative: str,
        metric_observed_value: Optional[float] = None,
        evidence_id: Optional[int] = None,
    ) -> RemediationReTestRecord:
        """Records an empirical validation re-test. PASS strictly requires accepted evidence."""
        if plan.is_immutable or plan.status in (RemediationStatusEnum.VERIFIED_CLOSED, RemediationStatusEnum.CANCELLED):
            raise HTTPException(status_code=409, detail="Cannot log re-test records on a closed or cancelled plan.")

        if not validation_narrative or len(validation_narrative.strip()) < 10:
            raise HTTPException(status_code=400, detail="Mandatory validation narrative must be at least 10 characters.")

        if test_result == ReTestResultEnum.PASS:
            if not evidence_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A 'PASS' re-test result strictly requires an associated evidence_id.",
                )
            ev = (
                db.query(EvidenceItem)
                .filter(
                    EvidenceItem.id == evidence_id,
                    EvidenceItem.organization_id == plan.organization_id,
                )
                .first()
            )
            if not ev:
                raise HTTPException(status_code=404, detail="Evidence item not found in your organization.")
            if ev.status != EvidenceStatusEnum.ACCEPTED:
                raise HTTPException(
                    status_code=400,
                    detail=f"Re-test evidence must be in ACCEPTED status (current: {ev.status}).",
                )

        record = RemediationReTestRecord(
            organization_id=plan.organization_id,
            remediation_plan_id=plan.id,
            test_executed_at=cls._ensure_utc(test_executed_at),
            tester_id=tester_id,
            test_result=test_result,
            metric_observed_value=metric_observed_value,
            evidence_id=evidence_id,
            validation_narrative=validation_narrative.strip(),
        )
        db.add(record)

        # If re-test fails during PENDING_VALIDATION, auto-revert plan to IN_EXECUTION for rework
        if test_result == ReTestResultEnum.FAIL and plan.status == RemediationStatusEnum.PENDING_VALIDATION:
            plan.status = RemediationStatusEnum.IN_EXECUTION
            plan.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(record)

        actor_email = cls._get_actor_email(db, tester_id)
        AuditService.log(
            db=db,
            organization_id=plan.organization_id,
            action="REMEDIATION_RETEST_LOGGED",
            resource_type="REMEDIATION_RETEST_RECORD",
            actor_email=actor_email,
            actor_id=tester_id,
            resource_id=str(record.id),
            details={"plan_code": plan.plan_code, "test_result": test_result.value},
        )
        return record

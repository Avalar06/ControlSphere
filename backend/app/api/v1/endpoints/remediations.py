from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.core.permissions import Permission
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
from app.schemas.remediation import (
    RemediationEvidenceLinkCreate,
    RemediationEvidenceLinkRead,
    RemediationOverviewResponse,
    RemediationPlanApproveRequest,
    RemediationPlanCancelRequest,
    RemediationPlanCreate,
    RemediationPlanDetailRead,
    RemediationPlanRead,
    RemediationPlanRejectValidationRequest,
    RemediationPlanUpdate,
    RemediationPlanVerifyCloseRequest,
    RemediationReTestCreate,
    RemediationReTestRecordRead,
    RemediationTaskCreate,
    RemediationTaskRead,
    RemediationTaskUpdate,
)
from app.services.audit_service import AuditService
from app.services.remediation_service import RemediationService

router = APIRouter()


def _enrich_plan_read(plan: RemediationPlan) -> RemediationPlanRead:
    sla_status, remaining = RemediationService.calculate_sla_status(plan)
    dto = RemediationPlanRead.model_validate(plan)
    dto.sla_status = sla_status
    dto.remaining_hours = remaining
    return dto


def _enrich_plan_detail_read(plan: RemediationPlan) -> RemediationPlanDetailRead:
    sla_status, remaining = RemediationService.calculate_sla_status(plan)
    dto = RemediationPlanDetailRead.model_validate(plan)
    dto.sla_status = sla_status
    dto.remaining_hours = remaining
    return dto


# ─── 1. CORE REMEDIATION PLAN ENDPOINTS ──────────────────────────────────────

@router.get("", response_model=List[RemediationPlanRead])
def list_remediation_plans(
    status_filter: Optional[RemediationStatusEnum] = Query(None, alias="status"),
    severity: Optional[RemediationSeverityEnum] = None,
    source_type: Optional[RemediationSourceTypeEnum] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REMEDIATION_READ)),
):
    """Lists all tenant-scoped remediation plans with multi-criteria filtering."""
    query = db.query(RemediationPlan).filter(
        RemediationPlan.organization_id == current_user.organization_id
    )

    if status_filter:
        query = query.filter(RemediationPlan.status == status_filter)
    if severity:
        query = query.filter(RemediationPlan.severity == severity)
    if source_type:
        query = query.filter(RemediationPlan.source_type == source_type)
    if search:
        s = f"%{search}%"
        query = query.filter(
            (RemediationPlan.title.ilike(s))
            | (RemediationPlan.plan_code.ilike(s))
            | (RemediationPlan.problem_statement.ilike(s))
        )

    plans = query.order_by(RemediationPlan.created_at.desc()).offset(skip).limit(limit).all()
    return [_enrich_plan_read(p) for p in plans]


@router.get("/overview", response_model=RemediationOverviewResponse)
def get_remediation_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REMEDIATION_READ)),
):
    """Returns aggregate enterprise remediation KPIs, SLA distributions, and execution averages."""
    plans = (
        db.query(RemediationPlan)
        .filter(RemediationPlan.organization_id == current_user.organization_id)
        .all()
    )

    total_plans = len(plans)
    open_plans = len(
        [
            p
            for p in plans
            if p.status
            in (
                RemediationStatusEnum.DRAFT,
                RemediationStatusEnum.APPROVED,
                RemediationStatusEnum.IN_EXECUTION,
                RemediationStatusEnum.PENDING_VALIDATION,
            )
        ]
    )
    crit_high = len(
        [
            p
            for p in plans
            if p.severity in (RemediationSeverityEnum.CRITICAL, RemediationSeverityEnum.HIGH)
        ]
    )
    pending_val = len(
        [p for p in plans if p.status == RemediationStatusEnum.PENDING_VALIDATION]
    )

    sla_breached = 0
    sla_dist: dict[str, int] = {s.value: 0 for s in SlaStatusEnum}
    status_dist: dict[str, int] = {s.value: 0 for s in RemediationStatusEnum}
    severity_dist: dict[str, int] = {s.value: 0 for s in RemediationSeverityEnum}
    source_dist: dict[str, int] = {s.value: 0 for s in RemediationSourceTypeEnum}

    rei_scores: List[float] = []
    ttr_values: List[float] = []

    for p in plans:
        status_dist[p.status.value] = status_dist.get(p.status.value, 0) + 1
        severity_dist[p.severity.value] = severity_dist.get(p.severity.value, 0) + 1
        source_dist[p.source_type.value] = source_dist.get(p.source_type.value, 0) + 1

        sla_st, _ = RemediationService.calculate_sla_status(p)
        sla_dist[sla_st.value] = sla_dist.get(sla_st.value, 0) + 1
        if sla_st == SlaStatusEnum.BREACHED:
            sla_breached += 1

        if p.rei_score is not None:
            rei_scores.append(p.rei_score)
        if p.ttr_hours is not None:
            ttr_values.append(p.ttr_hours)

    avg_rei = round(sum(rei_scores) / len(rei_scores), 2) if rei_scores else None
    avg_ttr = round(sum(ttr_values) / len(ttr_values), 2) if ttr_values else None

    return RemediationOverviewResponse(
        total_plans=total_plans,
        open_plans=open_plans,
        critical_or_high_plans=crit_high,
        pending_validation_plans=pending_val,
        sla_breached_plans=sla_breached,
        average_rei_score=avg_rei,
        average_ttr_hours=avg_ttr,
        status_distribution=status_dist,
        severity_distribution=severity_dist,
        source_distribution=source_dist,
        sla_distribution=sla_dist,
    )


@router.get("/{id}", response_model=RemediationPlanDetailRead)
def get_remediation_plan(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REMEDIATION_READ)),
):
    """Fetches full details of a specific remediation plan including tasks, evidence, and re-tests."""
    plan = (
        db.query(RemediationPlan)
        .filter(
            RemediationPlan.id == id,
            RemediationPlan.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Remediation plan not found in your organization.",
        )
    return _enrich_plan_detail_read(plan)


@router.post("", response_model=RemediationPlanRead, status_code=status.HTTP_201_CREATED)
def create_remediation_plan(
    data: RemediationPlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REMEDIATION_MANAGE)),
):
    """
    Creates a new remediation plan (CAPA).
    Enforces server-authoritative tenant derivation and exact single-source linkage.
    """
    plan = RemediationService.create_plan(
        db=db,
        organization_id=current_user.organization_id,
        plan_owner_id=current_user.id,
        plan_code=data.plan_code,
        title=data.title,
        problem_statement=data.problem_statement,
        root_cause_classification=data.root_cause_classification,
        source_type=data.source_type,
        severity=data.severity,
        finding_id=data.finding_id,
        compliance_drift_alert_id=data.compliance_drift_alert_id,
        security_incident_id=data.security_incident_id,
        vendor_assessment_id=data.vendor_assessment_id,
        audit_id=data.audit_id,
        target_completion_at=data.target_completion_at,
    )
    return _enrich_plan_read(plan)


@router.patch("/{id}", response_model=RemediationPlanRead)
def update_remediation_plan(
    id: int,
    data: RemediationPlanUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REMEDIATION_MANAGE)),
):
    """Updates mutable metadata of a remediation plan. Rejects CLOSED plans with HTTP 409."""
    plan = (
        db.query(RemediationPlan)
        .filter(
            RemediationPlan.id == id,
            RemediationPlan.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Remediation plan not found.")

    updated = RemediationService.update_plan(
        db=db,
        plan=plan,
        actor_id=current_user.id,
        title=data.title,
        problem_statement=data.problem_statement,
        root_cause_classification=data.root_cause_classification,
        severity=data.severity,
        target_completion_at=data.target_completion_at,
    )
    return _enrich_plan_read(updated)


@router.post("/{id}/approve", response_model=RemediationPlanRead)
def approve_remediation_plan(
    id: int,
    data: RemediationPlanApproveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REMEDIATION_APPROVE)),
):
    """
    Formally approves a DRAFT remediation plan.
    Enforces four-eyes separation (approver != owner) and task existence.
    """
    plan = (
        db.query(RemediationPlan)
        .filter(
            RemediationPlan.id == id,
            RemediationPlan.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Remediation plan not found.")

    approved = RemediationService.approve_plan(
        db=db,
        plan=plan,
        approver_id=current_user.id,
        custom_target_completion_at=data.target_completion_at,
        notes=data.notes,
    )
    return _enrich_plan_read(approved)


@router.post("/{id}/start", response_model=RemediationPlanRead)
def start_remediation_execution(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REMEDIATION_EXECUTE)),
):
    """Transitions an APPROVED plan to IN_EXECUTION and sets server started_at timestamp."""
    plan = (
        db.query(RemediationPlan)
        .filter(
            RemediationPlan.id == id,
            RemediationPlan.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Remediation plan not found.")

    started = RemediationService.start_execution(db=db, plan=plan, actor_id=current_user.id)
    return _enrich_plan_read(started)


@router.post("/{id}/submit-validation", response_model=RemediationPlanRead)
def submit_remediation_for_validation(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REMEDIATION_EXECUTE)),
):
    """
    Submits an IN_EXECUTION plan for validation.
    Requires 100% of non-cancelled tasks to be COMPLETED with valid evidence.
    """
    plan = (
        db.query(RemediationPlan)
        .filter(
            RemediationPlan.id == id,
            RemediationPlan.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Remediation plan not found.")

    submitted = RemediationService.submit_for_validation(
        db=db, plan=plan, actor_id=current_user.id
    )
    return _enrich_plan_read(submitted)


@router.post("/{id}/reject-validation", response_model=RemediationPlanRead)
def reject_remediation_validation(
    id: int,
    data: RemediationPlanRejectValidationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REMEDIATION_VERIFY)),
):
    """Rejects validation during review/re-test, sending plan back to IN_EXECUTION for rework."""
    plan = (
        db.query(RemediationPlan)
        .filter(
            RemediationPlan.id == id,
            RemediationPlan.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Remediation plan not found.")

    rejected = RemediationService.reject_validation(
        db=db,
        plan=plan,
        verifier_id=current_user.id,
        rejection_notes=data.rejection_notes,
    )
    return _enrich_plan_read(rejected)


@router.post("/{id}/verify-close", response_model=RemediationPlanRead)
def verify_and_close_remediation_plan(
    id: int,
    data: RemediationPlanVerifyCloseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REMEDIATION_VERIFY)),
):
    """
    Executes four-eyes verification and permanent closure of the remediation plan.
    Enforces:
    - Four-eyes separation (verifier != owner, verifier != any task assignee)
    - At least 1 PASS empirical re-test record
    - Mandatory verification notes (>= 15 chars)
    - Atomic upstream source resolution (CCM Drift, Findings, Incidents)
    - Permanently marks plan immutable
    """
    plan = (
        db.query(RemediationPlan)
        .filter(
            RemediationPlan.id == id,
            RemediationPlan.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Remediation plan not found.")

    closed = RemediationService.verify_and_close_plan(
        db=db,
        plan=plan,
        verifier_id=current_user.id,
        verification_notes=data.verification_notes,
    )
    return _enrich_plan_read(closed)


@router.post("/{id}/cancel", response_model=RemediationPlanRead)
def cancel_remediation_plan(
    id: int,
    data: RemediationPlanCancelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REMEDIATION_MANAGE)),
):
    """Cancels a DRAFT or APPROVED plan with mandatory cancellation justification."""
    plan = (
        db.query(RemediationPlan)
        .filter(
            RemediationPlan.id == id,
            RemediationPlan.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Remediation plan not found.")

    cancelled = RemediationService.cancel_plan(
        db=db,
        plan=plan,
        actor_id=current_user.id,
        cancellation_notes=data.cancellation_notes,
    )
    return _enrich_plan_read(cancelled)


# ─── 2. TASK ENDPOINTS ───────────────────────────────────────────────────────

@router.get("/{id}/tasks", response_model=List[RemediationTaskRead])
def list_remediation_tasks(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REMEDIATION_READ)),
):
    """Lists all remediation tasks for a given plan."""
    plan = (
        db.query(RemediationPlan)
        .filter(
            RemediationPlan.id == id,
            RemediationPlan.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Remediation plan not found.")
    return plan.tasks


@router.post("/{id}/tasks", response_model=RemediationTaskRead, status_code=status.HTTP_201_CREATED)
def create_remediation_task(
    id: int,
    data: RemediationTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REMEDIATION_MANAGE)),
):
    """Adds a new atomic remediation task to a plan."""
    plan = (
        db.query(RemediationPlan)
        .filter(
            RemediationPlan.id == id,
            RemediationPlan.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Remediation plan not found.")

    task = RemediationService.add_task(
        db=db,
        plan=plan,
        actor_id=current_user.id,
        task_seq=data.task_seq,
        title=data.title,
        description=data.description,
        assignee_id=data.assignee_id,
        due_date=data.due_date,
    )
    return task


@router.patch("/tasks/{task_id}", response_model=RemediationTaskRead)
def update_remediation_task(
    task_id: int,
    data: RemediationTaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REMEDIATION_EXECUTE)),
):
    """Updates a remediation task."""
    task = (
        db.query(RemediationTask)
        .filter(
            RemediationTask.id == task_id,
            RemediationTask.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Remediation task not found.")

    updated = RemediationService.update_task(
        db=db,
        task=task,
        actor_id=current_user.id,
        title=data.title,
        description=data.description,
        assignee_id=data.assignee_id,
        due_date=data.due_date,
        status=data.status,
        implementation_notes=data.implementation_notes,
    )
    return updated


@router.post("/tasks/{task_id}/start", response_model=RemediationTaskRead)
def start_remediation_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REMEDIATION_EXECUTE)),
):
    """Transitions a task to IN_PROGRESS."""
    task = (
        db.query(RemediationTask)
        .filter(
            RemediationTask.id == task_id,
            RemediationTask.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Remediation task not found.")

    updated = RemediationService.update_task(
        db=db, task=task, actor_id=current_user.id, status=TaskStatusEnum.IN_PROGRESS
    )
    return updated


@router.post("/tasks/{task_id}/complete", response_model=RemediationTaskRead)
def complete_remediation_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REMEDIATION_EXECUTE)),
):
    """Marks a task COMPLETED and records server completed_at timestamp."""
    task = (
        db.query(RemediationTask)
        .filter(
            RemediationTask.id == task_id,
            RemediationTask.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Remediation task not found.")

    updated = RemediationService.update_task(
        db=db, task=task, actor_id=current_user.id, status=TaskStatusEnum.COMPLETED
    )
    return updated


@router.post("/tasks/{task_id}/cancel", response_model=RemediationTaskRead)
def cancel_remediation_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REMEDIATION_MANAGE)),
):
    """Cancels a remediation task."""
    task = (
        db.query(RemediationTask)
        .filter(
            RemediationTask.id == task_id,
            RemediationTask.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Remediation task not found.")

    updated = RemediationService.update_task(
        db=db, task=task, actor_id=current_user.id, status=TaskStatusEnum.CANCELLED
    )
    return updated


# ─── 3. EVIDENCE BINDING ENDPOINTS ───────────────────────────────────────────

@router.get("/tasks/{task_id}/evidence", response_model=List[RemediationEvidenceLinkRead])
def list_task_evidence_links(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REMEDIATION_READ)),
):
    """Lists evidence items bound to a specific remediation task."""
    task = (
        db.query(RemediationTask)
        .filter(
            RemediationTask.id == task_id,
            RemediationTask.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Remediation task not found.")
    return task.evidence_links


@router.post(
    "/tasks/{task_id}/evidence",
    response_model=RemediationEvidenceLinkRead,
    status_code=status.HTTP_201_CREATED,
)
def link_evidence_to_task(
    task_id: int,
    data: RemediationEvidenceLinkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REMEDIATION_EXECUTE)),
):
    """
    Binds an accepted Phase 3 EvidenceItem to a remediation task.
    Rejects foreign, unaccepted, or superseded evidence.
    """
    task = (
        db.query(RemediationTask)
        .filter(
            RemediationTask.id == task_id,
            RemediationTask.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Remediation task not found.")

    link = RemediationService.link_evidence_to_task(
        db=db,
        task=task,
        actor_id=current_user.id,
        evidence_id=data.evidence_id,
        notes=data.notes,
    )
    return link


@router.delete("/tasks/{task_id}/evidence/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_evidence_from_task(
    task_id: int,
    link_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REMEDIATION_EXECUTE)),
):
    """Unlinks evidence from a task prior to plan closure."""
    link = (
        db.query(RemediationEvidenceLink)
        .filter(
            RemediationEvidenceLink.id == link_id,
            RemediationEvidenceLink.remediation_task_id == task_id,
            RemediationEvidenceLink.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not link:
        raise HTTPException(status_code=404, detail="Evidence link not found.")

    task = link.task
    if task.remediation_plan.is_immutable or task.remediation_plan.status in (
        RemediationStatusEnum.VERIFIED_CLOSED,
        RemediationStatusEnum.CANCELLED,
    ):
        raise HTTPException(status_code=409, detail="Parent plan is immutable.")

    db.delete(link)
    db.commit()

    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        action="REMEDIATION_EVIDENCE_UNLINKED",
        resource_type="REMEDIATION_EVIDENCE_LINK",
        actor_email=current_user.email,
        actor_id=current_user.id,
        resource_id=str(link_id),
        details={"task_id": task_id},
    )
    return None


# ─── 4. RE-TEST RECORD ENDPOINTS ─────────────────────────────────────────────

@router.get("/{id}/retests", response_model=List[RemediationReTestRecordRead])
def list_retest_records(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REMEDIATION_READ)),
):
    """Lists all empirical re-test records for a remediation plan."""
    plan = (
        db.query(RemediationPlan)
        .filter(
            RemediationPlan.id == id,
            RemediationPlan.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Remediation plan not found.")
    return plan.retest_records


@router.post(
    "/{id}/retests",
    response_model=RemediationReTestRecordRead,
    status_code=status.HTTP_201_CREATED,
)
def record_retest(
    id: int,
    data: RemediationReTestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REMEDIATION_VERIFY)),
):
    """
    Logs an empirical validation re-test.
    PASS strictly requires accepted evidence.
    FAIL auto-reverts plan from PENDING_VALIDATION back to IN_EXECUTION for rework.
    """
    plan = (
        db.query(RemediationPlan)
        .filter(
            RemediationPlan.id == id,
            RemediationPlan.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Remediation plan not found.")

    record = RemediationService.record_retest(
        db=db,
        plan=plan,
        tester_id=current_user.id,
        test_executed_at=data.test_executed_at,
        test_result=data.test_result,
        validation_narrative=data.validation_narrative,
        metric_observed_value=data.metric_observed_value,
        evidence_id=data.evidence_id,
    )
    return record

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.core.permissions import Permission
from app.models.resilience import (
    ContinuityPlanStatusEnum,
    CriticalityTierEnum,
    ExerciseOutcomeEnum,
    ExerciseStatusEnum,
)
from app.models.user import User
from app.schemas.resilience import (
    BusinessImpactAnalysisApproveRequest,
    BusinessImpactAnalysisCreate,
    BusinessImpactAnalysisRead,
    BusinessProcessCreate,
    BusinessProcessRead,
    BusinessProcessUpdate,
    ContinuityPlanCreate,
    ContinuityPlanDetailResponse,
    ContinuityPlanRejectRequest,
    ContinuityPlanResponse,
    ContinuityPlanUpdate,
    ContinuityRecoveryStepCreate,
    ContinuityRecoveryStepResponse,
    ContinuityRecoveryStepUpdate,
    ExerciseEscalationRequest,
    OutageCostCalculationRequest,
    OutageCostCalculationResult,
    OutageSimulationRequest,
    OutageSimulationResponse,
    ProcessDependencyCreate,
    ProcessDependencyHealthResponse,
    ProcessDependencyRead,
    ProcessImpactSummaryResponse,
    ResilienceDashboardResponse,
    ResilienceEvidenceLinkCreate,
    ResilienceEvidenceLinkResponse,
    ResilienceExerciseCancelRequest,
    ResilienceExerciseCompleteRequest,
    ResilienceExerciseCreate,
    ResilienceExerciseDetailResponse,
    ResilienceExerciseResponse,
    ResilienceExerciseReviewRequest,
    ResilienceExerciseStartRequest,
)
from app.services.resilience_service import (
    ResilienceService,
    calculate_projected_outage_loss,
)

router = APIRouter()


# ─── 1. BUSINESS PROCESS CATALOG ─────────────────────────────────────────────

@router.post("/processes", response_model=BusinessProcessRead, status_code=status.HTTP_201_CREATED)
def create_business_process(
    payload: BusinessProcessCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_MANAGE)),
):
    """Create a new business process in the tenant catalog."""
    return ResilienceService.create_business_process(
        db, current_user.organization_id, payload, current_user.id
    )


@router.get("/processes", response_model=List[BusinessProcessRead])
def list_business_processes(
    criticality_tier: Optional[CriticalityTierEnum] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_READ)),
):
    """List tenant-scoped business processes with optional filters."""
    return ResilienceService.list_business_processes(
        db,
        current_user.organization_id,
        criticality_tier=criticality_tier,
        search=search,
        skip=skip,
        limit=limit,
    )


@router.get("/processes/{process_id}", response_model=BusinessProcessRead)
def get_business_process(
    process_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_READ)),
):
    """Retrieve a single business process enforcing tenant isolation."""
    return ResilienceService.get_business_process(
        db, current_user.organization_id, process_id
    )


@router.put("/processes/{process_id}", response_model=BusinessProcessRead)
def update_business_process(
    process_id: int,
    payload: BusinessProcessUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_MANAGE)),
):
    """Update a business process in the tenant catalog."""
    return ResilienceService.update_business_process(
        db, current_user.organization_id, process_id, payload, current_user.id
    )


@router.delete("/processes/{process_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_business_process(
    process_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_MANAGE)),
):
    """Archive/delete a business process from the tenant catalog."""
    process = ResilienceService.get_business_process(
        db, current_user.organization_id, process_id
    )
    db.delete(process)
    db.commit()


# ─── 2. BUSINESS IMPACT ANALYSIS (BIA) LIFECYCLE ─────────────────────────────

@router.post("/bia", response_model=BusinessImpactAnalysisRead, status_code=status.HTTP_201_CREATED)
def create_draft_bia(
    payload: BusinessImpactAnalysisCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_MANAGE)),
):
    """Create a new draft Business Impact Analysis for a business process."""
    return ResilienceService.draft_bia(
        db, current_user.organization_id, payload, current_user.id
    )


@router.get("/processes/{process_id}/bia", response_model=List[BusinessImpactAnalysisRead])
def list_process_bias(
    process_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_READ)),
):
    """List all BIA versions for a business process."""
    return ResilienceService.list_process_bias(
        db, current_user.organization_id, process_id
    )


@router.get("/bia/{bia_id}", response_model=BusinessImpactAnalysisRead)
def get_bia(
    bia_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_READ)),
):
    """Retrieve a specific Business Impact Analysis enforcing tenant isolation."""
    return ResilienceService.get_bia(
        db, current_user.organization_id, bia_id
    )


@router.put("/bia/{bia_id}", response_model=BusinessImpactAnalysisRead)
def update_draft_bia(
    bia_id: int,
    payload: BusinessImpactAnalysisCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_MANAGE)),
):
    """Update a draft BIA. Only DRAFT status BIAs can be updated."""
    from app.models.resilience import BiaStatusEnum
    from fastapi import HTTPException

    bia = ResilienceService.get_bia(db, current_user.organization_id, bia_id)
    if bia.status != BiaStatusEnum.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot update BIA #{bia_id} in {bia.status.value} status. Only DRAFT records can be updated.",
        )

    bia.rto_hours = payload.rto_hours
    bia.rpo_hours = payload.rpo_hours
    bia.mtd_hours = payload.mtd_hours
    bia.hourly_downtime_cost = payload.hourly_downtime_cost
    bia.fixed_outage_cost = payload.fixed_outage_cost
    bia.notes = payload.notes
    db.commit()
    db.refresh(bia)
    return bia


@router.post("/bia/{bia_id}/approve", response_model=BusinessImpactAnalysisRead)
def approve_bia(
    bia_id: int,
    payload: Optional[BusinessImpactAnalysisApproveRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_APPROVE)),
):
    """Formally approve a draft BIA with four-eyes rule (requester != approver)."""
    notes = payload.notes if payload else None
    return ResilienceService.approve_bia(
        db, current_user.organization_id, bia_id, current_user.id, notes
    )


@router.post("/bia/{bia_id}/archive", response_model=BusinessImpactAnalysisRead)
def archive_draft_bia(
    bia_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_MANAGE)),
):
    """Archive a draft BIA. Only DRAFT status BIAs can be archived."""
    return ResilienceService.archive_draft_bia(
        db, current_user.organization_id, bia_id, current_user.id
    )


@router.get("/processes/{process_id}/bia/active", response_model=Optional[BusinessImpactAnalysisRead])
def get_active_bia(
    process_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_READ)),
):
    """Retrieve the currently active approved BIA baseline for a process."""
    from app.models.resilience import BiaStatusEnum, BusinessImpactAnalysis

    bia = (
        db.query(BusinessImpactAnalysis)
        .filter(
            BusinessImpactAnalysis.organization_id == current_user.organization_id,
            BusinessImpactAnalysis.process_id == process_id,
            BusinessImpactAnalysis.status == BiaStatusEnum.ACTIVE,
        )
        .first()
    )
    return bia


# ─── 3. CROSS-MODULE PROCESS DEPENDENCIES & HEALTH ───────────────────────────

@router.post("/dependencies", response_model=ProcessDependencyRead, status_code=status.HTTP_201_CREATED)
def add_process_dependency(
    payload: ProcessDependencyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_MANAGE)),
):
    """Add a cross-module dependency (Vendor, Control, CloudAsset, DataAsset, or Process) to a business process."""
    return ResilienceService.add_process_dependency(
        db, current_user.organization_id, payload, current_user.id
    )


@router.post(
    "/processes/{process_id}/dependencies",
    response_model=ProcessDependencyRead,
    status_code=status.HTTP_201_CREATED,
)
def add_process_dependency_for_process(
    process_id: int,
    payload: ProcessDependencyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_MANAGE)),
):
    """Add a cross-module dependency scoped to a specific business process."""
    return ResilienceService.add_process_dependency(
        db,
        current_user.organization_id,
        payload,
        current_user.id,
        process_id_override=process_id,
    )


@router.get("/processes/{process_id}/dependencies", response_model=List[ProcessDependencyRead])
def list_process_dependencies(
    process_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_READ)),
):
    """List all dependencies for a business process."""
    from app.models.resilience import ProcessDependency

    ResilienceService.get_business_process(db, current_user.organization_id, process_id)
    deps = (
        db.query(ProcessDependency)
        .filter(
            ProcessDependency.organization_id == current_user.organization_id,
            ProcessDependency.process_id == process_id,
        )
        .order_by(ProcessDependency.recovery_priority_order.asc(), ProcessDependency.id.asc())
        .all()
    )
    return deps


@router.delete("/dependencies/{dependency_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_process_dependency(
    dependency_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_MANAGE)),
):
    """Remove a cross-module dependency from a business process."""
    ResilienceService.remove_process_dependency(
        db, current_user.organization_id, dependency_id, current_user.id
    )


@router.get(
    "/processes/{process_id}/dependency-health",
    response_model=ProcessDependencyHealthResponse,
)
def get_process_dependency_health(
    process_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_READ)),
):
    """Evaluate live dependency health and unmitigated SPOF exposure for a business process."""
    return ResilienceService.get_process_dependency_health(
        db, current_user.organization_id, process_id
    )


# ─── 4. DETERMINISTIC OUTAGE LOSS & BLAST-RADIUS SIMULATION ──────────────────

@router.post("/outage-loss", response_model=OutageCostCalculationResult)
def calculate_outage_loss(
    payload: OutageCostCalculationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_READ)),
):
    """Calculate projected outage loss using deterministic formula: Total = Fixed + (Hourly * H)."""
    return calculate_projected_outage_loss(
        duration_hours=payload.duration_hours,
        hourly_downtime_cost=payload.hourly_downtime_cost,
        fixed_outage_cost=payload.fixed_outage_cost,
    )


@router.post("/simulate-outage", response_model=OutageSimulationResponse)
def simulate_outage(
    payload: OutageSimulationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_READ)),
):
    """Simulate downstream process blast radius and weighted financial loss for a failing dependency node."""
    return ResilienceService.simulate_outage(
        db, current_user.organization_id, payload
    )


@router.get(
    "/processes/{process_id}/impact-summary",
    response_model=ProcessImpactSummaryResponse,
)
def get_process_impact_summary(
    process_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_READ)),
):
    """Retrieve enriched process impact, continuity readiness, and empirical exercise summary."""
    return ResilienceService.get_process_impact_summary(
        db, current_user.organization_id, process_id
    )


@router.get("/dashboard", response_model=ResilienceDashboardResponse)
def get_resilience_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_READ)),
):
    """Retrieve tenant-wide operational resilience, continuity coverage, and DR exercise assurance metrics."""
    return ResilienceService.get_resilience_dashboard(
        db, current_user.organization_id
    )


# ─── 5. CONTINUITY PLANS & RECOVERY STEPS (BATCH 5) ──────────────────────────

@router.get(
    "/processes/{process_id}/continuity-plans",
    response_model=List[ContinuityPlanResponse],
)
def list_continuity_plans(
    process_id: int,
    status_filter: Optional[ContinuityPlanStatusEnum] = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_READ)),
):
    """List continuity plans for a business process ordered by version descending."""
    return ResilienceService.list_continuity_plans(
        db, current_user.organization_id, process_id, status_filter=status_filter
    )


@router.post(
    "/processes/{process_id}/continuity-plans",
    response_model=ContinuityPlanResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_continuity_plan(
    process_id: int,
    payload: ContinuityPlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_MANAGE)),
):
    """Create a new DRAFT Continuity Plan for a business process."""
    return ResilienceService.create_continuity_plan(
        db, current_user.organization_id, process_id, payload, current_user.id
    )


@router.get(
    "/continuity-plans/{plan_id}",
    response_model=ContinuityPlanDetailResponse,
)
def get_continuity_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_READ)),
):
    """Retrieve a Continuity Plan with ordered recovery steps, duration rollups, and evidence links."""
    return ResilienceService.get_continuity_plan_detail(
        db, current_user.organization_id, plan_id
    )


@router.patch(
    "/continuity-plans/{plan_id}",
    response_model=ContinuityPlanResponse,
)
def update_continuity_plan(
    plan_id: int,
    payload: ContinuityPlanUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_MANAGE)),
):
    """Update a DRAFT Continuity Plan."""
    return ResilienceService.update_continuity_plan(
        db, current_user.organization_id, plan_id, payload, current_user.id
    )


@router.get(
    "/continuity-plans/{plan_id}/steps",
    response_model=List[ContinuityRecoveryStepResponse],
)
def list_recovery_steps(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_READ)),
):
    """List ordered recovery steps for a Continuity Plan."""
    return ResilienceService.list_recovery_steps(
        db, current_user.organization_id, plan_id
    )


@router.post(
    "/continuity-plans/{plan_id}/steps",
    response_model=ContinuityRecoveryStepResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_recovery_step(
    plan_id: int,
    payload: ContinuityRecoveryStepCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_MANAGE)),
):
    """Add an ordered recovery step to a DRAFT Continuity Plan."""
    return ResilienceService.create_recovery_step(
        db, current_user.organization_id, plan_id, payload, current_user.id
    )


@router.patch(
    "/continuity-plans/{plan_id}/steps/{step_id}",
    response_model=ContinuityRecoveryStepResponse,
)
def update_recovery_step(
    plan_id: int,
    step_id: int,
    payload: ContinuityRecoveryStepUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_MANAGE)),
):
    """Update an ordered recovery step on a DRAFT Continuity Plan."""
    return ResilienceService.update_recovery_step(
        db, current_user.organization_id, plan_id, step_id, payload, current_user.id
    )


@router.delete(
    "/continuity-plans/{plan_id}/steps/{step_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_recovery_step(
    plan_id: int,
    step_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_MANAGE)),
):
    """Delete a recovery step from a DRAFT Continuity Plan."""
    ResilienceService.delete_recovery_step(
        db, current_user.organization_id, plan_id, step_id, current_user.id
    )


@router.post(
    "/continuity-plans/{plan_id}/submit",
    response_model=ContinuityPlanResponse,
)
def submit_continuity_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_MANAGE)),
):
    """Submit a DRAFT Continuity Plan for approval after verifying BIA RTO/RPO and step rollup invariants."""
    return ResilienceService.submit_continuity_plan(
        db, current_user.organization_id, plan_id, current_user.id
    )


@router.post(
    "/continuity-plans/{plan_id}/approve",
    response_model=ContinuityPlanResponse,
)
def approve_continuity_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_APPROVE)),
):
    """Approve a PENDING_APPROVAL Continuity Plan enforcing Four-Eyes SoD and atomic superseding."""
    return ResilienceService.approve_continuity_plan(
        db, current_user.organization_id, plan_id, current_user.id
    )


@router.post(
    "/continuity-plans/{plan_id}/reject",
    response_model=ContinuityPlanResponse,
)
def reject_continuity_plan(
    plan_id: int,
    payload: ContinuityPlanRejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_APPROVE)),
):
    """Reject a PENDING_APPROVAL Continuity Plan back to DRAFT."""
    return ResilienceService.reject_continuity_plan(
        db, current_user.organization_id, plan_id, payload, current_user.id
    )


@router.post(
    "/continuity-plans/{plan_id}/archive",
    response_model=ContinuityPlanResponse,
)
def archive_continuity_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_MANAGE)),
):
    """Archive a Continuity Plan (requires RESILIENCE_APPROVE if currently APPROVED, and no active exercises)."""
    return ResilienceService.archive_continuity_plan(
        db, current_user.organization_id, plan_id, current_user.id
    )


@router.get(
    "/continuity-plans/{plan_id}/evidence",
    response_model=List[ResilienceEvidenceLinkResponse],
)
def list_plan_evidence(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_READ)),
):
    """List evidence items cryptographically bound to a Continuity Plan."""
    return ResilienceService.list_plan_evidence(
        db, current_user.organization_id, plan_id
    )


@router.post(
    "/continuity-plans/{plan_id}/evidence",
    response_model=ResilienceEvidenceLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
def link_evidence_to_plan(
    plan_id: int,
    payload: ResilienceEvidenceLinkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_MANAGE)),
):
    """Bind a canonical EvidenceItem to a Continuity Plan with SHA-256 snapshot capture."""
    return ResilienceService.link_evidence_to_plan(
        db, current_user.organization_id, plan_id, payload, current_user.id
    )


# ─── 6. RESILIENCE EXERCISES & CLOSED-LOOP ESCALATION (BATCH 5) ──────────────

@router.get("/exercises", response_model=List[ResilienceExerciseResponse])
def list_exercises(
    process_id: Optional[int] = None,
    continuity_plan_id: Optional[int] = None,
    status_filter: Optional[ExerciseStatusEnum] = Query(default=None, alias="status"),
    outcome_filter: Optional[ExerciseOutcomeEnum] = Query(default=None, alias="outcome"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_READ)),
):
    """List tenant-scoped Resilience Exercises with optional filters."""
    return ResilienceService.list_exercises(
        db,
        current_user.organization_id,
        process_id=process_id,
        continuity_plan_id=continuity_plan_id,
        status_filter=status_filter,
        outcome_filter=outcome_filter,
        skip=skip,
        limit=limit,
    )


@router.post(
    "/exercises",
    response_model=ResilienceExerciseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_exercise(
    payload: ResilienceExerciseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_MANAGE)),
):
    """Schedule a new Resilience Exercise against an APPROVED Continuity Plan and ACTIVE BIA."""
    return ResilienceService.create_exercise(
        db, current_user.organization_id, payload, current_user.id
    )


@router.get(
    "/exercises/{exercise_id}",
    response_model=ResilienceExerciseDetailResponse,
)
def get_exercise(
    exercise_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_READ)),
):
    """Retrieve a Resilience Exercise with linked evidence items."""
    return ResilienceService.get_exercise_detail(
        db, current_user.organization_id, exercise_id
    )


@router.post(
    "/exercises/{exercise_id}/start",
    response_model=ResilienceExerciseResponse,
)
def start_exercise(
    exercise_id: int,
    payload: Optional[ResilienceExerciseStartRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_MANAGE)),
):
    """Transition a PLANNED Resilience Exercise to IN_PROGRESS."""
    return ResilienceService.start_exercise(
        db, current_user.organization_id, exercise_id, payload, current_user.id
    )


@router.post(
    "/exercises/{exercise_id}/complete",
    response_model=ResilienceExerciseResponse,
)
def complete_exercise(
    exercise_id: int,
    payload: ResilienceExerciseCompleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_MANAGE)),
):
    """Complete an IN_PROGRESS exercise, computing server-side RTO/RPO/MTD variance, outcome, and SHA-256 hash."""
    return ResilienceService.complete_exercise(
        db, current_user.organization_id, exercise_id, payload, current_user.id
    )


@router.post(
    "/exercises/{exercise_id}/review",
    response_model=ResilienceExerciseResponse,
)
def review_exercise(
    exercise_id: int,
    payload: Optional[ResilienceExerciseReviewRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_APPROVE)),
):
    """Formally review a COMPLETED exercise enforcing Four-Eyes SoD and breach escalation gate."""
    return ResilienceService.review_exercise(
        db, current_user.organization_id, exercise_id, payload, current_user.id
    )


@router.post(
    "/exercises/{exercise_id}/cancel",
    response_model=ResilienceExerciseResponse,
)
def cancel_exercise(
    exercise_id: int,
    payload: Optional[ResilienceExerciseCancelRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_MANAGE)),
):
    """Cancel a PLANNED or IN_PROGRESS Resilience Exercise."""
    return ResilienceService.cancel_exercise(
        db, current_user.organization_id, exercise_id, payload, current_user.id
    )


@router.get(
    "/exercises/{exercise_id}/evidence",
    response_model=List[ResilienceEvidenceLinkResponse],
)
def list_exercise_evidence(
    exercise_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_READ)),
):
    """List evidence items cryptographically bound to a Resilience Exercise."""
    return ResilienceService.list_exercise_evidence(
        db, current_user.organization_id, exercise_id
    )


@router.post(
    "/exercises/{exercise_id}/evidence",
    response_model=ResilienceEvidenceLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
def link_evidence_to_exercise(
    exercise_id: int,
    payload: ResilienceEvidenceLinkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_MANAGE)),
):
    """Bind a canonical EvidenceItem to a Resilience Exercise with SHA-256 snapshot capture."""
    return ResilienceService.link_evidence_to_exercise(
        db, current_user.organization_id, exercise_id, payload, current_user.id
    )


@router.post(
    "/exercises/{exercise_id}/escalate",
    response_model=ResilienceExerciseResponse,
)
def escalate_exercise_deficiency(
    exercise_id: int,
    payload: ExerciseEscalationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_MANAGE)),
):
    """Escalate a COMPLETED or REVIEWED exercise deficiency to canonical Finding, RemediationPlan, and Risk."""
    return ResilienceService.escalate_exercise_deficiency(
        db, current_user.organization_id, exercise_id, payload, current_user.id
    )

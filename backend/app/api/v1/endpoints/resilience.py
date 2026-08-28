from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.core.permissions import Permission
from app.models.resilience import CriticalityTierEnum
from app.models.user import User
from app.schemas.resilience import (
    BusinessImpactAnalysisApproveRequest,
    BusinessImpactAnalysisCreate,
    BusinessImpactAnalysisRead,
    BusinessProcessCreate,
    BusinessProcessRead,
    BusinessProcessUpdate,
    OutageCostCalculationRequest,
    OutageCostCalculationResult,
    ProcessDependencyCreate,
    ProcessDependencyRead,
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
    # Retrieve first to enforce tenant isolation (404 if not found)
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
    from app.models.resilience import BiaStatusEnum, BusinessImpactAnalysis
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


# ─── 3. CROSS-MODULE PROCESS DEPENDENCIES ────────────────────────────────────

@router.post("/dependencies", response_model=ProcessDependencyRead, status_code=status.HTTP_201_CREATED)
def add_process_dependency(
    payload: ProcessDependencyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_MANAGE)),
):
    """Add a cross-module dependency (Vendor or Control) to a business process."""
    return ResilienceService.add_process_dependency(
        db, current_user.organization_id, payload, current_user.id
    )


@router.get("/processes/{process_id}/dependencies", response_model=List[ProcessDependencyRead])
def list_process_dependencies(
    process_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_READ)),
):
    """List all dependencies for a business process."""
    from app.models.resilience import ProcessDependency
    deps = (
        db.query(ProcessDependency)
        .filter(
            ProcessDependency.organization_id == current_user.organization_id,
            ProcessDependency.process_id == process_id,
        )
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


# ─── 4. DETERMINISTIC OUTAGE LOSS CALCULATION ENGINE ─────────────────────────

@router.post("/outage-loss", response_model=OutageCostCalculationResult)
def calculate_outage_loss(
    payload: OutageCostCalculationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.RESILIENCE_READ)),
):
    """Calculate projected outage loss using deterministic formula: Total = Fixed + (Hourly * H)."""
    result = calculate_projected_outage_loss(
        duration_hours=payload.duration_hours,
        hourly_downtime_cost=payload.hourly_downtime_cost,
        fixed_outage_cost=payload.fixed_outage_cost,
    )
    return result

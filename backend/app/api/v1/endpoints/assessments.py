from datetime import date
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from app.api.deps import (
    get_client_ip,
    get_current_user,
    get_db,
    get_user_agent,
    require_permission,
)
from app.core.permissions import Permission
from app.models.assessment import (
    AssessmentConclusionEnum,
    AssessmentStatusEnum,
)
from app.models.user import User
from app.schemas.assessment import (
    AssessmentComplete,
    AssessmentCreate,
    AssessmentDetailResponse,
    AssessmentEvidenceCreate,
    AssessmentEvidenceResponse,
    AssessmentResponse,
    AssessmentStatsResponse,
    AssessmentUpdate,
)
from app.services.assessment_service import AssessmentService
from app.services.audit_service import AuditService

router = APIRouter()


@router.get("", response_model=List[AssessmentResponse])
def list_assessments(
    organization_control_id: Optional[int] = Query(None, description="Filter by control ID"),
    assessor_id: Optional[int] = Query(None, description="Filter by assessor user ID"),
    status: Optional[AssessmentStatusEnum] = Query(None, description="Filter by assessment status"),
    conclusion: Optional[AssessmentConclusionEnum] = Query(None, description="Filter by conclusion"),
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(require_permission(Permission.CONTROL_READ)),
    db: Session = Depends(get_db),
) -> Any:
    """List organization control assessments with filtering and pagination."""
    return AssessmentService.list_assessments(
        db=db,
        organization_id=current_user.organization_id,
        organization_control_id=organization_control_id,
        assessor_id=assessor_id,
        status=status,
        conclusion=conclusion,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )


@router.get("/stats", response_model=AssessmentStatsResponse)
def get_assessment_stats(
    current_user: User = Depends(require_permission(Permission.CONTROL_READ)),
    db: Session = Depends(get_db),
) -> Any:
    """Get aggregate assessment metrics for the tenant."""
    return AssessmentService.get_stats(
        db=db, organization_id=current_user.organization_id
    )


@router.post("", response_model=AssessmentResponse, status_code=status.HTTP_201_CREATED)
def create_assessment(
    request: Request,
    ass_in: AssessmentCreate,
    current_user: User = Depends(require_permission(Permission.CONTROL_ASSESS)),
    db: Session = Depends(get_db),
) -> Any:
    """Create a new control assessment in DRAFT status."""
    try:
        new_ass = AssessmentService.create_assessment(
            db=db,
            obj_in=ass_in,
            organization_id=current_user.organization_id,
            creator_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Audit log
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="assessment.create",
        resource_type="ASSESSMENT",
        resource_id=str(new_ass.id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={
            "control_id": new_ass.organization_control_id,
            "method": new_ass.assessment_method.value,
        },
    )

    return AssessmentService.get_assessment_by_id(
        db=db, assessment_id=new_ass.id, organization_id=current_user.organization_id
    )


@router.get("/{assessment_id}", response_model=AssessmentDetailResponse)
def get_assessment(
    assessment_id: int,
    current_user: User = Depends(require_permission(Permission.CONTROL_READ)),
    db: Session = Depends(get_db),
) -> Any:
    """Retrieve full details of an assessment including linked evidence and findings."""
    ass = AssessmentService.get_assessment_by_id(
        db=db, assessment_id=assessment_id, organization_id=current_user.organization_id
    )
    if not ass:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found in your organization.",
        )
    return ass


@router.patch("/{assessment_id}", response_model=AssessmentResponse)
def update_assessment(
    request: Request,
    assessment_id: int,
    ass_in: AssessmentUpdate,
    current_user: User = Depends(require_permission(Permission.CONTROL_ASSESS)),
    db: Session = Depends(get_db),
) -> Any:
    """Update metadata of an active (DRAFT or IN_PROGRESS) assessment."""
    try:
        updated = AssessmentService.update_assessment(
            db=db,
            assessment_id=assessment_id,
            organization_id=current_user.organization_id,
            obj_in=ass_in,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found in your organization.",
        )

    # Audit log
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="assessment.update",
        resource_type="ASSESSMENT",
        resource_id=str(assessment_id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={"updated_fields": list(ass_in.model_dump(exclude_unset=True).keys())},
    )

    return AssessmentService.get_assessment_by_id(
        db=db, assessment_id=assessment_id, organization_id=current_user.organization_id
    )


@router.post("/{assessment_id}/start", response_model=AssessmentResponse)
def start_assessment(
    request: Request,
    assessment_id: int,
    current_user: User = Depends(require_permission(Permission.CONTROL_ASSESS)),
    db: Session = Depends(get_db),
) -> Any:
    """Transition assessment status from DRAFT to IN_PROGRESS."""
    try:
        updated = AssessmentService.start_assessment(
            db=db, assessment_id=assessment_id, organization_id=current_user.organization_id
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found in your organization.",
        )

    # Audit log
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="assessment.start",
        resource_type="ASSESSMENT",
        resource_id=str(assessment_id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
    )

    return AssessmentService.get_assessment_by_id(
        db=db, assessment_id=assessment_id, organization_id=current_user.organization_id
    )


@router.post("/{assessment_id}/complete", response_model=AssessmentResponse)
def complete_assessment(
    request: Request,
    assessment_id: int,
    complete_in: AssessmentComplete,
    current_user: User = Depends(require_permission(Permission.CONTROL_ASSESS)),
    db: Session = Depends(get_db),
) -> Any:
    """Complete an assessment with an authoritative conclusion and summary."""
    try:
        completed = AssessmentService.complete_assessment(
            db=db,
            assessment_id=assessment_id,
            organization_id=current_user.organization_id,
            complete_in=complete_in,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not completed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found in your organization.",
        )

    # Audit log
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="assessment.complete",
        resource_type="ASSESSMENT",
        resource_id=str(assessment_id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={"conclusion": completed.conclusion.value, "summary": completed.summary},
    )

    return AssessmentService.get_assessment_by_id(
        db=db, assessment_id=assessment_id, organization_id=current_user.organization_id
    )


@router.post("/{assessment_id}/supersede", response_model=AssessmentResponse)
def supersede_assessment(
    request: Request,
    assessment_id: int,
    current_user: User = Depends(require_permission(Permission.CONTROL_ASSESS)),
    db: Session = Depends(get_db),
) -> Any:
    """Mark a completed assessment as SUPERSEDED by a newer assessment iteration."""
    try:
        superseded = AssessmentService.supersede_assessment(
            db=db, assessment_id=assessment_id, organization_id=current_user.organization_id
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not superseded:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found in your organization.",
        )

    # Audit log
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="assessment.supersede",
        resource_type="ASSESSMENT",
        resource_id=str(assessment_id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
    )

    return AssessmentService.get_assessment_by_id(
        db=db, assessment_id=assessment_id, organization_id=current_user.organization_id
    )


@router.post("/{assessment_id}/evidence", response_model=AssessmentEvidenceResponse, status_code=status.HTTP_201_CREATED)
def link_assessment_evidence(
    request: Request,
    assessment_id: int,
    link_in: AssessmentEvidenceCreate,
    current_user: User = Depends(require_permission(Permission.CONTROL_ASSESS)),
    db: Session = Depends(get_db),
) -> Any:
    """Link an existing evidence artifact to an assessment for traceability."""
    try:
        link = AssessmentService.link_evidence(
            db=db,
            assessment_id=assessment_id,
            evidence_id=link_in.evidence_id,
            organization_id=current_user.organization_id,
            created_by_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Audit log
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="assessment.evidence.link",
        resource_type="ASSESSMENT_EVIDENCE",
        resource_id=str(link.id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={"assessment_id": assessment_id, "evidence_id": link_in.evidence_id},
    )

    return link


@router.delete("/{assessment_id}/evidence/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_assessment_evidence(
    request: Request,
    assessment_id: int,
    evidence_id: int,
    current_user: User = Depends(require_permission(Permission.CONTROL_ASSESS)),
    db: Session = Depends(get_db),
) -> None:
    """Unlink an evidence artifact from an active assessment."""
    try:
        success = AssessmentService.unlink_evidence(
            db=db,
            assessment_id=assessment_id,
            evidence_id=evidence_id,
            organization_id=current_user.organization_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence linkage not found in your organization.",
        )

    # Audit log
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="assessment.evidence.unlink",
        resource_type="ASSESSMENT_EVIDENCE",
        resource_id=f"{assessment_id}:{evidence_id}",
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
    )

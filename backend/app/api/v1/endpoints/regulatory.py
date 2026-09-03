from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_permission
from app.core.permissions import Permission
from app.models.user import User
from app.models.regulatory import RegulatoryAuthorityTypeEnum, RegulatoryMandateStatusEnum, RegulatoryChangeStatusEnum
from app.schemas.regulatory import (
    RegulatorySourceCreate,
    RegulatorySourceResponse,
    RegulatoryMandateCreate,
    RegulatoryMandateResponse,
    RegulatoryObligationCreate,
    RegulatoryObligationResponse,
    RegulatoryChangeEventCreate,
    RegulatoryChangeReviewRequest,
    RegulatoryChangeApproveRequest,
    RegulatoryChangeDismissRequest,
    RegulatoryChangeEventResponse,
    RegulatoryImpactAssessmentResponse,
)
from app.services.regulatory_service import RegulatoryService

router = APIRouter()


# ── Sources ─────────────────────────────────────────────────────────────────

@router.get("/sources", response_model=List[RegulatorySourceResponse])
def list_sources(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    authority_type: Optional[RegulatoryAuthorityTypeEnum] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REGULATORY_READ)),
) -> Any:
    """List regulatory sources for current organization."""
    return RegulatoryService.list_sources(
        db=db,
        organization_id=current_user.organization_id,
        skip=skip,
        limit=limit,
        authority_type=authority_type,
    )


@router.post("/sources", response_model=RegulatorySourceResponse, status_code=status.HTTP_201_CREATED)
def create_source(
    source_in: RegulatorySourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REGULATORY_MANAGE)),
) -> Any:
    """Create a new regulatory source authority."""
    try:
        return RegulatoryService.create_source(
            db=db,
            organization_id=current_user.organization_id,
            source_in=source_in,
            current_user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT if "already exists" in str(e) else status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── Mandates ────────────────────────────────────────────────────────────────

@router.get("/mandates", response_model=List[RegulatoryMandateResponse])
def list_mandates(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status_filter: Optional[RegulatoryMandateStatusEnum] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REGULATORY_READ)),
) -> Any:
    """List regulatory mandates for current organization."""
    return RegulatoryService.list_mandates(
        db=db,
        organization_id=current_user.organization_id,
        skip=skip,
        limit=limit,
        status=status_filter,
    )


@router.post("/mandates", response_model=RegulatoryMandateResponse, status_code=status.HTTP_201_CREATED)
def create_mandate(
    mandate_in: RegulatoryMandateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REGULATORY_MANAGE)),
) -> Any:
    """Create a new regulatory mandate or statute."""
    try:
        return RegulatoryService.create_mandate(
            db=db,
            organization_id=current_user.organization_id,
            mandate_in=mandate_in,
            current_user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT if "already exists" in str(e) else status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── Obligations ─────────────────────────────────────────────────────────────

@router.get("/obligations", response_model=List[RegulatoryObligationResponse])
def list_obligations(
    mandate_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REGULATORY_READ)),
) -> Any:
    """List atomic regulatory obligations."""
    return RegulatoryService.list_obligations(
        db=db,
        organization_id=current_user.organization_id,
        mandate_id=mandate_id,
        skip=skip,
        limit=limit,
    )


@router.post("/obligations", response_model=RegulatoryObligationResponse, status_code=status.HTTP_201_CREATED)
def create_obligation(
    obligation_in: RegulatoryObligationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REGULATORY_MANAGE)),
) -> Any:
    """Create a new statutory obligation mapped to controls."""
    try:
        return RegulatoryService.create_obligation(
            db=db,
            organization_id=current_user.organization_id,
            obligation_in=obligation_in,
            current_user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT if "already exists" in str(e) else status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── Change Events & Four-Eyes Review / Approval ─────────────────────────────

@router.get("/changes", response_model=List[RegulatoryChangeEventResponse])
def list_changes(
    mandate_id: Optional[int] = None,
    status_filter: Optional[RegulatoryChangeStatusEnum] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REGULATORY_READ)),
) -> Any:
    """List regulatory change events."""
    return RegulatoryService.list_changes(
        db=db,
        organization_id=current_user.organization_id,
        mandate_id=mandate_id,
        status=status_filter,
        skip=skip,
        limit=limit,
    )


@router.post("/changes", response_model=RegulatoryChangeEventResponse, status_code=status.HTTP_201_CREATED)
def stage_change(
    change_in: RegulatoryChangeEventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REGULATORY_MANAGE)),
) -> Any:
    """Stage a new regulatory change event with server-computed content checksum."""
    try:
        return RegulatoryService.stage_change_event(
            db=db,
            organization_id=current_user.organization_id,
            change_in=change_in,
            current_user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT if ("already exists" in str(e) or "Duplicate" in str(e)) else status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/changes/{id}/review", response_model=RegulatoryChangeEventResponse)
def review_change(
    id: int,
    review_in: RegulatoryChangeReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REGULATORY_MANAGE)),
) -> Any:
    """Submit a regulatory impact assessment and transition change event to REVIEWED."""
    try:
        change_event, _ = RegulatoryService.review_change_event(
            db=db,
            organization_id=current_user.organization_id,
            change_id=id,
            review_in=review_in,
            reviewer_id=current_user.id,
        )
        return change_event
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/changes/{id}/approve", response_model=RegulatoryChangeEventResponse)
def approve_change(
    id: int,
    approve_in: RegulatoryChangeApproveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REGULATORY_APPROVE)),
) -> Any:
    """Four-Eyes approval of a reviewed regulatory change event."""
    try:
        return RegulatoryService.approve_change_event(
            db=db,
            organization_id=current_user.organization_id,
            change_id=id,
            approve_in=approve_in,
            approver_id=current_user.id,
        )
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/changes/{id}/dismiss", response_model=RegulatoryChangeEventResponse)
def dismiss_change(
    id: int,
    dismiss_in: RegulatoryChangeDismissRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REGULATORY_MANAGE)),
) -> Any:
    """Dismiss a regulatory change event."""
    try:
        return RegulatoryService.dismiss_change_event(
            db=db,
            organization_id=current_user.organization_id,
            change_id=id,
            dismiss_in=dismiss_in,
            current_user_id=current_user.id,
        )
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

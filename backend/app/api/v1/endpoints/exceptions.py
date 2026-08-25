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
from app.models.exception import (
    ExceptionStatusEnum,
    ExceptionTypeEnum,
)
from app.models.user import User
from app.schemas.exception import (
    ExceptionClosure,
    ExceptionCompensatingControlCreate,
    ExceptionCompensatingControlResponse,
    ExceptionCreate,
    ExceptionDetailResponse,
    ExceptionResponse,
    ExceptionReviewAction,
    ExceptionStatsResponse,
    ExceptionUpdate,
)
from app.services.audit_service import AuditService
from app.services.exception_service import ExceptionService

router = APIRouter()


@router.get("", response_model=List[ExceptionResponse])
def list_exceptions(
    status: Optional[ExceptionStatusEnum] = Query(None, description="Filter by status"),
    exception_type: Optional[ExceptionTypeEnum] = Query(None, description="Filter by type"),
    owner_id: Optional[int] = Query(None, description="Filter by owner ID"),
    reviewer_id: Optional[int] = Query(None, description="Filter by reviewer ID"),
    active_only: bool = Query(False, description="Filter active exceptions"),
    expired_only: bool = Query(False, description="Filter expired exceptions"),
    search: Optional[str] = Query(None, description="Search keyword"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(require_permission(Permission.EXCEPTION_READ)),
    db: Session = Depends(get_db),
) -> Any:
    """List security exceptions with multi-criteria filtering and effective status evaluation."""
    return ExceptionService.list_exceptions(
        db=db,
        organization_id=current_user.organization_id,
        status=status,
        exception_type=exception_type,
        owner_id=owner_id,
        reviewer_id=reviewer_id,
        active_only=active_only,
        expired_only=expired_only,
        search=search,
        skip=skip,
        limit=limit,
    )


@router.get("/stats", response_model=ExceptionStatsResponse)
def get_exception_stats(
    current_user: User = Depends(require_permission(Permission.EXCEPTION_READ)),
    db: Session = Depends(get_db),
) -> Any:
    """Get aggregate exception metrics including active, pending review, expired, and expiring soon."""
    return ExceptionService.get_stats(
        db=db, organization_id=current_user.organization_id
    )


@router.post("", response_model=ExceptionResponse, status_code=status.HTTP_201_CREATED)
def create_exception(
    request: Request,
    exc_in: ExceptionCreate,
    current_user: User = Depends(require_permission(Permission.EXCEPTION_MANAGE)),
    db: Session = Depends(get_db),
) -> Any:
    """Request a new security exception with documented justification and validity window."""
    try:
        new_exc = ExceptionService.create_exception(
            db=db,
            obj_in=exc_in,
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
        action="exception.create",
        resource_type="SECURITY_EXCEPTION",
        resource_id=str(new_exc.id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={
            "title": new_exc.title,
            "type": new_exc.exception_type.value,
            "expiry_date": new_exc.expiry_date.isoformat(),
        },
    )

    return ExceptionService.get_exception_by_id(
        db=db, exception_id=new_exc.id, organization_id=current_user.organization_id
    )


@router.get("/{exception_id}", response_model=ExceptionDetailResponse)
def get_exception(
    exception_id: int,
    current_user: User = Depends(require_permission(Permission.EXCEPTION_READ)),
    db: Session = Depends(get_db),
) -> Any:
    """Retrieve full details of a specific security exception including compensating controls and review log."""
    exc = ExceptionService.get_exception_by_id(
        db=db, exception_id=exception_id, organization_id=current_user.organization_id
    )
    if not exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Security exception not found in your organization.",
        )
    return exc


@router.patch("/{exception_id}", response_model=ExceptionResponse)
def update_exception(
    request: Request,
    exception_id: int,
    exc_in: ExceptionUpdate,
    current_user: User = Depends(require_permission(Permission.EXCEPTION_MANAGE)),
    db: Session = Depends(get_db),
) -> Any:
    """Update details or parameters of an active or pending security exception."""
    try:
        updated = ExceptionService.update_exception(
            db=db,
            exception_id=exception_id,
            organization_id=current_user.organization_id,
            obj_in=exc_in,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Security exception not found in your organization.",
        )

    # Audit log
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="exception.update",
        resource_type="SECURITY_EXCEPTION",
        resource_id=str(exception_id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={"updated_fields": list(exc_in.model_dump(exclude_unset=True).keys())},
    )

    return ExceptionService.get_exception_by_id(
        db=db, exception_id=exception_id, organization_id=current_user.organization_id
    )


@router.post("/{exception_id}/submit-review", response_model=ExceptionResponse)
def submit_exception_for_review(
    request: Request,
    exception_id: int,
    current_user: User = Depends(require_permission(Permission.EXCEPTION_MANAGE)),
    db: Session = Depends(get_db),
) -> Any:
    """Submit a REQUESTED exception for formal security review."""
    try:
        updated = ExceptionService.submit_for_review(
            db=db,
            exception_id=exception_id,
            organization_id=current_user.organization_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Security exception not found in your organization.",
        )

    # Audit log
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="exception.submit_review",
        resource_type="SECURITY_EXCEPTION",
        resource_id=str(exception_id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
    )

    return ExceptionService.get_exception_by_id(
        db=db, exception_id=exception_id, organization_id=current_user.organization_id
    )


@router.post("/{exception_id}/approve", response_model=ExceptionResponse)
def approve_exception(
    request: Request,
    exception_id: int,
    action_in: ExceptionReviewAction,
    current_user: User = Depends(require_permission(Permission.EXCEPTION_APPROVE)),
    db: Session = Depends(get_db),
) -> Any:
    """Formally approve an exception with reviewer actor tracking and approval notes."""
    try:
        approved = ExceptionService.approve_exception(
            db=db,
            exception_id=exception_id,
            organization_id=current_user.organization_id,
            action_in=action_in,
            reviewer_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not approved:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Security exception not found in your organization.",
        )

    # Audit log
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="exception.approve",
        resource_type="SECURITY_EXCEPTION",
        resource_id=str(exception_id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={"approval_notes": action_in.approval_notes, "new_status": approved.status.value},
    )

    return ExceptionService.get_exception_by_id(
        db=db, exception_id=exception_id, organization_id=current_user.organization_id
    )


@router.post("/{exception_id}/reject", response_model=ExceptionResponse)
def reject_exception(
    request: Request,
    exception_id: int,
    action_in: ExceptionReviewAction,
    current_user: User = Depends(require_permission(Permission.EXCEPTION_APPROVE)),
    db: Session = Depends(get_db),
) -> Any:
    """Formally reject an exception with documented rejection reason."""
    try:
        rejected = ExceptionService.reject_exception(
            db=db,
            exception_id=exception_id,
            organization_id=current_user.organization_id,
            action_in=action_in,
            reviewer_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not rejected:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Security exception not found in your organization.",
        )

    # Audit log
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="exception.reject",
        resource_type="SECURITY_EXCEPTION",
        resource_id=str(exception_id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={"rejection_reason": action_in.rejection_reason},
    )

    return ExceptionService.get_exception_by_id(
        db=db, exception_id=exception_id, organization_id=current_user.organization_id
    )


@router.post("/{exception_id}/close", response_model=ExceptionResponse)
def close_exception(
    request: Request,
    exception_id: int,
    closure_in: ExceptionClosure,
    current_user: User = Depends(require_permission(Permission.EXCEPTION_MANAGE)),
    db: Session = Depends(get_db),
) -> Any:
    """Close an active or expired exception."""
    try:
        closed = ExceptionService.close_exception(
            db=db,
            exception_id=exception_id,
            organization_id=current_user.organization_id,
            closure_in=closure_in,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not closed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Security exception not found in your organization.",
        )

    # Audit log
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="exception.close",
        resource_type="SECURITY_EXCEPTION",
        resource_id=str(exception_id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={"closure_notes": closure_in.closure_notes},
    )

    return ExceptionService.get_exception_by_id(
        db=db, exception_id=exception_id, organization_id=current_user.organization_id
    )


@router.post("/{exception_id}/compensating-controls", response_model=ExceptionCompensatingControlResponse, status_code=status.HTTP_201_CREATED)
def link_compensating_control(
    request: Request,
    exception_id: int,
    link_in: ExceptionCompensatingControlCreate,
    current_user: User = Depends(require_permission(Permission.EXCEPTION_MANAGE)),
    db: Session = Depends(get_db),
) -> Any:
    """Link a compensating control to an exception."""
    try:
        link = ExceptionService.link_compensating_control(
            db=db,
            exception_id=exception_id,
            obj_in=link_in,
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
        action="exception.compensating_control.link",
        resource_type="EXCEPTION_COMPENSATING_CONTROL",
        resource_id=str(link.id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={"exception_id": exception_id, "control_id": link_in.organization_control_id},
    )

    return link


@router.delete("/{exception_id}/compensating-controls/{control_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_compensating_control(
    request: Request,
    exception_id: int,
    control_id: int,
    current_user: User = Depends(require_permission(Permission.EXCEPTION_MANAGE)),
    db: Session = Depends(get_db),
) -> None:
    """Unlink a compensating control from an exception."""
    try:
        success = ExceptionService.unlink_compensating_control(
            db=db,
            exception_id=exception_id,
            organization_control_id=control_id,
            organization_id=current_user.organization_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Compensating control linkage not found in your organization.",
        )

    # Audit log
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="exception.compensating_control.unlink",
        resource_type="EXCEPTION_COMPENSATING_CONTROL",
        resource_id=f"{exception_id}:{control_id}",
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
    )

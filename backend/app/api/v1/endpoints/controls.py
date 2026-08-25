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
from app.models.control import ImplementationStatusEnum, PriorityEnum
from app.models.user import User
from app.schemas.control import (
    OrganizationControlResponse,
    OrganizationControlUpdate,
)
from app.services.audit_service import AuditService
from app.services.control_service import ControlService
from app.services.user_service import UserService

router = APIRouter()


@router.get("", response_model=List[OrganizationControlResponse])
def list_controls(
    framework_id: Optional[int] = Query(None, description="Filter by framework ID"),
    function_id: Optional[int] = Query(None, description="Filter by function ID"),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    status: Optional[ImplementationStatusEnum] = Query(None, description="Filter by status"),
    priority: Optional[PriorityEnum] = Query(None, description="Filter by priority"),
    owner_id: Optional[int] = Query(None, description="Filter by assigned owner user ID"),
    search: Optional[str] = Query(None, description="Search keyword in identifier, title, or outcome statement"),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    current_user: User = Depends(require_permission(Permission.CONTROL_READ)),
    db: Session = Depends(get_db),
) -> Any:
    """List organization controls with implementation state, filtered and searched."""
    return ControlService.list_controls(
        db=db,
        organization_id=current_user.organization_id,
        framework_id=framework_id,
        function_id=function_id,
        category_id=category_id,
        status=status,
        priority=priority,
        owner_id=owner_id,
        search=search,
        skip=skip,
        limit=limit,
    )


@router.get("/{control_id}", response_model=OrganizationControlResponse)
def get_control(
    control_id: int,
    current_user: User = Depends(require_permission(Permission.CONTROL_READ)),
    db: Session = Depends(get_db),
) -> Any:
    """Retrieve details of a specific organization control."""
    ctrl = ControlService.get_control_by_id(
        db=db, control_id=control_id, organization_id=current_user.organization_id
    )
    if not ctrl:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Control not found in your organization",
        )
    return ctrl


@router.patch("/{control_id}", response_model=OrganizationControlResponse)
def update_control(
    request: Request,
    control_id: int,
    control_in: OrganizationControlUpdate,
    current_user: User = Depends(require_permission(Permission.CONTROL_ASSESS)),
    db: Session = Depends(get_db),
) -> Any:
    """Update organization control implementation state, owner, priority, or notes."""
    existing_ctrl = ControlService.get_control_by_id(
        db=db, control_id=control_id, organization_id=current_user.organization_id
    )
    if not existing_ctrl:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Control not found in your organization",
        )

    # If owner is specified, verify owner belongs to caller's organization
    if control_in.owner_id is not None:
        owner_user = UserService.get_by_id(
            db, user_id=control_in.owner_id, organization_id=current_user.organization_id
        )
        if not owner_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigned owner does not belong to your organization",
            )

    updated_ctrl = ControlService.update_control(
        db=db,
        control_id=control_id,
        organization_id=current_user.organization_id,
        obj_in=control_in,
    )

    # Audit log
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    action_type = "control.update"
    if control_in.status is not None and control_in.status != existing_ctrl["status"]:
        action_type = "control.status.change"

    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action=action_type,
        resource_type="CONTROL",
        resource_id=str(control_id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={
            "subcategory": existing_ctrl["subcategory"].identifier,
            "updated_fields": list(control_in.model_dump(exclude_unset=True).keys()),
            "new_status": control_in.status.value if control_in.status else None,
        },
    )

    # Return refreshed full view
    return ControlService.get_control_by_id(
        db=db, control_id=control_id, organization_id=current_user.organization_id
    )
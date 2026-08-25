from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_client_ip,
    get_current_user,
    get_db,
    get_user_agent,
    require_permission,
    require_roles,
)
from app.core.permissions import Permission, RoleEnum
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.audit_service import AuditService
from app.services.user_service import UserService

router = APIRouter()


@router.get("", response_model=List[UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_permission(Permission.USER_READ)),
    db: Session = Depends(get_db),
) -> Any:
    """Retrieve users belonging strictly to the caller's organization."""
    return UserService.list_by_organization(
        db=db, organization_id=current_user.organization_id, skip=skip, limit=limit
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    request: Request,
    user_in: UserCreate,
    current_user: User = Depends(require_permission(Permission.USER_CREATE)),
    db: Session = Depends(get_db),
) -> Any:
    """Create a new user within the caller's organization."""
    existing = UserService.get_by_email(db, email=user_in.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists",
        )

    # Force user to belong to current user's organization to prevent cross-tenant creation
    target_org_id = current_user.organization_id
    new_user = UserService.create(db=db, obj_in=user_in, organization_id=target_org_id)

    # Audit log
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="user.create",
        resource_type="USER",
        resource_id=str(new_user.id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={"created_email": new_user.email, "role": new_user.role.value},
    )

    return new_user


@router.get("/{user_id}", response_model=UserResponse)
def get_user_by_id(
    user_id: int,
    current_user: User = Depends(require_permission(Permission.USER_READ)),
    db: Session = Depends(get_db),
) -> Any:
    """Retrieve a specific user within the caller's organization."""
    user = UserService.get_by_id(
        db=db, user_id=user_id, organization_id=current_user.organization_id
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in your organization",
        )
    return user


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    request: Request,
    user_id: int,
    user_in: UserUpdate,
    current_user: User = Depends(require_permission(Permission.USER_UPDATE)),
    db: Session = Depends(get_db),
) -> Any:
    """Update a user within the caller's organization."""
    db_user = UserService.get_by_id(
        db=db, user_id=user_id, organization_id=current_user.organization_id
    )
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in your organization",
        )

    updated_user = UserService.update(db=db, db_user=db_user, obj_in=user_in)

    # Audit log
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="user.update",
        resource_type="USER",
        resource_id=str(updated_user.id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={"updated_fields": list(user_in.model_dump(exclude_unset=True).keys())},
    )

    return updated_user
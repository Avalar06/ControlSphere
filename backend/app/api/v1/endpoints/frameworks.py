from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db, require_permission
from app.core.permissions import Permission
from app.models.user import User
from app.schemas.control import FrameworkProgressResponse
from app.schemas.framework import FrameworkResponse, FrameworkTreeResponse
from app.services.control_service import ControlService
from app.services.framework_service import FrameworkService

router = APIRouter()


@router.get("", response_model=List[FrameworkResponse])
def list_frameworks(
    current_user: User = Depends(require_permission(Permission.FRAMEWORK_READ)),
    db: Session = Depends(get_db),
) -> Any:
    """List all supported compliance frameworks."""
    return FrameworkService.list_frameworks(db)


@router.get("/{framework_id}", response_model=FrameworkResponse)
def get_framework(
    framework_id: int,
    current_user: User = Depends(require_permission(Permission.FRAMEWORK_READ)),
    db: Session = Depends(get_db),
) -> Any:
    """Retrieve details for a specific framework."""
    frameworks = FrameworkService.list_frameworks(db)
    for fw in frameworks:
        if fw["id"] == framework_id:
            return fw
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Framework not found",
    )


@router.get("/{framework_id}/tree", response_model=FrameworkTreeResponse)
def get_framework_tree(
    framework_id: int,
    current_user: User = Depends(require_permission(Permission.FRAMEWORK_READ)),
    db: Session = Depends(get_db),
) -> Any:
    """Retrieve the full hierarchical taxonomy tree of a framework."""
    fw_tree = FrameworkService.get_tree(db, framework_id=framework_id)
    if not fw_tree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Framework not found",
        )
    return fw_tree


@router.get("/{framework_id}/progress", response_model=FrameworkProgressResponse)
def get_framework_progress(
    framework_id: int,
    current_user: User = Depends(require_permission(Permission.FRAMEWORK_READ)),
    db: Session = Depends(get_db),
) -> Any:
    """Calculate deterministic organization progress and compliance score for a framework."""
    progress = ControlService.calculate_framework_progress(
        db, framework_id=framework_id, organization_id=current_user.organization_id
    )
    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Framework not found",
        )
    return progress
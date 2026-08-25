from typing import Any, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_user,
    get_db,
    require_permission,
)
from app.core.permissions import Permission
from app.models.user import User
from app.schemas.audit_log import AuditLogResponse
from app.services.audit_service import AuditService

router = APIRouter()


@router.get("", response_model=List[AuditLogResponse])
def list_audit_logs(
    action: Optional[str] = Query(None, description="Filter by action string"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    actor_email: Optional[str] = Query(None, description="Filter by actor email"),
    status: Optional[str] = Query(None, description="Filter by status (SUCCESS, FAILURE, etc)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_permission(Permission.AUDIT_LOG_READ)),
    db: Session = Depends(get_db),
) -> Any:
    """Retrieve immutable audit logs for the caller's organization."""
    return AuditService.list_logs_for_org(
        db=db,
        organization_id=current_user.organization_id,
        action=action,
        resource_type=resource_type,
        actor_email=actor_email,
        status=status,
        limit=limit,
        offset=offset,
    )
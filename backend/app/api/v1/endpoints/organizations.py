from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_client_ip,
    get_current_user,
    get_db,
    get_user_agent,
    require_permission,
)
from app.core.permissions import Permission
from app.models.user import User
from app.schemas.organization import OrganizationResponse, OrganizationUpdate
from app.services.audit_service import AuditService
from app.services.organization_service import OrganizationService

router = APIRouter()


@router.get("/me", response_model=OrganizationResponse)
def get_my_organization(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Retrieve details of the caller's current organization."""
    org = OrganizationService.get_by_id(db, org_id=current_user.organization_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
    return org


@router.patch("/me", response_model=OrganizationResponse)
def update_my_organization(
    request: Request,
    org_in: OrganizationUpdate,
    current_user: User = Depends(require_permission(Permission.ORG_UPDATE)),
    db: Session = Depends(get_db),
) -> Any:
    """Update details of the caller's current organization."""
    org = OrganizationService.get_by_id(db, org_id=current_user.organization_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    updated_org = OrganizationService.update(db, db_org=org, obj_in=org_in)

    # Audit log
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="organization.update",
        resource_type="ORGANIZATION",
        resource_id=str(updated_org.id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={"updated_fields": list(org_in.model_dump(exclude_unset=True).keys())},
    )

    return updated_org
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
from app.models.policy import PolicyStatusEnum, PolicyTypeEnum
from app.models.user import User
from app.schemas.policy import (
    PolicyControlMappingCreate,
    PolicyCreate,
    PolicyResponse,
    PolicyStatusUpdate,
    PolicyUpdate,
    PolicyVersionCreate,
    PolicyVersionResponse,
)
from app.services.audit_service import AuditService
from app.services.policy_service import PolicyService
from app.services.user_service import UserService

router = APIRouter()


@router.get("", response_model=List[PolicyResponse])
def list_policies(
    status: Optional[PolicyStatusEnum] = Query(None, description="Filter by status"),
    policy_type: Optional[PolicyTypeEnum] = Query(None, description="Filter by policy type"),
    owner_id: Optional[int] = Query(None, description="Filter by policy owner ID"),
    search: Optional[str] = Query(None, description="Search keyword in title or description"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(require_permission(Permission.POLICY_READ)),
    db: Session = Depends(get_db),
) -> Any:
    """List organization policies with version summaries and mapped controls."""
    return PolicyService.list_policies(
        db=db,
        organization_id=current_user.organization_id,
        status=status,
        policy_type=policy_type,
        owner_id=owner_id,
        search=search,
        skip=skip,
        limit=limit,
    )


@router.post("", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
def create_policy(
    request: Request,
    policy_in: PolicyCreate,
    current_user: User = Depends(require_permission(Permission.POLICY_MANAGE)),
    db: Session = Depends(get_db),
) -> Any:
    """Create a new policy with initial draft version v1."""
    if policy_in.owner_id is not None:
        owner_user = UserService.get_by_id(
            db, user_id=policy_in.owner_id, organization_id=current_user.organization_id
        )
        if not owner_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigned owner does not belong to your organization",
            )

    new_pol = PolicyService.create_policy(
        db=db,
        obj_in=policy_in,
        organization_id=current_user.organization_id,
        created_by_id=current_user.id,
    )

    # Audit log
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="policy.create",
        resource_type="POLICY",
        resource_id=str(new_pol.id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={"title": new_pol.title, "type": new_pol.policy_type.value},
    )

    return PolicyService.get_policy_by_id(
        db=db, policy_id=new_pol.id, organization_id=current_user.organization_id
    )


@router.get("/{policy_id}", response_model=PolicyResponse)
def get_policy(
    policy_id: int,
    current_user: User = Depends(require_permission(Permission.POLICY_READ)),
    db: Session = Depends(get_db),
) -> Any:
    """Retrieve full details of a policy, including versions and mapped controls."""
    pol = PolicyService.get_policy_by_id(
        db=db, policy_id=policy_id, organization_id=current_user.organization_id
    )
    if not pol:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found in your organization",
        )
    return pol


@router.patch("/{policy_id}", response_model=PolicyResponse)
def update_policy(
    request: Request,
    policy_id: int,
    policy_in: PolicyUpdate,
    current_user: User = Depends(require_permission(Permission.POLICY_MANAGE)),
    db: Session = Depends(get_db),
) -> Any:
    """Update policy metadata (title, description, dates, owner)."""
    existing_pol = PolicyService.get_policy_by_id(
        db=db, policy_id=policy_id, organization_id=current_user.organization_id
    )
    if not existing_pol:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found in your organization",
        )

    if policy_in.owner_id is not None:
        owner_user = UserService.get_by_id(
            db, user_id=policy_in.owner_id, organization_id=current_user.organization_id
        )
        if not owner_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigned owner does not belong to your organization",
            )

    updated_pol = PolicyService.update_policy(
        db=db,
        policy_id=policy_id,
        organization_id=current_user.organization_id,
        obj_in=policy_in,
    )

    # Audit log
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="policy.update",
        resource_type="POLICY",
        resource_id=str(policy_id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={"updated_fields": list(policy_in.model_dump(exclude_unset=True).keys())},
    )

    return PolicyService.get_policy_by_id(
        db=db, policy_id=policy_id, organization_id=current_user.organization_id
    )


@router.post("/{policy_id}/versions", response_model=PolicyVersionResponse, status_code=status.HTTP_201_CREATED)
def create_policy_version(
    request: Request,
    policy_id: int,
    version_in: PolicyVersionCreate,
    current_user: User = Depends(require_permission(Permission.POLICY_MANAGE)),
    db: Session = Depends(get_db),
) -> Any:
    """Create a new immutable version for an existing policy."""
    existing_pol = PolicyService.get_policy_by_id(
        db=db, policy_id=policy_id, organization_id=current_user.organization_id
    )
    if not existing_pol:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found in your organization",
        )

    ver = PolicyService.create_policy_version(
        db=db,
        policy_id=policy_id,
        organization_id=current_user.organization_id,
        obj_in=version_in,
        created_by_id=current_user.id,
    )

    # Audit log
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="policy.version.create",
        resource_type="POLICY_VERSION",
        resource_id=str(ver.id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={"policy_id": policy_id, "version_number": ver.version_number, "change_summary": ver.change_summary},
    )

    return ver


@router.post("/{policy_id}/status", response_model=PolicyResponse)
def update_policy_status(
    request: Request,
    policy_id: int,
    status_in: PolicyStatusUpdate,
    current_user: User = Depends(require_permission(Permission.POLICY_MANAGE)),
    db: Session = Depends(get_db),
) -> Any:
    """Advance or transition the lifecycle status of a policy (e.g. approve, publish, archive)."""
    try:
        updated_pol = PolicyService.update_policy_status(
            db=db,
            policy_id=policy_id,
            organization_id=current_user.organization_id,
            new_status=status_in.status,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    if not updated_pol:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found in your organization",
        )

    # Specific audit action based on status transition
    action_map = {
        PolicyStatusEnum.APPROVED: "policy.approve",
        PolicyStatusEnum.PUBLISHED: "policy.publish",
        PolicyStatusEnum.ARCHIVED: "policy.archive",
        PolicyStatusEnum.UNDER_REVIEW: "policy.submit_review",
        PolicyStatusEnum.DRAFT: "policy.draft",
    }
    action_name = action_map.get(status_in.status, "policy.status.change")

    # Audit log
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action=action_name,
        resource_type="POLICY",
        resource_id=str(policy_id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={"new_status": status_in.status.value, "reason": status_in.reason},
    )

    return PolicyService.get_policy_by_id(
        db=db, policy_id=policy_id, organization_id=current_user.organization_id
    )


@router.post("/{policy_id}/mappings", response_model=PolicyResponse)
def add_policy_control_mapping(
    request: Request,
    policy_id: int,
    mapping_in: PolicyControlMappingCreate,
    current_user: User = Depends(require_permission(Permission.POLICY_MANAGE)),
    db: Session = Depends(get_db),
) -> Any:
    """Map a policy to a framework subcategory control outcome."""
    try:
        mapping = PolicyService.add_control_mapping(
            db=db,
            policy_id=policy_id,
            organization_id=current_user.organization_id,
            subcategory_id=mapping_in.subcategory_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found in your organization",
        )

    # Audit log
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="policy.mapping.create",
        resource_type="POLICY_MAPPING",
        resource_id=str(mapping.id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={"policy_id": policy_id, "subcategory_id": mapping_in.subcategory_id},
    )

    return PolicyService.get_policy_by_id(
        db=db, policy_id=policy_id, organization_id=current_user.organization_id
    )


@router.delete("/{policy_id}/mappings/{subcategory_id}", response_model=PolicyResponse)
def remove_policy_control_mapping(
    request: Request,
    policy_id: int,
    subcategory_id: int,
    current_user: User = Depends(require_permission(Permission.POLICY_MANAGE)),
    db: Session = Depends(get_db),
) -> Any:
    """Remove a policy-to-control mapping."""
    success = PolicyService.remove_control_mapping(
        db=db,
        policy_id=policy_id,
        organization_id=current_user.organization_id,
        subcategory_id=subcategory_id,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapping not found",
        )

    # Audit log
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="policy.mapping.delete",
        resource_type="POLICY_MAPPING",
        resource_id=f"{policy_id}:{subcategory_id}",
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={"policy_id": policy_id, "subcategory_id": subcategory_id},
    )

    return PolicyService.get_policy_by_id(
        db=db, policy_id=policy_id, organization_id=current_user.organization_id
    )
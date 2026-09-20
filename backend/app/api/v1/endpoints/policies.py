from typing import Any, Dict, List, Optional
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
from app.models.policy import CampaignStatusEnum, PolicyStatusEnum, PolicyTypeEnum
from app.models.user import User
from app.schemas.policy import (
    CampaignEvidenceManifestResponse,
    PolicyAttestationCampaignCreate,
    PolicyAttestationCampaignResponse,
    PolicyAttestationCampaignUpdate,
    PolicyControlMappingCreate,
    PolicyCreate,
    PolicyResponse,
    PolicyReviewWorkflowAction,
    PolicyReviewWorkflowCreate,
    PolicyReviewWorkflowResponse,
    PolicyStatusUpdate,
    PolicyUpdate,
    PolicyVersionCreate,
    PolicyVersionResponse,
    PolicyVersionUpdate,
    UserAttestationRecordResponse,
    UserAttestationSubmit,
)
from app.services.audit_service import AuditService
from app.services.policy_service import PolicyService
from app.services.user_service import UserService

router = APIRouter()


# ── Policy Collection Endpoints ─────────────────────────────────────────────

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
    """Create a new policy with initial draft version v1 and canonical content hash."""
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


# ── Static Path Endpoints (MUST be registered before /{policy_id}) ──────────

@router.get("/my-pending-attestations", response_model=List[UserAttestationRecordResponse])
def get_my_pending_attestations(
    current_user: User = Depends(require_permission(Permission.POLICY_ATTEST)),
    db: Session = Depends(get_db),
) -> Any:
    """List pending policy attestations assigned to the authenticated user."""
    return PolicyService.get_user_pending_attestations(
        db=db,
        user_id=current_user.id,
        organization_id=current_user.organization_id,
    )


@router.get("/campaigns", response_model=List[PolicyAttestationCampaignResponse])
def list_campaigns(
    policy_id: Optional[int] = Query(None, description="Filter by policy ID"),
    campaign_status: Optional[CampaignStatusEnum] = Query(None, alias="status", description="Filter by campaign status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(require_permission(Permission.POLICY_READ)),
    db: Session = Depends(get_db),
) -> Any:
    """List workforce attestation campaigns in the organization."""
    campaigns = PolicyService.list_campaigns(
        db=db,
        organization_id=current_user.organization_id,
        policy_id=policy_id,
        status=campaign_status,
        skip=skip,
        limit=limit,
    )
    results = []
    for c in campaigns:
        rate = round((c.completed_count / c.total_targeted_count * 100), 2) if c.total_targeted_count else 0.0
        results.append({
            "id": c.id,
            "organization_id": c.organization_id,
            "campaign_code": c.campaign_code,
            "title": c.title,
            "description": c.description,
            "policy_id": c.policy_id,
            "version_id": c.version_id,
            "policy_version_hash": c.policy_version_hash,
            "target_type": c.target_type,
            "target_role": c.target_role,
            "due_date": c.due_date,
            "grace_period_days": c.grace_period_days,
            "status": c.status,
            "assessment_id": c.assessment_id,
            "total_targeted_count": c.total_targeted_count,
            "completed_count": c.completed_count,
            "completion_rate": rate,
            "created_by_id": c.created_by_id,
            "launched_at": c.launched_at,
            "closed_at": c.closed_at,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
            "policy_title": c.policy.title if c.policy else None,
            "policy_version_number": c.version.version_number if c.version else None,
        })
    return results


@router.post("/campaigns", response_model=PolicyAttestationCampaignResponse, status_code=status.HTTP_201_CREATED)
def create_campaign(
    request: Request,
    campaign_in: PolicyAttestationCampaignCreate,
    current_user: User = Depends(require_permission(Permission.POLICY_CAMPAIGN_MANAGE)),
    db: Session = Depends(get_db),
) -> Any:
    """Create a new attestation campaign in DRAFT status bound to an immutable policy version hash."""
    try:
        c = PolicyService.create_campaign(
            db=db,
            campaign_in=campaign_in,
            organization_id=current_user.organization_id,
            current_user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="policy.campaign.create",
        resource_type="POLICY_CAMPAIGN",
        resource_id=str(c.id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={"campaign_code": c.campaign_code, "policy_id": c.policy_id, "version_id": c.version_id},
    )

    return {
        "id": c.id,
        "organization_id": c.organization_id,
        "campaign_code": c.campaign_code,
        "title": c.title,
        "description": c.description,
        "policy_id": c.policy_id,
        "version_id": c.version_id,
        "policy_version_hash": c.policy_version_hash,
        "target_type": c.target_type,
        "target_role": c.target_role,
        "due_date": c.due_date,
        "grace_period_days": c.grace_period_days,
        "status": c.status,
        "assessment_id": c.assessment_id,
        "total_targeted_count": c.total_targeted_count,
        "completed_count": c.completed_count,
        "completion_rate": 0.0,
        "created_by_id": c.created_by_id,
        "launched_at": c.launched_at,
        "closed_at": c.closed_at,
        "created_at": c.created_at,
        "updated_at": c.updated_at,
    }


@router.get("/campaigns/{campaign_id}", response_model=PolicyAttestationCampaignResponse)
def get_campaign(
    campaign_id: int,
    current_user: User = Depends(require_permission(Permission.POLICY_READ)),
    db: Session = Depends(get_db),
) -> Any:
    """Retrieve attestation campaign details and progress telemetry."""
    c = PolicyService.get_campaign(db, campaign_id=campaign_id, organization_id=current_user.organization_id)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found in your organization")

    rate = round((c.completed_count / c.total_targeted_count * 100), 2) if c.total_targeted_count else 0.0
    return {
        "id": c.id,
        "organization_id": c.organization_id,
        "campaign_code": c.campaign_code,
        "title": c.title,
        "description": c.description,
        "policy_id": c.policy_id,
        "version_id": c.version_id,
        "policy_version_hash": c.policy_version_hash,
        "target_type": c.target_type,
        "target_role": c.target_role,
        "due_date": c.due_date,
        "grace_period_days": c.grace_period_days,
        "status": c.status,
        "assessment_id": c.assessment_id,
        "total_targeted_count": c.total_targeted_count,
        "completed_count": c.completed_count,
        "completion_rate": rate,
        "created_by_id": c.created_by_id,
        "launched_at": c.launched_at,
        "closed_at": c.closed_at,
        "created_at": c.created_at,
        "updated_at": c.updated_at,
        "policy_title": c.policy.title if c.policy else None,
        "policy_version_number": c.version.version_number if c.version else None,
    }


@router.patch("/campaigns/{campaign_id}", response_model=PolicyAttestationCampaignResponse)
def update_campaign(
    request: Request,
    campaign_id: int,
    campaign_in: PolicyAttestationCampaignUpdate,
    current_user: User = Depends(require_permission(Permission.POLICY_CAMPAIGN_MANAGE)),
    db: Session = Depends(get_db),
) -> Any:
    """Update campaign metadata while in DRAFT status. Policy bindings are frozen."""
    try:
        c = PolicyService.update_campaign(
            db=db,
            campaign_id=campaign_id,
            organization_id=current_user.organization_id,
            campaign_in=campaign_in,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="policy.campaign.update",
        resource_type="POLICY_CAMPAIGN",
        resource_id=str(campaign_id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={"updated_fields": list(campaign_in.model_dump(exclude_unset=True).keys())},
    )

    rate = round((c.completed_count / c.total_targeted_count * 100), 2) if c.total_targeted_count else 0.0
    return {
        "id": c.id,
        "organization_id": c.organization_id,
        "campaign_code": c.campaign_code,
        "title": c.title,
        "description": c.description,
        "policy_id": c.policy_id,
        "version_id": c.version_id,
        "policy_version_hash": c.policy_version_hash,
        "target_type": c.target_type,
        "target_role": c.target_role,
        "due_date": c.due_date,
        "grace_period_days": c.grace_period_days,
        "status": c.status,
        "assessment_id": c.assessment_id,
        "total_targeted_count": c.total_targeted_count,
        "completed_count": c.completed_count,
        "completion_rate": rate,
        "created_by_id": c.created_by_id,
        "launched_at": c.launched_at,
        "closed_at": c.closed_at,
        "created_at": c.created_at,
        "updated_at": c.updated_at,
        "policy_title": c.policy.title if c.policy else None,
        "policy_version_number": c.version.version_number if c.version else None,
    }


@router.post("/campaigns/{campaign_id}/launch", response_model=PolicyAttestationCampaignResponse)
def launch_campaign(
    request: Request,
    campaign_id: int,
    current_user: User = Depends(require_permission(Permission.POLICY_CAMPAIGN_MANAGE)),
    db: Session = Depends(get_db),
) -> Any:
    """Launch attestation campaign: enumerates target population and creates pending user attestation records."""
    try:
        c = PolicyService.launch_campaign(
            db=db,
            campaign_id=campaign_id,
            organization_id=current_user.organization_id,
            current_user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="policy.campaign.launch",
        resource_type="POLICY_CAMPAIGN",
        resource_id=str(campaign_id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={"campaign_code": c.campaign_code, "total_targeted": c.total_targeted_count},
    )

    return {
        "id": c.id,
        "organization_id": c.organization_id,
        "campaign_code": c.campaign_code,
        "title": c.title,
        "description": c.description,
        "policy_id": c.policy_id,
        "version_id": c.version_id,
        "policy_version_hash": c.policy_version_hash,
        "target_type": c.target_type,
        "target_role": c.target_role,
        "due_date": c.due_date,
        "grace_period_days": c.grace_period_days,
        "status": c.status,
        "assessment_id": c.assessment_id,
        "total_targeted_count": c.total_targeted_count,
        "completed_count": c.completed_count,
        "completion_rate": 0.0,
        "created_by_id": c.created_by_id,
        "launched_at": c.launched_at,
        "closed_at": c.closed_at,
        "created_at": c.created_at,
        "updated_at": c.updated_at,
    }


@router.post("/campaigns/{campaign_id}/close", response_model=PolicyAttestationCampaignResponse)
def close_campaign(
    request: Request,
    campaign_id: int,
    current_user: User = Depends(require_permission(Permission.POLICY_APPROVE)),
    db: Session = Depends(get_db),
) -> Any:
    """Close an active attestation campaign. Restricted to ADMIN and MANAGER."""
    try:
        c = PolicyService.close_campaign(
            db=db,
            campaign_id=campaign_id,
            organization_id=current_user.organization_id,
            current_user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="policy.campaign.close",
        resource_type="POLICY_CAMPAIGN",
        resource_id=str(campaign_id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={"campaign_code": c.campaign_code, "completed_count": c.completed_count},
    )

    rate = round((c.completed_count / c.total_targeted_count * 100), 2) if c.total_targeted_count else 0.0
    return {
        "id": c.id,
        "organization_id": c.organization_id,
        "campaign_code": c.campaign_code,
        "title": c.title,
        "description": c.description,
        "policy_id": c.policy_id,
        "version_id": c.version_id,
        "policy_version_hash": c.policy_version_hash,
        "target_type": c.target_type,
        "target_role": c.target_role,
        "due_date": c.due_date,
        "grace_period_days": c.grace_period_days,
        "status": c.status,
        "assessment_id": c.assessment_id,
        "total_targeted_count": c.total_targeted_count,
        "completed_count": c.completed_count,
        "completion_rate": rate,
        "created_by_id": c.created_by_id,
        "launched_at": c.launched_at,
        "closed_at": c.closed_at,
        "created_at": c.created_at,
        "updated_at": c.updated_at,
    }


@router.post("/campaigns/{campaign_id}/attest", response_model=UserAttestationRecordResponse)
def submit_attestation(
    request: Request,
    campaign_id: int,
    attest_in: UserAttestationSubmit,
    current_user: User = Depends(require_permission(Permission.POLICY_ATTEST)),
    db: Session = Depends(get_db),
) -> Any:
    """Submit personal policy attestation for the authenticated user, generating a cryptographic attestation digest."""
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    try:
        rec = PolicyService.submit_user_attestation(
            db=db,
            campaign_id=campaign_id,
            organization_id=current_user.organization_id,
            current_user_id=current_user.id,
            attest_in=attest_in,
            client_ip=ip,
            client_ua=ua,
        )
    except ValueError as e:
        err_msg = str(e)
        if "Duplicate attestation" in err_msg:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=err_msg)
        elif "not assigned" in err_msg or "not found" in err_msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err_msg)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)

    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="policy.attestation.submit",
        resource_type="USER_ATTESTATION",
        resource_id=str(rec.id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={"campaign_id": campaign_id, "receipt_hash": rec.attestation_receipt_hash},
    )

    return rec


@router.post("/campaigns/{campaign_id}/evidence", response_model=CampaignEvidenceManifestResponse)
def generate_campaign_evidence(
    request: Request,
    campaign_id: int,
    current_user: User = Depends(require_permission(Permission.POLICY_CAMPAIGN_MANAGE)),
    db: Session = Depends(get_db),
) -> Any:
    """Generate a tamper-evident campaign attestation manifest and create a Phase 3 EvidenceItem in UPLOADED status."""
    try:
        evidence = PolicyService.generate_campaign_evidence(
            db=db,
            campaign_id=campaign_id,
            organization_id=current_user.organization_id,
            current_user_id=current_user.id,
        )
    except ValueError as e:
        err_msg = str(e)
        if "not found" in err_msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)

    campaign = PolicyService.get_campaign(db, campaign_id, current_user.organization_id)
    rate = round((campaign.completed_count / campaign.total_targeted_count * 100), 2) if campaign.total_targeted_count else 0.0

    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="policy.evidence.generate",
        resource_type="EVIDENCE_ITEM",
        resource_id=str(evidence.id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={"campaign_id": campaign_id, "manifest_sha256": evidence.sha256_hash},
    )

    return {
        "campaign_id": campaign_id,
        "campaign_code": campaign.campaign_code,
        "evidence_item_id": evidence.id,
        "sha256_hash": evidence.sha256_hash,
        "status": evidence.status.value,
        "total_targeted": campaign.total_targeted_count,
        "total_completed": campaign.completed_count,
        "completion_rate": rate,
    }


# ── Parametric Policy Endpoints (/{policy_id} and subresources) ────────────

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

    try:
        updated_pol = PolicyService.update_policy(
            db=db,
            policy_id=policy_id,
            organization_id=current_user.organization_id,
            obj_in=policy_in,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

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


@router.post("/{policy_id}/status", response_model=PolicyResponse)
def update_policy_status(
    request: Request,
    policy_id: int,
    status_in: PolicyStatusUpdate,
    current_user: User = Depends(require_permission(Permission.POLICY_MANAGE)),
    db: Session = Depends(get_db),
) -> Any:
    """Advance or transition the lifecycle status of a policy."""
    try:
        updated_pol = PolicyService.update_policy_status(
            db=db,
            policy_id=policy_id,
            organization_id=current_user.organization_id,
            new_status=status_in.status,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not updated_pol:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found in your organization")

    # Specific audit action based on status transition
    action_map = {
        PolicyStatusEnum.APPROVED: "policy.approve",
        PolicyStatusEnum.PUBLISHED: "policy.publish",
        PolicyStatusEnum.ARCHIVED: "policy.archive",
        PolicyStatusEnum.UNDER_REVIEW: "policy.submit_review",
        PolicyStatusEnum.DRAFT: "policy.draft",
    }
    action_name = action_map.get(status_in.status, "policy.status.change")

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


# ── Policy Version Endpoints ────────────────────────────────────────────────

@router.get("/{policy_id}/versions", response_model=List[PolicyVersionResponse])
def list_policy_versions(
    policy_id: int,
    current_user: User = Depends(require_permission(Permission.POLICY_READ)),
    db: Session = Depends(get_db),
) -> Any:
    """List all versions for a policy, including canonical hash and approval metadata."""
    try:
        return PolicyService.list_policy_versions(
            db=db, policy_id=policy_id, organization_id=current_user.organization_id
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{policy_id}/versions", response_model=PolicyVersionResponse, status_code=status.HTTP_201_CREATED)
def create_policy_version(
    request: Request,
    policy_id: int,
    version_in: PolicyVersionCreate,
    current_user: User = Depends(require_permission(Permission.POLICY_MANAGE)),
    db: Session = Depends(get_db),
) -> Any:
    """Create a new incremented version in DRAFT status with canonical SHA-256 hash."""
    try:
        ver = PolicyService.create_policy_version(
            db=db,
            policy_id=policy_id,
            organization_id=current_user.organization_id,
            obj_in=version_in,
            created_by_id=current_user.id,
        )
    except ValueError as e:
        err_msg = str(e)
        if "not found" in err_msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)

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
        details={"policy_id": policy_id, "version_number": ver.version_number, "content_hash": ver.content_hash_sha256},
    )

    return ver


@router.get("/{policy_id}/versions/{version_id}", response_model=PolicyVersionResponse)
def get_policy_version(
    policy_id: int,
    version_id: int,
    current_user: User = Depends(require_permission(Permission.POLICY_READ)),
    db: Session = Depends(get_db),
) -> Any:
    """Retrieve details of a single policy version."""
    ver = PolicyService.get_policy_version(
        db=db, policy_id=policy_id, version_id=version_id, organization_id=current_user.organization_id
    )
    if not ver:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy version not found in your organization")
    return ver


@router.patch("/{policy_id}/versions/{version_id}", response_model=PolicyVersionResponse)
def update_policy_version(
    request: Request,
    policy_id: int,
    version_id: int,
    version_in: PolicyVersionUpdate,
    current_user: User = Depends(require_permission(Permission.POLICY_MANAGE)),
    db: Session = Depends(get_db),
) -> Any:
    """Update a policy version while in DRAFT status. Once submitted or approved, versions are strictly immutable."""
    try:
        ver = PolicyService.update_policy_version(
            db=db,
            policy_id=policy_id,
            version_id=version_id,
            organization_id=current_user.organization_id,
            obj_in=version_in,
        )
    except ValueError as e:
        err_msg = str(e)
        if "not found" in err_msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)

    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="policy.version.update",
        resource_type="POLICY_VERSION",
        resource_id=str(ver.id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={"version_number": ver.version_number, "content_hash": ver.content_hash_sha256},
    )

    return ver


@router.post("/{policy_id}/versions/{version_id}/submit-review", response_model=PolicyReviewWorkflowResponse)
def submit_version_for_review(
    request: Request,
    policy_id: int,
    version_id: int,
    review_in: PolicyReviewWorkflowCreate,
    current_user: User = Depends(require_permission(Permission.POLICY_MANAGE)),
    db: Session = Depends(get_db),
) -> Any:
    """Submit a DRAFT policy version into formal review workflow, locking content from further mutation."""
    try:
        ver, wf = PolicyService.submit_version_for_review(
            db=db,
            policy_id=policy_id,
            version_id=version_id,
            organization_id=current_user.organization_id,
            review_in=review_in,
            current_user_id=current_user.id,
        )
    except ValueError as e:
        err_msg = str(e)
        if "not found" in err_msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)

    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="policy.version.submit_review",
        resource_type="POLICY_REVIEW_WORKFLOW",
        resource_id=str(wf.id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={"version_id": version_id, "workflow_code": wf.workflow_code, "stage": wf.review_stage.value},
    )

    return wf


@router.post("/{policy_id}/versions/{version_id}/review/{workflow_id}", response_model=PolicyReviewWorkflowResponse)
def review_policy_version_workflow(
    request: Request,
    policy_id: int,
    version_id: int,
    workflow_id: int,
    action_in: PolicyReviewWorkflowAction,
    current_user: User = Depends(require_permission(Permission.POLICY_APPROVE)),
    db: Session = Depends(get_db),
) -> Any:
    """Approve or reject a policy version review workflow. Enforces strict Four-Eyes SoD (author cannot approve)."""
    try:
        ver, wf = PolicyService.review_policy_version_workflow(
            db=db,
            policy_id=policy_id,
            version_id=version_id,
            workflow_id=workflow_id,
            organization_id=current_user.organization_id,
            action_in=action_in,
            current_user_id=current_user.id,
        )
    except ValueError as e:
        err_msg = str(e)
        if "Four-Eyes Violation" in err_msg:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)
        if "not found" in err_msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)

    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action=f"policy.version.{action_in.decision.lower()}",
        resource_type="POLICY_REVIEW_WORKFLOW",
        resource_id=str(wf.id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={"version_id": version_id, "decision": action_in.decision, "approved_by_id": current_user.id},
    )

    return wf


@router.post("/{policy_id}/versions/{version_id}/publish", response_model=PolicyVersionResponse)
def publish_policy_version(
    request: Request,
    policy_id: int,
    version_id: int,
    current_user: User = Depends(require_permission(Permission.POLICY_MANAGE)),
    db: Session = Depends(get_db),
) -> Any:
    """Publish an APPROVED policy version, superseding any previously published versions."""
    try:
        ver = PolicyService.publish_policy_version(
            db=db,
            policy_id=policy_id,
            version_id=version_id,
            organization_id=current_user.organization_id,
            current_user_id=current_user.id,
        )
    except ValueError as e:
        err_msg = str(e)
        if "not found" in err_msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)

    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="policy.version.publish",
        resource_type="POLICY_VERSION",
        resource_id=str(ver.id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={"policy_id": policy_id, "version_number": ver.version_number, "content_hash": ver.content_hash_sha256},
    )

    return ver


@router.delete("/{policy_id}/versions/{version_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_policy_version(
    request: Request,
    policy_id: int,
    version_id: int,
    current_user: User = Depends(require_permission(Permission.POLICY_MANAGE)),
    db: Session = Depends(get_db),
) -> None:
    """Delete a policy version. Blocked if the version is bound to an active attestation campaign."""
    try:
        success = PolicyService.delete_policy_version(
            db=db, policy_id=policy_id, version_id=version_id, organization_id=current_user.organization_id
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy version not found in your organization")

    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="policy.version.delete",
        resource_type="POLICY_VERSION",
        resource_id=str(version_id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={"policy_id": policy_id},
    )


# ── Control Mapping Endpoints ───────────────────────────────────────────────

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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not mapping:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found in your organization")

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
    try:
        success = PolicyService.remove_control_mapping(
            db=db,
            policy_id=policy_id,
            organization_id=current_user.organization_id,
            subcategory_id=subcategory_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping not found")

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
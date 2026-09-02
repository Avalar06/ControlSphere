from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.core.permissions import Permission
from app.models.identity_governance import (
    CampaignStatusEnum,
    CertificationDecisionEnum,
    EmploymentStatusEnum,
    IdentityRiskBandEnum,
    IdentityTypeEnum,
    JITApprovalStatusEnum,
    SoDViolationStatusEnum,
    SystemTypeEnum,
)
from app.models.user import User
from app.schemas.identity_governance import (
    AccessCertificationCampaignCreate,
    AccessCertificationCampaignResponse,
    AccessCertificationItemResponse,
    AccessCertificationItemReview,
    EntitlementAssignmentCreate,
    EntitlementAssignmentResponse,
    GovernedIdentityCreate,
    GovernedIdentityResponse,
    GovernedIdentityUpdate,
    IdentityEntitlementCreate,
    IdentityEntitlementResponse,
    IdentityPostureSummaryResponse,
    JITAccessRequestCreate,
    JITAccessRequestResponse,
    JITAccessReviewRequest,
    SoDConflictPolicyCreate,
    SoDConflictPolicyResponse,
    SoDConflictViolationResponse,
    ZeroTrustAssessmentCreate,
    ZeroTrustAssessmentResponse,
    ZeroTrustPreviewRequest,
    ZeroTrustPreviewResponse,
)
from app.services.identity_governance_service import IdentityGovernanceService

router = APIRouter()


# ─── 1. GOVERNED IDENTITIES ───────────────────────────────────────────────────

@router.post("/identities", response_model=GovernedIdentityResponse, status_code=status.HTTP_201_CREATED)
def create_identity(
    payload: GovernedIdentityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.IDENTITY_MANAGE)),
):
    """Register a new workforce, service, or machine identity."""
    return IdentityGovernanceService.create_identity(
        db=db,
        org_id=current_user.organization_id,
        user_id=current_user.id,
        data=payload,
    )


@router.get("/identities", response_model=List[GovernedIdentityResponse])
def list_identities(
    identity_type: Optional[IdentityTypeEnum] = Query(None),
    employment_status: Optional[EmploymentStatusEnum] = Query(None),
    risk_band: Optional[IdentityRiskBandEnum] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.IDENTITY_READ)),
):
    """List governed identities for the tenant with optional filters."""
    return IdentityGovernanceService.list_identities(
        db=db,
        org_id=current_user.organization_id,
        identity_type=identity_type,
        employment_status=employment_status,
        risk_band=risk_band,
    )


@router.get("/identities/{identity_id}", response_model=GovernedIdentityResponse)
def get_identity(
    identity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.IDENTITY_READ)),
):
    """Get single identity detail."""
    return IdentityGovernanceService.get_identity(
        db=db,
        org_id=current_user.organization_id,
        identity_id=identity_id,
    )


@router.patch("/identities/{identity_id}", response_model=GovernedIdentityResponse)
def update_identity(
    identity_id: int,
    payload: GovernedIdentityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.IDENTITY_MANAGE)),
):
    """Update identity attributes and status."""
    return IdentityGovernanceService.update_identity(
        db=db,
        org_id=current_user.organization_id,
        user_id=current_user.id,
        identity_id=identity_id,
        data=payload,
    )


@router.delete("/identities/{identity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_identity(
    identity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.IDENTITY_MANAGE)),
):
    """Delete a non-active (suspended/terminated) identity."""
    IdentityGovernanceService.delete_identity(
        db=db,
        org_id=current_user.organization_id,
        user_id=current_user.id,
        identity_id=identity_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ─── 2. ENTITLEMENTS & ASSIGNMENTS ────────────────────────────────────────────

@router.post("/entitlements", response_model=IdentityEntitlementResponse, status_code=status.HTTP_201_CREATED)
def create_entitlement(
    payload: IdentityEntitlementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.IDENTITY_MANAGE)),
):
    """Register a new system permission or entitlement."""
    return IdentityGovernanceService.create_entitlement(
        db=db,
        org_id=current_user.organization_id,
        user_id=current_user.id,
        data=payload,
    )


@router.get("/entitlements", response_model=List[IdentityEntitlementResponse])
def list_entitlements(
    system_type: Optional[SystemTypeEnum] = Query(None),
    is_privileged: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.IDENTITY_READ)),
):
    """List entitlements for the organization."""
    return IdentityGovernanceService.list_entitlements(
        db=db,
        org_id=current_user.organization_id,
        system_type=system_type,
        is_privileged=is_privileged,
    )


@router.post("/identities/{identity_id}/assignments", response_model=EntitlementAssignmentResponse, status_code=status.HTTP_201_CREATED)
def assign_entitlement(
    identity_id: int,
    payload: EntitlementAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.IDENTITY_MANAGE)),
):
    """Assign an entitlement to an identity (evaluates SoD conflict policies)."""
    return IdentityGovernanceService.assign_entitlement(
        db=db,
        org_id=current_user.organization_id,
        user_id=current_user.id,
        identity_id=identity_id,
        data=payload,
    )


@router.get("/identities/{identity_id}/assignments", response_model=List[EntitlementAssignmentResponse])
def list_identity_assignments(
    identity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.IDENTITY_READ)),
):
    """List active entitlement assignments for an identity."""
    return IdentityGovernanceService.list_identity_assignments(
        db=db,
        org_id=current_user.organization_id,
        identity_id=identity_id,
    )


# ─── 3. ACCESS CERTIFICATION CAMPAIGNS (FOUR-EYES SoD) ────────────────────────

@router.post("/campaigns", response_model=AccessCertificationCampaignResponse, status_code=status.HTTP_201_CREATED)
def create_campaign(
    payload: AccessCertificationCampaignCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.IDENTITY_MANAGE)),
):
    """Launch a periodic User Access Review (UAR) Campaign."""
    return IdentityGovernanceService.create_campaign(
        db=db,
        org_id=current_user.organization_id,
        user_id=current_user.id,
        data=payload,
    )


@router.get("/campaigns", response_model=List[AccessCertificationCampaignResponse])
def list_campaigns(
    status_filter: Optional[CampaignStatusEnum] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.IDENTITY_READ)),
):
    """List access certification campaigns."""
    return IdentityGovernanceService.list_campaigns(
        db=db,
        org_id=current_user.organization_id,
        status_filter=status_filter,
    )


@router.get("/campaigns/{campaign_id}", response_model=AccessCertificationCampaignResponse)
def get_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.IDENTITY_READ)),
):
    """Get single certification campaign details."""
    return IdentityGovernanceService.get_campaign(
        db=db,
        org_id=current_user.organization_id,
        campaign_id=campaign_id,
    )


@router.get("/campaigns/{campaign_id}/items", response_model=List[AccessCertificationItemResponse])
def list_campaign_items(
    campaign_id: int,
    decision: Optional[CertificationDecisionEnum] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.IDENTITY_READ)),
):
    """List entitlement line items under certification in a campaign."""
    return IdentityGovernanceService.list_campaign_items(
        db=db,
        org_id=current_user.organization_id,
        campaign_id=campaign_id,
        decision=decision,
    )


@router.post("/certifications/{item_id}/review", response_model=AccessCertificationItemResponse)
def review_certification_item(
    item_id: int,
    payload: AccessCertificationItemReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.IDENTITY_APPROVE)),
):
    """Execute Four-Eyes review on an entitlement certification item (self-certification blocked)."""
    return IdentityGovernanceService.review_certification_item(
        db=db,
        org_id=current_user.organization_id,
        reviewer_id=current_user.id,
        item_id=item_id,
        review=payload,
    )


@router.post("/campaigns/{campaign_id}/finalize", response_model=AccessCertificationCampaignResponse)
def finalize_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.IDENTITY_APPROVE)),
):
    """Finalize an access certification campaign (renders decisions immutable)."""
    return IdentityGovernanceService.finalize_campaign(
        db=db,
        org_id=current_user.organization_id,
        user_id=current_user.id,
        campaign_id=campaign_id,
    )


# ─── 4. JIT ACCESS REQUESTS (FOUR-EYES SoD) ────────────────────────────────────

@router.post("/jit-requests", response_model=JITAccessRequestResponse, status_code=status.HTTP_201_CREATED)
def create_jit_request(
    payload: JITAccessRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.IDENTITY_ASSESS)),
):
    """Submit a Just-In-Time elevated access request."""
    return IdentityGovernanceService.create_jit_request(
        db=db,
        org_id=current_user.organization_id,
        user_id=current_user.id,
        data=payload,
    )


@router.get("/jit-requests", response_model=List[JITAccessRequestResponse])
def list_jit_requests(
    status_filter: Optional[JITApprovalStatusEnum] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.IDENTITY_READ)),
):
    """List JIT access requests for the tenant."""
    return IdentityGovernanceService.list_jit_requests(
        db=db,
        org_id=current_user.organization_id,
        status_filter=status_filter,
    )


@router.post("/jit-requests/{request_id}/review", response_model=JITAccessRequestResponse)
def review_jit_request(
    request_id: int,
    payload: JITAccessReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.IDENTITY_APPROVE)),
):
    """Execute Four-Eyes approval on a JIT privilege elevation request (self-approval blocked)."""
    return IdentityGovernanceService.review_jit_request(
        db=db,
        org_id=current_user.organization_id,
        reviewer_id=current_user.id,
        request_id=request_id,
        review=payload,
    )


# ─── 5. ZERO TRUST ASSURANCE ───────────────────────────────────────────────────

@router.post("/identities/{identity_id}/zero-trust", response_model=ZeroTrustAssessmentResponse, status_code=status.HTTP_201_CREATED)
def assess_zero_trust(
    identity_id: int,
    payload: ZeroTrustAssessmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.IDENTITY_ASSESS)),
):
    """Record server-authoritative Zero Trust Identity Assurance Assessment."""
    return IdentityGovernanceService.assess_zero_trust(
        db=db,
        org_id=current_user.organization_id,
        user_id=current_user.id,
        identity_id=identity_id,
        data=payload,
    )


@router.post("/zero-trust/preview", response_model=ZeroTrustPreviewResponse)
def preview_zero_trust(
    payload: ZeroTrustPreviewRequest,
    current_user: User = Depends(require_permission(Permission.IDENTITY_READ)),
):
    """Preview Zero Trust assurance calculations server-side without persisting."""
    return IdentityGovernanceService.preview_zero_trust(data=payload)


# ─── 6. SoD POLICIES & VIOLATIONS ──────────────────────────────────────────────

@router.post("/sod-policies", response_model=SoDConflictPolicyResponse, status_code=status.HTTP_201_CREATED)
def create_sod_policy(
    payload: SoDConflictPolicyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.IDENTITY_MANAGE)),
):
    """Configure a Segregation of Duties (SoD) toxic combination policy."""
    return IdentityGovernanceService.create_sod_policy(
        db=db,
        org_id=current_user.organization_id,
        user_id=current_user.id,
        data=payload,
    )


@router.get("/sod-policies", response_model=List[SoDConflictPolicyResponse])
def list_sod_policies(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.IDENTITY_READ)),
):
    """List configured SoD conflict policies."""
    return IdentityGovernanceService.list_sod_policies(
        db=db,
        org_id=current_user.organization_id,
    )


@router.get("/sod-violations", response_model=List[SoDConflictViolationResponse])
def list_sod_violations(
    identity_id: Optional[int] = Query(None),
    status_filter: Optional[SoDViolationStatusEnum] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.IDENTITY_READ)),
):
    """List active and remediated SoD conflict violations."""
    return IdentityGovernanceService.list_sod_violations(
        db=db,
        org_id=current_user.organization_id,
        identity_id=identity_id,
        status_filter=status_filter,
    )


# ─── 7. POSTURE SUMMARY ────────────────────────────────────────────────────────

@router.get("/posture/summary", response_model=IdentityPostureSummaryResponse)
def get_posture_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.IDENTITY_READ)),
):
    """Get aggregated IGA posture metrics for the organization."""
    return IdentityGovernanceService.get_posture_summary(
        db=db,
        org_id=current_user.organization_id,
    )

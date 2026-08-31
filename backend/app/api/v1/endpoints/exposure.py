from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.core.permissions import Permission
from app.models.exposure import (
    AssetTypeEnum,
    EnvironmentEnum,
    ExceptionApprovalStatusEnum,
    ExposureAssetLink,
    ExposureException,
    ExposureSeverityEnum,
    ExposureStatusEnum,
    VulnerabilityExposure,
)
from app.models.resilience import CriticalityTierEnum
from app.models.user import User
from app.schemas.exposure import (
    ExposureAssetLinkCreate,
    ExposureAssetLinkRead,
    ExposureExceptionCreate,
    ExposureExceptionRead,
    ExposureExceptionReviewRequest,
    ExposureIndexCalculateRequest,
    ExposureIndexCalculateResponse,
    ExposureSummaryResponse,
    VulnerabilityExposureCreate,
    VulnerabilityExposureRead,
    VulnerabilityExposureStatusUpdate,
    VulnerabilityExposureUpdate,
)
from app.schemas.remediation import RemediationPlanRead
from app.services.exposure_service import ExposureService

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# 1. EXPOSURE CATALOG ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.post("", response_model=VulnerabilityExposureRead, status_code=status.HTTP_201_CREATED)
def create_exposure(
    payload: VulnerabilityExposureCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXPOSURE_MANAGE)),
):
    """Ingest/Register a new vulnerability exposure record with server-authoritative SLA and index."""
    try:
        return ExposureService.create_exposure(
            db=db,
            organization_id=current_user.organization_id,
            data=payload,
            actor_id=current_user.id,
            actor_email=current_user.email,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=List[VulnerabilityExposureRead])
def list_exposures(
    severity: Optional[ExposureSeverityEnum] = None,
    status_filter: Optional[ExposureStatusEnum] = Query(None, alias="status"),
    cisa_kev: Optional[bool] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXPOSURE_READ)),
):
    """List tenant-scoped exposures with multi-attribute filtering and text search."""
    return ExposureService.list_exposures(
        db=db,
        organization_id=current_user.organization_id,
        severity=severity,
        status=status_filter,
        cisa_kev=cisa_kev,
        search=search,
        skip=skip,
        limit=limit,
    )


@router.get("/summary/posture", response_model=ExposureSummaryResponse)
def get_exposure_posture_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXPOSURE_READ)),
):
    """Calculates executive threat posture telemetry and SLA breach rates."""
    return ExposureService.get_exposure_posture_summary(
        db=db,
        organization_id=current_user.organization_id,
    )


@router.post("/calculate-index", response_model=ExposureIndexCalculateResponse)
def calculate_index_preview(
    payload: ExposureIndexCalculateRequest,
    current_user: User = Depends(require_permission(Permission.EXPOSURE_READ)),
):
    """Preview server-authoritative Exposure Index calculation."""
    try:
        base_score, multiplier, final_index = ExposureService.calculate_exposure_index(
            cvss_score=payload.cvss_score,
            epss_score=payload.epss_score,
            cisa_kev=payload.cisa_kev,
            highest_process_tier=payload.highest_process_tier,
        )
        return ExposureIndexCalculateResponse(
            cvss_score=payload.cvss_score,
            epss_score=payload.epss_score,
            cisa_kev=payload.cisa_kev,
            base_score=base_score,
            blast_radius_multiplier=multiplier,
            exposure_index=final_index,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/exceptions", response_model=List[ExposureExceptionRead])
def list_exceptions(
    exposure_id: Optional[int] = None,
    status_filter: Optional[ExceptionApprovalStatusEnum] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXPOSURE_READ)),
):
    """List SLA deferral exceptions for the tenant organization."""
    return ExposureService.list_exceptions(
        db=db,
        organization_id=current_user.organization_id,
        exposure_id=exposure_id,
        status=status_filter,
    )


@router.get("/{exposure_id}", response_model=VulnerabilityExposureRead)
def get_exposure(
    exposure_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXPOSURE_READ)),
):
    """Retrieve a single exposure record enforcing tenant isolation."""
    exposure = ExposureService.get_exposure(db, current_user.organization_id, exposure_id)
    if not exposure:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vulnerability exposure #{exposure_id} not found.",
        )
    return exposure


@router.put("/{exposure_id}", response_model=VulnerabilityExposureRead)
def update_exposure(
    exposure_id: int,
    payload: VulnerabilityExposureUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXPOSURE_MANAGE)),
):
    """Update exposure telemetry, CVSS/EPSS parameters, or metadata."""
    try:
        return ExposureService.update_exposure(
            db=db,
            organization_id=current_user.organization_id,
            exposure_id=exposure_id,
            data=payload,
            actor_id=current_user.id,
            actor_email=current_user.email,
        )
    except ValueError as e:
        msg = str(e)
        if "not found" in msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        if "immutable" in msg:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)


@router.delete("/{exposure_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exposure(
    exposure_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXPOSURE_MANAGE)),
):
    """Delete an exposure record (restricted to non-resolved records)."""
    try:
        ExposureService.delete_exposure(
            db=db,
            organization_id=current_user.organization_id,
            exposure_id=exposure_id,
            actor_id=current_user.id,
            actor_email=current_user.email,
        )
    except ValueError as e:
        msg = str(e)
        if "not found" in msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        if "immutable" in msg:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)


# ─────────────────────────────────────────────────────────────────────────────
# 2. LIFECYCLE STATE TRANSITIONS
# ─────────────────────────────────────────────────────────────────────────────

@router.put("/{exposure_id}/status", response_model=VulnerabilityExposureRead)
def update_exposure_status(
    exposure_id: int,
    payload: VulnerabilityExposureStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXPOSURE_MANAGE)),
):
    """Execute a governed lifecycle state transition."""
    try:
        return ExposureService.update_exposure_status(
            db=db,
            organization_id=current_user.organization_id,
            exposure_id=exposure_id,
            new_status=payload.status,
            actor_id=current_user.id,
            actor_email=current_user.email,
            notes=payload.notes,
        )
    except ValueError as e:
        msg = str(e)
        if "not found" in msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        if "terminal" in msg or "immutable" in msg or "Illegal lifecycle" in msg:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)


# ─────────────────────────────────────────────────────────────────────────────
# 3. ASSET & BLAST RADIUS LINKAGE
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{exposure_id}/assets", response_model=ExposureAssetLinkRead, status_code=status.HTTP_201_CREATED)
def link_asset_to_exposure(
    exposure_id: int,
    payload: ExposureAssetLinkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXPOSURE_MANAGE)),
):
    """Link an asset, Phase 13 Process, Phase 9 Vendor, or Phase 2 Control to the exposure."""
    try:
        return ExposureService.link_asset(
            db=db,
            organization_id=current_user.organization_id,
            exposure_id=exposure_id,
            data=payload,
            actor_id=current_user.id,
            actor_email=current_user.email,
        )
    except ValueError as e:
        msg = str(e)
        if "not found" in msg or "does not exist in this organization" in msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        if "immutable" in msg:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)


@router.get("/{exposure_id}/assets", response_model=List[ExposureAssetLinkRead])
def list_exposure_assets(
    exposure_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXPOSURE_READ)),
):
    """List all assets linked to an exposure."""
    exposure = ExposureService.get_exposure(db, current_user.organization_id, exposure_id)
    if not exposure:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vulnerability exposure #{exposure_id} not found.",
        )
    return ExposureService.list_asset_links(db, current_user.organization_id, exposure_id)


@router.delete("/assets/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_asset(
    link_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXPOSURE_MANAGE)),
):
    """Remove an asset link and recalculate blast radius."""
    try:
        ExposureService.unlink_asset(
            db=db,
            organization_id=current_user.organization_id,
            link_id=link_id,
            actor_id=current_user.id,
            actor_email=current_user.email,
        )
    except ValueError as e:
        msg = str(e)
        if "not found" in msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)


# ─────────────────────────────────────────────────────────────────────────────
# 4. FOUR-EYES EXCEPTION & DEFERRAL GOVERNANCE
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{exposure_id}/exceptions", response_model=ExposureExceptionRead, status_code=status.HTTP_201_CREATED)
def request_exception(
    exposure_id: int,
    payload: ExposureExceptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXPOSURE_MANAGE)),
):
    """Submit a four-eyes governed SLA extension request."""
    try:
        return ExposureService.request_exception(
            db=db,
            organization_id=current_user.organization_id,
            exposure_id=exposure_id,
            data=payload,
            requested_by_id=current_user.id,
            actor_email=current_user.email,
        )
    except ValueError as e:
        msg = str(e)
        if "not found" in msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        if "immutable" in msg:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)


@router.post("/exceptions/{exception_id}/review", response_model=ExposureExceptionRead)
def review_exception(
    exception_id: int,
    payload: ExposureExceptionReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXPOSURE_APPROVE)),
):
    """Review and approve/reject exception with Four-Eyes Segregation of Duties (requester != approver)."""
    try:
        return ExposureService.review_exception(
            db=db,
            organization_id=current_user.organization_id,
            exception_id=exception_id,
            review=payload,
            approver_id=current_user.id,
            actor_email=current_user.email,
        )
    except ValueError as e:
        msg = str(e)
        if "not found" in msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        if "Segregation of duties violation" in msg:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=msg)
        if "already in terminal state" in msg:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)


# ─────────────────────────────────────────────────────────────────────────────
# 5. CROSS-MODULE REMEDIATION SPAWNING (Phase 11)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{exposure_id}/remediate", response_model=RemediationPlanRead, status_code=status.HTTP_201_CREATED)
def spawn_remediation_plan(
    exposure_id: int,
    title: Optional[str] = None,
    finding_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REMEDIATION_MANAGE)),
):
    """Instantiate a Phase 11 RemediationPlan linked to the exposure."""
    try:
        return ExposureService.spawn_remediation_plan(
            db=db,
            organization_id=current_user.organization_id,
            exposure_id=exposure_id,
            owner_id=current_user.id,
            title=title,
            finding_id=finding_id,
            actor_id=current_user.id,
            actor_email=current_user.email,
        )
    except ValueError as e:
        msg = str(e)
        if "not found" in msg or "does not exist in this organization" in msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

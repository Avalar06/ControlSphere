from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.core.permissions import Permission
from app.models.privacy import (
    DataSensitivityLevel,
    DPIARiskBand,
    JurisdictionRiskTier,
    PrivacyApprovalStatus,
    ProcessingLegalBasis,
    ProcessingLifecycleState,
    TransferMechanism,
)
from app.models.user import User
from app.schemas.privacy import (
    DataAssetCreate,
    DataAssetResponse,
    DataAssetUpdate,
    DataTransferCalculatePreviewRequest,
    DataTransferCalculatePreviewResponse,
    DataTransferCreate,
    DataTransferResponse,
    DataTransferReviewRequest,
    DataTransferUpdate,
    DPIACalculatePreviewRequest,
    DPIACalculatePreviewResponse,
    DPIACreate,
    DPIAResponse,
    DPIAReviewRequest,
    DPIAUpdate,
    PrivacyPostureSummaryResponse,
    ProcessingActivityCreate,
    ProcessingActivityResponse,
    ProcessingActivityStatusUpdate,
    ProcessingActivityUpdate,
)
from app.services.privacy_service import PrivacyService

router = APIRouter()


# ─── 1. DATA ASSETS CATALOG ───────────────────────────────────────────────────

@router.post("/data-assets", response_model=DataAssetResponse, status_code=status.HTTP_201_CREATED)
def create_data_asset(
    payload: DataAssetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.PRIVACY_MANAGE)),
):
    """Register a new data asset into the organizational privacy catalog."""
    return PrivacyService.create_data_asset(
        db=db,
        organization_id=current_user.organization_id,
        owner_id=current_user.id,
        payload=payload,
    )


@router.get("/data-assets", response_model=List[DataAssetResponse])
def list_data_assets(
    sensitivity: Optional[DataSensitivityLevel] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.PRIVACY_READ)),
):
    """List tenant-scoped data assets with optional sensitivity filtering."""
    return PrivacyService.list_data_assets(
        db=db,
        organization_id=current_user.organization_id,
        skip=skip,
        limit=limit,
        sensitivity=sensitivity,
    )


@router.get("/data-assets/{asset_id}", response_model=DataAssetResponse)
def get_data_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.PRIVACY_READ)),
):
    """Retrieve details of a single data asset."""
    return PrivacyService.get_data_asset(
        db=db,
        organization_id=current_user.organization_id,
        asset_id=asset_id,
    )


@router.put("/data-assets/{asset_id}", response_model=DataAssetResponse)
def update_data_asset(
    asset_id: int,
    payload: DataAssetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.PRIVACY_MANAGE)),
):
    """Update metadata and properties of an existing data asset."""
    return PrivacyService.update_data_asset(
        db=db,
        organization_id=current_user.organization_id,
        asset_id=asset_id,
        user_id=current_user.id,
        payload=payload,
    )


@router.delete("/data-assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_data_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.PRIVACY_MANAGE)),
):
    """Delete a data asset from the catalog."""
    PrivacyService.delete_data_asset(
        db=db,
        organization_id=current_user.organization_id,
        asset_id=asset_id,
        user_id=current_user.id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ─── 2. PROCESSING ACTIVITIES / RoPA ──────────────────────────────────────────

@router.post("/activities", response_model=ProcessingActivityResponse, status_code=status.HTTP_201_CREATED)
def create_processing_activity(
    payload: ProcessingActivityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.PRIVACY_MANAGE)),
):
    """Create a new GDPR Article 30 Record of Processing Activities (RoPA) entry."""
    return PrivacyService.create_processing_activity(
        db=db,
        organization_id=current_user.organization_id,
        owner_id=current_user.id,
        payload=payload,
    )


@router.get("/activities", response_model=List[ProcessingActivityResponse])
def list_processing_activities(
    lifecycle_state: Optional[ProcessingLifecycleState] = None,
    legal_basis: Optional[ProcessingLegalBasis] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.PRIVACY_READ)),
):
    """List tenant-scoped processing activities with optional lifecycle and legal basis filters."""
    return PrivacyService.list_processing_activities(
        db=db,
        organization_id=current_user.organization_id,
        skip=skip,
        limit=limit,
        lifecycle_state=lifecycle_state,
        legal_basis=legal_basis,
    )


@router.get("/activities/{activity_id}", response_model=ProcessingActivityResponse)
def get_processing_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.PRIVACY_READ)),
):
    """Retrieve details of a single RoPA processing activity."""
    return PrivacyService.get_processing_activity(
        db=db,
        organization_id=current_user.organization_id,
        activity_id=activity_id,
    )


@router.put("/activities/{activity_id}", response_model=ProcessingActivityResponse)
def update_processing_activity(
    activity_id: int,
    payload: ProcessingActivityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.PRIVACY_MANAGE)),
):
    """Update details of an existing processing activity (blocked if RETIRED)."""
    return PrivacyService.update_processing_activity(
        db=db,
        organization_id=current_user.organization_id,
        activity_id=activity_id,
        user_id=current_user.id,
        payload=payload,
    )


@router.patch("/activities/{activity_id}/status", response_model=ProcessingActivityResponse)
def update_processing_activity_status(
    activity_id: int,
    payload: ProcessingActivityStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.PRIVACY_MANAGE)),
):
    """Transition the lifecycle state of a processing activity through governed state machine."""
    return PrivacyService.update_processing_activity_status(
        db=db,
        organization_id=current_user.organization_id,
        activity_id=activity_id,
        user_id=current_user.id,
        payload=payload,
    )


@router.delete("/activities/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_processing_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.PRIVACY_MANAGE)),
):
    """Delete a processing activity (blocked if ACTIVE)."""
    PrivacyService.delete_processing_activity(
        db=db,
        organization_id=current_user.organization_id,
        activity_id=activity_id,
        user_id=current_user.id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ─── 3. DPIA ASSESSMENTS ───────────────────────────────────────────────────────

@router.post("/dpia", response_model=DPIAResponse, status_code=status.HTTP_201_CREATED)
def create_dpia_assessment(
    payload: DPIACreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.PRIVACY_ASSESS)),
):
    """Initiate a Data Protection Impact Assessment (DPIA) with server-authoritative risk calculation."""
    return PrivacyService.create_dpia_assessment(
        db=db,
        organization_id=current_user.organization_id,
        created_by_id=current_user.id,
        payload=payload,
    )


@router.get("/dpia", response_model=List[DPIAResponse])
def list_dpia_assessments(
    activity_id: Optional[int] = None,
    risk_band: Optional[DPIARiskBand] = None,
    status_filter: Optional[PrivacyApprovalStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.PRIVACY_READ)),
):
    """List tenant-scoped DPIA assessments with optional activity, risk band, and status filters."""
    return PrivacyService.list_dpia_assessments(
        db=db,
        organization_id=current_user.organization_id,
        skip=skip,
        limit=limit,
        activity_id=activity_id,
        risk_band=risk_band,
        status_filter=status_filter,
    )


@router.get("/dpia/{dpia_id}", response_model=DPIAResponse)
def get_dpia_assessment(
    dpia_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.PRIVACY_READ)),
):
    """Retrieve details of a single DPIA assessment."""
    return PrivacyService.get_dpia_assessment(
        db=db,
        organization_id=current_user.organization_id,
        dpia_id=dpia_id,
    )


@router.put("/dpia/{dpia_id}", response_model=DPIAResponse)
def update_dpia_assessment(
    dpia_id: int,
    payload: DPIAUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.PRIVACY_ASSESS)),
):
    """Update DPIA assessment parameters and trigger automatic server-side score recalculation."""
    return PrivacyService.update_dpia_assessment(
        db=db,
        organization_id=current_user.organization_id,
        dpia_id=dpia_id,
        user_id=current_user.id,
        payload=payload,
    )


@router.post("/dpia/{dpia_id}/review", response_model=DPIAResponse)
def review_dpia_assessment(
    dpia_id: int,
    payload: DPIAReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.PRIVACY_APPROVE)),
):
    """Record DPO review decision (APPROVED/REJECTED) enforcing Four-Eyes Segregation of Duties."""
    return PrivacyService.review_dpia_assessment(
        db=db,
        organization_id=current_user.organization_id,
        dpia_id=dpia_id,
        reviewer_id=current_user.id,
        review_data=payload,
    )


@router.post("/dpia/calculate-preview", response_model=DPIACalculatePreviewResponse)
def calculate_dpia_preview(
    payload: DPIACalculatePreviewRequest,
    current_user: User = Depends(require_permission(Permission.PRIVACY_READ)),
):
    """Preview server-authoritative DPIA Inherent & Residual Risk scores without persistence."""
    irs = PrivacyService.calculate_dpia_inherent_risk(
        sensitivity_level=payload.sensitivity_level,
        volume_tier=payload.volume_tier,
        is_special_category=payload.is_special_category,
        automated_decision_making_risk=payload.automated_decision_making_risk,
        large_scale_monitoring_risk=payload.large_scale_monitoring_risk,
        vulnerable_subjects_risk=payload.vulnerable_subjects_risk,
    )
    rrs = PrivacyService.calculate_dpia_residual_risk(
        inherent_risk_score=irs,
        safeguards_mitigation_score=payload.safeguards_mitigation_score,
        has_threat_exposure=payload.has_threat_exposure,
    )
    risk_band = PrivacyService.determine_dpia_risk_band(rrs)
    prior_consultation = (rrs >= 80.0)

    return DPIACalculatePreviewResponse(
        inherent_risk_score=irs,
        residual_risk_score=rrs,
        risk_band=risk_band,
        prior_consultation_required=prior_consultation,
    )


# ─── 4. DATA TRANSFER ASSESSMENTS ─────────────────────────────────────────────

@router.post("/transfers", response_model=DataTransferResponse, status_code=status.HTTP_201_CREATED)
def create_data_transfer(
    payload: DataTransferCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.PRIVACY_ASSESS)),
):
    """Create a Transfer Impact Assessment (TIA) for cross-border data transfers."""
    return PrivacyService.create_data_transfer(
        db=db,
        organization_id=current_user.organization_id,
        requested_by_id=current_user.id,
        payload=payload,
    )


@router.get("/transfers", response_model=List[DataTransferResponse])
def list_data_transfers(
    activity_id: Optional[int] = None,
    tier: Optional[JurisdictionRiskTier] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.PRIVACY_READ)),
):
    """List tenant-scoped transfer assessments with optional activity and jurisdiction filters."""
    return PrivacyService.list_data_transfers(
        db=db,
        organization_id=current_user.organization_id,
        skip=skip,
        limit=limit,
        activity_id=activity_id,
        tier=tier,
    )


@router.get("/transfers/{transfer_id}", response_model=DataTransferResponse)
def get_data_transfer(
    transfer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.PRIVACY_READ)),
):
    """Retrieve details of a single data transfer assessment."""
    return PrivacyService.get_data_transfer(
        db=db,
        organization_id=current_user.organization_id,
        transfer_id=transfer_id,
    )


@router.post("/transfers/{transfer_id}/review", response_model=DataTransferResponse)
def review_data_transfer(
    transfer_id: int,
    payload: DataTransferReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.PRIVACY_APPROVE)),
):
    """Review / approve a cross-border transfer assessment enforcing Four-Eyes Segregation of Duties."""
    return PrivacyService.review_data_transfer(
        db=db,
        organization_id=current_user.organization_id,
        transfer_id=transfer_id,
        reviewer_id=current_user.id,
        review_data=payload,
    )


@router.post("/transfers/calculate-preview", response_model=DataTransferCalculatePreviewResponse)
def calculate_transfer_preview(
    payload: DataTransferCalculatePreviewRequest,
    current_user: User = Depends(require_permission(Permission.PRIVACY_READ)),
):
    """Preview server-authoritative Transfer Risk Index (TRI) calculation without persistence."""
    tri = PrivacyService.calculate_transfer_risk_index(
        destination_tier=payload.destination_jurisdiction_tier,
        mechanism=payload.transfer_mechanism,
        supplementary_measures_score=payload.supplementary_measures_score,
    )
    return DataTransferCalculatePreviewResponse(transfer_risk_index=tri)


# ─── 5. POSTURE SUMMARY & TELEMETRY ───────────────────────────────────────────

@router.get("/summary/posture", response_model=PrivacyPostureSummaryResponse)
@router.get("/posture/summary", response_model=PrivacyPostureSummaryResponse)
def get_privacy_posture_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.PRIVACY_READ)),
):
    """Calculate executive privacy posture summary and risk distribution telemetry."""
    return PrivacyService.get_privacy_posture_summary(
        db=db,
        organization_id=current_user.organization_id,
    )

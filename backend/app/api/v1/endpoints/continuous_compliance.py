import json
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_permission
from app.core.permissions import Permission
from app.models.user import User
from app.models.continuous_compliance import (
    ComplianceDriftStatusEnum,
    ComplianceDriftVectorEnum,
)
from app.schemas.continuous_compliance import (
    ContinuousComplianceProfileUpdate,
    ContinuousComplianceProfileResponse,
    ComplianceDriftRecordResponse,
    UnifiedAssurancePostureResponse,
    ContinuousAssuranceSnapshotCreate,
    ContinuousAssuranceSnapshotResponse,
)
from app.services.continuous_compliance_service import ContinuousComplianceService

router = APIRouter()


# ── Profile ─────────────────────────────────────────────────────────────────

@router.get("/profile", response_model=ContinuousComplianceProfileResponse)
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.CONTINUOUS_READ)),
) -> Any:
    """Get continuous compliance assurance profile and evaluation thresholds."""
    return ContinuousComplianceService.get_or_create_profile(
        db=db,
        organization_id=current_user.organization_id,
        current_user_id=current_user.id,
    )


@router.put("/profile", response_model=ContinuousComplianceProfileResponse)
def update_profile(
    profile_in: ContinuousComplianceProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.CONTINUOUS_MANAGE)),
) -> Any:
    """Update continuous compliance assurance profile thresholds."""
    return ContinuousComplianceService.update_profile(
        db=db,
        organization_id=current_user.organization_id,
        profile_in=profile_in,
        current_user_id=current_user.id,
    )


# ── Posture & Drift ─────────────────────────────────────────────────────────

@router.get("/posture", response_model=UnifiedAssurancePostureResponse)
def get_posture(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.CONTINUOUS_READ)),
) -> Any:
    """Get live, server-authoritative enterprise unified assurance score and pillar breakdown."""
    return ContinuousComplianceService.calculate_unified_assurance(
        db=db,
        organization_id=current_user.organization_id,
    )


@router.get("/drift", response_model=List[ComplianceDriftRecordResponse])
def list_drifts(
    status_filter: Optional[ComplianceDriftStatusEnum] = Query(None, alias="status"),
    vector_filter: Optional[ComplianceDriftVectorEnum] = Query(None, alias="vector"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.CONTINUOUS_READ)),
) -> Any:
    """List multi-vector compliance drift records."""
    return ContinuousComplianceService.list_drifts(
        db=db,
        organization_id=current_user.organization_id,
        status=status_filter,
        vector=vector_filter,
        skip=skip,
        limit=limit,
    )


@router.post("/evaluate", response_model=UnifiedAssurancePostureResponse)
def evaluate_compliance(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.CONTINUOUS_TRIGGER)),
) -> Any:
    """Trigger on-demand continuous compliance evaluation and automated CAPA triggers."""
    return ContinuousComplianceService.evaluate_continuous_compliance(
        db=db,
        organization_id=current_user.organization_id,
        current_user_id=current_user.id,
    )


@router.post("/drift/{id}/trigger-remediation", response_model=ComplianceDriftRecordResponse)
def trigger_remediation(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.CONTINUOUS_TRIGGER)),
) -> Any:
    """Trigger authoritative Phase 11 RemediationPlan (CAPA) from a compliance drift record."""
    try:
        drift, _ = ContinuousComplianceService.trigger_remediation_for_drift(
            db=db,
            organization_id=current_user.organization_id,
            drift_id=id,
            current_user_id=current_user.id,
        )
        return drift
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── Snapshots ───────────────────────────────────────────────────────────────

@router.get("/snapshots", response_model=List[ContinuousAssuranceSnapshotResponse])
def list_snapshots(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.CONTINUOUS_READ)),
) -> Any:
    """List immutable point-in-time continuous assurance snapshots."""
    snaps = ContinuousComplianceService.list_snapshots(
        db=db,
        organization_id=current_user.organization_id,
        skip=skip,
        limit=limit,
    )
    results = []
    for s in snaps:
        results.append({
            "id": s.id,
            "organization_id": s.organization_id,
            "snapshot_code": s.snapshot_code,
            "captured_at": s.captured_at,
            "overall_assurance_score": s.overall_assurance_score,
            "controls_assurance_score": s.controls_assurance_score,
            "evidence_pipeline_score": s.evidence_pipeline_score,
            "regulatory_compliance_score": s.regulatory_compliance_score,
            "remediation_sla_score": s.remediation_sla_score,
            "cloud_identity_posture_score": s.cloud_identity_posture_score,
            "harmonized_frameworks_score": s.harmonized_frameworks_score,
            "active_drift_count": s.active_drift_count,
            "critical_drift_count": s.critical_drift_count,
            "pillar_breakdown": json.loads(s.pillar_breakdown),
            "framework_compliance_breakdown": json.loads(s.framework_compliance_breakdown),
            "data_hash_sha256": s.data_hash_sha256,
            "calculation_version": s.calculation_version,
            "created_by_id": s.created_by_id,
            "created_at": s.created_at,
        })
    return results


@router.post("/snapshots", response_model=ContinuousAssuranceSnapshotResponse, status_code=status.HTTP_201_CREATED)
def capture_snapshot(
    snap_in: ContinuousAssuranceSnapshotCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.CONTINUOUS_TRIGGER)),
) -> Any:
    """Capture an immutable cryptographic continuous assurance snapshot."""
    try:
        s = ContinuousComplianceService.capture_assurance_snapshot(
            db=db,
            organization_id=current_user.organization_id,
            snap_in=snap_in,
            current_user_id=current_user.id,
        )
        return {
            "id": s.id,
            "organization_id": s.organization_id,
            "snapshot_code": s.snapshot_code,
            "captured_at": s.captured_at,
            "overall_assurance_score": s.overall_assurance_score,
            "controls_assurance_score": s.controls_assurance_score,
            "evidence_pipeline_score": s.evidence_pipeline_score,
            "regulatory_compliance_score": s.regulatory_compliance_score,
            "remediation_sla_score": s.remediation_sla_score,
            "cloud_identity_posture_score": s.cloud_identity_posture_score,
            "harmonized_frameworks_score": s.harmonized_frameworks_score,
            "active_drift_count": s.active_drift_count,
            "critical_drift_count": s.critical_drift_count,
            "pillar_breakdown": json.loads(s.pillar_breakdown),
            "framework_compliance_breakdown": json.loads(s.framework_compliance_breakdown),
            "data_hash_sha256": s.data_hash_sha256,
            "calculation_version": s.calculation_version,
            "created_by_id": s.created_by_id,
            "created_at": s.created_at,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT if "already exists" in str(e) else status.HTTP_400_BAD_REQUEST, detail=str(e))

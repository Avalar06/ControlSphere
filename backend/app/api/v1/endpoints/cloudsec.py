from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.core.permissions import Permission
from app.models.cloudsec import (
    CloudAssetTypeEnum,
    CloudCriticalityEnum,
    CloudEnvironmentEnum,
    CloudLifecycleStateEnum,
    CloudPostureStatusEnum,
    CloudProviderEnum,
    DriftStatusEnum,
    EvaluationStatusEnum,
    RuleSeverityEnum,
)
from app.models.user import User
from app.schemas.cloudsec import (
    CloudAssetCreate,
    CloudAssetResponse,
    CloudAssetStatusUpdate,
    CloudAssetUpdate,
    CloudBenchmarkRuleCreate,
    CloudBenchmarkRuleResponse,
    CloudConfigurationDriftCreate,
    CloudConfigurationDriftResponse,
    CloudIAMBlastRadiusCreate,
    CloudIAMBlastRadiusPreviewRequest,
    CloudIAMBlastRadiusPreviewResponse,
    CloudIAMBlastRadiusResponse,
    CloudPostureSummaryResponse,
    CloudSecurityBenchmarkCreate,
    CloudSecurityBenchmarkResponse,
    CloudSecurityFindingCreate,
    CloudSecurityFindingResponse,
)
from app.services.cloudsec_service import CloudSecService

router = APIRouter()


# ─── 1. CLOUD ASSETS ──────────────────────────────────────────────────────────

@router.post("/assets", response_model=CloudAssetResponse, status_code=status.HTTP_201_CREATED)
def create_cloud_asset(
    payload: CloudAssetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.CLOUDSEC_MANAGE)),
):
    """Register a new Cloud Asset in the CSPM inventory."""
    return CloudSecService.create_asset(
        db=db,
        org_id=current_user.organization_id,
        user_id=current_user.id,
        data=payload,
    )


@router.get("/assets", response_model=List[CloudAssetResponse])
def list_cloud_assets(
    provider: Optional[CloudProviderEnum] = Query(None),
    environment: Optional[CloudEnvironmentEnum] = Query(None),
    posture_status: Optional[CloudPostureStatusEnum] = Query(None),
    lifecycle_state: Optional[CloudLifecycleStateEnum] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.CLOUDSEC_READ)),
):
    """List Cloud Assets for the authenticated tenant with optional filters."""
    return CloudSecService.list_assets(
        db=db,
        org_id=current_user.organization_id,
        provider=provider,
        environment=environment,
        posture_status=posture_status,
        lifecycle_state=lifecycle_state,
    )


@router.get("/assets/{asset_id}", response_model=CloudAssetResponse)
def get_cloud_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.CLOUDSEC_READ)),
):
    """Get single Cloud Asset detail."""
    return CloudSecService.get_asset(
        db=db,
        org_id=current_user.organization_id,
        asset_id=asset_id,
    )


@router.patch("/assets/{asset_id}", response_model=CloudAssetResponse)
def update_cloud_asset(
    asset_id: int,
    payload: CloudAssetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.CLOUDSEC_MANAGE)),
):
    """Update Cloud Asset metadata and configuration."""
    return CloudSecService.update_asset(
        db=db,
        org_id=current_user.organization_id,
        user_id=current_user.id,
        asset_id=asset_id,
        data=payload,
    )


@router.post("/assets/{asset_id}/status", response_model=CloudAssetResponse)
def update_cloud_asset_status(
    asset_id: int,
    payload: CloudAssetStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.CLOUDSEC_MANAGE)),
):
    """Execute governed lifecycle transition for a cloud asset."""
    return CloudSecService.update_asset_status(
        db=db,
        org_id=current_user.organization_id,
        user_id=current_user.id,
        asset_id=asset_id,
        status_update=payload,
    )


@router.delete("/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cloud_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.CLOUDSEC_MANAGE)),
):
    """Delete a decommissioned cloud asset."""
    CloudSecService.delete_asset(
        db=db,
        org_id=current_user.organization_id,
        user_id=current_user.id,
        asset_id=asset_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ─── 2. BENCHMARKS & CIS RULES ────────────────────────────────────────────────

@router.post("/benchmarks", response_model=CloudSecurityBenchmarkResponse, status_code=status.HTTP_201_CREATED)
def create_benchmark(
    payload: CloudSecurityBenchmarkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.CLOUDSEC_MANAGE)),
):
    """Register a new Cloud Benchmark standard (e.g. CIS Foundations)."""
    return CloudSecService.create_benchmark(db=db, data=payload)


@router.get("/benchmarks", response_model=List[CloudSecurityBenchmarkResponse])
def list_benchmarks(
    provider: Optional[CloudProviderEnum] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.CLOUDSEC_READ)),
):
    """List available Cloud Security benchmarks."""
    return CloudSecService.list_benchmarks(db=db, provider=provider)


@router.post("/rules", response_model=CloudBenchmarkRuleResponse, status_code=status.HTTP_201_CREATED)
def create_benchmark_rule(
    payload: CloudBenchmarkRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.CLOUDSEC_MANAGE)),
):
    """Register a specific check rule under a Cloud Benchmark."""
    return CloudSecService.create_rule(db=db, data=payload)


@router.get("/rules", response_model=List[CloudBenchmarkRuleResponse])
def list_benchmark_rules(
    benchmark_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.CLOUDSEC_READ)),
):
    """List benchmark check rules."""
    return CloudSecService.list_rules(db=db, benchmark_id=benchmark_id)


# ─── 3. FINDINGS & EVALUATIONS ────────────────────────────────────────────────

@router.post("/findings", response_model=CloudSecurityFindingResponse, status_code=status.HTTP_201_CREATED)
def record_finding(
    payload: CloudSecurityFindingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.CLOUDSEC_ASSESS)),
):
    """Record an authoritative CSPM evaluation finding against a Cloud Asset."""
    return CloudSecService.record_finding(
        db=db,
        org_id=current_user.organization_id,
        user_id=current_user.id,
        data=payload,
    )


@router.get("/findings", response_model=List[CloudSecurityFindingResponse])
def list_findings(
    asset_id: Optional[int] = Query(None),
    evaluation_status: Optional[EvaluationStatusEnum] = Query(None),
    severity: Optional[RuleSeverityEnum] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.CLOUDSEC_READ)),
):
    """List CSPM findings for the authenticated organization."""
    return CloudSecService.list_findings(
        db=db,
        org_id=current_user.organization_id,
        asset_id=asset_id,
        evaluation_status=evaluation_status,
        severity=severity,
    )


# ─── 4. CONFIGURATION DRIFT ───────────────────────────────────────────────────

@router.post("/drifts", response_model=CloudConfigurationDriftResponse, status_code=status.HTTP_201_CREATED)
def record_drift(
    payload: CloudConfigurationDriftCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.CLOUDSEC_ASSESS)),
):
    """Record a detected configuration drift event."""
    return CloudSecService.record_drift(
        db=db,
        org_id=current_user.organization_id,
        user_id=current_user.id,
        data=payload,
    )


@router.get("/drifts", response_model=List[CloudConfigurationDriftResponse])
def list_drifts(
    asset_id: Optional[int] = Query(None),
    drift_status: Optional[DriftStatusEnum] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.CLOUDSEC_READ)),
):
    """List configuration drift events for the tenant."""
    return CloudSecService.list_drifts(
        db=db,
        org_id=current_user.organization_id,
        asset_id=asset_id,
        drift_status=drift_status,
    )


# ─── 5. IAM BLAST RADIUS ──────────────────────────────────────────────────────

@router.post("/blast-radius", response_model=CloudIAMBlastRadiusResponse, status_code=status.HTTP_201_CREATED)
def analyze_iam_blast_radius(
    payload: CloudIAMBlastRadiusCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.CLOUDSEC_ASSESS)),
):
    """Execute authoritative IAM Blast Radius calculation on a cloud principal/asset."""
    return CloudSecService.analyze_iam_blast_radius(
        db=db,
        org_id=current_user.organization_id,
        user_id=current_user.id,
        data=payload,
    )


@router.post("/blast-radius/preview", response_model=CloudIAMBlastRadiusPreviewResponse)
def preview_iam_blast_radius(
    payload: CloudIAMBlastRadiusPreviewRequest,
    current_user: User = Depends(require_permission(Permission.CLOUDSEC_READ)),
):
    """Preview IAM blast radius score calculation server-side without persisting."""
    return CloudSecService.preview_iam_blast_radius(data=payload)


# ─── 6. POSTURE SUMMARY & TELEMETRY ───────────────────────────────────────────

@router.get("/posture/summary", response_model=CloudPostureSummaryResponse)
def get_posture_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.CLOUDSEC_READ)),
):
    """Get aggregated executive CSPM posture metrics for the organization."""
    return CloudSecService.get_posture_summary(
        db=db,
        org_id=current_user.organization_id,
    )

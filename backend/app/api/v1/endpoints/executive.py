import io
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.core.permissions import Permission
from app.models.executive import (
    ArtifactTypeEnum,
    BriefingStatusEnum,
    DossierStatusEnum,
    DossierTypeEnum,
    ExportFormatEnum,
)
from app.models.user import User
from app.schemas.executive import (
    ExecutiveBriefingCreate,
    ExecutiveBriefingResponse,
    ExecutiveBriefingReview,
    ExecutiveDossierCreate,
    ExecutiveDossierResponse,
    ExecutiveDossierUpdate,
    ExecutiveExportArtifactResponse,
    ExecutiveSnapshotCreate,
    ExecutiveSnapshotResponse,
    ExecutiveTelemetryResponse,
    ExecutiveTrendsResponse,
)
from app.services.executive_service import ExecutiveService

router = APIRouter()


# ─── 1. TELEMETRY & AGGREGATION ──────────────────────────────────────────────

@router.get("/telemetry/live", response_model=ExecutiveTelemetryResponse)
def get_live_telemetry(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXECUTIVE_READ)),
):
    """Retrieve real-time server-calculated executive cyber-risk and posture telemetry."""
    telemetry, _ = ExecutiveService.calculate_live_telemetry(
        db=db,
        org_id=current_user.organization_id,
    )
    return telemetry


@router.get("/telemetry/trends", response_model=ExecutiveTrendsResponse)
def get_historical_trends(
    window_days: int = Query(90, ge=1, le=1095),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXECUTIVE_READ)),
):
    """Retrieve historical executive posture trend line data points from immutable snapshots."""
    return ExecutiveService.calculate_historical_trends(
        db=db,
        org_id=current_user.organization_id,
        window_days=window_days,
    )


@router.get("/telemetry/domain-matrix")
def get_domain_matrix(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXECUTIVE_READ)),
):
    """Retrieve detailed domain health matrix across all 10 governance dimensions."""
    telemetry, _ = ExecutiveService.calculate_live_telemetry(
        db=db,
        org_id=current_user.organization_id,
    )
    return {
        "overall_posture_score": telemetry.overall_posture_score,
        "domains": telemetry.domain_posture_breakdown,
        "calculated_at": telemetry.calculated_at,
    }


# ─── 2. IMMUTABLE POSTURE SNAPSHOTS ──────────────────────────────────────────

@router.post("/snapshots", response_model=ExecutiveSnapshotResponse, status_code=status.HTTP_201_CREATED)
def capture_snapshot(
    payload: ExecutiveSnapshotCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXECUTIVE_MANAGE)),
):
    """Capture a point-in-time immutable executive posture snapshot with cryptographic hash."""
    return ExecutiveService.capture_snapshot(
        db=db,
        org_id=current_user.organization_id,
        user_id=current_user.id,
        data=payload,
    )


@router.get("/snapshots", response_model=List[ExecutiveSnapshotResponse])
def list_snapshots(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXECUTIVE_READ)),
):
    """List historical posture snapshots for the authenticated organization."""
    return ExecutiveService.list_snapshots(
        db=db,
        org_id=current_user.organization_id,
    )


@router.get("/snapshots/{snapshot_id}", response_model=ExecutiveSnapshotResponse)
def get_snapshot(
    snapshot_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXECUTIVE_READ)),
):
    """Get single immutable snapshot detail and lineage manifest."""
    return ExecutiveService.get_snapshot(
        db=db,
        org_id=current_user.organization_id,
        snapshot_id=snapshot_id,
    )


# ─── 3. REGULATORY DOSSIERS ──────────────────────────────────────────────────

@router.post("/dossiers", response_model=ExecutiveDossierResponse, status_code=status.HTTP_201_CREATED)
def create_dossier(
    payload: ExecutiveDossierCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXECUTIVE_MANAGE)),
):
    """Create a new multi-framework regulatory compliance dossier manifest."""
    return ExecutiveService.create_dossier(
        db=db,
        org_id=current_user.organization_id,
        user_id=current_user.id,
        data=payload,
    )


@router.get("/dossiers", response_model=List[ExecutiveDossierResponse])
def list_dossiers(
    status_filter: Optional[DossierStatusEnum] = Query(None, alias="status"),
    dossier_type: Optional[DossierTypeEnum] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXECUTIVE_READ)),
):
    """List regulatory compliance dossiers."""
    return ExecutiveService.list_dossiers(
        db=db,
        org_id=current_user.organization_id,
        status_filter=status_filter,
        dossier_type=dossier_type,
    )


@router.get("/dossiers/{dossier_id}", response_model=ExecutiveDossierResponse)
def get_dossier(
    dossier_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXECUTIVE_READ)),
):
    """Get single regulatory dossier detail."""
    return ExecutiveService.get_dossier(
        db=db,
        org_id=current_user.organization_id,
        dossier_id=dossier_id,
    )


@router.patch("/dossiers/{dossier_id}", response_model=ExecutiveDossierResponse)
def update_dossier(
    dossier_id: int,
    payload: ExecutiveDossierUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXECUTIVE_MANAGE)),
):
    """Update draft regulatory dossier parameters."""
    return ExecutiveService.update_dossier(
        db=db,
        org_id=current_user.organization_id,
        user_id=current_user.id,
        dossier_id=dossier_id,
        data=payload,
    )


@router.post("/dossiers/{dossier_id}/compile", response_model=ExecutiveDossierResponse)
def compile_dossier(
    dossier_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXECUTIVE_MANAGE)),
):
    """Compile multi-framework evidence, controls, and findings into dossier sections."""
    return ExecutiveService.compile_dossier(
        db=db,
        org_id=current_user.organization_id,
        user_id=current_user.id,
        dossier_id=dossier_id,
    )


@router.post("/dossiers/{dossier_id}/finalize", response_model=ExecutiveDossierResponse)
def finalize_dossier(
    dossier_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXECUTIVE_APPROVE)),
):
    """Execute Four-Eyes finalization of a compiled regulatory dossier."""
    return ExecutiveService.finalize_dossier(
        db=db,
        org_id=current_user.organization_id,
        user_id=current_user.id,
        dossier_id=dossier_id,
    )


# ─── 4. EXECUTIVE & BOARD BRIEFINGS ──────────────────────────────────────────

@router.post("/briefings", response_model=ExecutiveBriefingResponse, status_code=status.HTTP_201_CREATED)
def generate_briefing(
    payload: ExecutiveBriefingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXECUTIVE_MANAGE)),
):
    """Generate a periodic board briefing draft with period-over-period delta analysis."""
    return ExecutiveService.generate_briefing(
        db=db,
        org_id=current_user.organization_id,
        user_id=current_user.id,
        data=payload,
    )


@router.get("/briefings", response_model=List[ExecutiveBriefingResponse])
def list_briefings(
    status_filter: Optional[BriefingStatusEnum] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXECUTIVE_READ)),
):
    """List executive and board briefings."""
    return ExecutiveService.list_briefings(
        db=db,
        org_id=current_user.organization_id,
        status_filter=status_filter,
    )


@router.get("/briefings/{briefing_id}", response_model=ExecutiveBriefingResponse)
def get_briefing(
    briefing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXECUTIVE_READ)),
):
    """Get single executive briefing detail."""
    return ExecutiveService.get_briefing(
        db=db,
        org_id=current_user.organization_id,
        briefing_id=briefing_id,
    )


@router.post("/briefings/{briefing_id}/submit", response_model=ExecutiveBriefingResponse)
def submit_briefing(
    briefing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXECUTIVE_MANAGE)),
):
    """Submit draft briefing for executive sign-off."""
    return ExecutiveService.submit_briefing(
        db=db,
        org_id=current_user.organization_id,
        user_id=current_user.id,
        briefing_id=briefing_id,
    )


@router.post("/briefings/{briefing_id}/review", response_model=ExecutiveBriefingResponse)
def review_briefing(
    briefing_id: int,
    payload: ExecutiveBriefingReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXECUTIVE_APPROVE)),
):
    """Execute Four-Eyes sign-off on executive briefing (self-approval blocked)."""
    return ExecutiveService.review_briefing(
        db=db,
        org_id=current_user.organization_id,
        reviewer_id=current_user.id,
        briefing_id=briefing_id,
        review=payload,
    )


# ─── 5. FORENSIC EXPORTS (PDF & JSON) ────────────────────────────────────────

@router.post("/exports/snapshot/{snapshot_id}", response_model=ExecutiveExportArtifactResponse, status_code=status.HTTP_201_CREATED)
def export_snapshot(
    snapshot_id: int,
    export_format: ExportFormatEnum = Query(ExportFormatEnum.PDF, alias="format"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXECUTIVE_EXPORT)),
):
    """Generate forensic PDF or JSON export artifact for a posture snapshot."""
    if export_format == ExportFormatEnum.PDF:
        return ExecutiveService.generate_pdf_export(
            db=db,
            org_id=current_user.organization_id,
            user_id=current_user.id,
            artifact_type=ArtifactTypeEnum.POSTURE_SNAPSHOT,
            resource_id=snapshot_id,
        )
    return ExecutiveService.generate_json_export(
        db=db,
        org_id=current_user.organization_id,
        user_id=current_user.id,
        artifact_type=ArtifactTypeEnum.POSTURE_SNAPSHOT,
        resource_id=snapshot_id,
    )


@router.post("/exports/dossier/{dossier_id}", response_model=ExecutiveExportArtifactResponse, status_code=status.HTTP_201_CREATED)
def export_dossier(
    dossier_id: int,
    export_format: ExportFormatEnum = Query(ExportFormatEnum.PDF, alias="format"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXECUTIVE_EXPORT)),
):
    """Generate forensic PDF or JSON regulatory dossier export package."""
    if export_format == ExportFormatEnum.PDF:
        return ExecutiveService.generate_pdf_export(
            db=db,
            org_id=current_user.organization_id,
            user_id=current_user.id,
            artifact_type=ArtifactTypeEnum.DOSSIER_PACKAGE,
            resource_id=dossier_id,
        )
    return ExecutiveService.generate_json_export(
        db=db,
        org_id=current_user.organization_id,
        user_id=current_user.id,
        artifact_type=ArtifactTypeEnum.DOSSIER_PACKAGE,
        resource_id=dossier_id,
    )


@router.post("/exports/briefing/{briefing_id}", response_model=ExecutiveExportArtifactResponse, status_code=status.HTTP_201_CREATED)
def export_briefing(
    briefing_id: int,
    export_format: ExportFormatEnum = Query(ExportFormatEnum.PDF, alias="format"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXECUTIVE_EXPORT)),
):
    """Generate forensic PDF or JSON executive briefing artifact."""
    if export_format == ExportFormatEnum.PDF:
        return ExecutiveService.generate_pdf_export(
            db=db,
            org_id=current_user.organization_id,
            user_id=current_user.id,
            artifact_type=ArtifactTypeEnum.EXECUTIVE_BRIEFING,
            resource_id=briefing_id,
        )
    return ExecutiveService.generate_json_export(
        db=db,
        org_id=current_user.organization_id,
        user_id=current_user.id,
        artifact_type=ArtifactTypeEnum.EXECUTIVE_BRIEFING,
        resource_id=briefing_id,
    )


@router.get("/exports", response_model=List[ExecutiveExportArtifactResponse])
def list_exports(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXECUTIVE_READ)),
):
    """List forensic export artifacts generated for the organization."""
    return ExecutiveService.list_exports(
        db=db,
        org_id=current_user.organization_id,
    )


@router.get("/exports/{export_id}/download")
def download_export(
    export_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.EXECUTIVE_EXPORT)),
):
    """Download forensic export artifact with SHA-256 integrity verification."""
    file_bytes, filename, mime_type = ExecutiveService.get_export_stream(
        db=db,
        org_id=current_user.organization_id,
        user_id=current_user.id,
        export_id=export_id,
    )

    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=mime_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

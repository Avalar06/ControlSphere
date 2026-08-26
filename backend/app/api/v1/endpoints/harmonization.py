from datetime import datetime, timezone
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_permission
from app.core.permissions import Permission
from app.models.framework import Framework
from app.models.harmonization import (
    CommonControlDomainEnum,
    CommonControlMapping,
    FrameworkComplianceSnapshot,
    FrameworkCrosswalkMapping,
    RationalizationStatusEnum,
    RationalizedCommonControl,
)
from app.models.user import User
from app.schemas.harmonization import (
    CommonControlCreate,
    CommonControlDetailResponse,
    CommonControlMappingCreate,
    CommonControlMappingResponse,
    CommonControlResponse,
    CommonControlUpdate,
    CrosswalkMappingCreate,
    CrosswalkMappingResponse,
    CrosswalkMappingUpdate,
    FrameworkCompliancePostureOverview,
    FrameworkComplianceSnapshotResponse,
    FrameworkDetailedPostureResponse,
    HarmonizationEvaluationResponse,
    MultiFrameworkPostureResponse,
)
from app.services.harmonization_service import HarmonizationService

router = APIRouter()


# ── Global Crosswalk Mappings ─────────────────────────────────────────────────

@router.get("/crosswalks", response_model=List[CrosswalkMappingResponse])
def list_crosswalks(
    source_framework_id: Optional[int] = Query(None, description="Filter by source framework ID"),
    target_framework_id: Optional[int] = Query(None, description="Filter by target framework ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.HARMONIZATION_READ)),
) -> Any:
    """List normative framework crosswalk mappings."""
    crosswalks = HarmonizationService.list_crosswalks(
        db=db,
        source_framework_id=source_framework_id,
        target_framework_id=target_framework_id,
    )
    result = []
    for cw in crosswalks:
        resp = CrosswalkMappingResponse.model_validate(cw)
        if cw.source_subcategory:
            resp.source_identifier = cw.source_subcategory.identifier
            resp.source_title = cw.source_subcategory.title
        if cw.target_subcategory:
            resp.target_identifier = cw.target_subcategory.identifier
            resp.target_title = cw.target_subcategory.title
        result.append(resp)
    return result


@router.get("/crosswalks/{crosswalk_id}", response_model=CrosswalkMappingResponse)
def get_crosswalk(
    crosswalk_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.HARMONIZATION_READ)),
) -> Any:
    """Get single normative framework crosswalk mapping."""
    cw = HarmonizationService.get_crosswalk(db=db, crosswalk_id=crosswalk_id)
    resp = CrosswalkMappingResponse.model_validate(cw)
    if cw.source_subcategory:
        resp.source_identifier = cw.source_subcategory.identifier
        resp.source_title = cw.source_subcategory.title
    if cw.target_subcategory:
        resp.target_identifier = cw.target_subcategory.identifier
        resp.target_title = cw.target_subcategory.title
    return resp


@router.post("/crosswalks", response_model=CrosswalkMappingResponse, status_code=status.HTTP_201_CREATED)
def create_crosswalk(
    mapping_in: CrosswalkMappingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.CROSSWALK_ADMIN)),
) -> Any:
    """Create a global normative framework crosswalk mapping (ADMIN with crosswalk:admin only)."""
    mapping = HarmonizationService.create_crosswalk(
        db=db,
        mapping_in=mapping_in,
        current_user=current_user,
    )
    resp = CrosswalkMappingResponse.model_validate(mapping)
    if mapping.source_subcategory:
        resp.source_identifier = mapping.source_subcategory.identifier
        resp.source_title = mapping.source_subcategory.title
    if mapping.target_subcategory:
        resp.target_identifier = mapping.target_subcategory.identifier
        resp.target_title = mapping.target_subcategory.title
    return resp


@router.patch("/crosswalks/{crosswalk_id}", response_model=CrosswalkMappingResponse)
def update_crosswalk(
    crosswalk_id: int,
    mapping_update: CrosswalkMappingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.CROSSWALK_ADMIN)),
) -> Any:
    """Update a global normative framework crosswalk mapping (ADMIN with crosswalk:admin only)."""
    mapping = HarmonizationService.update_crosswalk(
        db=db,
        crosswalk_id=crosswalk_id,
        mapping_update=mapping_update,
        current_user=current_user,
    )
    resp = CrosswalkMappingResponse.model_validate(mapping)
    if mapping.source_subcategory:
        resp.source_identifier = mapping.source_subcategory.identifier
        resp.source_title = mapping.source_subcategory.title
    if mapping.target_subcategory:
        resp.target_identifier = mapping.target_subcategory.identifier
        resp.target_title = mapping.target_subcategory.title
    return resp


@router.delete("/crosswalks/{crosswalk_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_crosswalk(
    crosswalk_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.CROSSWALK_ADMIN)),
) -> None:
    """Delete a global normative framework crosswalk mapping (ADMIN with crosswalk:admin only)."""
    HarmonizationService.delete_crosswalk(
        db=db,
        crosswalk_id=crosswalk_id,
        current_user=current_user,
    )


# ── Rationalized Common Controls ──────────────────────────────────────────────

@router.get("/common-controls", response_model=List[CommonControlResponse])
def list_common_controls(
    domain: Optional[CommonControlDomainEnum] = Query(None, description="Filter by domain"),
    status_filter: Optional[RationalizationStatusEnum] = Query(None, alias="status", description="Filter by status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.HARMONIZATION_READ)),
) -> Any:
    """List tenant rationalized common control objectives with live inherited health telemetry."""
    common_controls = HarmonizationService.list_common_controls(
        db=db,
        organization_id=current_user.organization_id,
        domain=domain,
        status_filter=status_filter,
    )
    result = []
    for cc in common_controls:
        resp = CommonControlResponse.model_validate(cc)
        resp.mapped_controls_count = len(cc.mappings)
        result.append(resp)
    return result


@router.post("/common-controls", response_model=CommonControlResponse, status_code=status.HTTP_201_CREATED)
def create_common_control(
    cc_in: CommonControlCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.HARMONIZATION_MANAGE)),
) -> Any:
    """Create a rationalized common control objective for tenant."""
    cc = HarmonizationService.create_common_control(
        db=db,
        organization_id=current_user.organization_id,
        cc_in=cc_in,
        current_user=current_user,
    )
    resp = CommonControlResponse.model_validate(cc)
    resp.mapped_controls_count = len(cc.mappings)
    return resp


@router.get("/common-controls/{common_control_id}", response_model=CommonControlDetailResponse)
def get_common_control(
    common_control_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.HARMONIZATION_READ)),
) -> Any:
    """Get common control details with mapped organization controls and telemetry."""
    cc = HarmonizationService.get_common_control(
        db=db,
        organization_id=current_user.organization_id,
        common_control_id=common_control_id,
    )
    # Refresh health score
    score, status_enum = HarmonizationService.recalculate_common_control_health(
        db=db,
        organization_id=current_user.organization_id,
        common_control_id=common_control_id,
    )
    resp = CommonControlDetailResponse.model_validate(cc)
    resp.inherited_health_score = score
    resp.inherited_health_status = status_enum
    resp.mapped_controls_count = len(cc.mappings)

    # Populate mapped control details
    mapping_responses = []
    for m in cc.mappings:
        m_resp = CommonControlMappingResponse.model_validate(m)
        if m.organization_control and m.organization_control.subcategory:
            m_resp.control_subcategory_identifier = m.organization_control.subcategory.identifier
            m_resp.control_subcategory_title = m.organization_control.subcategory.title
            m_resp.control_status = m.organization_control.status.value
        mapping_responses.append(m_resp)
    resp.mappings = mapping_responses
    return resp


@router.patch("/common-controls/{common_control_id}", response_model=CommonControlResponse)
@router.put("/common-controls/{common_control_id}", response_model=CommonControlResponse)
def update_common_control(
    common_control_id: int,
    cc_update: CommonControlUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.HARMONIZATION_MANAGE)),
) -> Any:
    """Update common control metadata."""
    cc = HarmonizationService.update_common_control(
        db=db,
        organization_id=current_user.organization_id,
        common_control_id=common_control_id,
        cc_update=cc_update,
        current_user=current_user,
    )
    resp = CommonControlResponse.model_validate(cc)
    resp.mapped_controls_count = len(cc.mappings)
    return resp


# ── Common Control Mappings ───────────────────────────────────────────────────

@router.get("/common-controls/{common_control_id}/mappings", response_model=List[CommonControlMappingResponse])
def list_common_control_mappings(
    common_control_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.HARMONIZATION_READ)),
) -> Any:
    """List linked organization controls for a common control."""
    mappings = HarmonizationService.get_common_control_mappings(
        db=db,
        organization_id=current_user.organization_id,
        common_control_id=common_control_id,
    )
    result = []
    for m in mappings:
        resp = CommonControlMappingResponse.model_validate(m)
        if m.organization_control and m.organization_control.subcategory:
            resp.control_subcategory_identifier = m.organization_control.subcategory.identifier
            resp.control_subcategory_title = m.organization_control.subcategory.title
            resp.control_status = m.organization_control.status.value
        result.append(resp)
    return result


@router.post("/common-controls/{common_control_id}/mappings", response_model=CommonControlMappingResponse, status_code=status.HTTP_201_CREATED)
def map_organization_control(
    common_control_id: int,
    mapping_in: CommonControlMappingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.HARMONIZATION_MANAGE)),
) -> Any:
    """Link an organization control to a common control."""
    mapping = HarmonizationService.map_organization_control(
        db=db,
        organization_id=current_user.organization_id,
        common_control_id=common_control_id,
        organization_control_id=mapping_in.organization_control_id,
        weight=mapping_in.weight,
        current_user=current_user,
    )
    resp = CommonControlMappingResponse.model_validate(mapping)
    if mapping.organization_control and mapping.organization_control.subcategory:
        resp.control_subcategory_identifier = mapping.organization_control.subcategory.identifier
        resp.control_subcategory_title = mapping.organization_control.subcategory.title
        resp.control_status = mapping.organization_control.status.value
    return resp


@router.delete("/common-controls/{common_control_id}/mappings/{organization_control_id}", status_code=status.HTTP_204_NO_CONTENT)
def unmap_organization_control(
    common_control_id: int,
    organization_control_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.HARMONIZATION_MANAGE)),
) -> None:
    """Unlink an organization control from a common control."""
    HarmonizationService.unmap_organization_control(
        db=db,
        organization_id=current_user.organization_id,
        common_control_id=common_control_id,
        organization_control_id=organization_control_id,
        current_user=current_user,
    )


# ── Multi-Framework Evaluation & Posture ──────────────────────────────────────

@router.post("/evaluate", response_model=HarmonizationEvaluationResponse)
def execute_harmonization_evaluation(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.HARMONIZATION_EXECUTE)),
) -> Any:
    """Trigger deterministic multi-framework evaluation and snapshot creation for all frameworks."""
    cc_count, fw_count, snaps_created = HarmonizationService.execute_full_harmonization_evaluation(
        db=db,
        organization_id=current_user.organization_id,
        current_user=current_user,
    )
    return HarmonizationEvaluationResponse(
        organization_id=current_user.organization_id,
        evaluated_common_controls=cc_count,
        evaluated_frameworks=fw_count,
        snapshots_created=snaps_created,
        evaluated_at=datetime.now(timezone.utc),
    )


@router.post("/frameworks/{framework_id}/evaluate", response_model=FrameworkComplianceSnapshotResponse, status_code=status.HTTP_201_CREATED)
def evaluate_single_framework(
    framework_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.HARMONIZATION_EXECUTE)),
) -> Any:
    """Trigger deterministic evaluation for a single framework and produce an immutable snapshot."""
    snapshot = HarmonizationService.evaluate_single_framework(
        db=db,
        organization_id=current_user.organization_id,
        framework_id=framework_id,
        current_user=current_user,
    )
    resp = FrameworkComplianceSnapshotResponse.model_validate(snapshot)
    if snapshot.framework:
        resp.framework_identifier = snapshot.framework.identifier
        resp.framework_name = snapshot.framework.name
    return resp


@router.get("/posture", response_model=MultiFrameworkPostureResponse)
def get_multi_framework_posture(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.HARMONIZATION_READ)),
) -> Any:
    """Get multi-framework compliance posture overview with coverage and health metrics."""
    now = datetime.now(timezone.utc)
    frameworks = db.query(Framework).all()
    overviews: List[FrameworkCompliancePostureOverview] = []

    for fw in frameworks:
        ov, _ = HarmonizationService.calculate_framework_compliance_posture(
            db=db,
            organization_id=current_user.organization_id,
            framework_id=fw.id,
            eval_time=now,
        )
        overviews.append(ov)

    common_controls = db.query(RationalizedCommonControl).filter(
        RationalizedCommonControl.organization_id == current_user.organization_id
    ).all()
    avg_cc_health = 100.0
    if common_controls:
        avg_cc_health = round(sum(cc.inherited_health_score for cc in common_controls) / len(common_controls), 1)

    return MultiFrameworkPostureResponse(
        frameworks=overviews,
        total_common_controls=len(common_controls),
        average_common_control_health=avg_cc_health,
        evaluated_at=now,
    )


@router.get("/frameworks/{framework_id}/posture", response_model=FrameworkDetailedPostureResponse)
def get_framework_detailed_posture(
    framework_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.HARMONIZATION_READ)),
) -> Any:
    """Get detailed subcategory-by-subcategory compliance and crosswalk breakdown matrix."""
    return HarmonizationService.get_framework_detailed_posture(
        db=db,
        organization_id=current_user.organization_id,
        framework_id=framework_id,
    )


# ── Historical Compliance Snapshots ──────────────────────────────────────────

@router.get("/snapshots", response_model=List[FrameworkComplianceSnapshotResponse])
def list_compliance_snapshots(
    framework_id: Optional[int] = Query(None, description="Filter by framework ID"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.HARMONIZATION_READ)),
) -> Any:
    """List historical immutable framework compliance posture snapshots."""
    query = (
        db.query(FrameworkComplianceSnapshot)
        .filter(FrameworkComplianceSnapshot.organization_id == current_user.organization_id)
    )
    if framework_id:
        query = query.filter(FrameworkComplianceSnapshot.framework_id == framework_id)
    snapshots = query.order_by(FrameworkComplianceSnapshot.created_at.desc()).limit(limit).all()

    result = []
    for s in snapshots:
        resp = FrameworkComplianceSnapshotResponse.model_validate(s)
        if s.framework:
            resp.framework_identifier = s.framework.identifier
            resp.framework_name = s.framework.name
        result.append(resp)
    return result


@router.get("/frameworks/{framework_id}/snapshots", response_model=List[FrameworkComplianceSnapshotResponse])
def list_framework_specific_snapshots(
    framework_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.HARMONIZATION_READ)),
) -> Any:
    """List historical snapshots for a specific framework."""
    snapshots = HarmonizationService.list_framework_snapshots(
        db=db,
        organization_id=current_user.organization_id,
        framework_id=framework_id,
        limit=limit,
    )
    result = []
    for s in snapshots:
        resp = FrameworkComplianceSnapshotResponse.model_validate(s)
        if s.framework:
            resp.framework_identifier = s.framework.identifier
            resp.framework_name = s.framework.name
        result.append(resp)
    return result


@router.get("/snapshots/{snapshot_id}", response_model=FrameworkComplianceSnapshotResponse)
def get_snapshot(
    snapshot_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.HARMONIZATION_READ)),
) -> Any:
    """Get single immutable framework compliance snapshot with strict tenant isolation."""
    s = HarmonizationService.get_snapshot(
        db=db,
        organization_id=current_user.organization_id,
        snapshot_id=snapshot_id,
    )
    resp = FrameworkComplianceSnapshotResponse.model_validate(s)
    if s.framework:
        resp.framework_identifier = s.framework.identifier
        resp.framework_name = s.framework.name
    return resp

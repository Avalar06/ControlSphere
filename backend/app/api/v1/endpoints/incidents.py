from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.api.deps import get_current_user, get_db, require_permission
from app.core.permissions import Permission
from app.models.control import OrganizationControl
from app.models.incident import (
    DisclosureStatusEnum,
    DisclosureTriggerTypeEnum,
    IncidentCategoryEnum,
    IncidentControlLink,
    IncidentControlRelationshipEnum,
    IncidentRegulatoryDisclosure,
    IncidentSeverityEnum,
    IncidentStatusEnum,
    IncidentTimelineEvent,
    IncidentVendorLink,
    RegulatorEnum,
    RootCauseClassificationEnum,
    SecurityIncident,
    TimelineEventSourceEnum,
    TimelineEventTypeEnum,
)
from app.models.monitoring import ComplianceDriftAlert
from app.models.tprm import Vendor, VendorEngagement
from app.models.user import User
from app.schemas.incident import (
    IncidentCloseRequest,
    IncidentControlLinkCreate,
    IncidentControlLinkRead,
    IncidentCreate,
    IncidentDetailRead,
    IncidentMaterialityUpdate,
    IncidentOverviewResponse,
    IncidentRead,
    IncidentRegulatoryDisclosureCreate,
    IncidentRegulatoryDisclosureRead,
    IncidentRegulatoryExemptionRequest,
    IncidentRegulatoryNotificationRequest,
    IncidentStatusTransition,
    IncidentTimelineEventCreate,
    IncidentTimelineEventRead,
    IncidentUpdate,
    IncidentVendorLinkCreate,
    IncidentVendorLinkRead,
)
from app.services.audit_service import AuditService
from app.services.incident_service import IncidentService

router = APIRouter()


# ─── 1. OVERVIEW & TELEMETRY ─────────────────────────────────────────────────

@router.get("/overview", response_model=IncidentOverviewResponse)
def get_incidents_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.INCIDENT_READ)),
):
    """Deterministic aggregate incident overview and telemetry."""
    incidents = (
        db.query(SecurityIncident)
        .filter(SecurityIncident.organization_id == current_user.organization_id)
        .all()
    )

    total_incidents = len(incidents)
    open_count = sum(1 for inc in incidents if inc.status != IncidentStatusEnum.CLOSED)
    crit_high_count = sum(
        1 for inc in incidents if inc.severity in [IncidentSeverityEnum.CRITICAL, IncidentSeverityEnum.HIGH]
    )
    material_count = sum(1 for inc in incidents if inc.is_material)

    status_dist = {s.value: 0 for s in IncidentStatusEnum}
    severity_dist = {s.value: 0 for s in IncidentSeverityEnum}
    category_dist = {c.value: 0 for c in IncidentCategoryEnum}

    ttc_list: List[float] = []
    mttr_list: List[float] = []

    for inc in incidents:
        status_dist[inc.status.value] += 1
        severity_dist[inc.severity.value] += 1
        category_dist[inc.category.value] += 1

        ttc = IncidentService.calculate_ttc_hours(inc)
        if ttc is not None:
            ttc_list.append(ttc)

        mttr = IncidentService.calculate_mttr_hours(inc)
        if mttr is not None:
            mttr_list.append(mttr)

    avg_ttc = round(sum(ttc_list) / len(ttc_list), 2) if ttc_list else None
    avg_mttr = round(sum(mttr_list) / len(mttr_list), 2) if mttr_list else None

    # Calculate overdue disclosures
    now_utc = datetime.now(timezone.utc)
    disclosures = (
        db.query(IncidentRegulatoryDisclosure)
        .filter(IncidentRegulatoryDisclosure.organization_id == current_user.organization_id)
        .all()
    )
    overdue_count = sum(
        1
        for d in disclosures
        if d.status == DisclosureStatusEnum.OVERDUE
        or (d.status in [DisclosureStatusEnum.PENDING, DisclosureStatusEnum.DUE] and d.deadline_at < now_utc)
    )

    return IncidentOverviewResponse(
        total_incidents=total_incidents,
        open_incidents=open_count,
        critical_or_high_incidents=crit_high_count,
        material_incidents=material_count,
        overdue_disclosures=overdue_count,
        status_distribution=status_dist,
        severity_distribution=severity_dist,
        category_distribution=category_dist,
        average_ttc_hours=avg_ttc,
        average_mttr_hours=avg_mttr,
    )


# ─── 2. INCIDENT LISTING & SEARCH ────────────────────────────────────────────

@router.get("", response_model=List[IncidentRead])
def list_incidents(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.INCIDENT_READ)),
    status_filter: Optional[IncidentStatusEnum] = Query(None, alias="status"),
    severity_filter: Optional[IncidentSeverityEnum] = Query(None, alias="severity"),
    category_filter: Optional[IncidentCategoryEnum] = Query(None, alias="category"),
    is_material_filter: Optional[bool] = Query(None, alias="is_material"),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Retrieve filtered, strictly tenant-scoped incidents."""
    query = db.query(SecurityIncident).filter(
        SecurityIncident.organization_id == current_user.organization_id
    )

    if status_filter:
        query = query.filter(SecurityIncident.status == status_filter)
    if severity_filter:
        query = query.filter(SecurityIncident.severity == severity_filter)
    if category_filter:
        query = query.filter(SecurityIncident.category == category_filter)
    if is_material_filter is not None:
        query = query.filter(SecurityIncident.is_material == is_material_filter)
    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            (SecurityIncident.incident_code.ilike(s))
            | (SecurityIncident.title.ilike(s))
            | (SecurityIncident.description.ilike(s))
        )

    return query.order_by(desc(SecurityIncident.created_at)).offset(offset).limit(limit).all()


# ─── 3. INCIDENT DETAIL ──────────────────────────────────────────────────────

@router.get("/{incident_id}", response_model=IncidentDetailRead)
def get_incident_detail(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.INCIDENT_READ)),
):
    """Retrieve full incident detail including timeline, links, and disclosures."""
    incident = (
        db.query(SecurityIncident)
        .filter(
            SecurityIncident.id == incident_id,
            SecurityIncident.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Security Incident #{incident_id} not found.",
        )

    now_utc = datetime.now(timezone.utc)
    dec_at = incident.declared_at if incident.declared_at.tzinfo is not None else incident.declared_at.replace(tzinfo=timezone.utc)
    age_hours = round(max((now_utc - dec_at).total_seconds(), 0.0) / 3600.0, 2)
    ttc = IncidentService.calculate_ttc_hours(incident)
    mttr = IncidentService.calculate_mttr_hours(incident)

    timeline_sorted = sorted(incident.timeline_events, key=lambda e: (e.event_occurred_at, e.id))

    return IncidentDetailRead(
        id=incident.id,
        organization_id=incident.organization_id,
        incident_code=incident.incident_code,
        title=incident.title,
        description=incident.description,
        severity=incident.severity,
        category=incident.category,
        status=incident.status,
        incident_commander_id=incident.incident_commander_id,
        business_owner_id=incident.business_owner_id,
        closed_by_id=incident.closed_by_id,
        detected_at=incident.detected_at,
        declared_at=incident.declared_at,
        contained_at=incident.contained_at,
        eradicated_at=incident.eradicated_at,
        recovered_at=incident.recovered_at,
        post_mortem_at=incident.post_mortem_at,
        closed_at=incident.closed_at,
        affected_record_count=incident.affected_record_count,
        affected_systems_summary=incident.affected_systems_summary,
        financial_impact_estimate=incident.financial_impact_estimate,
        is_material=incident.is_material,
        materiality_determined_at=incident.materiality_determined_at,
        materiality_determined_by_id=incident.materiality_determined_by_id,
        root_cause_classification=incident.root_cause_classification,
        root_cause_narrative=incident.root_cause_narrative,
        lessons_learned=incident.lessons_learned,
        closure_notes=incident.closure_notes,
        compliance_drift_alert_id=incident.compliance_drift_alert_id,
        created_at=incident.created_at,
        updated_at=incident.updated_at,
        timeline_events=[IncidentTimelineEventRead.model_validate(e) for e in timeline_sorted],
        disclosures=[IncidentRegulatoryDisclosureRead.model_validate(d) for d in incident.disclosures],
        control_links=[IncidentControlLinkRead.model_validate(c) for c in incident.control_links],
        vendor_links=[IncidentVendorLinkRead.model_validate(v) for v in incident.vendor_links],
        ttc_hours=ttc,
        mttr_hours=mttr,
        incident_age_hours=age_hours,
    )


# ─── 4. INCIDENT CREATION ────────────────────────────────────────────────────

@router.post("", response_model=IncidentRead, status_code=status.HTTP_201_CREATED)
def create_incident(
    payload: IncidentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.INCIDENT_MANAGE)),
):
    """Create a new security incident."""
    # Check duplicate incident code in tenant
    existing = (
        db.query(SecurityIncident)
        .filter(
            SecurityIncident.organization_id == current_user.organization_id,
            SecurityIncident.incident_code == payload.incident_code.strip().upper(),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Incident code '{payload.incident_code.upper()}' already exists in your organization.",
        )

    # Validate compliance_drift_alert_id if supplied
    if payload.compliance_drift_alert_id:
        alert = (
            db.query(ComplianceDriftAlert)
            .filter(
                ComplianceDriftAlert.id == payload.compliance_drift_alert_id,
                ComplianceDriftAlert.organization_id == current_user.organization_id,
            )
            .first()
        )
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"ComplianceDriftAlert #{payload.compliance_drift_alert_id} not found in your organization.",
            )

    # Validate business_owner_id if supplied
    if payload.business_owner_id:
        owner = (
            db.query(User)
            .filter(
                User.id == payload.business_owner_id,
                User.organization_id == current_user.organization_id,
            )
            .first()
        )
        if not owner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Business owner User #{payload.business_owner_id} not found in your organization.",
            )

    try:
        incident = IncidentService.create_incident(
            db=db,
            organization_id=current_user.organization_id,
            incident_commander_id=current_user.id,
            incident_code=payload.incident_code,
            title=payload.title,
            description=payload.description,
            severity=payload.severity,
            category=payload.category,
            detected_at=payload.detected_at,
            declared_at=payload.declared_at,
            business_owner_id=payload.business_owner_id,
            affected_record_count=payload.affected_record_count,
            affected_systems_summary=payload.affected_systems_summary,
            financial_impact_estimate=payload.financial_impact_estimate,
            compliance_drift_alert_id=payload.compliance_drift_alert_id,
        )
        return incident
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


# ─── 5. INCIDENT METADATA UPDATE ─────────────────────────────────────────────

@router.patch("/{incident_id}", response_model=IncidentRead)
def update_incident(
    incident_id: int,
    payload: IncidentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.INCIDENT_MANAGE)),
):
    """Update mutable incident metadata. Rejects closed incidents with 409 Conflict."""
    incident = (
        db.query(SecurityIncident)
        .filter(
            SecurityIncident.id == incident_id,
            SecurityIncident.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Security Incident #{incident_id} not found.",
        )

    if incident.status == IncidentStatusEnum.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Closed incidents are permanently immutable and cannot be updated.",
        )

    if payload.business_owner_id:
        owner = (
            db.query(User)
            .filter(
                User.id == payload.business_owner_id,
                User.organization_id == current_user.organization_id,
            )
            .first()
        )
        if not owner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Business owner User #{payload.business_owner_id} not found in your organization.",
            )

    try:
        updated = IncidentService.update_incident_metadata(
            db=db,
            incident=incident,
            user_id=current_user.id,
            title=payload.title,
            description=payload.description,
            severity=payload.severity,
            category=payload.category,
            business_owner_id=payload.business_owner_id,
            affected_record_count=payload.affected_record_count,
            affected_systems_summary=payload.affected_systems_summary,
            financial_impact_estimate=payload.financial_impact_estimate,
            root_cause_classification=payload.root_cause_classification,
            root_cause_narrative=payload.root_cause_narrative,
            lessons_learned=payload.lessons_learned,
        )
        return updated
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


# ─── 6. LIFECYCLE TRANSITION ─────────────────────────────────────────────────

@router.post("/{incident_id}/transition", response_model=IncidentRead)
def transition_incident_lifecycle(
    incident_id: int,
    payload: IncidentStatusTransition,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.INCIDENT_MANAGE)),
):
    """Transition progressive incident lifecycle state."""
    incident = (
        db.query(SecurityIncident)
        .filter(
            SecurityIncident.id == incident_id,
            SecurityIncident.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Security Incident #{incident_id} not found.",
        )

    if incident.status == IncidentStatusEnum.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Closed incidents are permanently immutable.",
        )

    if payload.target_status == IncidentStatusEnum.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="To close an incident, use the dedicated /close endpoint with mandatory Four-Eyes approval.",
        )

    try:
        updated = IncidentService.transition_lifecycle(
            db=db,
            incident=incident,
            target_status=payload.target_status,
            user_id=current_user.id,
            notes=payload.notes,
        )
        return updated
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ─── 7. FOUR-EYES INCIDENT CLOSURE ───────────────────────────────────────────

@router.post("/{incident_id}/close", response_model=IncidentRead)
def close_incident(
    incident_id: int,
    payload: IncidentCloseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.INCIDENT_CLOSE)),
):
    """Close incident under strict Four-Eyes governance."""
    incident = (
        db.query(SecurityIncident)
        .filter(
            SecurityIncident.id == incident_id,
            SecurityIncident.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Security Incident #{incident_id} not found.",
        )

    if incident.status == IncidentStatusEnum.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Incident is already CLOSED.",
        )

    if incident.status != IncidentStatusEnum.POST_MORTEM:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Incident must be in POST_MORTEM status before closing. Current status: '{incident.status.value}'.",
        )

    if current_user.id == incident.incident_commander_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Separation of duties violation: The Incident Commander cannot close their own incident. Independent manager review is required.",
        )

    try:
        closed = IncidentService.close_incident(
            db=db,
            incident=incident,
            closed_by_id=current_user.id,
            closure_notes=payload.closure_notes,
            lessons_learned=payload.lessons_learned,
            root_cause_classification=payload.root_cause_classification,
            root_cause_narrative=payload.root_cause_narrative,
        )
        return closed
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ─── 8. SEC MATERIALITY DETERMINATION ────────────────────────────────────────

@router.post("/{incident_id}/materiality", response_model=IncidentRead)
def set_incident_materiality(
    incident_id: int,
    payload: IncidentMaterialityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.INCIDENT_MANAGE)),
):
    """Set SEC Item 1.05 materiality determination."""
    incident = (
        db.query(SecurityIncident)
        .filter(
            SecurityIncident.id == incident_id,
            SecurityIncident.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Security Incident #{incident_id} not found.",
        )

    if incident.status == IncidentStatusEnum.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Closed incidents are permanently immutable.",
        )

    try:
        updated = IncidentService.set_materiality(
            db=db,
            incident=incident,
            user_id=current_user.id,
            is_material=payload.is_material,
            materiality_notes=payload.materiality_notes,
        )
        return updated
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ─── 9. TIMELINE MANAGEMENT (APPEND-ONLY) ────────────────────────────────────

@router.get("/{incident_id}/timeline", response_model=List[IncidentTimelineEventRead])
def get_incident_timeline(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.INCIDENT_READ)),
):
    """Retrieve chronologically ordered immutable forensic timeline."""
    incident = (
        db.query(SecurityIncident)
        .filter(
            SecurityIncident.id == incident_id,
            SecurityIncident.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Security Incident #{incident_id} not found.",
        )

    events = (
        db.query(IncidentTimelineEvent)
        .filter(
            IncidentTimelineEvent.incident_id == incident_id,
            IncidentTimelineEvent.organization_id == current_user.organization_id,
        )
        .order_by(IncidentTimelineEvent.event_occurred_at.asc(), IncidentTimelineEvent.id.asc())
        .all()
    )
    return events


@router.post("/{incident_id}/timeline", response_model=IncidentTimelineEventRead, status_code=status.HTTP_201_CREATED)
def append_incident_timeline_event(
    incident_id: int,
    payload: IncidentTimelineEventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.INCIDENT_MANAGE)),
):
    """Append an immutable event to the incident timeline."""
    incident = (
        db.query(SecurityIncident)
        .filter(
            SecurityIncident.id == incident_id,
            SecurityIncident.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Security Incident #{incident_id} not found.",
        )

    if incident.status == IncidentStatusEnum.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Closed incidents are permanently immutable and cannot accept new timeline entries.",
        )

    event = IncidentService.append_timeline_event(
        db=db,
        incident=incident,
        actor_id=current_user.id,
        event_type=payload.event_type,
        event_occurred_at=payload.event_occurred_at,
        description=payload.description,
        source=payload.source,
    )
    return event


# ─── 10. CONTROL LINKAGES ────────────────────────────────────────────────────

@router.post("/{incident_id}/controls", response_model=IncidentControlLinkRead, status_code=status.HTTP_201_CREATED)
def link_control_to_incident(
    incident_id: int,
    payload: IncidentControlLinkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.INCIDENT_MANAGE)),
):
    """Link an OrganizationControl to this incident."""
    incident = (
        db.query(SecurityIncident)
        .filter(
            SecurityIncident.id == incident_id,
            SecurityIncident.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Security Incident #{incident_id} not found.",
        )

    if incident.status == IncidentStatusEnum.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Closed incidents are permanently immutable.",
        )

    control = (
        db.query(OrganizationControl)
        .filter(
            OrganizationControl.id == payload.organization_control_id,
            OrganizationControl.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not control:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"OrganizationControl #{payload.organization_control_id} not found in your organization.",
        )

    existing = (
        db.query(IncidentControlLink)
        .filter(
            IncidentControlLink.organization_id == current_user.organization_id,
            IncidentControlLink.incident_id == incident_id,
            IncidentControlLink.organization_control_id == payload.organization_control_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Control #{payload.organization_control_id} is already linked to this incident.",
        )

    try:
        link = IncidentService.link_control(
            db=db,
            incident=incident,
            organization_control_id=payload.organization_control_id,
            relationship_type=payload.relationship_type,
            notes=payload.notes,
        )
        return link
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{incident_id}/controls/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_control_from_incident(
    incident_id: int,
    link_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.INCIDENT_MANAGE)),
):
    """Unlink an OrganizationControl association."""
    incident = (
        db.query(SecurityIncident)
        .filter(
            SecurityIncident.id == incident_id,
            SecurityIncident.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Security Incident #{incident_id} not found.",
        )

    if incident.status == IncidentStatusEnum.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Closed incidents are permanently immutable.",
        )

    link = (
        db.query(IncidentControlLink)
        .filter(
            IncidentControlLink.id == link_id,
            IncidentControlLink.incident_id == incident_id,
            IncidentControlLink.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"IncidentControlLink #{link_id} not found.",
        )

    IncidentService.unlink_control(db=db, incident=incident, link_id=link_id)
    return None


# ─── 11. VENDOR LINKAGES ─────────────────────────────────────────────────────

@router.post("/{incident_id}/vendors", response_model=IncidentVendorLinkRead, status_code=status.HTTP_201_CREATED)
def link_vendor_to_incident(
    incident_id: int,
    payload: IncidentVendorLinkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.INCIDENT_MANAGE)),
):
    """Link a Phase 9 Vendor / VendorEngagement to this incident."""
    incident = (
        db.query(SecurityIncident)
        .filter(
            SecurityIncident.id == incident_id,
            SecurityIncident.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Security Incident #{incident_id} not found.",
        )

    if incident.status == IncidentStatusEnum.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Closed incidents are permanently immutable.",
        )

    vendor = (
        db.query(Vendor)
        .filter(
            Vendor.id == payload.vendor_id,
            Vendor.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor #{payload.vendor_id} not found in your organization.",
        )

    if payload.vendor_engagement_id:
        engagement = (
            db.query(VendorEngagement)
            .filter(
                VendorEngagement.id == payload.vendor_engagement_id,
                VendorEngagement.vendor_id == payload.vendor_id,
                VendorEngagement.organization_id == current_user.organization_id,
            )
            .first()
        )
        if not engagement:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"VendorEngagement #{payload.vendor_engagement_id} does not belong to Vendor #{payload.vendor_id}.",
            )

    existing = (
        db.query(IncidentVendorLink)
        .filter(
            IncidentVendorLink.organization_id == current_user.organization_id,
            IncidentVendorLink.incident_id == incident_id,
            IncidentVendorLink.vendor_id == payload.vendor_id,
            IncidentVendorLink.vendor_engagement_id == payload.vendor_engagement_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This vendor / engagement is already linked to this incident.",
        )

    try:
        link = IncidentService.link_vendor(
            db=db,
            incident=incident,
            vendor_id=payload.vendor_id,
            vendor_engagement_id=payload.vendor_engagement_id,
            is_vendor_originated=payload.is_vendor_originated,
            notes=payload.notes,
        )
        return link
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{incident_id}/vendors/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_vendor_from_incident(
    incident_id: int,
    link_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.INCIDENT_MANAGE)),
):
    """Unlink a Vendor association."""
    incident = (
        db.query(SecurityIncident)
        .filter(
            SecurityIncident.id == incident_id,
            SecurityIncident.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Security Incident #{incident_id} not found.",
        )

    if incident.status == IncidentStatusEnum.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Closed incidents are permanently immutable.",
        )

    link = (
        db.query(IncidentVendorLink)
        .filter(
            IncidentVendorLink.id == link_id,
            IncidentVendorLink.incident_id == incident_id,
            IncidentVendorLink.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"IncidentVendorLink #{link_id} not found.",
        )

    IncidentService.unlink_vendor(db=db, incident=incident, link_id=link_id)
    return None


# ─── 12. REGULATORY DISCLOSURE MANAGEMENT ────────────────────────────────────

@router.get("/{incident_id}/disclosures", response_model=List[IncidentRegulatoryDisclosureRead])
def list_incident_disclosures(
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.INCIDENT_READ)),
):
    """List regulatory disclosure countdown records for an incident."""
    incident = (
        db.query(SecurityIncident)
        .filter(
            SecurityIncident.id == incident_id,
            SecurityIncident.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Security Incident #{incident_id} not found.",
        )

    return incident.disclosures


@router.post("/{incident_id}/disclosures", response_model=IncidentRegulatoryDisclosureRead, status_code=status.HTTP_201_CREATED)
def evaluate_incident_disclosure(
    incident_id: int,
    payload: IncidentRegulatoryDisclosureCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.INCIDENT_DISCLOSE)),
):
    """Evaluate and initialize statutory regulatory disclosure clock."""
    incident = (
        db.query(SecurityIncident)
        .filter(
            SecurityIncident.id == incident_id,
            SecurityIncident.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Security Incident #{incident_id} not found.",
        )

    disclosure = IncidentService.evaluate_regulatory_disclosure(
        db=db,
        incident=incident,
        regulator=payload.regulator,
        triggered_by_id=current_user.id,
        trigger_type=payload.trigger_type,
        triggered_at=payload.triggered_at,
        rule_version=payload.rule_version,
    )
    return disclosure


@router.post("/disclosures/{disclosure_id}/notify", response_model=IncidentRegulatoryDisclosureRead)
def notify_regulatory_disclosure(
    disclosure_id: int,
    payload: IncidentRegulatoryNotificationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.INCIDENT_DISCLOSE)),
):
    """Record verified regulatory breach disclosure notification."""
    disclosure = (
        db.query(IncidentRegulatoryDisclosure)
        .filter(
            IncidentRegulatoryDisclosure.id == disclosure_id,
            IncidentRegulatoryDisclosure.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not disclosure:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"IncidentRegulatoryDisclosure #{disclosure_id} not found.",
        )

    updated = IncidentService.record_disclosure_notification(
        db=db,
        disclosure=disclosure,
        notified_by_id=current_user.id,
        notification_reference_code=payload.notification_reference_code,
        disclosure_notes=payload.disclosure_notes,
    )
    return updated


@router.post("/disclosures/{disclosure_id}/exempt", response_model=IncidentRegulatoryDisclosureRead)
def exempt_regulatory_disclosure(
    disclosure_id: int,
    payload: IncidentRegulatoryExemptionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.INCIDENT_DISCLOSE)),
):
    """Record legal regulatory exemption justification."""
    disclosure = (
        db.query(IncidentRegulatoryDisclosure)
        .filter(
            IncidentRegulatoryDisclosure.id == disclosure_id,
            IncidentRegulatoryDisclosure.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not disclosure:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"IncidentRegulatoryDisclosure #{disclosure_id} not found.",
        )

    try:
        updated = IncidentService.exempt_regulatory_disclosure(
            db=db,
            disclosure=disclosure,
            user_id=current_user.id,
            exemption_reason=payload.exemption_reason,
        )
        return updated
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

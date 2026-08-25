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
from app.models.risk import (
    RiskCategoryEnum,
    RiskSourceEnum,
    RiskStatusEnum,
    RiskTreatmentStrategyEnum,
)
from app.models.user import User
from app.schemas.risk import (
    HeatmapCell,
    RiskAcceptance,
    RiskControlLinkCreate,
    RiskControlLinkResponse,
    RiskCreate,
    RiskDetailResponse,
    RiskFindingLinkCreate,
    RiskFindingLinkResponse,
    RiskResponse,
    RiskStatsResponse,
    RiskStatusUpdate,
    RiskUpdate,
)
from app.services.audit_service import AuditService
from app.services.risk_service import RiskService

router = APIRouter()


@router.get("", response_model=List[RiskResponse])
def list_risks(
    status: Optional[RiskStatusEnum] = Query(None, description="Filter by risk status"),
    risk_category: Optional[RiskCategoryEnum] = Query(None, description="Filter by category"),
    risk_source: Optional[RiskSourceEnum] = Query(None, description="Filter by source"),
    treatment_strategy: Optional[RiskTreatmentStrategyEnum] = Query(None, description="Filter by treatment strategy"),
    inherent_band: Optional[str] = Query(None, description="Filter by inherent band (LOW, MODERATE, HIGH, CRITICAL)"),
    appetite_status: Optional[str] = Query(None, description="Filter by appetite status (WITHIN_APPETITE, NEAR_LIMIT, ABOVE_APPETITE)"),
    owner_id: Optional[int] = Query(None, description="Filter by owner ID"),
    overdue_treatment: bool = Query(False, description="Filter risks with overdue treatment"),
    search: Optional[str] = Query(None, description="Search keyword"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(require_permission(Permission.RISK_READ)),
    db: Session = Depends(get_db),
) -> Any:
    """List organization risks with comprehensive filtering and deterministic score evaluation."""
    return RiskService.list_risks(
        db=db,
        organization_id=current_user.organization_id,
        status=status,
        risk_category=risk_category,
        risk_source=risk_source,
        treatment_strategy=treatment_strategy,
        inherent_band=inherent_band,
        appetite_status=appetite_status,
        owner_id=owner_id,
        overdue_treatment=overdue_treatment,
        search=search,
        skip=skip,
        limit=limit,
    )


@router.get("/stats", response_model=RiskStatsResponse)
def get_risk_stats(
    current_user: User = Depends(require_permission(Permission.RISK_READ)),
    db: Session = Depends(get_db),
) -> Any:
    """Get aggregate enterprise risk posture statistics and risk reduction metrics."""
    return RiskService.get_stats(
        db=db, organization_id=current_user.organization_id
    )


@router.get("/heatmap", response_model=List[HeatmapCell])
def get_risk_heatmap(
    current_user: User = Depends(require_permission(Permission.RISK_READ)),
    db: Session = Depends(get_db),
) -> Any:
    """Get deterministic 5x5 inherent risk heatmap cell distribution."""
    return RiskService.get_heatmap(
        db=db, organization_id=current_user.organization_id
    )


@router.post("", response_model=RiskResponse, status_code=status.HTTP_201_CREATED)
def create_risk(
    request: Request,
    risk_in: RiskCreate,
    current_user: User = Depends(require_permission(Permission.RISK_MANAGE)),
    db: Session = Depends(get_db),
) -> Any:
    """Create a new risk with deterministic inherent score & appetite calculation."""
    try:
        new_risk = RiskService.create_risk(
            db=db,
            obj_in=risk_in,
            organization_id=current_user.organization_id,
            creator_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Audit log
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="risk.create",
        resource_type="RISK",
        resource_id=str(new_risk.id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={
            "title": new_risk.title,
            "category": new_risk.risk_category.value,
            "inherent_score": new_risk.inherent_score,
            "inherent_band": new_risk.inherent_band,
            "appetite_status": new_risk.appetite_status,
        },
    )

    return RiskService.get_risk_by_id(
        db=db, risk_id=new_risk.id, organization_id=current_user.organization_id
    )


@router.get("/{risk_id}", response_model=RiskDetailResponse)
def get_risk(
    risk_id: int,
    current_user: User = Depends(require_permission(Permission.RISK_READ)),
    db: Session = Depends(get_db),
) -> Any:
    """Retrieve full details of a specific risk including linked controls, findings, and treatment status."""
    r = RiskService.get_risk_by_id(
        db=db, risk_id=risk_id, organization_id=current_user.organization_id
    )
    if not r:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Risk not found in your organization.",
        )
    return r


@router.patch("/{risk_id}", response_model=RiskResponse)
def update_risk(
    request: Request,
    risk_id: int,
    risk_in: RiskUpdate,
    current_user: User = Depends(require_permission(Permission.RISK_MANAGE)),
    db: Session = Depends(get_db),
) -> Any:
    """Update metadata, inherent/residual evaluation, or treatment plan of an active risk."""
    try:
        updated = RiskService.update_risk(
            db=db,
            risk_id=risk_id,
            organization_id=current_user.organization_id,
            obj_in=risk_in,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Risk not found in your organization.",
        )

    # Audit log
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="risk.update",
        resource_type="RISK",
        resource_id=str(risk_id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={"updated_fields": list(risk_in.model_dump(exclude_unset=True).keys())},
    )

    return RiskService.get_risk_by_id(
        db=db, risk_id=risk_id, organization_id=current_user.organization_id
    )


@router.post("/{risk_id}/status", response_model=RiskResponse)
def update_risk_status(
    request: Request,
    risk_id: int,
    status_in: RiskStatusUpdate,
    current_user: User = Depends(require_permission(Permission.RISK_MANAGE)),
    db: Session = Depends(get_db),
) -> Any:
    """Transition risk lifecycle status in accordance with strict state machine rules."""
    try:
        updated = RiskService.update_status(
            db=db,
            risk_id=risk_id,
            organization_id=current_user.organization_id,
            status_in=status_in,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Risk not found in your organization.",
        )

    # Audit log
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="risk.status.change",
        resource_type="RISK",
        resource_id=str(risk_id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={"new_status": status_in.status.value, "notes": status_in.notes},
    )

    return RiskService.get_risk_by_id(
        db=db, risk_id=risk_id, organization_id=current_user.organization_id
    )


@router.post("/{risk_id}/risk-acceptance", response_model=RiskResponse)
def accept_risk(
    request: Request,
    risk_id: int,
    acceptance_in: RiskAcceptance,
    current_user: User = Depends(require_permission(Permission.RISK_ACCEPT)),
    db: Session = Depends(get_db),
) -> Any:
    """Formally accept risk with documented business justification and authorized reviewer timestamp."""
    try:
        accepted = RiskService.accept_risk(
            db=db,
            risk_id=risk_id,
            organization_id=current_user.organization_id,
            acceptance_in=acceptance_in,
            acceptor_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not accepted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Risk not found in your organization.",
        )

    # Audit log
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="risk.accept",
        resource_type="RISK",
        resource_id=str(risk_id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={
            "justification": acceptance_in.justification,
            "expiry_date": acceptance_in.expiry_date.isoformat() if acceptance_in.expiry_date else None,
            "inherent_score": accepted.inherent_score,
            "residual_score": accepted.residual_score,
        },
    )

    return RiskService.get_risk_by_id(
        db=db, risk_id=risk_id, organization_id=current_user.organization_id
    )


@router.post("/{risk_id}/controls", response_model=RiskControlLinkResponse, status_code=status.HTTP_201_CREATED)
def link_risk_control(
    request: Request,
    risk_id: int,
    link_in: RiskControlLinkCreate,
    current_user: User = Depends(require_permission(Permission.RISK_MANAGE)),
    db: Session = Depends(get_db),
) -> Any:
    """Link an organization control to a risk for mitigation traceability."""
    try:
        link = RiskService.link_control(
            db=db,
            risk_id=risk_id,
            organization_control_id=link_in.organization_control_id,
            organization_id=current_user.organization_id,
            creator_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Audit log
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="risk.control.link",
        resource_type="RISK_CONTROL_LINK",
        resource_id=str(link.id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={"risk_id": risk_id, "organization_control_id": link_in.organization_control_id},
    )

    return link


@router.delete("/{risk_id}/controls/{control_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_risk_control(
    request: Request,
    risk_id: int,
    control_id: int,
    current_user: User = Depends(require_permission(Permission.RISK_MANAGE)),
    db: Session = Depends(get_db),
) -> None:
    """Unlink an organization control from a risk."""
    success = RiskService.unlink_control(
        db=db,
        risk_id=risk_id,
        organization_control_id=control_id,
        organization_id=current_user.organization_id,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Risk control linkage not found in your organization.",
        )

    # Audit log
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="risk.control.unlink",
        resource_type="RISK_CONTROL_LINK",
        resource_id=f"{risk_id}:{control_id}",
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
    )


@router.post("/{risk_id}/findings", response_model=RiskFindingLinkResponse, status_code=status.HTTP_201_CREATED)
def link_risk_finding(
    request: Request,
    risk_id: int,
    link_in: RiskFindingLinkCreate,
    current_user: User = Depends(require_permission(Permission.RISK_MANAGE)),
    db: Session = Depends(get_db),
) -> Any:
    """Link an existing deficiency finding to a risk."""
    try:
        link = RiskService.link_finding(
            db=db,
            risk_id=risk_id,
            finding_id=link_in.finding_id,
            organization_id=current_user.organization_id,
            creator_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Audit log
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="risk.finding.link",
        resource_type="RISK_FINDING_LINK",
        resource_id=str(link.id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={"risk_id": risk_id, "finding_id": link_in.finding_id},
    )

    return link


@router.delete("/{risk_id}/findings/{finding_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_risk_finding(
    request: Request,
    risk_id: int,
    finding_id: int,
    current_user: User = Depends(require_permission(Permission.RISK_MANAGE)),
    db: Session = Depends(get_db),
) -> None:
    """Unlink a deficiency finding from a risk."""
    success = RiskService.unlink_finding(
        db=db,
        risk_id=risk_id,
        finding_id=finding_id,
        organization_id=current_user.organization_id,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Risk finding linkage not found in your organization.",
        )

    # Audit log
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="risk.finding.unlink",
        resource_type="RISK_FINDING_LINK",
        resource_id=f"{risk_id}:{finding_id}",
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
    )

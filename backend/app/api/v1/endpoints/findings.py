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
from app.models.finding import (
    FindingSeverityEnum,
    FindingStatusEnum,
    FindingTypeEnum,
)
from app.models.user import User
from app.schemas.finding import (
    FindingCreate,
    FindingDetailResponse,
    FindingEvidenceCreate,
    FindingEvidenceResponse,
    FindingResponse,
    FindingRiskAcceptance,
    FindingStatsResponse,
    FindingStatusUpdate,
    FindingUpdate,
    FindingValidation,
)
from app.services.audit_service import AuditService
from app.services.finding_service import FindingService

router = APIRouter()


@router.get("", response_model=List[FindingResponse])
def list_findings(
    organization_control_id: Optional[int] = Query(None, description="Filter by control ID"),
    assessment_id: Optional[int] = Query(None, description="Filter by assessment ID"),
    owner_id: Optional[int] = Query(None, description="Filter by owner ID"),
    status: Optional[FindingStatusEnum] = Query(None, description="Filter by finding status"),
    severity: Optional[FindingSeverityEnum] = Query(None, description="Filter by severity"),
    finding_type: Optional[FindingTypeEnum] = Query(None, description="Filter by finding type"),
    risk_band: Optional[str] = Query(None, description="Filter by risk band (LOW, MODERATE, HIGH, CRITICAL)"),
    overdue_only: bool = Query(False, description="Filter only overdue findings"),
    search: Optional[str] = Query(None, description="Search keywords"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(require_permission(Permission.FINDING_READ)),
    db: Session = Depends(get_db),
) -> Any:
    """List organization findings with multi-criteria filtering, risk scoring, and overdue status."""
    return FindingService.list_findings(
        db=db,
        organization_id=current_user.organization_id,
        organization_control_id=organization_control_id,
        assessment_id=assessment_id,
        owner_id=owner_id,
        status=status,
        severity=severity,
        finding_type=finding_type,
        risk_band=risk_band,
        overdue_only=overdue_only,
        search=search,
        skip=skip,
        limit=limit,
    )


@router.get("/stats", response_model=FindingStatsResponse)
def get_finding_stats(
    current_user: User = Depends(require_permission(Permission.FINDING_READ)),
    db: Session = Depends(get_db),
) -> Any:
    """Get organization risk posture statistics and finding counts."""
    return FindingService.get_stats(
        db=db, organization_id=current_user.organization_id
    )


@router.post("", response_model=FindingResponse, status_code=status.HTTP_201_CREATED)
def create_finding(
    request: Request,
    finding_in: FindingCreate,
    current_user: User = Depends(require_permission(Permission.FINDING_MANAGE)),
    db: Session = Depends(get_db),
) -> Any:
    """Create a new finding with deterministic risk score calculation."""
    try:
        new_finding = FindingService.create_finding(
            db=db,
            obj_in=finding_in,
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
        action="finding.create",
        resource_type="FINDING",
        resource_id=str(new_finding.id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={
            "title": new_finding.title,
            "severity": new_finding.severity.value,
            "risk_score": new_finding.risk_score,
            "risk_band": new_finding.risk_band,
            "control_id": new_finding.organization_control_id,
        },
    )

    return FindingService.get_finding_by_id(
        db=db, finding_id=new_finding.id, organization_id=current_user.organization_id
    )


@router.get("/{finding_id}", response_model=FindingDetailResponse)
def get_finding(
    finding_id: int,
    current_user: User = Depends(require_permission(Permission.FINDING_READ)),
    db: Session = Depends(get_db),
) -> Any:
    """Retrieve full details of a specific finding including linked evidence and remediation history."""
    f = FindingService.get_finding_by_id(
        db=db, finding_id=finding_id, organization_id=current_user.organization_id
    )
    if not f:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found in your organization.",
        )
    return f


@router.patch("/{finding_id}", response_model=FindingResponse)
def update_finding(
    request: Request,
    finding_id: int,
    finding_in: FindingUpdate,
    current_user: User = Depends(require_permission(Permission.FINDING_MANAGE)),
    db: Session = Depends(get_db),
) -> Any:
    """Update metadata, owner, or risk parameters of an active finding."""
    try:
        updated = FindingService.update_finding(
            db=db,
            finding_id=finding_id,
            organization_id=current_user.organization_id,
            obj_in=finding_in,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found in your organization.",
        )

    # Audit log
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="finding.update",
        resource_type="FINDING",
        resource_id=str(finding_id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={"updated_fields": list(finding_in.model_dump(exclude_unset=True).keys())},
    )

    return FindingService.get_finding_by_id(
        db=db, finding_id=finding_id, organization_id=current_user.organization_id
    )


@router.post("/{finding_id}/status", response_model=FindingResponse)
def update_finding_status(
    request: Request,
    finding_id: int,
    status_in: FindingStatusUpdate,
    current_user: User = Depends(require_permission(Permission.REMEDIATION_MANAGE)),
    db: Session = Depends(get_db),
) -> Any:
    """Update finding remediation status (e.g. IN_REMEDIATION, PENDING_VALIDATION, CLOSED)."""
    try:
        updated = FindingService.update_status(
            db=db,
            finding_id=finding_id,
            organization_id=current_user.organization_id,
            status_in=status_in,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found in your organization.",
        )

    # Audit log
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    action_name = "finding.close" if status_in.status.value == "CLOSED" else "finding.status.change"
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action=action_name,
        resource_type="FINDING",
        resource_id=str(finding_id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={"new_status": status_in.status.value, "notes": status_in.notes},
    )

    return FindingService.get_finding_by_id(
        db=db, finding_id=finding_id, organization_id=current_user.organization_id
    )


@router.post("/{finding_id}/validate", response_model=FindingResponse)
def validate_finding(
    request: Request,
    finding_id: int,
    validation_in: FindingValidation,
    current_user: User = Depends(require_permission(Permission.FINDING_MANAGE)),
    db: Session = Depends(get_db),
) -> Any:
    """Perform authoritative validation on a finding submitted for validation (PASS -> RESOLVED, FAIL -> IN_REMEDIATION)."""
    try:
        validated = FindingService.validate_finding(
            db=db,
            finding_id=finding_id,
            organization_id=current_user.organization_id,
            validation_in=validation_in,
            validator_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not validated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found in your organization.",
        )

    # Audit log
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    action_name = "finding.resolve" if validation_in.is_valid else "finding.validation.fail"
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action=action_name,
        resource_type="FINDING",
        resource_id=str(finding_id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={
            "is_valid": validation_in.is_valid,
            "new_status": validated.status.value,
            "notes": validation_in.validation_notes,
        },
    )

    return FindingService.get_finding_by_id(
        db=db, finding_id=finding_id, organization_id=current_user.organization_id
    )


@router.post("/{finding_id}/risk-acceptance", response_model=FindingResponse)
def accept_finding_risk(
    request: Request,
    finding_id: int,
    risk_in: FindingRiskAcceptance,
    current_user: User = Depends(require_permission(Permission.RISK_MANAGE)),
    db: Session = Depends(get_db),
) -> Any:
    """Perform formal risk acceptance on an active finding with documented justification and review date."""
    try:
        accepted = FindingService.accept_risk(
            db=db,
            finding_id=finding_id,
            organization_id=current_user.organization_id,
            risk_in=risk_in,
            acceptor_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not accepted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found in your organization.",
        )

    # Audit log
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="finding.risk.accept",
        resource_type="FINDING",
        resource_id=str(finding_id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={
            "justification": risk_in.justification,
            "expiry_date": risk_in.expiry_date.isoformat() if risk_in.expiry_date else None,
            "risk_score": accepted.risk_score,
        },
    )

    return FindingService.get_finding_by_id(
        db=db, finding_id=finding_id, organization_id=current_user.organization_id
    )


@router.post("/{finding_id}/evidence", response_model=FindingEvidenceResponse, status_code=status.HTTP_201_CREATED)
def link_finding_evidence(
    request: Request,
    finding_id: int,
    link_in: FindingEvidenceCreate,
    current_user: User = Depends(require_permission(Permission.FINDING_MANAGE)),
    db: Session = Depends(get_db),
) -> Any:
    """Link an evidence artifact to a finding for audit traceability."""
    try:
        link = FindingService.link_evidence(
            db=db,
            finding_id=finding_id,
            evidence_id=link_in.evidence_id,
            organization_id=current_user.organization_id,
            created_by_id=current_user.id,
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
        action="finding.evidence.link",
        resource_type="FINDING_EVIDENCE",
        resource_id=str(link.id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={"finding_id": finding_id, "evidence_id": link_in.evidence_id},
    )

    return link


@router.delete("/{finding_id}/evidence/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_finding_evidence(
    request: Request,
    finding_id: int,
    evidence_id: int,
    current_user: User = Depends(require_permission(Permission.FINDING_MANAGE)),
    db: Session = Depends(get_db),
) -> None:
    """Unlink an evidence artifact from a finding."""
    try:
        success = FindingService.unlink_evidence(
            db=db,
            finding_id=finding_id,
            evidence_id=evidence_id,
            organization_id=current_user.organization_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence linkage not found in your organization.",
        )

    # Audit log
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="finding.evidence.unlink",
        resource_type="FINDING_EVIDENCE",
        resource_id=f"{finding_id}:{evidence_id}",
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
    )

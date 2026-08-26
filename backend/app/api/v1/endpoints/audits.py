from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip, get_current_user, get_db, get_user_agent, require_permission
from app.core.permissions import Permission
from app.models.audit_engagement import AuditStatusEnum, AuditTypeEnum
from app.models.user import User
from app.schemas.audit_engagement import (
    AuditClosure,
    AuditCreate,
    AuditDetailResponse,
    AuditEvidenceLinkCreate,
    AuditEvidenceLinkResponse,
    AuditFindingLinkCreate,
    AuditFindingLinkResponse,
    AuditOpinionCreate,
    AuditProcedureCreate,
    AuditProcedureResponse,
    AuditProcedureUpdate,
    AuditReadinessResponse,
    AuditResponse,
    AuditScopeAdd,
    AuditScopeResponse,
    AuditStatsResponse,
    AuditStatusUpdate,
    AuditUpdate,
)
from app.services.audit_engagement_service import AuditEngagementService
from app.services.audit_service import AuditService

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# Audit CRUD
# ─────────────────────────────────────────────────────────────────────────────

@router.get("", response_model=List[AuditResponse])
def list_audits(
    status: Optional[AuditStatusEnum] = Query(None),
    audit_type: Optional[AuditTypeEnum] = Query(None),
    lead_auditor_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(require_permission(Permission.AUDIT_READ)),
    db: Session = Depends(get_db),
) -> Any:
    """List audits with filtering. Scope is strictly tenant-scoped."""
    return AuditEngagementService.list_audits(
        db=db,
        organization_id=current_user.organization_id,
        status=status,
        audit_type=audit_type,
        lead_auditor_id=lead_auditor_id,
        search=search,
        skip=skip,
        limit=limit,
    )


@router.get("/stats", response_model=AuditStatsResponse)
def get_audit_stats(
    current_user: User = Depends(require_permission(Permission.AUDIT_READ)),
    db: Session = Depends(get_db),
) -> Any:
    """Get deterministic aggregate audit statistics for the organization."""
    return AuditEngagementService.get_stats(
        db=db, organization_id=current_user.organization_id
    )


@router.post("", response_model=AuditResponse, status_code=status.HTTP_201_CREATED)
def create_audit(
    request: Request,
    audit_in: AuditCreate,
    current_user: User = Depends(require_permission(Permission.AUDIT_MANAGE)),
    db: Session = Depends(get_db),
) -> Any:
    """Create a new audit engagement."""
    try:
        new_audit = AuditEngagementService.create_audit(
            db=db,
            obj_in=audit_in,
            organization_id=current_user.organization_id,
            creator_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="audit.create",
        resource_type="AUDIT",
        resource_id=str(new_audit.id),
        status="SUCCESS",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        details={"title": new_audit.title, "audit_type": new_audit.audit_type.value},
    )

    result = AuditEngagementService.get_audit_by_id(
        db=db, audit_id=new_audit.id, organization_id=current_user.organization_id
    )
    return result


@router.get("/{audit_id}", response_model=AuditDetailResponse)
def get_audit(
    audit_id: int,
    current_user: User = Depends(require_permission(Permission.AUDIT_READ)),
    db: Session = Depends(get_db),
) -> Any:
    """Retrieve full audit details including scope, procedures, and finding links."""
    result = AuditEngagementService.get_audit_by_id(
        db=db, audit_id=audit_id, organization_id=current_user.organization_id
    )
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found in your organization.")
    return result


@router.patch("/{audit_id}", response_model=AuditResponse)
def update_audit(
    request: Request,
    audit_id: int,
    audit_in: AuditUpdate,
    current_user: User = Depends(require_permission(Permission.AUDIT_MANAGE)),
    db: Session = Depends(get_db),
) -> Any:
    """Update audit metadata. Closed audits are immutable."""
    try:
        updated = AuditEngagementService.update_audit(
            db=db,
            audit_id=audit_id,
            organization_id=current_user.organization_id,
            obj_in=audit_in,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found in your organization.")

    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="audit.update",
        resource_type="AUDIT",
        resource_id=str(audit_id),
        status="SUCCESS",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        details={"updated_fields": list(audit_in.model_dump(exclude_unset=True).keys())},
    )

    return AuditEngagementService.get_audit_by_id(
        db=db, audit_id=audit_id, organization_id=current_user.organization_id
    )


@router.post("/{audit_id}/status", response_model=AuditResponse)
def update_audit_status(
    request: Request,
    audit_id: int,
    status_in: AuditStatusUpdate,
    current_user: User = Depends(require_permission(Permission.AUDIT_MANAGE)),
    db: Session = Depends(get_db),
) -> Any:
    """Transition audit lifecycle status (server-enforced state machine)."""
    try:
        updated = AuditEngagementService.update_status(
            db=db,
            audit_id=audit_id,
            organization_id=current_user.organization_id,
            status_in=status_in,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found in your organization.")

    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="audit.status.change",
        resource_type="AUDIT",
        resource_id=str(audit_id),
        status="SUCCESS",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        details={"new_status": status_in.status.value, "notes": status_in.notes},
    )

    return AuditEngagementService.get_audit_by_id(
        db=db, audit_id=audit_id, organization_id=current_user.organization_id
    )


# ─────────────────────────────────────────────────────────────────────────────
# Scope
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{audit_id}/scope", response_model=List[AuditScopeResponse])
def list_audit_scope(
    audit_id: int,
    current_user: User = Depends(require_permission(Permission.AUDIT_READ)),
    db: Session = Depends(get_db),
) -> Any:
    """List controls in the audit scope."""
    try:
        scope = AuditEngagementService.list_scope_controls(
            db=db, audit_id=audit_id, organization_id=current_user.organization_id
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return scope


@router.post("/{audit_id}/scope", response_model=AuditScopeResponse, status_code=status.HTTP_201_CREATED)
def add_audit_scope_control(
    request: Request,
    audit_id: int,
    scope_in: AuditScopeAdd,
    current_user: User = Depends(require_permission(Permission.AUDIT_EXECUTE)),
    db: Session = Depends(get_db),
) -> Any:
    """Add a control to the audit scope."""
    try:
        sc = AuditEngagementService.add_scope_control(
            db=db,
            audit_id=audit_id,
            obj_in=scope_in,
            organization_id=current_user.organization_id,
            creator_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="audit.scope.add",
        resource_type="AUDIT_SCOPE",
        resource_id=str(sc.id),
        status="SUCCESS",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        details={"audit_id": audit_id, "control_id": scope_in.organization_control_id},
    )
    return sc


@router.delete("/{audit_id}/scope/{control_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_audit_scope_control(
    request: Request,
    audit_id: int,
    control_id: int,
    current_user: User = Depends(require_permission(Permission.AUDIT_EXECUTE)),
    db: Session = Depends(get_db),
) -> None:
    """Remove a control from the audit scope."""
    try:
        success = AuditEngagementService.remove_scope_control(
            db=db,
            audit_id=audit_id,
            organization_control_id=control_id,
            organization_id=current_user.organization_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scope control not found.")

    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="audit.scope.remove",
        resource_type="AUDIT_SCOPE",
        resource_id=f"{audit_id}:{control_id}",
        status="SUCCESS",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Procedures
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{audit_id}/procedures", response_model=List[AuditProcedureResponse])
def list_audit_procedures(
    audit_id: int,
    current_user: User = Depends(require_permission(Permission.AUDIT_READ)),
    db: Session = Depends(get_db),
) -> Any:
    """List all procedures for an audit."""
    audit = AuditEngagementService.get_audit_by_id(
        db=db, audit_id=audit_id, organization_id=current_user.organization_id
    )
    if not audit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found in your organization.")
    return audit.get("procedures", [])


@router.post("/{audit_id}/procedures", response_model=AuditProcedureResponse, status_code=status.HTTP_201_CREATED)
def create_audit_procedure(
    request: Request,
    audit_id: int,
    proc_in: AuditProcedureCreate,
    current_user: User = Depends(require_permission(Permission.AUDIT_EXECUTE)),
    db: Session = Depends(get_db),
) -> Any:
    """Create an audit procedure test step."""
    try:
        procedure = AuditEngagementService.create_procedure(
            db=db,
            audit_id=audit_id,
            obj_in=proc_in,
            organization_id=current_user.organization_id,
            creator_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="audit.procedure.create",
        resource_type="AUDIT_PROCEDURE",
        resource_id=str(procedure.id),
        status="SUCCESS",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        details={"audit_id": audit_id, "title": procedure.title},
    )
    return _procedure_response(procedure)


@router.patch("/{audit_id}/procedures/{procedure_id}", response_model=AuditProcedureResponse)
def update_audit_procedure(
    request: Request,
    audit_id: int,
    procedure_id: int,
    proc_in: AuditProcedureUpdate,
    current_user: User = Depends(require_permission(Permission.AUDIT_EXECUTE)),
    db: Session = Depends(get_db),
) -> Any:
    """Update an audit procedure (record actual results, update status)."""
    try:
        updated = AuditEngagementService.update_procedure(
            db=db,
            audit_id=audit_id,
            procedure_id=procedure_id,
            organization_id=current_user.organization_id,
            obj_in=proc_in,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Procedure not found.")

    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="audit.procedure.update",
        resource_type="AUDIT_PROCEDURE",
        resource_id=str(procedure_id),
        status="SUCCESS",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        details={"updated_fields": list(proc_in.model_dump(exclude_unset=True).keys())},
    )
    return _procedure_response(updated)


# ─────────────────────────────────────────────────────────────────────────────
# Procedure Evidence
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{audit_id}/procedures/{procedure_id}/evidence", response_model=AuditEvidenceLinkResponse, status_code=status.HTTP_201_CREATED)
def link_evidence_to_procedure(
    request: Request,
    audit_id: int,
    procedure_id: int,
    ev_in: AuditEvidenceLinkCreate,
    current_user: User = Depends(require_permission(Permission.AUDIT_EXECUTE)),
    db: Session = Depends(get_db),
) -> Any:
    """Link existing evidence to an audit procedure."""
    try:
        link = AuditEngagementService.link_evidence_to_procedure(
            db=db,
            audit_id=audit_id,
            procedure_id=procedure_id,
            obj_in=ev_in,
            organization_id=current_user.organization_id,
            creator_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="audit.evidence.link",
        resource_type="AUDIT_PROCEDURE_EVIDENCE",
        resource_id=str(link.id),
        status="SUCCESS",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        details={"procedure_id": procedure_id, "evidence_id": ev_in.evidence_id},
    )
    return link


@router.delete("/{audit_id}/procedures/{procedure_id}/evidence/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_evidence_from_procedure(
    request: Request,
    audit_id: int,
    procedure_id: int,
    evidence_id: int,
    current_user: User = Depends(require_permission(Permission.AUDIT_EXECUTE)),
    db: Session = Depends(get_db),
) -> None:
    """Unlink evidence from an audit procedure."""
    try:
        success = AuditEngagementService.unlink_evidence_from_procedure(
            db=db,
            audit_id=audit_id,
            procedure_id=procedure_id,
            evidence_id=evidence_id,
            organization_id=current_user.organization_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence link not found.")

    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="audit.evidence.unlink",
        resource_type="AUDIT_PROCEDURE_EVIDENCE",
        resource_id=f"{procedure_id}:{evidence_id}",
        status="SUCCESS",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Finding Links
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{audit_id}/findings", response_model=List[AuditFindingLinkResponse])
def list_audit_findings(
    audit_id: int,
    current_user: User = Depends(require_permission(Permission.AUDIT_READ)),
    db: Session = Depends(get_db),
) -> Any:
    """List findings linked to this audit."""
    try:
        links = AuditEngagementService.list_findings(
            db=db, audit_id=audit_id, organization_id=current_user.organization_id
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return links


@router.post("/{audit_id}/findings", response_model=AuditFindingLinkResponse, status_code=status.HTTP_201_CREATED)
def link_audit_finding(
    request: Request,
    audit_id: int,
    link_in: AuditFindingLinkCreate,
    current_user: User = Depends(require_permission(Permission.AUDIT_EXECUTE)),
    db: Session = Depends(get_db),
) -> Any:
    """Link an existing finding to this audit."""
    try:
        link = AuditEngagementService.link_finding(
            db=db,
            audit_id=audit_id,
            obj_in=link_in,
            organization_id=current_user.organization_id,
            creator_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="audit.finding.link",
        resource_type="AUDIT_FINDING_LINK",
        resource_id=str(link.id),
        status="SUCCESS",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        details={"audit_id": audit_id, "finding_id": link_in.finding_id},
    )
    return link


@router.delete("/{audit_id}/findings/{finding_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_audit_finding(
    request: Request,
    audit_id: int,
    finding_id: int,
    current_user: User = Depends(require_permission(Permission.AUDIT_EXECUTE)),
    db: Session = Depends(get_db),
) -> None:
    """Unlink a finding from this audit."""
    try:
        success = AuditEngagementService.unlink_finding(
            db=db,
            audit_id=audit_id,
            finding_id=finding_id,
            organization_id=current_user.organization_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding link not found.")

    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="audit.finding.unlink",
        resource_type="AUDIT_FINDING_LINK",
        resource_id=f"{audit_id}:{finding_id}",
        status="SUCCESS",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Readiness
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{audit_id}/readiness", response_model=AuditReadinessResponse)
def get_audit_readiness(
    audit_id: int,
    current_user: User = Depends(require_permission(Permission.AUDIT_READ)),
    db: Session = Depends(get_db),
) -> Any:
    """Get deterministic audit readiness metrics. All calculations are server-authoritative."""
    result = AuditEngagementService.get_readiness(
        db=db, audit_id=audit_id, organization_id=current_user.organization_id
    )
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found in your organization.")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Opinion (human-authoritative, never AI-issued)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{audit_id}/opinion", response_model=AuditResponse)
def issue_audit_opinion(
    request: Request,
    audit_id: int,
    opinion_in: AuditOpinionCreate,
    current_user: User = Depends(require_permission(Permission.AUDIT_APPROVE)),
    db: Session = Depends(get_db),
) -> Any:
    """Issue a human-authoritative audit opinion. Requires AUDIT_APPROVE permission and separation of duties."""
    try:
        updated = AuditEngagementService.issue_opinion(
            db=db,
            audit_id=audit_id,
            organization_id=current_user.organization_id,
            opinion_in=opinion_in,
            issuer_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found in your organization.")

    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="audit.opinion.issue",
        resource_type="AUDIT",
        resource_id=str(audit_id),
        status="SUCCESS",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        details={"opinion": opinion_in.opinion.value, "issuer_id": current_user.id},
    )

    return AuditEngagementService.get_audit_by_id(
        db=db, audit_id=audit_id, organization_id=current_user.organization_id
    )


# ─────────────────────────────────────────────────────────────────────────────
# Closure
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{audit_id}/close", response_model=AuditResponse)
def close_audit(
    request: Request,
    audit_id: int,
    closure_in: AuditClosure,
    current_user: User = Depends(require_permission(Permission.AUDIT_CLOSE)),
    db: Session = Depends(get_db),
) -> Any:
    """Close a COMPLETED audit. Requires AUDIT_CLOSE permission."""
    try:
        closed = AuditEngagementService.close_audit(
            db=db,
            audit_id=audit_id,
            organization_id=current_user.organization_id,
            closure_in=closure_in,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not closed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found in your organization.")

    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="audit.close",
        resource_type="AUDIT",
        resource_id=str(audit_id),
        status="SUCCESS",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        details={"closure_notes": closure_in.closure_notes},
    )

    return AuditEngagementService.get_audit_by_id(
        db=db, audit_id=audit_id, organization_id=current_user.organization_id
    )


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────
def _procedure_response(p: Any) -> dict:
    return {
        "id": p.id,
        "audit_id": p.audit_id,
        "organization_control_id": p.organization_control_id,
        "title": p.title,
        "objective": p.objective,
        "test_steps": p.test_steps,
        "expected_result": p.expected_result,
        "actual_result": p.actual_result,
        "assessment_method": p.assessment_method,
        "result": p.result,
        "execution_notes": p.execution_notes,
        "limitations": p.limitations,
        "tester_id": p.tester_id,
        "execution_date": p.execution_date,
        "created_by_id": p.created_by_id,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
        "evidence_count": len(p.evidence_links) if hasattr(p, "evidence_links") and p.evidence_links else 0,
    }

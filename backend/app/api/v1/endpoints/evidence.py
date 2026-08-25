import io
import urllib.parse
from typing import Any, List, Optional
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.api.deps import (
    get_client_ip,
    get_current_user,
    get_db,
    get_user_agent,
    require_permission,
)
from app.core.file_security import FileSecurityError
from app.core.permissions import Permission
from app.models.evidence import (
    EvidenceStatusEnum,
    EvidenceTypeEnum,
)
from app.models.user import User
from app.schemas.evidence import (
    ControlEvidenceSummaryResponse,
    EvidenceItemDetailResponse,
    EvidenceItemResponse,
    EvidenceItemUpdate,
    EvidenceRequirementCreate,
    EvidenceRequirementResponse,
    EvidenceRequirementUpdate,
    EvidenceReviewCreate,
    EvidenceReviewResponse,
    OrganizationEvidenceStatsResponse,
)
from app.services.audit_service import AuditService
from app.services.evidence_service import EvidenceService

router = APIRouter()


# ----------------------------------------------------------------
# Evidence Requirements Endpoints
# ----------------------------------------------------------------
@router.get("/requirements", response_model=List[EvidenceRequirementResponse])
def list_evidence_requirements(
    organization_control_id: Optional[int] = Query(None, description="Filter by control ID"),
    is_required: Optional[bool] = Query(None, description="Filter by required flag"),
    evidence_type: Optional[EvidenceTypeEnum] = Query(None, description="Filter by evidence type"),
    search: Optional[str] = Query(None, description="Search keyword in title or description"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(require_permission(Permission.EVIDENCE_READ)),
    db: Session = Depends(get_db),
) -> Any:
    """List organization evidence requirements."""
    return EvidenceService.list_requirements(
        db=db,
        organization_id=current_user.organization_id,
        organization_control_id=organization_control_id,
        is_required=is_required,
        evidence_type=evidence_type,
        search=search,
        skip=skip,
        limit=limit,
    )


@router.post("/requirements", response_model=EvidenceRequirementResponse, status_code=status.HTTP_201_CREATED)
def create_evidence_requirement(
    request: Request,
    req_in: EvidenceRequirementCreate,
    current_user: User = Depends(require_permission(Permission.EVIDENCE_MANAGE)),
    db: Session = Depends(get_db),
) -> Any:
    """Define a new evidence requirement for an organization control."""
    try:
        new_req = EvidenceService.create_requirement(
            db=db,
            obj_in=req_in,
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
        action="evidence.requirement.create",
        resource_type="EVIDENCE_REQUIREMENT",
        resource_id=str(new_req.id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={"title": new_req.title, "control_id": new_req.organization_control_id},
    )

    return EvidenceService.get_requirement_by_id(
        db=db, requirement_id=new_req.id, organization_id=current_user.organization_id
    )


@router.get("/requirements/{requirement_id}", response_model=EvidenceRequirementResponse)
def get_evidence_requirement(
    requirement_id: int,
    current_user: User = Depends(require_permission(Permission.EVIDENCE_READ)),
    db: Session = Depends(get_db),
) -> Any:
    """Get details for a specific evidence requirement."""
    req = EvidenceService.get_requirement_by_id(
        db=db, requirement_id=requirement_id, organization_id=current_user.organization_id
    )
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence requirement not found in your organization",
        )
    return req


@router.patch("/requirements/{requirement_id}", response_model=EvidenceRequirementResponse)
def update_evidence_requirement(
    request: Request,
    requirement_id: int,
    req_in: EvidenceRequirementUpdate,
    current_user: User = Depends(require_permission(Permission.EVIDENCE_MANAGE)),
    db: Session = Depends(get_db),
) -> Any:
    """Update evidence requirement definition."""
    updated = EvidenceService.update_requirement(
        db=db,
        requirement_id=requirement_id,
        organization_id=current_user.organization_id,
        obj_in=req_in,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence requirement not found in your organization",
        )

    # Audit log
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="evidence.requirement.update",
        resource_type="EVIDENCE_REQUIREMENT",
        resource_id=str(requirement_id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={"updated_fields": list(req_in.model_dump(exclude_unset=True).keys())},
    )

    return EvidenceService.get_requirement_by_id(
        db=db, requirement_id=requirement_id, organization_id=current_user.organization_id
    )


@router.delete("/requirements/{requirement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_evidence_requirement(
    request: Request,
    requirement_id: int,
    current_user: User = Depends(require_permission(Permission.EVIDENCE_MANAGE)),
    db: Session = Depends(get_db),
) -> None:
    """Delete an evidence requirement."""
    success = EvidenceService.delete_requirement(
        db=db,
        requirement_id=requirement_id,
        organization_id=current_user.organization_id,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence requirement not found in your organization",
        )

    # Audit log
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="evidence.requirement.delete",
        resource_type="EVIDENCE_REQUIREMENT",
        resource_id=str(requirement_id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
    )


# ----------------------------------------------------------------
# Evidence Items & Upload Endpoints
# ----------------------------------------------------------------
@router.get("", response_model=List[EvidenceItemResponse])
def list_evidence_items(
    organization_control_id: Optional[int] = Query(None, description="Filter by control ID"),
    evidence_requirement_id: Optional[int] = Query(None, description="Filter by requirement ID"),
    status: Optional[EvidenceStatusEnum] = Query(None, description="Filter by status"),
    uploaded_by_id: Optional[int] = Query(None, description="Filter by uploader user ID"),
    search: Optional[str] = Query(None, description="Search keyword"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(require_permission(Permission.EVIDENCE_READ)),
    db: Session = Depends(get_db),
) -> Any:
    """List organization evidence items with review summaries and control linkages."""
    return EvidenceService.list_evidence(
        db=db,
        organization_id=current_user.organization_id,
        organization_control_id=organization_control_id,
        evidence_requirement_id=evidence_requirement_id,
        status=status,
        uploaded_by_id=uploaded_by_id,
        search=search,
        skip=skip,
        limit=limit,
    )


@router.get("/stats", response_model=OrganizationEvidenceStatsResponse)
def get_evidence_stats(
    current_user: User = Depends(require_permission(Permission.EVIDENCE_READ)),
    db: Session = Depends(get_db),
) -> Any:
    """Retrieve organization-wide aggregate evidence assurance statistics."""
    return EvidenceService.calculate_organization_evidence_stats(
        db=db, organization_id=current_user.organization_id
    )


@router.get("/controls/{control_id}/assurance", response_model=ControlEvidenceSummaryResponse)
def get_control_evidence_assurance(
    control_id: int,
    current_user: User = Depends(require_permission(Permission.EVIDENCE_READ)),
    db: Session = Depends(get_db),
) -> Any:
    """Retrieve evidence assurance metrics for a specific organization control."""
    return EvidenceService.calculate_control_evidence_metrics(
        db=db,
        organization_control_id=control_id,
        organization_id=current_user.organization_id,
    )


@router.post("/upload", response_model=EvidenceItemResponse, status_code=status.HTTP_201_CREATED)
async def upload_evidence(
    request: Request,
    file: UploadFile = File(...),
    organization_control_id: int = Form(...),
    evidence_requirement_id: Optional[int] = Form(None),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    current_user: User = Depends(require_permission(Permission.EVIDENCE_UPLOAD)),
    db: Session = Depends(get_db),
) -> Any:
    """Upload and validate an untrusted evidence file."""
    file_bytes = await file.read()
    orig_name = file.filename or "uploaded_artifact"
    declared_content_type = file.content_type or "application/octet-stream"

    try:
        item = EvidenceService.upload_evidence(
            db=db,
            organization_id=current_user.organization_id,
            organization_control_id=organization_control_id,
            evidence_requirement_id=evidence_requirement_id,
            title=title or orig_name,
            description=description,
            file_bytes=file_bytes,
            original_filename=orig_name,
            declared_content_type=declared_content_type,
            uploaded_by_id=current_user.id,
        )
    except FileSecurityError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
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
        action="evidence.upload",
        resource_type="EVIDENCE",
        resource_id=str(item.id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={
            "control_id": organization_control_id,
            "filename": item.original_filename,
            "file_size": item.file_size,
            "sha256_hash": item.sha256_hash,
        },
    )

    return EvidenceService.get_evidence_by_id(
        db=db, evidence_id=item.id, organization_id=current_user.organization_id
    )


@router.get("/{evidence_id}", response_model=EvidenceItemDetailResponse)
def get_evidence_item(
    evidence_id: int,
    current_user: User = Depends(require_permission(Permission.EVIDENCE_READ)),
    db: Session = Depends(get_db),
) -> Any:
    """Retrieve full details of an evidence item, including review history."""
    item = EvidenceService.get_evidence_by_id(
        db=db, evidence_id=evidence_id, organization_id=current_user.organization_id
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence item not found in your organization",
        )
    return item


@router.patch("/{evidence_id}", response_model=EvidenceItemResponse)
def update_evidence_metadata(
    request: Request,
    evidence_id: int,
    item_in: EvidenceItemUpdate,
    current_user: User = Depends(require_permission(Permission.EVIDENCE_UPLOAD)),
    db: Session = Depends(get_db),
) -> Any:
    """Update editable metadata (title, description) of an active evidence item."""
    try:
        updated = EvidenceService.update_evidence_metadata(
            db=db,
            evidence_id=evidence_id,
            organization_id=current_user.organization_id,
            title=item_in.title,
            description=item_in.description,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence item not found in your organization",
        )

    # Audit log
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="evidence.metadata.update",
        resource_type="EVIDENCE",
        resource_id=str(evidence_id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={"updated_fields": list(item_in.model_dump(exclude_unset=True).keys())},
    )

    return EvidenceService.get_evidence_by_id(
        db=db, evidence_id=evidence_id, organization_id=current_user.organization_id
    )


@router.post("/{evidence_id}/submit-review", response_model=EvidenceItemResponse)
def submit_evidence_for_review(
    request: Request,
    evidence_id: int,
    current_user: User = Depends(require_permission(Permission.EVIDENCE_UPLOAD)),
    db: Session = Depends(get_db),
) -> Any:
    """Transition evidence status from UPLOADED or REJECTED to UNDER_REVIEW."""
    try:
        updated = EvidenceService.submit_for_review(
            db=db, evidence_id=evidence_id, organization_id=current_user.organization_id
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence item not found in your organization",
        )

    # Audit log
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="evidence.submit_review",
        resource_type="EVIDENCE",
        resource_id=str(evidence_id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
    )

    return EvidenceService.get_evidence_by_id(
        db=db, evidence_id=evidence_id, organization_id=current_user.organization_id
    )


@router.post("/{evidence_id}/review", response_model=EvidenceItemDetailResponse)
def review_evidence(
    request: Request,
    evidence_id: int,
    review_in: EvidenceReviewCreate,
    current_user: User = Depends(require_permission(Permission.EVIDENCE_REVIEW)),
    db: Session = Depends(get_db),
) -> Any:
    """Evaluate and submit an authorized review decision (ACCEPT / REJECT) on an evidence item."""
    try:
        item, rev = EvidenceService.review_evidence(
            db=db,
            evidence_id=evidence_id,
            organization_id=current_user.organization_id,
            review_in=review_in,
            reviewer_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Audit log
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    action_name = "evidence.accept" if review_in.decision.value == "ACCEPT" else "evidence.reject"
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action=action_name,
        resource_type="EVIDENCE",
        resource_id=str(evidence_id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={
            "decision": review_in.decision.value,
            "rejection_reason": review_in.rejection_reason,
            "review_notes": review_in.review_notes,
        },
    )

    return EvidenceService.get_evidence_by_id(
        db=db, evidence_id=evidence_id, organization_id=current_user.organization_id
    )


@router.post("/{evidence_id}/supersede", response_model=EvidenceItemResponse)
def supersede_evidence(
    request: Request,
    evidence_id: int,
    new_evidence_id: int = Query(..., description="ID of replacement evidence item"),
    current_user: User = Depends(require_permission(Permission.EVIDENCE_UPLOAD)),
    db: Session = Depends(get_db),
) -> Any:
    """Mark an old evidence item as SUPERSEDED by a newly uploaded artifact."""
    try:
        superseded = EvidenceService.supersede_evidence(
            db=db,
            old_evidence_id=evidence_id,
            new_evidence_id=new_evidence_id,
            organization_id=current_user.organization_id,
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
        action="evidence.supersede",
        resource_type="EVIDENCE",
        resource_id=str(evidence_id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={"superseded_by_id": new_evidence_id},
    )

    return EvidenceService.get_evidence_by_id(
        db=db, evidence_id=evidence_id, organization_id=current_user.organization_id
    )


@router.get("/{evidence_id}/download")
def download_evidence(
    request: Request,
    evidence_id: int,
    current_user: User = Depends(require_permission(Permission.EVIDENCE_READ)),
    db: Session = Depends(get_db),
) -> Any:
    """Securely stream an authenticated evidence file with safe Content-Disposition headers."""
    try:
        file_bytes, original_filename, content_type, file_size = EvidenceService.get_evidence_file_for_download(
            db=db, evidence_id=evidence_id, organization_id=current_user.organization_id
        )
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence artifact not found or inaccessible in your organization.",
        )

    # Audit log download access
    ip = get_client_ip(request)
    ua = get_user_agent(request)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="evidence.download",
        resource_type="EVIDENCE",
        resource_id=str(evidence_id),
        status="SUCCESS",
        ip_address=ip,
        user_agent=ua,
        details={"filename": original_filename, "file_size": file_size},
    )

    # Safe RFC 5987 / RFC 6266 filename encoding
    safe_filename = original_filename.replace('"', '\\"')
    encoded_filename = urllib.parse.quote(original_filename)

    headers = {
        "Content-Disposition": f'attachment; filename="{safe_filename}"; filename*=UTF-8\'\'{encoded_filename}',
        "Content-Length": str(file_size),
        "X-Content-Type-Options": "nosniff",
    }

    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=content_type,
        headers=headers,
    )
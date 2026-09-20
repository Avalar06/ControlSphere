from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.permissions import Permission, RoleEnum, has_permission
from app.models.audit_engagement import PBCStatusEnum
from app.models.user import User
from app.schemas.audit_fieldwork import (
    AuditPBCRequestCreate,
    AuditPBCRequestUpdate,
    AuditPBCRequestFulfill,
    AuditPBCRequestReview,
    AuditPBCRequestResponse,
    AuditSamplePopulationCreate,
    AuditSampleGenerateRequest,
    AuditSampleItemUpdate,
    AuditSampleEscalateFinding,
    AuditSampleItemResponse,
    AuditSamplePopulationResponse,
    AuditWorkpaperSubmit,
    AuditWorkpaperApprove,
    AuditWorkpaperRequestChanges,
    AuditWorkpaperResponse,
)
from app.schemas.finding import FindingResponse
from app.services.audit_fieldwork_service import AuditFieldworkService
from app.services.finding_service import FindingService

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# Helper: Format PBC response
# ─────────────────────────────────────────────────────────────────────────────
def _pbc_to_response(pbc) -> AuditPBCRequestResponse:
    return AuditPBCRequestResponse(
        id=pbc.id,
        organization_id=pbc.organization_id,
        audit_id=pbc.audit_id,
        procedure_id=pbc.procedure_id,
        organization_control_id=pbc.organization_control_id,
        request_identifier=pbc.request_identifier,
        title=pbc.title,
        description=pbc.description,
        status=pbc.status,
        priority=pbc.priority,
        assigned_to_id=pbc.assigned_to_id,
        due_date=pbc.due_date,
        fulfilled_evidence_id=pbc.fulfilled_evidence_id,
        submission_notes=pbc.submission_notes,
        submitted_at=pbc.submitted_at,
        reviewed_by_id=pbc.reviewed_by_id,
        reviewed_at=pbc.reviewed_at,
        rejection_reason=pbc.rejection_reason,
        created_by_id=pbc.created_by_id,
        created_at=pbc.created_at,
        updated_at=pbc.updated_at,
        assigned_to_name=pbc.assigned_to.full_name if pbc.assigned_to else None,
        reviewed_by_name=pbc.reviewed_by.full_name if pbc.reviewed_by else None,
        control_code=(
            pbc.organization_control.subcategory.identifier
            if (pbc.organization_control and pbc.organization_control.subcategory)
            else None
        ),
        evidence_filename=pbc.fulfilled_evidence.original_filename if pbc.fulfilled_evidence else None,
    )


# ─────────────────────────────────────────────────────────────────────────────
# PBC REQUEST ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/audits/{audit_id}/pbc-requests",
    response_model=AuditPBCRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create PBC Request",
)
def create_pbc_request(
    audit_id: int,
    obj_in: AuditPBCRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        has_permission(current_user.role, Permission.AUDIT_MANAGE)
        or has_permission(current_user.role, Permission.AUDIT_EXECUTE)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: AUDIT_MANAGE or AUDIT_EXECUTE required.",
        )
    pbc = AuditFieldworkService.create_pbc_request(
        db=db,
        organization_id=current_user.organization_id,
        audit_id=audit_id,
        obj_in=obj_in,
        creator_id=current_user.id,
    )
    return _pbc_to_response(pbc)


@router.get(
    "/audits/{audit_id}/pbc-requests",
    response_model=List[AuditPBCRequestResponse],
    summary="List PBC Requests for Audit",
)
def list_pbc_requests(
    audit_id: int,
    procedure_id: Optional[int] = Query(None),
    assigned_to_id: Optional[int] = Query(None),
    status_filter: Optional[PBCStatusEnum] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not has_permission(current_user.role, Permission.AUDIT_READ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied.")
    records = AuditFieldworkService.list_pbc_requests(
        db=db,
        organization_id=current_user.organization_id,
        audit_id=audit_id,
        procedure_id=procedure_id,
        assigned_to_id=assigned_to_id,
        status_filter=status_filter,
    )
    return [_pbc_to_response(r) for r in records]


@router.get(
    "/audits/{audit_id}/pbc-requests/{pbc_id}",
    response_model=AuditPBCRequestResponse,
    summary="Get PBC Request Details",
)
def get_pbc_request(
    audit_id: int,
    pbc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not has_permission(current_user.role, Permission.AUDIT_READ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied.")
    pbc = AuditFieldworkService.get_pbc_request(
        db=db,
        organization_id=current_user.organization_id,
        audit_id=audit_id,
        pbc_id=pbc_id,
    )
    return _pbc_to_response(pbc)


@router.put(
    "/audits/{audit_id}/pbc-requests/{pbc_id}",
    response_model=AuditPBCRequestResponse,
    summary="Update PBC Request",
)
def update_pbc_request(
    audit_id: int,
    pbc_id: int,
    obj_in: AuditPBCRequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        has_permission(current_user.role, Permission.AUDIT_MANAGE)
        or has_permission(current_user.role, Permission.AUDIT_EXECUTE)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied.")
    pbc = AuditFieldworkService.update_pbc_request(
        db=db,
        organization_id=current_user.organization_id,
        audit_id=audit_id,
        pbc_id=pbc_id,
        obj_in=obj_in,
    )
    return _pbc_to_response(pbc)


@router.post(
    "/audits/{audit_id}/pbc-requests/{pbc_id}/fulfill",
    response_model=AuditPBCRequestResponse,
    summary="Fulfill PBC Request with Evidence",
)
def fulfill_pbc_request(
    audit_id: int,
    pbc_id: int,
    obj_in: AuditPBCRequestFulfill,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pbc = AuditFieldworkService.fulfill_pbc_request(
        db=db,
        organization_id=current_user.organization_id,
        audit_id=audit_id,
        pbc_id=pbc_id,
        user_id=current_user.id,
        obj_in=obj_in,
    )
    return _pbc_to_response(pbc)


@router.post(
    "/audits/{audit_id}/pbc-requests/{pbc_id}/review",
    response_model=AuditPBCRequestResponse,
    summary="Review (Accept or Reject) PBC Request",
)
def review_pbc_request(
    audit_id: int,
    pbc_id: int,
    obj_in: AuditPBCRequestReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        has_permission(current_user.role, Permission.AUDIT_MANAGE)
        or has_permission(current_user.role, Permission.AUDIT_EXECUTE)
        or has_permission(current_user.role, Permission.AUDIT_REVIEW)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied.")
    pbc = AuditFieldworkService.review_pbc_request(
        db=db,
        organization_id=current_user.organization_id,
        audit_id=audit_id,
        pbc_id=pbc_id,
        reviewer_id=current_user.id,
        obj_in=obj_in,
    )
    return _pbc_to_response(pbc)


# ─────────────────────────────────────────────────────────────────────────────
# SAMPLING POPULATION & TESTING ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/audits/{audit_id}/procedures/{procedure_id}/population",
    response_model=AuditSamplePopulationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Define Sampling Population for Procedure",
)
def create_population(
    audit_id: int,
    procedure_id: int,
    obj_in: AuditSamplePopulationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        has_permission(current_user.role, Permission.AUDIT_MANAGE)
        or has_permission(current_user.role, Permission.AUDIT_EXECUTE)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied.")
    pop = AuditFieldworkService.create_population(
        db=db,
        organization_id=current_user.organization_id,
        audit_id=audit_id,
        procedure_id=procedure_id,
        obj_in=obj_in,
        creator_id=current_user.id,
    )
    return pop


@router.post(
    "/audits/{audit_id}/procedures/{procedure_id}/population/{population_id}/freeze",
    response_model=AuditSamplePopulationResponse,
    summary="Freeze Population Snapshot",
)
def freeze_population(
    audit_id: int,
    procedure_id: int,
    population_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        has_permission(current_user.role, Permission.AUDIT_MANAGE)
        or has_permission(current_user.role, Permission.AUDIT_EXECUTE)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied.")
    pop = AuditFieldworkService.freeze_population(
        db=db,
        organization_id=current_user.organization_id,
        audit_id=audit_id,
        procedure_id=procedure_id,
        population_id=population_id,
        user_id=current_user.id,
    )
    return pop


@router.post(
    "/audits/{audit_id}/procedures/{procedure_id}/population/{population_id}/generate",
    response_model=AuditSamplePopulationResponse,
    summary="Generate Deterministic Samples",
)
def generate_samples(
    audit_id: int,
    procedure_id: int,
    population_id: int,
    obj_in: AuditSampleGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        has_permission(current_user.role, Permission.AUDIT_MANAGE)
        or has_permission(current_user.role, Permission.AUDIT_EXECUTE)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied.")
    pop = AuditFieldworkService.generate_samples(
        db=db,
        organization_id=current_user.organization_id,
        audit_id=audit_id,
        procedure_id=procedure_id,
        population_id=population_id,
        user_id=current_user.id,
        obj_in=obj_in,
    )
    return pop


@router.get(
    "/audits/{audit_id}/procedures/{procedure_id}/population",
    response_model=Optional[AuditSamplePopulationResponse],
    summary="Get Population & Generated Samples for Procedure",
)
def get_population(
    audit_id: int,
    procedure_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not has_permission(current_user.role, Permission.AUDIT_READ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied.")
    pop = AuditFieldworkService.get_population_with_samples(
        db=db,
        organization_id=current_user.organization_id,
        audit_id=audit_id,
        procedure_id=procedure_id,
    )
    if not pop:
        return None
    return pop


@router.put(
    "/audits/{audit_id}/procedures/{procedure_id}/samples/{sample_id}",
    response_model=AuditSampleItemResponse,
    summary="Record Sample Item Testing Result",
)
def update_sample_item(
    audit_id: int,
    procedure_id: int,
    sample_id: int,
    obj_in: AuditSampleItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        has_permission(current_user.role, Permission.AUDIT_MANAGE)
        or has_permission(current_user.role, Permission.AUDIT_EXECUTE)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied.")
    item = AuditFieldworkService.update_sample_item(
        db=db,
        organization_id=current_user.organization_id,
        audit_id=audit_id,
        procedure_id=procedure_id,
        sample_id=sample_id,
        user_id=current_user.id,
        obj_in=obj_in,
    )
    return item


@router.post(
    "/audits/{audit_id}/procedures/{procedure_id}/samples/{sample_id}/escalate-finding",
    response_model=FindingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Escalate Sample Failure to Authoritative Finding",
)
def escalate_sample_deficiency(
    audit_id: int,
    procedure_id: int,
    sample_id: int,
    obj_in: AuditSampleEscalateFinding,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        has_permission(current_user.role, Permission.AUDIT_MANAGE)
        or has_permission(current_user.role, Permission.AUDIT_EXECUTE)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied.")
    finding = AuditFieldworkService.escalate_sample_deficiency(
        db=db,
        organization_id=current_user.organization_id,
        audit_id=audit_id,
        procedure_id=procedure_id,
        sample_id=sample_id,
        user_id=current_user.id,
        obj_in=obj_in,
    )
    return FindingService.get_finding_by_id(
        db=db,
        finding_id=finding.id,
        organization_id=current_user.organization_id,
    )


# ─────────────────────────────────────────────────────────────────────────────
# WORKPAPER FOUR-EYES GOVERNANCE ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────
def _workpaper_to_response(wp) -> AuditWorkpaperResponse:
    return AuditWorkpaperResponse(
        id=wp.id,
        organization_id=wp.organization_id,
        audit_id=wp.audit_id,
        procedure_id=wp.procedure_id,
        version_number=wp.version_number,
        status=wp.status,
        testing_summary=wp.testing_summary,
        conclusion=wp.conclusion,
        prepared_by_id=wp.prepared_by_id,
        prepared_at=wp.prepared_at,
        reviewed_by_id=wp.reviewed_by_id,
        reviewed_at=wp.reviewed_at,
        review_notes=wp.review_notes,
        rejection_reason=wp.rejection_reason,
        workpaper_hash_sha256=wp.workpaper_hash_sha256,
        created_at=wp.created_at,
        updated_at=wp.updated_at,
        prepared_by_name=wp.prepared_by.full_name if wp.prepared_by else None,
        reviewed_by_name=wp.reviewed_by.full_name if wp.reviewed_by else None,
    )


@router.get(
    "/audits/{audit_id}/procedures/{procedure_id}/workpaper",
    response_model=Optional[AuditWorkpaperResponse],
    summary="Get Workpaper Review State",
)
def get_workpaper(
    audit_id: int,
    procedure_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not has_permission(current_user.role, Permission.AUDIT_READ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied.")
    wp = AuditFieldworkService.get_workpaper(
        db=db,
        organization_id=current_user.organization_id,
        audit_id=audit_id,
        procedure_id=procedure_id,
    )
    if not wp:
        return None
    return _workpaper_to_response(wp)


@router.post(
    "/audits/{audit_id}/procedures/{procedure_id}/workpaper/submit",
    response_model=AuditWorkpaperResponse,
    summary="Submit Workpaper for Four-Eyes Review",
)
def submit_workpaper(
    audit_id: int,
    procedure_id: int,
    obj_in: AuditWorkpaperSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        has_permission(current_user.role, Permission.AUDIT_MANAGE)
        or has_permission(current_user.role, Permission.AUDIT_EXECUTE)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied.")
    wp = AuditFieldworkService.submit_workpaper(
        db=db,
        organization_id=current_user.organization_id,
        audit_id=audit_id,
        procedure_id=procedure_id,
        user_id=current_user.id,
        obj_in=obj_in,
    )
    return _workpaper_to_response(wp)


@router.post(
    "/audits/{audit_id}/procedures/{procedure_id}/workpaper/approve",
    response_model=AuditWorkpaperResponse,
    summary="Approve Workpaper & Seal Digest (Four-Eyes)",
)
def approve_workpaper(
    audit_id: int,
    procedure_id: int,
    obj_in: AuditWorkpaperApprove,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        has_permission(current_user.role, Permission.AUDIT_APPROVE)
        or has_permission(current_user.role, Permission.AUDIT_REVIEW)
        or current_user.role in (RoleEnum.ADMIN, RoleEnum.MANAGER, RoleEnum.AUDITOR)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied.")
    wp = AuditFieldworkService.approve_workpaper(
        db=db,
        organization_id=current_user.organization_id,
        audit_id=audit_id,
        procedure_id=procedure_id,
        reviewer_id=current_user.id,
        obj_in=obj_in,
    )
    return _workpaper_to_response(wp)


@router.post(
    "/audits/{audit_id}/procedures/{procedure_id}/workpaper/request-changes",
    response_model=AuditWorkpaperResponse,
    summary="Request Changes on Workpaper (Reject)",
)
def request_changes_workpaper(
    audit_id: int,
    procedure_id: int,
    obj_in: AuditWorkpaperRequestChanges,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not (
        has_permission(current_user.role, Permission.AUDIT_APPROVE)
        or has_permission(current_user.role, Permission.AUDIT_REVIEW)
        or current_user.role in (RoleEnum.ADMIN, RoleEnum.MANAGER, RoleEnum.AUDITOR)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied.")
    wp = AuditFieldworkService.request_changes_workpaper(
        db=db,
        organization_id=current_user.organization_id,
        audit_id=audit_id,
        procedure_id=procedure_id,
        reviewer_id=current_user.id,
        obj_in=obj_in,
    )
    return _workpaper_to_response(wp)

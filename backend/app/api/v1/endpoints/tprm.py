from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.api.deps import get_current_user, get_db, require_permission
from app.core.permissions import Permission
from app.models.evidence import EvidenceItem, EvidenceStatusEnum
from app.models.finding import Finding, FindingSeverityEnum, FindingStatusEnum, FindingTypeEnum
from app.models.harmonization import CommonControlMapping, RationalizedCommonControl
from app.models.tprm import (
    BusinessCriticalityEnum,
    DataClassificationEnum,
    EngagementStatusEnum,
    HostingModelEnum,
    NetworkConnectivityEnum,
    PiiFinancialAccessEnum,
    Vendor,
    VendorAssessment,
    VendorAssessmentItem,
    VendorAssessmentStatusEnum,
    VendorAssessmentTypeEnum,
    VendorContract,
    VendorContractStatusEnum,
    VendorDocumentTypeEnum,
    VendorEngagement,
    VendorEvidenceLink,
    VendorOffboardingItem,
    VendorOffboardingRecord,
    VendorResponseStatusEnum,
    VendorRiskBandEnum,
    VendorSlaBreach,
    VendorSlaObligation,
    VendorStatusEnum,
    VendorSubprocessor,
    VendorTierEnum,
)
from app.models.user import User
from app.schemas.tprm import (
    ConcentrationRiskReportResponse,
    VendorAssessmentCreate,
    VendorAssessmentItemEscalateRequest,
    VendorAssessmentItemRead,
    VendorAssessmentItemUpdate,
    VendorAssessmentRead,
    VendorAssessmentReview,
    VendorAssessmentUpdate,
    VendorContractCreate,
    VendorContractRead,
    VendorContractReview,
    VendorContractUpdate,
    VendorCreate,
    VendorEngagementCreate,
    VendorEngagementRead,
    VendorEngagementUpdate,
    VendorEvidenceLinkCreate,
    VendorEvidenceLinkRead,
    VendorInherentRiskBreakdown,
    VendorOffboardingCancelRequest,
    VendorOffboardingCompleteRequest,
    VendorOffboardingInitiateRequest,
    VendorOffboardingItemAttestRequest,
    VendorOffboardingItemRead,
    VendorOffboardingItemWaiveRequest,
    VendorOffboardingRecordRead,
    VendorRead,
    VendorResidualRiskBreakdown,
    VendorRiskPostureResponse,
    VendorSlaBreachCreate,
    VendorSlaBreachEscalateRequest,
    VendorSlaBreachRead,
    VendorSlaBreachReopenRequest,
    VendorSlaBreachResolveRequest,
    VendorSlaBreachVerifyCloseRequest,
    VendorSlaBreachWaiveRequest,
    VendorSlaObligationCreate,
    VendorSlaObligationRead,
    VendorSlaObligationUpdate,
    VendorSubprocessorCreate,
    VendorSubprocessorRead,
    VendorSubprocessorReview,
    VendorSubprocessorUpdate,
    VendorTierOverride,
    VendorUpdate,
)
from app.services.audit_service import AuditService
from app.services.tprm_service import (
    ConflictError,
    TPRMService,
    UnprocessableEntityError,
)

router = APIRouter()


def _raise_http_for_tprm_error(e: Exception) -> None:
    if isinstance(e, PermissionError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    if isinstance(e, LookupError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    if isinstance(e, ConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    if isinstance(e, UnprocessableEntityError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ─── 1. VENDORS CRUD & OVERVIEW ──────────────────────────────────────────────

@router.get("/overview", response_model=Dict[str, Any])
def get_vendors_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_READ)),
):
    """Executive TPRM overview statistics."""
    vendors = (
        db.query(Vendor)
        .filter(Vendor.organization_id == current_user.organization_id)
        .all()
    )

    total_vendors = len(vendors)
    tier_counts = {t.value: 0 for t in VendorTierEnum}
    status_counts = {s.value: 0 for s in VendorStatusEnum}
    risk_band_counts = {b.value: 0 for b in VendorRiskBandEnum}
    total_residual = 0.0
    open_sla_breaches_total = 0
    approved_subprocessors_total = 0

    for v in vendors:
        tier_counts[v.effective_tier.value] += 1
        status_counts[v.vendor_status.value] += 1
        risk_band_counts[v.risk_band.value] += 1
        total_residual += v.residual_risk_score
        open_sla_breaches_total += getattr(v, "open_sla_breaches_count", 0) or 0
        approved_subprocessors_total += getattr(v, "approved_subprocessors_count", 0) or 0

    avg_residual = round(total_residual / total_vendors, 1) if total_vendors > 0 else 0.0
    high_critical_count = (
        risk_band_counts[VendorRiskBandEnum.HIGH.value]
        + risk_band_counts[VendorRiskBandEnum.CRITICAL.value]
    )

    active_contracts_count = (
        db.query(VendorContract)
        .filter(
            VendorContract.organization_id == current_user.organization_id,
            VendorContract.status.in_(
                [VendorContractStatusEnum.APPROVED, VendorContractStatusEnum.ACTIVE]
            ),
        )
        .count()
    )
    concentration_report = TPRMService.compute_concentration_risk(
        db, current_user.organization_id
    )

    return {
        "total_vendors": total_vendors,
        "average_residual_risk": avg_residual,
        "high_or_critical_risk_vendors": high_critical_count,
        "tier_distribution": tier_counts,
        "status_distribution": status_counts,
        "risk_band_distribution": risk_band_counts,
        "open_sla_breaches_count": open_sla_breaches_total,
        "approved_subprocessors_count": approved_subprocessors_total,
        "active_contracts_count": active_contracts_count,
        "spof_fourth_parties_count": concentration_report.spof_count,
    }


@router.get("/concentration-risk", response_model=ConcentrationRiskReportResponse)
def get_concentration_risk(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_READ)),
):
    """Computes fourth-party concentration risk and identifies Single Points of Failure (SPOFs)."""
    return TPRMService.compute_concentration_risk(db, current_user.organization_id)


@router.get("/subprocessors", response_model=List[VendorSubprocessorRead])
def list_all_organization_subprocessors(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_READ)),
):
    """Lists all subprocessors across the tenant organization."""
    return (
        db.query(VendorSubprocessor)
        .filter(VendorSubprocessor.organization_id == current_user.organization_id)
        .order_by(desc(VendorSubprocessor.created_at))
        .all()
    )


@router.get("", response_model=List[VendorRead])
def list_vendors(
    vendor_status: Optional[VendorStatusEnum] = None,
    tier: Optional[VendorTierEnum] = None,
    risk_band: Optional[VendorRiskBandEnum] = None,
    search: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_READ)),
):
    """Lists vendors strictly scoped to the tenant organization."""
    query = db.query(Vendor).filter(Vendor.organization_id == current_user.organization_id)

    if vendor_status:
        query = query.filter(Vendor.vendor_status == vendor_status)
    if tier:
        query = query.filter(
            (Vendor.override_tier == tier)
            | ((Vendor.override_tier.is_(None)) & (Vendor.calculated_tier == tier))
        )
    if risk_band:
        query = query.filter(Vendor.risk_band == risk_band)
    if search:
        query = query.filter(
            Vendor.legal_name.ilike(f"%{search}%")
            | Vendor.vendor_code.ilike(f"%{search}%")
            | Vendor.trade_name.ilike(f"%{search}%")
        )

    return query.order_by(desc(Vendor.created_at)).offset(offset).limit(limit).all()


@router.post("", response_model=VendorRead, status_code=status.HTTP_201_CREATED)
def create_vendor(
    payload: VendorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_MANAGE)),
):
    """Creates a new vendor profile."""
    # Check duplicate code within tenant
    existing = (
        db.query(Vendor)
        .filter(
            Vendor.organization_id == current_user.organization_id,
            Vendor.vendor_code == payload.vendor_code,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Vendor with code '{payload.vendor_code}' already exists in this organization.",
        )

    # Check business owner if provided
    if payload.business_owner_id:
        owner = (
            db.query(User)
            .filter(
                User.id == payload.business_owner_id,
                User.organization_id == current_user.organization_id,
                User.is_active == True,
            )
            .first()
        )
        if not owner:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Business owner must be an active user belonging to the organization.",
            )

    vendor = Vendor(
        organization_id=current_user.organization_id,
        vendor_code=payload.vendor_code,
        legal_name=payload.legal_name,
        trade_name=payload.trade_name,
        business_owner_id=payload.business_owner_id,
        vendor_status=VendorStatusEnum.PROSPECT,
        calculated_inherent_risk=0.0,
        calculated_tier=VendorTierEnum.TIER_4_LOW,
        residual_risk_score=0.0,
        risk_band=VendorRiskBandEnum.LOW,
    )
    db.add(vendor)
    db.commit()
    db.refresh(vendor)

    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        action="VENDOR_CREATED",
        resource_type="vendor",
        resource_id=str(vendor.id),
        actor_email=current_user.email,
        actor_id=current_user.id,
        details={"vendor_code": vendor.vendor_code, "legal_name": vendor.legal_name},
    )

    return vendor


@router.get("/{id}", response_model=VendorRead)
def get_vendor(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_READ)),
):
    """Retrieves vendor details."""
    vendor = (
        db.query(Vendor)
        .filter(Vendor.id == id, Vendor.organization_id == current_user.organization_id)
        .first()
    )
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor with ID {id} not found.",
        )
    return vendor


@router.patch("/{id}", response_model=VendorRead)
def update_vendor(
    id: int,
    payload: VendorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_MANAGE)),
):
    """Updates vendor metadata or transitions lifecycle status."""
    vendor = (
        db.query(Vendor)
        .filter(Vendor.id == id, Vendor.organization_id == current_user.organization_id)
        .first()
    )
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor with ID {id} not found.",
        )

    # Business owner check
    if payload.business_owner_id is not None:
        owner = (
            db.query(User)
            .filter(
                User.id == payload.business_owner_id,
                User.organization_id == current_user.organization_id,
                User.is_active == True,
            )
            .first()
        )
        if not owner:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Business owner must be an active user belonging to the organization.",
            )
        vendor.business_owner_id = payload.business_owner_id

    if payload.legal_name is not None:
        vendor.legal_name = payload.legal_name
    if payload.trade_name is not None:
        vendor.trade_name = payload.trade_name

    # Lifecycle transition
    status_changed = False
    if payload.vendor_status is not None and payload.vendor_status != vendor.vendor_status:
        try:
            TPRMService.validate_vendor_transition(
                current_status=vendor.vendor_status,
                new_status=payload.vendor_status,
                db=db,
                vendor=vendor,
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        old_status = vendor.vendor_status
        vendor.vendor_status = payload.vendor_status
        status_changed = True

        AuditService.log(
            db=db,
            organization_id=current_user.organization_id,
            action="VENDOR_STATUS_CHANGED",
            resource_type="vendor",
            resource_id=str(vendor.id),
            actor_email=current_user.email,
            actor_id=current_user.id,
            details={"old_status": old_status.value, "new_status": payload.vendor_status.value},
        )

    vendor.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(vendor)

    if not status_changed:
        AuditService.log(
            db=db,
            organization_id=current_user.organization_id,
            action="VENDOR_UPDATED",
            resource_type="vendor",
            resource_id=str(vendor.id),
            actor_email=current_user.email,
            actor_id=current_user.id,
            details={"vendor_code": vendor.vendor_code},
        )

    return vendor


# ─── 2. TIER GOVERNANCE & OVERRIDE ──────────────────────────────────────────

@router.post("/{id}/override-tier", response_model=VendorRead)
def override_vendor_tier(
    id: int,
    payload: VendorTierOverride,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_APPROVE)),
):
    """Authoritative tier override requiring justification and approval permission."""
    vendor = (
        db.query(Vendor)
        .filter(Vendor.id == id, Vendor.organization_id == current_user.organization_id)
        .first()
    )
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor with ID {id} not found.",
        )

    if len(payload.reason.strip()) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tier override justification reason must be at least 10 characters.",
        )

    vendor.override_tier = payload.override_tier
    vendor.tier_override_reason = payload.reason
    vendor.tier_overridden_by_id = current_user.id
    vendor.tier_overridden_at = datetime.now(timezone.utc)
    vendor.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(vendor)

    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        action="VENDOR_TIER_OVERRIDE",
        resource_type="vendor",
        resource_id=str(vendor.id),
        actor_email=current_user.email,
        actor_id=current_user.id,
        details={
            "override_tier": payload.override_tier.value,
            "calculated_tier": vendor.calculated_tier.value,
            "reason": payload.reason,
        },
    )

    return vendor


# ─── 3. ENGAGEMENTS ─────────────────────────────────────────────────────────

@router.post("/{id}/engagements", response_model=VendorEngagementRead, status_code=status.HTTP_201_CREATED)
def create_engagement(
    id: int,
    payload: VendorEngagementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_MANAGE)),
):
    """Registers a new engagement and recomputes vendor inherent risk."""
    vendor = (
        db.query(Vendor)
        .filter(Vendor.id == id, Vendor.organization_id == current_user.organization_id)
        .first()
    )
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor with ID {id} not found.",
        )

    if vendor.vendor_status in (
        VendorStatusEnum.OFFBOARDED,
        VendorStatusEnum.TERMINATED,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot create new engagements for vendor in terminal status '{vendor.vendor_status.value}'.",
        )

    # Check unique engagement code within org
    existing = (
        db.query(VendorEngagement)
        .filter(
            VendorEngagement.organization_id == current_user.organization_id,
            VendorEngagement.engagement_code == payload.engagement_code,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Engagement with code '{payload.engagement_code}' already exists.",
        )

    risk = TPRMService.calculate_engagement_risk(
        criticality=payload.criticality,
        data_classification=payload.data_classification,
        network=payload.network_connectivity,
        pii=payload.pii_access,
        hosting=payload.hosting_model,
    )

    engagement = VendorEngagement(
        organization_id=current_user.organization_id,
        vendor_id=vendor.id,
        engagement_code=payload.engagement_code,
        engagement_name=payload.engagement_name,
        description=payload.description,
        status=EngagementStatusEnum.ACTIVE,
        criticality=payload.criticality,
        data_classification=payload.data_classification,
        hosting_model=payload.hosting_model,
        network_connectivity=payload.network_connectivity,
        pii_access=payload.pii_access,
        calculated_risk_score=risk,
    )
    db.add(engagement)
    db.flush()

    # Recalculate vendor telemetry
    TPRMService.recalculate_vendor_telemetry(db, vendor)
    db.commit()
    db.refresh(engagement)

    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        action="VENDOR_ENGAGEMENT_CREATED",
        resource_type="vendor_engagement",
        resource_id=str(engagement.id),
        actor_email=current_user.email,
        actor_id=current_user.id,
        details={
            "vendor_code": vendor.vendor_code,
            "engagement_code": engagement.engagement_code,
            "risk_score": risk,
        },
    )

    return engagement


@router.patch("/engagements/{engagement_id}", response_model=VendorEngagementRead)
def update_engagement(
    engagement_id: int,
    payload: VendorEngagementUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_MANAGE)),
):
    """Updates engagement parameters and recomputes vendor inherent risk."""
    engagement = (
        db.query(VendorEngagement)
        .filter(
            VendorEngagement.id == engagement_id,
            VendorEngagement.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not engagement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Engagement with ID {engagement_id} not found.",
        )

    if payload.engagement_name is not None:
        engagement.engagement_name = payload.engagement_name
    if payload.description is not None:
        engagement.description = payload.description
    if payload.status is not None:
        engagement.status = payload.status
    if payload.criticality is not None:
        engagement.criticality = payload.criticality
    if payload.data_classification is not None:
        engagement.data_classification = payload.data_classification
    if payload.hosting_model is not None:
        engagement.hosting_model = payload.hosting_model
    if payload.network_connectivity is not None:
        engagement.network_connectivity = payload.network_connectivity
    if payload.pii_access is not None:
        engagement.pii_access = payload.pii_access

    engagement.calculated_risk_score = TPRMService.calculate_engagement_risk(
        criticality=engagement.criticality,
        data_classification=engagement.data_classification,
        network=engagement.network_connectivity,
        pii=engagement.pii_access,
        hosting=engagement.hosting_model,
    )
    engagement.updated_at = datetime.now(timezone.utc)

    # Recalculate vendor telemetry
    TPRMService.recalculate_vendor_telemetry(db, engagement.vendor)
    db.commit()
    db.refresh(engagement)

    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        action="VENDOR_ENGAGEMENT_UPDATED",
        resource_type="vendor_engagement",
        resource_id=str(engagement.id),
        actor_email=current_user.email,
        actor_id=current_user.id,
        details={"engagement_code": engagement.engagement_code},
    )

    return engagement


# ─── 4. ASSESSMENTS & QUESTIONNAIRES ────────────────────────────────────────

@router.get("/{id}/assessments", response_model=List[VendorAssessmentRead])
def list_vendor_assessments(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_READ)),
):
    """Lists assessments for a specific vendor."""
    vendor = (
        db.query(Vendor)
        .filter(Vendor.id == id, Vendor.organization_id == current_user.organization_id)
        .first()
    )
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor with ID {id} not found.",
        )

    return (
        db.query(VendorAssessment)
        .filter(VendorAssessment.vendor_id == vendor.id)
        .order_by(desc(VendorAssessment.created_at))
        .all()
    )


@router.post("/{id}/assessments", response_model=VendorAssessmentRead, status_code=status.HTTP_201_CREATED)
def create_vendor_assessment(
    id: int,
    payload: VendorAssessmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_ASSESS)),
):
    """Creates a new assessment questionnaire for a vendor."""
    vendor = (
        db.query(Vendor)
        .filter(Vendor.id == id, Vendor.organization_id == current_user.organization_id)
        .first()
    )
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor with ID {id} not found.",
        )

    if vendor.vendor_status in (
        VendorStatusEnum.OFFBOARDED,
        VendorStatusEnum.TERMINATED,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot create new assessments for vendor in terminal status '{vendor.vendor_status.value}'.",
        )

    # Check unique assessment code
    existing = (
        db.query(VendorAssessment)
        .filter(
            VendorAssessment.organization_id == current_user.organization_id,
            VendorAssessment.assessment_code == payload.assessment_code,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Assessment code '{payload.assessment_code}' already exists.",
        )

    if payload.engagement_id:
        eng = (
            db.query(VendorEngagement)
            .filter(
                VendorEngagement.id == payload.engagement_id,
                VendorEngagement.vendor_id == vendor.id,
            )
            .first()
        )
        if not eng:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Engagement does not belong to this vendor.",
            )

    assessment = VendorAssessment(
        organization_id=current_user.organization_id,
        vendor_id=vendor.id,
        engagement_id=payload.engagement_id,
        assessment_code=payload.assessment_code,
        title=payload.title,
        assessment_type=payload.assessment_type,
        status=VendorAssessmentStatusEnum.DRAFT,
        assessor_id=current_user.id,
        valid_until=payload.valid_until,
        calculated_score=0.0,
    )
    db.add(assessment)
    db.flush()

    # Add items if provided
    if payload.items:
        for item_data in payload.items:
            item = VendorAssessmentItem(
                organization_id=current_user.organization_id,
                assessment_id=assessment.id,
                rationalized_common_control_id=item_data.rationalized_common_control_id,
                question_key=item_data.question_key,
                question_text=item_data.question_text,
                response_status=item_data.response_status,
                weight=item_data.weight,
                vendor_response_text=item_data.vendor_response_text,
                assessor_notes=item_data.assessor_notes,
            )
            db.add(item)
        db.flush()
        assessment.calculated_score = TPRMService.calculate_assessment_score(assessment.items)

    db.commit()
    db.refresh(assessment)

    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        action="VENDOR_ASSESSMENT_CREATED",
        resource_type="vendor_assessment",
        resource_id=str(assessment.id),
        actor_email=current_user.email,
        actor_id=current_user.id,
        details={"assessment_code": assessment.assessment_code, "vendor_code": vendor.vendor_code},
    )

    return assessment


@router.get("/assessments/{assessment_id}", response_model=VendorAssessmentRead)
def get_vendor_assessment(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_READ)),
):
    """Retrieves an assessment with all its line items."""
    assessment = (
        db.query(VendorAssessment)
        .filter(
            VendorAssessment.id == assessment_id,
            VendorAssessment.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment with ID {assessment_id} not found.",
        )
    return assessment


@router.patch("/assessments/{assessment_id}/items", response_model=VendorAssessmentRead)
def update_assessment_items(
    assessment_id: int,
    payload: Dict[int, VendorAssessmentItemUpdate],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_ASSESS)),
):
    """Updates questionnaire item responses and recomputes assessment score."""
    assessment = (
        db.query(VendorAssessment)
        .filter(
            VendorAssessment.id == assessment_id,
            VendorAssessment.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment with ID {assessment_id} not found.",
        )

    # Immutability check
    if assessment.status in [VendorAssessmentStatusEnum.APPROVED, VendorAssessmentStatusEnum.SUPERSEDED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify items of an approved or superseded assessment (historical immutability).",
        )

    for item_id, item_update in payload.items():
        item = (
            db.query(VendorAssessmentItem)
            .filter(
                VendorAssessmentItem.id == item_id,
                VendorAssessmentItem.assessment_id == assessment.id,
            )
            .first()
        )
        if not item:
            continue

        if item_update.response_status is not None:
            item.response_status = item_update.response_status
            # If NON_COMPLIANT and linked to a common control, generate a Finding if needed
            if (
                item.response_status == VendorResponseStatusEnum.NON_COMPLIANT
                and item.rationalized_common_control_id is not None
            ):
                item.findings_count = max(item.findings_count, 1)

        if item_update.vendor_response_text is not None:
            item.vendor_response_text = item_update.vendor_response_text
        if item_update.assessor_notes is not None:
            item.assessor_notes = item_update.assessor_notes

    db.flush()
    assessment.calculated_score = TPRMService.calculate_assessment_score(assessment.items)
    assessment.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(assessment)

    return assessment


@router.post("/assessments/{assessment_id}/submit", response_model=VendorAssessmentRead)
def submit_assessment(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_ASSESS)),
):
    """Submits a draft assessment (transitions DRAFT -> SUBMITTED)."""
    assessment = (
        db.query(VendorAssessment)
        .filter(
            VendorAssessment.id == assessment_id,
            VendorAssessment.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment with ID {assessment_id} not found.",
        )

    try:
        TPRMService.validate_assessment_transition(
            current_status=assessment.status,
            new_status=VendorAssessmentStatusEnum.SUBMITTED,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    assessment.status = VendorAssessmentStatusEnum.SUBMITTED
    assessment.submitted_at = datetime.now(timezone.utc)
    assessment.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(assessment)

    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        action="VENDOR_ASSESSMENT_SUBMITTED",
        resource_type="vendor_assessment",
        resource_id=str(assessment.id),
        actor_email=current_user.email,
        actor_id=current_user.id,
        details={"assessment_code": assessment.assessment_code},
    )

    return assessment


@router.post("/assessments/{assessment_id}/start-review", response_model=VendorAssessmentRead)
def start_assessment_review(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_APPROVE)),
):
    """Transitions a submitted assessment into review (transitions SUBMITTED -> IN_REVIEW)."""
    assessment = (
        db.query(VendorAssessment)
        .filter(
            VendorAssessment.id == assessment_id,
            VendorAssessment.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment with ID {assessment_id} not found.",
        )

    try:
        TPRMService.validate_assessment_transition(
            current_status=assessment.status,
            new_status=VendorAssessmentStatusEnum.IN_REVIEW,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    assessment.status = VendorAssessmentStatusEnum.IN_REVIEW
    assessment.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(assessment)

    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        action="VENDOR_ASSESSMENT_IN_REVIEW",
        resource_type="vendor_assessment",
        resource_id=str(assessment.id),
        actor_email=current_user.email,
        actor_id=current_user.id,
        details={"assessment_code": assessment.assessment_code},
    )

    return assessment


@router.post("/assessments/{assessment_id}/approve", response_model=VendorAssessmentRead)
def approve_assessment(
    assessment_id: int,
    payload: VendorAssessmentReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_APPROVE)),
):
    """Approves an in-review assessment with four-eyes separation of duties."""
    assessment = (
        db.query(VendorAssessment)
        .filter(
            VendorAssessment.id == assessment_id,
            VendorAssessment.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment with ID {assessment_id} not found.",
        )

    try:
        approved = TPRMService.approve_assessment(
            db=db,
            assessment=assessment,
            reviewer_id=current_user.id,
            review_notes=payload.review_notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    db.commit()
    db.refresh(approved)

    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        action="VENDOR_ASSESSMENT_APPROVED",
        resource_type="vendor_assessment",
        resource_id=str(approved.id),
        actor_email=current_user.email,
        actor_id=current_user.id,
        details={
            "assessment_code": approved.assessment_code,
            "calculated_score": approved.calculated_score,
            "vendor_code": approved.vendor.vendor_code,
        },
    )

    return approved


@router.post("/assessments/{assessment_id}/reject", response_model=VendorAssessmentRead)
def reject_assessment(
    assessment_id: int,
    payload: VendorAssessmentReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_APPROVE)),
):
    """Rejects an in-review assessment with mandatory reason, returning it to DRAFT."""
    assessment = (
        db.query(VendorAssessment)
        .filter(
            VendorAssessment.id == assessment_id,
            VendorAssessment.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment with ID {assessment_id} not found.",
        )

    if not payload.rejection_reason or len(payload.rejection_reason.strip()) < 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mandatory rejection reason required (minimum 5 characters).",
        )

    try:
        TPRMService.validate_assessment_transition(
            current_status=assessment.status,
            new_status=VendorAssessmentStatusEnum.REJECTED,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    assessment.status = VendorAssessmentStatusEnum.DRAFT
    assessment.rejection_reason = payload.rejection_reason
    assessment.review_notes = payload.review_notes
    assessment.reviewer_id = current_user.id
    assessment.reviewed_at = datetime.now(timezone.utc)
    assessment.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(assessment)

    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        action="VENDOR_ASSESSMENT_REJECTED",
        resource_type="vendor_assessment",
        resource_id=str(assessment.id),
        actor_email=current_user.email,
        actor_id=current_user.id,
        details={
            "assessment_code": assessment.assessment_code,
            "rejection_reason": payload.rejection_reason,
        },
    )

    return assessment


# ─── 5. EVIDENCE INTEGRATION (REUSING PHASE 3) ──────────────────────────────

@router.post("/{id}/evidence", response_model=VendorEvidenceLinkRead, status_code=status.HTTP_201_CREATED)
def link_vendor_evidence(
    id: int,
    payload: VendorEvidenceLinkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_MANAGE)),
):
    """Links an existing Phase 3 EvidenceItem to a vendor."""
    vendor = (
        db.query(Vendor)
        .filter(Vendor.id == id, Vendor.organization_id == current_user.organization_id)
        .first()
    )
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor with ID {id} not found.",
        )

    # Check evidence exists, belongs to tenant, and is not superseded
    evidence = (
        db.query(EvidenceItem)
        .filter(
            EvidenceItem.id == payload.evidence_id,
            EvidenceItem.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not evidence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"EvidenceItem with ID {payload.evidence_id} not found in this organization.",
        )

    if evidence.status == EvidenceStatusEnum.SUPERSEDED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot link superseded evidence to a vendor.",
        )

    # Check duplicate link
    existing_link = (
        db.query(VendorEvidenceLink)
        .filter(
            VendorEvidenceLink.vendor_id == vendor.id,
            VendorEvidenceLink.evidence_id == evidence.id,
        )
        .first()
    )
    if existing_link:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="EvidenceItem is already linked to this vendor.",
        )

    link = VendorEvidenceLink(
        organization_id=current_user.organization_id,
        vendor_id=vendor.id,
        evidence_id=evidence.id,
        document_type=payload.document_type,
        effective_date=payload.effective_date,
        expiration_date=payload.expiration_date,
        is_verified=True if evidence.status == EvidenceStatusEnum.ACCEPTED else False,
        verified_by_id=current_user.id if evidence.status == EvidenceStatusEnum.ACCEPTED else None,
        verified_at=datetime.now(timezone.utc) if evidence.status == EvidenceStatusEnum.ACCEPTED else None,
    )
    db.add(link)
    db.commit()
    db.refresh(link)

    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        action="VENDOR_EVIDENCE_LINKED",
        resource_type="vendor_evidence_link",
        resource_id=str(link.id),
        actor_email=current_user.email,
        actor_id=current_user.id,
        details={
            "vendor_code": vendor.vendor_code,
            "evidence_id": evidence.id,
            "document_type": payload.document_type.value,
        },
    )

    return link


@router.delete("/{id}/evidence/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_vendor_evidence(
    id: int,
    link_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_MANAGE)),
):
    """Unlinks evidence from a vendor without deleting the underlying EvidenceItem."""
    link = (
        db.query(VendorEvidenceLink)
        .filter(
            VendorEvidenceLink.id == link_id,
            VendorEvidenceLink.vendor_id == id,
            VendorEvidenceLink.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor evidence link with ID {link_id} not found.",
        )

    db.delete(link)
    db.commit()

    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        action="VENDOR_EVIDENCE_UNLINKED",
        resource_type="vendor_evidence_link",
        resource_id=str(link_id),
        actor_email=current_user.email,
        actor_id=current_user.id,
        details={"vendor_id": id, "link_id": link_id},
    )

    return None


# ─── 6. VENDOR RISK POSTURE TELEMETRY ────────────────────────────────────────

@router.get("/{id}/risk-posture", response_model=VendorRiskPostureResponse)
def get_vendor_risk_posture(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_READ)),
):
    """Detailed vendor risk posture telemetry."""
    vendor = (
        db.query(Vendor)
        .filter(Vendor.id == id, Vendor.organization_id == current_user.organization_id)
        .first()
    )
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor with ID {id} not found.",
        )

    # Recalculate live telemetry
    TPRMService.recalculate_vendor_telemetry(db, vendor)
    db.commit()
    db.refresh(vendor)

    # Find highest criticality engagement code
    active_engs = [e for e in vendor.engagements if e.status == EngagementStatusEnum.ACTIVE]
    highest_code = None
    if active_engs:
        sorted_engs = sorted(
            active_engs,
            key=lambda e: TPRMService.CRITICALITY_SCORES.get(e.criticality, 0),
            reverse=True,
        )
        highest_code = sorted_engs[0].engagement_code

    # Latest approved assessment
    latest_assessment = (
        db.query(VendorAssessment)
        .filter(
            VendorAssessment.vendor_id == vendor.id,
            VendorAssessment.status == VendorAssessmentStatusEnum.APPROVED,
        )
        .order_by(desc(VendorAssessment.reviewed_at))
        .first()
    )
    latest_score = latest_assessment.calculated_score if latest_assessment else None

    # Risk floor & base residual
    risk_floor = 0.20 * vendor.calculated_inherent_risk
    if latest_score is not None:
        base_residual = vendor.calculated_inherent_risk * (1.0 - (0.70 * (latest_score / 100.0)))
    else:
        base_residual = vendor.calculated_inherent_risk

    penalties = TPRMService.compute_vendor_penalty_breakdown(
        db=db, vendor=vendor, latest_assessment=latest_assessment
    )
    concentration_report = TPRMService.compute_concentration_risk(
        db=db, organization_id=current_user.organization_id
    )
    latest_offboarding = (
        vendor.offboarding_records[0].status if vendor.offboarding_records else None
    )

    return VendorRiskPostureResponse(
        vendor_id=vendor.id,
        vendor_code=vendor.vendor_code,
        legal_name=vendor.legal_name,
        status=vendor.vendor_status,
        inherent=VendorInherentRiskBreakdown(
            inherent_risk_score=vendor.calculated_inherent_risk,
            calculated_tier=vendor.calculated_tier,
            effective_tier=vendor.effective_tier,
            highest_criticality_engagement_code=highest_code,
            active_engagements_count=len(active_engs),
        ),
        residual=VendorResidualRiskBreakdown(
            inherent_risk_score=vendor.calculated_inherent_risk,
            latest_assessment_score=latest_score,
            risk_floor=round(risk_floor, 1),
            base_residual_risk=round(base_residual, 1),
            finding_penalties=penalties["finding_penalties"],
            exception_penalties=penalties["exception_penalties"],
            sla_breach_penalties=penalties["sla_breach_penalties"],
            subprocessor_penalties=penalties["subprocessor_penalties"],
            residual_risk_score=vendor.residual_risk_score,
            risk_band=vendor.risk_band,
        ),
        finding_penalties=penalties["finding_penalties"],
        exception_penalties=penalties["exception_penalties"],
        sla_breach_penalties=penalties["sla_breach_penalties"],
        subprocessor_penalties=penalties["subprocessor_penalties"],
        open_sla_breaches_count=vendor.open_sla_breaches_count or 0,
        approved_subprocessors_count=vendor.approved_subprocessors_count or 0,
        concentration_risk_summary={
            "shared_fourth_party_count": concentration_report.shared_fourth_party_count,
            "spof_count": concentration_report.spof_count,
        },
        offboarding_status=latest_offboarding,
        engagements=vendor.engagements,
        latest_approved_assessment=latest_assessment,
        evidence_links=vendor.evidence_links,
        contracts=vendor.contracts,
        subprocessors=vendor.subprocessors,
        sla_obligations=vendor.sla_obligations,
        sla_breaches=vendor.sla_breaches,
        offboarding_records=vendor.offboarding_records,
    )


# ─── 7. BATCH 6: VENDOR CONTRACTS & LEGAL ASSURANCE ─────────────────────────

def _get_vendor_or_404(db: Session, vendor_id: int, organization_id: int) -> Vendor:
    vendor = (
        db.query(Vendor)
        .filter(Vendor.id == vendor_id, Vendor.organization_id == organization_id)
        .first()
    )
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor with ID {vendor_id} not found.",
        )
    return vendor


def _get_contract_or_404(
    db: Session, vendor_id: int, contract_id: int, organization_id: int
) -> VendorContract:
    contract = (
        db.query(VendorContract)
        .filter(
            VendorContract.id == contract_id,
            VendorContract.vendor_id == vendor_id,
            VendorContract.organization_id == organization_id,
        )
        .first()
    )
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor contract with ID {contract_id} not found.",
        )
    return contract


@router.get("/{id}/contracts", response_model=List[VendorContractRead])
def list_vendor_contracts(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_READ)),
):
    vendor = _get_vendor_or_404(db, id, current_user.organization_id)
    return (
        db.query(VendorContract)
        .filter(
            VendorContract.vendor_id == vendor.id,
            VendorContract.organization_id == current_user.organization_id,
        )
        .order_by(desc(VendorContract.created_at))
        .all()
    )


@router.post(
    "/{id}/contracts",
    response_model=VendorContractRead,
    status_code=status.HTTP_201_CREATED,
)
def create_vendor_contract(
    id: int,
    payload: VendorContractCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_MANAGE)),
):
    vendor = _get_vendor_or_404(db, id, current_user.organization_id)
    try:
        contract = TPRMService.create_contract(
            db=db, vendor=vendor, payload=payload, creator_id=current_user.id
        )
    except Exception as e:
        _raise_http_for_tprm_error(e)

    db.commit()
    db.refresh(contract)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        action="VENDOR_CONTRACT_CREATED",
        resource_type="vendor_contract",
        resource_id=str(contract.id),
        actor_email=current_user.email,
        actor_id=current_user.id,
        details={
            "vendor_id": vendor.id,
            "contract_code": contract.contract_code,
            "contract_type": contract.contract_type.value,
        },
    )
    return contract


@router.patch("/{id}/contracts/{contract_id}", response_model=VendorContractRead)
def update_vendor_contract(
    id: int,
    contract_id: int,
    payload: VendorContractUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_MANAGE)),
):
    _get_vendor_or_404(db, id, current_user.organization_id)
    contract = _get_contract_or_404(db, id, contract_id, current_user.organization_id)
    try:
        updated = TPRMService.update_contract(db=db, contract=contract, payload=payload)
    except Exception as e:
        _raise_http_for_tprm_error(e)

    db.commit()
    db.refresh(updated)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        action="VENDOR_CONTRACT_UPDATED",
        resource_type="vendor_contract",
        resource_id=str(updated.id),
        actor_email=current_user.email,
        actor_id=current_user.id,
        details={"contract_code": updated.contract_code},
    )
    return updated


@router.post("/{id}/contracts/{contract_id}/submit", response_model=VendorContractRead)
@router.post(
    "/{id}/contracts/{contract_id}/submit-review", response_model=VendorContractRead
)
def submit_vendor_contract(
    id: int,
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_MANAGE)),
):
    _get_vendor_or_404(db, id, current_user.organization_id)
    contract = _get_contract_or_404(db, id, contract_id, current_user.organization_id)
    try:
        submitted = TPRMService.submit_contract(
            db=db, contract=contract, submitter_id=current_user.id
        )
    except Exception as e:
        _raise_http_for_tprm_error(e)

    db.commit()
    db.refresh(submitted)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        action="VENDOR_CONTRACT_SUBMITTED",
        resource_type="vendor_contract",
        resource_id=str(submitted.id),
        actor_email=current_user.email,
        actor_id=current_user.id,
        details={"contract_code": submitted.contract_code},
    )
    return submitted


@router.post("/{id}/contracts/{contract_id}/approve", response_model=VendorContractRead)
def approve_vendor_contract(
    id: int,
    contract_id: int,
    payload: VendorContractReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_APPROVE)),
):
    _get_vendor_or_404(db, id, current_user.organization_id)
    contract = _get_contract_or_404(db, id, contract_id, current_user.organization_id)
    try:
        approved = TPRMService.approve_contract(
            db=db,
            contract=contract,
            approver_id=current_user.id,
            payload=payload,
        )
    except Exception as e:
        _raise_http_for_tprm_error(e)

    db.commit()
    db.refresh(approved)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        action="VENDOR_CONTRACT_APPROVED",
        resource_type="vendor_contract",
        resource_id=str(approved.id),
        actor_email=current_user.email,
        actor_id=current_user.id,
        details={
            "contract_code": approved.contract_code,
            "status": approved.status.value,
        },
    )
    return approved


@router.post("/{id}/contracts/{contract_id}/reject", response_model=VendorContractRead)
def reject_vendor_contract(
    id: int,
    contract_id: int,
    payload: VendorContractReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_APPROVE)),
):
    _get_vendor_or_404(db, id, current_user.organization_id)
    contract = _get_contract_or_404(db, id, contract_id, current_user.organization_id)
    try:
        rejected = TPRMService.reject_contract(
            db=db,
            contract=contract,
            reviewer_id=current_user.id,
            payload=payload,
        )
    except Exception as e:
        _raise_http_for_tprm_error(e)

    db.commit()
    db.refresh(rejected)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        action="VENDOR_CONTRACT_REJECTED",
        resource_type="vendor_contract",
        resource_id=str(rejected.id),
        actor_email=current_user.email,
        actor_id=current_user.id,
        details={
            "contract_code": rejected.contract_code,
            "rejection_reason": rejected.rejection_reason,
        },
    )
    return rejected


# ─── 8. BATCH 6: SUBPROCESSORS & FOURTH-PARTY LINEAGE ───────────────────────

def _get_subprocessor_or_404(
    db: Session, vendor_id: int, subprocessor_id: int, organization_id: int
) -> VendorSubprocessor:
    sp = (
        db.query(VendorSubprocessor)
        .filter(
            VendorSubprocessor.id == subprocessor_id,
            VendorSubprocessor.vendor_id == vendor_id,
            VendorSubprocessor.organization_id == organization_id,
        )
        .first()
    )
    if not sp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor subprocessor with ID {subprocessor_id} not found.",
        )
    return sp


@router.get("/{id}/subprocessors", response_model=List[VendorSubprocessorRead])
def list_vendor_subprocessors(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_READ)),
):
    vendor = _get_vendor_or_404(db, id, current_user.organization_id)
    return (
        db.query(VendorSubprocessor)
        .filter(
            VendorSubprocessor.vendor_id == vendor.id,
            VendorSubprocessor.organization_id == current_user.organization_id,
        )
        .order_by(desc(VendorSubprocessor.created_at))
        .all()
    )


@router.post(
    "/{id}/subprocessors",
    response_model=VendorSubprocessorRead,
    status_code=status.HTTP_201_CREATED,
)
def create_vendor_subprocessor(
    id: int,
    payload: VendorSubprocessorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_ASSESS)),
):
    vendor = _get_vendor_or_404(db, id, current_user.organization_id)
    try:
        sp = TPRMService.create_subprocessor(
            db=db, vendor=vendor, payload=payload, creator_id=current_user.id
        )
    except Exception as e:
        _raise_http_for_tprm_error(e)

    db.commit()
    db.refresh(sp)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        action="VENDOR_SUBPROCESSOR_REGISTERED",
        resource_type="vendor_subprocessor",
        resource_id=str(sp.id),
        actor_email=current_user.email,
        actor_id=current_user.id,
        details={
            "vendor_id": vendor.id,
            "subprocessor_code": sp.subprocessor_code,
            "subprocessor_name": sp.subprocessor_name,
        },
    )
    return sp


@router.patch(
    "/{id}/subprocessors/{subprocessor_id}", response_model=VendorSubprocessorRead
)
def update_vendor_subprocessor(
    id: int,
    subprocessor_id: int,
    payload: VendorSubprocessorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_ASSESS)),
):
    _get_vendor_or_404(db, id, current_user.organization_id)
    sp = _get_subprocessor_or_404(
        db, id, subprocessor_id, current_user.organization_id
    )
    try:
        updated = TPRMService.update_subprocessor(db=db, sp=sp, payload=payload)
    except Exception as e:
        _raise_http_for_tprm_error(e)

    db.commit()
    db.refresh(updated)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        action="VENDOR_SUBPROCESSOR_UPDATED",
        resource_type="vendor_subprocessor",
        resource_id=str(updated.id),
        actor_email=current_user.email,
        actor_id=current_user.id,
        details={"subprocessor_code": updated.subprocessor_code},
    )
    return updated


@router.post(
    "/{id}/subprocessors/{subprocessor_id}/submit",
    response_model=VendorSubprocessorRead,
)
@router.post(
    "/{id}/subprocessors/{subprocessor_id}/submit-review",
    response_model=VendorSubprocessorRead,
)
def submit_vendor_subprocessor(
    id: int,
    subprocessor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_ASSESS)),
):
    _get_vendor_or_404(db, id, current_user.organization_id)
    sp = _get_subprocessor_or_404(
        db, id, subprocessor_id, current_user.organization_id
    )
    try:
        submitted = TPRMService.submit_subprocessor(
            db=db, sp=sp, submitter_id=current_user.id
        )
    except Exception as e:
        _raise_http_for_tprm_error(e)

    db.commit()
    db.refresh(submitted)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        action="VENDOR_SUBPROCESSOR_SUBMITTED",
        resource_type="vendor_subprocessor",
        resource_id=str(submitted.id),
        actor_email=current_user.email,
        actor_id=current_user.id,
        details={"subprocessor_code": submitted.subprocessor_code},
    )
    return submitted


@router.post(
    "/{id}/subprocessors/{subprocessor_id}/approve",
    response_model=VendorSubprocessorRead,
)
def approve_vendor_subprocessor(
    id: int,
    subprocessor_id: int,
    payload: VendorSubprocessorReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_APPROVE)),
):
    _get_vendor_or_404(db, id, current_user.organization_id)
    sp = _get_subprocessor_or_404(
        db, id, subprocessor_id, current_user.organization_id
    )
    try:
        approved = TPRMService.approve_subprocessor(
            db=db, sp=sp, approver_id=current_user.id, payload=payload
        )
    except Exception as e:
        _raise_http_for_tprm_error(e)

    db.commit()
    db.refresh(approved)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        action="VENDOR_SUBPROCESSOR_APPROVED",
        resource_type="vendor_subprocessor",
        resource_id=str(approved.id),
        actor_email=current_user.email,
        actor_id=current_user.id,
        details={"subprocessor_code": approved.subprocessor_code},
    )
    return approved


@router.post(
    "/{id}/subprocessors/{subprocessor_id}/reject",
    response_model=VendorSubprocessorRead,
)
def reject_vendor_subprocessor(
    id: int,
    subprocessor_id: int,
    payload: VendorSubprocessorReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_APPROVE)),
):
    _get_vendor_or_404(db, id, current_user.organization_id)
    sp = _get_subprocessor_or_404(
        db, id, subprocessor_id, current_user.organization_id
    )
    try:
        rejected = TPRMService.reject_subprocessor(
            db=db, sp=sp, reviewer_id=current_user.id, payload=payload
        )
    except Exception as e:
        _raise_http_for_tprm_error(e)

    db.commit()
    db.refresh(rejected)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        action="VENDOR_SUBPROCESSOR_REJECTED",
        resource_type="vendor_subprocessor",
        resource_id=str(rejected.id),
        actor_email=current_user.email,
        actor_id=current_user.id,
        details={
            "subprocessor_code": rejected.subprocessor_code,
            "rejection_reason": rejected.rejection_reason,
        },
    )
    return rejected


@router.post(
    "/{id}/subprocessors/{subprocessor_id}/suspend",
    response_model=VendorSubprocessorRead,
)
def suspend_vendor_subprocessor(
    id: int,
    subprocessor_id: int,
    payload: VendorSubprocessorReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_APPROVE)),
):
    _get_vendor_or_404(db, id, current_user.organization_id)
    sp = _get_subprocessor_or_404(
        db, id, subprocessor_id, current_user.organization_id
    )
    try:
        suspended = TPRMService.suspend_subprocessor(
            db=db, sp=sp, actor_id=current_user.id, payload=payload
        )
    except Exception as e:
        _raise_http_for_tprm_error(e)

    db.commit()
    db.refresh(suspended)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        action="VENDOR_SUBPROCESSOR_SUSPENDED",
        resource_type="vendor_subprocessor",
        resource_id=str(suspended.id),
        actor_email=current_user.email,
        actor_id=current_user.id,
        details={
            "subprocessor_code": suspended.subprocessor_code,
            "suspension_reason": suspended.suspension_reason,
        },
    )
    return suspended


@router.post(
    "/{id}/subprocessors/{subprocessor_id}/terminate",
    response_model=VendorSubprocessorRead,
)
def terminate_vendor_subprocessor(
    id: int,
    subprocessor_id: int,
    payload: VendorSubprocessorReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_APPROVE)),
):
    _get_vendor_or_404(db, id, current_user.organization_id)
    sp = _get_subprocessor_or_404(
        db, id, subprocessor_id, current_user.organization_id
    )
    try:
        terminated = TPRMService.terminate_subprocessor(
            db=db, sp=sp, actor_id=current_user.id, payload=payload
        )
    except Exception as e:
        _raise_http_for_tprm_error(e)

    db.commit()
    db.refresh(terminated)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        action="VENDOR_SUBPROCESSOR_TERMINATED",
        resource_type="vendor_subprocessor",
        resource_id=str(terminated.id),
        actor_email=current_user.email,
        actor_id=current_user.id,
        details={
            "subprocessor_code": terminated.subprocessor_code,
            "termination_reason": terminated.termination_reason,
        },
    )
    return terminated


# ─── 9. BATCH 6: SLA OBLIGATIONS & BREACH ESCALATION ────────────────────────

def _get_sla_obligation_or_404(
    db: Session, vendor_id: int, obligation_id: int, organization_id: int
) -> VendorSlaObligation:
    ob = (
        db.query(VendorSlaObligation)
        .filter(
            VendorSlaObligation.id == obligation_id,
            VendorSlaObligation.vendor_id == vendor_id,
            VendorSlaObligation.organization_id == organization_id,
        )
        .first()
    )
    if not ob:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SLA obligation with ID {obligation_id} not found.",
        )
    return ob


def _get_sla_breach_or_404(
    db: Session, vendor_id: int, breach_id: int, organization_id: int
) -> VendorSlaBreach:
    breach = (
        db.query(VendorSlaBreach)
        .filter(
            VendorSlaBreach.id == breach_id,
            VendorSlaBreach.vendor_id == vendor_id,
            VendorSlaBreach.organization_id == organization_id,
        )
        .first()
    )
    if not breach:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"SLA breach with ID {breach_id} not found.",
        )
    return breach


@router.get("/{id}/sla-obligations", response_model=List[VendorSlaObligationRead])
def list_vendor_sla_obligations(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_READ)),
):
    vendor = _get_vendor_or_404(db, id, current_user.organization_id)
    return (
        db.query(VendorSlaObligation)
        .filter(
            VendorSlaObligation.vendor_id == vendor.id,
            VendorSlaObligation.organization_id == current_user.organization_id,
        )
        .order_by(desc(VendorSlaObligation.created_at))
        .all()
    )


@router.post(
    "/{id}/sla-obligations",
    response_model=VendorSlaObligationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_vendor_sla_obligation(
    id: int,
    payload: VendorSlaObligationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_MANAGE)),
):
    vendor = _get_vendor_or_404(db, id, current_user.organization_id)
    try:
        ob = TPRMService.create_sla_obligation(
            db=db, vendor=vendor, payload=payload, creator_id=current_user.id
        )
    except Exception as e:
        _raise_http_for_tprm_error(e)

    db.commit()
    db.refresh(ob)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        action="VENDOR_SLA_OBLIGATION_CREATED",
        resource_type="vendor_sla_obligation",
        resource_id=str(ob.id),
        actor_email=current_user.email,
        actor_id=current_user.id,
        details={
            "vendor_id": vendor.id,
            "obligation_code": ob.obligation_code,
            "metric_type": ob.metric_type.value,
        },
    )
    return ob


@router.patch(
    "/{id}/sla-obligations/{obligation_id}",
    response_model=VendorSlaObligationRead,
)
def update_vendor_sla_obligation(
    id: int,
    obligation_id: int,
    payload: VendorSlaObligationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_MANAGE)),
):
    _get_vendor_or_404(db, id, current_user.organization_id)
    ob = _get_sla_obligation_or_404(db, id, obligation_id, current_user.organization_id)
    try:
        updated = TPRMService.update_sla_obligation(
            db=db, obligation=ob, payload=payload
        )
    except Exception as e:
        _raise_http_for_tprm_error(e)

    db.commit()
    db.refresh(updated)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        action="VENDOR_SLA_OBLIGATION_UPDATED",
        resource_type="vendor_sla_obligation",
        resource_id=str(updated.id),
        actor_email=current_user.email,
        actor_id=current_user.id,
        details={"obligation_code": updated.obligation_code},
    )
    return updated


@router.get("/{id}/sla-breaches", response_model=List[VendorSlaBreachRead])
def list_vendor_sla_breaches(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_READ)),
):
    vendor = _get_vendor_or_404(db, id, current_user.organization_id)
    return (
        db.query(VendorSlaBreach)
        .filter(
            VendorSlaBreach.vendor_id == vendor.id,
            VendorSlaBreach.organization_id == current_user.organization_id,
        )
        .order_by(desc(VendorSlaBreach.occurred_at))
        .all()
    )


@router.post(
    "/{id}/sla-breaches",
    response_model=VendorSlaBreachRead,
    status_code=status.HTTP_201_CREATED,
)
def record_vendor_sla_breach(
    id: int,
    payload: VendorSlaBreachCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_ASSESS)),
):
    vendor = _get_vendor_or_404(db, id, current_user.organization_id)
    try:
        breach = TPRMService.record_sla_breach(
            db=db, vendor=vendor, payload=payload, reporter_id=current_user.id
        )
    except Exception as e:
        _raise_http_for_tprm_error(e)

    db.commit()
    db.refresh(breach)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        action="VENDOR_SLA_BREACH_RECORDED",
        resource_type="vendor_sla_breach",
        resource_id=str(breach.id),
        actor_email=current_user.email,
        actor_id=current_user.id,
        details={
            "vendor_id": vendor.id,
            "breach_code": breach.breach_code,
            "severity": breach.severity.value,
            "observed_value": breach.observed_value,
        },
    )
    return breach


@router.post(
    "/{id}/sla-breaches/{breach_id}/escalate",
    response_model=VendorSlaBreachRead,
)
def escalate_vendor_sla_breach(
    id: int,
    breach_id: int,
    payload: VendorSlaBreachEscalateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_ASSESS)),
):
    _get_vendor_or_404(db, id, current_user.organization_id)
    breach = _get_sla_breach_or_404(db, id, breach_id, current_user.organization_id)
    try:
        escalated = TPRMService.escalate_sla_breach(
            db=db, breach=breach, payload=payload, actor_id=current_user.id
        )
    except Exception as e:
        _raise_http_for_tprm_error(e)

    db.commit()
    db.refresh(escalated)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        action="VENDOR_SLA_BREACH_ESCALATED",
        resource_type="vendor_sla_breach",
        resource_id=str(escalated.id),
        actor_email=current_user.email,
        actor_id=current_user.id,
        details={
            "breach_code": escalated.breach_code,
            "linked_finding_id": escalated.linked_finding_id,
            "linked_remediation_plan_id": escalated.linked_remediation_plan_id,
            "linked_risk_id": escalated.linked_risk_id,
        },
    )
    return escalated


@router.post(
    "/{id}/sla-breaches/{breach_id}/resolve",
    response_model=VendorSlaBreachRead,
)
def resolve_vendor_sla_breach(
    id: int,
    breach_id: int,
    payload: VendorSlaBreachResolveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_MANAGE)),
):
    _get_vendor_or_404(db, id, current_user.organization_id)
    breach = _get_sla_breach_or_404(db, id, breach_id, current_user.organization_id)
    try:
        resolved = TPRMService.resolve_sla_breach(
            db=db, breach=breach, payload=payload, resolver_id=current_user.id
        )
    except Exception as e:
        _raise_http_for_tprm_error(e)

    db.commit()
    db.refresh(resolved)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        action="VENDOR_SLA_BREACH_RESOLVED",
        resource_type="vendor_sla_breach",
        resource_id=str(resolved.id),
        actor_email=current_user.email,
        actor_id=current_user.id,
        details={
            "breach_code": resolved.breach_code,
            "status": resolved.status.value,
        },
    )
    return resolved


@router.post(
    "/{id}/sla-breaches/{breach_id}/waive",
    response_model=VendorSlaBreachRead,
)
def waive_vendor_sla_breach(
    id: int,
    breach_id: int,
    payload: VendorSlaBreachWaiveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_APPROVE)),
):
    _get_vendor_or_404(db, id, current_user.organization_id)
    breach = _get_sla_breach_or_404(db, id, breach_id, current_user.organization_id)
    try:
        waived = TPRMService.waive_sla_breach(
            db=db,
            breach=breach,
            payload=payload,
            actor_id=current_user.id,
        )
    except Exception as e:
        _raise_http_for_tprm_error(e)

    db.commit()
    db.refresh(waived)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        action="VENDOR_SLA_BREACH_WAIVED",
        resource_type="vendor_sla_breach",
        resource_id=str(waived.id),
        actor_email=current_user.email,
        actor_id=current_user.id,
        details={
            "breach_code": waived.breach_code,
            "linked_exception_id": waived.linked_exception_id,
        },
    )
    return waived


@router.post(
    "/{id}/sla-breaches/{breach_id}/reopen",
    response_model=VendorSlaBreachRead,
)
def reopen_vendor_sla_breach(
    id: int,
    breach_id: int,
    payload: Optional[VendorSlaBreachReopenRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_APPROVE)),
):
    _get_vendor_or_404(db, id, current_user.organization_id)
    breach = _get_sla_breach_or_404(db, id, breach_id, current_user.organization_id)
    try:
        reopened = TPRMService.reopen_sla_breach(
            db=db,
            breach=breach,
            actor_id=current_user.id,
            reason=payload.reason if payload else None,
        )
    except Exception as e:
        _raise_http_for_tprm_error(e)

    db.commit()
    db.refresh(reopened)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        action="VENDOR_SLA_BREACH_REOPENED",
        resource_type="vendor_sla_breach",
        resource_id=str(reopened.id),
        actor_email=current_user.email,
        actor_id=current_user.id,
        details={"breach_code": reopened.breach_code},
    )
    return reopened


@router.post(
    "/{id}/sla-breaches/{breach_id}/verify-close",
    response_model=VendorSlaBreachRead,
)
def verify_close_vendor_sla_breach(
    id: int,
    breach_id: int,
    payload: Optional[VendorSlaBreachVerifyCloseRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_APPROVE)),
):
    _get_vendor_or_404(db, id, current_user.organization_id)
    breach = _get_sla_breach_or_404(db, id, breach_id, current_user.organization_id)
    try:
        closed = TPRMService.verify_close_sla_breach(
            db=db,
            breach=breach,
            verifier_id=current_user.id,
            resolution_notes=payload.resolution_notes if payload else None,
            evidence_id=payload.evidence_id if payload else None,
        )
    except Exception as e:
        _raise_http_for_tprm_error(e)

    db.commit()
    db.refresh(closed)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        action="VENDOR_SLA_BREACH_VERIFIED_CLOSED",
        resource_type="vendor_sla_breach",
        resource_id=str(closed.id),
        actor_email=current_user.email,
        actor_id=current_user.id,
        details={"breach_code": closed.breach_code},
    )
    return closed


# ─── 10. BATCH 6: CLOSED-LOOP ASSESSMENT ITEM ESCALATION ────────────────────

@router.post(
    "/assessments/{assessment_id}/items/{item_id}/escalate",
    response_model=VendorAssessmentItemRead,
)
def escalate_vendor_assessment_item(
    assessment_id: int,
    item_id: int,
    payload: VendorAssessmentItemEscalateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_ASSESS)),
):
    assessment = (
        db.query(VendorAssessment)
        .filter(
            VendorAssessment.id == assessment_id,
            VendorAssessment.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment with ID {assessment_id} not found.",
        )

    item = (
        db.query(VendorAssessmentItem)
        .filter(
            VendorAssessmentItem.id == item_id,
            VendorAssessmentItem.assessment_id == assessment.id,
            VendorAssessmentItem.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment item with ID {item_id} not found.",
        )

    try:
        escalated = TPRMService.escalate_assessment_item(
            db=db,
            assessment=assessment,
            item=item,
            payload=payload,
            actor_id=current_user.id,
        )
    except Exception as e:
        _raise_http_for_tprm_error(e)

    db.commit()
    db.refresh(escalated)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        action="VENDOR_ASSESSMENT_ITEM_ESCALATED",
        resource_type="vendor_assessment_item",
        resource_id=str(escalated.id),
        actor_email=current_user.email,
        actor_id=current_user.id,
        details={
            "assessment_id": assessment.id,
            "question_key": escalated.question_key,
            "linked_finding_id": escalated.linked_finding_id,
            "linked_remediation_plan_id": escalated.linked_remediation_plan_id,
            "linked_risk_id": escalated.linked_risk_id,
        },
    )
    return escalated


# ─── 11. BATCH 6: GOVERNED VENDOR OFFBOARDING ───────────────────────────────

def _get_offboarding_record_or_404(
    db: Session, vendor_id: int, record_id: int, organization_id: int
) -> VendorOffboardingRecord:
    record = (
        db.query(VendorOffboardingRecord)
        .filter(
            VendorOffboardingRecord.id == record_id,
            VendorOffboardingRecord.vendor_id == vendor_id,
            VendorOffboardingRecord.organization_id == organization_id,
        )
        .first()
    )
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Offboarding record with ID {record_id} not found.",
        )
    return record


@router.get("/{id}/offboarding", response_model=List[VendorOffboardingRecordRead])
def list_vendor_offboarding_records(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_READ)),
):
    vendor = _get_vendor_or_404(db, id, current_user.organization_id)
    return (
        db.query(VendorOffboardingRecord)
        .filter(
            VendorOffboardingRecord.vendor_id == vendor.id,
            VendorOffboardingRecord.organization_id == current_user.organization_id,
        )
        .order_by(desc(VendorOffboardingRecord.initiated_at))
        .all()
    )


@router.post(
    "/{id}/offboarding",
    response_model=VendorOffboardingRecordRead,
    status_code=status.HTTP_201_CREATED,
)
def initiate_vendor_offboarding(
    id: int,
    payload: VendorOffboardingInitiateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_ASSESS)),
):
    vendor = _get_vendor_or_404(db, id, current_user.organization_id)
    try:
        record = TPRMService.initiate_offboarding(
            db=db, vendor=vendor, payload=payload, initiator_id=current_user.id
        )
    except Exception as e:
        _raise_http_for_tprm_error(e)

    db.commit()
    db.refresh(record)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        action="VENDOR_OFFBOARDING_INITIATED",
        resource_type="vendor_offboarding_record",
        resource_id=str(record.id),
        actor_email=current_user.email,
        actor_id=current_user.id,
        details={
            "vendor_id": vendor.id,
            "offboarding_code": record.offboarding_code,
            "target_vendor_status": record.target_vendor_status.value,
        },
    )
    return record


@router.post(
    "/{id}/offboarding/{record_id}/items/{item_id}/attest",
    response_model=VendorOffboardingItemRead,
)
@router.post(
    "/{id}/offboarding/{record_id}/items/{item_id}/complete",
    response_model=VendorOffboardingItemRead,
)
@router.patch(
    "/{id}/offboarding/{record_id}/items/{item_id}",
    response_model=VendorOffboardingItemRead,
)
def attest_vendor_offboarding_item(
    id: int,
    record_id: int,
    item_id: int,
    payload: VendorOffboardingItemAttestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_ASSESS)),
):
    _get_vendor_or_404(db, id, current_user.organization_id)
    record = _get_offboarding_record_or_404(
        db, id, record_id, current_user.organization_id
    )
    item = (
        db.query(VendorOffboardingItem)
        .filter(
            VendorOffboardingItem.id == item_id,
            VendorOffboardingItem.offboarding_record_id == record.id,
            VendorOffboardingItem.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Offboarding item with ID {item_id} not found.",
        )

    try:
        updated_item = TPRMService.attest_offboarding_item(
            db=db,
            record=record,
            item=item,
            payload=payload,
            actor_id=current_user.id,
        )
    except Exception as e:
        _raise_http_for_tprm_error(e)

    db.commit()
    db.refresh(updated_item)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        action="VENDOR_OFFBOARDING_ITEM_ATTESTED",
        resource_type="vendor_offboarding_item",
        resource_id=str(updated_item.id),
        actor_email=current_user.email,
        actor_id=current_user.id,
        details={
            "offboarding_record_id": record.id,
            "step_key": updated_item.step_key,
            "evidence_id": updated_item.evidence_id,
        },
    )
    return updated_item


@router.post(
    "/{id}/offboarding/{record_id}/items/{item_id}/waive",
    response_model=VendorOffboardingItemRead,
)
def waive_vendor_offboarding_item(
    id: int,
    record_id: int,
    item_id: int,
    payload: VendorOffboardingItemWaiveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_APPROVE)),
):
    _get_vendor_or_404(db, id, current_user.organization_id)
    record = _get_offboarding_record_or_404(
        db, id, record_id, current_user.organization_id
    )
    item = (
        db.query(VendorOffboardingItem)
        .filter(
            VendorOffboardingItem.id == item_id,
            VendorOffboardingItem.offboarding_record_id == record.id,
            VendorOffboardingItem.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Offboarding item with ID {item_id} not found.",
        )

    try:
        waived_item = TPRMService.waive_offboarding_item(
            db=db,
            record=record,
            item=item,
            payload=payload,
            actor_id=current_user.id,
        )
    except Exception as e:
        _raise_http_for_tprm_error(e)

    db.commit()
    db.refresh(waived_item)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        action="VENDOR_OFFBOARDING_ITEM_WAIVED",
        resource_type="vendor_offboarding_item",
        resource_id=str(waived_item.id),
        actor_email=current_user.email,
        actor_id=current_user.id,
        details={
            "offboarding_record_id": record.id,
            "step_key": waived_item.step_key,
            "linked_exception_id": waived_item.linked_exception_id,
        },
    )
    return waived_item


@router.post(
    "/{id}/offboarding/{record_id}/submit",
    response_model=VendorOffboardingRecordRead,
)
@router.post(
    "/{id}/offboarding/{record_id}/submit-signoff",
    response_model=VendorOffboardingRecordRead,
)
def submit_vendor_offboarding(
    id: int,
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_ASSESS)),
):
    _get_vendor_or_404(db, id, current_user.organization_id)
    record = _get_offboarding_record_or_404(
        db, id, record_id, current_user.organization_id
    )
    try:
        submitted = TPRMService.submit_offboarding(
            db=db,
            record=record,
            submitter_id=current_user.id,
        )
    except Exception as e:
        _raise_http_for_tprm_error(e)

    db.commit()
    db.refresh(submitted)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        action="VENDOR_OFFBOARDING_SUBMITTED",
        resource_type="vendor_offboarding_record",
        resource_id=str(submitted.id),
        actor_email=current_user.email,
        actor_id=current_user.id,
        details={
            "vendor_id": id,
            "offboarding_code": submitted.offboarding_code,
        },
    )
    return submitted


@router.post(
    "/{id}/offboarding/{record_id}/verify-close",
    response_model=VendorOffboardingRecordRead,
)
@router.post(
    "/{id}/offboarding/{record_id}/approve",
    response_model=VendorOffboardingRecordRead,
)
def verify_and_close_vendor_offboarding(
    id: int,
    record_id: int,
    payload: VendorOffboardingCompleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_APPROVE)),
):
    _get_vendor_or_404(db, id, current_user.organization_id)
    record = _get_offboarding_record_or_404(
        db, id, record_id, current_user.organization_id
    )
    try:
        completed = TPRMService.verify_and_complete_offboarding(
            db=db,
            record=record,
            payload=payload,
            verifier_id=current_user.id,
        )
    except Exception as e:
        _raise_http_for_tprm_error(e)

    db.commit()
    db.refresh(completed)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        action="VENDOR_OFFBOARDING_COMPLETED",
        resource_type="vendor_offboarding_record",
        resource_id=str(completed.id),
        actor_email=current_user.email,
        actor_id=current_user.id,
        details={
            "vendor_id": id,
            "offboarding_code": completed.offboarding_code,
            "final_vendor_status": completed.vendor.vendor_status.value,
        },
    )
    return completed


@router.post(
    "/{id}/offboarding/{record_id}/reject",
    response_model=VendorOffboardingRecordRead,
)
def reject_vendor_offboarding(
    id: int,
    record_id: int,
    payload: VendorOffboardingCancelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_APPROVE)),
):
    _get_vendor_or_404(db, id, current_user.organization_id)
    record = _get_offboarding_record_or_404(
        db, id, record_id, current_user.organization_id
    )
    try:
        rejected = TPRMService.reject_offboarding(
            db=db,
            record=record,
            reviewer_id=current_user.id,
            reason=payload.cancellation_reason,
        )
    except Exception as e:
        _raise_http_for_tprm_error(e)

    db.commit()
    db.refresh(rejected)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        action="VENDOR_OFFBOARDING_REJECTED",
        resource_type="vendor_offboarding_record",
        resource_id=str(rejected.id),
        actor_email=current_user.email,
        actor_id=current_user.id,
        details={
            "offboarding_code": rejected.offboarding_code,
            "reason": payload.cancellation_reason,
        },
    )
    return rejected


@router.post(
    "/{id}/offboarding/{record_id}/cancel",
    response_model=VendorOffboardingRecordRead,
)
def cancel_vendor_offboarding(
    id: int,
    record_id: int,
    payload: VendorOffboardingCancelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.VENDOR_ASSESS)),
):
    _get_vendor_or_404(db, id, current_user.organization_id)
    record = _get_offboarding_record_or_404(
        db, id, record_id, current_user.organization_id
    )
    try:
        cancelled = TPRMService.cancel_offboarding(
            db=db,
            record=record,
            payload=payload,
            actor_id=current_user.id,
        )
    except Exception as e:
        _raise_http_for_tprm_error(e)

    db.commit()
    db.refresh(cancelled)
    AuditService.log(
        db=db,
        organization_id=current_user.organization_id,
        action="VENDOR_OFFBOARDING_CANCELLED",
        resource_type="vendor_offboarding_record",
        resource_id=str(cancelled.id),
        actor_email=current_user.email,
        actor_id=current_user.id,
        details={
            "offboarding_code": cancelled.offboarding_code,
            "cancellation_reason": cancelled.cancellation_reason,
        },
    )
    return cancelled

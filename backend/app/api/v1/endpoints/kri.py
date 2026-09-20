from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.permissions import Permission, has_permission
from app.models.kri import BreachStatusEnum, KriThreshold
from app.models.user import User
from app.schemas.kri import (
    KeyRiskIndicatorCreate,
    KeyRiskIndicatorResponse,
    KeyRiskIndicatorUpdate,
    KriBreachAcknowledgeRequest,
    KriBreachCloseRequest,
    KriBreachEscalateFindingRequest,
    KriBreachResponse,
    KriObservationCreate,
    KriObservationResponse,
    KriRiskLinkCreate,
    KriRiskLinkResponse,
    KriTelemetryOverviewResponse,
    KriThresholdCreate,
    KriThresholdResponse,
    RiskAppetiteStatementCreate,
    RiskAppetiteStatementResponse,
)
from app.services.kri_service import KriService

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# Helper: Format KRI with active threshold
# ─────────────────────────────────────────────────────────────────────────────

def _kri_to_response(db: Session, kri) -> KeyRiskIndicatorResponse:
    active_thresh = (
        db.query(KriThreshold)
        .filter(
            KriThreshold.kri_id == kri.id,
            KriThreshold.is_active == True,  # noqa: E712
        )
        .first()
    )
    thresh_resp = KriThresholdResponse.model_validate(active_thresh) if active_thresh else None
    resp = KeyRiskIndicatorResponse.model_validate(kri)
    resp.active_threshold = thresh_resp
    return resp


# ─────────────────────────────────────────────────────────────────────────────
# 1. Risk Appetite Statements Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/appetite-statements", response_model=List[RiskAppetiteStatementResponse])
def list_appetite_statements(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List risk appetite statements for the current tenant."""
    if not has_permission(current_user.role, Permission.APPETITE_READ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions."
        )
    return KriService.list_appetite_statements(db, current_user.organization_id)


@router.post(
    "/appetite-statements",
    response_model=RiskAppetiteStatementResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_appetite_statement(
    data: RiskAppetiteStatementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a draft organizational risk appetite statement."""
    if not has_permission(current_user.role, Permission.APPETITE_MANAGE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions."
        )
    return KriService.create_appetite_statement(
        db, current_user.organization_id, data, current_user.id
    )


@router.get("/appetite-statements/{statement_id}", response_model=RiskAppetiteStatementResponse)
def get_appetite_statement(
    statement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get single risk appetite statement details."""
    if not has_permission(current_user.role, Permission.APPETITE_READ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions."
        )
    return KriService.get_appetite_statement(db, current_user.organization_id, statement_id)


@router.post(
    "/appetite-statements/{statement_id}/approve",
    response_model=RiskAppetiteStatementResponse,
)
def approve_appetite_statement(
    statement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Approve a draft risk appetite statement with Four-Eyes SoD check."""
    if not has_permission(current_user.role, Permission.APPETITE_APPROVE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions."
        )
    return KriService.approve_appetite_statement(
        db, current_user.organization_id, statement_id, current_user.id
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. Key Risk Indicators Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/indicators", response_model=List[KeyRiskIndicatorResponse])
def list_kris(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all registered Key Risk Indicators for the tenant."""
    if not has_permission(current_user.role, Permission.KRI_READ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions."
        )
    kris = KriService.list_kris(db, current_user.organization_id)
    return [_kri_to_response(db, k) for k in kris]


@router.post(
    "/indicators",
    response_model=KeyRiskIndicatorResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_kri(
    data: KeyRiskIndicatorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Register a new Key Risk Indicator with optional initial threshold."""
    if not has_permission(current_user.role, Permission.KRI_MANAGE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions."
        )
    kri = KriService.create_kri(db, current_user.organization_id, data, current_user.id)
    return _kri_to_response(db, kri)


@router.get("/indicators/{kri_id}", response_model=KeyRiskIndicatorResponse)
def get_kri(
    kri_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch KRI details, current operational status, and active threshold."""
    if not has_permission(current_user.role, Permission.KRI_READ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions."
        )
    kri = KriService.get_kri(db, current_user.organization_id, kri_id)
    return _kri_to_response(db, kri)


@router.put("/indicators/{kri_id}", response_model=KeyRiskIndicatorResponse)
def update_kri(
    kri_id: int,
    data: KeyRiskIndicatorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update KRI registry metadata."""
    if not has_permission(current_user.role, Permission.KRI_MANAGE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions."
        )
    kri = KriService.update_kri(db, current_user.organization_id, kri_id, data, current_user.id)
    return _kri_to_response(db, kri)


@router.post(
    "/indicators/{kri_id}/thresholds",
    response_model=KriThresholdResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_threshold(
    kri_id: int,
    data: KriThresholdCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Version and activate a new threshold for a KRI."""
    if not has_permission(current_user.role, Permission.KRI_MANAGE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions."
        )
    kri = KriService.get_kri(db, current_user.organization_id, kri_id)
    threshold = KriService.create_threshold(
        db, current_user.organization_id, kri, data, current_user.id
    )
    return KriThresholdResponse.model_validate(threshold)


# ─────────────────────────────────────────────────────────────────────────────
# 3. KRI Observations Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/indicators/{kri_id}/observations",
    response_model=KriObservationResponse,
    status_code=status.HTTP_201_CREATED,
)
def ingest_observation(
    kri_id: int,
    data: KriObservationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Ingest an immutable time-series observation and evaluate against active threshold."""
    if not has_permission(current_user.role, Permission.KRI_OBSERVE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions."
        )
    obs = KriService.ingest_observation(
        db, current_user.organization_id, kri_id, data, current_user.id
    )
    resp = KriObservationResponse.model_validate(obs)
    resp.evaluation_status = getattr(obs, "evaluation_status", None)
    resp.breach_id = getattr(obs, "breach_id", None)
    return resp


@router.get(
    "/indicators/{kri_id}/observations",
    response_model=List[KriObservationResponse],
)
def list_observations(
    kri_id: int,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Query historical immutable observations for a KRI."""
    if not has_permission(current_user.role, Permission.KRI_READ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions."
        )
    return KriService.list_observations(db, current_user.organization_id, kri_id, limit)


@router.put("/indicators/{kri_id}/observations/{observation_id}")
@router.patch("/indicators/{kri_id}/observations/{observation_id}")
def block_observation_mutation():
    """In-place mutation of observations is strictly prohibited (append-only ledger)."""
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail="Observations are append-only immutable records. In-place modification is strictly prohibited.",
    )


@router.delete("/indicators/{kri_id}/observations/{observation_id}")
def block_observation_deletion():
    """Deletion of historical observations is strictly prohibited (append-only ledger)."""
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail="Observations are append-only immutable records. Deletion is strictly prohibited.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 4. KRI Risk Linkage Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/indicators/{kri_id}/link-risk",
    response_model=KriRiskLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
def link_risk(
    kri_id: int,
    data: KriRiskLinkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Link a KRI to a registered Phase 5 operational Risk."""
    if not has_permission(current_user.role, Permission.KRI_MANAGE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions."
        )
    link = KriService.link_risk(db, current_user.organization_id, kri_id, data, current_user.id)
    resp = KriRiskLinkResponse.model_validate(link)
    resp.risk_title = link.risk.title if link.risk else None
    return resp


@router.delete(
    "/indicators/{kri_id}/link-risk/{risk_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def unlink_risk(
    kri_id: int,
    risk_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Unlink a KRI from an operational Risk."""
    if not has_permission(current_user.role, Permission.KRI_MANAGE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions."
        )
    KriService.unlink_risk(db, current_user.organization_id, kri_id, risk_id, current_user.id)


# ─────────────────────────────────────────────────────────────────────────────
# 5. KRI Breach Governance Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/breaches", response_model=List[KriBreachResponse])
def list_breaches(
    kri_id: Optional[int] = Query(None),
    status: Optional[BreachStatusEnum] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List KRI breach records with optional status and KRI filtering."""
    if not has_permission(current_user.role, Permission.KRI_READ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions."
        )
    return KriService.list_breaches(db, current_user.organization_id, kri_id, status)


@router.get("/breaches/{breach_id}", response_model=KriBreachResponse)
def get_breach(
    breach_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch single breach record details."""
    if not has_permission(current_user.role, Permission.KRI_READ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions."
        )
    return KriService.get_breach(db, current_user.organization_id, breach_id)


@router.post("/breaches/{breach_id}/acknowledge", response_model=KriBreachResponse)
def acknowledge_breach(
    breach_id: int,
    data: KriBreachAcknowledgeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Acknowledge an active KRI breach."""
    if not has_permission(current_user.role, Permission.KRI_BREACH_ACTION):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions."
        )
    return KriService.acknowledge_breach(
        db, current_user.organization_id, breach_id, data, current_user.id
    )


@router.post("/breaches/{breach_id}/escalate-finding", response_model=KriBreachResponse)
def escalate_breach_to_finding(
    breach_id: int,
    data: KriBreachEscalateFindingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Escalate a control-related KRI breach to an authoritative Phase 4 Finding."""
    if not has_permission(current_user.role, Permission.KRI_BREACH_ACTION):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions."
        )
    return KriService.escalate_breach_to_finding(
        db, current_user.organization_id, breach_id, data, current_user.id
    )


@router.post("/breaches/{breach_id}/close", response_model=KriBreachResponse)
def close_breach(
    breach_id: int,
    data: KriBreachCloseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Execute Four-Eyes governed closure on a KRI breach."""
    if not has_permission(current_user.role, Permission.KRI_BREACH_CLOSE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions."
        )
    return KriService.close_breach(
        db, current_user.organization_id, breach_id, data, current_user.id
    )


# ─────────────────────────────────────────────────────────────────────────────
# 6. Telemetry & Executive Overview Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/telemetry/overview", response_model=KriTelemetryOverviewResponse)
def get_telemetry_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get high-level KRI posture, active breaches, and appetite compliance overview."""
    if not has_permission(current_user.role, Permission.KRI_READ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions."
        )
    return KriService.get_telemetry_overview(db, current_user.organization_id)

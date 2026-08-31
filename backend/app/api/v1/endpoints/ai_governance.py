from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.core.permissions import Permission
from app.models.ai_governance import (
    AIApprovalStatusEnum,
    AIAutonomyLevelEnum,
    AIDataSensitivityEnum,
    AIDeploymentApproval,
    AIHostingTypeEnum,
    AILifecycleStateEnum,
    AIModelCard,
    AIRegulatoryTierEnum,
    AISystem,
    AISystemTypeEnum,
)
from app.models.user import User
from app.schemas.ai_governance import (
    AIDeploymentApprovalCreate,
    AIDeploymentApprovalResponse,
    AIDeploymentApprovalReviewRequest,
    AIIndexCalculateRequest,
    AIIndexCalculateResponse,
    AIModelCardCreate,
    AIModelCardResponse,
    AIPostureSummaryResponse,
    AISystemCreate,
    AISystemResponse,
    AISystemStatusUpdate,
    AISystemUpdate,
)
from app.services.ai_governance_service import AIGovernanceService

router = APIRouter()


# ─── 1. AI SYSTEMS CATALOG ENDPOINTS ─────────────────────────────────────────

@router.post("/systems", response_model=AISystemResponse, status_code=status.HTTP_201_CREATED)
def create_ai_system(
    payload: AISystemCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.AI_MANAGE)),
):
    """Register/Ingest a new AI system into the governance registry."""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return AIGovernanceService.create_ai_system(
        db=db,
        organization_id=current_user.organization_id,
        data=payload,
        current_user=current_user,
        ip_address=ip_address,
        user_agent=user_agent,
    )


@router.get("/systems", response_model=List[AISystemResponse])
def list_ai_systems(
    regulatory_tier: Optional[AIRegulatoryTierEnum] = None,
    lifecycle_state: Optional[AILifecycleStateEnum] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.AI_READ)),
):
    """List tenant-scoped AI systems with optional tier, lifecycle, and text filtering."""
    return AIGovernanceService.list_ai_systems(
        db=db,
        organization_id=current_user.organization_id,
        regulatory_tier=regulatory_tier,
        lifecycle_state=lifecycle_state,
        search=search,
        skip=skip,
        limit=limit,
    )


@router.get("/systems/summary/posture", response_model=AIPostureSummaryResponse)
def get_ai_posture_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.AI_READ)),
):
    """Calculate executive algorithmic risk posture summary for tenant organization."""
    return AIGovernanceService.get_posture_summary(
        db=db,
        organization_id=current_user.organization_id,
    )


@router.post("/systems/calculate-index", response_model=AIIndexCalculateResponse)
def calculate_index_preview(
    payload: AIIndexCalculateRequest,
    current_user: User = Depends(require_permission(Permission.AI_READ)),
):
    """Preview server-authoritative Algorithmic Risk Index calculation without persistence."""
    base_risk = AIGovernanceService.BASE_RISK_MAP.get(payload.regulatory_tier, 25.0)
    autonomy_mult = AIGovernanceService.AUTONOMY_MULTIPLIER_MAP.get(payload.autonomy_level, 1.00)
    norm_tier = str(payload.process_tier).upper() if payload.process_tier else "TIER_4"
    process_mult = AIGovernanceService.PROCESS_TIER_MULTIPLIER_MAP.get(norm_tier, 1.00)

    data_addon = AIGovernanceService.DATA_SENSITIVITY_ADDON_MAP.get(payload.data_sensitivity, 2.0)
    hallucination_penalty = max(0.0, min(100.0, float(payload.hallucination_rate_percent))) * 0.20
    injection_penalty = max(0.0, min(100.0, 100.0 - float(payload.prompt_injection_resistance_score))) * 0.15
    safety_penalty = round(hallucination_penalty + injection_penalty + data_addon, 2)

    ari = AIGovernanceService.calculate_algorithmic_risk_index(
        regulatory_tier=payload.regulatory_tier,
        autonomy_level=payload.autonomy_level,
        data_sensitivity=payload.data_sensitivity,
        process_tier=payload.process_tier,
        hallucination_rate_percent=payload.hallucination_rate_percent,
        prompt_injection_resistance_score=payload.prompt_injection_resistance_score,
    )
    return AIIndexCalculateResponse(
        base_risk=base_risk,
        autonomy_multiplier=autonomy_mult,
        process_tier_multiplier=process_mult,
        safety_penalty=safety_penalty,
        algorithmic_risk_index=ari,
    )


@router.get("/systems/{system_id}", response_model=AISystemResponse)
def get_ai_system(
    system_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.AI_READ)),
):
    """Retrieve a single AI system with all attached model cards and approvals."""
    return AIGovernanceService.get_ai_system(
        db=db,
        organization_id=current_user.organization_id,
        system_id=system_id,
    )


@router.put("/systems/{system_id}", response_model=AISystemResponse)
def update_ai_system(
    system_id: int,
    payload: AISystemUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.AI_MANAGE)),
):
    """Update AI system metadata and recalculate algorithmic risk metrics."""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return AIGovernanceService.update_ai_system(
        db=db,
        organization_id=current_user.organization_id,
        system_id=system_id,
        data=payload,
        current_user=current_user,
        ip_address=ip_address,
        user_agent=user_agent,
    )


@router.delete("/systems/{system_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ai_system(
    system_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.AI_MANAGE)),
):
    """Delete a non-production AI system."""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    AIGovernanceService.delete_ai_system(
        db=db,
        organization_id=current_user.organization_id,
        system_id=system_id,
        current_user=current_user,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return None


@router.post("/systems/{system_id}/lifecycle", response_model=AISystemResponse)
def update_system_lifecycle_state(
    system_id: int,
    payload: AISystemStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.AI_MANAGE)),
):
    """Execute a lifecycle state transition enforcing EU AI Act Article 5 and Four-Eyes staging/production deployment gates."""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return AIGovernanceService.update_lifecycle_state(
        db=db,
        organization_id=current_user.organization_id,
        system_id=system_id,
        target_state=payload.lifecycle_state,
        notes=payload.notes,
        current_user=current_user,
        ip_address=ip_address,
        user_agent=user_agent,
    )


# ─── 2. MODEL CARD GOVERNANCE ENDPOINTS ──────────────────────────────────────

@router.post("/systems/{system_id}/model-cards", response_model=AIModelCardResponse, status_code=status.HTTP_201_CREATED)
def create_model_card(
    system_id: int,
    payload: AIModelCardCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.AI_ASSESS)),
):
    """Publish a model card version with safety and hallucination telemetry, triggering ARI update."""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return AIGovernanceService.create_model_card(
        db=db,
        organization_id=current_user.organization_id,
        system_id=system_id,
        data=payload,
        current_user=current_user,
        ip_address=ip_address,
        user_agent=user_agent,
    )


@router.get("/systems/{system_id}/model-cards", response_model=List[AIModelCardResponse])
def list_model_cards(
    system_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.AI_READ)),
):
    """List all model cards attached to an AI system."""
    return AIGovernanceService.list_model_cards(
        db=db,
        organization_id=current_user.organization_id,
        system_id=system_id,
    )


@router.get("/model-cards/{card_id}", response_model=AIModelCardResponse)
def get_model_card(
    card_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.AI_READ)),
):
    """Retrieve a single model card enforcing tenant isolation."""
    return AIGovernanceService.get_model_card(
        db=db,
        organization_id=current_user.organization_id,
        card_id=card_id,
    )


# ─── 3. FOUR-EYES DEPLOYMENT APPROVAL ENDPOINTS ──────────────────────────────

@router.post("/systems/{system_id}/approvals", response_model=AIDeploymentApprovalResponse, status_code=status.HTTP_201_CREATED)
def request_deployment_approval(
    system_id: int,
    payload: AIDeploymentApprovalCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.AI_MANAGE)),
):
    """Submit a deployment approval request for STAGING or PRODUCTION environment."""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return AIGovernanceService.request_deployment_approval(
        db=db,
        organization_id=current_user.organization_id,
        system_id=system_id,
        data=payload,
        current_user=current_user,
        ip_address=ip_address,
        user_agent=user_agent,
    )


@router.get("/approvals", response_model=List[AIDeploymentApprovalResponse])
def list_deployment_approvals(
    system_id: Optional[int] = None,
    approval_status: Optional[AIApprovalStatusEnum] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.AI_READ)),
):
    """List tenant-scoped deployment approvals."""
    return AIGovernanceService.list_deployment_approvals(
        db=db,
        organization_id=current_user.organization_id,
        system_id=system_id,
        approval_status=approval_status,
    )


@router.get("/approvals/{approval_id}", response_model=AIDeploymentApprovalResponse)
def get_deployment_approval(
    approval_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.AI_READ)),
):
    """Retrieve a single deployment approval request."""
    return AIGovernanceService.get_deployment_approval(
        db=db,
        organization_id=current_user.organization_id,
        approval_id=approval_id,
    )


@router.post("/approvals/{approval_id}/review", response_model=AIDeploymentApprovalResponse)
def review_deployment_approval(
    approval_id: int,
    payload: AIDeploymentApprovalReviewRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.AI_APPROVE)),
):
    """Execute Four-Eyes deployment approval/rejection. Requester cannot review own request."""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return AIGovernanceService.review_deployment_approval(
        db=db,
        organization_id=current_user.organization_id,
        approval_id=approval_id,
        data=payload,
        current_user=current_user,
        ip_address=ip_address,
        user_agent=user_agent,
    )

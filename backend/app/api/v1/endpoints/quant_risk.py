from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.core.permissions import Permission
from app.models.quant_risk import (
    ScenarioStatusEnum,
    ThreatActorCategoryEnum,
)
from app.models.user import User
from app.schemas.quant_risk import (
    FinancialRiskAppetiteApproveRequest,
    FinancialRiskAppetiteCreate,
    FinancialRiskAppetiteRead,
    QuantOverviewResponse,
    QuantitativeRiskScenarioCreate,
    QuantitativeRiskScenarioRead,
    QuantitativeRiskScenarioUpdate,
    QuantitativeSimulationRequest,
    QuantitativeSimulationRunRead,
    RosiAnalysisCreate,
    RosiAnalysisRead,
)
from app.services.quantum_grc_service import QuantumGrcService

router = APIRouter()


# ─── 0. PORTFOLIO OVERVIEW & POSTURE ─────────────────────────────────────────

@router.get("/overview", response_model=QuantOverviewResponse)
def get_quant_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.QUANTRISK_READ)),
):
    """Retrieve tenant-wide quantitative risk posture, portfolio ALE/VaR, and appetite breach status."""
    return QuantumGrcService.get_portfolio_overview(db, current_user.organization_id)


# ─── 1. QUANTITATIVE RISK SCENARIOS ──────────────────────────────────────────

@router.post("/scenarios", response_model=QuantitativeRiskScenarioRead, status_code=status.HTTP_201_CREATED)
def create_scenario(
    payload: QuantitativeRiskScenarioCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.QUANTRISK_MANAGE)),
):
    """Create a new quantitative risk scenario with server-authoritative telemetry."""
    return QuantumGrcService.create_scenario(
        db, current_user.organization_id, current_user.id, payload
    )


@router.get("/scenarios", response_model=List[QuantitativeRiskScenarioRead])
def list_scenarios(
    status_filter: Optional[ScenarioStatusEnum] = Query(None, alias="status"),
    threat_category: Optional[ThreatActorCategoryEnum] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.QUANTRISK_READ)),
):
    """List tenant-scoped quantitative scenarios with optional filters."""
    return QuantumGrcService.list_scenarios(
        db=db,
        org_id=current_user.organization_id,
        status_filter=status_filter,
        threat_category=threat_category,
        search=search,
        skip=skip,
        limit=limit,
    )


@router.get("/scenarios/{scenario_id}", response_model=QuantitativeRiskScenarioRead)
def get_scenario(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.QUANTRISK_READ)),
):
    """Fetch single scenario enforcing tenant isolation."""
    return QuantumGrcService.get_scenario(db, current_user.organization_id, scenario_id)


@router.put("/scenarios/{scenario_id}", response_model=QuantitativeRiskScenarioRead)
def update_scenario(
    scenario_id: int,
    payload: QuantitativeRiskScenarioUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.QUANTRISK_MANAGE)),
):
    """Update scenario fields and recalculate server metrics (rejects frozen scenarios with 409)."""
    return QuantumGrcService.update_scenario(
        db, current_user.organization_id, current_user.id, scenario_id, payload
    )


@router.post("/scenarios/{scenario_id}/activate", response_model=QuantitativeRiskScenarioRead)
def activate_scenario(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.QUANTRISK_MANAGE)),
):
    """Activate a draft scenario."""
    return QuantumGrcService.activate_scenario(
        db, current_user.organization_id, current_user.id, scenario_id
    )


@router.post("/scenarios/{scenario_id}/freeze", response_model=QuantitativeRiskScenarioRead)
def freeze_scenario(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.QUANTRISK_MANAGE)),
):
    """Freeze a scenario baseline into an immutable record."""
    return QuantumGrcService.freeze_scenario(
        db, current_user.organization_id, current_user.id, scenario_id
    )


@router.post("/scenarios/{scenario_id}/archive", response_model=QuantitativeRiskScenarioRead)
def archive_scenario(
    scenario_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.QUANTRISK_MANAGE)),
):
    """Archive a scenario."""
    return QuantumGrcService.archive_scenario(
        db, current_user.organization_id, current_user.id, scenario_id
    )


# ─── 2. EMPIRICAL MONTE CARLO SIMULATION ─────────────────────────────────────

@router.post("/scenarios/{scenario_id}/simulate", response_model=QuantitativeSimulationRunRead, status_code=status.HTTP_201_CREATED)
def execute_simulation(
    scenario_id: int,
    request: QuantitativeSimulationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.QUANTRISK_EXECUTE)),
):
    """Execute empirical Monte Carlo simulation (100 to 50,000 trials) and record empirical VaR."""
    return QuantumGrcService.execute_simulation(
        db, current_user.organization_id, current_user.id, scenario_id, request
    )


@router.get("/scenarios/{scenario_id}/simulations", response_model=List[QuantitativeSimulationRunRead])
def list_scenario_simulations(
    scenario_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.QUANTRISK_READ)),
):
    """List historical simulation runs for a scenario."""
    return QuantumGrcService.list_simulations_for_scenario(
        db, current_user.organization_id, scenario_id, skip=skip, limit=limit
    )


@router.get("/simulations/{run_id}", response_model=QuantitativeSimulationRunRead)
def get_simulation(
    run_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.QUANTRISK_READ)),
):
    """Retrieve a specific historical simulation run."""
    return QuantumGrcService.get_simulation(db, current_user.organization_id, run_id)


# ─── 3. RETURN ON SECURITY INVESTMENT (ROSI) ─────────────────────────────────

@router.post("/scenarios/{scenario_id}/rosi", response_model=RosiAnalysisRead, status_code=status.HTTP_201_CREATED)
def calculate_rosi(
    scenario_id: int,
    payload: RosiAnalysisCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.QUANTRISK_EXECUTE)),
):
    """Calculate and record ROSI for a remediation plan."""
    return QuantumGrcService.calculate_and_record_rosi(
        db, current_user.organization_id, current_user.id, scenario_id, payload
    )


@router.get("/scenarios/{scenario_id}/rosi", response_model=List[RosiAnalysisRead])
def list_scenario_rosi(
    scenario_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.QUANTRISK_READ)),
):
    """List ROSI analyses for a scenario."""
    return QuantumGrcService.list_rosi_for_scenario(
        db, current_user.organization_id, scenario_id, skip=skip, limit=limit
    )


@router.get("/rosi/{analysis_id}", response_model=RosiAnalysisRead)
def get_rosi_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.QUANTRISK_READ)),
):
    """Retrieve a specific ROSI analysis."""
    return QuantumGrcService.get_rosi_analysis(db, current_user.organization_id, analysis_id)


# ─── 4. FINANCIAL RISK APPETITE & FOUR-EYES GOVERNANCE ───────────────────────

@router.post("/appetites", response_model=FinancialRiskAppetiteRead, status_code=status.HTTP_201_CREATED)
def create_risk_appetite(
    payload: FinancialRiskAppetiteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.QUANTRISK_MANAGE)),
):
    """Create a new draft Financial Risk Appetite version."""
    return QuantumGrcService.create_risk_appetite(
        db, current_user.organization_id, current_user.id, payload
    )


@router.get("/appetites", response_model=List[FinancialRiskAppetiteRead])
def list_risk_appetites(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.QUANTRISK_READ)),
):
    """List tenant risk appetite versions."""
    return QuantumGrcService.list_risk_appetites(
        db, current_user.organization_id, skip=skip, limit=limit
    )


@router.get("/appetites/current", response_model=Optional[FinancialRiskAppetiteRead])
def get_current_appetite(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.QUANTRISK_READ)),
):
    """Retrieve currently active approved risk appetite."""
    return QuantumGrcService.get_active_appetite(db, current_user.organization_id)


@router.get("/appetites/{appetite_id}", response_model=FinancialRiskAppetiteRead)
def get_risk_appetite(
    appetite_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.QUANTRISK_READ)),
):
    """Retrieve a specific risk appetite version."""
    return QuantumGrcService.get_risk_appetite(db, current_user.organization_id, appetite_id)


@router.post("/appetites/{appetite_id}/approve", response_model=FinancialRiskAppetiteRead)
def approve_risk_appetite(
    appetite_id: int,
    payload: Optional[FinancialRiskAppetiteApproveRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.QUANTRISK_APPROVE)),
):
    """Formally approve a Financial Risk Appetite with four-eyes rule (requester != approver)."""
    notes = payload.notes if payload else None
    return QuantumGrcService.approve_risk_appetite(
        db=db,
        org_id=current_user.organization_id,
        user_id=current_user.id,
        appetite_id=appetite_id,
        notes=notes,
    )
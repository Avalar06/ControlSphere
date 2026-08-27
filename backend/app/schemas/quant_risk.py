from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.quant_risk import (
    AppetiteBreachStateEnum,
    AppetiteStatusEnum,
    ScenarioStatusEnum,
    ThreatActorCategoryEnum,
)
from app.schemas.user import UserResponse


# ─────────────────────────────────────────────────────────────────────────────
# 1. QUANTITATIVE RISK SCENARIO SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class QuantitativeRiskScenarioBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=5)
    threat_actor_category: ThreatActorCategoryEnum = ThreatActorCategoryEnum.CYBERCRIMINAL

    # Upstream Linkages
    risk_id: Optional[int] = None
    organization_control_id: Optional[int] = None
    vendor_id: Optional[int] = None

    # Three-Point Threat & Loss Inputs
    tef_min: float = Field(default=0.0, ge=0.0, description="Minimum Threat Event Frequency (events/yr)")
    tef_mode: float = Field(default=1.0, ge=0.0, description="Most likely Threat Event Frequency (events/yr)")
    tef_max: float = Field(default=5.0, ge=0.0, description="Maximum Threat Event Frequency (events/yr)")
    tcap: float = Field(default=0.5, ge=0.0, le=1.0, description="Threat Capability Factor (0.0 to 1.0)")

    pl_min: float = Field(default=0.0, ge=0.0, description="Minimum Primary Loss in USD")
    pl_mode: float = Field(default=10000.0, ge=0.0, description="Most likely Primary Loss in USD")
    pl_max: float = Field(default=50000.0, ge=0.0, description="Maximum Primary Loss in USD")

    sl_min: float = Field(default=0.0, ge=0.0, description="Minimum Secondary Loss in USD")
    sl_mode: float = Field(default=5000.0, ge=0.0, description="Most likely Secondary Loss in USD")
    sl_max: float = Field(default=20000.0, ge=0.0, description="Maximum Secondary Loss in USD")
    slop: float = Field(default=0.5, ge=0.0, le=1.0, description="Secondary Loss Event Probability (0.0 to 1.0)")


class QuantitativeRiskScenarioCreate(QuantitativeRiskScenarioBase):
    scenario_code: str = Field(..., min_length=3, max_length=64)

    @model_validator(mode="after")
    def validate_pert_ranges(self) -> "QuantitativeRiskScenarioCreate":
        if not (self.tef_min <= self.tef_mode <= self.tef_max):
            raise ValueError(
                f"Invalid TEF range: must satisfy tef_min ({self.tef_min}) <= tef_mode ({self.tef_mode}) <= tef_max ({self.tef_max})"
            )
        if not (self.pl_min <= self.pl_mode <= self.pl_max):
            raise ValueError(
                f"Invalid Primary Loss range: must satisfy pl_min ({self.pl_min}) <= pl_mode ({self.pl_mode}) <= pl_max ({self.pl_max})"
            )
        if not (self.sl_min <= self.sl_mode <= self.sl_max):
            raise ValueError(
                f"Invalid Secondary Loss range: must satisfy sl_min ({self.sl_min}) <= sl_mode ({self.sl_mode}) <= sl_max ({self.sl_max})"
            )
        return self


class QuantitativeRiskScenarioUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=255)
    description: Optional[str] = Field(default=None, min_length=5)
    threat_actor_category: Optional[ThreatActorCategoryEnum] = None

    risk_id: Optional[int] = None
    organization_control_id: Optional[int] = None
    vendor_id: Optional[int] = None

    tef_min: Optional[float] = Field(default=None, ge=0.0)
    tef_mode: Optional[float] = Field(default=None, ge=0.0)
    tef_max: Optional[float] = Field(default=None, ge=0.0)
    tcap: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    pl_min: Optional[float] = Field(default=None, ge=0.0)
    pl_mode: Optional[float] = Field(default=None, ge=0.0)
    pl_max: Optional[float] = Field(default=None, ge=0.0)

    sl_min: Optional[float] = Field(default=None, ge=0.0)
    sl_mode: Optional[float] = Field(default=None, ge=0.0)
    sl_max: Optional[float] = Field(default=None, ge=0.0)
    slop: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_pert_ranges(self) -> "QuantitativeRiskScenarioUpdate":
        if self.tef_min is not None and self.tef_mode is not None and self.tef_max is not None:
            if not (self.tef_min <= self.tef_mode <= self.tef_max):
                raise ValueError("Invalid TEF range: must satisfy tef_min <= tef_mode <= tef_max")
        if self.pl_min is not None and self.pl_mode is not None and self.pl_max is not None:
            if not (self.pl_min <= self.pl_mode <= self.pl_max):
                raise ValueError("Invalid Primary Loss range: must satisfy pl_min <= pl_mode <= pl_max")
        if self.sl_min is not None and self.sl_mode is not None and self.sl_max is not None:
            if not (self.sl_min <= self.sl_mode <= self.sl_max):
                raise ValueError("Invalid Secondary Loss range: must satisfy sl_min <= sl_mode <= sl_max")
        return self


class QuantitativeRiskScenarioRead(QuantitativeRiskScenarioBase):
    id: int
    organization_id: int
    scenario_code: str
    status: ScenarioStatusEnum

    # Server-Authoritative Calculated Metrics
    control_strength: float
    vulnerability_factor: float
    loss_event_frequency: float
    single_loss_expectancy: float
    annualized_loss_expectancy: float
    var_95_parametric: Optional[float] = None
    var_99_parametric: Optional[float] = None
    var_95_empirical: Optional[float] = None
    var_99_empirical: Optional[float] = None

    # Governance & Immutability
    is_immutable: bool
    is_ccm_stale: bool
    calculation_version: str
    input_snapshot_hash: Optional[str] = None
    calculated_at: Optional[datetime] = None

    created_by_id: int
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UserResponse] = None

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# 2. QUANTITATIVE SIMULATION RUN SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class QuantitativeSimulationRequest(BaseModel):
    trial_count: int = Field(
        default=10000,
        ge=100,
        le=50000,
        description="Number of empirical simulation trials (100 to 50,000)",
    )
    simulation_seed: Optional[int] = Field(
        default=None,
        description="Optional seed for deterministic reproducibility",
    )


class QuantitativeSimulationRunRead(BaseModel):
    id: int
    organization_id: int
    scenario_id: int
    trial_count: int
    simulation_seed: int
    algorithm_version: str

    mean_loss: float
    variance_loss: float
    std_dev_loss: float

    percentile_10: float
    percentile_50: float
    percentile_90: float
    percentile_95: float
    percentile_99: float

    simulated_by_id: int
    simulated_at: datetime
    simulated_by: Optional[UserResponse] = None

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# 3. ROSI ANALYSIS SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class RosiAnalysisCreate(BaseModel):
    remediation_plan_id: int
    remediation_cost: float = Field(..., gt=0.0, description="Cost of remediation in USD (must be > 0)")
    projected_control_strength_delta: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional manual projected CS improvement (0.0 to 1.0); defaults to plan REI derivation",
    )


class RosiAnalysisRead(BaseModel):
    id: int
    organization_id: int
    scenario_id: int
    remediation_plan_id: int

    remediation_cost: float
    current_ale: float
    projected_ale: float
    risk_reduction_ale: float
    net_economic_benefit: float
    rosi_percentage: float

    created_by_id: int
    created_at: datetime
    created_by: Optional[UserResponse] = None

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# 4. FINANCIAL RISK APPETITE SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class FinancialRiskAppetiteCreate(BaseModel):
    ale_limit: float = Field(..., ge=0.0, description="Maximum Annualized Loss Expectancy in USD")
    var_95_limit: float = Field(..., ge=0.0, description="Maximum 95th Percentile Tail Loss in USD")
    notes: Optional[str] = None


class FinancialRiskAppetiteApproveRequest(BaseModel):
    notes: Optional[str] = None


class FinancialRiskAppetiteRead(BaseModel):
    id: int
    organization_id: int
    version: int
    ale_limit: float
    var_95_limit: float
    status: AppetiteStatusEnum
    notes: Optional[str] = None

    requested_by_id: int
    approved_by_id: Optional[int] = None
    created_at: datetime
    approved_at: Optional[datetime] = None

    requested_by: Optional[UserResponse] = None
    approved_by: Optional[UserResponse] = None

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# 5. OVERVIEW & PORTFOLIO TELEMETRY SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class QuantOverviewResponse(BaseModel):
    total_scenarios: int
    active_scenarios: int
    frozen_scenarios: int
    portfolio_ale: float
    portfolio_var_95: float
    appetite_status: AppetiteBreachStateEnum
    ale_limit: Optional[float] = None
    var_95_limit: Optional[float] = None
    threat_category_distribution: Dict[str, int]
    top_risk_scenarios: List[QuantitativeRiskScenarioRead]

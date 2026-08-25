from datetime import date, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.risk import (
    RiskCategoryEnum,
    RiskSourceEnum,
    RiskStatusEnum,
    RiskTreatmentStrategyEnum,
)
from app.schemas.control import OrganizationControlResponse
from app.schemas.finding import FindingResponse
from app.schemas.user import UserResponse


class RiskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    risk_category: RiskCategoryEnum = RiskCategoryEnum.CYBERSECURITY
    risk_source: RiskSourceEnum = RiskSourceEnum.INTERNAL_AUDIT
    inherent_impact: int = Field(default=3, ge=1, le=5)
    inherent_likelihood: int = Field(default=3, ge=1, le=5)
    target_risk_band: str = Field(default="MODERATE")
    owner_id: Optional[int] = None
    review_date: Optional[date] = None


class RiskCreate(RiskBase):
    treatment_strategy: RiskTreatmentStrategyEnum = RiskTreatmentStrategyEnum.NOT_SPECIFIED
    treatment_plan: Optional[str] = None
    treatment_owner_id: Optional[int] = None
    treatment_due_date: Optional[date] = None


class RiskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    risk_category: Optional[RiskCategoryEnum] = None
    risk_source: Optional[RiskSourceEnum] = None
    owner_id: Optional[int] = None
    inherent_impact: Optional[int] = Field(None, ge=1, le=5)
    inherent_likelihood: Optional[int] = Field(None, ge=1, le=5)
    residual_impact: Optional[int] = Field(None, ge=1, le=5)
    residual_likelihood: Optional[int] = Field(None, ge=1, le=5)
    target_risk_band: Optional[str] = None
    treatment_strategy: Optional[RiskTreatmentStrategyEnum] = None
    treatment_plan: Optional[str] = None
    treatment_owner_id: Optional[int] = None
    treatment_due_date: Optional[date] = None
    review_date: Optional[date] = None


class RiskStatusUpdate(BaseModel):
    status: RiskStatusEnum
    notes: Optional[str] = None


class RiskAcceptance(BaseModel):
    justification: str = Field(..., min_length=5)
    expiry_date: Optional[date] = None


class RiskControlLinkCreate(BaseModel):
    organization_control_id: int


class RiskControlLinkResponse(BaseModel):
    id: int
    organization_id: int
    risk_id: int
    organization_control_id: int
    created_by_id: Optional[int] = None
    created_at: datetime
    organization_control: Optional[OrganizationControlResponse] = None

    model_config = ConfigDict(from_attributes=True)


class LinkedFindingResponse(BaseModel):
    id: int
    organization_id: int
    title: str
    finding_type: str
    severity: str
    risk_score: int
    risk_band: str
    status: str
    due_date: Optional[date] = None

    model_config = ConfigDict(from_attributes=True)


class RiskFindingLinkCreate(BaseModel):
    finding_id: int


class RiskFindingLinkResponse(BaseModel):
    id: int
    organization_id: int
    risk_id: int
    finding_id: int
    created_by_id: Optional[int] = None
    created_at: datetime
    finding: Optional[LinkedFindingResponse] = None

    model_config = ConfigDict(from_attributes=True)


class RiskResponse(RiskBase):
    id: int
    organization_id: int
    inherent_score: int
    inherent_band: str
    residual_impact: Optional[int] = None
    residual_likelihood: Optional[int] = None
    residual_score: Optional[int] = None
    residual_band: Optional[str] = None
    appetite_status: str  # WITHIN_APPETITE, NEAR_LIMIT, ABOVE_APPETITE
    status: RiskStatusEnum

    treatment_strategy: RiskTreatmentStrategyEnum
    treatment_plan: Optional[str] = None
    treatment_owner_id: Optional[int] = None
    treatment_due_date: Optional[date] = None
    treatment_overdue_status: str = "NO_DUE_DATE"

    risk_acceptance_justification: Optional[str] = None
    risk_accepted_at: Optional[datetime] = None
    risk_accepted_by_id: Optional[int] = None
    risk_acceptance_expiry: Optional[date] = None

    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    owner: Optional[UserResponse] = None
    treatment_owner: Optional[UserResponse] = None
    created_by: Optional[UserResponse] = None
    risk_accepted_by: Optional[UserResponse] = None

    linked_controls_count: int = 0
    linked_findings_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class RiskDetailResponse(RiskResponse):
    control_links: List[RiskControlLinkResponse] = []
    finding_links: List[RiskFindingLinkResponse] = []

    model_config = ConfigDict(from_attributes=True)


class HeatmapCell(BaseModel):
    likelihood: int
    impact: int
    score: int
    band: str
    count: int


class RiskStatsResponse(BaseModel):
    total_risks: int
    identified_count: int
    assessed_count: int
    treatment_planned_count: int
    mitigating_count: int
    monitoring_count: int
    accepted_count: int
    closed_count: int

    critical_inherent_count: int
    high_inherent_count: int
    moderate_inherent_count: int
    low_inherent_count: int

    above_appetite_count: int
    near_limit_count: int
    within_appetite_count: int

    overdue_treatments_count: int
    due_soon_treatments_count: int

    inherent_vs_residual_reduction: float  # Percentage risk score reduction

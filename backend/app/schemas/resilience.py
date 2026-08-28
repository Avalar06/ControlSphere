from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.resilience import (
    BiaStatusEnum,
    CriticalityTierEnum,
    DependencyTypeEnum,
)
from app.schemas.user import UserResponse


# ─────────────────────────────────────────────────────────────────────────────
# 1. BUSINESS PROCESS SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class BusinessProcessBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Unique business process name")
    description: Optional[str] = Field(default=None, description="Detailed function and scope description")
    criticality_tier: CriticalityTierEnum = Field(
        default=CriticalityTierEnum.TIER_3,
        description="Organizational criticality classification tier",
    )


class BusinessProcessCreate(BusinessProcessBase):
    pass


class BusinessProcessUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    description: Optional[str] = None
    criticality_tier: Optional[CriticalityTierEnum] = None


# ─────────────────────────────────────────────────────────────────────────────
# 2. BUSINESS IMPACT ANALYSIS (BIA) SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class BusinessImpactAnalysisBase(BaseModel):
    rto_hours: float = Field(
        default=4.0,
        ge=0.0,
        description="Recovery Time Objective in hours (must be <= MTD)",
    )
    rpo_hours: float = Field(
        default=1.0,
        ge=0.0,
        description="Recovery Point Objective in hours",
    )
    mtd_hours: float = Field(
        default=24.0,
        ge=0.0,
        description="Maximum Tolerable Downtime in hours",
    )
    hourly_downtime_cost: float = Field(
        default=10000.0,
        ge=0.0,
        description="Financial disruption loss per downtime hour in USD",
    )
    fixed_outage_cost: float = Field(
        default=5000.0,
        ge=0.0,
        description="Fixed initial disruption/incident cost in USD",
    )
    notes: Optional[str] = Field(default=None, description="Justification and impact context notes")

    @model_validator(mode="after")
    def validate_rto_mtd(self) -> "BusinessImpactAnalysisBase":
        if self.rto_hours > self.mtd_hours:
            raise ValueError(
                f"Invalid downtime thresholds: Recovery Time Objective ({self.rto_hours}h) "
                f"cannot exceed Maximum Tolerable Downtime ({self.mtd_hours}h)."
            )
        return self


class BusinessImpactAnalysisCreate(BusinessImpactAnalysisBase):
    process_id: int = Field(..., description="Target business process ID")


class BusinessImpactAnalysisApproveRequest(BaseModel):
    notes: Optional[str] = Field(default=None, description="Formal approval review notes")


class BusinessImpactAnalysisRead(BusinessImpactAnalysisBase):
    id: int
    organization_id: int
    process_id: int
    status: BiaStatusEnum
    version: int

    requested_by_id: int
    approved_by_id: Optional[int] = None
    approved_at: Optional[datetime] = None

    created_at: datetime
    updated_at: datetime

    requested_by: Optional[UserResponse] = None
    approved_by: Optional[UserResponse] = None

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# 3. PROCESS DEPENDENCY SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class ProcessDependencyCreate(BaseModel):
    process_id: int = Field(..., description="Target business process ID")
    dependency_type: DependencyTypeEnum = Field(..., description="Type of dependency: VENDOR or CONTROL")
    dependency_id: int = Field(..., description="Foreign ID of target Vendor or Control in tenant")
    notes: Optional[str] = Field(default=None, max_length=255, description="Contextual dependency notes")


class ProcessDependencyRead(BaseModel):
    id: int
    organization_id: int
    process_id: int
    dependency_type: DependencyTypeEnum
    dependency_id: int
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# 4. BUSINESS PROCESS READ WITH RELATIONSHIPS
# ─────────────────────────────────────────────────────────────────────────────

class BusinessProcessRead(BusinessProcessBase):
    id: int
    organization_id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime

    owner: Optional[UserResponse] = None
    active_bia: Optional[BusinessImpactAnalysisRead] = None
    dependencies: List[ProcessDependencyRead] = []

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# 5. DETERMINISTIC OUTAGE CALCULATION SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class OutageCostCalculationRequest(BaseModel):
    duration_hours: float = Field(..., ge=0.0, description="Downtime outage duration in hours")
    hourly_downtime_cost: float = Field(..., ge=0.0, description="Hourly variable loss in USD")
    fixed_outage_cost: float = Field(default=0.0, ge=0.0, description="Initial fixed loss in USD")


class OutageCostCalculationResult(BaseModel):
    duration_hours: float
    fixed_outage_cost: float
    hourly_downtime_cost: float
    variable_outage_cost: float
    total_projected_loss: float

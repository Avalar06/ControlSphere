from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.harmonization import (
    CommonControlDomainEnum,
    MappingTypeEnum,
    RationalizationStatusEnum,
)
from app.models.monitoring import ControlHealthStatusEnum


# ── Crosswalk Schemas ─────────────────────────────────────────────────────────

class CrosswalkMappingBase(BaseModel):
    source_subcategory_id: int
    target_subcategory_id: int
    mapping_type: MappingTypeEnum = MappingTypeEnum.EXACT
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    bidirectional: bool = True
    rationale: str = Field(min_length=3)


class CrosswalkMappingCreate(CrosswalkMappingBase):
    pass


class CrosswalkMappingUpdate(BaseModel):
    mapping_type: Optional[MappingTypeEnum] = None
    confidence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    bidirectional: Optional[bool] = None
    rationale: Optional[str] = Field(default=None, min_length=3)


class CrosswalkMappingResponse(CrosswalkMappingBase):
    id: int
    created_at: datetime
    updated_at: datetime
    source_identifier: Optional[str] = None
    source_title: Optional[str] = None
    target_identifier: Optional[str] = None
    target_title: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ── Common Control Mapping Schemas ───────────────────────────────────────────

class CommonControlMappingCreate(BaseModel):
    organization_control_id: int
    weight: float = Field(default=1.0, ge=0.1, le=10.0)


class CommonControlMappingResponse(BaseModel):
    id: int
    organization_id: int
    rationalized_common_control_id: int
    organization_control_id: int
    weight: float
    created_at: datetime

    # Denormalized control context
    control_subcategory_identifier: Optional[str] = None
    control_subcategory_title: Optional[str] = None
    control_status: Optional[str] = None
    control_health_score: Optional[float] = None
    control_health_status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ── Rationalized Common Control Schemas ───────────────────────────────────────

class CommonControlBase(BaseModel):
    common_control_code: str = Field(min_length=2, max_length=64)
    title: str = Field(min_length=2, max_length=255)
    description: str = Field(min_length=5)
    domain: CommonControlDomainEnum = CommonControlDomainEnum.GOVERNANCE_RISK
    rationalization_status: RationalizationStatusEnum = RationalizationStatusEnum.ACTIVE
    owner_id: Optional[int] = None
    deprecation_reason: Optional[str] = None


class CommonControlCreate(CommonControlBase):
    initial_control_ids: Optional[List[int]] = None


class CommonControlUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=255)
    description: Optional[str] = Field(default=None, min_length=5)
    domain: Optional[CommonControlDomainEnum] = None
    rationalization_status: Optional[RationalizationStatusEnum] = None
    owner_id: Optional[int] = None
    deprecation_reason: Optional[str] = None


class CommonControlResponse(CommonControlBase):
    id: int
    organization_id: int
    inherited_health_score: float
    inherited_health_status: ControlHealthStatusEnum
    mapped_controls_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CommonControlDetailResponse(CommonControlResponse):
    mappings: List[CommonControlMappingResponse] = []


# ── Framework Compliance Snapshot & Posture Schemas ─────────────────────────

class FrameworkComplianceSnapshotResponse(BaseModel):
    id: int
    organization_id: int
    framework_id: int
    calculation_version: str
    coverage_percentage: float
    compliance_health_score: float
    total_subcategories: int
    covered_subcategories: int
    unmapped_subcategories: int
    evaluated_at: datetime
    created_at: datetime

    # Framework metadata
    framework_identifier: Optional[str] = None
    framework_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SubcategoryComplianceMatrixItem(BaseModel):
    subcategory_id: int
    subcategory_identifier: str
    subcategory_title: str
    category_identifier: str
    function_identifier: str
    is_directly_covered: bool
    is_crosswalk_covered: bool
    source_subcategory_id: Optional[int] = None
    source_identifier: Optional[str] = None
    crosswalk_confidence: Optional[float] = None
    effective_health_score: float
    health_status: str


class FrameworkCompliancePostureOverview(BaseModel):
    framework_id: int
    framework_identifier: str
    framework_name: str
    total_subcategories: int
    directly_covered_subcategories: int
    crosswalk_covered_subcategories: int
    total_covered_subcategories: int
    coverage_percentage: float
    compliance_health_score: float
    evaluated_at: Optional[datetime] = None


class MultiFrameworkPostureResponse(BaseModel):
    frameworks: List[FrameworkCompliancePostureOverview]
    total_common_controls: int
    average_common_control_health: float
    evaluated_at: datetime


class FrameworkDetailedPostureResponse(BaseModel):
    overview: FrameworkCompliancePostureOverview
    subcategories: List[SubcategoryComplianceMatrixItem] = []


class HarmonizationEvaluationResponse(BaseModel):
    organization_id: int
    evaluated_common_controls: int
    evaluated_frameworks: int
    snapshots_created: int
    evaluated_at: datetime

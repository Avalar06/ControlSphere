from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.exposure import (
    AssetTypeEnum,
    EnvironmentEnum,
    ExceptionApprovalStatusEnum,
    ExposureSeverityEnum,
    ExposureStatusEnum,
)
from app.models.resilience import CriticalityTierEnum
from app.schemas.user import UserResponse


# ─────────────────────────────────────────────────────────────────────────────
# 1. EXPOSURE ASSET LINK SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class ExposureAssetLinkBase(BaseModel):
    asset_identifier: str = Field(..., min_length=1, max_length=255)
    asset_type: AssetTypeEnum = AssetTypeEnum.SERVER
    environment: EnvironmentEnum = EnvironmentEnum.PRODUCTION
    process_id: Optional[int] = None
    vendor_id: Optional[int] = None
    control_id: Optional[int] = None
    notes: Optional[str] = None


class ExposureAssetLinkCreate(ExposureAssetLinkBase):
    pass


class ExposureAssetLinkRead(ExposureAssetLinkBase):
    id: int
    organization_id: int
    exposure_id: int
    created_at: datetime

    # Minimal nested views if available
    process_name: Optional[str] = None
    process_tier: Optional[CriticalityTierEnum] = None
    vendor_name: Optional[str] = None
    control_title: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# 2. EXPOSURE EXCEPTION (FOUR-EYES SLA DEFERRAL) SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class ExposureExceptionBase(BaseModel):
    requested_sla_due: datetime
    justification: str = Field(..., min_length=5)
    compensating_controls: Optional[str] = None


class ExposureExceptionCreate(ExposureExceptionBase):
    pass


class ExposureExceptionReviewRequest(BaseModel):
    decision: ExceptionApprovalStatusEnum = Field(
        ...,
        description="Must be APPROVED or REJECTED",
    )
    review_notes: Optional[str] = None

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, v: ExceptionApprovalStatusEnum) -> ExceptionApprovalStatusEnum:
        if v not in (ExceptionApprovalStatusEnum.APPROVED, ExceptionApprovalStatusEnum.REJECTED):
            raise ValueError("Exception review decision must be APPROVED or REJECTED.")
        return v


class ExposureExceptionRead(BaseModel):
    id: int
    organization_id: int
    exposure_id: int
    requested_by_id: int
    approved_by_id: Optional[int] = None
    status: ExceptionApprovalStatusEnum
    original_sla_due: datetime
    requested_sla_due: datetime
    justification: str
    compensating_controls: Optional[str] = None
    review_notes: Optional[str] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None

    requested_by: Optional[UserResponse] = None
    approved_by: Optional[UserResponse] = None

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# 3. VULNERABILITY EXPOSURE SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class VulnerabilityExposureBase(BaseModel):
    cve_id: str = Field(..., min_length=3, max_length=50)
    cwe_id: Optional[str] = Field(None, max_length=50)
    title: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    cvss_score: float = Field(default=0.0, ge=0.0, le=10.0)
    cvss_vector: Optional[str] = Field(None, max_length=150)
    epss_score: float = Field(default=0.0, ge=0.0, le=1.0)
    cisa_kev: bool = False
    severity: ExposureSeverityEnum = ExposureSeverityEnum.MEDIUM

    @field_validator("cve_id")
    @classmethod
    def format_cve(cls, v: str) -> str:
        cleaned = v.strip().upper()
        if not cleaned:
            raise ValueError("CVE ID cannot be empty.")
        return cleaned


class VulnerabilityExposureCreate(VulnerabilityExposureBase):
    discovered_at: Optional[datetime] = None
    remediation_sla_due: Optional[datetime] = None


class VulnerabilityExposureUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    cwe_id: Optional[str] = Field(None, max_length=50)
    cvss_score: Optional[float] = Field(None, ge=0.0, le=10.0)
    cvss_vector: Optional[str] = Field(None, max_length=150)
    epss_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    cisa_kev: Optional[bool] = None
    severity: Optional[ExposureSeverityEnum] = None


class VulnerabilityExposureStatusUpdate(BaseModel):
    status: ExposureStatusEnum
    notes: Optional[str] = None


class VulnerabilityExposureRead(VulnerabilityExposureBase):
    id: int
    organization_id: int
    status: ExposureStatusEnum
    exposure_index: float
    remediation_sla_due: datetime
    remediation_plan_id: Optional[int] = None
    discovered_at: datetime
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    asset_links: List[ExposureAssetLinkRead] = []
    exceptions: List[ExposureExceptionRead] = []

    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────────────────────────────────────
# 4. CALCULATION & SUMMARY POSTURE SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class ExposureIndexCalculateRequest(BaseModel):
    cvss_score: float = Field(..., ge=0.0, le=10.0)
    epss_score: float = Field(default=0.0, ge=0.0, le=1.0)
    cisa_kev: bool = False
    highest_process_tier: Optional[CriticalityTierEnum] = None


class ExposureIndexCalculateResponse(BaseModel):
    cvss_score: float
    epss_score: float
    cisa_kev: bool
    base_score: float
    blast_radius_multiplier: float
    exposure_index: float


class ExposureSummaryResponse(BaseModel):
    total_exposures: int
    critical_exposures: int
    high_exposures: int
    cisa_kev_count: int
    active_exceptions_count: int
    sla_breached_count: int
    sla_breach_rate_percent: float
    average_exposure_index: float
    severity_distribution: Dict[str, int]
    status_distribution: Dict[str, int]

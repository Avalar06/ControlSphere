from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.regulatory import (
    RegulatoryAuthorityTypeEnum,
    RegulatoryTrustTierEnum,
    RegulatoryEnforceabilityEnum,
    RegulatoryMandateStatusEnum,
    RegulatoryApplicabilityEnum,
    RegulatoryComplianceStatusEnum,
    RegulatoryChangeTypeEnum,
    RegulatoryChangeSeverityEnum,
    RegulatoryChangeStatusEnum,
    RegulatoryImpactLevelEnum,
    RegulatoryImpactStatusEnum,
)


# ── Regulatory Source Schemas ───────────────────────────────────────────────

class RegulatorySourceBase(BaseModel):
    source_code: str = Field(..., max_length=64)
    name: str = Field(..., max_length=255)
    authority_type: RegulatoryAuthorityTypeEnum = RegulatoryAuthorityTypeEnum.GOVERNMENT
    jurisdiction: str = Field(..., max_length=100)
    website_url: Optional[str] = Field(None, max_length=500)
    trust_tier: RegulatoryTrustTierEnum = RegulatoryTrustTierEnum.OFFICIAL
    description: Optional[str] = None
    is_active: bool = True


class RegulatorySourceCreate(RegulatorySourceBase):
    pass


class RegulatorySourceUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    authority_type: Optional[RegulatoryAuthorityTypeEnum] = None
    jurisdiction: Optional[str] = Field(None, max_length=100)
    website_url: Optional[str] = Field(None, max_length=500)
    trust_tier: Optional[RegulatoryTrustTierEnum] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class RegulatorySourceResponse(RegulatorySourceBase):
    id: int
    organization_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Regulatory Mandate Schemas ──────────────────────────────────────────────

class RegulatoryMandateBase(BaseModel):
    source_id: int
    mandate_code: str = Field(..., max_length=64)
    title: str = Field(..., max_length=255)
    short_name: str = Field(..., max_length=100)
    legal_citation: Optional[str] = Field(None, max_length=255)
    jurisdiction: str = Field(..., max_length=100)
    enforceability_level: RegulatoryEnforceabilityEnum = RegulatoryEnforceabilityEnum.MANDATORY
    status: RegulatoryMandateStatusEnum = RegulatoryMandateStatusEnum.DRAFT
    framework_id: Optional[int] = None
    description: Optional[str] = None
    effective_date: Optional[date] = None
    sunset_date: Optional[date] = None


class RegulatoryMandateCreate(RegulatoryMandateBase):
    pass


class RegulatoryMandateUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    short_name: Optional[str] = Field(None, max_length=100)
    legal_citation: Optional[str] = Field(None, max_length=255)
    jurisdiction: Optional[str] = Field(None, max_length=100)
    enforceability_level: Optional[RegulatoryEnforceabilityEnum] = None
    status: Optional[RegulatoryMandateStatusEnum] = None
    framework_id: Optional[int] = None
    description: Optional[str] = None
    effective_date: Optional[date] = None
    sunset_date: Optional[date] = None


class RegulatoryMandateResponse(RegulatoryMandateBase):
    id: int
    organization_id: int
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Regulatory Version Schemas ──────────────────────────────────────────────

class RegulatoryVersionBase(BaseModel):
    mandate_id: int
    version_code: str = Field(..., max_length=64)
    title: str = Field(..., max_length=255)
    published_date: date
    effective_date: date
    sunset_date: Optional[date] = None
    content_hash_sha256: str = Field(..., max_length=64)
    change_summary: Optional[str] = None
    is_current: bool = True


class RegulatoryVersionCreate(RegulatoryVersionBase):
    pass


class RegulatoryVersionResponse(RegulatoryVersionBase):
    id: int
    organization_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Regulatory Obligation Schemas ───────────────────────────────────────────

class RegulatoryObligationBase(BaseModel):
    mandate_id: int
    version_id: Optional[int] = None
    obligation_code: str = Field(..., max_length=64)
    title: str = Field(..., max_length=255)
    description: str
    article_reference: Optional[str] = Field(None, max_length=100)
    applicability: RegulatoryApplicabilityEnum = RegulatoryApplicabilityEnum.APPLICABLE
    organization_control_id: Optional[int] = None
    compliance_status: RegulatoryComplianceStatusEnum = RegulatoryComplianceStatusEnum.NEEDS_REVIEW


class RegulatoryObligationCreate(RegulatoryObligationBase):
    pass


class RegulatoryObligationUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    article_reference: Optional[str] = Field(None, max_length=100)
    applicability: Optional[RegulatoryApplicabilityEnum] = None
    organization_control_id: Optional[int] = None
    compliance_status: Optional[RegulatoryComplianceStatusEnum] = None


class RegulatoryObligationResponse(RegulatoryObligationBase):
    id: int
    organization_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Regulatory Change Event Schemas ─────────────────────────────────────────

class RegulatoryChangeEventBase(BaseModel):
    mandate_id: int
    change_code: str = Field(..., max_length=64)
    title: str = Field(..., max_length=255)
    change_type: RegulatoryChangeTypeEnum = RegulatoryChangeTypeEnum.AMENDMENT
    severity: RegulatoryChangeSeverityEnum = RegulatoryChangeSeverityEnum.MAJOR
    official_publication_date: date
    enforcement_date: Optional[date] = None
    source_url: Optional[str] = Field(None, max_length=500)
    raw_summary: str


class RegulatoryChangeEventCreate(RegulatoryChangeEventBase):
    content_hash_sha256: Optional[str] = Field(None, max_length=64)  # Computed server-side if not supplied


class RegulatoryChangeReviewRequest(BaseModel):
    review_notes: Optional[str] = None
    impact_level: RegulatoryImpactLevelEnum = RegulatoryImpactLevelEnum.MEDIUM
    impacted_control_ids: Optional[List[int]] = None
    impacted_policy_ids: Optional[List[int]] = None
    gap_analysis_summary: str
    action_plan: Optional[str] = None


class RegulatoryChangeApproveRequest(BaseModel):
    review_notes: Optional[str] = None


class RegulatoryChangeDismissRequest(BaseModel):
    dismissal_reason: str


class RegulatoryChangeEventResponse(RegulatoryChangeEventBase):
    id: int
    organization_id: int
    status: RegulatoryChangeStatusEnum
    content_hash_sha256: str
    created_by_id: Optional[int] = None
    approved_by_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    dismissal_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Regulatory Impact Assessment Schemas ────────────────────────────────────

class RegulatoryImpactAssessmentResponse(BaseModel):
    id: int
    organization_id: int
    change_event_id: int
    assessment_code: str
    title: str
    impact_level: RegulatoryImpactLevelEnum
    status: RegulatoryImpactStatusEnum
    impacted_control_ids: Optional[str] = None
    impacted_policy_ids: Optional[str] = None
    gap_analysis_summary: str
    action_plan: Optional[str] = None
    created_by_id: int
    reviewed_by_id: Optional[int] = None
    approved_by_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

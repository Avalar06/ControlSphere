from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.tprm import (
    BusinessCriticalityEnum,
    DataClassificationEnum,
    EngagementStatusEnum,
    HostingModelEnum,
    NetworkConnectivityEnum,
    PiiFinancialAccessEnum,
    VendorAssessmentStatusEnum,
    VendorAssessmentTypeEnum,
    VendorDocumentTypeEnum,
    VendorResponseStatusEnum,
    VendorRiskBandEnum,
    VendorStatusEnum,
    VendorTierEnum,
)


# ─── VENDOR SCHEMAS ──────────────────────────────────────────────────────────

class VendorBase(BaseModel):
    vendor_code: str = Field(..., min_length=2, max_length=50)
    legal_name: str = Field(..., min_length=2, max_length=255)
    trade_name: Optional[str] = Field(None, max_length=255)
    business_owner_id: Optional[int] = None


class VendorCreate(VendorBase):
    pass


class VendorUpdate(BaseModel):
    legal_name: Optional[str] = Field(None, min_length=2, max_length=255)
    trade_name: Optional[str] = Field(None, max_length=255)
    vendor_status: Optional[VendorStatusEnum] = None
    business_owner_id: Optional[int] = None


class VendorTierOverride(BaseModel):
    override_tier: VendorTierEnum
    reason: str = Field(..., min_length=10, description="Mandatory justification for manual tier override")


class VendorRead(VendorBase):
    id: int
    organization_id: int
    vendor_status: VendorStatusEnum
    calculated_inherent_risk: float
    calculated_tier: VendorTierEnum
    override_tier: Optional[VendorTierEnum] = None
    tier_override_reason: Optional[str] = None
    tier_overridden_by_id: Optional[int] = None
    tier_overridden_at: Optional[datetime] = None
    effective_tier: VendorTierEnum
    residual_risk_score: float
    risk_band: VendorRiskBandEnum
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── VENDOR ENGAGEMENT SCHEMAS ──────────────────────────────────────────────

class VendorEngagementBase(BaseModel):
    engagement_code: str = Field(..., min_length=2, max_length=50)
    engagement_name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    criticality: BusinessCriticalityEnum = BusinessCriticalityEnum.MEDIUM
    data_classification: DataClassificationEnum = DataClassificationEnum.INTERNAL
    hosting_model: HostingModelEnum = HostingModelEnum.MULTI_TENANT_SAAS
    network_connectivity: NetworkConnectivityEnum = NetworkConnectivityEnum.ISOLATED_NO_CONNECTION
    pii_access: PiiFinancialAccessEnum = PiiFinancialAccessEnum.NONE


class VendorEngagementCreate(VendorEngagementBase):
    pass


class VendorEngagementUpdate(BaseModel):
    engagement_name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    status: Optional[EngagementStatusEnum] = None
    criticality: Optional[BusinessCriticalityEnum] = None
    data_classification: Optional[DataClassificationEnum] = None
    hosting_model: Optional[HostingModelEnum] = None
    network_connectivity: Optional[NetworkConnectivityEnum] = None
    pii_access: Optional[PiiFinancialAccessEnum] = None


class VendorEngagementRead(VendorEngagementBase):
    id: int
    organization_id: int
    vendor_id: int
    status: EngagementStatusEnum
    calculated_risk_score: float
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── VENDOR ASSESSMENT ITEM SCHEMAS ─────────────────────────────────────────

class VendorAssessmentItemBase(BaseModel):
    question_key: str = Field(..., min_length=1, max_length=100)
    question_text: str = Field(..., min_length=1)
    rationalized_common_control_id: Optional[int] = None
    response_status: VendorResponseStatusEnum = VendorResponseStatusEnum.NOT_APPLICABLE
    weight: float = Field(1.0, ge=0.1, le=10.0)
    vendor_response_text: Optional[str] = None
    assessor_notes: Optional[str] = None


class VendorAssessmentItemCreate(VendorAssessmentItemBase):
    pass


class VendorAssessmentItemUpdate(BaseModel):
    response_status: Optional[VendorResponseStatusEnum] = None
    vendor_response_text: Optional[str] = None
    assessor_notes: Optional[str] = None


class VendorAssessmentItemRead(VendorAssessmentItemBase):
    id: int
    organization_id: int
    assessment_id: int
    findings_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── VENDOR ASSESSMENT SCHEMAS ──────────────────────────────────────────────

class VendorAssessmentBase(BaseModel):
    assessment_code: str = Field(..., min_length=2, max_length=50)
    title: str = Field(..., min_length=2, max_length=255)
    assessment_type: VendorAssessmentTypeEnum = VendorAssessmentTypeEnum.INITIAL_DUE_DILIGENCE
    engagement_id: Optional[int] = None
    valid_until: Optional[datetime] = None


class VendorAssessmentCreate(VendorAssessmentBase):
    items: Optional[List[VendorAssessmentItemCreate]] = None


class VendorAssessmentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    engagement_id: Optional[int] = None
    valid_until: Optional[datetime] = None


class VendorAssessmentReview(BaseModel):
    review_notes: Optional[str] = None
    rejection_reason: Optional[str] = None


class VendorAssessmentRead(VendorAssessmentBase):
    id: int
    organization_id: int
    vendor_id: int
    status: VendorAssessmentStatusEnum
    assessor_id: int
    reviewer_id: Optional[int] = None
    calculated_score: float
    review_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    items: List[VendorAssessmentItemRead] = []

    model_config = ConfigDict(from_attributes=True)


# ─── VENDOR EVIDENCE LINK SCHEMAS ───────────────────────────────────────────

class VendorEvidenceLinkCreate(BaseModel):
    evidence_id: int
    document_type: VendorDocumentTypeEnum = VendorDocumentTypeEnum.OTHER
    effective_date: datetime
    expiration_date: datetime


class VendorEvidenceLinkRead(BaseModel):
    id: int
    organization_id: int
    vendor_id: int
    evidence_id: int
    document_type: VendorDocumentTypeEnum
    effective_date: datetime
    expiration_date: datetime
    is_verified: bool
    verified_by_id: Optional[int] = None
    verified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── TELEMETRY & POSTURE SCHEMAS ─────────────────────────────────────────────

class VendorInherentRiskBreakdown(BaseModel):
    inherent_risk_score: float
    calculated_tier: VendorTierEnum
    effective_tier: VendorTierEnum
    highest_criticality_engagement_code: Optional[str] = None
    active_engagements_count: int


class VendorResidualRiskBreakdown(BaseModel):
    inherent_risk_score: float
    latest_assessment_score: Optional[float] = None
    risk_floor: float
    base_residual_risk: float
    finding_penalties: float
    exception_penalties: float
    residual_risk_score: float
    risk_band: VendorRiskBandEnum


class VendorRiskPostureResponse(BaseModel):
    vendor_id: int
    vendor_code: str
    legal_name: str
    status: VendorStatusEnum
    inherent: VendorInherentRiskBreakdown
    residual: VendorResidualRiskBreakdown
    engagements: List[VendorEngagementRead]
    latest_approved_assessment: Optional[VendorAssessmentRead] = None
    evidence_links: List[VendorEvidenceLinkRead]

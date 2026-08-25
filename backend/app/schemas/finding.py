from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.finding import (
    FindingSeverityEnum,
    FindingStatusEnum,
    FindingTypeEnum,
)
from app.schemas.evidence import EvidenceItemResponse
from app.schemas.user import UserResponse


class FindingBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    finding_type: FindingTypeEnum = FindingTypeEnum.CONTROL_GAP
    severity: FindingSeverityEnum = FindingSeverityEnum.MEDIUM
    impact: int = Field(default=3, ge=1, le=5)
    likelihood: int = Field(default=3, ge=1, le=5)
    recommendation: str = Field(..., min_length=1)
    root_cause: Optional[str] = None
    due_date: Optional[date] = None
    remediation_plan: Optional[str] = None
    owner_id: Optional[int] = None


class FindingCreate(FindingBase):
    organization_control_id: int
    assessment_id: Optional[int] = None


class FindingUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    finding_type: Optional[FindingTypeEnum] = None
    severity: Optional[FindingSeverityEnum] = None
    impact: Optional[int] = Field(None, ge=1, le=5)
    likelihood: Optional[int] = Field(None, ge=1, le=5)
    recommendation: Optional[str] = None
    root_cause: Optional[str] = None
    due_date: Optional[date] = None
    remediation_plan: Optional[str] = None
    remediation_notes: Optional[str] = None
    owner_id: Optional[int] = None


class FindingStatusUpdate(BaseModel):
    status: FindingStatusEnum
    notes: Optional[str] = None
    resolution: Optional[str] = None


class FindingValidation(BaseModel):
    is_valid: bool
    validation_notes: str = Field(..., min_length=1)


class FindingRiskAcceptance(BaseModel):
    justification: str = Field(..., min_length=5)
    expiry_date: Optional[date] = None


class FindingEvidenceCreate(BaseModel):
    evidence_id: int


class FindingEvidenceResponse(BaseModel):
    id: int
    organization_id: int
    finding_id: int
    evidence_id: int
    created_by_id: Optional[int] = None
    created_at: datetime
    evidence: Optional[EvidenceItemResponse] = None

    model_config = ConfigDict(from_attributes=True)


class FindingResponse(FindingBase):
    id: int
    organization_id: int
    organization_control_id: int
    assessment_id: Optional[int] = None
    risk_score: int
    risk_band: str
    status: FindingStatusEnum
    overdue_status: str  # ON_TRACK, DUE_SOON, OVERDUE, NO_DUE_DATE, COMPLETED

    remediation_notes: Optional[str] = None
    resolution: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by_id: Optional[int] = None
    closed_at: Optional[datetime] = None
    closed_by_id: Optional[int] = None

    risk_acceptance_justification: Optional[str] = None
    risk_accepted_at: Optional[datetime] = None
    risk_accepted_by_id: Optional[int] = None
    risk_acceptance_expiry: Optional[date] = None

    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    owner: Optional[UserResponse] = None
    created_by: Optional[UserResponse] = None
    resolved_by: Optional[UserResponse] = None
    closed_by: Optional[UserResponse] = None
    risk_accepted_by: Optional[UserResponse] = None

    control_identifier: Optional[str] = None
    control_title: Optional[str] = None
    assessment_summary: Optional[str] = None
    evidence_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class FindingDetailResponse(FindingResponse):
    evidence_links: List[FindingEvidenceResponse] = []

    model_config = ConfigDict(from_attributes=True)


class FindingStatsResponse(BaseModel):
    total_findings: int
    open_count: int
    in_remediation_count: int
    pending_validation_count: int
    resolved_count: int
    accepted_risk_count: int
    closed_count: int

    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    informational_count: int

    overdue_count: int
    due_soon_count: int
    on_track_count: int

from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.assessment import (
    AssessmentConclusionEnum,
    AssessmentMethodEnum,
    AssessmentStatusEnum,
)
from app.schemas.evidence import EvidenceItemResponse
from app.schemas.user import UserResponse


class AssessmentBase(BaseModel):
    assessment_method: AssessmentMethodEnum = AssessmentMethodEnum.EXAMINATION
    assessment_scope: Optional[str] = None
    assessment_date: date = Field(default_factory=date.today)
    summary: Optional[str] = None
    limitations: Optional[str] = None


class AssessmentCreate(AssessmentBase):
    organization_control_id: int
    assessor_id: Optional[int] = None


class AssessmentUpdate(BaseModel):
    assessment_method: Optional[AssessmentMethodEnum] = None
    assessment_scope: Optional[str] = None
    assessment_date: Optional[date] = None
    summary: Optional[str] = None
    limitations: Optional[str] = None
    assessor_id: Optional[int] = None


class AssessmentComplete(BaseModel):
    conclusion: AssessmentConclusionEnum
    summary: str = Field(..., min_length=1)
    limitations: Optional[str] = None


class AssessmentEvidenceCreate(BaseModel):
    evidence_id: int


class AssessmentEvidenceResponse(BaseModel):
    id: int
    organization_id: int
    assessment_id: int
    evidence_id: int
    created_by_id: Optional[int] = None
    created_at: datetime
    evidence: Optional[EvidenceItemResponse] = None

    model_config = ConfigDict(from_attributes=True)


class AssessmentResponse(AssessmentBase):
    id: int
    organization_id: int
    organization_control_id: int
    assessor_id: Optional[int] = None
    status: AssessmentStatusEnum
    conclusion: AssessmentConclusionEnum
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    assessor: Optional[UserResponse] = None
    control_identifier: Optional[str] = None
    control_title: Optional[str] = None
    evidence_count: int = 0
    findings_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class AssessmentDetailResponse(AssessmentResponse):
    evidence_links: List[AssessmentEvidenceResponse] = []

    model_config = ConfigDict(from_attributes=True)


class AssessmentStatsResponse(BaseModel):
    total_assessments: int
    draft_count: int
    in_progress_count: int
    completed_count: int
    superseded_count: int
    effective_count: int
    partially_effective_count: int
    ineffective_count: int
    not_assessed_count: int

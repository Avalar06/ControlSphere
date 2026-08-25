from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.evidence import (
    EvidenceStatusEnum,
    EvidenceTypeEnum,
    ReviewDecisionEnum,
)
from app.schemas.user import UserResponse


# ----------------------------------------------------
# Evidence Requirement Schemas
# ----------------------------------------------------
class EvidenceRequirementBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    evidence_type: EvidenceTypeEnum = EvidenceTypeEnum.DOCUMENT
    is_required: bool = True
    guidance: Optional[str] = None


class EvidenceRequirementCreate(EvidenceRequirementBase):
    organization_control_id: int


class EvidenceRequirementUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    evidence_type: Optional[EvidenceTypeEnum] = None
    is_required: Optional[bool] = None
    guidance: Optional[str] = None


class EvidenceRequirementResponse(EvidenceRequirementBase):
    id: int
    organization_id: int
    organization_control_id: int
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UserResponse] = None
    items_count: int = 0
    accepted_items_count: int = 0

    model_config = ConfigDict(from_attributes=True)


# ----------------------------------------------------
# Evidence Review Schemas
# ----------------------------------------------------
class EvidenceReviewCreate(BaseModel):
    decision: ReviewDecisionEnum
    review_notes: Optional[str] = None
    rejection_reason: Optional[str] = None


class EvidenceReviewResponse(BaseModel):
    id: int
    organization_id: int
    evidence_id: int
    reviewer_id: Optional[int] = None
    decision: ReviewDecisionEnum
    review_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    reviewed_at: datetime
    reviewer: Optional[UserResponse] = None

    model_config = ConfigDict(from_attributes=True)


# ----------------------------------------------------
# Evidence Item Schemas
# ----------------------------------------------------
class EvidenceItemUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class EvidenceItemResponse(BaseModel):
    id: int
    organization_id: int
    organization_control_id: int
    evidence_requirement_id: Optional[int] = None
    uploaded_by_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    original_filename: str
    stored_filename: str
    file_extension: str
    content_type: str
    file_size: int
    sha256_hash: str
    status: EvidenceStatusEnum
    superseded_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    uploaded_by: Optional[UserResponse] = None
    requirement_title: Optional[str] = None
    control_identifier: Optional[str] = None
    control_title: Optional[str] = None
    latest_review: Optional[EvidenceReviewResponse] = None

    model_config = ConfigDict(from_attributes=True)


class EvidenceItemDetailResponse(EvidenceItemResponse):
    reviews: List[EvidenceReviewResponse] = []


# ----------------------------------------------------
# Control Assurance & Stats Schemas
# ----------------------------------------------------
class ControlEvidenceSummaryResponse(BaseModel):
    organization_control_id: int
    total_requirements: int
    required_count: int
    submitted_count: int
    accepted_count: int
    rejected_count: int
    pending_count: int
    superseded_count: int
    evidence_coverage_pct: float


class OrganizationEvidenceStatsResponse(BaseModel):
    total_evidence_items: int
    accepted_count: int
    pending_review_count: int
    rejected_count: int
    uploaded_count: int
    superseded_count: int
    overall_coverage_pct: float
    controls_missing_required_evidence: int
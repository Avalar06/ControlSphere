from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.policy import (
    PolicyStatusEnum,
    PolicyTypeEnum,
    PolicyVersionStatusEnum,
    PolicyReviewStageEnum,
    PolicyReviewStatusEnum,
    CampaignTargetTypeEnum,
    CampaignStatusEnum,
    AttestationRecordStatusEnum,
)
from app.schemas.framework import SubcategoryBase
from app.schemas.user import UserResponse


# ── Policy Version Schemas ──────────────────────────────────────────────────

class PolicyVersionCreate(BaseModel):
    content: str = Field(..., min_length=1)
    change_summary: str = Field(..., min_length=1, max_length=255)
    effective_date: Optional[date] = None


class PolicyVersionUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=1)
    change_summary: Optional[str] = Field(None, min_length=1, max_length=255)
    effective_date: Optional[date] = None


class PolicyVersionResponse(BaseModel):
    id: int
    organization_id: Optional[int] = None
    policy_id: int
    version_number: int
    content: str
    content_hash_sha256: Optional[str] = None
    change_summary: str
    status: PolicyVersionStatusEnum = PolicyVersionStatusEnum.DRAFT
    effective_date: Optional[date] = None
    created_by_id: Optional[int] = None
    approved_by_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    created_by: Optional[UserResponse] = None
    approved_by: Optional[UserResponse] = None

    model_config = ConfigDict(from_attributes=True)


# ── Policy Review Workflow Schemas ──────────────────────────────────────────

class PolicyReviewWorkflowCreate(BaseModel):
    review_stage: PolicyReviewStageEnum = PolicyReviewStageEnum.LEGAL_REVIEW
    assigned_reviewer_id: Optional[int] = None
    review_notes: Optional[str] = None


class PolicyReviewWorkflowAction(BaseModel):
    decision: str = Field(..., description="APPROVE, REJECT, or CHANGES_REQUESTED")
    review_notes: Optional[str] = None


class PolicyReviewWorkflowResponse(BaseModel):
    id: int
    organization_id: int
    policy_id: int
    version_id: int
    workflow_code: str
    review_stage: PolicyReviewStageEnum
    status: PolicyReviewStatusEnum
    assigned_reviewer_id: Optional[int] = None
    review_notes: Optional[str] = None
    reviewed_by_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    approved_by_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    created_by_id: Optional[int] = None
    created_at: datetime
    assigned_reviewer: Optional[UserResponse] = None
    reviewed_by: Optional[UserResponse] = None
    approved_by: Optional[UserResponse] = None

    model_config = ConfigDict(from_attributes=True)


# ── Policy Attestation Campaign Schemas ─────────────────────────────────────

class PolicyAttestationCampaignCreate(BaseModel):
    campaign_code: str = Field(..., min_length=2, max_length=64)
    title: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    policy_id: int
    version_id: int
    target_type: CampaignTargetTypeEnum = CampaignTargetTypeEnum.ALL_USERS
    target_role: Optional[str] = None
    due_date: datetime
    grace_period_days: int = 0
    assessment_id: Optional[int] = None


class PolicyAttestationCampaignUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    grace_period_days: Optional[int] = None


class PolicyAttestationCampaignResponse(BaseModel):
    id: int
    organization_id: int
    campaign_code: str
    title: str
    description: Optional[str] = None
    policy_id: int
    version_id: int
    policy_version_hash: str
    target_type: CampaignTargetTypeEnum
    target_role: Optional[str] = None
    due_date: datetime
    grace_period_days: int
    status: CampaignStatusEnum
    assessment_id: Optional[int] = None
    total_targeted_count: int = 0
    completed_count: int = 0
    completion_rate: float = 0.0
    created_by_id: Optional[int] = None
    launched_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    policy_title: Optional[str] = None
    policy_version_number: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


# ── User Attestation Schemas ────────────────────────────────────────────────

class UserAttestationSubmit(BaseModel):
    policy_version_hash: str = Field(..., description="Client verifies hash of policy version being attested")
    acknowledgement_text: Optional[str] = Field(None, max_length=2000)


class UserAttestationRecordResponse(BaseModel):
    id: int
    organization_id: int
    campaign_id: int
    policy_id: int
    version_id: int
    user_id: int
    status: AttestationRecordStatusEnum
    attested_at: Optional[datetime] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    acknowledgement_text: Optional[str] = None
    comprehension_passed: bool = True
    attestation_receipt_hash: Optional[str] = None
    evidence_item_id: Optional[int] = None
    created_at: datetime
    policy_title: Optional[str] = None
    policy_version_number: Optional[int] = None
    campaign_title: Optional[str] = None
    due_date: Optional[datetime] = None
    user_email: Optional[str] = None
    user_full_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CampaignEvidenceManifestResponse(BaseModel):
    campaign_id: int
    campaign_code: str
    evidence_item_id: int
    sha256_hash: str
    status: str
    total_targeted: int
    total_completed: int
    completion_rate: float

    model_config = ConfigDict(from_attributes=True)


# ── Root Policy Schemas ─────────────────────────────────────────────────────

class PolicyBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    policy_type: PolicyTypeEnum = PolicyTypeEnum.INFORMATION_SECURITY
    status: PolicyStatusEnum = PolicyStatusEnum.DRAFT
    owner_id: Optional[int] = None
    effective_date: Optional[date] = None
    review_date: Optional[date] = None


class PolicyCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    policy_type: PolicyTypeEnum = PolicyTypeEnum.INFORMATION_SECURITY
    owner_id: Optional[int] = None
    effective_date: Optional[date] = None
    review_date: Optional[date] = None
    initial_content: str = Field(..., min_length=1, description="Initial markdown content for version 1")
    mapped_subcategory_ids: List[int] = []


class PolicyUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    policy_type: Optional[PolicyTypeEnum] = None
    owner_id: Optional[int] = None
    effective_date: Optional[date] = None
    review_date: Optional[date] = None


class PolicyStatusUpdate(BaseModel):
    status: PolicyStatusEnum
    reason: Optional[str] = None


class PolicyControlMappingCreate(BaseModel):
    subcategory_id: int


class PolicyResponse(PolicyBase):
    id: int
    organization_id: int
    created_at: datetime
    updated_at: datetime
    owner: Optional[UserResponse] = None
    current_version: Optional[PolicyVersionResponse] = None
    total_versions: int = 0
    mapped_subcategories: List[SubcategoryBase] = []

    model_config = ConfigDict(from_attributes=True)
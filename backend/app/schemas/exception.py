from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.exception import ExceptionStatusEnum, ExceptionTypeEnum
from app.schemas.control import OrganizationControlResponse
from app.schemas.finding import FindingResponse
from app.schemas.policy import PolicyResponse
from app.schemas.user import UserResponse


class ExceptionBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    justification: str = Field(..., min_length=5)
    exception_type: ExceptionTypeEnum = ExceptionTypeEnum.CONTROL_DEVIATION
    expiry_date: date
    effective_date: Optional[date] = None
    review_date: Optional[date] = None
    residual_risk_level: str = Field(default="MODERATE")
    owner_id: Optional[int] = None
    reviewer_id: Optional[int] = None

    linked_organization_control_id: Optional[int] = None
    linked_policy_id: Optional[int] = None
    linked_finding_id: Optional[int] = None


class ExceptionCreate(ExceptionBase):
    pass


class ExceptionUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    justification: Optional[str] = Field(None, min_length=5)
    exception_type: Optional[ExceptionTypeEnum] = None
    expiry_date: Optional[date] = None
    effective_date: Optional[date] = None
    review_date: Optional[date] = None
    residual_risk_level: Optional[str] = None
    owner_id: Optional[int] = None
    reviewer_id: Optional[int] = None

    linked_organization_control_id: Optional[int] = None
    linked_policy_id: Optional[int] = None
    linked_finding_id: Optional[int] = None


class ExceptionReviewAction(BaseModel):
    approval_notes: Optional[str] = None
    rejection_reason: Optional[str] = None


class ExceptionClosure(BaseModel):
    closure_notes: str = Field(..., min_length=1)


class ExceptionCompensatingControlCreate(BaseModel):
    organization_control_id: int
    implementation_notes: Optional[str] = None


class ExceptionCompensatingControlResponse(BaseModel):
    id: int
    organization_id: int
    exception_id: int
    organization_control_id: int
    implementation_notes: Optional[str] = None
    created_by_id: Optional[int] = None
    created_at: datetime
    organization_control: Optional[OrganizationControlResponse] = None

    model_config = ConfigDict(from_attributes=True)


class ExceptionResponse(ExceptionBase):
    id: int
    organization_id: int
    status: ExceptionStatusEnum
    effective_status: str  # REQUESTED, UNDER_REVIEW, APPROVED, ACTIVE, EXPIRED, REJECTED, CLOSED

    requested_by_id: Optional[int] = None
    requested_at: datetime
    approved_at: Optional[datetime] = None

    approval_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    closure_notes: Optional[str] = None
    closed_at: Optional[datetime] = None
    closed_by_id: Optional[int] = None

    created_at: datetime
    updated_at: datetime

    requested_by: Optional[UserResponse] = None
    owner: Optional[UserResponse] = None
    reviewer: Optional[UserResponse] = None
    closed_by: Optional[UserResponse] = None

    linked_control: Optional[OrganizationControlResponse] = None
    linked_policy: Optional[PolicyResponse] = None
    linked_finding: Optional[FindingResponse] = None
    compensating_controls_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class ExceptionDetailResponse(ExceptionResponse):
    compensating_controls: List[ExceptionCompensatingControlResponse] = []

    model_config = ConfigDict(from_attributes=True)


class ExceptionStatsResponse(BaseModel):
    total_exceptions: int
    requested_count: int
    under_review_count: int
    active_count: int
    expired_count: int
    rejected_count: int
    closed_count: int
    expiring_soon_count: int  # Expiring in <= 14 days

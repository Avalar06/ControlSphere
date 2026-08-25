from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.policy import PolicyStatusEnum, PolicyTypeEnum
from app.schemas.framework import SubcategoryBase
from app.schemas.user import UserResponse


class PolicyVersionResponse(BaseModel):
    id: int
    policy_id: int
    version_number: int
    content: str
    change_summary: str
    created_by_id: Optional[int] = None
    created_at: datetime
    created_by: Optional[UserResponse] = None

    model_config = ConfigDict(from_attributes=True)


class PolicyVersionCreate(BaseModel):
    content: str = Field(..., min_length=1)
    change_summary: str = Field(..., min_length=1, max_length=255)


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
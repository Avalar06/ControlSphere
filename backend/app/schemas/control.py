from datetime import date, datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.control import ImplementationStatusEnum, PriorityEnum
from app.schemas.framework import SubcategoryBase
from app.schemas.user import UserResponse


class OrganizationControlBase(BaseModel):
    status: ImplementationStatusEnum = ImplementationStatusEnum.NOT_STARTED
    priority: PriorityEnum = PriorityEnum.MEDIUM
    owner_id: Optional[int] = None
    target_date: Optional[date] = None
    review_date: Optional[date] = None
    implementation_statement: Optional[str] = None
    notes: Optional[str] = None


class OrganizationControlUpdate(BaseModel):
    status: Optional[ImplementationStatusEnum] = None
    priority: Optional[PriorityEnum] = None
    owner_id: Optional[int] = None
    target_date: Optional[date] = None
    review_date: Optional[date] = None
    implementation_statement: Optional[str] = None
    notes: Optional[str] = None


class OrganizationControlResponse(OrganizationControlBase):
    id: int
    organization_id: int
    subcategory_id: int
    created_at: datetime
    updated_at: datetime
    subcategory: Optional[SubcategoryBase] = None
    owner: Optional[UserResponse] = None
    function_identifier: Optional[str] = None
    function_name: Optional[str] = None
    category_identifier: Optional[str] = None
    category_name: Optional[str] = None
    mapped_policies_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class FunctionProgressItem(BaseModel):
    name: str
    total: int
    implemented: int
    partially_implemented: int
    in_progress: int
    not_started: int
    score_pct: float


class FrameworkProgressResponse(BaseModel):
    framework_id: int
    framework_identifier: str
    framework_name: str
    total_controls: int
    implemented_count: int
    partially_implemented_count: int
    in_progress_count: int
    not_started_count: int
    not_applicable_count: int
    needs_review_count: int
    compliance_score_pct: float
    by_function: Dict[str, FunctionProgressItem]
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict
from app.core.permissions import RoleEnum
from app.schemas.organization import OrganizationResponse


class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: RoleEnum = RoleEnum.VIEWER
    is_active: bool = True


class UserCreate(UserBase):
    password: str
    organization_id: Optional[int] = None  # Optional in payload; inferred from admin or explicitly assigned


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[RoleEnum] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class UserResponse(UserBase):
    id: int
    organization_id: int
    created_at: datetime
    updated_at: datetime
    organization: Optional[OrganizationResponse] = None

    model_config = ConfigDict(from_attributes=True)


class UserProfileResponse(UserResponse):
    permissions: list[str] = []
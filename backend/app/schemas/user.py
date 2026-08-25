from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict, Field, field_validator
from app.core.permissions import RoleEnum
from app.schemas.organization import OrganizationResponse


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    role: RoleEnum = RoleEnum.VIEWER
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=72, description="Password must be between 8 and 72 characters.")
    organization_id: Optional[int] = None

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password cannot exceed 72 bytes")
        return v


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[RoleEnum] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if len(v.encode("utf-8")) > 72:
                raise ValueError("Password cannot exceed 72 bytes")
        return v


class UserResponse(UserBase):
    id: int
    organization_id: int
    created_at: datetime
    updated_at: datetime
    organization: Optional[OrganizationResponse] = None

    model_config = ConfigDict(from_attributes=True)


class UserProfileResponse(UserResponse):
    permissions: list[str] = []
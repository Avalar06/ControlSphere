from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class SubcategoryBase(BaseModel):
    id: int
    identifier: str
    title: str
    description: str
    display_order: int

    model_config = ConfigDict(from_attributes=True)


class CategoryBase(BaseModel):
    id: int
    identifier: str
    name: str
    description: Optional[str] = None
    display_order: int

    model_config = ConfigDict(from_attributes=True)


class FunctionBase(BaseModel):
    id: int
    identifier: str
    name: str
    description: Optional[str] = None
    display_order: int

    model_config = ConfigDict(from_attributes=True)


class FrameworkBase(BaseModel):
    id: int
    identifier: str
    name: str
    version: str
    description: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CategoryTree(CategoryBase):
    subcategories: List[SubcategoryBase] = []


class FunctionTree(FunctionBase):
    categories: List[CategoryTree] = []


class FrameworkTreeResponse(FrameworkBase):
    functions: List[FunctionTree] = []


class FrameworkResponse(FrameworkBase):
    total_functions: int = 0
    total_categories: int = 0
    total_subcategories: int = 0
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    parent_id: uuid.UUID | None = None
    description: str | None = Field(default=None, max_length=8000)
    sort_order: int = 0
    is_active: bool = True
    slug: str | None = Field(default=None, max_length=180)


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    parent_id: uuid.UUID | None = None
    description: str | None = Field(default=None, max_length=8000)
    sort_order: int | None = None
    is_active: bool | None = None
    slug: str | None = Field(default=None, max_length=180)


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    parent_id: uuid.UUID | None
    name: str
    slug: str
    description: str | None
    sort_order: int
    is_active: bool
    path: str
    created_at: datetime
    updated_at: datetime


class CategoryNode(CategoryOut):
    children: list["CategoryNode"] = Field(default_factory=list)

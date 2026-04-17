"""Pydantic request/response schemas for the custom component editor API."""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class AbstractMethodInfo(BaseModel):
    name: str
    signature: str
    docstring: str


class ClassAttributeInfo(BaseModel):
    name: str
    type: str
    default: Any = None


class BaseClassSummary(BaseModel):
    name: str
    type: str
    import_path: str
    enabled: bool


class BaseClassInfo(BaseClassSummary):
    enabled: bool = True
    docstring: str
    abstract_methods: List[AbstractMethodInfo]
    class_attributes: List[ClassAttributeInfo]
    skeleton: str


class ValidationRequest(BaseModel):
    source_code: str
    class_name: str
    base_class: str


class ValidationResponse(BaseModel):
    ok: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class CustomComponentCreate(BaseModel):
    class_name: str
    base_class: str
    source_code: str
    description: Optional[str] = None


class CustomComponentUpdate(BaseModel):
    class_name: Optional[str] = None
    base_class: Optional[str] = None
    source_code: Optional[str] = None
    description: Optional[str] = None


class CustomComponentResponse(BaseModel):
    id: int
    class_name: str
    base_type: str
    base_class: str
    description: Optional[str]
    source_code: str
    is_override: bool
    created: datetime
    last_modified: datetime

    model_config = {"from_attributes": True}


class ComponentSourceResponse(BaseModel):
    class_name: str
    source_code: str
    base_class: str
    base_type: str
    import_path: Optional[str] = None
    origin: str  # "core" | "plugin" | "custom-override" | "custom"
    editable: bool

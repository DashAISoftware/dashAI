from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from DashAI.back.api.api_v1.schemas.auth_params import RoleSummary


class ProjectCreateParams(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name cannot be empty.")
        return value

    @field_validator("description")
    @classmethod
    def blank_to_none(cls, value: Optional[str]) -> Optional[str]:
        if value is None or not value.strip():
            return None
        return value.strip()


class MemberAddParams(BaseModel):
    # Members are added by their username, which is public, not by email
    username: str = Field(min_length=1, max_length=50)
    role_uid: str = Field(min_length=1, max_length=50)


class MemberRoleParams(BaseModel):
    role_uid: str = Field(min_length=1, max_length=50)


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created: datetime
    member_count: int
    # The current user's role in the project; None for an administrator who
    # is not a member
    my_role: Optional[RoleSummary]
    # What the current user can do inside the project, so the frontend can
    # hide what is not allowed
    my_permissions: List[str]


class MemberResponse(BaseModel):
    user_id: int
    username: str
    social_name: str
    role: RoleSummary
    joined: datetime

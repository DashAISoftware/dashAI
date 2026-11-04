from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from DashAI.back.auth.passwords import validate_password_length

MIN_PASSWORD_LENGTH = 8

# Letters, digits, dots, dashes and underscores, as in "@username"
USERNAME_PATTERN = r"^[A-Za-z0-9_.-]+$"
# Loose check: something@something.something, without spaces
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


def _check_password(value: str) -> str:
    validate_password_length(value)
    return value


class RegisterParams(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=USERNAME_PATTERN)
    email: str = Field(max_length=255, pattern=EMAIL_PATTERN)
    password: str = Field(min_length=MIN_PASSWORD_LENGTH)
    social_name: str = Field(min_length=1, max_length=100)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("social_name")
    @classmethod
    def strip_social_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name cannot be empty.")
        return value

    @field_validator("password")
    @classmethod
    def check_password(cls, value: str) -> str:
        return _check_password(value)


class LoginParams(BaseModel):
    # Either the email or the username
    identifier: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=255)


class ChangePasswordParams(BaseModel):
    current_password: str = Field(min_length=1, max_length=255)
    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH)

    @field_validator("new_password")
    @classmethod
    def check_password(cls, value: str) -> str:
        return _check_password(value)


class ProfileUpdateParams(BaseModel):
    """Fields the user can edit; only the ones sent are changed."""

    social_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    bio: Optional[str] = Field(default=None, max_length=1000)
    phone: Optional[str] = Field(default=None, max_length=30)
    github: Optional[str] = Field(default=None, max_length=255)
    linkedin: Optional[str] = Field(default=None, max_length=255)

    @field_validator("social_name")
    @classmethod
    def check_social_name(cls, value: Optional[str]) -> str:
        # The column is required: it can be changed but not cleared
        if value is None or not value.strip():
            raise ValueError("Name cannot be empty.")
        return value.strip()

    @field_validator("bio", "phone", "github", "linkedin")
    @classmethod
    def blank_to_none(cls, value: Optional[str]) -> Optional[str]:
        # An emptied form field clears the value
        if value is None or not value.strip():
            return None
        return value.strip()


class RoleSummary(BaseModel):
    uid: str
    name: str


class UserResponse(BaseModel):
    """The logged-in user as seen by the frontend.

    Never includes the password hash or the token version.
    """

    id: int
    username: str
    email: str
    social_name: str
    bio: Optional[str]
    phone: Optional[str]
    github: Optional[str]
    linkedin: Optional[str]
    legal_name: Optional[str]
    organization: Optional[str]
    position: Optional[str]
    global_role: RoleSummary
    permissions: List[str]
    last_login: Optional[datetime]
    created: datetime

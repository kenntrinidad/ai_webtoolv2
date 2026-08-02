"""Pydantic contracts for user management API requests and responses."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

UserRole = Literal["admin", "user"]
UserStatus = Literal["active", "inactive"]


class UserCreate(BaseModel):
    """Payload required to create a user account."""

    username: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=5, max_length=320)
    full_name: str | None = Field(default=None, max_length=200)
    password: str = Field(min_length=12, max_length=1024)
    role: UserRole = "user"
    status: UserStatus = "active"
    must_change_password: bool | None = None


class UserUpdate(BaseModel):
    """Fields used to update an existing user account."""

    username: str | None = Field(default=None, min_length=1, max_length=120)
    email: str | None = Field(default=None, min_length=5, max_length=320)
    full_name: str | None = Field(default=None, max_length=200)
    password: str | None = Field(default=None, min_length=12, max_length=1024)
    role: UserRole | None = None
    status: UserStatus | None = None
    must_change_password: bool | None = None


class UserRead(BaseModel):
    """Account representation returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    email: str
    full_name: str | None
    role: UserRole
    status: UserStatus
    must_change_password: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None

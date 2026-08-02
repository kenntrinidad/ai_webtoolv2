"""Request and response schemas for session authentication."""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Credentials accepted by the login endpoint."""

    identifier: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=1024)


class PasswordChangeRequest(BaseModel):
    """Current and replacement credentials for an authenticated account."""

    current_password: str = Field(min_length=1, max_length=1024)
    new_password: str = Field(min_length=12, max_length=1024)


class AuthenticatedUserRead(BaseModel):
    """Safe account data returned to an authenticated browser."""

    id: str
    username: str
    email: str
    full_name: str | None
    role: str
    status: str
    must_change_password: bool

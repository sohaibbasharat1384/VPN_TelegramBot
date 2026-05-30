"""Authentication request/response schemas."""
from __future__ import annotations

from pydantic import EmailStr, Field

from app.schemas.base import APIModel


class LoginRequest(APIModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(APIModel):
    refresh_token: str


class TokenPair(APIModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # access-token lifetime in seconds


class AdminProfile(APIModel):
    id: int
    email: str | None
    telegram_id: int | None
    full_name: str
    role: str
    permissions: list[str]
    is_active: bool

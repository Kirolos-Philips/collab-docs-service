"""Pydantic schemas for auth module."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for user registration."""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=100)


class UserLogin(BaseModel):
    """Schema for user login."""

    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """Schema for partial user profile update."""

    username: str | None = Field(None, min_length=3, max_length=50)


class UserResponse(BaseModel):
    """Schema for user response (no sensitive data)."""

    id: str
    email: EmailStr
    username: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    avatar_url: str | None = None


class Token(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """JWT token payload."""

    sub: str  # user_id
    exp: datetime | None = None


class VerifyEmailRequest(BaseModel):
    """Schema for email verification."""

    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)


class ForgotPasswordRequest(BaseModel):
    """Schema for forgot password request."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Schema for reset password request."""

    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=8, max_length=100)

"""User schemas — request/response models for auth endpoints."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for user registration."""

    email: str = Field(..., min_length=5, max_length=255, examples=["user@example.com"])
    password: str = Field(..., min_length=8, max_length=128, examples=["strongpassword123"])


class UserLogin(BaseModel):
    """Schema for user login."""

    email: str = Field(..., examples=["user@example.com"])
    password: str = Field(..., examples=["strongpassword123"])


class UserResponse(BaseModel):
    """Schema for returning user data (no password)."""

    id: int
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"

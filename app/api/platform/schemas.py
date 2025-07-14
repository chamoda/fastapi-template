from __future__ import annotations
import re
from pydantic import EmailStr, UUID4, Field, field_validator

from app.schemas import Model, DateTime, Password


class AuthRequest(Model):
    email: EmailStr
    password: str


class AuthResponse(Model):
    access_token: str


class RegistrationRequest(Model):
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    email: EmailStr
    password: Password

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Name cannot be empty or whitespace only")
        # Remove excessive whitespace and validate characters
        cleaned = re.sub(r"\s+", " ", v.strip())
        if not re.match(r"^[a-zA-Z\s\'-]+$", cleaned):
            raise ValueError(
                "Name can only contain letters, spaces, hyphens, and apostrophes"
            )
        return cleaned


class RegistrationResponse(Model):
    id: UUID4


class RegistrationEmailVerificationVerifyRequest(Model):
    code: str


class UserResponse(Model):
    id: UUID4
    created_at: DateTime
    updated_at: DateTime | None
    first_name: str
    last_name: str
    email: str


class ForgotPasswordRequest(Model):
    email: EmailStr


class ResetPasswordRequest(Model):
    token: str
    password: Password

import re
from datetime import UTC
from typing import Annotated, Any
from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    WrapSerializer,
    SecretStr,
    Field,
    field_validator,
)

DateTime = Annotated[
    AwareDatetime,
    WrapSerializer(
        lambda v, nxt: nxt(v.astimezone(UTC)).replace("+00:00", "Z"),
        when_used="json",
    ),
]


class Model(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, from_attributes=True)


class MessageResponse(Model):
    message: str


class ErrorDetail(Model):
    code: str
    message: str
    field: str | None = None
    details: dict[str, Any] | None = None


class ErrorResponse(Model):
    error: ErrorDetail


class HealthCheckResponse(Model):
    status: str  # "healthy" or "unhealthy"


def validate_password_strength(password: str) -> str:
    """Validate password meets security requirements."""
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if len(password) > 128:
        raise ValueError("Password must be no more than 128 characters long")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValueError("Password must contain at least one special character")
    return password


# Custom password field with validation
Password = Annotated[
    SecretStr,
    Field(min_length=8, max_length=128),
    field_validator("password", mode="before")(
        lambda v: (
            validate_password_strength(
                v.get_secret_value() if isinstance(v, SecretStr) else v
            )
            and v
        )
    ),
]

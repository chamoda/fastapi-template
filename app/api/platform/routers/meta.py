from datetime import datetime, timedelta
from fastapi import APIRouter, Response, status, Request
from fastapi_mail import MessageSchema, MessageType
from sqlalchemy import select, text

from app.api.platform.schemas import (
    AuthRequest,
    AuthResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from app.schemas import HealthCheckResponse, MessageResponse
from app.exceptions import (
    APIException,
    ResourceNotFoundException,
    ValidationException,
    ExpiredException,
)
from app.security import (
    verify_password,
    generate_jwt_token,
    generate_token,
    hash_password,
)
from app.models import User, PasswordResetToken
from app.database import DBSession
from app.config import settings
from app.logging import logging
from app.notifications import send_mail
from app.limiter import limiter
from app.utils import templates

router = APIRouter()


@router.get("/health")
async def health(session: DBSession, response: Response) -> HealthCheckResponse:
    try:
        # Check database connectivity
        await session.execute(text("SELECT 1"))
        return HealthCheckResponse(status="healthy")

    except Exception as e:
        # Log error internally but don't expose details
        logging.error(f"Health check failed: {e}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthCheckResponse(status="unhealthy")


@router.post("/auth")
async def auth(
    auth_request: AuthRequest, session: DBSession, response: Response
) -> AuthResponse:
    result = await session.execute(
        select(User).where(
            User.email == auth_request.email.lower(),
        )
    )
    user = result.scalars().first()

    if user:
        if verify_password(auth_request.password, user.password):
            access_token = generate_jwt_token({"sub": str(user.id)})
            response.set_cookie(
                key="access_token",
                value=f"Bearer {access_token}",
                samesite="lax",
                secure=settings.SECURE_COOKIE,
                httponly=True,
                max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert to seconds
            )
            return AuthResponse(access_token=access_token)
    raise APIException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        code="INVALID_CREDENTIALS",
        message="Incorrect username or password",
    )


@router.post("/logout")
async def logout(response: Response) -> MessageResponse:
    response.delete_cookie("access_token")
    return MessageResponse(message="Successfully logged out")


@router.post("/auth/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(
    request: Request, forgot_request: ForgotPasswordRequest, session: DBSession
) -> MessageResponse:
    normalized_email = forgot_request.email.lower()

    # Check if user exists
    result = await session.execute(
        select(User).where(User.email == normalized_email, User.is_active)
    )
    user = result.scalars().first()

    if not user:
        # Return success even if user doesn't exist for security
        return MessageResponse(
            message="If an account with this email exists, a reset link has been sent"
        )

    # Generate reset token
    reset_token = PasswordResetToken(user_id=user.id, token=generate_token(32))
    session.add(reset_token)
    await session.commit()

    # Send email
    reset_url = f"{settings.PLATFORM_URL}/reset-password?token={reset_token.token}"
    await send_mail(
        MessageSchema(
            recipients=[user.email],
            subject="AlmaStack: Password Reset Request",
            body=templates.get_template("reset_password.txt").render(
                first_name=user.first_name, reset_url=reset_url
            ),
            subtype=MessageType.plain,
        )
    )

    return MessageResponse(
        message="If an account with this email exists, a reset link has been sent"
    )


@router.post("/auth/reset-password")
async def reset_password(
    reset_request: ResetPasswordRequest, session: DBSession
) -> MessageResponse:
    # Find the reset token
    result = await session.execute(
        select(PasswordResetToken)
        .where(
            PasswordResetToken.token == reset_request.token,
            PasswordResetToken.used_at.is_(None),
        )
        .join(User)
    )
    reset_token = result.scalars().first()

    if not reset_token:
        raise ValidationException(
            message="Invalid or expired reset token", field="token"
        )

    # Check if token is expired (1 hour)
    if reset_token.created_at + timedelta(hours=1) < datetime.utcnow():
        raise ExpiredException(message="Reset token has expired")

    # Update user password
    user_result = await session.execute(
        select(User).where(User.id == reset_token.user_id)
    )
    user = user_result.scalars().first()

    if not user:
        raise ResourceNotFoundException(message="User not found")

    # Hash and update password
    user.password = hash_password(reset_request.password.get_secret_value())

    # Mark token as used
    reset_token.used_at = datetime.utcnow()

    await session.commit()

    return MessageResponse(message="Password has been reset successfully")

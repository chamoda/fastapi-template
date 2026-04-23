from datetime import datetime, timedelta
import hmac
from fastapi import (
    APIRouter,
    Response,
    status,
    Request,
)
from fastapi_mail import MessageSchema, MessageType
from pydantic import UUID4, NameEmail
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import DBSession
from app.models import Registration, RegistrationEmailVerification, User
from app.notifications import send_mail
from app.limiter import limiter

from app.api.platform.schemas import (
    AuthResponse,
    RegistrationRequest,
    RegistrationResponse,
    RegistrationEmailVerificationVerifyRequest,
)
from app.schemas import MessageResponse
from app.exceptions import (
    DuplicateResourceException,
    ResourceNotFoundException,
    ValidationException,
    RateLimitException,
    ExpiredException,
)
from app.utils import templates
from app.security import generate_code, generate_jwt_token
from app.config import settings
from app.security import hash_password


router = APIRouter()


@router.post("/registrations", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def registration_create(
    request: Request, registration_request: RegistrationRequest, session: DBSession
) -> RegistrationResponse:
    normalized_email = registration_request.email.lower()

    result = await session.execute(
        select(User.email).where(User.email == normalized_email)
    )
    if result.scalars().first():
        raise DuplicateResourceException(
            message="An account already exists with this email address", field="email"
        )

    registration = Registration(
        first_name=registration_request.first_name,
        last_name=registration_request.last_name,
        email=normalized_email,
        password=hash_password(registration_request.password.get_secret_value()),
    )
    session.add(registration)
    await session.commit()

    return RegistrationResponse.model_validate(registration)


@router.post("/registrations/{registration_id}/email-verifications")
async def create_email_verification(
    registration_id: UUID4, session: DBSession
) -> MessageResponse:
    # First get the registration to check the email
    registration_result = await session.execute(
        select(Registration).where(Registration.id == registration_id)
    )
    registration = registration_result.scalars().first()
    if not registration:
        raise ResourceNotFoundException(message="Registration not found")

    # Check for recent verification requests by registration ID (rate limiting)
    recent_requests = await session.execute(
        select(RegistrationEmailVerification).where(
            RegistrationEmailVerification.registration_id == registration_id,
            RegistrationEmailVerification.created_at + timedelta(minutes=1)
            >= datetime.utcnow(),
        )
    )
    if recent_requests.scalars().first():
        raise RateLimitException(
            message="Please wait at least 1 minute before requesting another verification code"
        )

    # Check for recent verification requests by email across all registrations
    recent_email_requests = await session.execute(
        select(RegistrationEmailVerification)
        .join(Registration)
        .where(
            Registration.email == registration.email,
            RegistrationEmailVerification.created_at + timedelta(minutes=1)
            >= datetime.utcnow(),
        )
    )
    if recent_email_requests.scalars().first():
        raise RateLimitException(
            message="Too many verification requests for this email address. Please wait before trying again"
        )

    # Check for existing valid verification
    result = await session.execute(
        select(RegistrationEmailVerification)
        .where(
            RegistrationEmailVerification.registration_id == registration_id,
            RegistrationEmailVerification.verified.is_(False),
            RegistrationEmailVerification.created_at + timedelta(minutes=5)
            >= datetime.utcnow(),
        )
        .options(selectinload(RegistrationEmailVerification.registration))
    )
    registration_email_verification = result.scalars().first()

    if not registration_email_verification:
        registration_email_verification = RegistrationEmailVerification()
        registration_email_verification.registration_id = registration_id
        registration_email_verification.code = generate_code()
        registration_email_verification.attempt_count = 0
        session.add(registration_email_verification)
        await session.commit()
        await session.refresh(registration_email_verification, ["registration"])

    await send_mail(
        MessageSchema(
            recipients=[
                NameEmail(
                    name=registration_email_verification.registration.first_name,
                    email=registration_email_verification.registration.email,
                )
            ],
            subject="Email Verification Code",
            body=templates.get_template("verify_email.txt").render(
                code=registration_email_verification.code,
                first_name=registration_email_verification.registration.first_name,
            ),
            subtype=MessageType.plain,
        )
    )

    return MessageResponse(message="Email verification code sent successfully")


@router.put("/registrations/{registration_id}/email-verifications/current")
async def update_email_verification(
    registration_id: UUID4,
    verification_request: RegistrationEmailVerificationVerifyRequest,
    session: DBSession,
    response: Response,
) -> AuthResponse:
    result = await session.execute(
        select(RegistrationEmailVerification)
        .where(
            RegistrationEmailVerification.registration_id == registration_id,
            RegistrationEmailVerification.verified.is_(False),
        )
        .options(selectinload(RegistrationEmailVerification.registration))
        .order_by(RegistrationEmailVerification.created_at.desc())
    )
    registration_email_verification = result.scalars().first()

    if not registration_email_verification:
        raise ResourceNotFoundException(message="No pending verification found")

    # Check if attempt count should be reset (after 5 minutes cooldown)
    if (
        registration_email_verification.last_attempt_at
        and registration_email_verification.last_attempt_at + timedelta(minutes=5)
        <= datetime.utcnow()
    ):
        registration_email_verification.attempt_count = 0
        await session.commit()

    if registration_email_verification.attempt_count >= 5:
        cooldown_remaining = None
        if registration_email_verification.last_attempt_at:
            cooldown_end = registration_email_verification.last_attempt_at + timedelta(
                minutes=5
            )
            if cooldown_end > datetime.utcnow():
                cooldown_remaining = cooldown_end - datetime.utcnow()

        message = "Maximum verification attempts exceeded."
        if cooldown_remaining:
            minutes_left = int(cooldown_remaining.total_seconds() / 60) + 1
            message += f" Please wait {minutes_left} more minute(s) to try again."
        else:
            message += " Please wait 5 minutes before trying again."

        raise RateLimitException(message=message)

    if (
        registration_email_verification.created_at + timedelta(minutes=5)
        < datetime.utcnow()
    ):
        raise ExpiredException(message="Verification code has expired")

    # Use constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(
        registration_email_verification.code, verification_request.code
    ):
        registration_email_verification.attempt_count += 1
        registration_email_verification.last_attempt_at = datetime.utcnow()
        await session.commit()
        raise ValidationException(message="Invalid verification code", field="code")

    registration_email_verification.verified = True
    registration_email_verification.verified_at = datetime.utcnow()
    await session.commit()

    user = User()
    user.first_name = registration_email_verification.registration.first_name
    user.last_name = registration_email_verification.registration.last_name
    user.email = registration_email_verification.registration.email
    user.password = registration_email_verification.registration.password
    user.is_active = True
    session.add(user)

    await session.commit()

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

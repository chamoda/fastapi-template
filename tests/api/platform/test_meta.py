import pytest
from faker import Faker
from datetime import datetime, timedelta
from sqlalchemy import select
from app.security import hash_password, generate_token
from app.models import User, PasswordResetToken

fake = Faker()


@pytest.mark.asyncio
async def test_health_endpoint_healthy(async_client):
    """Test health endpoint returns healthy status when database is accessible."""
    response = await async_client.get("/platform/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_auth_success(async_client):
    """Test successful authentication with valid credentials."""
    # Create a test user directly (not via registration which creates Registration, not User)
    email = fake.email().lower()
    password = "testpassword123"

    # Create User directly for authentication testing
    async with getattr(async_client, "test_session_factory")() as db:
        user = User(
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            email=email,
            password=hash_password(password),
            is_active=True,
        )
        db.add(user)
        await db.commit()

    # Test authentication
    auth_data = {"email": email, "password": password}
    response = await async_client.post("/platform/auth", json=auth_data)

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data


@pytest.mark.asyncio
async def test_auth_invalid_email(async_client):
    """Test authentication fails with non-existent email."""
    auth_data = {"email": "nonexistent@example.com", "password": "anypassword"}

    response = await async_client.post("/platform/auth", json=auth_data)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_auth_invalid_password(async_client):
    """Test authentication fails with wrong password."""
    # Create a test user
    email = fake.email().lower()
    password = "correctpassword"

    async with getattr(async_client, "test_session_factory")() as db:
        user = User(
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            email=email,
            password=hash_password(password),
            is_active=True,
        )
        db.add(user)
        await db.commit()

    # Test with wrong password
    auth_data = {"email": email, "password": "wrongpassword"}

    response = await async_client.post("/platform/auth", json=auth_data)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_auth_missing_fields(async_client):
    """Test authentication fails with missing required fields."""
    auth_data = {
        "email": fake.email()
        # Missing password
    }

    response = await async_client.post("/platform/auth", json=auth_data)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_auth_invalid_email_format(async_client):
    """Test authentication fails with invalid email format."""
    auth_data = {"email": "invalid-email", "password": "somepassword"}

    response = await async_client.post("/platform/auth", json=auth_data)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_logout_success(async_client):
    """Test successful logout."""
    response = await async_client.post("/platform/logout")

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Successfully logged out"


@pytest.mark.asyncio
async def test_forgot_password_success(async_client, mock_email_service):
    """Test successful forgot password request."""
    # Create a test user
    email = fake.email().lower()

    async with getattr(async_client, "test_session_factory")() as db:
        user = User(
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            email=email,
            password=hash_password("testpassword123"),
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        user_id = user.id

    # Request password reset
    forgot_data = {"email": email}
    response = await async_client.post(
        "/platform/auth/forgot-password", json=forgot_data
    )

    assert response.status_code == 200
    data = response.json()
    assert (
        data["message"]
        == "If an account with this email exists, a reset link has been sent"
    )

    # Note: Email sending is mocked in tests, we focus on API behavior

    # Verify token was created in database
    async with getattr(async_client, "test_session_factory")() as db:
        result = await db.execute(
            select(PasswordResetToken).where(PasswordResetToken.user_id == user_id)
        )
        token = result.scalars().first()
        assert token is not None
        assert token.used_at is None


@pytest.mark.asyncio
async def test_forgot_password_nonexistent_email(async_client, mock_email_service):
    """Test forgot password with non-existent email returns success (security)."""
    forgot_data = {"email": "nonexistent@example.com"}
    response = await async_client.post(
        "/platform/auth/forgot-password", json=forgot_data
    )

    assert response.status_code == 200
    data = response.json()
    assert (
        data["message"]
        == "If an account with this email exists, a reset link has been sent"
    )

    # Verify no email was sent
    mock_email_service.assert_not_called()


@pytest.mark.asyncio
async def test_forgot_password_inactive_user(async_client, mock_email_service):
    """Test forgot password with inactive user returns success but no email sent."""
    # Create an inactive test user
    email = fake.email().lower()

    async with getattr(async_client, "test_session_factory")() as db:
        user = User(
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            email=email,
            password=hash_password("testpassword123"),
            is_active=False,  # Inactive user
        )
        db.add(user)
        await db.commit()

    # Request password reset
    forgot_data = {"email": email}
    response = await async_client.post(
        "/platform/auth/forgot-password", json=forgot_data
    )

    assert response.status_code == 200
    data = response.json()
    assert (
        data["message"]
        == "If an account with this email exists, a reset link has been sent"
    )

    # Verify no email was sent (user is inactive)
    mock_email_service.assert_not_called()


@pytest.mark.asyncio
async def test_forgot_password_invalid_email_format(async_client):
    """Test forgot password with invalid email format."""
    forgot_data = {"email": "invalid-email"}
    response = await async_client.post(
        "/platform/auth/forgot-password", json=forgot_data
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_reset_password_success(async_client):
    """Test successful password reset."""
    # Create a test user
    email = fake.email().lower()
    original_password = "originalpassword123"
    new_password = "NewP@ssw0rd123"

    async with getattr(async_client, "test_session_factory")() as db:
        user = User(
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            email=email,
            password=hash_password(original_password),
            is_active=True,
        )
        db.add(user)
        await db.commit()

        # Create a reset token
        reset_token = PasswordResetToken(
            user_id=user.id, token=generate_token(32), created_at=datetime.utcnow()
        )
        db.add(reset_token)
        await db.commit()

    # Reset password
    reset_data = {"token": reset_token.token, "password": new_password}
    response = await async_client.post("/platform/auth/reset-password", json=reset_data)

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Password has been reset successfully"

    # Verify token is marked as used
    async with getattr(async_client, "test_session_factory")() as db:
        result = await db.execute(
            select(PasswordResetToken).where(PasswordResetToken.id == reset_token.id)
        )
        updated_token = result.scalars().first()
        assert updated_token.used_at is not None

        # Verify password was actually changed (database check not needed for this test)

    # Test authentication with new password
    auth_data = {"email": email, "password": new_password}
    auth_response = await async_client.post("/platform/auth", json=auth_data)
    assert auth_response.status_code == 200


@pytest.mark.asyncio
async def test_reset_password_invalid_token(async_client):
    """Test password reset with invalid token."""
    reset_data = {"token": "invalid-token-12345", "password": "NewP@ssw0rd123"}
    response = await async_client.post("/platform/auth/reset-password", json=reset_data)

    assert response.status_code == 400
    data = response.json()
    assert "invalid or expired reset token" in data["error"]["message"].lower()


@pytest.mark.asyncio
async def test_reset_password_expired_token(async_client):
    """Test password reset with expired token."""
    # Create a test user
    email = fake.email().lower()

    async with getattr(async_client, "test_session_factory")() as db:
        user = User(
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            email=email,
            password=hash_password("testpassword123"),
            is_active=True,
        )
        db.add(user)
        await db.commit()

        # Create an expired reset token (created 2 hours ago)
        reset_token = PasswordResetToken(
            user_id=user.id,
            token=generate_token(32),
            created_at=datetime.utcnow() - timedelta(hours=2),
        )
        db.add(reset_token)
        await db.commit()

    # Try to reset password with expired token
    reset_data = {"token": reset_token.token, "password": "NewP@ssw0rd123"}
    response = await async_client.post("/platform/auth/reset-password", json=reset_data)

    assert response.status_code == 410
    data = response.json()
    assert "expired" in data["error"]["message"].lower()


@pytest.mark.asyncio
async def test_reset_password_used_token(async_client):
    """Test password reset with already used token."""
    # Create a test user
    email = fake.email().lower()

    async with getattr(async_client, "test_session_factory")() as db:
        user = User(
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            email=email,
            password=hash_password("testpassword123"),
            is_active=True,
        )
        db.add(user)
        await db.commit()

        # Create a used reset token
        reset_token = PasswordResetToken(
            user_id=user.id,
            token=generate_token(32),
            created_at=datetime.utcnow(),
            used_at=datetime.utcnow(),  # Already used
        )
        db.add(reset_token)
        await db.commit()

    # Try to reset password with used token
    reset_data = {"token": reset_token.token, "password": "NewP@ssw0rd123"}
    response = await async_client.post("/platform/auth/reset-password", json=reset_data)

    assert response.status_code == 400
    data = response.json()
    assert "invalid or expired reset token" in data["error"]["message"].lower()


@pytest.mark.asyncio
async def test_reset_password_weak_password(async_client):
    """Test password reset with weak password."""
    # Create a test user and token
    email = fake.email().lower()

    async with getattr(async_client, "test_session_factory")() as db:
        user = User(
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            email=email,
            password=hash_password("testpassword123"),
            is_active=True,
        )
        db.add(user)
        await db.commit()

        reset_token = PasswordResetToken(
            user_id=user.id, token=generate_token(32), created_at=datetime.utcnow()
        )
        db.add(reset_token)
        await db.commit()

    # Try to reset with weak password
    reset_data = {
        "token": reset_token.token,
        "password": "weak",  # Doesn't meet password requirements
    }
    response = await async_client.post("/platform/auth/reset-password", json=reset_data)

    assert response.status_code == 422

import pytest
from datetime import datetime, timedelta
from faker import Faker
from app.models import RegistrationEmailVerification, User

fake = Faker()


@pytest.mark.asyncio
async def test_registration_create_success(async_client):
    """Test successful user registration."""
    registration_data = {
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "email": fake.unique.email(),
        "password": "OhIZ$I3v$bhA^8DZ",
    }

    response = await async_client.post(
        "/platform/registrations", json=registration_data
    )

    assert response.status_code == 201
    data = response.json()
    assert "id" in data


@pytest.mark.asyncio
async def test_registration_create_invalid_email(async_client):
    """Test registration fails with invalid email."""
    registration_data = {
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "email": "invalid-email",
        "password": "test_password123",
    }

    response = await async_client.post(
        "/platform/registrations", json=registration_data
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_registration_create_short_password(async_client):
    """Test registration fails with password too short."""
    registration_data = {
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "email": fake.unique.email(),
        "password": "short",
    }

    response = await async_client.post(
        "/platform/registrations", json=registration_data
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_registration_missing_fields(async_client):
    """Test registration fails with missing required fields."""
    incomplete_data = {
        "first_name": fake.first_name(),
        # Missing last_name, email, password
    }

    response = await async_client.post("/platform/registrations", json=incomplete_data)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_registration_empty_fields(async_client):
    """Test registration fails with empty required fields."""
    empty_data = {"first_name": "", "last_name": "", "email": "", "password": ""}

    response = await async_client.post("/platform/registrations", json=empty_data)
    assert response.status_code == 422


# Email Verification Tests


@pytest.mark.asyncio
async def test_email_verification_create_success(async_client):
    """Test successful email verification creation."""
    # First create a registration
    registration_data = {
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "email": fake.unique.email(),
        "password": "TestPassword123!",
    }

    reg_response = await async_client.post(
        "/platform/registrations", json=registration_data
    )
    assert reg_response.status_code == 201
    registration_id = reg_response.json()["id"]

    # Create email verification
    response = await async_client.post(
        f"/platform/registrations/{registration_id}/email-verifications"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Email verification code sent successfully"


@pytest.mark.asyncio
async def test_email_verification_create_nonexistent_registration(async_client):
    """Test email verification creation for non-existent registration."""
    fake_registration_id = "550e8400-e29b-41d4-a716-446655440000"

    response = await async_client.post(
        f"/platform/registrations/{fake_registration_id}/email-verifications"
    )

    assert response.status_code == 404
    data = response.json()
    assert "error" in data


@pytest.mark.asyncio
async def test_email_verification_create_rate_limit_registration(async_client):
    """Test rate limiting for email verification creation per registration."""
    # Create a registration
    registration_data = {
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "email": fake.unique.email(),
        "password": "TestPassword123!",
    }

    reg_response = await async_client.post(
        "/platform/registrations", json=registration_data
    )
    registration_id = reg_response.json()["id"]

    # Create first email verification
    response1 = await async_client.post(
        f"/platform/registrations/{registration_id}/email-verifications"
    )
    assert response1.status_code == 200

    # Try to create another immediately (should be rate limited)
    response2 = await async_client.post(
        f"/platform/registrations/{registration_id}/email-verifications"
    )
    assert response2.status_code == 429  # Too Many Requests
    data = response2.json()
    assert "error" in data


@pytest.mark.asyncio
async def test_email_verification_reuse_existing_valid_code(async_client):
    """Test reusing existing valid verification code."""
    # Create registration and initial verification
    registration_data = {
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "email": fake.unique.email(),  # Use unique email to avoid rate limiting
        "password": "TestPassword123!",
    }

    reg_response = await async_client.post(
        "/platform/registrations", json=registration_data
    )
    registration_id = reg_response.json()["id"]

    # Create first verification
    response1 = await async_client.post(
        f"/platform/registrations/{registration_id}/email-verifications"
    )
    assert response1.status_code == 200

    # Manually expire the rate limit and create another
    async with getattr(async_client, "test_session_factory")() as db:
        from sqlalchemy import update

        # Update the creation time to be more than 1 minute ago to bypass rate limit
        await db.execute(
            update(RegistrationEmailVerification)
            .where(RegistrationEmailVerification.registration_id == registration_id)
            .values(created_at=datetime.utcnow() - timedelta(minutes=2))
        )
        await db.commit()

    # Try to create another verification - should reuse existing valid code
    response2 = await async_client.post(
        f"/platform/registrations/{registration_id}/email-verifications"
    )
    assert response2.status_code == 200
    data = response2.json()
    assert data["message"] == "Email verification code sent successfully"


@pytest.mark.asyncio
async def test_email_verification_verify_success(async_client):
    """Test successful email verification with correct code."""
    # Create registration and verification
    registration_data = {
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "email": fake.unique.email(),
        "password": "TestPassword123!",
    }

    reg_response = await async_client.post(
        "/platform/registrations", json=registration_data
    )
    registration_id = reg_response.json()["id"]

    await async_client.post(
        f"/platform/registrations/{registration_id}/email-verifications"
    )

    # Get the verification code from the database since response is 204 No Content
    async with getattr(async_client, "test_session_factory")() as db:
        from sqlalchemy import select

        result = await db.execute(
            select(RegistrationEmailVerification).where(
                RegistrationEmailVerification.registration_id == registration_id
            )
        )
        verification = result.scalar_one()
        verification_code = verification.code

    # Verify with correct code
    verify_data = {"code": verification_code}
    response = await async_client.put(
        f"/platform/registrations/{registration_id}/email-verifications/current",
        json=verify_data,
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data

    # Check that a User was created
    async with getattr(async_client, "test_session_factory")() as db:
        from sqlalchemy import select

        result = await db.execute(
            select(User).where(User.email == registration_data["email"])
        )
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.is_active is True


@pytest.mark.asyncio
async def test_email_verification_verify_invalid_code(async_client):
    """Test email verification with invalid code."""
    # Create registration and verification
    registration_data = {
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "email": fake.unique.email(),
        "password": "TestPassword123!",
    }

    reg_response = await async_client.post(
        "/platform/registrations", json=registration_data
    )
    registration_id = reg_response.json()["id"]

    await async_client.post(
        f"/platform/registrations/{registration_id}/email-verifications"
    )

    # Verify with incorrect code
    verify_data = {"code": "WRONGCOD"}
    response = await async_client.put(
        f"/platform/registrations/{registration_id}/email-verifications/current",
        json=verify_data,
    )

    assert response.status_code == 400
    data = response.json()
    assert "error" in data


@pytest.mark.asyncio
async def test_email_verification_verify_expired_code(async_client):
    """Test email verification with expired code."""
    # Create registration and verification
    registration_data = {
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "email": fake.unique.email(),
        "password": "TestPassword123!",
    }

    reg_response = await async_client.post(
        "/platform/registrations", json=registration_data
    )
    registration_id = reg_response.json()["id"]

    await async_client.post(
        f"/platform/registrations/{registration_id}/email-verifications"
    )

    # Get the verification code and expire it
    async with getattr(async_client, "test_session_factory")() as db:
        from sqlalchemy import select

        result = await db.execute(
            select(RegistrationEmailVerification).where(
                RegistrationEmailVerification.registration_id == registration_id
            )
        )
        verification = result.scalar_one()
        verification_code = verification.code

    # Manually expire the verification code
    async with getattr(async_client, "test_session_factory")() as db:
        from sqlalchemy import select, update

        # Update the creation time to be more than 5 minutes ago
        await db.execute(
            update(RegistrationEmailVerification)
            .where(RegistrationEmailVerification.registration_id == registration_id)
            .values(created_at=datetime.utcnow() - timedelta(minutes=6))
        )
        await db.commit()

    # Try to verify with expired code
    verify_data = {"code": verification_code}
    response = await async_client.put(
        f"/platform/registrations/{registration_id}/email-verifications/current",
        json=verify_data,
    )

    assert response.status_code == 410  # Gone (expired)
    data = response.json()
    assert "error" in data


@pytest.mark.asyncio
async def test_email_verification_verify_attempt_limit(async_client):
    """Test email verification attempt count limit."""
    # Create registration and verification
    registration_data = {
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "email": fake.unique.email(),
        "password": "TestPassword123!",
    }

    reg_response = await async_client.post(
        "/platform/registrations", json=registration_data
    )
    registration_id = reg_response.json()["id"]

    await async_client.post(
        f"/platform/registrations/{registration_id}/email-verifications"
    )

    # Make 5 failed attempts
    verify_data = {"code": "WRONGCOD"}
    for _ in range(5):
        response = await async_client.put(
            f"/platform/registrations/{registration_id}/email-verifications/current",
            json=verify_data,
        )
        assert response.status_code == 400

    # 6th attempt should be rate limited
    response = await async_client.put(
        f"/platform/registrations/{registration_id}/email-verifications/current",
        json=verify_data,
    )
    assert response.status_code == 429  # Too Many Requests
    data = response.json()
    assert "error" in data


@pytest.mark.asyncio
async def test_email_verification_verify_nonexistent_registration(async_client):
    """Test email verification for non-existent registration."""
    fake_registration_id = "550e8400-e29b-41d4-a716-446655440000"
    verify_data = {"code": "TESTCODE"}

    response = await async_client.put(
        f"/platform/registrations/{fake_registration_id}/email-verifications/current",
        json=verify_data,
    )

    assert response.status_code == 404
    data = response.json()
    assert "error" in data


@pytest.mark.asyncio
async def test_email_verification_verify_no_verification_exists(async_client):
    """Test email verification when no verification record exists."""
    # Create registration but no verification
    registration_data = {
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "email": fake.unique.email(),
        "password": "TestPassword123!",
    }

    reg_response = await async_client.post(
        "/platform/registrations", json=registration_data
    )
    registration_id = reg_response.json()["id"]

    # Try to verify without creating verification first
    verify_data = {"code": "TESTCODE"}
    response = await async_client.put(
        f"/platform/registrations/{registration_id}/email-verifications/current",
        json=verify_data,
    )

    assert response.status_code == 404
    data = response.json()
    assert "error" in data

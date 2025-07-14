import secrets
from datetime import datetime, timedelta
from jose import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.config import settings

# Initialize Argon2 password hasher with secure defaults
ph = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash a password using Argon2."""
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash using Argon2."""
    try:
        ph.verify(hashed_password, plain_password)
        return True
    except VerifyMismatchError:
        return False


def generate_jwt_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def generate_token(length=32) -> str:
    return secrets.token_hex(length)


def generate_code(length: int = 8) -> str:
    """Generate a cryptographically secure alphanumeric verification code.

    Uses secrets module for secure random number generation.
    Uses uppercase letters and digits for better security and readability.
    8 characters = 36^8 = ~2.8 trillion possibilities.
    """
    # Using uppercase letters and digits (36 characters total)
    # Excludes confusing characters like 0/O, 1/I for better UX
    alphabet = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"  # 32 characters (no 0,1,I,O)
    return "".join(secrets.choice(alphabet) for _ in range(length))

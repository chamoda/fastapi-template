import redis
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from app.config import settings
from app.exceptions import RateLimitException

# Initialize Redis connection
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

# Initialize limiter with Redis backend
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.REDIS_URL,
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> None:
    """Rate limit exception handler that raises our custom RateLimitException"""
    raise RateLimitException(message="Too many requests. Please try again later.")

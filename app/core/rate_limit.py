"""
Rate Limiting Configuration for Socratic AI.

Uses SlowAPI for request rate limiting with different tiers:
- Auth endpoints: Strict limits to prevent brute force
- Generation endpoints: Moderate limits (LLM calls are expensive)
- General API: Standard limits
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.core.config import settings


def get_identifier(request: Request) -> str:
    """
    Get rate limit identifier.

    Uses authenticated user ID if available, otherwise falls back to IP.
    This prevents a single user from bypassing limits with multiple IPs.
    """
    # Try to get user from request state (set by auth middleware)
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "id"):
        return f"user:{user.id}"

    # Fall back to IP address
    return get_remote_address(request)


# Initialize limiter with identifier function
limiter = Limiter(
    key_func=get_identifier,
    default_limits=[settings.RATE_LIMIT_DEFAULT],
    storage_uri=settings.RATE_LIMIT_STORAGE_URI,
    strategy="fixed-window",
)


# Preset rate limit decorators for different endpoint types
def auth_limit():
    """Strict rate limit for auth endpoints (login, register)."""
    return limiter.limit(settings.RATE_LIMIT_AUTH)


def generation_limit():
    """Moderate rate limit for LLM generation endpoints."""
    return limiter.limit(settings.RATE_LIMIT_GENERATION)


def standard_limit():
    """Standard rate limit for general API endpoints."""
    return limiter.limit(settings.RATE_LIMIT_DEFAULT)

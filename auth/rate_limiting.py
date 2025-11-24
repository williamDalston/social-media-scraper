"""
Advanced rate limiting with sliding window and per-user limits.
"""
from flask import request, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps
import time


def get_user_id_for_rate_limit():
    """
    Get user ID for rate limiting.
    Falls back to IP address if user not authenticated.
    """
    user = getattr(request, "current_user", None)
    if user:
        return f"user:{user.id}"
    return get_remote_address()


def get_user_role_for_rate_limit():
    """
    Get user role for tiered rate limits.
    """
    user = getattr(request, "current_user", None)
    if user:
        return user.role
    return "anonymous"


# Tiered rate limits based on user role
TIERED_RATE_LIMITS = {
    "Admin": "1000 per hour",
    "Editor": "500 per hour",
    "Viewer": "200 per hour",
    "anonymous": "100 per hour",
}


def get_tiered_rate_limit():
    """
    Get rate limit based on user role.
    """
    role = get_user_role_for_rate_limit()
    return TIERED_RATE_LIMITS.get(role, TIERED_RATE_LIMITS["anonymous"])


def add_rate_limit_headers(response, limiter_instance, endpoint):
    """
    Add rate limit headers to response.

    Args:
        response: Flask response object
        limiter_instance: Flask-Limiter instance
        endpoint: Endpoint name

    Returns:
        Response with rate limit headers
    """
    try:
        # Get rate limit info from limiter
        key = get_user_id_for_rate_limit()

        # Try to get remaining quota
        # Note: This is a simplified version - full implementation would
        # need to query the rate limiter's storage backend
        if hasattr(g, "rate_limit_remaining"):
            response.headers["X-RateLimit-Remaining"] = str(g.rate_limit_remaining)
        if hasattr(g, "rate_limit_reset"):
            response.headers["X-RateLimit-Reset"] = str(g.rate_limit_reset)

        # Add rate limit info header
        limit = get_tiered_rate_limit()
        response.headers["X-RateLimit-Limit"] = limit

        return response
    except Exception:
        # If rate limit headers fail, don't break the response
        return response


def rate_limit_with_headers(limiter_instance, limit_string):
    """
    Decorator that adds rate limiting with headers.

    Args:
        limiter_instance: Flask-Limiter instance
        limit_string: Rate limit string (e.g., "100 per hour")

    Returns:
        Decorator function
    """

    def decorator(f):
        @wraps(f)
        @limiter_instance.limit(limit_string, key_func=get_user_id_for_rate_limit)
        def decorated_function(*args, **kwargs):
            # Execute the function
            response = f(*args, **kwargs)

            # Add rate limit headers
            response = add_rate_limit_headers(response, limiter_instance, f.__name__)

            return response

        return decorated_function

    return decorator

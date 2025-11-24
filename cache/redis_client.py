"""
Redis caching client configuration with fallback support.
"""
import os
import logging
from flask import Flask
from flask_caching import Cache
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Initialize cache instance
cache = Cache()

# Track cache operations for metrics
_track_cache_metrics = True
_cache_available = False


def init_cache(app: Flask, fallback_to_simple=True):
    """
    Initialize Flask-Caching with Redis backend, with fallback to simple cache.

    Args:
        app: Flask application instance
        fallback_to_simple: If True, fall back to simple cache if Redis unavailable
    """
    global _cache_available
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Try Redis first
    try:
        cache_config = {
            "CACHE_TYPE": "redis",
            "CACHE_REDIS_URL": redis_url,
            "CACHE_DEFAULT_TIMEOUT": 300,  # 5 minutes default
            "CACHE_KEY_PREFIX": "hhs_scraper:",
            "CACHE_OPTIONS": {
                "socket_connect_timeout": 5,
                "socket_timeout": 5,
                "retry_on_timeout": True,
                "health_check_interval": 30,
            },
        }

        cache.init_app(app, config=cache_config)

        # Test connection
        try:
            cache.set("test_key", "test_value", timeout=1)
            cache.get("test_key")
            cache.delete("test_key")
            _cache_available = True
            logger.info("Redis cache initialized successfully")
        except Exception as e:
            logger.warning(f"Redis connection test failed: {e}")
            if fallback_to_simple:
                _init_simple_cache(app)
            else:
                raise

    except Exception as e:
        logger.warning(f"Failed to initialize Redis cache: {e}")
        if fallback_to_simple:
            _init_simple_cache(app)
        else:
            raise

    return cache


def _init_simple_cache(app: Flask):
    """Initialize simple in-memory cache as fallback."""
    global _cache_available
    logger.warning(
        "Falling back to simple in-memory cache (not shared across processes)"
    )
    cache_config = {
        "CACHE_TYPE": "simple",
        "CACHE_DEFAULT_TIMEOUT": 300,
    }
    cache.init_app(app, config=cache_config)
    _cache_available = False  # Mark as unavailable for metrics


def is_cache_available() -> bool:
    """Check if Redis cache is available."""
    return _cache_available


# Cache key naming conventions
CACHE_KEYS = {
    "summary": "summary:latest",
    "history": "history:{platform}:{handle}",
    "grid": "grid:all",
    "account": "account:{account_key}",
    "accounts_list": "accounts:list",
}


def get_cache_key(key_type: str, **kwargs) -> str:
    """
    Generate cache key from template.

    Args:
        key_type: Type of cache key (summary, history, grid, account, accounts_list)
        **kwargs: Variables to fill in the template

    Returns:
        Formatted cache key string
    """
    template = CACHE_KEYS.get(key_type)
    if not template:
        raise ValueError(f"Unknown cache key type: {key_type}")

    return template.format(**kwargs)

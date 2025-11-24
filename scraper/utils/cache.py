"""
Caching layer for platform metadata and scraped data.
"""

import time
import hashlib
import logging
from typing import Optional, Any, Dict
from functools import wraps

logger = logging.getLogger(__name__)


class SimpleCache:
    """
    Simple in-memory cache with TTL support.
    Can be extended to use Redis for distributed caching.
    """

    def __init__(self, default_ttl: int = 3600):
        """
        Initialize cache.

        Args:
            default_ttl: Default time-to-live in seconds
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
        logger.info(f"Initialized SimpleCache with TTL={default_ttl}s")

    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        """
        Create a cache key from arguments.

        Args:
            prefix: Key prefix
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Cache key string
        """
        # Create a hash of the arguments
        key_parts = [prefix]
        if args:
            key_parts.extend(str(arg) for arg in args)
        if kwargs:
            # Sort kwargs for consistent keys
            sorted_kwargs = sorted(kwargs.items())
            key_parts.extend(f"{k}={v}" for k, v in sorted_kwargs)

        key_string = ":".join(key_parts)
        # Create hash for shorter keys
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        return f"{prefix}:{key_hash}"

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        if key not in self._cache:
            return None

        entry = self._cache[key]

        # Check if expired
        if time.time() > entry["expires_at"]:
            del self._cache[key]
            return None

        return entry["value"]

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        if ttl is None:
            ttl = self.default_ttl

        self._cache[key] = {
            "value": value,
            "expires_at": time.time() + ttl,
        }

    def delete(self, key: str) -> None:
        """Delete key from cache."""
        if key in self._cache:
            del self._cache[key]

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()

    def size(self) -> int:
        """Get number of cache entries."""
        return len(self._cache)

    def cleanup_expired(self) -> int:
        """
        Remove expired entries from cache.

        Returns:
            Number of entries removed
        """
        now = time.time()
        expired_keys = [
            key for key, entry in self._cache.items() if now > entry["expires_at"]
        ]

        for key in expired_keys:
            del self._cache[key]

        return len(expired_keys)


# Global cache instance
_cache_instance: Optional[SimpleCache] = None


def get_cache() -> SimpleCache:
    """Get or create global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = SimpleCache()
    return _cache_instance


def cached(prefix: str, ttl: int = 3600):
    """
    Decorator to cache function results.

    Args:
        prefix: Cache key prefix
        ttl: Time-to-live in seconds

    Example:
        @cached('platform_metadata', ttl=7200)
        def get_platform_info(platform: str):
            ...
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache()
            key = cache._make_key(prefix, *args, **kwargs)

            # Try to get from cache
            cached_value = cache.get(key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {key}")
                return cached_value

            # Call function and cache result
            logger.debug(f"Cache miss for {key}, calling function")
            result = func(*args, **kwargs)
            cache.set(key, result, ttl=ttl)

            return result

        return wrapper

    return decorator

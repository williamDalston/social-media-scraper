"""
Cache wrapper with metrics tracking integration.
"""
from functools import wraps
from .redis_client import cache
from .metrics import get_metrics


def cached_with_metrics(timeout=300, key_prefix=None):
    """
    Cache decorator that tracks cache hits and misses.

    Args:
        timeout: Cache timeout in seconds
        key_prefix: Cache key prefix
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_prefix:
                if callable(key_prefix):
                    cache_key = key_prefix()
                else:
                    cache_key = key_prefix
            else:
                cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"

            # Try to get from cache
            metrics = get_metrics()
            cached_value = cache.get(cache_key)

            if cached_value is not None:
                metrics.record_cache_hit(cache_key)
                return cached_value
            else:
                metrics.record_cache_miss(cache_key)
                # Execute function
                result = func(*args, **kwargs)
                # Store in cache
                try:
                    cache.set(cache_key, result, timeout=timeout)
                except Exception as e:
                    # Cache set failed, but continue
                    import logging

                    logging.getLogger(__name__).warning(f"Failed to set cache: {e}")
                return result

        return wrapper

    return decorator

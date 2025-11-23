"""
Cache invalidation logic.
"""
from .redis_client import cache, get_cache_key

def invalidate_cache(key_pattern: str = None):
    """
    Invalidate cache entries matching a pattern.
    
    Args:
        key_pattern: Cache key pattern to invalidate (None = all)
    """
    if key_pattern:
        # Delete specific key
        cache.delete(key_pattern)
    else:
        # Clear all cache (use with caution)
        cache.clear()

def invalidate_summary_cache():
    """Invalidate summary cache."""
    cache.delete(get_cache_key('summary'))

def invalidate_history_cache(platform: str = None, handle: str = None):
    """
    Invalidate history cache for specific account or all.
    
    Args:
        platform: Platform name (optional)
        handle: Handle name (optional)
    """
    if platform and handle:
        cache.delete(get_cache_key('history', platform=platform, handle=handle))
    else:
        # Invalidate all history caches (pattern matching would be better, but flask-caching doesn't support it directly)
        # For now, we'll rely on TTL expiration
        pass

def invalidate_grid_cache():
    """Invalidate grid data cache."""
    cache.delete(get_cache_key('grid'))

def invalidate_account_cache(account_key: int):
    """
    Invalidate account-specific cache.
    
    Args:
        account_key: Account key to invalidate
    """
    cache.delete(get_cache_key('account', account_key=account_key))

def invalidate_accounts_list_cache():
    """Invalidate accounts list cache."""
    cache.delete(get_cache_key('accounts_list'))


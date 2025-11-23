"""
Advanced cache invalidation strategies with tag-based and dependency tracking.
"""
import logging
from typing import List, Set, Optional
from .redis_client import cache, get_cache_key, is_cache_available
from .multi_level import get_multi_cache

logger = logging.getLogger(__name__)

# Cache tag registry for tag-based invalidation
_cache_tags = {}  # tag -> set of keys
_key_tags = {}    # key -> set of tags


def register_cache_tag(key: str, tags: List[str]):
    """
    Register cache key with tags for tag-based invalidation.
    
    Args:
        key: Cache key
        tags: List of tags associated with this key
    """
    if not tags:
        return
    
    _key_tags[key] = set(tags)
    for tag in tags:
        if tag not in _cache_tags:
            _cache_tags[tag] = set()
        _cache_tags[tag].add(key)


def invalidate_by_tag(tag: str):
    """
    Invalidate all cache entries with a specific tag.
    
    Args:
        tag: Tag to invalidate
    """
    if tag not in _cache_tags:
        return
    
    keys = _cache_tags[tag].copy()
    multi_cache = get_multi_cache()
    
    for key in keys:
        try:
            multi_cache.delete(key)
            # Remove from registry
            if key in _key_tags:
                del _key_tags[key]
        except Exception as e:
            logger.warning(f"Failed to invalidate key {key}: {e}")
    
    # Clean up tag registry
    del _cache_tags[tag]
    logger.info(f"Invalidated {len(keys)} cache entries with tag '{tag}'")


def invalidate_cache(key_pattern: str = None):
    """
    Invalidate cache entries matching a pattern.
    
    Args:
        key_pattern: Cache key pattern to invalidate (None = all)
    """
    multi_cache = get_multi_cache()
    
    if key_pattern:
        # Delete specific key
        multi_cache.delete(key_pattern)
        # Remove from tag registry
        if key_pattern in _key_tags:
            tags = _key_tags[key_pattern]
            for tag in tags:
                if tag in _cache_tags:
                    _cache_tags[tag].discard(key_pattern)
            del _key_tags[key_pattern]
    else:
        # Clear all cache (use with caution)
        multi_cache.clear()
        _cache_tags.clear()
        _key_tags.clear()


def invalidate_summary_cache():
    """Invalidate summary cache."""
    key = get_cache_key('summary')
    invalidate_cache(key)
    invalidate_by_tag('summary')  # Also invalidate by tag


def invalidate_history_cache(platform: str = None, handle: str = None):
    """
    Invalidate history cache for specific account or all.
    
    Args:
        platform: Platform name (optional)
        handle: Handle name (optional)
    """
    if platform and handle:
        key = get_cache_key('history', platform=platform, handle=handle)
        invalidate_cache(key)
        invalidate_by_tag(f'history:{platform}:{handle}')
        invalidate_by_tag(f'account:{platform}:{handle}')
    else:
        # Invalidate all history caches
        invalidate_by_tag('history')
        logger.info("Invalidated all history caches")


def invalidate_grid_cache():
    """Invalidate grid data cache."""
    key = get_cache_key('grid')
    invalidate_cache(key)
    invalidate_by_tag('grid')


def invalidate_account_cache(account_key: int):
    """
    Invalidate account-specific cache.
    
    Args:
        account_key: Account key to invalidate
    """
    key = get_cache_key('account', account_key=account_key)
    invalidate_cache(key)
    invalidate_by_tag(f'account:{account_key}')


def invalidate_accounts_list_cache():
    """Invalidate accounts list cache."""
    key = get_cache_key('accounts_list')
    invalidate_cache(key)
    invalidate_by_tag('accounts')


def invalidate_platform_cache(platform: str):
    """
    Invalidate all cache entries for a specific platform.
    
    Args:
        platform: Platform name
    """
    invalidate_by_tag(f'platform:{platform}')
    logger.info(f"Invalidated all cache entries for platform '{platform}'")


def invalidate_on_snapshot_create(account_key: int, platform: str, handle: str):
    """
    Invalidate relevant caches when a new snapshot is created.
    
    Args:
        account_key: Account key
        platform: Platform name
        handle: Handle name
    """
    # Invalidate summary (contains latest data)
    invalidate_summary_cache()
    
    # Invalidate history for this account
    invalidate_history_cache(platform, handle)
    
    # Invalidate grid (contains all snapshots)
    invalidate_grid_cache()
    
    # Invalidate account-specific cache
    invalidate_account_cache(account_key)
    
    logger.debug(f"Invalidated caches for new snapshot: {platform}/{handle}")


def invalidate_on_account_update(account_key: int, platform: str, handle: str):
    """
    Invalidate relevant caches when an account is updated.
    
    Args:
        account_key: Account key
        platform: Platform name
        handle: Handle name
    """
    invalidate_account_cache(account_key)
    invalidate_accounts_list_cache()
    invalidate_history_cache(platform, handle)
    invalidate_summary_cache()
    
    logger.debug(f"Invalidated caches for account update: {platform}/{handle}")


def get_invalidation_stats() -> dict:
    """Get cache invalidation statistics."""
    return {
        'total_tags': len(_cache_tags),
        'total_tagged_keys': len(_key_tags),
        'tags': list(_cache_tags.keys()),
    }


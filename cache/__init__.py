"""
Cache module for Redis-based caching with multi-level support.
"""
from .redis_client import cache, init_cache, is_cache_available
from .invalidation import (
    invalidate_cache, invalidate_summary_cache, invalidate_history_cache, 
    invalidate_grid_cache, invalidate_accounts_list_cache,
    invalidate_by_tag, invalidate_platform_cache,
    invalidate_on_snapshot_create, invalidate_on_account_update
)
from .metrics import get_metrics, PerformanceMetrics
from .cache_wrapper import cached_with_metrics
from .multi_level import get_multi_cache, MultiLevelCache, LRUCache
from .warming import get_warmer, CacheWarmer, warm_cache_on_startup
from .analytics import get_analytics, CacheAnalytics

__all__ = [
    'cache',
    'init_cache',
    'is_cache_available',
    'invalidate_cache',
    'invalidate_summary_cache',
    'invalidate_history_cache',
    'invalidate_grid_cache',
    'invalidate_accounts_list_cache',
    'invalidate_by_tag',
    'invalidate_platform_cache',
    'invalidate_on_snapshot_create',
    'invalidate_on_account_update',
    'get_metrics',
    'PerformanceMetrics',
    'cached_with_metrics',
    'get_multi_cache',
    'MultiLevelCache',
    'LRUCache',
    'get_warmer',
    'CacheWarmer',
    'warm_cache_on_startup',
    'get_analytics',
    'CacheAnalytics',
]


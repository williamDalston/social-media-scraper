"""
Cache module for Redis-based caching.
"""
from .redis_client import cache, init_cache, is_cache_available
from .invalidation import (
    invalidate_cache, invalidate_summary_cache, invalidate_history_cache, 
    invalidate_grid_cache, invalidate_accounts_list_cache
)
from .metrics import get_metrics, PerformanceMetrics
from .cache_wrapper import cached_with_metrics

__all__ = [
    'cache',
    'init_cache',
    'is_cache_available',
    'invalidate_cache',
    'invalidate_summary_cache',
    'invalidate_history_cache',
    'invalidate_grid_cache',
    'invalidate_accounts_list_cache',
    'get_metrics',
    'PerformanceMetrics',
    'cached_with_metrics',
]


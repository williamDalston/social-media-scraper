"""
Multi-level caching implementation (L1: Memory, L2: Redis).
Provides fast in-memory cache with Redis as secondary cache.
"""
import time
import threading
from typing import Optional, Any, Callable
from functools import wraps
import logging

logger = logging.getLogger(__name__)

class MultiLevelCache:
    """Multi-level cache with memory (L1) and Redis (L2)."""
    
    def __init__(self, redis_cache=None):
        self.l1_cache = {}  # In-memory cache
        self.l1_timestamps = {}  # Track when items were cached
        self.l1_ttl = 60  # L1 TTL in seconds (1 minute)
        self.l2_cache = redis_cache  # Redis cache (L2)
        self.lock = threading.Lock()
        self.stats = {
            'l1_hits': 0,
            'l1_misses': 0,
            'l2_hits': 0,
            'l2_misses': 0,
        }
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache (L1 first, then L2)."""
        # Try L1 cache first
        with self.lock:
            if key in self.l1_cache:
                # Check if expired
                if time.time() - self.l1_timestamps.get(key, 0) < self.l1_ttl:
                    self.stats['l1_hits'] += 1
                    logger.debug(f"L1 cache hit: {key}")
                    return self.l1_cache[key]
                else:
                    # Expired, remove from L1
                    del self.l1_cache[key]
                    del self.l1_timestamps[key]
        
        self.stats['l1_misses'] += 1
        
        # Try L2 cache (Redis)
        if self.l2_cache:
            try:
                value = self.l2_cache.get(key)
                if value is not None:
                    self.stats['l2_hits'] += 1
                    logger.debug(f"L2 cache hit: {key}")
                    
                    # Promote to L1
                    with self.lock:
                        self.l1_cache[key] = value
                        self.l1_timestamps[key] = time.time()
                    
                    return value
                else:
                    self.stats['l2_misses'] += 1
            except Exception as e:
                logger.warning(f"L2 cache error for {key}: {e}")
                self.stats['l2_misses'] += 1
        
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in both L1 and L2 cache."""
        # Set in L1
        with self.lock:
            self.l1_cache[key] = value
            self.l1_timestamps[key] = time.time()
        
        # Set in L2 (Redis)
        if self.l2_cache:
            try:
                if ttl:
                    self.l2_cache.set(key, value, timeout=ttl)
                else:
                    self.l2_cache.set(key, value)
                logger.debug(f"Cached in L1 and L2: {key}")
            except Exception as e:
                logger.warning(f"L2 cache set error for {key}: {e}")
    
    def delete(self, key: str):
        """Delete from both L1 and L2 cache."""
        with self.lock:
            if key in self.l1_cache:
                del self.l1_cache[key]
                del self.l1_timestamps[key]
        
        if self.l2_cache:
            try:
                self.l2_cache.delete(key)
            except Exception as e:
                logger.warning(f"L2 cache delete error for {key}: {e}")
    
    def clear(self):
        """Clear both L1 and L2 cache."""
        with self.lock:
            self.l1_cache.clear()
            self.l1_timestamps.clear()
        
        if self.l2_cache:
            try:
                self.l2_cache.clear()
            except Exception as e:
                logger.warning(f"L2 cache clear error: {e}")
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        total_requests = sum(self.stats.values())
        if total_requests == 0:
            return {
                **self.stats,
                'l1_hit_rate': 0.0,
                'l2_hit_rate': 0.0,
                'overall_hit_rate': 0.0,
                'l1_size': len(self.l1_cache)
            }
        
        l1_requests = self.stats['l1_hits'] + self.stats['l1_misses']
        l2_requests = self.stats['l2_hits'] + self.stats['l2_misses']
        
        return {
            **self.stats,
            'l1_hit_rate': self.stats['l1_hits'] / l1_requests if l1_requests > 0 else 0.0,
            'l2_hit_rate': self.stats['l2_hits'] / l2_requests if l2_requests > 0 else 0.0,
            'overall_hit_rate': (self.stats['l1_hits'] + self.stats['l2_hits']) / total_requests,
            'l1_size': len(self.l1_cache)
        }
    
    def cleanup_expired(self):
        """Remove expired items from L1 cache."""
        now = time.time()
        with self.lock:
            expired_keys = [
                key for key, timestamp in self.l1_timestamps.items()
                if now - timestamp >= self.l1_ttl
            ]
            for key in expired_keys:
                del self.l1_cache[key]
                del self.l1_timestamps[key]
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired L1 cache entries")

def cached_multilevel(key_prefix: str = "", ttl: int = 300):
    """
    Decorator for multi-level caching.
    
    Args:
        key_prefix: Prefix for cache key
        ttl: Time to live in seconds
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Import here to avoid circular imports
            from cache.multilevel_cache import get_multilevel_cache
            ml_cache = get_multilevel_cache()
            
            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Try to get from cache
            cached_value = ml_cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Cache miss, compute value
            value = func(*args, **kwargs)
            
            # Store in cache
            ml_cache.set(cache_key, value, ttl=ttl)
            
            return value
        return wrapper
    return decorator

# Global multi-level cache instance
_multilevel_cache: Optional[MultiLevelCache] = None

def init_multilevel_cache(redis_cache=None) -> MultiLevelCache:
    """Initialize multi-level cache."""
    global _multilevel_cache
    _multilevel_cache = MultiLevelCache(redis_cache=redis_cache)
    return _multilevel_cache

def get_multilevel_cache() -> MultiLevelCache:
    """Get global multi-level cache instance."""
    global _multilevel_cache
    if _multilevel_cache is None:
        # Try to get Redis cache from Flask-Caching
        try:
            from cache.redis_client import cache
            redis_cache = cache
        except:
            redis_cache = None
        
        _multilevel_cache = MultiLevelCache(redis_cache=redis_cache)
    
    return _multilevel_cache


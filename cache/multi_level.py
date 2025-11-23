"""
Multi-level caching implementation (L1: Memory, L2: Redis).
"""
import os
import time
import threading
from typing import Any, Optional, Callable
from collections import OrderedDict
from .redis_client import cache, is_cache_available
from .metrics import get_metrics

class LRUCache:
    """Thread-safe LRU cache for L1 (memory) caching."""
    
    def __init__(self, maxsize: int = 1000, ttl: int = 60):
        """
        Initialize LRU cache.
        
        Args:
            maxsize: Maximum number of items to cache
            ttl: Time to live in seconds
        """
        self.maxsize = maxsize
        self.ttl = ttl
        self._cache = OrderedDict()
        self._timestamps = {}
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        with self._lock:
            if key not in self._cache:
                return None
            
            # Check if expired
            if time.time() - self._timestamps.get(key, 0) > self.ttl:
                self._delete(key)
                return None
            
            # Move to end (most recently used)
            value = self._cache.pop(key)
            self._cache[key] = value
            return value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache."""
        with self._lock:
            ttl = ttl or self.ttl
            
            # Remove if exists
            if key in self._cache:
                del self._cache[key]
            
            # Add new value
            self._cache[key] = value
            self._timestamps[key] = time.time()
            
            # Evict if over maxsize
            if len(self._cache) > self.maxsize:
                # Remove oldest (first item)
                self._cache.popitem(last=False)
                oldest_key = min(self._timestamps.keys(), key=lambda k: self._timestamps[k])
                del self._timestamps[oldest_key]
    
    def _delete(self, key: str):
        """Delete key from cache."""
        if key in self._cache:
            del self._cache[key]
        if key in self._timestamps:
            del self._timestamps[key]
    
    def delete(self, key: str):
        """Delete key from cache (thread-safe)."""
        with self._lock:
            self._delete(key)
    
    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()
    
    def size(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self._cache)


class MultiLevelCache:
    """Multi-level cache with L1 (memory) and L2 (Redis)."""
    
    def __init__(self, l1_maxsize: int = 1000, l1_ttl: int = 60, l2_ttl: int = 300):
        """
        Initialize multi-level cache.
        
        Args:
            l1_maxsize: Maximum size for L1 (memory) cache
            l1_ttl: TTL for L1 cache in seconds
            l2_ttl: TTL for L2 (Redis) cache in seconds
        """
        self.l1_cache = LRUCache(maxsize=l1_maxsize, ttl=l1_ttl)
        self.l2_ttl = l2_ttl
        self.l2_available = is_cache_available()
        self.metrics = get_metrics()
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache (L1 first, then L2).
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        start_time = time.time()
        
        # Try L1 first
        value = self.l1_cache.get(key)
        if value is not None:
            duration = time.time() - start_time
            self.metrics.record_cache_hit(f'l1:{key}')
            # Record for production monitoring
            try:
                from .production_monitoring import record_cache_operation
                record_cache_operation('get', key, 'l1', duration, success=True)
            except Exception:
                pass
            return value
        
        # Try L2 (Redis)
        if self.l2_available:
            try:
                l2_start = time.time()
                value = cache.get(key)
                l2_duration = time.time() - l2_start
                
                if value is not None:
                    # Promote to L1
                    self.l1_cache.set(key, value)
                    duration = time.time() - start_time
                    self.metrics.record_cache_hit(f'l2:{key}')
                    # Record for production monitoring
                    try:
                        from .production_monitoring import record_cache_operation
                        record_cache_operation('get', key, 'l2', duration, success=True)
                    except Exception:
                        pass
                    return value
                else:
                    duration = time.time() - start_time
                    self.metrics.record_cache_miss(f'l2:{key}')
                    # Record for production monitoring
                    try:
                        from .production_monitoring import record_cache_operation
                        record_cache_operation('get', key, 'l2', duration, success=False)
                    except Exception:
                        pass
            except Exception as e:
                duration = time.time() - start_time
                # Record error
                try:
                    from .production_monitoring import record_cache_operation
                    record_cache_operation('get', key, 'l2', duration, success=False, error=str(e))
                except Exception:
                    pass
                # L2 unavailable, continue
                pass
        
        duration = time.time() - start_time
        self.metrics.record_cache_miss(f'total:{key}')
        # Record for production monitoring
        try:
            from .production_monitoring import record_cache_operation
            record_cache_operation('get', key, None, duration, success=False)
        except Exception:
            pass
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set value in both L1 and L2 caches.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Optional TTL override
        """
        start_time = time.time()
        
        # Set in L1
        try:
            self.l1_cache.set(key, value, ttl=ttl)
            l1_duration = time.time() - start_time
            # Record for production monitoring
            try:
                from .production_monitoring import record_cache_operation
                record_cache_operation('set', key, 'l1', l1_duration, success=True)
            except Exception:
                pass
        except Exception as e:
            l1_duration = time.time() - start_time
            try:
                from .production_monitoring import record_cache_operation
                record_cache_operation('set', key, 'l1', l1_duration, success=False, error=str(e))
            except Exception:
                pass
        
        # Set in L2 (Redis)
        if self.l2_available:
            try:
                l2_start = time.time()
                cache.set(key, value, timeout=ttl or self.l2_ttl)
                l2_duration = time.time() - l2_start
                # Record for production monitoring
                try:
                    from .production_monitoring import record_cache_operation
                    record_cache_operation('set', key, 'l2', l2_duration, success=True)
                except Exception:
                    pass
            except Exception as e:
                l2_duration = time.time() - start_time
                # Record error
                try:
                    from .production_monitoring import record_cache_operation
                    record_cache_operation('set', key, 'l2', l2_duration, success=False, error=str(e))
                except Exception:
                    pass
                # L2 unavailable, continue with L1 only
                pass
    
    def delete(self, key: str):
        """Delete key from both L1 and L2 caches."""
        self.l1_cache.delete(key)
        if self.l2_available:
            try:
                cache.delete(key)
            except Exception:
                pass
    
    def clear(self):
        """Clear both L1 and L2 caches."""
        self.l1_cache.clear()
        if self.l2_available:
            try:
                cache.clear()
            except Exception:
                pass
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        return {
            'l1_size': self.l1_cache.size(),
            'l1_maxsize': self.l1_cache.maxsize,
            'l2_available': self.l2_available,
            'l1_ttl': self.l1_cache.ttl,
            'l2_ttl': self.l2_ttl,
        }


# Global multi-level cache instance
_multi_cache = None

def get_multi_cache() -> MultiLevelCache:
    """Get or create global multi-level cache instance."""
    global _multi_cache
    if _multi_cache is None:
        _multi_cache = MultiLevelCache(
            l1_maxsize=int(os.getenv('CACHE_L1_MAXSIZE', '1000')),
            l1_ttl=int(os.getenv('CACHE_L1_TTL', '60')),
            l2_ttl=int(os.getenv('CACHE_L2_TTL', '300'))
        )
    return _multi_cache


"""
Cache analytics and hit rate monitoring.
"""
import time
from typing import Dict, List, Optional
from collections import defaultdict, deque
from threading import Lock
from .multi_level import get_multi_cache
from .metrics import get_metrics

class CacheAnalytics:
    """Cache analytics and monitoring."""
    
    def __init__(self, max_history: int = 10000):
        """
        Initialize cache analytics.
        
        Args:
            max_history: Maximum number of operations to track
        """
        self.max_history = max_history
        self._lock = Lock()
        
        # Operation tracking
        self.operations = deque(maxlen=max_history)
        
        # Hit/miss tracking by key pattern
        self.hits_by_pattern = defaultdict(int)
        self.misses_by_pattern = defaultdict(int)
        
        # Timing tracking
        self.timings = defaultdict(list)
        
        # Cache size tracking
        self.size_history = deque(maxlen=1000)
        
    def record_operation(self, operation: str, key: str, hit: bool, duration: float = 0):
        """
        Record a cache operation.
        
        Args:
            operation: Operation type (get, set, delete)
            key: Cache key
            hit: Whether it was a hit (for get operations)
            duration: Operation duration in seconds
        """
        with self._lock:
            timestamp = time.time()
            self.operations.append({
                'timestamp': timestamp,
                'operation': operation,
                'key': key,
                'hit': hit,
                'duration': duration
            })
            
            # Track by pattern
            pattern = self._extract_pattern(key)
            if operation == 'get':
                if hit:
                    self.hits_by_pattern[pattern] += 1
                else:
                    self.misses_by_pattern[pattern] += 1
            
            # Track timing
            if duration > 0:
                self.timings[operation].append(duration)
                # Keep only recent timings
                if len(self.timings[operation]) > 1000:
                    self.timings[operation] = self.timings[operation][-1000:]
    
    def record_size(self, l1_size: int, l2_available: bool):
        """Record current cache size."""
        with self._lock:
            self.size_history.append({
                'timestamp': time.time(),
                'l1_size': l1_size,
                'l2_available': l2_available
            })
    
    def _extract_pattern(self, key: str) -> str:
        """Extract pattern from cache key."""
        if ':' in key:
            parts = key.split(':')
            if len(parts) >= 2:
                return f"{parts[0]}:{parts[1]}"
        return key.split(':')[0] if ':' in key else 'unknown'
    
    def get_hit_rate(self, pattern: Optional[str] = None) -> Dict:
        """
        Get cache hit rate statistics.
        
        Args:
            pattern: Optional pattern to filter by
            
        Returns:
            Dictionary with hit rate statistics
        """
        with self._lock:
            if pattern:
                hits = self.hits_by_pattern.get(pattern, 0)
                misses = self.misses_by_pattern.get(pattern, 0)
                total = hits + misses
                
                return {
                    'pattern': pattern,
                    'hits': hits,
                    'misses': misses,
                    'total': total,
                    'hit_rate': (hits / total * 100) if total > 0 else 0,
                    'miss_rate': (misses / total * 100) if total > 0 else 0,
                }
            else:
                # Overall statistics
                total_hits = sum(self.hits_by_pattern.values())
                total_misses = sum(self.misses_by_pattern.values())
                total = total_hits + total_misses
                
                return {
                    'overall': {
                        'hits': total_hits,
                        'misses': total_misses,
                        'total': total,
                        'hit_rate': (total_hits / total * 100) if total > 0 else 0,
                        'miss_rate': (total_misses / total * 100) if total > 0 else 0,
                    },
                    'by_pattern': {
                        pattern: {
                            'hits': self.hits_by_pattern[pattern],
                            'misses': self.misses_by_pattern[pattern],
                            'total': self.hits_by_pattern[pattern] + self.misses_by_pattern[pattern],
                            'hit_rate': (
                                (self.hits_by_pattern[pattern] / 
                                 (self.hits_by_pattern[pattern] + self.misses_by_pattern[pattern]) * 100)
                                if (self.hits_by_pattern[pattern] + self.misses_by_pattern[pattern]) > 0 else 0
                            )
                        }
                        for pattern in set(list(self.hits_by_pattern.keys()) + list(self.misses_by_pattern.keys()))
                    }
                }
    
    def get_timing_stats(self) -> Dict:
        """Get timing statistics for cache operations."""
        with self._lock:
            stats = {}
            for operation, timings in self.timings.items():
                if timings:
                    stats[operation] = {
                        'count': len(timings),
                        'avg': sum(timings) / len(timings),
                        'min': min(timings),
                        'max': max(timings),
                        'p95': self._percentile(timings, 95),
                        'p99': self._percentile(timings, 99),
                    }
            return stats
    
    def get_recent_operations(self, limit: int = 100) -> List[Dict]:
        """Get recent cache operations."""
        with self._lock:
            return list(self.operations)[-limit:]
    
    def get_size_trends(self) -> Dict:
        """Get cache size trends."""
        with self._lock:
            if not self.size_history:
                return {}
            
            sizes = [s['l1_size'] for s in self.size_history]
            return {
                'current': sizes[-1] if sizes else 0,
                'avg': sum(sizes) / len(sizes) if sizes else 0,
                'min': min(sizes) if sizes else 0,
                'max': max(sizes) if sizes else 0,
                'samples': len(sizes)
            }
    
    def get_recommendations(self) -> List[str]:
        """
        Get cache optimization recommendations.
        
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        hit_rate_stats = self.get_hit_rate()
        overall = hit_rate_stats.get('overall', {})
        hit_rate = overall.get('hit_rate', 0)
        
        # Hit rate recommendations
        if hit_rate < 50:
            recommendations.append(
                f"Cache hit rate is low ({hit_rate:.1f}%). Consider increasing cache TTL or implementing cache warming."
            )
        elif hit_rate < 70:
            recommendations.append(
                f"Cache hit rate could be improved ({hit_rate:.1f}%). Review cache keys and TTL settings."
            )
        
        # Pattern-specific recommendations
        by_pattern = hit_rate_stats.get('by_pattern', {})
        for pattern, stats in by_pattern.items():
            pattern_hit_rate = stats.get('hit_rate', 0)
            if pattern_hit_rate < 50 and stats.get('total', 0) > 100:
                recommendations.append(
                    f"Pattern '{pattern}' has low hit rate ({pattern_hit_rate:.1f}%). "
                    f"Consider optimizing cache strategy for this pattern."
                )
        
        # Size recommendations
        size_trends = self.get_size_trends()
        current_size = size_trends.get('current', 0)
        max_size = size_trends.get('max', 0)
        
        multi_cache = get_multi_cache()
        l1_maxsize = multi_cache.l1_cache.maxsize
        
        if current_size > l1_maxsize * 0.9:
            recommendations.append(
                f"L1 cache is nearly full ({current_size}/{l1_maxsize}). Consider increasing maxsize or TTL."
            )
        
        # Timing recommendations
        timing_stats = self.get_timing_stats()
        for operation, stats in timing_stats.items():
            avg_time = stats.get('avg', 0)
            if operation == 'get' and avg_time > 0.01:  # 10ms
                recommendations.append(
                    f"Cache {operation} operations are slow (avg {avg_time*1000:.2f}ms). "
                    f"Consider optimizing cache implementation."
                )
        
        return recommendations
    
    def _percentile(self, data: list, percentile: float) -> float:
        """Calculate percentile of data."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def get_all_stats(self) -> Dict:
        """Get all analytics statistics."""
        return {
            'hit_rate': self.get_hit_rate(),
            'timing': self.get_timing_stats(),
            'size_trends': self.get_size_trends(),
            'recent_operations_count': len(self.operations),
            'recommendations': self.get_recommendations(),
        }
    
    def reset(self):
        """Reset all analytics data."""
        with self._lock:
            self.operations.clear()
            self.hits_by_pattern.clear()
            self.misses_by_pattern.clear()
            self.timings.clear()
            self.size_history.clear()


# Global analytics instance
_analytics = None

def get_analytics() -> CacheAnalytics:
    """Get or create global cache analytics instance."""
    global _analytics
    if _analytics is None:
        _analytics = CacheAnalytics()
    return _analytics


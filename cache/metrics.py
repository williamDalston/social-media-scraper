"""
Performance metrics tracking for caching and API performance.
"""
import time
from typing import Dict, Optional
from collections import defaultdict, deque
from threading import Lock

class PerformanceMetrics:
    """Thread-safe performance metrics tracker."""
    
    def __init__(self, max_history=1000):
        """
        Initialize metrics tracker.
        
        Args:
            max_history: Maximum number of historical records to keep
        """
        self.max_history = max_history
        self._lock = Lock()
        
        # API metrics
        self.api_times = defaultdict(list)  # endpoint -> list of response times
        self.api_counts = defaultdict(int)  # endpoint -> request count
        self.api_errors = defaultdict(int)  # endpoint -> error count
        
        # Cache metrics
        self.cache_hits = defaultdict(int)
        self.cache_misses = defaultdict(int)
        self.cache_operations = deque(maxlen=max_history)
        
        # Database metrics
        self.db_query_times = deque(maxlen=max_history)
        self.db_query_counts = 0
        
        # Scraper metrics
        self.scraper_times = deque(maxlen=max_history)
        self.scraper_success = 0
        self.scraper_errors = 0
        
    def record_api_request(self, endpoint: str, duration: float, error: bool = False):
        """Record API request metrics."""
        with self._lock:
            self.api_counts[endpoint] += 1
            self.api_times[endpoint].append(duration)
            # Keep only recent times
            if len(self.api_times[endpoint]) > self.max_history:
                self.api_times[endpoint] = self.api_times[endpoint][-self.max_history:]
            
            if error:
                self.api_errors[endpoint] += 1
    
    def record_cache_hit(self, key: str):
        """Record cache hit."""
        with self._lock:
            self.cache_hits[key] += 1
            self.cache_operations.append(('hit', key, time.time()))
    
    def record_cache_miss(self, key: str):
        """Record cache miss."""
        with self._lock:
            self.cache_misses[key] += 1
            self.cache_operations.append(('miss', key, time.time()))
    
    def record_db_query(self, duration: float):
        """Record database query time."""
        with self._lock:
            self.db_query_times.append(duration)
            self.db_query_counts += 1
    
    def record_scraper_execution(self, duration: float, success: bool):
        """Record scraper execution metrics."""
        with self._lock:
            self.scraper_times.append(duration)
            if success:
                self.scraper_success += 1
            else:
                self.scraper_errors += 1
    
    def get_api_stats(self, endpoint: Optional[str] = None) -> Dict:
        """Get API statistics for endpoint or all endpoints."""
        with self._lock:
            if endpoint:
                times = self.api_times.get(endpoint, [])
                return {
                    'endpoint': endpoint,
                    'count': self.api_counts.get(endpoint, 0),
                    'errors': self.api_errors.get(endpoint, 0),
                    'avg_time': sum(times) / len(times) if times else 0,
                    'min_time': min(times) if times else 0,
                    'max_time': max(times) if times else 0,
                    'p95_time': self._percentile(times, 95) if times else 0,
                    'p99_time': self._percentile(times, 99) if times else 0,
                }
            else:
                return {
                    ep: self.get_api_stats(ep)
                    for ep in self.api_counts.keys()
                }
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        with self._lock:
            total_hits = sum(self.cache_hits.values())
            total_misses = sum(self.cache_misses.values())
            total_requests = total_hits + total_misses
            
            return {
                'total_hits': total_hits,
                'total_misses': total_misses,
                'total_requests': total_requests,
                'hit_rate': (total_hits / total_requests * 100) if total_requests > 0 else 0,
                'miss_rate': (total_misses / total_requests * 100) if total_requests > 0 else 0,
                'by_key': {
                    key: {
                        'hits': self.cache_hits[key],
                        'misses': self.cache_misses.get(key, 0),
                        'hit_rate': (
                            self.cache_hits[key] / 
                            (self.cache_hits[key] + self.cache_misses.get(key, 0)) * 100
                            if (self.cache_hits[key] + self.cache_misses.get(key, 0)) > 0 else 0
                        )
                    }
                    for key in self.cache_hits.keys()
                }
            }
    
    def get_db_stats(self) -> Dict:
        """Get database statistics."""
        with self._lock:
            times = list(self.db_query_times)
            return {
                'total_queries': self.db_query_counts,
                'recent_queries': len(times),
                'avg_time': sum(times) / len(times) if times else 0,
                'min_time': min(times) if times else 0,
                'max_time': max(times) if times else 0,
                'p95_time': self._percentile(times, 95) if times else 0,
            }
    
    def get_scraper_stats(self) -> Dict:
        """Get scraper statistics."""
        with self._lock:
            times = list(self.scraper_times)
            return {
                'total_executions': self.scraper_success + self.scraper_errors,
                'success_count': self.scraper_success,
                'error_count': self.scraper_errors,
                'success_rate': (
                    self.scraper_success / (self.scraper_success + self.scraper_errors) * 100
                    if (self.scraper_success + self.scraper_errors) > 0 else 0
                ),
                'avg_time': sum(times) / len(times) if times else 0,
                'min_time': min(times) if times else 0,
                'max_time': max(times) if times else 0,
            }
    
    def get_all_stats(self) -> Dict:
        """Get all performance statistics."""
        return {
            'api': self.get_api_stats(),
            'cache': self.get_cache_stats(),
            'database': self.get_db_stats(),
            'scraper': self.get_scraper_stats(),
        }
    
    def _percentile(self, data: list, percentile: float) -> float:
        """Calculate percentile of data."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def reset(self):
        """Reset all metrics."""
        with self._lock:
            self.api_times.clear()
            self.api_counts.clear()
            self.api_errors.clear()
            self.cache_hits.clear()
            self.cache_misses.clear()
            self.cache_operations.clear()
            self.db_query_times.clear()
            self.db_query_counts = 0
            self.scraper_times.clear()
            self.scraper_success = 0
            self.scraper_errors = 0


# Global metrics instance
_metrics = PerformanceMetrics()

def get_metrics() -> PerformanceMetrics:
    """Get global metrics instance."""
    return _metrics


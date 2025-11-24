"""
Production cache performance monitoring and optimization.
"""
import os
import logging
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import deque, defaultdict
from threading import Lock

logger = logging.getLogger(__name__)


class CachePerformanceMonitor:
    """Monitor cache performance for production optimization."""

    def __init__(self, max_history: int = 10000):
        """
        Initialize cache performance monitor.

        Args:
            max_history: Maximum number of operations to track
        """
        self.max_history = max_history
        self._lock = Lock()

        # Track operations
        self._operations = deque(maxlen=max_history)
        self._key_stats = defaultdict(
            lambda: {"hits": 0, "misses": 0, "sets": 0, "deletes": 0}
        )
        self._timing_stats = deque(maxlen=max_history)

        # Track by cache level
        self._l1_stats = {"hits": 0, "misses": 0, "sets": 0}
        self._l2_stats = {"hits": 0, "misses": 0, "sets": 0}

        # Track errors
        self._errors = deque(maxlen=1000)

    def record_operation(
        self,
        operation: str,
        key: str,
        cache_level: Optional[str] = None,
        duration: Optional[float] = None,
        success: bool = True,
        error: Optional[str] = None,
    ):
        """
        Record a cache operation.

        Args:
            operation: Operation type (get, set, delete)
            key: Cache key
            cache_level: Cache level (l1, l2, or None)
            duration: Operation duration in seconds
            success: Whether operation succeeded
            error: Error message if failed
        """
        timestamp = datetime.utcnow()

        with self._lock:
            # Record operation
            self._operations.append(
                {
                    "operation": operation,
                    "key": key,
                    "cache_level": cache_level,
                    "duration": duration,
                    "success": success,
                    "error": error,
                    "timestamp": timestamp,
                }
            )

            # Update key stats
            if operation == "get":
                if success:
                    self._key_stats[key]["hits"] += 1
                    if cache_level == "l1":
                        self._l1_stats["hits"] += 1
                    elif cache_level == "l2":
                        self._l2_stats["hits"] += 1
                else:
                    self._key_stats[key]["misses"] += 1
                    if cache_level == "l1":
                        self._l1_stats["misses"] += 1
                    elif cache_level == "l2":
                        self._l2_stats["misses"] += 1
            elif operation == "set":
                self._key_stats[key]["sets"] += 1
                if cache_level == "l1":
                    self._l1_stats["sets"] += 1
                elif cache_level == "l2":
                    self._l2_stats["sets"] += 1
            elif operation == "delete":
                self._key_stats[key]["deletes"] += 1

            # Record timing if provided
            if duration is not None:
                self._timing_stats.append(
                    {
                        "operation": operation,
                        "cache_level": cache_level,
                        "duration": duration,
                        "timestamp": timestamp,
                    }
                )

            # Record error if any
            if not success and error:
                self._errors.append(
                    {
                        "operation": operation,
                        "key": key,
                        "cache_level": cache_level,
                        "error": error,
                        "timestamp": timestamp,
                    }
                )

    def get_overall_stats(self) -> Dict:
        """Get overall cache performance statistics."""
        with self._lock:
            # Calculate hit rates
            total_l1_ops = self._l1_stats["hits"] + self._l1_stats["misses"]
            total_l2_ops = self._l2_stats["hits"] + self._l2_stats["misses"]

            l1_hit_rate = (
                (self._l1_stats["hits"] / total_l1_ops * 100) if total_l1_ops > 0 else 0
            )
            l2_hit_rate = (
                (self._l2_stats["hits"] / total_l2_ops * 100) if total_l2_ops > 0 else 0
            )

            # Overall hit rate
            total_hits = self._l1_stats["hits"] + self._l2_stats["hits"]
            total_misses = self._l1_stats["misses"] + self._l2_stats["misses"]
            total_ops = total_hits + total_misses
            overall_hit_rate = (total_hits / total_ops * 100) if total_ops > 0 else 0

            # Calculate timing stats
            timing_list = list(self._timing_stats)
            if timing_list:
                durations = [t["duration"] for t in timing_list]
                sorted_durations = sorted(durations)
                p95_idx = int(len(sorted_durations) * 0.95)
                p99_idx = int(len(sorted_durations) * 0.99)

                p95_duration = (
                    sorted_durations[p95_idx] if p95_idx < len(sorted_durations) else 0
                )
                p99_duration = (
                    sorted_durations[p99_idx] if p99_idx < len(sorted_durations) else 0
                )
            else:
                p95_duration = 0
                p99_duration = 0

            return {
                "overall": {
                    "total_operations": len(self._operations),
                    "total_hits": total_hits,
                    "total_misses": total_misses,
                    "hit_rate": round(overall_hit_rate, 2),
                    "error_count": len(self._errors),
                },
                "l1_cache": {
                    "hits": self._l1_stats["hits"],
                    "misses": self._l1_stats["misses"],
                    "sets": self._l1_stats["sets"],
                    "hit_rate": round(l1_hit_rate, 2),
                    "total_operations": total_l1_ops,
                },
                "l2_cache": {
                    "hits": self._l2_stats["hits"],
                    "misses": self._l2_stats["misses"],
                    "sets": self._l2_stats["sets"],
                    "hit_rate": round(l2_hit_rate, 2),
                    "total_operations": total_l2_ops,
                },
                "performance": {
                    "avg_duration": sum(d["duration"] for d in timing_list)
                    / len(timing_list)
                    if timing_list
                    else 0,
                    "p95_duration": p95_duration,
                    "p99_duration": p99_duration,
                    "min_duration": min(d["duration"] for d in timing_list)
                    if timing_list
                    else 0,
                    "max_duration": max(d["duration"] for d in timing_list)
                    if timing_list
                    else 0,
                },
                "timestamp": datetime.utcnow().isoformat(),
            }

    def get_key_stats(self, limit: int = 20) -> List[Dict]:
        """
        Get statistics for top keys by access frequency.

        Args:
            limit: Maximum number of keys to return

        Returns:
            List of key statistics
        """
        with self._lock:
            # Calculate stats for each key
            key_list = []
            for key, stats in self._key_stats.items():
                total_ops = (
                    stats["hits"] + stats["misses"] + stats["sets"] + stats["deletes"]
                )
                hit_rate = (
                    (stats["hits"] / (stats["hits"] + stats["misses"]) * 100)
                    if (stats["hits"] + stats["misses"]) > 0
                    else 0
                )

                key_list.append(
                    {
                        "key": key,
                        "hits": stats["hits"],
                        "misses": stats["misses"],
                        "sets": stats["sets"],
                        "deletes": stats["deletes"],
                        "total_operations": total_ops,
                        "hit_rate": round(hit_rate, 2),
                    }
                )

            # Sort by total operations
            key_list.sort(key=lambda x: x["total_operations"], reverse=True)

            return key_list[:limit]

    def get_recent_errors(self, limit: int = 50) -> List[Dict]:
        """
        Get recent cache errors.

        Args:
            limit: Maximum number of errors to return

        Returns:
            List of error records
        """
        with self._lock:
            return [
                {
                    "operation": e["operation"],
                    "key": e["key"],
                    "cache_level": e["cache_level"],
                    "error": e["error"],
                    "timestamp": e["timestamp"].isoformat(),
                }
                for e in list(self._errors)[-limit:]
            ]

    def get_trends(self, hours: int = 24) -> Dict:
        """
        Get cache performance trends over time.

        Args:
            hours: Number of hours to look back

        Returns:
            Dictionary with trend data
        """
        with self._lock:
            cutoff = datetime.utcnow() - timedelta(hours=hours)

            # Filter recent operations
            recent_ops = [op for op in self._operations if op["timestamp"] >= cutoff]

            # Group by hour
            hourly_stats = defaultdict(
                lambda: {"hits": 0, "misses": 0, "sets": 0, "deletes": 0, "errors": 0}
            )

            for op in recent_ops:
                hour_key = op["timestamp"].replace(minute=0, second=0, microsecond=0)
                if op["operation"] == "get":
                    if op["success"]:
                        hourly_stats[hour_key]["hits"] += 1
                    else:
                        hourly_stats[hour_key]["misses"] += 1
                elif op["operation"] == "set":
                    hourly_stats[hour_key]["sets"] += 1
                elif op["operation"] == "delete":
                    hourly_stats[hour_key]["deletes"] += 1

                if not op["success"]:
                    hourly_stats[hour_key]["errors"] += 1

            # Convert to list
            trends = []
            for hour, stats in sorted(hourly_stats.items()):
                total_ops = stats["hits"] + stats["misses"]
                hit_rate = (stats["hits"] / total_ops * 100) if total_ops > 0 else 0

                trends.append(
                    {
                        "hour": hour.isoformat(),
                        "hits": stats["hits"],
                        "misses": stats["misses"],
                        "sets": stats["sets"],
                        "deletes": stats["deletes"],
                        "errors": stats["errors"],
                        "hit_rate": round(hit_rate, 2),
                    }
                )

            return {
                "period_hours": hours,
                "trends": trends,
                "timestamp": datetime.utcnow().isoformat(),
            }

    def get_recommendations(self) -> List[Dict]:
        """
        Get cache optimization recommendations.

        Returns:
            List of recommendations
        """
        recommendations = []

        with self._lock:
            stats = self.get_overall_stats()

            # Check overall hit rate
            overall_hit_rate = stats["overall"]["hit_rate"]
            if overall_hit_rate < 70:
                recommendations.append(
                    {
                        "type": "hit_rate_low",
                        "severity": "high" if overall_hit_rate < 50 else "medium",
                        "issue": f"Overall cache hit rate is {overall_hit_rate:.1f}% (target: > 80%)",
                        "recommendation": "Consider increasing cache TTLs or implementing cache warming",
                        "current_value": overall_hit_rate,
                        "target_value": 80,
                    }
                )

            # Check L1 vs L2 hit rates
            l1_hit_rate = stats["l1_cache"]["hit_rate"]
            l2_hit_rate = stats["l2_cache"]["hit_rate"]

            if l1_hit_rate < 50 and l2_hit_rate > 70:
                recommendations.append(
                    {
                        "type": "l1_cache_inefficient",
                        "severity": "medium",
                        "issue": f"L1 cache hit rate ({l1_hit_rate:.1f}%) is much lower than L2 ({l2_hit_rate:.1f}%)",
                        "recommendation": "Consider increasing L1 cache size or TTL",
                        "current_l1_hit_rate": l1_hit_rate,
                        "current_l2_hit_rate": l2_hit_rate,
                    }
                )

            # Check error rate
            error_count = stats["overall"]["error_count"]
            total_ops = stats["overall"]["total_operations"]
            if total_ops > 0:
                error_rate = error_count / total_ops * 100
                if error_rate > 1:
                    recommendations.append(
                        {
                            "type": "error_rate_high",
                            "severity": "high" if error_rate > 5 else "medium",
                            "issue": f"Cache error rate is {error_rate:.2f}%",
                            "recommendation": "Review cache errors and check Redis connectivity",
                            "error_count": error_count,
                            "total_operations": total_ops,
                        }
                    )

            # Check performance
            p95_duration = stats["performance"]["p95_duration"]
            if p95_duration > 0.01:  # > 10ms
                recommendations.append(
                    {
                        "type": "performance_slow",
                        "severity": "medium",
                        "issue": f"Cache p95 operation time is {p95_duration*1000:.2f}ms (target: < 10ms)",
                        "recommendation": "Review cache configuration and network latency",
                        "current_p95_ms": p95_duration * 1000,
                    }
                )

        return recommendations


# Global monitor instance
_cache_monitor: Optional[CachePerformanceMonitor] = None
_cache_monitor_lock = Lock()


def get_cache_monitor() -> CachePerformanceMonitor:
    """Get global cache performance monitor instance."""
    global _cache_monitor
    with _cache_monitor_lock:
        if _cache_monitor is None:
            _cache_monitor = CachePerformanceMonitor()
        return _cache_monitor


def record_cache_operation(
    operation: str,
    key: str,
    cache_level: Optional[str] = None,
    duration: Optional[float] = None,
    success: bool = True,
    error: Optional[str] = None,
):
    """Record a cache operation."""
    monitor = get_cache_monitor()
    monitor.record_operation(operation, key, cache_level, duration, success, error)


def get_cache_performance_stats() -> Dict:
    """Get cache performance statistics."""
    monitor = get_cache_monitor()
    return monitor.get_overall_stats()


def get_cache_recommendations() -> List[Dict]:
    """Get cache optimization recommendations."""
    monitor = get_cache_monitor()
    return monitor.get_recommendations()

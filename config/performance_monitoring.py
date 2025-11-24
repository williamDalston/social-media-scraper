"""
Performance monitoring: slow query detection, memory leak detection, resource tracking.
"""
import os
import time
import logging
import tracemalloc
import gc
from typing import Dict, List, Optional, Callable
from collections import deque
from datetime import datetime, timedelta
from functools import wraps

logger = logging.getLogger(__name__)

# Performance tracking
_slow_queries = deque(maxlen=100)
_memory_snapshots = deque(maxlen=50)
_query_times = deque(maxlen=1000)
_memory_tracking_enabled = False

# Thresholds
SLOW_QUERY_THRESHOLD = 1.0  # seconds
MEMORY_LEAK_THRESHOLD_MB = 100  # MB increase per hour
MEMORY_CHECK_INTERVAL = 300  # 5 minutes


def enable_memory_tracking():
    """Enable memory leak tracking."""
    global _memory_tracking_enabled
    if not _memory_tracking_enabled:
        tracemalloc.start()
        _memory_tracking_enabled = True
        logger.info("Memory tracking enabled")


def track_slow_query(query: str, duration: float, context: Optional[Dict] = None):
    """
    Track a slow query.

    Args:
        query: Query string or description
        duration: Query duration in seconds
        context: Additional context
    """
    if duration >= SLOW_QUERY_THRESHOLD:
        _slow_queries.append(
            {
                "query": query[:200],  # Truncate long queries
                "duration": duration,
                "timestamp": datetime.utcnow().isoformat(),
                "context": context or {},
            }
        )
        logger.warning(
            f"Slow query detected: {duration:.3f}s",
            extra={"query": query[:200], "duration": duration, "context": context},
        )


def track_query_time(duration: float):
    """Track query time for statistics."""
    _query_times.append({"duration": duration, "timestamp": time.time()})


def get_slow_queries(limit: int = 10) -> List[Dict]:
    """
    Get recent slow queries.

    Args:
        limit: Maximum number of queries to return

    Returns:
        List of slow query records
    """
    return list(_slow_queries)[-limit:]


def get_query_statistics() -> Dict:
    """
    Get query performance statistics.

    Returns:
        Dictionary with statistics
    """
    if not _query_times:
        return {
            "count": 0,
            "avg_duration": 0,
            "max_duration": 0,
            "min_duration": 0,
            "p95_duration": 0,
            "p99_duration": 0,
        }

    durations = [q["duration"] for q in _query_times]
    sorted_durations = sorted(durations)

    return {
        "count": len(durations),
        "avg_duration": sum(durations) / len(durations),
        "max_duration": max(durations),
        "min_duration": min(durations),
        "p95_duration": sorted_durations[int(len(sorted_durations) * 0.95)]
        if sorted_durations
        else 0,
        "p99_duration": sorted_durations[int(len(sorted_durations) * 0.99)]
        if sorted_durations
        else 0,
    }


def check_memory_leak() -> Optional[Dict]:
    """
    Check for memory leaks by comparing current memory with previous snapshots.

    Returns:
        Dictionary with leak information if detected, None otherwise
    """
    if not _memory_tracking_enabled:
        return None

    try:
        current, peak = tracemalloc.get_traced_memory()
        current_mb = current / (1024 * 1024)
        peak_mb = peak / (1024 * 1024)

        snapshot = {
            "current_mb": current_mb,
            "peak_mb": peak_mb,
            "timestamp": datetime.utcnow(),
        }

        _memory_snapshots.append(snapshot)

        # Check for leak if we have enough snapshots
        if len(_memory_snapshots) >= 2:
            first = _memory_snapshots[0]
            last = _memory_snapshots[-1]

            time_diff = (
                last["timestamp"] - first["timestamp"]
            ).total_seconds() / 3600  # hours
            memory_diff = last["current_mb"] - first["current_mb"]

            if time_diff > 0:
                memory_per_hour = memory_diff / time_diff

                if memory_per_hour > MEMORY_LEAK_THRESHOLD_MB:
                    return {
                        "detected": True,
                        "memory_increase_mb": memory_diff,
                        "memory_per_hour_mb": memory_per_hour,
                        "time_span_hours": time_diff,
                        "current_mb": current_mb,
                        "peak_mb": peak_mb,
                    }

        return {"detected": False, "current_mb": current_mb, "peak_mb": peak_mb}
    except Exception as e:
        logger.error(f"Memory leak check failed: {e}")
        return None


def get_memory_stats() -> Dict:
    """
    Get current memory statistics.

    Returns:
        Dictionary with memory statistics
    """
    try:
        import psutil

        process = psutil.Process()
        memory_info = process.memory_info()

        return {
            "rss_mb": memory_info.rss / (1024 * 1024),  # Resident Set Size
            "vms_mb": memory_info.vms / (1024 * 1024),  # Virtual Memory Size
            "percent": process.memory_percent(),
            "available_mb": psutil.virtual_memory().available / (1024 * 1024),
        }
    except Exception as e:
        logger.error(f"Failed to get memory stats: {e}")
        return {}


def monitor_query_time(threshold: float = SLOW_QUERY_THRESHOLD):
    """
    Decorator to monitor query execution time.

    Usage:
        @monitor_query_time(threshold=0.5)
        def execute_query():
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                track_query_time(duration)

                if duration >= threshold:
                    track_slow_query(
                        query=f"{func.__name__}",
                        duration=duration,
                        context={"function": func.__name__, "args": str(args)[:100]},
                    )

                return result
            except Exception as e:
                duration = time.time() - start_time
                track_query_time(duration)
                raise

        return wrapper

    return decorator


def get_resource_usage_trends(hours: int = 24) -> Dict:
    """
    Get resource usage trends over time.

    Args:
        hours: Number of hours to look back

    Returns:
        Dictionary with resource trends
    """
    # This would ideally pull from time-series data
    # For now, return current stats
    memory_stats = get_memory_stats()
    query_stats = get_query_statistics()

    return {
        "memory": memory_stats,
        "queries": query_stats,
        "slow_queries_count": len(_slow_queries),
        "timestamp": datetime.utcnow().isoformat(),
    }


def check_performance_budgets() -> Dict:
    """
    Check performance budgets and return violations.

    Returns:
        Dictionary with budget violations
    """
    violations = []

    # Check query performance budget
    query_stats = get_query_statistics()
    if query_stats["p95_duration"] > 0.5:  # 500ms p95 budget
        violations.append(
            {
                "metric": "query_p95_duration",
                "value": query_stats["p95_duration"],
                "budget": 0.5,
                "severity": "high" if query_stats["p95_duration"] > 1.0 else "medium",
            }
        )

    # Check memory budget
    memory_stats = get_memory_stats()
    if memory_stats.get("rss_mb", 0) > 1000:  # 1GB budget
        violations.append(
            {
                "metric": "memory_rss",
                "value": memory_stats["rss_mb"],
                "budget": 1000,
                "severity": "high" if memory_stats["rss_mb"] > 2000 else "medium",
            }
        )

    # Check slow query budget
    if len(_slow_queries) > 10:
        violations.append(
            {
                "metric": "slow_queries_count",
                "value": len(_slow_queries),
                "budget": 10,
                "severity": "medium",
            }
        )

    return {
        "violations": violations,
        "violation_count": len(violations),
        "timestamp": datetime.utcnow().isoformat(),
    }

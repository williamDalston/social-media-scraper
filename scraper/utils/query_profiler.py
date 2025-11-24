"""
Database query optimization and profiling utilities.
"""
import time
import logging
from typing import Dict, List, Optional, Callable
from functools import wraps
from collections import defaultdict, deque
from threading import Lock
from sqlalchemy import event
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class QueryProfiler:
    """Database query profiler for identifying slow queries."""

    def __init__(self, max_queries: int = 10000, slow_query_threshold: float = 0.1):
        """
        Initialize query profiler.

        Args:
            max_queries: Maximum number of queries to track
            slow_query_threshold: Threshold in seconds for slow queries
        """
        self.max_queries = max_queries
        self.slow_query_threshold = slow_query_threshold
        self._lock = Lock()

        # Query tracking
        self.queries = deque(maxlen=max_queries)
        self.slow_queries = deque(maxlen=1000)

        # Statistics
        self.query_counts = defaultdict(int)
        self.query_times = defaultdict(list)
        self.query_errors = defaultdict(int)

    def record_query(
        self, statement: str, duration: float, error: Optional[Exception] = None
    ):
        """
        Record a database query.

        Args:
            statement: SQL statement
            duration: Query duration in seconds
            error: Optional error that occurred
        """
        with self._lock:
            normalized = self._normalize_statement(statement)

            self.queries.append(
                {
                    "statement": statement,
                    "normalized": normalized,
                    "duration": duration,
                    "timestamp": time.time(),
                    "error": str(error) if error else None,
                }
            )

            # Track statistics
            self.query_counts[normalized] += 1
            self.query_times[normalized].append(duration)

            # Keep only recent times
            if len(self.query_times[normalized]) > 1000:
                self.query_times[normalized] = self.query_times[normalized][-1000:]

            # Track slow queries
            if duration > self.slow_query_threshold:
                self.slow_queries.append(
                    {
                        "statement": statement,
                        "normalized": normalized,
                        "duration": duration,
                        "timestamp": time.time(),
                    }
                )

            # Track errors
            if error:
                self.query_errors[normalized] += 1

    def _normalize_statement(self, statement: str) -> str:
        """Normalize SQL statement for grouping."""
        # Remove whitespace
        normalized = " ".join(statement.split())

        # Replace specific values with placeholders
        import re

        # Replace numbers
        normalized = re.sub(r"\b\d+\b", "?", normalized)
        # Replace strings
        normalized = re.sub(r"'[^']*'", "'?'", normalized)
        normalized = re.sub(r'"[^"]*"', '"?"', normalized)

        return normalized

    def get_slow_queries(self, limit: int = 10) -> List[Dict]:
        """Get slowest queries."""
        with self._lock:
            sorted_queries = sorted(
                self.slow_queries, key=lambda x: x["duration"], reverse=True
            )
            return sorted_queries[:limit]

    def get_query_stats(self, normalized: Optional[str] = None) -> Dict:
        """
        Get query statistics.

        Args:
            normalized: Optional normalized statement to filter by

        Returns:
            Dictionary with query statistics
        """
        with self._lock:
            if normalized:
                times = self.query_times.get(normalized, [])
                return {
                    "normalized": normalized,
                    "count": self.query_counts.get(normalized, 0),
                    "errors": self.query_errors.get(normalized, 0),
                    "avg_time": sum(times) / len(times) if times else 0,
                    "min_time": min(times) if times else 0,
                    "max_time": max(times) if times else 0,
                    "p95_time": self._percentile(times, 95) if times else 0,
                    "p99_time": self._percentile(times, 99) if times else 0,
                }
            else:
                # Overall statistics
                all_times = []
                for times in self.query_times.values():
                    all_times.extend(times)

                return {
                    "total_queries": len(self.queries),
                    "unique_queries": len(self.query_counts),
                    "slow_queries": len(self.slow_queries),
                    "total_errors": sum(self.query_errors.values()),
                    "overall_avg_time": sum(all_times) / len(all_times)
                    if all_times
                    else 0,
                    "overall_min_time": min(all_times) if all_times else 0,
                    "overall_max_time": max(all_times) if all_times else 0,
                    "by_query": {
                        norm: self.get_query_stats(norm)
                        for norm in list(self.query_counts.keys())[:20]  # Top 20
                    },
                }

    def get_recommendations(self) -> List[str]:
        """Get query optimization recommendations."""
        recommendations = []

        stats = self.get_query_stats()
        slow_queries = self.get_slow_queries(limit=5)

        # Check for slow queries
        if slow_queries:
            recommendations.append(
                f"Found {len(self.slow_queries)} slow queries (> {self.slow_query_threshold}s). "
                f"Review and optimize the slowest queries."
            )

            for query in slow_queries[:3]:
                recommendations.append(
                    f"Slow query detected: {query['normalized'][:100]}... "
                    f"(avg {query['duration']:.3f}s). Consider adding indexes or optimizing."
                )

        # Check for frequent queries
        for normalized, count in sorted(
            self.query_counts.items(), key=lambda x: x[1], reverse=True
        )[:5]:
            if count > 100:
                avg_time = sum(self.query_times[normalized]) / len(
                    self.query_times[normalized]
                )
                if avg_time > 0.05:  # 50ms
                    recommendations.append(
                        f"Frequent query ({count} times, avg {avg_time*1000:.2f}ms): "
                        f"{normalized[:80]}... Consider caching or optimization."
                    )

        # Check for errors
        error_queries = [
            (norm, count) for norm, count in self.query_errors.items() if count > 0
        ]
        if error_queries:
            recommendations.append(
                f"Found {len(error_queries)} queries with errors. Review error handling."
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
        """Get all profiling statistics."""
        return {
            "overall": self.get_query_stats(),
            "slow_queries": self.get_slow_queries(limit=10),
            "recommendations": self.get_recommendations(),
        }

    def reset(self):
        """Reset all profiling data."""
        with self._lock:
            self.queries.clear()
            self.slow_queries.clear()
            self.query_counts.clear()
            self.query_times.clear()
            self.query_errors.clear()


# Global profiler instance
_profiler = None


def get_profiler() -> QueryProfiler:
    """Get or create global query profiler instance."""
    global _profiler
    if _profiler is None:
        _profiler = QueryProfiler()
    return _profiler


def profile_query(func: Callable):
    """Decorator to profile database queries."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        error = None
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            error = e
            raise
        finally:
            duration = time.time() - start_time
            profiler = get_profiler()
            # Try to extract SQL statement from result if possible
            statement = f"{func.__name__}({len(args)} args, {len(kwargs)} kwargs)"
            profiler.record_query(statement, duration, error)

    return wrapper


def setup_query_listening(engine: Engine):
    """
    Set up SQLAlchemy event listeners for query profiling.

    Args:
        engine: SQLAlchemy engine
    """
    profiler = get_profiler()

    @event.listens_for(engine, "before_cursor_execute")
    def receive_before_cursor_execute(
        conn, cursor, statement, parameters, context, executemany
    ):
        context._query_start_time = time.time()
        context._query_statement = statement

    @event.listens_for(engine, "after_cursor_execute")
    def receive_after_cursor_execute(
        conn, cursor, statement, parameters, context, executemany
    ):
        total = time.time() - context._query_start_time
        profiler.record_query(statement, total)

    @event.listens_for(engine, "handle_error")
    def receive_handle_error(exception_context):
        statement = getattr(exception_context, "statement", "unknown")
        profiler.record_query(statement, 0, exception_context.original_exception)

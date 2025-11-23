"""
Database performance monitoring and optimization for production.
"""
import os
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import deque, defaultdict
from threading import Lock
from sqlalchemy import event, Engine
from sqlalchemy.engine import Connection

logger = logging.getLogger(__name__)


class DatabasePerformanceMonitor:
    """Monitor database performance for production optimization."""
    
    def __init__(self, max_history: int = 10000):
        """
        Initialize database performance monitor.
        
        Args:
            max_history: Maximum number of queries to track
        """
        self.max_history = max_history
        self._lock = Lock()
        
        # Track queries
        self._queries = deque(maxlen=max_history)
        self._slow_queries = deque(maxlen=1000)  # Keep last 1000 slow queries
        self._query_patterns = defaultdict(lambda: {
            'count': 0,
            'total_time': 0.0,
            'min_time': float('inf'),
            'max_time': 0.0,
            'errors': 0
        })
        
        # Connection pool stats
        self._pool_stats = {
            'total_connections': 0,
            'active_connections': 0,
            'idle_connections': 0,
            'overflow_connections': 0
        }
        
        # Track errors
        self._errors = deque(maxlen=1000)
        
        # Thresholds
        self.slow_query_threshold = float(os.getenv('DB_SLOW_QUERY_THRESHOLD', '0.5'))  # 500ms
        
    def record_query(
        self,
        query: str,
        duration: float,
        success: bool = True,
        error: Optional[str] = None,
        context: Optional[Dict] = None
    ):
        """
        Record a database query.
        
        Args:
            query: Query string or description
            duration: Query duration in seconds
            success: Whether query succeeded
            error: Error message if failed
            context: Additional context
        """
        timestamp = datetime.utcnow()
        
        with self._lock:
            # Record query
            query_record = {
                'query': query[:500] if query else 'unknown',  # Truncate long queries
                'duration': duration,
                'success': success,
                'error': error,
                'context': context or {},
                'timestamp': timestamp
            }
            
            self._queries.append(query_record)
            
            # Track slow queries
            if duration >= self.slow_query_threshold:
                self._slow_queries.append(query_record)
                logger.warning(
                    f"Slow query detected: {duration:.3f}s",
                    extra={
                        'query': query[:200],
                        'duration': duration,
                        'context': context
                    }
                )
            
            # Track query patterns (simplified query string)
            pattern = self._simplify_query(query)
            pattern_stats = self._query_patterns[pattern]
            pattern_stats['count'] += 1
            pattern_stats['total_time'] += duration
            pattern_stats['min_time'] = min(pattern_stats['min_time'], duration)
            pattern_stats['max_time'] = max(pattern_stats['max_time'], duration)
            if not success:
                pattern_stats['errors'] += 1
            
            # Record error if any
            if not success and error:
                self._errors.append({
                    'query': query[:200],
                    'error': error,
                    'duration': duration,
                    'timestamp': timestamp
                })
    
    def _simplify_query(self, query: str) -> str:
        """
        Simplify query string for pattern matching.
        
        Args:
            query: Full query string
            
        Returns:
            Simplified pattern
        """
        if not query:
            return 'unknown'
        
        # Remove specific values, keep structure
        simplified = query.lower()
        
        # Replace numbers with ?
        import re
        simplified = re.sub(r'\d+', '?', simplified)
        
        # Replace quoted strings with ?
        simplified = re.sub(r"'[^']*'", '?', simplified)
        simplified = re.sub(r'"[^"]*"', '?', simplified)
        
        # Truncate to first 100 chars
        simplified = simplified[:100]
        
        return simplified
    
    def update_pool_stats(
        self,
        total: int,
        active: int,
        idle: int,
        overflow: int
    ):
        """
        Update connection pool statistics.
        
        Args:
            total: Total connections
            active: Active connections
            idle: Idle connections
            overflow: Overflow connections
        """
        with self._lock:
            self._pool_stats = {
                'total_connections': total,
                'active_connections': active,
                'idle_connections': idle,
                'overflow_connections': overflow,
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def get_overall_stats(self) -> Dict:
        """Get overall database performance statistics."""
        with self._lock:
            if not self._queries:
                return {
                    'total_queries': 0,
                    'slow_queries_count': 0,
                    'error_count': 0
                }
            
            # Calculate statistics
            durations = [q['duration'] for q in self._queries]
            sorted_durations = sorted(durations)
            
            p50_idx = int(len(sorted_durations) * 0.50)
            p95_idx = int(len(sorted_durations) * 0.95)
            p99_idx = int(len(sorted_durations) * 0.99)
            
            p50 = sorted_durations[p50_idx] if p50_idx < len(sorted_durations) else 0
            p95 = sorted_durations[p95_idx] if p95_idx < len(sorted_durations) else 0
            p99 = sorted_durations[p99_idx] if p99_idx < len(sorted_durations) else 0
            
            # Calculate success rate
            success_count = sum(1 for q in self._queries if q['success'])
            total_count = len(self._queries)
            success_rate = (success_count / total_count * 100) if total_count > 0 else 0
            
            return {
                'total_queries': total_count,
                'success_count': success_count,
                'error_count': len(self._errors),
                'success_rate': round(success_rate, 2),
                'slow_queries_count': len(self._slow_queries),
                'performance': {
                    'avg_duration': sum(durations) / len(durations) if durations else 0,
                    'min_duration': min(durations) if durations else 0,
                    'max_duration': max(durations) if durations else 0,
                    'p50_duration': p50,
                    'p95_duration': p95,
                    'p99_duration': p99
                },
                'connection_pool': self._pool_stats,
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def get_slow_queries(self, limit: int = 20) -> List[Dict]:
        """
        Get recent slow queries.
        
        Args:
            limit: Maximum number of queries to return
            
        Returns:
            List of slow query records
        """
        with self._lock:
            return [
                {
                    'query': q['query'],
                    'duration': round(q['duration'], 3),
                    'success': q['success'],
                    'error': q.get('error'),
                    'context': q.get('context', {}),
                    'timestamp': q['timestamp'].isoformat()
                }
                for q in list(self._slow_queries)[-limit:]
            ]
    
    def get_query_patterns(self, limit: int = 20) -> List[Dict]:
        """
        Get statistics for query patterns.
        
        Args:
            limit: Maximum number of patterns to return
            
        Returns:
            List of pattern statistics
        """
        with self._lock:
            patterns = []
            for pattern, stats in self._query_patterns.items():
                avg_time = (
                    stats['total_time'] / stats['count']
                    if stats['count'] > 0 else 0
                )
                
                patterns.append({
                    'pattern': pattern,
                    'count': stats['count'],
                    'avg_time': round(avg_time, 3),
                    'min_time': round(stats['min_time'], 3) if stats['min_time'] != float('inf') else 0,
                    'max_time': round(stats['max_time'], 3),
                    'total_time': round(stats['total_time'], 3),
                    'errors': stats['errors'],
                    'error_rate': round((stats['errors'] / stats['count'] * 100) if stats['count'] > 0 else 0, 2)
                })
            
            # Sort by total time (descending)
            patterns.sort(key=lambda x: x['total_time'], reverse=True)
            
            return patterns[:limit]
    
    def get_recent_errors(self, limit: int = 50) -> List[Dict]:
        """
        Get recent database errors.
        
        Args:
            limit: Maximum number of errors to return
            
        Returns:
            List of error records
        """
        with self._lock:
            return [
                {
                    'query': e['query'],
                    'error': e['error'],
                    'duration': round(e['duration'], 3),
                    'timestamp': e['timestamp'].isoformat()
                }
                for e in list(self._errors)[-limit:]
            ]
    
    def get_trends(self, hours: int = 24) -> Dict:
        """
        Get database performance trends over time.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dictionary with trend data
        """
        with self._lock:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            
            # Filter recent queries
            recent_queries = [
                q for q in self._queries
                if q['timestamp'] >= cutoff
            ]
            
            # Group by hour
            hourly_stats = defaultdict(lambda: {
                'count': 0,
                'total_time': 0.0,
                'errors': 0,
                'slow_queries': 0
            })
            
            for q in recent_queries:
                hour_key = q['timestamp'].replace(minute=0, second=0, microsecond=0)
                stats = hourly_stats[hour_key]
                stats['count'] += 1
                stats['total_time'] += q['duration']
                if not q['success']:
                    stats['errors'] += 1
                if q['duration'] >= self.slow_query_threshold:
                    stats['slow_queries'] += 1
            
            # Convert to list
            trends = []
            for hour, stats in sorted(hourly_stats.items()):
                avg_time = (
                    stats['total_time'] / stats['count']
                    if stats['count'] > 0 else 0
                )
                
                trends.append({
                    'hour': hour.isoformat(),
                    'count': stats['count'],
                    'avg_duration': round(avg_time, 3),
                    'errors': stats['errors'],
                    'slow_queries': stats['slow_queries']
                })
            
            return {
                'period_hours': hours,
                'trends': trends,
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def get_recommendations(self) -> List[Dict]:
        """
        Get database optimization recommendations.
        
        Returns:
            List of recommendations
        """
        recommendations = []
        
        with self._lock:
            stats = self.get_overall_stats()
            
            # Check p95 query time
            p95 = stats['performance']['p95_duration']
            if p95 > 0.1:  # > 100ms
                recommendations.append({
                    'type': 'slow_queries',
                    'severity': 'high' if p95 > 0.5 else 'medium',
                    'issue': f'Database p95 query time is {p95*1000:.2f}ms (target: < 100ms)',
                    'recommendation': 'Review slow queries and add indexes if needed',
                    'current_p95_ms': p95 * 1000
                })
            
            # Check error rate
            error_rate = stats.get('error_count', 0) / max(stats.get('total_queries', 1), 1) * 100
            if error_rate > 1:
                recommendations.append({
                    'type': 'high_error_rate',
                    'severity': 'high' if error_rate > 5 else 'medium',
                    'issue': f'Database error rate is {error_rate:.2f}%',
                    'recommendation': 'Review error logs and fix connection issues',
                    'error_count': stats.get('error_count', 0),
                    'total_queries': stats.get('total_queries', 0)
                })
            
            # Check slow query count
            slow_count = stats.get('slow_queries_count', 0)
            if slow_count > 10:
                recommendations.append({
                    'type': 'many_slow_queries',
                    'severity': 'medium',
                    'issue': f'{slow_count} slow queries detected',
                    'recommendation': 'Review slow query patterns and optimize',
                    'slow_query_count': slow_count
                })
            
            # Check connection pool
            pool_stats = stats.get('connection_pool', {})
            active = pool_stats.get('active_connections', 0)
            total = pool_stats.get('total_connections', 0)
            if total > 0:
                utilization = (active / total * 100)
                if utilization > 80:
                    recommendations.append({
                        'type': 'high_pool_utilization',
                        'severity': 'warning',
                        'issue': f'Connection pool utilization is {utilization:.1f}%',
                        'recommendation': 'Consider increasing pool size',
                        'active_connections': active,
                        'total_connections': total
                    })
        
        return recommendations


# Global monitor instance
_db_monitor: Optional[DatabasePerformanceMonitor] = None
_db_monitor_lock = Lock()


def get_db_monitor() -> DatabasePerformanceMonitor:
    """Get global database performance monitor instance."""
    global _db_monitor
    with _db_monitor_lock:
        if _db_monitor is None:
            _db_monitor = DatabasePerformanceMonitor()
        return _db_monitor


def setup_query_monitoring(engine: Engine):
    """
    Set up SQLAlchemy event listeners for query monitoring.
    
    Args:
        engine: SQLAlchemy engine
    """
    monitor = get_db_monitor()
    
    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Record query start time."""
        conn.info.setdefault("query_start_time", []).append(time.time())
    
    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Record query completion."""
        try:
            query_start_time = conn.info["query_start_time"].pop(-1)
            duration = time.time() - query_start_time
            
            # Record query
            monitor.record_query(
                query=statement,
                duration=duration,
                success=True,
                context={
                    'parameters': str(parameters)[:200] if parameters else None,
                    'executemany': executemany
                }
            )
        except Exception as e:
            logger.debug(f"Error recording query: {e}")
    
    @event.listens_for(engine, "handle_error")
    def handle_error(context):
        """Record query errors."""
        try:
            statement = context.statement if hasattr(context, 'statement') else 'unknown'
            error = str(context.original_exception) if hasattr(context, 'original_exception') else 'unknown'
            
            # Try to get duration if available
            duration = 0.0
            if hasattr(context, 'connection') and context.connection:
                if 'query_start_time' in context.connection.info:
                    start_times = context.connection.info.get('query_start_time', [])
                    if start_times:
                        duration = time.time() - start_times[-1]
            
            monitor.record_query(
                query=statement,
                duration=duration,
                success=False,
                error=error
            )
        except Exception as e:
            logger.debug(f"Error recording query error: {e}")


def record_db_query(query: str, duration: float, success: bool = True, error: Optional[str] = None):
    """Record a database query manually."""
    monitor = get_db_monitor()
    monitor.record_query(query, duration, success, error)


def get_db_performance_stats() -> Dict:
    """Get database performance statistics."""
    monitor = get_db_monitor()
    return monitor.get_overall_stats()


def get_db_recommendations() -> List[Dict]:
    """Get database optimization recommendations."""
    monitor = get_db_monitor()
    return monitor.get_recommendations()


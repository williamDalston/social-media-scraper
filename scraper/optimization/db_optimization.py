"""
Database optimization utilities - query optimization, connection pooling, monitoring.
"""
import logging
import time
from functools import wraps
from typing import Callable, Any
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import Pool

logger = logging.getLogger(__name__)

# Query performance tracking
query_stats = {
    'total_queries': 0,
    'slow_queries': [],
    'query_times': []
}

SLOW_QUERY_THRESHOLD = 1.0  # 1 second

@event.listens_for(Engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Track query execution time."""
    conn.info.setdefault('query_start_time', []).append(time.time())

@event.listens_for(Engine, "after_cursor_execute")
def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log slow queries."""
    total = time.time() - conn.info['query_start_time'].pop()
    
    query_stats['total_queries'] += 1
    query_stats['query_times'].append(total)
    
    # Keep only last 1000 query times
    if len(query_stats['query_times']) > 1000:
        query_stats['query_times'] = query_stats['query_times'][-1000:]
    
    if total > SLOW_QUERY_THRESHOLD:
        query_stats['slow_queries'].append({
            'statement': statement[:200],  # First 200 chars
            'duration': total,
            'timestamp': time.time()
        })
        
        # Keep only last 100 slow queries
        if len(query_stats['slow_queries']) > 100:
            query_stats['slow_queries'] = query_stats['slow_queries'][-100:]
        
        logger.warning(f"Slow query detected ({total:.2f}s): {statement[:200]}")

def optimize_connection_pool(engine, pool_size=5, max_overflow=10, pool_timeout=30, pool_recycle=3600):
    """
    Optimize database connection pool settings.
    
    Args:
        engine: SQLAlchemy engine
        pool_size: Number of connections to maintain
        max_overflow: Maximum overflow connections
        pool_timeout: Timeout for getting connection from pool
        pool_recycle: Recycle connections after this many seconds
    """
    engine.pool._pool.size = pool_size
    engine.pool._pool.max_overflow = max_overflow
    engine.pool._pool._timeout = pool_timeout
    engine.pool._pool._recycle = pool_recycle
    
    logger.info(f"Connection pool optimized: size={pool_size}, overflow={max_overflow}, recycle={pool_recycle}s")

def get_query_stats() -> dict:
    """Get query performance statistics."""
    if query_stats['total_queries'] == 0:
        return {
            'total_queries': 0,
            'average_time': 0,
            'slow_queries_count': 0,
            'p95_time': 0,
            'p99_time': 0
        }
    
    query_times = query_stats['query_times']
    query_times_sorted = sorted(query_times)
    
    p95_idx = int(len(query_times_sorted) * 0.95)
    p99_idx = int(len(query_times_sorted) * 0.99)
    
    return {
        'total_queries': query_stats['total_queries'],
        'average_time': sum(query_times) / len(query_times),
        'slow_queries_count': len(query_stats['slow_queries']),
        'p95_time': query_times_sorted[p95_idx] if p95_idx < len(query_times_sorted) else 0,
        'p99_time': query_times_sorted[p99_idx] if p99_idx < len(query_times_sorted) else 0,
        'slow_queries': query_stats['slow_queries'][-10:]  # Last 10 slow queries
    }

def track_query_performance(func: Callable) -> Callable:
    """Decorator to track query performance."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            
            if duration > SLOW_QUERY_THRESHOLD:
                logger.warning(f"Slow {func.__name__} took {duration:.2f}s")
            
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"{func.__name__} failed after {duration:.2f}s: {e}")
            raise
    
    return wrapper

def analyze_query_plan(engine, query: str) -> dict:
    """Analyze query execution plan."""
    try:
        with engine.connect() as conn:
            # For SQLite, use EXPLAIN QUERY PLAN
            if 'sqlite' in str(engine.url):
                result = conn.execute(text(f"EXPLAIN QUERY PLAN {query}"))
                plan = [dict(row) for row in result]
            else:
                # For PostgreSQL, use EXPLAIN ANALYZE
                result = conn.execute(text(f"EXPLAIN ANALYZE {query}"))
                plan = [dict(row) for row in result]
            
            return {
                'query': query,
                'plan': plan,
                'recommendations': _generate_recommendations(plan)
            }
    except Exception as e:
        logger.error(f"Query plan analysis failed: {e}")
        return {'error': str(e)}

def _generate_recommendations(plan: list) -> list:
    """Generate optimization recommendations from query plan."""
    recommendations = []
    
    # Check for full table scans
    for step in plan:
        step_str = str(step).lower()
        if 'scan' in step_str and 'index' not in step_str:
            recommendations.append("Consider adding an index to avoid full table scan")
    
    # Check for missing indexes
    if any('index' not in str(step).lower() for step in plan):
        recommendations.append("Query may benefit from additional indexes")
    
    return recommendations

def optimize_database_indexes(engine):
    """Create recommended indexes for common queries."""
    indexes = [
        # FactFollowersSnapshot indexes
        "CREATE INDEX IF NOT EXISTS idx_snapshot_account_date ON fact_followers_snapshot(account_key, snapshot_date)",
        "CREATE INDEX IF NOT EXISTS idx_snapshot_date ON fact_followers_snapshot(snapshot_date)",
        
        # DimAccount indexes
        "CREATE INDEX IF NOT EXISTS idx_account_platform ON dim_account(platform)",
        "CREATE INDEX IF NOT EXISTS idx_account_handle ON dim_account(handle)",
        "CREATE INDEX IF NOT EXISTS idx_account_org ON dim_account(org_name)",
    ]
    
    with engine.connect() as conn:
        for index_sql in indexes:
            try:
                conn.execute(text(index_sql))
                conn.commit()
                logger.info(f"Created index: {index_sql[:50]}...")
            except Exception as e:
                logger.warning(f"Index creation failed (may already exist): {e}")


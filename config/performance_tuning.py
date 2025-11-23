"""
Production performance tuning utilities.
"""
import os
import logging
import time
from typing import Dict, List, Optional, Any
from functools import wraps
from datetime import datetime

logger = logging.getLogger(__name__)


class PerformanceTuner:
    """Performance tuning utilities for production optimization."""
    
    @staticmethod
    def optimize_database_connections(
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_timeout: int = 30,
        pool_recycle: int = 3600
    ) -> Dict[str, Any]:
        """
        Get optimized database connection pool settings.
        
        Args:
            pool_size: Base pool size
            max_overflow: Maximum overflow connections
            pool_timeout: Connection timeout
            pool_recycle: Connection recycle time
            
        Returns:
            Dictionary with connection pool settings
        """
        # Adjust based on environment
        env = os.getenv('FLASK_ENV', 'development')
        
        if env == 'production':
            # Production: larger pools
            pool_size = int(os.getenv('DB_POOL_SIZE', pool_size * 2))
            max_overflow = int(os.getenv('DB_MAX_OVERFLOW', max_overflow * 2))
        elif env == 'development':
            # Development: smaller pools
            pool_size = max(2, pool_size // 2)
            max_overflow = max(5, max_overflow // 2)
        
        return {
            'pool_size': pool_size,
            'max_overflow': max_overflow,
            'pool_timeout': pool_timeout,
            'pool_recycle': pool_recycle,
            'pool_pre_ping': True,  # Verify connections before using
            'echo': False  # Don't log SQL in production
        }
    
    @staticmethod
    def optimize_cache_settings(
        default_timeout: int = 300,
        key_prefix: str = "hhs_scraper:"
    ) -> Dict[str, Any]:
        """
        Get optimized cache settings.
        
        Args:
            default_timeout: Default cache TTL
            key_prefix: Cache key prefix
            
        Returns:
            Dictionary with cache settings
        """
        env = os.getenv('FLASK_ENV', 'development')
        
        # Production: longer TTLs for stability
        if env == 'production':
            default_timeout = int(os.getenv('CACHE_DEFAULT_TIMEOUT', default_timeout * 2))
        
        return {
            'CACHE_DEFAULT_TIMEOUT': default_timeout,
            'CACHE_KEY_PREFIX': key_prefix,
            'CACHE_OPTIONS': {
                'socket_connect_timeout': 5,
                'socket_timeout': 5,
                'retry_on_timeout': True,
                'health_check_interval': 30,
                'max_connections': 50 if env == 'production' else 10
            }
        }
    
    @staticmethod
    def optimize_worker_settings(
        max_workers: int = 5,
        queue_prefetch: int = 4
    ) -> Dict[str, Any]:
        """
        Get optimized worker settings for Celery.
        
        Args:
            max_workers: Maximum worker threads
            queue_prefetch: Queue prefetch count
            
        Returns:
            Dictionary with worker settings
        """
        env = os.getenv('FLASK_ENV', 'development')
        
        if env == 'production':
            max_workers = int(os.getenv('CELERY_MAX_WORKERS', max_workers * 2))
            queue_prefetch = int(os.getenv('CELERY_PREFETCH', queue_prefetch * 2))
        
        return {
            'max_workers': max_workers,
            'queue_prefetch': queue_prefetch,
            'task_acks_late': True,  # Acknowledge after task completion
            'task_reject_on_worker_lost': True,  # Reject tasks if worker dies
            'worker_prefetch_multiplier': 1  # Conservative prefetch
        }
    
    @staticmethod
    def get_performance_recommendations(metrics: Dict) -> List[Dict]:
        """
        Get performance optimization recommendations based on metrics.
        
        Args:
            metrics: Performance metrics dictionary
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # Check API response times
        api_stats = metrics.get('api', {})
        if isinstance(api_stats, dict):
            for endpoint, stats in api_stats.items():
                if isinstance(stats, dict):
                    p95 = stats.get('p95_time', 0)
                    if p95 > 1.0:  # > 1 second
                        recommendations.append({
                            'type': 'api_optimization',
                            'endpoint': endpoint,
                            'issue': f'p95 response time is {p95:.3f}s (target: < 1s)',
                            'recommendation': 'Consider adding caching or optimizing database queries',
                            'priority': 'high' if p95 > 2.0 else 'medium'
                        })
        
        # Check cache hit rate
        cache_stats = metrics.get('cache', {})
        if isinstance(cache_stats, dict):
            hit_rate = cache_stats.get('hit_rate', 0)
            if hit_rate < 70:
                recommendations.append({
                    'type': 'cache_optimization',
                    'issue': f'Cache hit rate is {hit_rate:.1f}% (target: > 80%)',
                    'recommendation': 'Consider increasing cache TTLs or implementing cache warming',
                    'priority': 'medium'
                })
        
        # Check database query times
        db_stats = metrics.get('database', {})
        if isinstance(db_stats, dict):
            p95 = db_stats.get('p95_time', 0)
            if p95 > 0.5:  # > 500ms
                recommendations.append({
                    'type': 'database_optimization',
                    'issue': f'Database p95 query time is {p95:.3f}s (target: < 0.5s)',
                    'recommendation': 'Review slow queries and add indexes if needed',
                    'priority': 'high' if p95 > 1.0 else 'medium'
                })
        
        # Check scraper performance
        scraper_stats = metrics.get('scraper', {})
        if isinstance(scraper_stats, dict):
            success_rate = scraper_stats.get('success_rate', 0)
            if success_rate < 90:
                recommendations.append({
                    'type': 'scraper_optimization',
                    'issue': f'Scraper success rate is {success_rate:.1f}% (target: > 95%)',
                    'recommendation': 'Review scraper error logs and improve error handling',
                    'priority': 'high' if success_rate < 80 else 'medium'
                })
        
        return recommendations


def performance_tuning_decorator(metric_name: str):
    """
    Decorator to automatically tune performance based on metrics.
    
    Usage:
        @performance_tuning_decorator('api_response')
        def my_api_endpoint():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Record metric
                from config.production_performance import record_performance_metric
                record_performance_metric(metric_name, duration)
                
                # Check alerts
                from config.performance_alerting import check_performance_alerts
                alerts = check_performance_alerts(metric_name, duration)
                
                if alerts:
                    logger.warning(
                        f"Performance alerts triggered for {func.__name__}: {alerts}",
                        extra={'alerts': alerts, 'duration': duration}
                    )
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"Error in {func.__name__}: {e}",
                    extra={'duration': duration, 'error': str(e)},
                    exc_info=True
                )
                raise
        return wrapper
    return decorator


def get_performance_tuning_config() -> Dict[str, Any]:
    """
    Get complete performance tuning configuration.
    
    Returns:
        Dictionary with all tuning settings
    """
    tuner = PerformanceTuner()
    
    return {
        'database': tuner.optimize_database_connections(),
        'cache': tuner.optimize_cache_settings(),
        'workers': tuner.optimize_worker_settings(),
        'environment': os.getenv('FLASK_ENV', 'development'),
        'timestamp': datetime.utcnow().isoformat()
    }


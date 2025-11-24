"""
Advanced health check system with dependency checks, caching, and circuit breakers.
"""
import os
import time
import logging
import psutil
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from functools import lru_cache

logger = logging.getLogger(__name__)

# Health check cache
_health_cache = {}
_health_cache_ttl = 5.0  # Cache health checks for 5 seconds


class HealthCheckResult:
    """Result of a health check."""

    def __init__(
        self,
        name: str,
        status: str,
        message: str = "",
        details: Optional[Dict] = None,
        response_time: float = 0.0,
    ):
        self.name = name
        self.status = status  # 'healthy', 'degraded', 'unhealthy'
        self.message = message
        self.details = details or {}
        self.response_time = response_time
        self.timestamp = datetime.utcnow()

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "details": self.details,
            "response_time_ms": round(self.response_time * 1000, 2),
            "timestamp": self.timestamp.isoformat(),
        }


def check_database(db_path: Optional[str] = None) -> HealthCheckResult:
    """
    Check database connectivity.

    Args:
        db_path: Database path (optional)

    Returns:
        HealthCheckResult
    """
    start_time = time.time()
    name = "database"

    try:
        from scraper.schema import init_db
        from sqlalchemy import text

        if db_path is None:
            db_path = os.getenv("DATABASE_PATH", "social_media.db")

        engine = init_db(db_path)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()

        response_time = time.time() - start_time

        return HealthCheckResult(
            name=name,
            status="healthy",
            message="Database connection successful",
            details={"db_path": db_path},
            response_time=response_time,
        )
    except Exception as e:
        response_time = time.time() - start_time
        logger.error(f"Database health check failed: {e}")
        return HealthCheckResult(
            name=name,
            status="unhealthy",
            message=f"Database connection failed: {str(e)}",
            details={"error": str(e)},
            response_time=response_time,
        )


def check_redis() -> HealthCheckResult:
    """
    Check Redis connectivity.

    Returns:
        HealthCheckResult
    """
    start_time = time.time()
    name = "redis"

    try:
        from cache.redis_client import cache

        # Try to set and get a test value
        test_key = "health_check_test"
        test_value = str(time.time())

        cache.set(test_key, test_value, timeout=5)
        retrieved = cache.get(test_key)
        cache.delete(test_key)

        if retrieved == test_value:
            response_time = time.time() - start_time
            return HealthCheckResult(
                name=name,
                status="healthy",
                message="Redis connection successful",
                details={"operation": "read_write_test"},
                response_time=response_time,
            )
        else:
            response_time = time.time() - start_time
            return HealthCheckResult(
                name=name,
                status="degraded",
                message="Redis read/write test failed",
                details={"operation": "read_write_test"},
                response_time=response_time,
            )
    except Exception as e:
        response_time = time.time() - start_time
        logger.warning(f"Redis health check failed: {e}")
        return HealthCheckResult(
            name=name,
            status="degraded",  # Redis is optional, so degraded not unhealthy
            message=f"Redis connection failed: {str(e)}",
            details={"error": str(e)},
            response_time=response_time,
        )


def check_celery() -> HealthCheckResult:
    """
    Check Celery worker availability.

    Returns:
        HealthCheckResult
    """
    start_time = time.time()
    name = "celery"

    try:
        from celery_app import celery_app

        inspect = celery_app.control.inspect()
        if inspect:
            active_workers = inspect.active()
            stats = inspect.stats()

            worker_count = len(active_workers) if active_workers else 0

            response_time = time.time() - start_time

            if worker_count > 0:
                return HealthCheckResult(
                    name=name,
                    status="healthy",
                    message=f"{worker_count} Celery worker(s) active",
                    details={
                        "worker_count": worker_count,
                        "workers": list(active_workers.keys())
                        if active_workers
                        else [],
                    },
                    response_time=response_time,
                )
            else:
                return HealthCheckResult(
                    name=name,
                    status="degraded",
                    message="No active Celery workers",
                    details={"worker_count": 0},
                    response_time=response_time,
                )
        else:
            response_time = time.time() - start_time
            return HealthCheckResult(
                name=name,
                status="degraded",
                message="Cannot connect to Celery",
                details={},
                response_time=response_time,
            )
    except Exception as e:
        response_time = time.time() - start_time
        logger.warning(f"Celery health check failed: {e}")
        return HealthCheckResult(
            name=name,
            status="degraded",
            message=f"Celery check failed: {str(e)}",
            details={"error": str(e)},
            response_time=response_time,
        )


def check_disk_space(
    path: str = "/", threshold_percent: float = 90.0
) -> HealthCheckResult:
    """
    Check disk space availability.

    Args:
        path: Path to check
        threshold_percent: Warning threshold (default: 90%)

    Returns:
        HealthCheckResult
    """
    start_time = time.time()
    name = "disk_space"

    try:
        disk = psutil.disk_usage(path)
        percent_used = disk.percent
        free_gb = disk.free / (1024**3)

        response_time = time.time() - start_time

        if percent_used >= threshold_percent:
            return HealthCheckResult(
                name=name,
                status="degraded",
                message=f"Disk usage at {percent_used:.1f}%",
                details={
                    "path": path,
                    "percent_used": percent_used,
                    "free_gb": round(free_gb, 2),
                    "total_gb": round(disk.total / (1024**3), 2),
                },
                response_time=response_time,
            )
        else:
            return HealthCheckResult(
                name=name,
                status="healthy",
                message=f"Disk usage at {percent_used:.1f}%",
                details={
                    "path": path,
                    "percent_used": percent_used,
                    "free_gb": round(free_gb, 2),
                    "total_gb": round(disk.total / (1024**3), 2),
                },
                response_time=response_time,
            )
    except Exception as e:
        response_time = time.time() - start_time
        return HealthCheckResult(
            name=name,
            status="degraded",
            message=f"Disk check failed: {str(e)}",
            details={"error": str(e)},
            response_time=response_time,
        )


def check_memory(threshold_percent: float = 90.0) -> HealthCheckResult:
    """
    Check memory usage.

    Args:
        threshold_percent: Warning threshold (default: 90%)

    Returns:
        HealthCheckResult
    """
    start_time = time.time()
    name = "memory"

    try:
        memory = psutil.virtual_memory()
        percent_used = memory.percent
        available_gb = memory.available / (1024**3)

        response_time = time.time() - start_time

        if percent_used >= threshold_percent:
            return HealthCheckResult(
                name=name,
                status="degraded",
                message=f"Memory usage at {percent_used:.1f}%",
                details={
                    "percent_used": percent_used,
                    "available_gb": round(available_gb, 2),
                    "total_gb": round(memory.total / (1024**3), 2),
                },
                response_time=response_time,
            )
        else:
            return HealthCheckResult(
                name=name,
                status="healthy",
                message=f"Memory usage at {percent_used:.1f}%",
                details={
                    "percent_used": percent_used,
                    "available_gb": round(available_gb, 2),
                    "total_gb": round(memory.total / (1024**3), 2),
                },
                response_time=response_time,
            )
    except Exception as e:
        response_time = time.time() - start_time
        return HealthCheckResult(
            name=name,
            status="degraded",
            message=f"Memory check failed: {str(e)}",
            details={"error": str(e)},
            response_time=response_time,
        )


def check_external_api(url: str, timeout: float = 5.0) -> HealthCheckResult:
    """
    Check external API availability.

    Args:
        url: API URL to check
        timeout: Request timeout in seconds

    Returns:
        HealthCheckResult
    """
    start_time = time.time()
    name = f"external_api_{url}"

    try:
        import requests

        response = requests.get(url, timeout=timeout)
        response_time = time.time() - start_time

        if response.status_code == 200:
            return HealthCheckResult(
                name=name,
                status="healthy",
                message=f"External API accessible",
                details={"url": url, "status_code": response.status_code},
                response_time=response_time,
            )
        else:
            return HealthCheckResult(
                name=name,
                status="degraded",
                message=f"External API returned {response.status_code}",
                details={"url": url, "status_code": response.status_code},
                response_time=response_time,
            )
    except Exception as e:
        response_time = time.time() - start_time
        return HealthCheckResult(
            name=name,
            status="unhealthy",
            message=f"External API check failed: {str(e)}",
            details={"url": url, "error": str(e)},
            response_time=response_time,
        )


def run_health_checks(
    db_path: Optional[str] = None, include_optional: bool = True, use_cache: bool = True
) -> Dict[str, HealthCheckResult]:
    """
    Run all health checks.

    Args:
        db_path: Database path (optional)
        include_optional: Include optional checks (Redis, Celery)
        use_cache: Use cached results if available

    Returns:
        Dictionary of health check results
    """
    results = {}

    # Core checks (always run)
    cache_key = "database"
    if use_cache and cache_key in _health_cache:
        cached_time, cached_result = _health_cache[cache_key]
        if time.time() - cached_time < _health_cache_ttl:
            results["database"] = cached_result
        else:
            result = check_database(db_path)
            _health_cache[cache_key] = (time.time(), result)
            results["database"] = result
    else:
        result = check_database(db_path)
        _health_cache[cache_key] = (time.time(), result)
        results["database"] = result

    # Disk and memory (always run, but cache)
    for check_func, cache_key in [(check_disk_space, "disk"), (check_memory, "memory")]:
        if use_cache and cache_key in _health_cache:
            cached_time, cached_result = _health_cache[cache_key]
            if time.time() - cached_time < _health_cache_ttl:
                results[cache_key] = cached_result
            else:
                result = check_func()
                _health_cache[cache_key] = (time.time(), result)
                results[cache_key] = result
        else:
            result = check_func()
            _health_cache[cache_key] = (time.time(), result)
            results[cache_key] = result

    # Optional checks
    if include_optional:
        for check_func, cache_key in [(check_redis, "redis"), (check_celery, "celery")]:
            if use_cache and cache_key in _health_cache:
                cached_time, cached_result = _health_cache[cache_key]
                if time.time() - cached_time < _health_cache_ttl:
                    results[cache_key] = cached_result
                else:
                    result = check_func()
                    _health_cache[cache_key] = (time.time(), result)
                    results[cache_key] = result
            else:
                result = check_func()
                _health_cache[cache_key] = (time.time(), result)
                results[cache_key] = result

    return results


def get_overall_health(results: Dict[str, HealthCheckResult]) -> str:
    """
    Determine overall health status from individual checks.

    Args:
        results: Dictionary of health check results

    Returns:
        Overall status: 'healthy', 'degraded', or 'unhealthy'
    """
    if not results:
        return "unhealthy"

    statuses = [result.status for result in results.values()]

    if "unhealthy" in statuses:
        return "unhealthy"
    elif "degraded" in statuses:
        return "degraded"
    else:
        return "healthy"

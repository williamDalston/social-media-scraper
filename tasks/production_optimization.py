"""
Production optimization utilities for job management.
"""
import logging
import time
from datetime import datetime, timedelta
from tasks.utils import get_db_session
from tasks.job_management import get_queue_depth, get_job_backlog
from models.job import Job

logger = logging.getLogger(__name__)


def calculate_optimal_schedule_time(job_type, historical_data=None):
    """
    Calculate optimal time to schedule a job based on historical performance.

    Args:
        job_type: Type of job
        historical_data: Optional historical performance data

    Returns:
        datetime: Optimal scheduling time
    """
    session = get_db_session()
    try:
        # Get historical job performance by hour of day
        completed_jobs = (
            session.query(Job)
            .filter(
                Job.job_type == job_type,
                Job.status == "completed",
                Job.started_at.isnot(None),
                Job.completed_at.isnot(None),
                Job.created_at >= datetime.utcnow() - timedelta(days=30),
            )
            .all()
        )

        if not completed_jobs:
            # Default to 2 AM UTC if no historical data
            optimal_hour = 2
        else:
            # Find hour with best average performance
            hour_performance = {}
            for job in completed_jobs:
                hour = job.started_at.hour
                duration = (job.completed_at - job.started_at).total_seconds()

                if hour not in hour_performance:
                    hour_performance[hour] = {"total": 0, "count": 0, "avg_duration": 0}

                hour_performance[hour]["total"] += duration
                hour_performance[hour]["count"] += 1

            # Calculate averages and find best hour
            for hour, data in hour_performance.items():
                data["avg_duration"] = data["total"] / data["count"]

            # Optimal hour is one with lowest average duration
            optimal_hour = min(
                hour_performance.items(), key=lambda x: x[1]["avg_duration"]
            )[0]

        # Schedule for next occurrence of optimal hour
        now = datetime.utcnow()
        optimal_time = now.replace(hour=optimal_hour, minute=0, second=0, microsecond=0)

        if optimal_time <= now:
            optimal_time += timedelta(days=1)

        return optimal_time

    finally:
        session.close()


def intelligent_backoff(retry_count, base_delay=60, max_delay=3600, exponential_base=2):
    """
    Calculate intelligent backoff delay with jitter.

    Args:
        retry_count: Current retry attempt number
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff

    Returns:
        int: Delay in seconds
    """
    import random

    # Exponential backoff
    delay = min(base_delay * (exponential_base**retry_count), max_delay)

    # Add jitter (random 0-20% of delay)
    jitter = random.uniform(0, delay * 0.2)

    return int(delay + jitter)


def should_retry_job(job, error_type=None):
    """
    Determine if a job should be retried based on failure analysis.

    Args:
        job: Job object
        error_type: Type of error that occurred

    Returns:
        tuple: (should_retry: bool, reason: str)
    """
    # Don't retry if already exceeded max retries
    if hasattr(job, "retry_count") and job.retry_count >= 3:
        return False, "Max retries exceeded"

    # Don't retry if job was cancelled
    if job.status == "cancelled":
        return False, "Job was cancelled"

    # Retry transient errors
    transient_errors = [
        "timeout",
        "connection",
        "network",
        "temporary",
        "rate limit",
        "503",
        "502",
        "504",
        "429",
    ]

    error_msg = (job.error_message or "").lower()
    if any(err in error_msg for err in transient_errors):
        return True, "Transient error detected"

    # Don't retry permanent errors
    permanent_errors = [
        "not found",
        "404",
        "401",
        "403",
        "invalid",
        "malformed",
        "authentication",
        "authorization",
    ]

    if any(err in error_msg for err in permanent_errors):
        return False, "Permanent error detected"

    # Default: retry if under max attempts
    return True, "Retry allowed"


def get_worker_scaling_recommendation():
    """
    Get recommendation for worker scaling based on queue depth.

    Returns:
        dict: Scaling recommendation
    """
    backlog = get_job_backlog()
    queue_depth = backlog.get("scraping_queue_depth", 0)
    pending = backlog.get("total_pending", 0)

    # Get current worker count
    from tasks.job_management import get_worker_health

    worker_health = get_worker_health()
    current_workers = worker_health.get("total_workers", 0)
    active_workers = worker_health.get("active_workers", 0)

    # Calculate recommendation
    # Assume each worker can handle ~10 jobs concurrently
    jobs_per_worker = 10
    recommended_workers = max(1, (pending + queue_depth) // jobs_per_worker + 1)

    recommendation = {
        "current_workers": current_workers,
        "active_workers": active_workers,
        "pending_jobs": pending,
        "queue_depth": queue_depth,
        "recommended_workers": recommended_workers,
        "scale_up": recommended_workers > current_workers,
        "scale_down": recommended_workers < current_workers and pending < 5,
        "reason": f"Queue depth: {queue_depth}, Pending: {pending}",
    }

    return recommendation


def optimize_job_distribution():
    """
    Optimize job distribution across workers.

    Returns:
        dict: Distribution optimization results
    """
    from celery_app import celery_app

    try:
        inspect = celery_app.control.inspect()
        if not inspect:
            return {"status": "unavailable", "message": "Cannot inspect workers"}

        active = inspect.active()
        reserved = inspect.reserved()

        # Calculate load per worker
        worker_loads = {}
        for worker_name in (active or {}).keys():
            active_count = len((active or {}).get(worker_name, []))
            reserved_count = len((reserved or {}).get(worker_name, []))
            worker_loads[worker_name] = active_count + reserved_count

        if not worker_loads:
            return {"status": "no_workers", "message": "No active workers"}

        # Calculate statistics
        loads = list(worker_loads.values())
        avg_load = sum(loads) / len(loads) if loads else 0
        max_load = max(loads) if loads else 0
        min_load = min(loads) if loads else 0

        # Calculate load imbalance
        imbalance = max_load - min_load if loads else 0
        imbalance_percent = (imbalance / avg_load * 100) if avg_load > 0 else 0

        return {
            "status": "ok",
            "worker_loads": worker_loads,
            "avg_load": avg_load,
            "max_load": max_load,
            "min_load": min_load,
            "imbalance": imbalance,
            "imbalance_percent": imbalance_percent,
            "needs_rebalancing": imbalance_percent > 20,  # More than 20% imbalance
            "recommendation": "Rebalance jobs"
            if imbalance_percent > 20
            else "Distribution is balanced",
        }
    except Exception as e:
        logger.error(f"Error optimizing job distribution: {e}")
        return {"status": "error", "error": str(e)}


def get_resource_usage_optimization():
    """
    Get recommendations for resource usage optimization.

    Returns:
        dict: Optimization recommendations
    """
    session = get_db_session()
    try:
        # Analyze recent job performance
        recent_jobs = (
            session.query(Job)
            .filter(
                Job.created_at >= datetime.utcnow() - timedelta(days=7),
                Job.status.in_(["completed", "failed"]),
            )
            .all()
        )

        if not recent_jobs:
            return {"status": "insufficient_data", "recommendations": []}

        recommendations = []

        # Check for long-running jobs
        long_running = [
            j for j in recent_jobs if j.duration_seconds and j.duration_seconds > 3600
        ]
        if long_running:
            recommendations.append(
                {
                    "type": "long_running_jobs",
                    "severity": "medium",
                    "message": f"{len(long_running)} jobs took longer than 1 hour",
                    "suggestion": "Consider breaking long jobs into smaller chunks or increasing worker resources",
                }
            )

        # Check for high failure rate
        failed = [j for j in recent_jobs if j.status == "failed"]
        failure_rate = len(failed) / len(recent_jobs) * 100 if recent_jobs else 0
        if failure_rate > 10:
            recommendations.append(
                {
                    "type": "high_failure_rate",
                    "severity": "high",
                    "message": f"Failure rate is {failure_rate:.1f}%",
                    "suggestion": "Review error logs and improve error handling",
                }
            )

        # Check for queue backlog
        backlog = get_job_backlog()
        if backlog.get("total_pending", 0) > 100:
            recommendations.append(
                {
                    "type": "queue_backlog",
                    "severity": "medium",
                    "message": f"Queue backlog: {backlog.get('total_pending', 0)} jobs",
                    "suggestion": "Scale up workers or optimize job execution time",
                }
            )

        return {
            "status": "ok",
            "total_jobs_analyzed": len(recent_jobs),
            "recommendations": recommendations,
        }
    finally:
        session.close()

"""
Celery application configuration for background task processing.
"""
import os
from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv

load_dotenv()

# Get Redis URL from environment or use default
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
broker_url = os.getenv("CELERY_BROKER_URL", redis_url)
result_backend = os.getenv("CELERY_RESULT_BACKEND", redis_url)

# Create Celery app
celery_app = Celery(
    "social_media_scraper",
    broker=broker_url,
    backend=result_backend,
    include=["tasks.scraper_tasks", "tasks.scheduled_tasks", "tasks.job_alerting"],
)

# Celery configuration
celery_app.conf.update(
    # Task serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Task routing with priorities
    task_routes={
        "tasks.scraper_tasks.*": {"queue": "scraping"},
        "tasks.scheduled_tasks.*": {"queue": "scheduled"},
    },
    # Task priorities (0-9, higher is more priority)
    task_default_priority=5,
    # Priority routing - higher priority tasks go to priority queue
    task_default_queue="scraping",
    task_default_exchange="tasks",
    task_default_exchange_type="direct",
    task_default_routing_key="scraping",
    # Task timeouts
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3300,  # 55 minutes soft limit
    # Result expiration
    result_expires=3600,  # Results expire after 1 hour
    # Worker settings - optimized for production
    worker_prefetch_multiplier=4,  # Increased for better throughput
    worker_max_tasks_per_child=100,  # Increased to reduce worker churn
    worker_disable_rate_limits=False,  # Enable rate limiting
    # Task execution settings
    task_acks_late=True,  # Acknowledge after task completion
    task_reject_on_worker_lost=True,  # Reject tasks if worker dies
    task_ignore_result=False,  # Keep results for monitoring
    # Broker settings
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    # Result backend settings
    result_backend_transport_options={
        "master_name": "mymaster",
        "visibility_timeout": 3600,
    },
    # Performance optimizations
    task_compression="gzip",  # Compress large task payloads
    result_compression="gzip",  # Compress large results
    task_always_eager=False,  # Always use async execution
    task_eager_propagates=True,  # Propagate exceptions in eager mode
    # Beat schedule for periodic tasks
    beat_schedule={
        "daily-scrape-all": {
            "task": "tasks.scheduled_tasks.daily_scrape_all",
            "schedule": crontab(hour=2, minute=0),  # 2 AM UTC daily
        },
        "cleanup-old-jobs": {
            "task": "tasks.scheduled_tasks.cleanup_old_jobs",
            "schedule": crontab(
                hour=3, minute=0, day_of_month=1
            ),  # 3 AM UTC on 1st of month
        },
        "health-check": {
            "task": "tasks.scheduled_tasks.health_check",
            "schedule": crontab(minute="*/15"),  # Every 15 minutes
        },
        "process-scheduled-jobs": {
            "task": "tasks.scheduled_tasks.process_scheduled_jobs",
            "schedule": crontab(minute="*"),  # Every minute
        },
        "check-conditional-jobs": {
            "task": "tasks.scheduled_tasks.check_conditional_jobs",
            "schedule": crontab(minute="*/5"),  # Every 5 minutes
        },
        "archive-old-results": {
            "task": "tasks.scheduled_tasks.archive_old_job_results",
            "schedule": crontab(
                hour=4, minute=0, day_of_month=1
            ),  # 4 AM UTC on 1st of month
        },
        "monitor-jobs-and-alert": {
            "task": "tasks.job_alerting.monitor_jobs_and_alert",
            "schedule": crontab(minute="*/5"),  # Every 5 minutes
        },
    },
)

if __name__ == "__main__":
    celery_app.start()

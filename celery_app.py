"""
Celery application configuration for background task processing.
"""
import os
from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv

load_dotenv()

# Get Redis URL from environment or use default
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
broker_url = os.getenv('CELERY_BROKER_URL', redis_url)
result_backend = os.getenv('CELERY_RESULT_BACKEND', redis_url)

# Create Celery app
celery_app = Celery(
    'social_media_scraper',
    broker=broker_url,
    backend=result_backend,
    include=['tasks.scraper_tasks', 'tasks.scheduled_tasks']
)

# Celery configuration
celery_app.conf.update(
    # Task serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Task routing
    task_routes={
        'tasks.scraper_tasks.*': {'queue': 'scraping'},
        'tasks.scheduled_tasks.*': {'queue': 'scheduled'},
    },
    
    # Task priorities (0-9, higher is more priority)
    task_default_priority=5,
    
    # Task timeouts
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3300,  # 55 minutes soft limit
    
    # Result expiration
    result_expires=3600,  # Results expire after 1 hour
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
    
    # Beat schedule for periodic tasks
    beat_schedule={
        'daily-scrape-all': {
            'task': 'tasks.scheduled_tasks.daily_scrape_all',
            'schedule': crontab(hour=2, minute=0),  # 2 AM UTC daily
        },
        'cleanup-old-jobs': {
            'task': 'tasks.scheduled_tasks.cleanup_old_jobs',
            'schedule': crontab(hour=3, minute=0, day_of_month=1),  # 3 AM UTC on 1st of month
        },
        'health-check': {
            'task': 'tasks.scheduled_tasks.health_check',
            'schedule': crontab(minute='*/15'),  # Every 15 minutes
        },
    },
)

if __name__ == '__main__':
    celery_app.start()


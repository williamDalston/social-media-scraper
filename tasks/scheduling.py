"""
Advanced scheduling utilities for jobs.
"""
import logging
from datetime import datetime, timedelta
from croniter import croniter
from tasks.utils import get_db_session
from models.job import Job
from celery_app import celery_app

logger = logging.getLogger(__name__)


def schedule_job_with_cron(job_type, cron_expression, task_func, priority=5, **task_kwargs):
    """
    Schedule a job using a cron expression.
    
    Args:
        job_type: Type of job
        cron_expression: Cron expression (e.g., "0 2 * * *" for daily at 2 AM)
        task_func: Celery task function
        priority: Job priority
        **task_kwargs: Task arguments
        
    Returns:
        str: Scheduled job identifier
    """
    # Validate cron expression
    try:
        base_time = datetime.utcnow()
        cron = croniter(cron_expression, base_time)
        next_run = cron.get_next(datetime)
    except Exception as e:
        raise ValueError(f"Invalid cron expression: {e}")
    
    session = get_db_session()
    try:
        # Create a scheduled job record
        job = Job(
            job_type=job_type,
            status='scheduled',
            priority=priority,
            scheduled_for=next_run
        )
        
        # Store task info
        import json
        job.result = json.dumps({
            'cron_expression': cron_expression,
            'task_name': task_func.name,
            'task_kwargs': task_kwargs,
            'recurring': True
        })
        
        session.add(job)
        session.commit()
        
        logger.info(f"Scheduled job {job.id} with cron {cron_expression}, next run: {next_run}")
        return job.job_id
        
    finally:
        session.close()


def schedule_job_for_datetime(job_type, scheduled_datetime, task_func, priority=5, **task_kwargs):
    """
    Schedule a job for a specific datetime.
    
    Args:
        job_type: Type of job
        scheduled_datetime: When to run the job
        task_func: Celery task function
        priority: Job priority
        **task_kwargs: Task arguments
        
    Returns:
        str: Scheduled job identifier
    """
    session = get_db_session()
    try:
        job = Job(
            job_type=job_type,
            status='scheduled',
            priority=priority,
            scheduled_for=scheduled_datetime
        )
        
        import json
        job.result = json.dumps({
            'task_name': task_func.name,
            'task_kwargs': task_kwargs,
            'recurring': False
        })
        
        session.add(job)
        session.commit()
        
        logger.info(f"Scheduled job {job.id} for {scheduled_datetime}")
        return job.job_id
        
    finally:
        session.close()


def schedule_conditional_job(condition_func, job_type, task_func, check_interval=300, **task_kwargs):
    """
    Schedule a job that only runs when a condition is met.
    
    Args:
        condition_func: Function that returns True when job should run
        job_type: Type of job
        task_func: Celery task function
        check_interval: How often to check condition (seconds)
        **task_kwargs: Task arguments
        
    Returns:
        str: Conditional job identifier
    """
    session = get_db_session()
    try:
        job = Job(
            job_type=job_type,
            status='conditional',
            priority=5
        )
        
        import json
        job.result = json.dumps({
            'condition_check_interval': check_interval,
            'task_name': task_func.name,
            'task_kwargs': task_kwargs,
            'condition_type': 'custom'
        })
        
        session.add(job)
        session.commit()
        
        # Schedule a periodic check task
        from tasks.scheduled_tasks import check_conditional_jobs
        # This would be called by a periodic task
        
        logger.info(f"Created conditional job {job.id}")
        return job.job_id
        
    finally:
        session.close()


def get_due_scheduled_jobs():
    """
    Get all scheduled jobs that are due to run.
    
    Returns:
        list: List of Job objects that are due
    """
    session = get_db_session()
    try:
        now = datetime.utcnow()
        due_jobs = session.query(Job).filter(
            Job.status == 'scheduled',
            Job.scheduled_for <= now,
            Job.paused == 'false'
        ).all()
        
        return due_jobs
    finally:
        session.close()


def process_due_scheduled_jobs():
    """
    Process all scheduled jobs that are due to run.
    """
    due_jobs = get_due_scheduled_jobs()
    
    for job in due_jobs:
        try:
            import json
            task_info = json.loads(job.result) if job.result else {}
            task_name = task_info.get('task_name')
            task_kwargs = task_info.get('task_kwargs', {})
            cron_expression = task_info.get('cron_expression')
            recurring = task_info.get('recurring', False)
            
            if task_name:
                task_func = celery_app.tasks.get(task_name)
                if task_func:
                    # Start the task
                    result = task_func.delay(**task_kwargs)
                    
                    # Update job record
                    session = get_db_session()
                    try:
                        job.job_id = result.id
                        job.status = 'pending'
                        job.result = None
                        
                        # If recurring, schedule next run
                        if recurring and cron_expression:
                            from croniter import croniter
                            cron = croniter(cron_expression, datetime.utcnow())
                            job.scheduled_for = cron.get_next(datetime)
                            job.status = 'scheduled'
                        else:
                            job.status = 'pending'
                        
                        session.commit()
                        logger.info(f"Started scheduled job {job.id} as {result.id}")
                    finally:
                        session.close()
        except Exception as e:
            logger.error(f"Error processing scheduled job {job.id}: {e}")
            session = get_db_session()
            try:
                job.status = 'failed'
                job.error_message = str(e)
                session.commit()
            finally:
                session.close()


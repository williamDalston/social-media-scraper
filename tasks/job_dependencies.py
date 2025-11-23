"""
Job dependency management for chaining jobs.
"""
import logging
from datetime import datetime
from tasks.utils import get_db_session
from models.job import Job
from celery_app import celery_app
from tasks.job_management import check_job_dependencies

logger = logging.getLogger(__name__)


def create_dependent_job(parent_job_id, job_type, task_func, **task_kwargs):
    """
    Create a job that depends on another job completing.
    
    Args:
        parent_job_id: Job ID that must complete first
        job_type: Type of job to create
        task_func: Celery task function to execute
        **task_kwargs: Arguments for the task
        
    Returns:
        str: New job ID
    """
    session = get_db_session()
    try:
        # Verify parent job exists
        parent = session.query(Job).filter_by(job_id=parent_job_id).first()
        if not parent:
            raise ValueError(f"Parent job {parent_job_id} not found")
        
        # Create the dependent job but don't start it yet
        # We'll use a callback to start it when parent completes
        job = Job(
            job_type=job_type,
            status='pending',
            depends_on_job_id=parent_job_id,
            priority=task_kwargs.get('priority', 5),
            paused='true'  # Pause until dependency is met
        )
        session.add(job)
        session.commit()
        
        # Store the task info in result field temporarily
        import json
        job.result = json.dumps({
            'task_name': task_func.name,
            'task_kwargs': task_kwargs
        })
        session.commit()
        
        logger.info(f"Created dependent job {job.id} waiting for {parent_job_id}")
        return job.job_id
        
    finally:
        session.close()


def check_and_start_dependent_jobs(parent_job_id):
    """
    Check if any jobs are waiting for a parent job and start them.
    
    Args:
        parent_job_id: Job ID that just completed
    """
    session = get_db_session()
    try:
        # Find all jobs waiting for this parent
        dependent_jobs = session.query(Job).filter_by(
            depends_on_job_id=parent_job_id,
            status='pending',
            paused='true'
        ).all()
        
        for job in dependent_jobs:
            # Check if dependencies are satisfied
            satisfied, blocking = check_job_dependencies(job.job_id)
            
            if satisfied:
                # Parse task info and start the job
                import json
                try:
                    task_info = json.loads(job.result) if job.result else {}
                    task_name = task_info.get('task_name')
                    task_kwargs = task_info.get('task_kwargs', {})
                    
                    if task_name:
                        # Get the task function
                        task_func = celery_app.tasks.get(task_name)
                        if task_func:
                            # Start the task
                            result = task_func.delay(**task_kwargs)
                            job.job_id = result.id
                            job.paused = 'false'
                            job.status = 'pending'
                            job.result = None  # Clear temp data
                            session.commit()
                            logger.info(f"Started dependent job {job.id} as {result.id}")
                        else:
                            logger.error(f"Task {task_name} not found for dependent job {job.id}")
                    else:
                        logger.warning(f"No task name in dependent job {job.id}")
                except Exception as e:
                    logger.error(f"Error starting dependent job {job.id}: {e}")
                    job.status = 'failed'
                    job.error_message = f"Failed to start: {str(e)}"
                    session.commit()
            else:
                logger.info(f"Dependent job {job.id} still blocked: {blocking}")
                
    finally:
        session.close()


# Hook into task completion to check dependencies
@celery_app.task(bind=True)
def task_completion_hook(self, parent_job_id):
    """
    Hook to check and start dependent jobs when a task completes.
    This should be called as a callback after task completion.
    """
    try:
        check_and_start_dependent_jobs(parent_job_id)
    except Exception as e:
        logger.error(f"Error in task completion hook: {e}")


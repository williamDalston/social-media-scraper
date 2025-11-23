"""
Advanced job management utilities for Phase 2 enhancements.
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy import and_, or_
from tasks.utils import get_db_session
from models.job import Job
from celery_app import celery_app

logger = logging.getLogger(__name__)


def get_queue_depth(queue_name='scraping'):
    """
    Get the depth (number of pending jobs) in a queue.
    
    Args:
        queue_name: Name of the queue
        
    Returns:
        int: Number of pending jobs in queue
    """
    try:
        inspect = celery_app.control.inspect()
        if inspect:
            reserved = inspect.reserved()
            active = inspect.active()
            scheduled = inspect.scheduled()
            
            if not (reserved or active or scheduled):
                return 0
            
            count = 0
            for worker, tasks in (reserved or {}).items():
                for task in tasks:
                    if task.get('delivery_info', {}).get('routing_key') == queue_name:
                        count += 1
            
            for worker, tasks in (active or {}).items():
                for task in tasks:
                    if task.get('delivery_info', {}).get('routing_key') == queue_name:
                        count += 1
            
            return count
    except Exception as e:
        logger.error(f"Error getting queue depth: {e}")
        # Fallback to database count
        session = get_db_session()
        try:
            return session.query(Job).filter(
                Job.status == 'pending',
                Job.paused == 'false'
            ).count()
        finally:
            session.close()
    return 0


def get_job_backlog():
    """
    Get total backlog of pending jobs.
    
    Returns:
        dict: Backlog statistics
    """
    session = get_db_session()
    try:
        pending = session.query(Job).filter(
            Job.status == 'pending',
            Job.paused == 'false'
        ).count()
        
        running = session.query(Job).filter(Job.status == 'running').count()
        
        # Group by priority
        by_priority = {}
        for priority in range(10):
            count = session.query(Job).filter(
                Job.status == 'pending',
                Job.priority == priority,
                Job.paused == 'false'
            ).count()
            if count > 0:
                by_priority[priority] = count
        
        return {
            'total_pending': pending,
            'total_running': running,
            'by_priority': by_priority,
            'scraping_queue_depth': get_queue_depth('scraping'),
            'scheduled_queue_depth': get_queue_depth('scheduled'),
        }
    finally:
        session.close()


def check_job_dependencies(job_id):
    """
    Check if a job's dependencies are satisfied.
    
    Args:
        job_id: Job ID to check
        
    Returns:
        tuple: (satisfied: bool, blocking_jobs: list)
    """
    session = get_db_session()
    try:
        job = session.query(Job).filter_by(job_id=job_id).first()
        if not job or not job.depends_on_job_id:
            return True, []
        
        # Check if dependency job is completed
        dependency = session.query(Job).filter_by(job_id=job.depends_on_job_id).first()
        if not dependency:
            return False, [f"Dependency job {job.depends_on_job_id} not found"]
        
        if dependency.status == 'completed':
            return True, []
        elif dependency.status == 'failed':
            return False, [f"Dependency job {job.depends_on_job_id} failed"]
        else:
            return False, [f"Dependency job {job.depends_on_job_id} is {dependency.status}"]
    finally:
        session.close()


def calculate_job_sla_status(job):
    """
    Calculate if job met its SLA.
    
    Args:
        job: Job object
        
    Returns:
        dict: SLA status information
    """
    if not job.sla_seconds or not job.started_at:
        return {'met_sla': None, 'sla_seconds': None, 'actual_seconds': None}
    
    if job.completed_at:
        actual_seconds = (job.completed_at - job.started_at).total_seconds()
        met_sla = actual_seconds <= job.sla_seconds
    elif job.started_at:
        # Job is still running, check if it's exceeded SLA
        elapsed = (datetime.utcnow() - job.started_at).total_seconds()
        met_sla = elapsed <= job.sla_seconds
        actual_seconds = elapsed
    else:
        return {'met_sla': None, 'sla_seconds': job.sla_seconds, 'actual_seconds': None}
    
    return {
        'met_sla': met_sla,
        'sla_seconds': job.sla_seconds,
        'actual_seconds': actual_seconds,
        'sla_violation_percent': ((actual_seconds - job.sla_seconds) / job.sla_seconds * 100) if actual_seconds > job.sla_seconds else 0
    }


def get_job_performance_analytics(days=30):
    """
    Get job performance analytics.
    
    Args:
        days: Number of days to analyze
        
    Returns:
        dict: Performance analytics
    """
    session = get_db_session()
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get all jobs in period
        jobs = session.query(Job).filter(Job.created_at >= cutoff_date).all()
        
        total = len(jobs)
        completed = sum(1 for j in jobs if j.status == 'completed')
        failed = sum(1 for j in jobs if j.status == 'failed')
        cancelled = sum(1 for j in jobs if j.status == 'cancelled')
        
        # Calculate durations
        durations = []
        sla_met = 0
        sla_total = 0
        
        for job in jobs:
            if job.completed_at and job.started_at:
                duration = (job.completed_at - job.started_at).total_seconds()
                durations.append(duration)
                job.duration_seconds = duration
                
                # Check SLA
                if job.sla_seconds:
                    sla_total += 1
                    if duration <= job.sla_seconds:
                        sla_met += 1
        
        avg_duration = sum(durations) / len(durations) if durations else 0
        min_duration = min(durations) if durations else 0
        max_duration = max(durations) if durations else 0
        
        # Group by job type
        by_type = {}
        for job_type in set(j.job_type for j in jobs):
            type_jobs = [j for j in jobs if j.job_type == job_type]
            by_type[job_type] = {
                'total': len(type_jobs),
                'completed': sum(1 for j in type_jobs if j.status == 'completed'),
                'failed': sum(1 for j in type_jobs if j.status == 'failed'),
                'success_rate': (sum(1 for j in type_jobs if j.status == 'completed') / len(type_jobs) * 100) if type_jobs else 0
            }
        
        return {
            'period_days': days,
            'total_jobs': total,
            'completed': completed,
            'failed': failed,
            'cancelled': cancelled,
            'success_rate': (completed / total * 100) if total > 0 else 0,
            'avg_duration_seconds': avg_duration,
            'min_duration_seconds': min_duration,
            'max_duration_seconds': max_duration,
            'sla_compliance_rate': (sla_met / sla_total * 100) if sla_total > 0 else None,
            'by_job_type': by_type
        }
    finally:
        session.close()


def get_worker_health():
    """
    Get worker health status.
    
    Returns:
        dict: Worker health information
    """
    try:
        inspect = celery_app.control.inspect()
        if not inspect:
            return {'status': 'unavailable', 'workers': []}
        
        active = inspect.active()
        stats = inspect.stats()
        registered = inspect.registered()
        
        workers = []
        for worker_name in (registered or {}).keys():
            worker_info = {
                'name': worker_name,
                'status': 'active' if worker_name in (active or {}) else 'idle',
                'active_tasks': len((active or {}).get(worker_name, [])),
                'stats': (stats or {}).get(worker_name, {})
            }
            workers.append(worker_info)
        
        return {
            'status': 'healthy' if workers else 'no_workers',
            'total_workers': len(workers),
            'active_workers': sum(1 for w in workers if w['status'] == 'active'),
            'workers': workers
        }
    except Exception as e:
        logger.error(f"Error getting worker health: {e}")
        return {'status': 'error', 'error': str(e), 'workers': []}


def pause_job(job_id):
    """
    Pause a job (if it's pending).
    
    Args:
        job_id: Job ID to pause
        
    Returns:
        bool: True if paused, False otherwise
    """
    session = get_db_session()
    try:
        job = session.query(Job).filter_by(job_id=job_id).first()
        if not job:
            return False
        
        if job.status == 'pending':
            job.paused = 'true'
            session.commit()
            
            # Revoke the Celery task if it hasn't started
            try:
                celery_app.control.revoke(job_id, terminate=False)
            except Exception:
                pass
            
            return True
        return False
    finally:
        session.close()


def resume_job(job_id):
    """
    Resume a paused job.
    
    Args:
        job_id: Job ID to resume
        
    Returns:
        bool: True if resumed, False otherwise
    """
    session = get_db_session()
    try:
        job = session.query(Job).filter_by(job_id=job_id).first()
        if not job:
            return False
        
        if job.paused == 'true' and job.status == 'pending':
            job.paused = 'false'
            session.commit()
            
            # Re-queue the job (would need to re-trigger the task)
            # This is a simplified version - in production you'd re-queue properly
            return True
        return False
    finally:
        session.close()


"""
Scheduled periodic tasks using Celery Beat.
"""
import os
import json
import logging
from datetime import datetime, timedelta
from celery_app import celery_app
from tasks.utils import get_db_session
from tasks.scraper_tasks import scrape_all_accounts

# Set up logging
logger = logging.getLogger(__name__)

@celery_app.task
def daily_scrape_all():
    """
    Daily scheduled task to scrape all accounts.
    Runs at 2 AM UTC (configurable via Celery Beat schedule).
    
    Returns:
        dict: Result with status
    """
    try:
        logger.info("Starting daily scrape_all scheduled task")
        db_path = os.getenv('DB_PATH', 'social_media.db')
        mode = os.getenv('SCRAPER_MODE', 'simulated')
        
        # Trigger the scrape_all_accounts task asynchronously
        result = scrape_all_accounts.delay(mode=mode, db_path=db_path)
        
        logger.info(f"Daily scrape job started with job_id: {result.id}")
        return {
            'status': 'started',
            'job_id': result.id,
            'message': 'Daily scrape job started',
            'timestamp': datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error starting daily scrape task: {e}", exc_info=True)
        return {
            'status': 'failed',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }

@celery_app.task
def cleanup_old_jobs():
    """
    Cleanup old completed/failed jobs older than 30 days.
    Runs monthly on the 1st at 3 AM UTC.
    
    Returns:
        dict: Result with cleanup summary
    """
    session = None
    try:
        logger.info("Starting cleanup_old_jobs scheduled task")
        session = get_db_session()
        from models.job import Job
        
        # Calculate cutoff date (30 days ago)
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        # Find old jobs
        old_jobs = session.query(Job).filter(
            Job.completed_at < cutoff_date,
            Job.status.in_(['completed', 'failed', 'cancelled'])
        ).all()
        
        count = len(old_jobs)
        
        # Delete old jobs
        for job in old_jobs:
            session.delete(job)
        
        session.commit()
        
        logger.info(f"Cleaned up {count} old jobs")
        return {
            'status': 'completed',
            'deleted_count': count,
            'cutoff_date': cutoff_date.isoformat(),
            'message': f'Deleted {count} old jobs',
            'timestamp': datetime.utcnow().isoformat()
        }
    except Exception as e:
        if session:
            session.rollback()
        logger.error(f"Error in cleanup_old_jobs task: {e}", exc_info=True)
        return {
            'status': 'failed',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }
    finally:
        if session:
            session.close()

@celery_app.task
def health_check():
    """
    Health check task to verify system is operational.
    Runs every 15 minutes.
    
    Checks:
    - Database connectivity
    - Redis connectivity
    - Recent job success rate
    
    Returns:
        dict: Health status
    """
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'checks': {}
    }
    
    # Check database
    try:
        session = get_db_session()
        session.execute('SELECT 1')
        session.close()
        health_status['checks']['database'] = 'ok'
    except Exception as e:
        health_status['status'] = 'unhealthy'
        health_status['checks']['database'] = f'error: {str(e)}'
    
    # Check Redis (via Celery)
    try:
        from celery_app import celery_app
        inspect = celery_app.control.inspect()
        if inspect:
            active_workers = inspect.active()
            if active_workers:
                health_status['checks']['redis'] = 'ok'
                health_status['checks']['celery_workers'] = len(active_workers)
            else:
                health_status['status'] = 'degraded'
                health_status['checks']['redis'] = 'ok'
                health_status['checks']['celery_workers'] = 0
                health_status['checks']['warning'] = 'No active Celery workers'
        else:
            health_status['status'] = 'unhealthy'
            health_status['checks']['redis'] = 'error: Cannot connect to Celery'
    except Exception as e:
        health_status['status'] = 'unhealthy'
        health_status['checks']['redis'] = f'error: {str(e)}'
    
    # Check recent job success rate (last 24 hours)
    try:
        session = get_db_session()
        from models.job import Job
        
        since = datetime.utcnow() - timedelta(hours=24)
        recent_jobs = session.query(Job).filter(Job.created_at >= since).all()
        
        if recent_jobs:
            completed = sum(1 for j in recent_jobs if j.status == 'completed')
            failed = sum(1 for j in recent_jobs if j.status == 'failed')
            total = len(recent_jobs)
            success_rate = (completed / total) * 100 if total > 0 else 100
            
            health_status['checks']['recent_jobs'] = {
                'total': total,
                'completed': completed,
                'failed': failed,
                'success_rate': round(success_rate, 2)
            }
            
            if success_rate < 50:
                health_status['status'] = 'degraded'
        else:
            health_status['checks']['recent_jobs'] = {
                'total': 0,
                'message': 'No recent jobs'
            }
        
        session.close()
    except Exception as e:
        health_status['checks']['recent_jobs'] = f'error: {str(e)}'
    
    return health_status


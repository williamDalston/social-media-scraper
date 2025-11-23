"""
Job alerting system for production monitoring.
"""
import logging
from datetime import datetime, timedelta
from tasks.utils import get_db_session
from models.job import Job
from tasks.job_management import get_job_backlog, get_worker_health
from celery_app import celery_app

logger = logging.getLogger(__name__)


def check_job_failures_and_alert(threshold=5, time_window_minutes=15):
    """
    Check for job failures and send alerts if threshold exceeded.
    
    Args:
        threshold: Number of failures to trigger alert
        time_window_minutes: Time window to check
        
    Returns:
        dict: Alert status
    """
    session = get_db_session()
    try:
        cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)
        
        recent_failures = session.query(Job).filter(
            Job.status == 'failed',
            Job.completed_at >= cutoff_time
        ).count()
        
        if recent_failures >= threshold:
            alert = {
                'alert_type': 'high_failure_rate',
                'severity': 'high',
                'message': f"{recent_failures} job failures in last {time_window_minutes} minutes",
                'threshold': threshold,
                'actual': recent_failures,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Send alert (in production, would integrate with alerting system)
            send_alert(alert)
            
            return alert
        
        return {'status': 'ok', 'failures': recent_failures}
    finally:
        session.close()


def check_sla_violations_and_alert():
    """
    Check for SLA violations and send alerts.
    
    Returns:
        dict: Alert status
    """
    session = get_db_session()
    try:
        # Get running jobs with SLA
        running_jobs = session.query(Job).filter(
            Job.status == 'running',
            Job.sla_seconds.isnot(None),
            Job.started_at.isnot(None)
        ).all()
        
        violations = []
        for job in running_jobs:
            elapsed = (datetime.utcnow() - job.started_at).total_seconds()
            if elapsed > job.sla_seconds:
                violations.append({
                    'job_id': job.job_id,
                    'job_type': job.job_type,
                    'sla_seconds': job.sla_seconds,
                    'elapsed_seconds': elapsed,
                    'violation_percent': ((elapsed - job.sla_seconds) / job.sla_seconds * 100)
                })
        
        if violations:
            alert = {
                'alert_type': 'sla_violation',
                'severity': 'high',
                'message': f"{len(violations)} jobs violating SLA",
                'violations': violations,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            send_alert(alert)
            return alert
        
        return {'status': 'ok', 'violations': 0}
    finally:
        session.close()


def check_queue_backlog_and_alert(threshold=100):
    """
    Check queue backlog and alert if too high.
    
    Args:
        threshold: Backlog threshold to trigger alert
        
    Returns:
        dict: Alert status
    """
    backlog = get_job_backlog()
    total_pending = backlog.get('total_pending', 0)
    
    if total_pending >= threshold:
        alert = {
            'alert_type': 'queue_backlog',
            'severity': 'medium',
            'message': f"Queue backlog: {total_pending} jobs",
            'threshold': threshold,
            'actual': total_pending,
            'backlog_details': backlog,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        send_alert(alert)
        return alert
    
    return {'status': 'ok', 'backlog': total_pending}


def check_worker_health_and_alert():
    """
    Check worker health and alert if issues detected.
    
    Returns:
        dict: Alert status
    """
    worker_health = get_worker_health()
    
    if worker_health.get('status') != 'healthy':
        alert = {
            'alert_type': 'worker_health',
            'severity': 'high',
            'message': f"Worker health issue: {worker_health.get('status')}",
            'worker_health': worker_health,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        send_alert(alert)
        return alert
    
    # Check if no workers
    if worker_health.get('total_workers', 0) == 0:
        alert = {
            'alert_type': 'no_workers',
            'severity': 'critical',
            'message': 'No Celery workers available',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        send_alert(alert)
        return alert
    
    return {'status': 'ok', 'workers': worker_health.get('total_workers', 0)}


def send_alert(alert_data):
    """
    Send alert through configured channels.
    
    Args:
        alert_data: Alert data dictionary
    """
    # Log the alert
    severity = alert_data.get('severity', 'info')
    message = alert_data.get('message', 'Alert triggered')
    
    if severity == 'critical':
        logger.critical(f"ALERT: {message}", extra={'alert': alert_data})
    elif severity == 'high':
        logger.error(f"ALERT: {message}", extra={'alert': alert_data})
    else:
        logger.warning(f"ALERT: {message}", extra={'alert': alert_data})
    
    # In production, would integrate with:
    # - Email notifications
    # - Slack/PagerDuty
    # - SMS alerts for critical
    # - Alerting service (e.g., AlertManager)
    
    # Store alert in database for tracking
    try:
        session = get_db_session()
        # Could create an Alert model to track alerts
        # For now, just log
        pass
    except Exception as e:
        logger.error(f"Error storing alert: {e}")


@celery_app.task
def monitor_jobs_and_alert():
    """
    Periodic task to monitor jobs and send alerts.
    Runs every 5 minutes.
    """
    alerts = []
    
    # Check various conditions
    alerts.append(check_job_failures_and_alert())
    alerts.append(check_sla_violations_and_alert())
    alerts.append(check_queue_backlog_and_alert())
    alerts.append(check_worker_health_and_alert())
    
    return {
        'status': 'completed',
        'alerts_checked': len(alerts),
        'alerts_triggered': sum(1 for a in alerts if a.get('alert_type')),
        'timestamp': datetime.utcnow().isoformat()
    }


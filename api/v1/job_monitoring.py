"""
Job monitoring and analytics API endpoints.
"""
from flask_restx import Namespace, Resource, fields
from flask import request
from sqlalchemy import func
from datetime import datetime, timedelta
from api.errors import BadRequestError
from auth.decorators import require_any_role
from tasks.utils import get_db_session
from tasks.job_management import (
    get_queue_depth, get_job_backlog, get_job_performance_analytics,
    get_worker_health, calculate_job_sla_status
)
from models.job import Job

ns = Namespace('job-monitoring', description='Job monitoring and analytics')

# Response models
queue_stats_model = ns.model('QueueStats', {
    'total_pending': fields.Integer(description='Total pending jobs'),
    'total_running': fields.Integer(description='Total running jobs'),
    'by_priority': fields.Raw(description='Jobs by priority'),
    'scraping_queue_depth': fields.Integer(description='Scraping queue depth'),
    'scheduled_queue_depth': fields.Integer(description='Scheduled queue depth'),
})

performance_analytics_model = ns.model('PerformanceAnalytics', {
    'period_days': fields.Integer(description='Analysis period in days'),
    'total_jobs': fields.Integer(description='Total jobs'),
    'completed': fields.Integer(description='Completed jobs'),
    'failed': fields.Integer(description='Failed jobs'),
    'success_rate': fields.Float(description='Success rate percentage'),
    'avg_duration_seconds': fields.Float(description='Average duration'),
    'sla_compliance_rate': fields.Float(description='SLA compliance rate'),
    'by_job_type': fields.Raw(description='Statistics by job type'),
})

worker_health_model = ns.model('WorkerHealth', {
    'status': fields.String(description='Overall status'),
    'total_workers': fields.Integer(description='Total workers'),
    'active_workers': fields.Integer(description='Active workers'),
    'workers': fields.List(fields.Raw(description='Worker details')),
})

sla_status_model = ns.model('SLAStatus', {
    'met_sla': fields.Boolean(description='Whether SLA was met'),
    'sla_seconds': fields.Integer(description='SLA target in seconds'),
    'actual_seconds': fields.Float(description='Actual duration'),
    'sla_violation_percent': fields.Float(description='SLA violation percentage'),
})


@ns.route('/backlog')
@ns.doc(security='Bearer Auth')
class JobBacklog(Resource):
    """Get job backlog statistics."""
    
    @ns.doc('get_job_backlog')
    @ns.marshal_with(queue_stats_model)
    @ns.response(200, 'Success')
    @ns.response(401, 'Unauthorized')
    @require_any_role(['Admin', 'Editor', 'Viewer'])
    def get(self):
        """Get current job backlog and queue statistics."""
        return get_job_backlog()


@ns.route('/performance')
@ns.doc(security='Bearer Auth')
class JobPerformance(Resource):
    """Get job performance analytics."""
    
    @ns.doc('get_job_performance')
    @ns.marshal_with(performance_analytics_model)
    @ns.param('days', 'Number of days to analyze', type=int, default=30)
    @ns.response(200, 'Success')
    @ns.response(401, 'Unauthorized')
    @require_any_role(['Admin', 'Editor', 'Viewer'])
    def get(self):
        """Get job performance analytics for the specified period."""
        days = request.args.get('days', 30, type=int)
        if days < 1 or days > 365:
            raise BadRequestError('Days must be between 1 and 365')
        return get_job_performance_analytics(days)


@ns.route('/workers')
@ns.doc(security='Bearer Auth')
class WorkerHealth(Resource):
    """Get worker health status."""
    
    @ns.doc('get_worker_health')
    @ns.marshal_with(worker_health_model)
    @ns.response(200, 'Success')
    @ns.response(401, 'Unauthorized')
    @require_any_role(['Admin', 'Editor', 'Viewer'])
    def get(self):
        """Get Celery worker health and status."""
        return get_worker_health()


@ns.route('/<job_id>/sla')
@ns.doc(security='Bearer Auth')
@ns.param('job_id', 'Job ID')
class JobSLA(Resource):
    """Get SLA status for a job."""
    
    @ns.doc('get_job_sla')
    @ns.marshal_with(sla_status_model)
    @ns.response(200, 'Success')
    @ns.response(404, 'Job not found')
    @ns.response(401, 'Unauthorized')
    @require_any_role(['Admin', 'Editor', 'Viewer'])
    def get(self, job_id):
        """Get SLA compliance status for a specific job."""
        session = get_db_session()
        try:
            job = session.query(Job).filter_by(job_id=job_id).first()
            if not job:
                from api.errors import NotFoundError
                raise NotFoundError(f'Job {job_id} not found')
            
            return calculate_job_sla_status(job)
        finally:
            session.close()


@ns.route('/failures')
@ns.doc(security='Bearer Auth')
class JobFailures(Resource):
    """Get job failure analysis."""
    
    @ns.doc('get_job_failures')
    @ns.param('days', 'Number of days to analyze', type=int, default=7)
    @ns.response(200, 'Success')
    @ns.response(401, 'Unauthorized')
    @require_any_role(['Admin', 'Editor'])
    def get(self):
        """Get analysis of failed jobs."""
        days = request.args.get('days', 7, type=int)
        session = get_db_session()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            failed_jobs = session.query(Job).filter(
                Job.status == 'failed',
                Job.created_at >= cutoff_date
            ).order_by(Job.created_at.desc()).all()
            
            # Group by error type
            error_groups = {}
            for job in failed_jobs:
                error_msg = job.error_message or 'Unknown error'
                # Extract error type (first part before colon or first word)
                error_type = error_msg.split(':')[0].split()[0] if error_msg else 'Unknown'
                if error_type not in error_groups:
                    error_groups[error_type] = {
                        'count': 0,
                        'jobs': [],
                        'latest': None
                    }
                error_groups[error_type]['count'] += 1
                error_groups[error_type]['jobs'].append({
                    'job_id': job.job_id,
                    'job_type': job.job_type,
                    'error_message': error_msg,
                    'created_at': job.created_at.isoformat() if job.created_at else None
                })
                if not error_groups[error_type]['latest'] or job.created_at > error_groups[error_type]['latest']:
                    error_groups[error_type]['latest'] = job.created_at.isoformat() if job.created_at else None
            
            # Group by job type
            by_job_type = {}
            for job in failed_jobs:
                if job.job_type not in by_job_type:
                    by_job_type[job.job_type] = 0
                by_job_type[job.job_type] += 1
            
            return {
                'period_days': days,
                'total_failures': len(failed_jobs),
                'by_error_type': error_groups,
                'by_job_type': by_job_type,
                'recent_failures': [job.to_dict() for job in failed_jobs[:10]]
            }
        finally:
            session.close()


"""
Jobs API namespace.

Endpoints for managing background scraper jobs.
"""

from flask_restx import Namespace, Resource, fields
from flask import request
from sqlalchemy.orm import sessionmaker
from sqlalchemy import func
import os
from datetime import datetime, timedelta
from api.errors import BadRequestError, InternalServerError, NotFoundError
from api.schemas import ScraperRunRequestSchema
from api.validators import validate_request_body, serialize_response
from auth.decorators import require_any_role
from tasks.scraper_tasks import scrape_all_accounts, scrape_account, scrape_platform, backfill_account
from tasks.utils import get_db_session
from models.job import Job
from scraper.schema import init_db

ns = Namespace('jobs', description='Background job management operations')

# Flask-RESTX models for documentation
scraper_request_model = ns.model('ScraperRequest', {
    'mode': fields.String(
        description='Scraper mode',
        enum=['simulated', 'real'],
        default='simulated',
        example='simulated'
    )
})

scraper_response_model = ns.model('ScraperResponse', {
    'message': fields.String(description='Response message'),
    'job_id': fields.String(description='Job ID for tracking'),
    'status': fields.String(description='Job status')
})

job_model = ns.model('Job', {
    'id': fields.Integer(description='Job database ID'),
    'job_id': fields.String(description='Celery task ID'),
    'job_type': fields.String(description='Type of job'),
    'status': fields.String(description='Job status'),
    'progress': fields.Float(description='Progress percentage'),
    'result': fields.Raw(description='Job result data'),
    'error_message': fields.String(description='Error message if failed'),
    'account_key': fields.Integer(description='Associated account key'),
    'platform': fields.String(description='Associated platform'),
    'created_at': fields.String(description='Creation timestamp'),
    'started_at': fields.String(description='Start timestamp'),
    'completed_at': fields.String(description='Completion timestamp'),
})

job_list_model = ns.model('JobList', {
    'data': fields.List(fields.Nested(job_model)),
    'pagination': fields.Raw(description='Pagination info')
})

job_stats_model = ns.model('JobStats', {
    'total_jobs': fields.Integer(description='Total number of jobs'),
    'pending': fields.Integer(description='Pending jobs'),
    'running': fields.Integer(description='Running jobs'),
    'completed': fields.Integer(description='Completed jobs'),
    'failed': fields.Integer(description='Failed jobs'),
    'cancelled': fields.Integer(description='Cancelled jobs'),
    'success_rate': fields.Float(description='Success rate percentage'),
    'avg_duration': fields.Float(description='Average job duration in seconds'),
})

error_model = ns.model('Error', {
    'error': fields.Nested(ns.model('ErrorDetail', {
        'code': fields.String(description='Error code'),
        'message': fields.String(description='Error message'),
        'details': fields.Raw(description='Additional error details')
    }))
})

# Helper function
def get_db_path():
    return os.getenv('DATABASE_PATH', 'social_media.db')


@ns.route('/run-scraper')
@ns.doc(security='Bearer Auth')
class RunScraper(Resource):
    """Run the scraper to collect metrics."""
    
    @ns.doc('run_scraper')
    @ns.expect(scraper_request_model)
    @ns.marshal_with(scraper_response_model)
    @ns.response(200, 'Success')
    @ns.response(400, 'Bad Request', error_model)
    @ns.response(401, 'Unauthorized', error_model)
    @ns.response(403, 'Forbidden', error_model)
    @ns.response(500, 'Internal Server Error', error_model)
    @require_any_role(['Admin', 'Editor'])
    def post(self):
        """
        Run the scraper to collect social media metrics.
        
        This endpoint triggers the scraper to collect metrics for all accounts.
        The scraper can run in simulated mode (for testing) or real mode.
        
        This endpoint triggers an asynchronous background job to scrape metrics
        for all accounts. The scraper can run in simulated mode (for testing) or real mode.
        
        Returns immediately with a job_id that can be used to track progress.
        
        Only Admin and Editor roles can run the scraper.
        """
        # Get mode from request body (default to 'simulated')
        mode = 'simulated'
        if request.is_json:
            data = request.get_json() or {}
            mode = data.get('mode', 'simulated')
        
        # Validate mode
        if mode not in ['simulated', 'real']:
            raise BadRequestError('Invalid mode. Must be "simulated" or "real"')
        
        try:
            db_path = get_db_path()
            # Trigger async task
            task = scrape_all_accounts.delay(mode=mode, db_path=db_path)
            
            # Create job record
            from tasks.utils import create_job_record
            create_job_record(task.id, 'scrape_all', db_path=db_path)
            
            return {
                'message': 'Scraper job started',
                'job_id': task.id,
                'status': 'pending'
            }
        except Exception as e:
            raise InternalServerError(f'Failed to start scraper job: {str(e)}')


@ns.route('/<job_id>')
@ns.doc(security='Bearer Auth')
@ns.param('job_id', 'Job ID (Celery task ID)')
class JobStatus(Resource):
    """Get job status information."""
    
    @ns.doc('get_job_status')
    @ns.marshal_with(job_model)
    @ns.response(200, 'Success')
    @ns.response(404, 'Job not found', error_model)
    @ns.response(401, 'Unauthorized', error_model)
    @require_any_role(['Admin', 'Editor', 'Viewer'])
    def get(self, job_id):
        """
        Get status of a specific job.
        
        Returns detailed information about a background job including
        status, progress, and results.
        """
        session = get_db_session()
        try:
            job = session.query(Job).filter_by(job_id=job_id).first()
            if not job:
                raise NotFoundError(f'Job {job_id} not found')
            
            # Also check Celery task status for real-time updates
            try:
                from celery_app import celery_app
                task = celery_app.AsyncResult(job_id)
                if task.state == 'PENDING':
                    pass  # Use database status
                elif task.state == 'PROGRESS':
                    job.status = 'running'
                    if task.info:
                        job.progress = task.info.get('progress', job.progress)
                elif task.state == 'SUCCESS':
                    if job.status in ['pending', 'running']:
                        job.status = 'completed'
                elif task.state == 'FAILURE':
                    if job.status != 'failed':
                        job.status = 'failed'
                        job.error_message = str(task.info) if task.info else 'Task failed'
            except Exception:
                pass  # If Celery is not available, use database status
            
            return job.to_dict()
        finally:
            session.close()


@ns.route('')
@ns.doc(security='Bearer Auth')
class JobList(Resource):
    """List all jobs with filtering and pagination."""
    
    @ns.doc('list_jobs')
    @ns.marshal_with(job_list_model)
    @ns.response(200, 'Success')
    @ns.response(401, 'Unauthorized', error_model)
    @require_any_role(['Admin', 'Editor', 'Viewer'])
    def get(self):
        """
        List all jobs with optional filtering and pagination.
        
        Query parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 50, max: 100)
        - status: Filter by status (pending, running, completed, failed, cancelled)
        - job_type: Filter by job type (scrape_all, scrape_account, etc.)
        """
        session = get_db_session()
        try:
            # Pagination parameters
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 50, type=int)
            status_filter = request.args.get('status', type=str)
            job_type_filter = request.args.get('job_type', type=str)
            
            per_page = min(per_page, 100)
            per_page = max(per_page, 1)
            
            # Base query
            query = session.query(Job)
            
            # Apply filters
            if status_filter:
                query = query.filter(Job.status == status_filter)
            if job_type_filter:
                query = query.filter(Job.job_type == job_type_filter)
            
            # Order by created_at descending
            query = query.order_by(Job.created_at.desc())
            
            # Get total count
            total = query.count()
            
            # Apply pagination
            jobs = query.offset((page - 1) * per_page).limit(per_page).all()
            
            data = [job.to_dict() for job in jobs]
            
            return {
                'data': data,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page if total > 0 else 0
                }
            }
        finally:
            session.close()


@ns.route('/stats')
@ns.doc(security='Bearer Auth')
class JobStats(Resource):
    """Get job statistics."""
    
    @ns.doc('get_job_stats')
    @ns.marshal_with(job_stats_model)
    @ns.response(200, 'Success')
    @ns.response(401, 'Unauthorized', error_model)
    @require_any_role(['Admin', 'Editor', 'Viewer'])
    def get(self):
        """
        Get statistics about jobs.
        
        Returns aggregated statistics including counts by status,
        success rate, and average duration.
        """
        session = get_db_session()
        try:
            # Get counts by status
            status_counts = session.query(
                Job.status,
                func.count(Job.id).label('count')
            ).group_by(Job.status).all()
            
            stats = {
                'total_jobs': 0,
                'pending': 0,
                'running': 0,
                'completed': 0,
                'failed': 0,
                'cancelled': 0,
            }
            
            for status, count in status_counts:
                stats['total_jobs'] += count
                if status in stats:
                    stats[status] = count
            
            # Calculate success rate
            completed = stats['completed']
            failed = stats['failed']
            total_finished = completed + failed
            stats['success_rate'] = (completed / total_finished * 100) if total_finished > 0 else 0.0
            
            # Calculate average duration for completed jobs
            completed_jobs = session.query(Job).filter(
                Job.status == 'completed',
                Job.started_at.isnot(None),
                Job.completed_at.isnot(None)
            ).all()
            
            if completed_jobs:
                durations = []
                for job in completed_jobs:
                    if job.started_at and job.completed_at:
                        duration = (job.completed_at - job.started_at).total_seconds()
                        durations.append(duration)
                stats['avg_duration'] = sum(durations) / len(durations) if durations else 0.0
            else:
                stats['avg_duration'] = 0.0
            
            return stats
        finally:
            session.close()


@ns.route('/<job_id>/pause')
@ns.doc(security='Bearer Auth')
@ns.param('job_id', 'Job ID (Celery task ID)')
class PauseJob(Resource):
    """Pause a pending job."""
    
    @ns.doc('pause_job')
    @ns.marshal_with(job_model)
    @ns.response(200, 'Success')
    @ns.response(400, 'Bad Request', error_model)
    @ns.response(404, 'Job not found', error_model)
    @ns.response(401, 'Unauthorized', error_model)
    @require_any_role(['Admin', 'Editor'])
    def post(self, job_id):
        """Pause a pending job."""
        from tasks.job_management import pause_job
        
        if pause_job(job_id):
            session = get_db_session()
            try:
                job = session.query(Job).filter_by(job_id=job_id).first()
                return job.to_dict()
            finally:
                session.close()
        else:
            raise BadRequestError('Job cannot be paused (must be pending)')


@ns.route('/<job_id>/resume')
@ns.doc(security='Bearer Auth')
@ns.param('job_id', 'Job ID (Celery task ID)')
class ResumeJob(Resource):
    """Resume a paused job."""
    
    @ns.doc('resume_job')
    @ns.marshal_with(job_model)
    @ns.response(200, 'Success')
    @ns.response(400, 'Bad Request', error_model)
    @ns.response(404, 'Job not found', error_model)
    @ns.response(401, 'Unauthorized', error_model)
    @require_any_role(['Admin', 'Editor'])
    def post(self, job_id):
        """Resume a paused job."""
        from tasks.job_management import resume_job
        
        if resume_job(job_id):
            session = get_db_session()
            try:
                job = session.query(Job).filter_by(job_id=job_id).first()
                return job.to_dict()
            finally:
                session.close()
        else:
            raise BadRequestError('Job cannot be resumed (must be paused and pending)')


@ns.route('/<job_id>/cancel')
@ns.doc(security='Bearer Auth')
@ns.param('job_id', 'Job ID (Celery task ID)')
class CancelJob(Resource):
    """Cancel a running job."""
    
    @ns.doc('cancel_job')
    @ns.marshal_with(job_model)
    @ns.response(200, 'Success')
    @ns.response(400, 'Bad Request', error_model)
    @ns.response(404, 'Job not found', error_model)
    @ns.response(401, 'Unauthorized', error_model)
    @require_any_role(['Admin', 'Editor'])
    def post(self, job_id):
        """
        Cancel a running or pending job.
        
        Only Admin and Editor roles can cancel jobs.
        """
        session = get_db_session()
        try:
            job = session.query(Job).filter_by(job_id=job_id).first()
            if not job:
                raise NotFoundError(f'Job {job_id} not found')
            
            if job.status not in ['pending', 'running']:
                raise BadRequestError(f'Cannot cancel job with status: {job.status}')
            
            # Revoke the Celery task
            try:
                from celery_app import celery_app
                celery_app.control.revoke(job_id, terminate=True)
            except Exception as e:
                # Log but don't fail if Celery is unavailable
                pass
            
            # Update job status
            job.status = 'cancelled'
            job.completed_at = datetime.utcnow()
            session.commit()
            
            return job.to_dict()
        finally:
            session.close()


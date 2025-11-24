"""
Celery tasks for scraping operations.
"""
import os
import json
import logging
from datetime import datetime, date
from celery_app import celery_app
from tasks.utils import get_db_session, update_job_progress, create_job_record
from scraper.schema import DimAccount, FactFollowersSnapshot
from scraper.collect_metrics import simulate_metrics
from scraper.backfill import backfill_history
from scraper.scrapers import get_scraper
from tasks.production_optimization import intelligent_backoff, should_retry_job
from tasks.job_checkpointing import save_job_checkpoint, load_job_checkpoint

# Set up logging
logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def scrape_account(self, account_key, mode='real', db_path=None):
    """
    Scrape metrics for a single account.
    
    Args:
        account_key: The account key to scrape
        mode: Scraper mode ('simulated' or 'real')
        db_path: Path to database file
    
    Returns:
        dict: Result with status and data
    """
    if db_path is None:
        db_path = os.getenv('DB_PATH', 'social_media.db')
    
    job_id = self.request.id
    session = None
    
    try:
        # Validate inputs
        if not account_key:
            raise ValueError("account_key is required")
        if not isinstance(account_key, (int, str)):
            raise ValueError(f"account_key must be int or str, got {type(account_key).__name__}")
        
        session = get_db_session(db_path)
        
        # Create or update job record
        from models.job import Job
        job = None
        try:
            job = session.query(Job).filter_by(job_id=job_id).first()
            if not job:
                # Job might not exist if created after task started, create it now
                try:
                    job = create_job_record(job_id, 'scrape_account', account_key=account_key, db_path=db_path)
                    session = get_db_session(db_path)  # Refresh session
                    job = session.query(Job).filter_by(job_id=job_id).first()
                except Exception as e:
                    logger.warning(
                        f"Could not create job record: {e}, continuing without it",
                        extra={'job_id': job_id, 'account_key': account_key}
                    )
        except Exception as e:
            logger.error(
                f"Error querying job record: {e}",
                extra={'job_id': job_id, 'account_key': account_key}
            )
            # Continue without job record
        
        if job:
            try:
                job.status = 'running'
                job.started_at = datetime.utcnow()
                session.commit()
            except Exception as e:
                logger.error(
                    f"Error updating job status: {e}",
                    extra={'job_id': job_id, 'account_key': account_key}
                )
                session.rollback()
        
        # Get account
        try:
            account = session.query(DimAccount).filter_by(account_key=account_key).first()
            if not account:
                raise ValueError(f"Account with key {account_key} not found")
        except Exception as e:
            logger.error(
                f"Error querying account: {e}",
                extra={'account_key': account_key}
            )
            raise
        
        # Update progress
        try:
            self.update_state(state='PROGRESS', meta={'progress': 25, 'message': f'Scraping {account.handle}...'})
            update_job_progress(job_id, 25, 'running', {'message': f'Scraping {account.handle}...'})
        except Exception as e:
            logger.warning(f"Error updating progress: {e}", extra={'job_id': job_id})
        
        # Get scraper and scrape
        logger.info(f"Starting scrape for account {account.handle} (key: {account_key})")
        try:
            scraper = get_scraper(mode)
            if not scraper:
                raise ValueError(f"Could not get scraper for mode: {mode}")
        except Exception as e:
            logger.error(f"Error getting scraper: {e}", extra={'mode': mode, 'account_key': account_key})
            raise
        
        try:
            data = scraper.scrape(account)
        except Exception as scrape_error:
            logger.error(
                f"Error during scraping: {scrape_error}",
                extra={
                    'account_key': account_key,
                    'platform': account.platform,
                    'handle': account.handle,
                    'error_type': type(scrape_error).__name__
                }
            )
            raise
        
        if not data:
            error_msg = f"Failed to scrape account {account.handle} - scraper returned no data"
            logger.error(error_msg, extra={'account_key': account_key, 'platform': account.platform})
            raise ValueError(error_msg)
        
        # Validate scraped data
        if not isinstance(data, dict):
            raise ValueError(f"Scraped data must be a dictionary, got {type(data).__name__}")
        
        # Update progress
        self.update_state(state='PROGRESS', meta={'progress': 75, 'message': 'Saving results...'})
        update_job_progress(job_id, 75, 'running', {'message': 'Saving results...'})
        
        # Check if snapshot exists for today
        today = date.today()
        existing = session.query(FactFollowersSnapshot).filter_by(
            account_key=account_key,
            snapshot_date=today
        ).first()
        
        # Update account metadata from scraped data
        from scraper.utils.metrics_calculator import update_account_metadata, calculate_snapshot_metrics
        try:
            update_account_metadata(account, data)
        except Exception as metadata_error:
            logger.warning(
                f"Error updating account metadata: {metadata_error}",
                extra={'account_key': account_key}
            )
            # Continue even if metadata update fails
        
        # Safely convert data values to integers
        def safe_int(value, default=0):
            """Safely convert value to integer."""
            try:
                if value is None:
                    return default
                return int(float(value)) if value else default
            except (ValueError, TypeError):
                return default
        
        if existing:
            # Update existing snapshot
            try:
                existing.followers_count = safe_int(data.get('followers_count'), 0)
                existing.following_count = safe_int(data.get('following_count'), 0)
                existing.posts_count = safe_int(data.get('posts_count'), 0)
                existing.likes_count = safe_int(data.get('likes_count'), 0)
                existing.comments_count = safe_int(data.get('comments_count'), 0)
                existing.shares_count = safe_int(data.get('shares_count'), 0)
                existing.subscribers_count = safe_int(data.get('subscribers_count'), 0)  # For YouTube
                existing.video_views = safe_int(data.get('views_count'), 0)  # For YouTube
                existing.videos_count = safe_int(data.get('videos_count'), 0)  # For YouTube
                existing.engagements_total = existing.likes_count + existing.comments_count + existing.shares_count
                
                # Recalculate metrics
                try:
                    calculate_snapshot_metrics(existing, session, account, data)
                except Exception as metrics_error:
                    logger.warning(
                        f"Error calculating metrics: {metrics_error}",
                        extra={'account_key': account_key}
                    )
            except Exception as update_error:
                logger.error(
                    f"Error updating existing snapshot: {update_error}",
                    extra={'account_key': account_key}
                )
                raise
        else:
            # Create new snapshot
            try:
                snapshot = FactFollowersSnapshot(
                    account_key=account_key,
                    snapshot_date=today,
                    followers_count=safe_int(data.get('followers_count'), 0),
                    following_count=safe_int(data.get('following_count'), 0),
                    posts_count=safe_int(data.get('posts_count'), 0),
                    likes_count=safe_int(data.get('likes_count'), 0),
                    comments_count=safe_int(data.get('comments_count'), 0),
                    shares_count=safe_int(data.get('shares_count'), 0),
                    subscribers_count=safe_int(data.get('subscribers_count'), 0),  # For YouTube
                    video_views=safe_int(data.get('views_count'), 0),  # For YouTube
                    videos_count=safe_int(data.get('videos_count'), 0),  # For YouTube
                    engagements_total=0
                )
                snapshot.engagements_total = snapshot.likes_count + snapshot.comments_count + snapshot.shares_count
                
                # Calculate additional metrics
                try:
                    calculate_snapshot_metrics(snapshot, session, account, data)
                except Exception as metrics_error:
                    logger.warning(
                        f"Error calculating metrics: {metrics_error}",
                        extra={'account_key': account_key}
                    )
                
                session.add(snapshot)
            except Exception as create_error:
                logger.error(
                    f"Error creating snapshot: {create_error}",
                    extra={'account_key': account_key}
                )
                raise
        
        try:
            session.commit()
        except Exception as commit_error:
            logger.error(
                f"Error committing snapshot: {commit_error}",
                extra={'account_key': account_key}
            )
            session.rollback()
            raise
        
        # Update job as completed
        result_data = {
            'status': 'completed',
            'account_key': account_key,
            'account_handle': account.handle,
            'platform': account.platform,
            'followers_count': data.get('followers_count', 0),
            'snapshot_date': today.isoformat()
        }
        
        if job:
            try:
                job.status = 'completed'
                job.progress = 100.0
                try:
                    job.result = json.dumps(result_data)
                except (TypeError, ValueError) as json_error:
                    logger.warning(
                        f"Error serializing result data: {json_error}",
                        extra={'job_id': job_id}
                    )
                    job.result = str(result_data)
                job.completed_at = datetime.utcnow()
                
                # Calculate duration
                if job.started_at:
                    job.duration_seconds = (job.completed_at - job.started_at).total_seconds()
                
                session.commit()
            except Exception as job_update_error:
                logger.error(
                    f"Error updating job completion status: {job_update_error}",
                    extra={'job_id': job_id, 'account_key': account_key}
                )
                session.rollback()
                # Don't fail the task if job update fails
        
        # Cache result if enabled
        try:
            from tasks.job_optimization import cache_job_result
            cache_job_result(job_id, result_data)
        except Exception as e:
            logger.debug(f"Could not cache job result: {e}")
        
        # Check and start dependent jobs
        try:
            from tasks.job_dependencies import check_and_start_dependent_jobs
            check_and_start_dependent_jobs(job_id)
        except Exception as e:
            logger.warning(f"Error checking dependent jobs: {e}")
        
        return result_data
        
    except Exception as exc:
        logger.error(
            f"Error in scrape_account task for account_key {account_key}: {exc}",
            exc_info=True,
            extra={
                'account_key': account_key,
                'job_id': job_id,
                'error_type': type(exc).__name__,
                'mode': mode
            }
        )
        
        if session:
            try:
                session.rollback()
                # Update job as failed
                from models.job import Job
                try:
                    job = session.query(Job).filter_by(job_id=job_id).first()
                    if job:
                        job.status = 'failed'
                        job.error_message = str(exc)[:500]  # Limit error message length
                        job.completed_at = datetime.utcnow()
                        session.commit()
                except Exception as job_update_error:
                    logger.error(
                        f"Error updating failed job status: {job_update_error}",
                        extra={'job_id': job_id, 'account_key': account_key}
                    )
                    session.rollback()
            except Exception as rollback_error:
                logger.error(
                    f"Error during rollback: {rollback_error}",
                    extra={'job_id': job_id, 'account_key': account_key}
                )
        else:
            logger.warning(
                f"No session available for rollback",
                extra={'job_id': job_id, 'account_key': account_key}
            )
        
        # Intelligent retry with backoff
        if self.request.retries < self.max_retries:
            should_retry, reason = should_retry_job(job, type(exc).__name__)
            
            if should_retry:
                retry_countdown = intelligent_backoff(self.request.retries)
                logger.info(f"Retrying scrape_account task (attempt {self.request.retries + 1}/{self.max_retries}) in {retry_countdown}s - {reason}")
                raise self.retry(exc=exc, countdown=retry_countdown)
            else:
                logger.error(f"Not retrying scrape_account task: {reason}")
                raise exc
        else:
            logger.error(f"Max retries exceeded for scrape_account task")
            raise exc
    finally:
        if session:
            session.close()

@celery_app.task(bind=True, max_retries=2, default_retry_delay=120)
def scrape_all_accounts(self, mode='real', db_path=None):
    """
    Scrape metrics for all accounts.
    
    Args:
        mode: Scraper mode ('simulated' or 'real')
        db_path: Path to database file
    
    Returns:
        dict: Result with status and summary
    """
    if db_path is None:
        db_path = os.getenv('DB_PATH', 'social_media.db')
    
    job_id = self.request.id
    session = get_db_session(db_path)
    
    try:
        # Create or update job record
        from models.job import Job
        job = session.query(Job).filter_by(job_id=job_id).first()
        if not job:
            job = Job(
                job_id=job_id,
                job_type='scrape_all',
                status='running',
                started_at=datetime.utcnow()
            )
            session.add(job)
        else:
            job.status = 'running'
            job.started_at = datetime.utcnow()
        session.commit()
        
        # Get all active accounts
        accounts = session.query(DimAccount).filter(
            (DimAccount.is_active == True) | (DimAccount.is_active.is_(None))
        ).all()
        total_accounts = len(accounts)
        
        if total_accounts == 0:
            raise ValueError("No accounts found in database")
        
        logger.info(f"Starting scrape_all_accounts job for {total_accounts} accounts")
        
        # Update progress
        self.update_state(state='PROGRESS', meta={'progress': 10, 'message': f'Starting scrape for {total_accounts} accounts...'})
        update_job_progress(job_id, 10, 'running', {'message': f'Starting scrape for {total_accounts} accounts...'})
        
        # Use the existing collect_metrics function
        session.close()  # Close before calling simulate_metrics which creates its own session
        
        # Update progress before starting
        self.update_state(state='PROGRESS', meta={'progress': 20, 'message': 'Running scraper...'})
        update_job_progress(job_id, 20, 'running', {'message': 'Running scraper...'})
        
        # Progress callback to update job progress
        def progress_callback(processed, total, current_account, speed, elapsed):
            progress = 20 + int((processed / total) * 70)  # 20-90% range
            eta_seconds = (total - processed) / speed if speed > 0 else 0
            eta_str = f"{int(eta_seconds // 60)}m {int(eta_seconds % 60)}s" if eta_seconds > 0 else "--"
            
            meta = {
                'progress': progress,
                'message': f'Scraping {current_account}... ({processed}/{total})',
                'processed': processed,
                'total': total,
                'speed': round(speed, 2),
                'elapsed': round(elapsed, 1),
                'eta': eta_str
            }
            self.update_state(state='PROGRESS', meta=meta)
            update_job_progress(job_id, progress, 'running', meta)
        
        # Optimize: Use more workers for better parallelization (up to 10)
        import os
        max_workers = min(10, int(os.getenv('SCRAPER_MAX_WORKERS', '8')))
        simulate_metrics(db_path=db_path, mode=mode, parallel=True, max_workers=max_workers, progress_callback=progress_callback)
        
        # Update progress after completion
        self.update_state(state='PROGRESS', meta={'progress': 90, 'message': 'Finalizing...'})
        update_job_progress(job_id, 90, 'running', {'message': 'Finalizing...'})
        
        # Reopen session for job update
        session = get_db_session(db_path)
        job = session.query(Job).filter_by(job_id=job_id).first()
        
        # Update job as completed
        result_data = {
            'status': 'completed',
            'total_accounts': total_accounts,
            'message': f'Successfully scraped {total_accounts} accounts'
        }
        
        job.status = 'completed'
        job.progress = 100.0
        job.result = json.dumps(result_data)
        job.completed_at = datetime.utcnow()
        session.commit()
        
        return result_data
        
    except Exception as exc:
        if 'session' in locals():
            session.rollback()
            from models.job import Job
            job = session.query(Job).filter_by(job_id=job_id).first()
            if job:
                job.status = 'failed'
                job.error_message = str(exc)
                job.completed_at = datetime.utcnow()
                session.commit()
            session.close()
        
        # Retry if we haven't exceeded max retries
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=120 * (self.request.retries + 1))
        else:
            raise exc

@celery_app.task(bind=True, max_retries=2, default_retry_delay=120)
def scrape_platform(self, platform, mode='real', db_path=None):
    """
    Scrape metrics for all accounts on a specific platform.
    
    Args:
        platform: Platform name (e.g., 'x', 'instagram', 'youtube')
        mode: Scraper mode ('simulated' or 'real')
        db_path: Path to database file
    
    Returns:
        dict: Result with status and summary
    """
    if db_path is None:
        db_path = os.getenv('DB_PATH', 'social_media.db')
    
    job_id = self.request.id
    session = get_db_session(db_path)
    
    try:
        # Create or update job record
        from models.job import Job
        job = session.query(Job).filter_by(job_id=job_id).first()
        if not job:
            job = Job(
                job_id=job_id,
                job_type='scrape_platform',
                status='running',
                platform=platform,
                started_at=datetime.utcnow()
            )
            session.add(job)
        else:
            job.status = 'running'
            job.started_at = datetime.utcnow()
        session.commit()
        
        # Get active accounts for platform
        accounts = session.query(DimAccount).filter_by(platform=platform).filter(
            (DimAccount.is_active == True) | (DimAccount.is_active.is_(None))
        ).all()
        total_accounts = len(accounts)
        
        if total_accounts == 0:
            raise ValueError(f"No accounts found for platform {platform}")
        
        # Update progress
        self.update_state(state='PROGRESS', meta={'progress': 10, 'message': f'Starting scrape for {total_accounts} {platform} accounts...'})
        update_job_progress(job_id, 10, 'running', {'message': f'Starting scrape for {total_accounts} {platform} accounts...'})
        
        # Scrape each account
        scraper = get_scraper(mode)
        today = date.today()
        processed = 0
        
        for i, account in enumerate(accounts):
            # Update progress
            progress = 10 + int((i / total_accounts) * 80)
            self.update_state(state='PROGRESS', meta={'progress': progress, 'message': f'Scraping {account.handle}...'})
            update_job_progress(job_id, progress, 'running', {'message': f'Scraping {account.handle}...'})
            
            # Check if snapshot exists for today
            existing = session.query(FactFollowersSnapshot).filter_by(
                account_key=account.account_key,
                snapshot_date=today
            ).first()
            
            if existing:
                processed += 1
                continue
            
            # Scrape account
            data = scraper.scrape(account)
            
            if data:
                snapshot = FactFollowersSnapshot(
                    account_key=account.account_key,
                    snapshot_date=today,
                    followers_count=data.get('followers_count', 0),
                    following_count=data.get('following_count', 0),
                    posts_count=data.get('posts_count', 0),
                    likes_count=data.get('likes_count', 0),
                    comments_count=data.get('comments_count', 0),
                    shares_count=data.get('shares_count', 0),
                    subscribers_count=data.get('subscribers_count', 0),  # For YouTube
                    video_views=data.get('views_count', 0),  # For YouTube
                    engagements_total=0
                )
                snapshot.engagements_total = snapshot.likes_count + snapshot.comments_count + snapshot.shares_count
                session.add(snapshot)
                processed += 1
        
        session.commit()
        
        # Update job as completed
        result_data = {
            'status': 'completed',
            'platform': platform,
            'total_accounts': total_accounts,
            'processed': processed,
            'message': f'Successfully scraped {processed} accounts on {platform}'
        }
        
        job.status = 'completed'
        job.progress = 100.0
        job.result = json.dumps(result_data)
        job.completed_at = datetime.utcnow()
        session.commit()
        
        return result_data
        
    except Exception as exc:
        session.rollback()
        
        from models.job import Job
        job = session.query(Job).filter_by(job_id=job_id).first()
        if job:
            job.status = 'failed'
            job.error_message = str(exc)
            job.completed_at = datetime.utcnow()
            session.commit()
        
        # Retry if we haven't exceeded max retries
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=120 * (self.request.retries + 1))
        else:
            raise exc
    finally:
        session.close()

@celery_app.task(bind=True, max_retries=2, default_retry_delay=120)
def scrape_selected_accounts(self, account_keys, mode='real', db_path=None):
    """
    Scrape metrics for specific accounts.
    
    Args:
        account_keys: List of account keys to scrape
        mode: Scraper mode ('simulated' or 'real')
        db_path: Path to database file
    
    Returns:
        dict: Result with status and summary
    """
    if db_path is None:
        db_path = os.getenv('DB_PATH', 'social_media.db')
    
    if not account_keys or not isinstance(account_keys, list):
        raise ValueError("account_keys must be a non-empty list")
    
    job_id = self.request.id
    session = get_db_session(db_path)
    
    try:
        # Create or update job record
        from models.job import Job
        job = session.query(Job).filter_by(job_id=job_id).first()
        if not job:
            job = Job(
                job_id=job_id,
                job_type='scrape_selected',
                status='running',
                started_at=datetime.utcnow()
            )
            session.add(job)
        else:
            job.status = 'running'
            job.started_at = datetime.utcnow()
        session.commit()
        
        # Get accounts
        accounts = session.query(DimAccount).filter(DimAccount.account_key.in_(account_keys)).all()
        total_accounts = len(accounts)
        
        if total_accounts == 0:
            raise ValueError(f"No accounts found for the provided account keys: {account_keys}")
        
        if total_accounts != len(account_keys):
            found_keys = [a.account_key for a in accounts]
            missing_keys = [k for k in account_keys if k not in found_keys]
            logger.warning(f"Some account keys not found: {missing_keys}")
        
        logger.info(f"Starting scrape_selected_accounts job for {total_accounts} accounts")
        
        # Update progress
        self.update_state(state='PROGRESS', meta={'progress': 10, 'message': f'Starting scrape for {total_accounts} selected accounts...'})
        update_job_progress(job_id, 10, 'running', {'message': f'Starting scrape for {total_accounts} selected accounts...'})
        
        # Use the existing collect_metrics function with account_keys
        session.close()  # Close before calling simulate_metrics which creates its own session
        
        # Update progress before starting
        self.update_state(state='PROGRESS', meta={'progress': 20, 'message': 'Running scraper...'})
        update_job_progress(job_id, 20, 'running', {'message': 'Running scraper...'})
        
        # Progress callback to update job progress
        def progress_callback(processed, total, current_account, speed, elapsed):
            progress = 20 + int((processed / total) * 70)  # 20-90% range
            eta_seconds = (total - processed) / speed if speed > 0 else 0
            eta_str = f"{int(eta_seconds // 60)}m {int(eta_seconds % 60)}s" if eta_seconds > 0 else "--"
            
            meta = {
                'progress': progress,
                'message': f'Scraping {current_account}... ({processed}/{total})',
                'processed': processed,
                'total': total,
                'speed': round(speed, 2),
                'elapsed': round(elapsed, 1),
                'eta': eta_str
            }
            self.update_state(state='PROGRESS', meta=meta)
            update_job_progress(job_id, progress, 'running', meta)
        
        # Optimize: Use more workers for better parallelization (up to 10)
        import os
        max_workers = min(10, int(os.getenv('SCRAPER_MAX_WORKERS', '8')))
        from scraper.collect_metrics import simulate_metrics
        simulate_metrics(db_path=db_path, mode=mode, parallel=True, max_workers=max_workers, 
                         progress_callback=progress_callback, account_keys=account_keys)
        
        # Update progress after completion
        self.update_state(state='PROGRESS', meta={'progress': 90, 'message': 'Finalizing...'})
        update_job_progress(job_id, 90, 'running', {'message': 'Finalizing...'})
        
        # Reopen session for job update
        session = get_db_session(db_path)
        job = session.query(Job).filter_by(job_id=job_id).first()
        
        # Update job as completed
        result_data = {
            'status': 'completed',
            'total_accounts': total_accounts,
            'account_keys': account_keys,
            'message': f'Successfully scraped {total_accounts} selected accounts'
        }
        
        job.status = 'completed'
        job.progress = 100.0
        job.result = json.dumps(result_data)
        job.completed_at = datetime.utcnow()
        session.commit()
        
        return result_data
        
    except Exception as exc:
        if 'session' in locals():
            session.rollback()
            from models.job import Job
            job = session.query(Job).filter_by(job_id=job_id).first()
            if job:
                job.status = 'failed'
                job.error_message = str(exc)
                job.completed_at = datetime.utcnow()
                session.commit()
            session.close()
        
        # Retry if we haven't exceeded max retries
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=120 * (self.request.retries + 1))
        else:
            raise exc

@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def backfill_account(self, account_key, days=365, db_path=None):
    """
    Backfill historical data for a specific account.
    
    Args:
        account_key: The account key to backfill
        days: Number of days to backfill (default 365)
        db_path: Path to database file
    
    Returns:
        dict: Result with status and summary
    """
    if db_path is None:
        db_path = os.getenv('DB_PATH', 'social_media.db')
    
    job_id = self.request.id
    session = get_db_session(db_path)
    
    try:
        # Create or update job record
        from models.job import Job
        job = session.query(Job).filter_by(job_id=job_id).first()
        if not job:
            job = Job(
                job_id=job_id,
                job_type='backfill_account',
                status='running',
                account_key=account_key,
                started_at=datetime.utcnow()
            )
            session.add(job)
        else:
            job.status = 'running'
            job.started_at = datetime.utcnow()
        session.commit()
        
        # Get account
        account = session.query(DimAccount).filter_by(account_key=account_key).first()
        if not account:
            raise ValueError(f"Account with key {account_key} not found")
        
        # Update progress
        self.update_state(state='PROGRESS', meta={'progress': 10, 'message': f'Starting backfill for {account.handle}...'})
        update_job_progress(job_id, 10, 'running', {'message': f'Starting backfill for {account.handle}...'})
        
        # Close session before calling backfill_history which creates its own session
        session.close()
        
        # Use the existing backfill function (but we need to modify it to work with single account)
        # For now, we'll call the full backfill and it will handle all accounts
        # In a production system, you'd want a single-account backfill function
        backfill_history(db_path=db_path, days_back=days)
        
        # Reopen session for job update
        session = get_db_session(db_path)
        job = session.query(Job).filter_by(job_id=job_id).first()
        
        # Update job as completed
        result_data = {
            'status': 'completed',
            'account_key': account_key,
            'account_handle': account.handle,
            'days': days,
            'message': f'Successfully backfilled {days} days of history for {account.handle}'
        }
        
        job.status = 'completed'
        job.progress = 100.0
        job.result = json.dumps(result_data)
        job.completed_at = datetime.utcnow()
        session.commit()
        
        return result_data
        
    except Exception as exc:
        if 'session' in locals():
            session.rollback()
            from models.job import Job
            job = session.query(Job).filter_by(job_id=job_id).first()
            if job:
                job.status = 'failed'
                job.error_message = str(exc)
                job.completed_at = datetime.utcnow()
                session.commit()
            session.close()
        
        # Retry if we haven't exceeded max retries
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=300 * (self.request.retries + 1))
        else:
            raise exc


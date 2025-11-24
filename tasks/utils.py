"""
Utility functions for task processing.
"""
import os
import logging
from sqlalchemy.orm import sessionmaker
from scraper.schema import init_db

# Set up logging
logger = logging.getLogger(__name__)

# Cache engines per db_path to avoid recreating them
_engine_cache = {}


def get_db_session(db_path=None):
    """
    Get a database session for tasks.
    Reuses engines to improve performance.
    """
    if db_path is None:
        db_path = os.getenv("DB_PATH", "social_media.db")

    # Reuse engine if available
    if db_path not in _engine_cache:
        _engine_cache[db_path] = init_db(db_path)

    engine = _engine_cache[db_path]
    Session = sessionmaker(bind=engine)
    return Session()


def update_job_progress(job_id, progress, status="PROGRESS", meta=None):
    """
    Update job progress in the database.

    Args:
        job_id: Celery task ID
        progress: Progress percentage (0-100)
        status: Job status (pending, running, completed, failed, cancelled)
        meta: Optional metadata to store in result field
    """
    from models.job import Job

    session = None
    try:
        session = get_db_session()
        job = session.query(Job).filter_by(job_id=job_id).first()
        if job:
            job.progress = min(100.0, max(0.0, float(progress)))  # Clamp between 0-100
            job.status = status.lower() if isinstance(status, str) else status
            if meta:
                import json

                try:
                    job.result = json.dumps(meta)
                except (TypeError, ValueError) as e:
                    logger.warning(f"Failed to serialize job meta for {job_id}: {e}")
                    job.result = str(meta)
            session.commit()
            logger.debug(
                f"Updated job {job_id} progress to {progress}% with status {status}"
            )
        else:
            logger.warning(f"Job {job_id} not found in database for progress update")
    except Exception as e:
        if session:
            session.rollback()
        logger.error(f"Error updating job progress for {job_id}: {e}", exc_info=True)
    finally:
        if session:
            session.close()


def create_job_record(job_id, job_type, account_key=None, platform=None, db_path=None):
    """
    Create a job record in the database.

    Args:
        job_id: Celery task ID
        job_type: Type of job (scrape_all, scrape_account, etc.)
        account_key: Optional account key
        platform: Optional platform name
        db_path: Optional database path

    Returns:
        Job: The created job object
    """
    from models.job import Job
    from datetime import datetime

    session = None
    try:
        session = get_db_session(db_path)
        job = Job(
            job_id=job_id,
            job_type=job_type,
            status="pending",
            progress=0.0,
            account_key=account_key,
            platform=platform,
            created_at=datetime.utcnow(),
        )
        session.add(job)
        session.commit()
        logger.info(f"Created job record {job_id} of type {job_type}")
        return job
    except Exception as e:
        if session:
            session.rollback()
        logger.error(f"Error creating job record {job_id}: {e}", exc_info=True)
        raise
    finally:
        if session:
            session.close()

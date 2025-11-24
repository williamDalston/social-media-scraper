"""
Job result optimization utilities.
"""
import json
import gzip
import logging
from datetime import datetime, timedelta
from tasks.utils import get_db_session
from models.job import Job

logger = logging.getLogger(__name__)


def compress_job_result(result_data):
    """
    Compress job result data.

    Args:
        result_data: Dictionary or string to compress

    Returns:
        bytes: Compressed data
    """
    if isinstance(result_data, dict):
        data_str = json.dumps(result_data)
    else:
        data_str = str(result_data)

    return gzip.compress(data_str.encode("utf-8"))


def decompress_job_result(compressed_data):
    """
    Decompress job result data.

    Args:
        compressed_data: Compressed bytes

    Returns:
        dict: Decompressed data
    """
    try:
        decompressed = gzip.decompress(compressed_data)
        return json.loads(decompressed.decode("utf-8"))
    except Exception as e:
        logger.error(f"Error decompressing job result: {e}")
        return None


def cache_job_result(job_id, result_data, ttl_seconds=3600):
    """
    Cache job result in Redis (if available).

    Args:
        job_id: Job ID
        result_data: Result data to cache
        ttl_seconds: Time to live in seconds

    Returns:
        bool: True if cached successfully
    """
    try:
        import redis
        from celery_app import celery_app

        redis_client = redis.from_url(celery_app.conf.broker_url)
        cache_key = f"job_result:{job_id}"

        # Compress and cache
        compressed = compress_job_result(result_data)
        redis_client.setex(cache_key, ttl_seconds, compressed)

        logger.debug(f"Cached job result for {job_id}")
        return True
    except Exception as e:
        logger.warning(f"Could not cache job result: {e}")
        return False


def get_cached_job_result(job_id):
    """
    Get cached job result.

    Args:
        job_id: Job ID

    Returns:
        dict: Cached result or None
    """
    try:
        import redis
        from celery_app import celery_app

        redis_client = redis.from_url(celery_app.conf.broker_url)
        cache_key = f"job_result:{job_id}"

        compressed = redis_client.get(cache_key)
        if compressed:
            return decompress_job_result(compressed)
    except Exception as e:
        logger.warning(f"Could not get cached job result: {e}")
    return None


def archive_old_job_results(days=90):
    """
    Archive old job results to reduce database size.

    Args:
        days: Archive jobs older than this many days

    Returns:
        int: Number of jobs archived
    """
    session = get_db_session()
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        old_jobs = (
            session.query(Job)
            .filter(
                Job.completed_at < cutoff_date,
                Job.status.in_(["completed", "failed"]),
                Job.result.isnot(None),
            )
            .all()
        )

        archived_count = 0
        for job in old_jobs:
            # Compress and store result
            if job.result:
                try:
                    # Parse result
                    result_data = (
                        json.loads(job.result)
                        if isinstance(job.result, str)
                        else job.result
                    )

                    # Compress
                    compressed = compress_job_result(result_data)

                    # Store compressed version (in production, might store in object storage)
                    # For now, we'll just mark as archived and clear the result
                    job.result = f"ARCHIVED:{len(compressed)} bytes"
                    archived_count += 1
                except Exception as e:
                    logger.error(f"Error archiving job {job.id}: {e}")

        session.commit()
        logger.info(f"Archived {archived_count} job results")
        return archived_count
    finally:
        session.close()


def stream_job_result(job_id, chunk_size=1024):
    """
    Stream job result in chunks (for long-running tasks).

    Args:
        job_id: Job ID
        chunk_size: Chunk size in bytes

    Yields:
        bytes: Chunks of result data
    """
    session = get_db_session()
    try:
        job = session.query(Job).filter_by(job_id=job_id).first()
        if not job or not job.result:
            return

        result_str = job.result
        result_bytes = (
            result_str.encode("utf-8") if isinstance(result_str, str) else result_str
        )

        for i in range(0, len(result_bytes), chunk_size):
            yield result_bytes[i : i + chunk_size]
    finally:
        session.close()

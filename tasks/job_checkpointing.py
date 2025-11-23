"""
Job checkpointing and state persistence for long-running tasks.
"""
import json
import logging
from datetime import datetime
from tasks.utils import get_db_session
from models.job import Job

logger = logging.getLogger(__name__)


def save_job_checkpoint(job_id, checkpoint_data, checkpoint_name='default'):
    """
    Save a checkpoint for a job to allow resuming.
    
    Args:
        job_id: Job ID
        checkpoint_data: Data to save in checkpoint
        checkpoint_name: Name of checkpoint
        
    Returns:
        bool: True if saved successfully
    """
    try:
        import redis
        from celery_app import celery_app
        
        redis_client = redis.from_url(celery_app.conf.broker_url)
        checkpoint_key = f"job_checkpoint:{job_id}:{checkpoint_name}"
        
        checkpoint = {
            'job_id': job_id,
            'checkpoint_name': checkpoint_name,
            'data': checkpoint_data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        redis_client.setex(
            checkpoint_key,
            86400 * 7,  # 7 days TTL
            json.dumps(checkpoint)
        )
        
        logger.debug(f"Saved checkpoint {checkpoint_name} for job {job_id}")
        return True
    except Exception as e:
        logger.warning(f"Could not save checkpoint: {e}")
        # Fallback to database
        return save_job_checkpoint_db(job_id, checkpoint_data, checkpoint_name)


def save_job_checkpoint_db(job_id, checkpoint_data, checkpoint_name='default'):
    """
    Save checkpoint to database as fallback.
    
    Args:
        job_id: Job ID
        checkpoint_data: Data to save
        checkpoint_name: Name of checkpoint
        
    Returns:
        bool: True if saved successfully
    """
    session = get_db_session()
    try:
        job = session.query(Job).filter_by(job_id=job_id).first()
        if not job:
            return False
        
        # Store checkpoint in result field as JSON
        checkpoints = {}
        if job.result:
            try:
                result_data = json.loads(job.result)
                if isinstance(result_data, dict) and '_checkpoints' in result_data:
                    checkpoints = result_data['_checkpoints']
            except (json.JSONDecodeError, TypeError):
                pass
        
        checkpoints[checkpoint_name] = {
            'data': checkpoint_data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if isinstance(result_data, dict):
            result_data['_checkpoints'] = checkpoints
        else:
            result_data = {'_checkpoints': checkpoints}
        
        job.result = json.dumps(result_data)
        session.commit()
        
        return True
    except Exception as e:
        logger.error(f"Error saving checkpoint to database: {e}")
        session.rollback()
        return False
    finally:
        session.close()


def load_job_checkpoint(job_id, checkpoint_name='default'):
    """
    Load a checkpoint for a job.
    
    Args:
        job_id: Job ID
        checkpoint_name: Name of checkpoint
        
    Returns:
        dict: Checkpoint data or None
    """
    try:
        import redis
        from celery_app import celery_app
        
        redis_client = redis.from_url(celery_app.conf.broker_url)
        checkpoint_key = f"job_checkpoint:{job_id}:{checkpoint_name}"
        
        checkpoint_json = redis_client.get(checkpoint_key)
        if checkpoint_json:
            checkpoint = json.loads(checkpoint_json)
            return checkpoint.get('data')
    except Exception as e:
        logger.debug(f"Could not load checkpoint from Redis: {e}")
    
    # Fallback to database
    return load_job_checkpoint_db(job_id, checkpoint_name)


def load_job_checkpoint_db(job_id, checkpoint_name='default'):
    """
    Load checkpoint from database.
    
    Args:
        job_id: Job ID
        checkpoint_name: Name of checkpoint
        
    Returns:
        dict: Checkpoint data or None
    """
    session = get_db_session()
    try:
        job = session.query(Job).filter_by(job_id=job_id).first()
        if not job or not job.result:
            return None
        
        try:
            result_data = json.loads(job.result)
            if isinstance(result_data, dict) and '_checkpoints' in result_data:
                checkpoints = result_data['_checkpoints']
                if checkpoint_name in checkpoints:
                    return checkpoints[checkpoint_name].get('data')
        except (json.JSONDecodeError, TypeError):
            pass
        
        return None
    finally:
        session.close()


def resume_job_from_checkpoint(job_id, checkpoint_name='default'):
    """
    Resume a job from a checkpoint.
    
    Args:
        job_id: Job ID
        checkpoint_name: Name of checkpoint to resume from
        
    Returns:
        dict: Checkpoint data or None
    """
    checkpoint = load_job_checkpoint(job_id, checkpoint_name)
    
    if checkpoint:
        logger.info(f"Resuming job {job_id} from checkpoint {checkpoint_name}")
        return checkpoint
    
    logger.warning(f"No checkpoint found for job {job_id}")
    return None


def save_job_state(job_id, state_data):
    """
    Save complete job state for persistence.
    
    Args:
        job_id: Job ID
        state_data: Complete state data
        
    Returns:
        bool: True if saved successfully
    """
    session = get_db_session()
    try:
        job = session.query(Job).filter_by(job_id=job_id).first()
        if not job:
            return False
        
        # Store state in result field
        state = {
            '_state': state_data,
            '_state_timestamp': datetime.utcnow().isoformat()
        }
        
        # Merge with existing result if any
        if job.result:
            try:
                existing = json.loads(job.result)
                if isinstance(existing, dict):
                    state.update(existing)
            except (json.JSONDecodeError, TypeError):
                pass
        
        job.result = json.dumps(state)
        session.commit()
        
        logger.debug(f"Saved state for job {job_id}")
        return True
    except Exception as e:
        logger.error(f"Error saving job state: {e}")
        session.rollback()
        return False
    finally:
        session.close()


def load_job_state(job_id):
    """
    Load complete job state.
    
    Args:
        job_id: Job ID
        
    Returns:
        dict: State data or None
    """
    session = get_db_session()
    try:
        job = session.query(Job).filter_by(job_id=job_id).first()
        if not job or not job.result:
            return None
        
        try:
            result_data = json.loads(job.result)
            if isinstance(result_data, dict) and '_state' in result_data:
                return result_data['_state']
        except (json.JSONDecodeError, TypeError):
            pass
        
        return None
    finally:
        session.close()


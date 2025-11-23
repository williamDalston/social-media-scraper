"""
API key authentication for service accounts.
"""
import secrets
import hashlib
from datetime import datetime
from sqlalchemy.orm import sessionmaker
from scraper.schema import init_db
from models.user import User
from .audit import log_security_event, AuditEventType
import os
from dotenv import load_dotenv

load_dotenv()

db_path = os.getenv('DATABASE_PATH', 'social_media.db')

def get_db_session():
    """Get database session."""
    engine = init_db(db_path)
    Session = sessionmaker(bind=engine)
    return Session()

def generate_api_key() -> str:
    """
    Generate a secure API key.
    
    Returns:
        Secure random API key string
    """
    return f"sk_{secrets.token_urlsafe(32)}"

def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for storage.
    
    Args:
        api_key: Plain text API key
    
    Returns:
        Hashed API key
    """
    return hashlib.sha256(api_key.encode()).hexdigest()

def create_api_key(user_id: int) -> str:
    """
    Create an API key for a user.
    
    Args:
        user_id: User ID
    
    Returns:
        API key string
    """
    session = get_db_session()
    try:
        user = session.query(User).filter_by(id=user_id, is_active=True).first()
        
        if not user:
            return None
        
        # Generate API key
        api_key = generate_api_key()
        api_key_hash = hash_api_key(api_key)
        
        # Store hashed key
        user.api_key = api_key_hash
        user.api_key_created = datetime.utcnow()
        
        session.commit()
        
        # Log the event
        log_security_event(
            AuditEventType.API_KEY_CREATED,
            user_id=user_id,
            username=user.username,
            success=True
        )
        
        return api_key
    except Exception as e:
        session.rollback()
        return None
    finally:
        session.close()

def verify_api_key(api_key: str) -> User:
    """
    Verify an API key and return the user if valid.
    
    Args:
        api_key: API key to verify
    
    Returns:
        User object if key is valid, None otherwise
    """
    session = get_db_session()
    try:
        api_key_hash = hash_api_key(api_key)
        
        user = session.query(User).filter_by(
            api_key=api_key_hash,
            is_active=True
        ).first()
        
        return user
    except Exception:
        return None
    finally:
        session.close()

def revoke_api_key(user_id: int) -> bool:
    """
    Revoke an API key for a user.
    
    Args:
        user_id: User ID
    
    Returns:
        True if key was revoked, False otherwise
    """
    session = get_db_session()
    try:
        user = session.query(User).filter_by(id=user_id).first()
        
        if not user:
            return False
        
        # Clear API key
        user.api_key = None
        user.api_key_created = None
        
        session.commit()
        
        # Log the event
        log_security_event(
            AuditEventType.API_KEY_REVOKED,
            user_id=user_id,
            username=user.username,
            success=True
        )
        
        return True
    except Exception:
        session.rollback()
        return False
    finally:
        session.close()


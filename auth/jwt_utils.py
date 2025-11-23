import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app
from sqlalchemy.orm import sessionmaker
from scraper.schema import init_db
from models.user import User
import os
from dotenv import load_dotenv

load_dotenv()

# JWT Configuration
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)

db_path = os.getenv('DATABASE_PATH', 'social_media.db')

def get_db_session():
    """Get database session."""
    engine = init_db(db_path)
    Session = sessionmaker(bind=engine)
    return Session()

def generate_token(user_id: int, role: str, token_type: str = 'access') -> dict:
    """
    Generate JWT token for a user.
    
    Args:
        user_id: User ID
        role: User role
        token_type: 'access' or 'refresh'
    
    Returns:
        Dictionary with token and expiration
    """
    expires_delta = JWT_ACCESS_TOKEN_EXPIRES if token_type == 'access' else JWT_REFRESH_TOKEN_EXPIRES
    
    payload = {
        'user_id': user_id,
        'role': role,
        'type': token_type,
        'exp': datetime.utcnow() + expires_delta,
        'iat': datetime.utcnow()
    }
    
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    
    return {
        'token': token,
        'expires_in': int(expires_delta.total_seconds()),
        'token_type': 'Bearer'
    }

def verify_token(token: str) -> dict:
    """
    Verify and decode JWT token.
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded token payload
    
    Raises:
        jwt.ExpiredSignatureError: If token is expired
        jwt.InvalidTokenError: If token is invalid
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")

def get_current_user():
    """
    Get current user from JWT token in request headers.
    
    Returns:
        User object or None
    """
    auth_header = request.headers.get('Authorization')
    
    if not auth_header:
        return None
    
    try:
        # Extract token from "Bearer <token>"
        token = auth_header.split(' ')[1] if ' ' in auth_header else auth_header
        payload = verify_token(token)
        user_id = payload.get('user_id')
        
        if not user_id:
            return None
        
        session = get_db_session()
        user = session.query(User).filter_by(id=user_id, is_active=True).first()
        session.close()
        
        return user
    except (ValueError, IndexError, Exception):
        return None


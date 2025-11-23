"""
Utility functions for authentication and user management.
"""
from sqlalchemy.orm import sessionmaker
from scraper.schema import init_db
from models.user import User, UserRole
import os
from dotenv import load_dotenv

load_dotenv()

def get_db_session():
    """Get database session."""
    db_path = os.getenv('DATABASE_PATH', 'social_media.db')
    engine = init_db(db_path)
    Session = sessionmaker(bind=engine)
    return Session()

def create_default_admin(username: str = 'admin', email: str = 'admin@example.com', password: str = 'Admin123!@#'):
    """
    Create a default admin user if no users exist.
    This is useful for initial setup.
    
    Args:
        username: Admin username (default: 'admin')
        email: Admin email (default: 'admin@example.com')
        password: Admin password (default: 'Admin123!@#')
    
    Returns:
        User object if created, None if user already exists
    """
    session = get_db_session()
    try:
        # Check if any users exist
        user_count = session.query(User).count()
        
        if user_count > 0:
            # Users already exist, don't create default admin
            return None
        
        # Create default admin user
        admin = User(
            username=username,
            email=email,
            role=UserRole.ADMIN.value,
            is_active=True
        )
        admin.set_password(password)
        
        session.add(admin)
        session.commit()
        
        print(f"Default admin user created:")
        print(f"  Username: {username}")
        print(f"  Email: {email}")
        print(f"  Password: {password}")
        print("  ⚠️  IMPORTANT: Change the default password immediately!")
        
        return admin
    except Exception as e:
        session.rollback()
        print(f"Error creating default admin: {e}")
        return None
    finally:
        session.close()

def ensure_admin_exists():
    """
    Ensure at least one admin user exists.
    Creates default admin if no admin users exist.
    """
    session = get_db_session()
    try:
        admin_count = session.query(User).filter_by(role=UserRole.ADMIN.value, is_active=True).count()
        
        if admin_count == 0:
            # No active admins, create default
            return create_default_admin()
        
        return None
    finally:
        session.close()


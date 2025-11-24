"""
Database validation utilities to prevent configuration errors.
"""
import logging
import re
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


def validate_database_path(db_path: str) -> Tuple[bool, Optional[str], str]:
    """
    Validate and normalize database path before use.
    
    Args:
        db_path: Database path or connection string
        
    Returns:
        Tuple of (is_valid, error_message, normalized_path)
        - is_valid: True if path is valid
        - error_message: Error message if invalid, None if valid
        - normalized_path: Normalized path (SQLite URL format)
    """
    if not db_path:
        return False, "Database path cannot be empty", None
    
    if not isinstance(db_path, str):
        return False, f"Database path must be a string, got {type(db_path).__name__}", None
    
    db_path = db_path.strip()
    if not db_path:
        return False, "Database path cannot be empty after stripping whitespace", None
    
    # Detect database type
    db_path_lower = db_path.lower()
    has_url_scheme = '://' in db_path
    
    is_sqlite = (
        db_path.startswith('sqlite://') or
        db_path.endswith('.db') or
        (not has_url_scheme and 
         not db_path.startswith('postgresql') and 
         not db_path.startswith('mysql'))
    )
    
    is_production_db = (
        db_path.startswith('postgresql://') or
        db_path.startswith('postgresql+') or
        db_path.startswith('mysql://') or
        db_path.startswith('mysql+')
    )
    
    if is_sqlite:
        # Normalize SQLite path
        if db_path.startswith('sqlite:///'):
            normalized = db_path
        elif db_path.startswith('sqlite://'):
            normalized = db_path.replace('sqlite://', 'sqlite:///', 1)
        else:
            normalized = f'sqlite:///{db_path}'
        return True, None, normalized
    elif is_production_db:
        # Validate production database URL format
        if not re.match(r'^(postgresql|mysql)(\+[\w]+)?://', db_path):
            return False, f"Invalid production database URL format: {db_path}", None
        return True, None, db_path
    else:
        return False, (
            f"Unrecognized database path format: {db_path!r}. "
            "Supported formats: 'social_media.db', 'sqlite:///path/to.db', "
            "'postgresql://user:pass@host:port/db', or 'mysql://user:pass@host:port/db'"
        ), None


def test_database_connection(engine) -> Tuple[bool, Optional[str]]:
    """
    Test database connection to catch errors early.
    
    Args:
        engine: SQLAlchemy engine
        
    Returns:
        Tuple of (is_connected, error_message)
    """
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return True, None
    except Exception as e:
        error_msg = f"Database connection test failed: {e}"
        logger.error(error_msg)
        return False, error_msg


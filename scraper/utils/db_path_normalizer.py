"""
Database path normalization and validation utilities.
This module provides preemptive validation to prevent database initialization errors.
"""
import os
import sys
from typing import Tuple, Optional


def normalize_db_path(db_path: str) -> Tuple[str, str, bool]:
    """
    Normalize and validate database path before passing to init_db.
    
    This function provides preemptive validation to catch errors early.
    
    Args:
        db_path: Raw database path from user/environment
        
    Returns:
        Tuple of (normalized_path, sqlite_url, is_sqlite)
        - normalized_path: Normalized path for file operations
        - sqlite_url: Full SQLite URL if SQLite, None otherwise
        - is_sqlite: True if this is a SQLite database
        
    Raises:
        ValueError: If path is invalid
    """
    if not db_path:
        raise ValueError("Database path cannot be empty")
    
    if not isinstance(db_path, str):
        raise ValueError(f"Database path must be a string, got {type(db_path).__name__}")
    
    db_path = db_path.strip()
    if not db_path:
        raise ValueError("Database path cannot be empty after stripping")
    
    # CRITICAL: Check for .db extension FIRST - this is the most reliable indicator
    db_path_lower = db_path.lower()
    has_db_extension = db_path_lower.endswith('.db')
    contains_db = '.db' in db_path_lower
    
    # SQLite detection - be extremely explicit
    is_sqlite = False
    sqlite_url = None
    
    # Priority 1: Explicit SQLite URL
    if db_path.startswith('sqlite:///'):
        is_sqlite = True
        sqlite_url = db_path
        normalized_path = db_path.replace('sqlite:///', '')
    elif db_path.startswith('sqlite://'):
        is_sqlite = True
        sqlite_url = db_path.replace('sqlite://', 'sqlite:///', 1)
        normalized_path = db_path.replace('sqlite://', '')
    # Priority 2: .db extension (most common case)
    elif has_db_extension:
        is_sqlite = True
        # Convert to absolute path
        if os.path.isabs(db_path):
            abs_path = db_path
        else:
            abs_path = os.path.abspath(db_path)
        # Normalize path separators
        normalized_path = abs_path.replace('\\', '/')
        # Construct SQLite URL - ensure proper format
        sqlite_url = f'sqlite:///{normalized_path}'
    # Priority 3: Contains .db but not at end (edge case)
    elif contains_db and not db_path.startswith(('postgresql://', 'postgresql+', 'mysql://', 'mysql+')):
        is_sqlite = True
        if os.path.isabs(db_path):
            abs_path = db_path
        else:
            abs_path = os.path.abspath(db_path)
        normalized_path = abs_path.replace('\\', '/')
        sqlite_url = f'sqlite:///{normalized_path}'
    # Priority 4: No URL scheme and not a production DB
    elif '://' not in db_path and not db_path.startswith(('postgresql', 'mysql')):
        # Default to SQLite for simple filenames
        is_sqlite = True
        if os.path.isabs(db_path):
            abs_path = db_path
        else:
            abs_path = os.path.abspath(db_path)
        normalized_path = abs_path.replace('\\', '/')
        sqlite_url = f'sqlite:///{normalized_path}'
    else:
        # Production database - return as-is
        is_sqlite = False
        sqlite_url = None
        normalized_path = db_path
    
    # Validate SQLite URL format if we created one
    if is_sqlite and sqlite_url:
        if not sqlite_url.startswith('sqlite:///'):
            raise ValueError(
                f"Invalid SQLite URL constructed: '{sqlite_url}' from path: '{db_path}'. "
                "This should never happen - please report this bug."
            )
    
    return normalized_path, sqlite_url, is_sqlite


def validate_sqlite_url(url: str) -> bool:
    """
    Validate that a URL is a properly formatted SQLite URL.
    
    Args:
        url: URL to validate
        
    Returns:
        True if valid SQLite URL, False otherwise
    """
    if not url:
        return False
    if not isinstance(url, str):
        return False
    return url.startswith('sqlite:///')


def get_sqlite_url_from_path(db_path: str) -> str:
    """
    Convert a database path to a SQLite URL.
    
    This is a helper function that ensures correct URL format.
    
    Args:
        db_path: Database file path
        
    Returns:
        Properly formatted SQLite URL
        
    Raises:
        ValueError: If path cannot be converted to SQLite URL
    """
    _, sqlite_url, is_sqlite = normalize_db_path(db_path)
    
    if not is_sqlite:
        raise ValueError(f"Path '{db_path}' is not a SQLite database path")
    
    if not sqlite_url:
        raise ValueError(f"Failed to construct SQLite URL from path: '{db_path}'")
    
    return sqlite_url


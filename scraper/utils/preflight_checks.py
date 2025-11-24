"""
Pre-flight validation checks before running the scraper.
Anticipates and prevents common errors before they occur.
"""

import os
import sys
import importlib
import logging
from typing import Dict, List, Tuple, Optional
from sqlalchemy.orm import sessionmaker
from sqlalchemy import inspect

logger = logging.getLogger(__name__)


class PreflightCheckError(Exception):
    """Raised when a pre-flight check fails."""
    pass


def check_database_exists(db_path: str) -> Tuple[bool, Optional[str]]:
    """
    Check if database file exists and is accessible.
    
    Returns:
        (success, error_message)
    """
    try:
        # Check if it's a SQLite database
        if db_path.startswith('sqlite:///'):
            db_path = db_path.replace('sqlite:///', '')
        elif db_path.startswith('sqlite:'):
            db_path = db_path.replace('sqlite:', '')
        
        # Check if it's not a connection string (PostgreSQL, MySQL, etc.)
        if not db_path.startswith(('postgresql://', 'mysql://', 'mssql://')):
            # SQLite - check file permissions
            db_dir = os.path.dirname(db_path) if os.path.dirname(db_path) else '.'
            
            # Check if directory exists and is writable
            if db_dir and not os.path.exists(db_dir):
                return False, f"Database directory does not exist: {db_dir}"
            
            if db_dir and not os.access(db_dir, os.W_OK):
                return False, f"Database directory is not writable: {db_dir}"
            
            # If database exists, check if it's readable
            if os.path.exists(db_path):
                if not os.access(db_path, os.R_OK):
                    return False, f"Database file exists but is not readable: {db_path}"
                if not os.access(db_path, os.W_OK):
                    return False, f"Database file exists but is not writable: {db_path}"
        
        return True, None
    except Exception as e:
        return False, f"Error checking database: {str(e)}"


def check_database_schema(db_path: str) -> Tuple[bool, Optional[str]]:
    """
    Check if database schema is initialized.
    
    Returns:
        (success, error_message)
    """
    try:
        from scraper.schema import init_db, DimAccount, FactFollowersSnapshot, Base
        from models.job import Job  # Ensure Job model is registered
        
        engine = init_db(db_path)
        inspector = inspect(engine)
        
        # Check required tables exist
        required_tables = ['dim_account', 'fact_followers_snapshot', 'fact_social_post']
        
        if hasattr(inspector, 'get_table_names'):
            existing_tables = inspector.get_table_names()
        else:
            # SQLite fallback
            existing_tables = [t[0] for t in engine.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        
        missing_tables = [t for t in required_tables if t not in existing_tables]
        
        if missing_tables:
            return False, f"Database schema not initialized. Missing tables: {', '.join(missing_tables)}. Run 'python scraper/main.py --init-db' first."
        
        # Try to create a session and verify we can query
        Session = sessionmaker(bind=engine)
        session = Session()
        try:
            # This will fail if tables don't have proper structure
            session.query(DimAccount).limit(1).all()
        except Exception as e:
            return False, f"Database schema appears corrupted: {str(e)}"
        finally:
            session.close()
            engine.dispose()
        
        return True, None
    except ImportError as e:
        return False, f"Missing required module: {str(e)}. Install dependencies with 'pip install -r requirements.txt'"
    except Exception as e:
        return False, f"Error checking database schema: {str(e)}"


def check_accounts_exist(db_path: str) -> Tuple[bool, Optional[str], int]:
    """
    Check if there are accounts to scrape.
    
    Returns:
        (success, error_message, account_count)
    """
    try:
        from scraper.schema import init_db, DimAccount
        
        engine = init_db(db_path)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            # Check for active accounts
            active_accounts = session.query(DimAccount).filter(
                (DimAccount.is_active == True) | (DimAccount.is_active.is_(None))
            ).count()
            
            total_accounts = session.query(DimAccount).count()
            
            if total_accounts == 0:
                return False, "No accounts found in database. Please add accounts first using the bulk upload feature or populate from hhs_accounts.json.", 0
            
            if active_accounts == 0:
                return False, f"Found {total_accounts} accounts but none are active. Please activate accounts in the database or check is_active flags.", 0
            
            return True, None, active_accounts
        finally:
            session.close()
            engine.dispose()
    except Exception as e:
        return False, f"Error checking accounts: {str(e)}", 0


def check_required_modules() -> Tuple[bool, List[str]]:
    """
    Check if required Python modules are installed.
    
    Returns:
        (success, missing_modules)
    """
    required_modules = [
        'sqlalchemy',
        'requests',
        'beautifulsoup4',
        'lxml',
    ]
    
    # Optional modules (scraper will work without these, but with limited functionality)
    optional_modules = [
        'selenium',
        'undetected_chromedriver',
        'playwright',
    ]
    
    missing_required = []
    
    for module in required_modules:
        try:
            # Handle modules with different import names
            import_name = {
                'beautifulsoup4': 'bs4',
                'lxml': 'lxml',
            }.get(module, module)
            
            importlib.import_module(import_name)
        except ImportError:
            missing_required.append(module)
    
    return len(missing_required) == 0, missing_required


def check_scraper_imports() -> Tuple[bool, Optional[str]]:
    """
    Check if scraper modules can be imported.
    
    Returns:
        (success, error_message)
    """
    try:
        from scraper.scrapers import get_scraper
        from scraper.platforms import (
            XScraper,
            InstagramScraper,
            FacebookScraper,
            LinkedInScraper,
            YouTubeScraper,
        )
        return True, None
    except ImportError as e:
        return False, f"Error importing scraper modules: {str(e)}. Check that all scraper files are present."
    except Exception as e:
        return False, f"Error checking scraper imports: {str(e)}"


def check_file_permissions() -> Tuple[bool, Optional[str]]:
    """
    Check file system permissions for logs and temp files.
    
    Returns:
        (success, error_message)
    """
    try:
        # Check if we can write to current directory
        test_file = '.preflight_test'
        try:
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
        except Exception as e:
            return False, f"Cannot write to current directory: {str(e)}. Check file permissions."
        
        # Check logs directory
        logs_dir = 'logs'
        if os.path.exists(logs_dir):
            if not os.access(logs_dir, os.W_OK):
                return False, f"Logs directory exists but is not writable: {logs_dir}"
        
        return True, None
    except Exception as e:
        return False, f"Error checking file permissions: {str(e)}"


def check_network_connectivity() -> Tuple[bool, Optional[str]]:
    """
    Check basic network connectivity (optional check).
    
    Returns:
        (success, error_message)
    """
    try:
        import socket
        import requests
        
        # Try to resolve a common domain
        socket.gethostbyname('google.com')
        
        # Try a simple HTTP request
        try:
            response = requests.get('https://www.google.com', timeout=5)
            if response.status_code != 200:
                return False, "Network connectivity check failed: Cannot reach internet"
        except requests.RequestException:
            # Network might be down, but this is not critical
            logger.warning("Network connectivity check failed, but continuing anyway")
            return True, None
        
        return True, None
    except socket.gaierror:
        return False, "DNS resolution failed. Check your internet connection."
    except ImportError:
        # requests not installed - skip network check
        return True, None
    except Exception as e:
        # Don't fail on network issues - they might be temporary
        logger.warning(f"Network check warning: {str(e)}")
        return True, None


def run_preflight_checks(db_path: str = 'social_media.db', include_network: bool = False) -> Dict:
    """
    Run all pre-flight checks before starting the scraper.
    
    Args:
        db_path: Path to database file
        include_network: Whether to include network connectivity check
    
    Returns:
        Dictionary with check results:
        {
            'all_passed': bool,
            'checks': [
                {'name': str, 'passed': bool, 'message': str},
                ...
            ],
            'account_count': int,
            'errors': [str],
            'warnings': [str]
        }
    """
    results = {
        'all_passed': True,
        'checks': [],
        'account_count': 0,
        'errors': [],
        'warnings': []
    }
    
    # Check 1: Database exists
    passed, error = check_database_exists(db_path)
    results['checks'].append({
        'name': 'Database File',
        'passed': passed,
        'message': error or 'Database file exists and is accessible'
    })
    if not passed:
        results['all_passed'] = False
        results['errors'].append(f"Database check failed: {error}")
    else:
        logger.info("✓ Database file check passed")
    
    # Check 2: Database schema
    passed, error = check_database_schema(db_path)
    results['checks'].append({
        'name': 'Database Schema',
        'passed': passed,
        'message': error or 'Database schema is initialized'
    })
    if not passed:
        results['all_passed'] = False
        results['errors'].append(f"Schema check failed: {error}")
    else:
        logger.info("✓ Database schema check passed")
    
    # Check 3: Accounts exist
    passed, error, count = check_accounts_exist(db_path)
    results['account_count'] = count
    results['checks'].append({
        'name': 'Accounts Available',
        'passed': passed,
        'message': error or f'Found {count} active account(s) to scrape'
    })
    if not passed:
        results['all_passed'] = False
        results['errors'].append(f"Accounts check failed: {error}")
    else:
        logger.info(f"✓ Accounts check passed: {count} accounts available")
    
    # Check 4: Required modules
    passed, missing = check_required_modules()
    results['checks'].append({
        'name': 'Required Modules',
        'passed': passed,
        'message': f"Missing modules: {', '.join(missing)}" if missing else 'All required modules installed'
    })
    if not passed:
        results['all_passed'] = False
        results['errors'].append(f"Missing required modules: {', '.join(missing)}. Install with: pip install {' '.join(missing)}")
    else:
        logger.info("✓ Required modules check passed")
    
    # Check 5: Scraper imports
    passed, error = check_scraper_imports()
    results['checks'].append({
        'name': 'Scraper Modules',
        'passed': passed,
        'message': error or 'Scraper modules can be imported'
    })
    if not passed:
        results['all_passed'] = False
        results['errors'].append(f"Scraper import check failed: {error}")
    else:
        logger.info("✓ Scraper modules check passed")
    
    # Check 6: File permissions
    passed, error = check_file_permissions()
    results['checks'].append({
        'name': 'File Permissions',
        'passed': passed,
        'message': error or 'File system permissions OK'
    })
    if not passed:
        results['all_passed'] = False
        results['errors'].append(f"Permissions check failed: {error}")
    else:
        logger.info("✓ File permissions check passed")
    
    # Check 7: Network connectivity (optional)
    if include_network:
        passed, error = check_network_connectivity()
        results['checks'].append({
            'name': 'Network Connectivity',
            'passed': passed,
            'message': error or 'Network connectivity OK'
        })
        if not passed:
            results['warnings'].append(f"Network check failed: {error}")
            # Don't fail on network issues
        else:
            logger.info("✓ Network connectivity check passed")
    
    return results


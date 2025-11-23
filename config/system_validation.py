"""
Comprehensive system validation module for startup and runtime checks.
Validates all system components, dependencies, and configurations.
"""
import os
import sys
import logging
import importlib
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    CRITICAL = "critical"  # System cannot start
    ERROR = "error"       # System may not function correctly
    WARNING = "warning"   # System may have degraded functionality
    INFO = "info"         # Informational only


@dataclass
class ValidationResult:
    """Result of a validation check."""
    name: str
    severity: ValidationSeverity
    status: bool  # True if passed, False if failed
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    fix_suggestion: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'name': self.name,
            'severity': self.severity.value,
            'status': self.status,
            'message': self.message,
            'details': self.details,
            'fix_suggestion': self.fix_suggestion,
            'timestamp': self.timestamp.isoformat()
        }


class SystemValidator:
    """Comprehensive system validator."""
    
    def __init__(self):
        self.results: List[ValidationResult] = []
        self.critical_failures: List[ValidationResult] = []
        self.errors: List[ValidationResult] = []
        self.warnings: List[ValidationResult] = []
    
    def validate_all(self, skip_optional: bool = False) -> Tuple[bool, List[ValidationResult]]:
        """
        Run all validation checks.
        
        Args:
            skip_optional: Skip optional checks (Redis, Celery, etc.)
        
        Returns:
            Tuple of (all_passed, results)
        """
        self.results = []
        self.critical_failures = []
        self.errors = []
        self.warnings = []
        
        logger.info("Starting comprehensive system validation...")
        
        # Core validations (always required)
        self._validate_environment()
        self._validate_python_version()
        self._validate_dependencies()
        self._validate_database()
        self._validate_configuration()
        self._validate_file_permissions()
        self._validate_ports()
        
        # Optional validations
        if not skip_optional:
            self._validate_redis()
            self._validate_celery()
            self._validate_external_services()
        
        # Categorize results
        for result in self.results:
            if result.severity == ValidationSeverity.CRITICAL and not result.status:
                self.critical_failures.append(result)
            elif result.severity == ValidationSeverity.ERROR and not result.status:
                self.errors.append(result)
            elif result.severity == ValidationSeverity.WARNING and not result.status:
                self.warnings.append(result)
        
        all_passed = len(self.critical_failures) == 0 and len(self.errors) == 0
        
        logger.info(f"Validation complete: {len(self.results)} checks, "
                   f"{len(self.critical_failures)} critical failures, "
                   f"{len(self.errors)} errors, {len(self.warnings)} warnings")
        
        return all_passed, self.results
    
    def _validate_environment(self):
        """Validate environment variables."""
        logger.debug("Validating environment variables...")
        
        required_vars = [
            'SECRET_KEY',
            'JWT_SECRET_KEY',
        ]
        
        missing = []
        for var in required_vars:
            if not os.getenv(var):
                missing.append(var)
        
        if missing:
            self.results.append(ValidationResult(
                name="environment_variables",
                severity=ValidationSeverity.CRITICAL,
                status=False,
                message=f"Missing required environment variables: {', '.join(missing)}",
                details={'missing_vars': missing},
                fix_suggestion=f"Set the following environment variables: {', '.join(missing)}"
            ))
        else:
            self.results.append(ValidationResult(
                name="environment_variables",
                severity=ValidationSeverity.INFO,
                status=True,
                message="All required environment variables are set",
                details={'checked_vars': required_vars}
            ))
        
        # Check for default/weak secrets
        secret_key = os.getenv('SECRET_KEY', '')
        jwt_secret = os.getenv('JWT_SECRET_KEY', '')
        
        weak_secrets = []
        if secret_key in ['your-secret-key-change-in-production', '']:
            weak_secrets.append('SECRET_KEY')
        if jwt_secret in ['your-jwt-secret-key-change-in-production', '']:
            weak_secrets.append('JWT_SECRET_KEY')
        
        if weak_secrets:
            self.results.append(ValidationResult(
                name="weak_secrets",
                severity=ValidationSeverity.CRITICAL,
                status=False,
                message=f"Using default/weak secrets: {', '.join(weak_secrets)}",
                details={'weak_secrets': weak_secrets},
                fix_suggestion="Generate strong, unique secrets for production"
            ))
    
    def _validate_python_version(self):
        """Validate Python version."""
        logger.debug("Validating Python version...")
        
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            self.results.append(ValidationResult(
                name="python_version",
                severity=ValidationSeverity.CRITICAL,
                status=False,
                message=f"Python {version.major}.{version.minor} is not supported. Requires Python 3.8+",
                details={'current_version': f"{version.major}.{version.minor}.{version.micro}"},
                fix_suggestion="Upgrade to Python 3.8 or higher"
            ))
        else:
            self.results.append(ValidationResult(
                name="python_version",
                severity=ValidationSeverity.INFO,
                status=True,
                message=f"Python version {version.major}.{version.minor}.{version.micro} is supported",
                details={'version': f"{version.major}.{version.minor}.{version.micro}"}
            ))
    
    def _validate_dependencies(self):
        """Validate required Python packages."""
        logger.debug("Validating dependencies...")
        
        required_packages = [
            'flask',
            'sqlalchemy',
            'pandas',
            'flask_limiter',
            'flask_cors',
            'flask_compress',
        ]
        
        missing = []
        for package in required_packages:
            try:
                importlib.import_module(package.replace('-', '_'))
            except ImportError:
                missing.append(package)
        
        if missing:
            self.results.append(ValidationResult(
                name="dependencies",
                severity=ValidationSeverity.CRITICAL,
                status=False,
                message=f"Missing required packages: {', '.join(missing)}",
                details={'missing_packages': missing},
                fix_suggestion=f"Install missing packages: pip install {' '.join(missing)}"
            ))
        else:
            self.results.append(ValidationResult(
                name="dependencies",
                severity=ValidationSeverity.INFO,
                status=True,
                message="All required packages are installed",
                details={'checked_packages': required_packages}
            ))
    
    def _validate_database(self):
        """Validate database connectivity and schema."""
        logger.debug("Validating database...")
        
        try:
            from scraper.schema import init_db
            from sqlalchemy import text, inspect
            
            db_path = os.getenv('DATABASE_PATH', 'social_media.db')
            
            # Check if database file exists or can be created
            db_dir = os.path.dirname(os.path.abspath(db_path)) or '.'
            if not os.path.exists(db_dir):
                try:
                    os.makedirs(db_dir, exist_ok=True)
                except Exception as e:
                    self.results.append(ValidationResult(
                        name="database_directory",
                        severity=ValidationSeverity.CRITICAL,
                        status=False,
                        message=f"Cannot create database directory: {str(e)}",
                        details={'db_path': db_path, 'error': str(e)},
                        fix_suggestion=f"Ensure directory {db_dir} is writable or set DATABASE_PATH to a writable location"
                    ))
                    return
            
            # Try to connect
            try:
                engine = init_db(db_path)
                with engine.connect() as conn:
                    result = conn.execute(text("SELECT 1"))
                    result.fetchone()
                
                # Check for required tables
                inspector = inspect(engine)
                tables = inspector.get_table_names()
                required_tables = ['dim_account', 'fact_followers_snapshot']
                
                missing_tables = [t for t in required_tables if t not in tables]
                
                if missing_tables:
                    self.results.append(ValidationResult(
                        name="database_schema",
                        severity=ValidationSeverity.ERROR,
                        status=False,
                        message=f"Missing required tables: {', '.join(missing_tables)}",
                        details={'missing_tables': missing_tables, 'existing_tables': tables},
                        fix_suggestion="Run database migrations: alembic upgrade head"
                    ))
                else:
                    self.results.append(ValidationResult(
                        name="database",
                        severity=ValidationSeverity.INFO,
                        status=True,
                        message="Database connection and schema are valid",
                        details={'db_path': db_path, 'tables': tables}
                    ))
            except Exception as e:
                self.results.append(ValidationResult(
                    name="database_connection",
                    severity=ValidationSeverity.CRITICAL,
                    status=False,
                    message=f"Database connection failed: {str(e)}",
                    details={'db_path': db_path, 'error': str(e)},
                    fix_suggestion="Check database path and permissions, ensure SQLite is available"
                ))
        except ImportError as e:
            self.results.append(ValidationResult(
                name="database_import",
                severity=ValidationSeverity.CRITICAL,
                status=False,
                message=f"Cannot import database modules: {str(e)}",
                details={'error': str(e)},
                fix_suggestion="Ensure scraper.schema module is available"
            ))
    
    def _validate_configuration(self):
        """Validate application configuration."""
        logger.debug("Validating configuration...")
        
        try:
            from config.settings import config
            
            # Check critical config values
            issues = []
            
            # Check database path
            db_path = getattr(config, 'DATABASE_PATH', None) or os.getenv('DATABASE_PATH', 'social_media.db')
            if not os.path.exists(os.path.dirname(os.path.abspath(db_path))):
                issues.append("Database directory does not exist")
            
            # Check CORS origins
            cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:5000')
            if '*' in cors_origins and os.getenv('FLASK_ENV') == 'production':
                issues.append("CORS allows all origins in production")
            
            if issues:
                self.results.append(ValidationResult(
                    name="configuration",
                    severity=ValidationSeverity.WARNING,
                    status=False,
                    message=f"Configuration issues found: {', '.join(issues)}",
                    details={'issues': issues},
                    fix_suggestion="Review and fix configuration issues"
                ))
            else:
                self.results.append(ValidationResult(
                    name="configuration",
                    severity=ValidationSeverity.INFO,
                    status=True,
                    message="Configuration is valid",
                    details={}
                ))
        except Exception as e:
            self.results.append(ValidationResult(
                name="configuration",
                severity=ValidationSeverity.WARNING,
                status=False,
                message=f"Configuration validation failed: {str(e)}",
                details={'error': str(e)},
                fix_suggestion="Check configuration files and environment variables"
            ))
    
    def _validate_file_permissions(self):
        """Validate file and directory permissions."""
        logger.debug("Validating file permissions...")
        
        critical_paths = [
            os.getenv('DATABASE_PATH', 'social_media.db'),
            os.getenv('LOG_DIRECTORY', 'logs'),
        ]
        
        issues = []
        for path in critical_paths:
            if os.path.isfile(path):
                if not os.access(path, os.R_OK | os.W_OK):
                    issues.append(f"{path} is not readable/writable")
            elif os.path.isdir(path):
                if not os.access(path, os.R_OK | os.W_OK):
                    issues.append(f"{path} is not readable/writable")
            else:
                # Try to create directory if it doesn't exist
                try:
                    os.makedirs(path, exist_ok=True)
                except Exception as e:
                    issues.append(f"Cannot create {path}: {str(e)}")
        
        if issues:
            self.results.append(ValidationResult(
                name="file_permissions",
                severity=ValidationSeverity.ERROR,
                status=False,
                message=f"File permission issues: {', '.join(issues)}",
                details={'issues': issues},
                fix_suggestion="Fix file permissions or change paths to writable locations"
            ))
        else:
            self.results.append(ValidationResult(
                name="file_permissions",
                severity=ValidationSeverity.INFO,
                status=True,
                message="File permissions are valid",
                details={}
            ))
    
    def _validate_ports(self):
        """Validate that required ports are available."""
        logger.debug("Validating ports...")
        
        import socket
        
        port = int(os.getenv('PORT', 5000))
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        
        if result == 0:
            # Port is in use - check if it's our app
            self.results.append(ValidationResult(
                name="port_availability",
                severity=ValidationSeverity.WARNING,
                status=False,
                message=f"Port {port} is already in use",
                details={'port': port},
                fix_suggestion=f"Change PORT environment variable or stop the service using port {port}"
            ))
        else:
            self.results.append(ValidationResult(
                name="port_availability",
                severity=ValidationSeverity.INFO,
                status=True,
                message=f"Port {port} is available",
                details={'port': port}
            ))
    
    def _validate_redis(self):
        """Validate Redis connectivity (optional)."""
        logger.debug("Validating Redis...")
        
        try:
            from cache.redis_client import cache
            
            # Try to set and get a test value
            test_key = 'validation_test'
            test_value = 'test'
            
            cache.set(test_key, test_value, timeout=5)
            retrieved = cache.get(test_key)
            cache.delete(test_key)
            
            if retrieved == test_value:
                self.results.append(ValidationResult(
                    name="redis",
                    severity=ValidationSeverity.INFO,
                    status=True,
                    message="Redis connection is working",
                    details={}
                ))
            else:
                self.results.append(ValidationResult(
                    name="redis",
                    severity=ValidationSeverity.WARNING,
                    status=False,
                    message="Redis read/write test failed",
                    details={},
                    fix_suggestion="Check Redis connection and configuration"
                ))
        except Exception as e:
            self.results.append(ValidationResult(
                name="redis",
                severity=ValidationSeverity.WARNING,
                status=False,
                message=f"Redis is not available: {str(e)}",
                details={'error': str(e)},
                fix_suggestion="Redis is optional but recommended for caching. Check Redis configuration."
            ))
    
    def _validate_celery(self):
        """Validate Celery workers (optional)."""
        logger.debug("Validating Celery...")
        
        try:
            from celery_app import celery_app
            
            inspect = celery_app.control.inspect()
            if inspect:
                active_workers = inspect.active()
                worker_count = len(active_workers) if active_workers else 0
                
                if worker_count > 0:
                    self.results.append(ValidationResult(
                        name="celery",
                        severity=ValidationSeverity.INFO,
                        status=True,
                        message=f"{worker_count} Celery worker(s) are active",
                        details={'worker_count': worker_count}
                    ))
                else:
                    self.results.append(ValidationResult(
                        name="celery",
                        severity=ValidationSeverity.WARNING,
                        status=False,
                        message="No active Celery workers",
                        details={},
                        fix_suggestion="Start Celery workers for background task processing"
                    ))
            else:
                self.results.append(ValidationResult(
                    name="celery",
                    severity=ValidationSeverity.WARNING,
                    status=False,
                    message="Cannot connect to Celery",
                    details={},
                    fix_suggestion="Ensure Celery broker is running and configured"
                ))
        except Exception as e:
            self.results.append(ValidationResult(
                name="celery",
                severity=ValidationSeverity.WARNING,
                status=False,
                message=f"Celery validation failed: {str(e)}",
                details={'error': str(e)},
                fix_suggestion="Celery is optional but recommended for background tasks"
            ))
    
    def _validate_external_services(self):
        """Validate external service connectivity (optional)."""
        logger.debug("Validating external services...")
        
        # Check Sentry if configured
        sentry_dsn = os.getenv('SENTRY_DSN')
        if sentry_dsn:
            try:
                import sentry_sdk
                self.results.append(ValidationResult(
                    name="sentry",
                    severity=ValidationSeverity.INFO,
                    status=True,
                    message="Sentry is configured",
                    details={}
                ))
            except ImportError:
                self.results.append(ValidationResult(
                    name="sentry",
                    severity=ValidationSeverity.WARNING,
                    status=False,
                    message="Sentry DSN configured but sentry_sdk not installed",
                    details={},
                    fix_suggestion="Install sentry-sdk: pip install sentry-sdk"
                ))
    
    def get_summary(self) -> Dict[str, Any]:
        """Get validation summary."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status)
        failed = total - passed
        
        return {
            'total': total,
            'passed': passed,
            'failed': failed,
            'critical_failures': len(self.critical_failures),
            'errors': len(self.errors),
            'warnings': len(self.warnings),
            'all_passed': len(self.critical_failures) == 0 and len(self.errors) == 0,
            'results': [r.to_dict() for r in self.results]
        }


def validate_system_on_startup(skip_optional: bool = False) -> bool:
    """
    Validate system on startup. Raises SystemExit if critical failures.
    
    Args:
        skip_optional: Skip optional checks
    
    Returns:
        True if all critical checks passed
    """
    validator = SystemValidator()
    all_passed, results = validator.validate_all(skip_optional=skip_optional)
    
    if not all_passed:
        logger.error("System validation failed!")
        for result in validator.critical_failures + validator.errors:
            logger.error(f"  {result.name}: {result.message}")
            if result.fix_suggestion:
                logger.error(f"    Fix: {result.fix_suggestion}")
        
        # Don't exit in production - log and continue
        if os.getenv('FLASK_ENV') != 'production':
            logger.warning("Continuing despite validation failures (non-production mode)")
        else:
            logger.error("Critical validation failures in production mode")
    
    return all_passed


if __name__ == '__main__':
    # Run validation when executed directly
    logging.basicConfig(level=logging.INFO)
    validator = SystemValidator()
    all_passed, results = validator.validate_all()
    
    print("\n=== System Validation Results ===\n")
    summary = validator.get_summary()
    print(f"Total checks: {summary['total']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Critical failures: {summary['critical_failures']}")
    print(f"Errors: {summary['errors']}")
    print(f"Warnings: {summary['warnings']}\n")
    
    for result in results:
        status = "✓" if result.status else "✗"
        severity = result.severity.value.upper()
        print(f"{status} [{severity}] {result.name}: {result.message}")
        if not result.status and result.fix_suggestion:
            print(f"    → {result.fix_suggestion}")
    
    sys.exit(0 if all_passed else 1)


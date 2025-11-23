"""
Enhanced error detection and reporting system.
Provides easy error pinpointing, categorization, and fix suggestions.
"""
import os
import sys
import logging
import traceback
import inspect
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Error categories for classification."""
    DATABASE = "database"
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    CONFIGURATION = "configuration"
    SCRAPER = "scraper"
    TASK_QUEUE = "task_queue"
    CACHE = "cache"
    API = "api"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    """Error severity levels."""
    CRITICAL = "critical"  # System cannot function
    HIGH = "high"         # Major functionality broken
    MEDIUM = "medium"     # Degraded functionality
    LOW = "low"          # Minor issue
    INFO = "info"        # Informational


@dataclass
class ErrorContext:
    """Context information for an error."""
    timestamp: datetime
    error_type: str
    error_message: str
    category: ErrorCategory
    severity: ErrorSeverity
    stack_trace: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    function_name: Optional[str] = None
    module_name: Optional[str] = None
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    account_key: Optional[str] = None
    platform: Optional[str] = None
    environment: Optional[str] = None
    additional_context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'error_type': self.error_type,
            'error_message': self.error_message,
            'category': self.category.value,
            'severity': self.severity.value,
            'stack_trace': self.stack_trace,
            'file_path': self.file_path,
            'line_number': self.line_number,
            'function_name': self.function_name,
            'module_name': self.module_name,
            'request_id': self.request_id,
            'user_id': self.user_id,
            'account_key': self.account_key,
            'platform': self.platform,
            'environment': self.environment,
            'additional_context': self.additional_context
        }


@dataclass
class ErrorFix:
    """Suggested fix for an error."""
    description: str
    steps: List[str]
    code_example: Optional[str] = None
    documentation_link: Optional[str] = None
    related_errors: List[str] = field(default_factory=list)
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'description': self.description,
            'steps': self.steps,
            'code_example': self.code_example,
            'documentation_link': self.documentation_link,
            'related_errors': self.related_errors
        }


class ErrorDetector:
    """Enhanced error detection and analysis system."""
    
    def __init__(self):
        self.error_history: List[ErrorContext] = []
        self.error_patterns: Dict[str, List[ErrorContext]] = defaultdict(list)
        self.fix_suggestions: Dict[str, ErrorFix] = {}
        self._load_fix_suggestions()
    
    def detect_error(self, exception: Exception, context: Optional[Dict[str, Any]] = None) -> ErrorContext:
        """
        Detect and analyze an error.
        
        Args:
            exception: The exception that occurred
            context: Additional context information
        
        Returns:
            ErrorContext with full error information
        """
        context = context or {}
        
        # Extract stack trace
        exc_type, exc_value, exc_traceback = sys.exc_info()
        stack_trace = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        
        # Extract file and line information
        tb = exc_traceback
        file_path = None
        line_number = None
        function_name = None
        module_name = None
        
        if tb:
            frame = tb.tb_frame
            while frame:
                if frame.f_code.co_filename != __file__:
                    file_path = frame.f_code.co_filename
                    line_number = tb.tb_lineno
                    function_name = frame.f_code.co_name
                    module_name = frame.f_globals.get('__name__', '')
                    break
                tb = tb.tb_next
                if tb:
                    frame = tb.tb_frame
        
        # Classify error
        category, severity = self._classify_error(exception, stack_trace)
        
        # Create error context
        error_context = ErrorContext(
            timestamp=datetime.utcnow(),
            error_type=type(exception).__name__,
            error_message=str(exception),
            category=category,
            severity=severity,
            stack_trace=stack_trace,
            file_path=file_path,
            line_number=line_number,
            function_name=function_name,
            module_name=module_name,
            request_id=context.get('request_id'),
            user_id=context.get('user_id'),
            account_key=context.get('account_key'),
            platform=context.get('platform'),
            environment=os.getenv('FLASK_ENV', 'development'),
            additional_context=context
        )
        
        # Store in history
        self.error_history.append(error_context)
        
        # Track patterns
        pattern_key = self._get_pattern_key(error_context)
        self.error_patterns[pattern_key].append(error_context)
        
        return error_context
    
    def _classify_error(self, exception: Exception, stack_trace: str) -> Tuple[ErrorCategory, ErrorSeverity]:
        """Classify error by category and severity."""
        error_str = str(exception).lower()
        error_type = type(exception).__name__
        stack_lower = stack_trace.lower()
        
        # Database errors
        if any(keyword in error_str or keyword in stack_lower 
               for keyword in ['sql', 'database', 'db', 'sqlite', 'connection', 'table', 'column']):
            if 'connection' in error_str or 'cannot connect' in error_str:
                return ErrorCategory.DATABASE, ErrorSeverity.CRITICAL
            elif 'table' in error_str or 'column' in error_str or 'schema' in error_str:
                return ErrorCategory.DATABASE, ErrorSeverity.HIGH
            else:
                return ErrorCategory.DATABASE, ErrorSeverity.MEDIUM
        
        # Network errors
        if any(keyword in error_str or keyword in stack_lower 
               for keyword in ['connection', 'timeout', 'network', 'dns', 'refused', 'unreachable']):
            if 'timeout' in error_str:
                return ErrorCategory.NETWORK, ErrorSeverity.MEDIUM
            else:
                return ErrorCategory.NETWORK, ErrorSeverity.HIGH
        
        # Authentication errors
        if any(keyword in error_str 
               for keyword in ['unauthorized', 'authentication', 'login', 'token', 'jwt', 'invalid credentials']):
            return ErrorCategory.AUTHENTICATION, ErrorSeverity.HIGH
        
        # Authorization errors
        if any(keyword in error_str 
               for keyword in ['forbidden', 'permission', 'access denied', 'insufficient']):
            return ErrorCategory.AUTHORIZATION, ErrorSeverity.MEDIUM
        
        # Validation errors
        if any(keyword in error_str or keyword in error_type.lower()
               for keyword in ['validation', 'invalid', 'malformed', 'bad request']):
            return ErrorCategory.VALIDATION, ErrorSeverity.LOW
        
        # Configuration errors
        if any(keyword in error_str or keyword in stack_lower
               for keyword in ['config', 'environment', 'missing', 'not set', 'undefined']):
            return ErrorCategory.CONFIGURATION, ErrorSeverity.HIGH
        
        # Scraper errors
        if any(keyword in error_str or keyword in stack_lower
               for keyword in ['scraper', 'scrape', 'rate limit', '429', 'blocked']):
            if 'rate limit' in error_str or '429' in error_str:
                return ErrorCategory.SCRAPER, ErrorSeverity.MEDIUM
            else:
                return ErrorCategory.SCRAPER, ErrorSeverity.HIGH
        
        # Task queue errors
        if any(keyword in error_str or keyword in stack_lower
               for keyword in ['celery', 'task', 'queue', 'worker', 'broker']):
            return ErrorCategory.TASK_QUEUE, ErrorSeverity.HIGH
        
        # Cache errors
        if any(keyword in error_str or keyword in stack_lower
               for keyword in ['redis', 'cache', 'memcached']):
            return ErrorCategory.CACHE, ErrorSeverity.MEDIUM
        
        # API errors
        if any(keyword in error_str or keyword in error_type.lower()
               for keyword in ['api', 'endpoint', 'route', 'http', 'request']):
            return ErrorCategory.API, ErrorSeverity.MEDIUM
        
        # System errors
        if any(keyword in error_str or keyword in error_type.lower()
               for keyword in ['memory', 'disk', 'os', 'system', 'resource']):
            return ErrorCategory.SYSTEM, ErrorSeverity.CRITICAL
        
        # Default
        return ErrorCategory.UNKNOWN, ErrorSeverity.MEDIUM
    
    def _get_pattern_key(self, error_context: ErrorContext) -> str:
        """Generate a pattern key for error grouping."""
        # Group by error type and file
        key_parts = [
            error_context.error_type,
            error_context.file_path or 'unknown',
            error_context.function_name or 'unknown'
        ]
        return '|'.join(key_parts)
    
    def get_fix_suggestion(self, error_context: ErrorContext) -> Optional[ErrorFix]:
        """Get fix suggestion for an error."""
        # Check predefined fixes
        error_key = f"{error_context.category.value}:{error_context.error_type}"
        if error_key in self.fix_suggestions:
            return self.fix_suggestions[error_key]
        
        # Generate dynamic fix based on error context
        return self._generate_fix(error_context)
    
    def _generate_fix(self, error_context: ErrorContext) -> Optional[ErrorFix]:
        """Generate a fix suggestion based on error context."""
        category = error_context.category
        error_message = error_context.error_message.lower()
        
        if category == ErrorCategory.DATABASE:
            if 'connection' in error_message:
                return ErrorFix(
                    description="Database connection error",
                    steps=[
                        "Check database file path and permissions",
                        "Ensure database file exists or can be created",
                        "Verify database is not locked by another process",
                        "Check DATABASE_PATH environment variable"
                    ],
                    code_example="DATABASE_PATH=/path/to/database.db",
                    documentation_link="/docs/database-setup"
                )
            elif 'table' in error_message or 'column' in error_message:
                return ErrorFix(
                    description="Database schema error",
                    steps=[
                        "Run database migrations: alembic upgrade head",
                        "Check if tables exist: SELECT name FROM sqlite_master WHERE type='table'",
                        "Verify schema matches expected structure"
                    ],
                    code_example="alembic upgrade head",
                    documentation_link="/docs/database-migrations"
                )
        
        elif category == ErrorCategory.NETWORK:
            if 'timeout' in error_message:
                return ErrorFix(
                    description="Network timeout error",
                    steps=[
                        "Check network connectivity",
                        "Increase timeout settings",
                        "Verify target service is running",
                        "Check firewall rules"
                    ],
                    code_example="requests.get(url, timeout=30)",
                    documentation_link="/docs/network-troubleshooting"
                )
            elif 'connection refused' in error_message:
                return ErrorFix(
                    description="Connection refused error",
                    steps=[
                        "Verify target service is running",
                        "Check service is listening on correct port",
                        "Verify firewall allows connections",
                        "Check service logs for errors"
                    ],
                    code_example="netstat -tuln | grep <port>",
                    documentation_link="/docs/network-troubleshooting"
                )
        
        elif category == ErrorCategory.CONFIGURATION:
            return ErrorFix(
                description="Configuration error",
                steps=[
                    "Check environment variables are set",
                    "Verify configuration file exists and is valid",
                    "Check for typos in variable names",
                    "Review configuration documentation"
                ],
                code_example="export SECRET_KEY='your-secret-key'",
                documentation_link="/docs/configuration"
            )
        
        elif category == ErrorCategory.SCRAPER:
            if 'rate limit' in error_message or '429' in error_message:
                return ErrorFix(
                    description="Rate limit exceeded",
                    steps=[
                        "Implement exponential backoff",
                        "Reduce scraping frequency",
                        "Use proxy rotation",
                        "Check platform rate limits"
                    ],
                    code_example="time.sleep(2 ** retry_count)",
                    documentation_link="/docs/scraper-optimization"
                )
        
        elif category == ErrorCategory.AUTHENTICATION:
            return ErrorFix(
                description="Authentication error",
                steps=[
                    "Verify credentials are correct",
                    "Check token expiration",
                    "Refresh authentication token",
                    "Review authentication configuration"
                ],
                code_example="token = refresh_auth_token()",
                documentation_link="/docs/authentication"
            )
        
        return None
    
    def get_error_summary(self, time_window: Optional[timedelta] = None) -> Dict[str, Any]:
        """Get error summary for a time window."""
        if time_window:
            cutoff = datetime.utcnow() - time_window
            recent_errors = [e for e in self.error_history if e.timestamp >= cutoff]
        else:
            recent_errors = self.error_history
        
        # Group by category
        by_category = defaultdict(int)
        by_severity = defaultdict(int)
        by_type = defaultdict(int)
        
        for error in recent_errors:
            by_category[error.category.value] += 1
            by_severity[error.severity.value] += 1
            by_type[error.error_type] += 1
        
        # Get most common errors
        most_common = sorted(by_type.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'total_errors': len(recent_errors),
            'by_category': dict(by_category),
            'by_severity': dict(by_severity),
            'by_type': dict(by_type),
            'most_common': [{'type': t, 'count': c} for t, c in most_common],
            'time_window': str(time_window) if time_window else 'all'
        }
    
    def get_similar_errors(self, error_context: ErrorContext, limit: int = 5) -> List[ErrorContext]:
        """Get similar errors from history."""
        pattern_key = self._get_pattern_key(error_context)
        similar = self.error_patterns.get(pattern_key, [])
        
        # Exclude the current error
        similar = [e for e in similar if e.timestamp != error_context.timestamp]
        
        return similar[:limit]
    
    def _load_fix_suggestions(self):
        """Load predefined fix suggestions."""
        # Database fixes
        self.fix_suggestions['database:OperationalError'] = ErrorFix(
            description="Database operational error",
            steps=[
                "Check database file permissions",
                "Verify database is not locked",
                "Check disk space availability",
                "Review database logs"
            ],
            documentation_link="/docs/database-troubleshooting"
        )
        
        # Network fixes
        self.fix_suggestions['network:ConnectionError'] = ErrorFix(
            description="Network connection error",
            steps=[
                "Check network connectivity",
                "Verify target service is running",
                "Check firewall and proxy settings",
                "Review network logs"
            ],
            documentation_link="/docs/network-troubleshooting"
        )
        
        # Add more predefined fixes as needed


# Global error detector instance
_error_detector = ErrorDetector()


def detect_error(exception: Exception, context: Optional[Dict[str, Any]] = None) -> ErrorContext:
    """
    Detect and analyze an error.
    
    Args:
        exception: The exception that occurred
        context: Additional context information
    
    Returns:
        ErrorContext with full error information
    """
    return _error_detector.detect_error(exception, context)


def get_error_summary(time_window: Optional[timedelta] = None) -> Dict[str, Any]:
    """Get error summary."""
    return _error_detector.get_error_summary(time_window)


def get_fix_suggestion(error_context: ErrorContext) -> Optional[ErrorFix]:
    """Get fix suggestion for an error."""
    return _error_detector.get_fix_suggestion(error_context)


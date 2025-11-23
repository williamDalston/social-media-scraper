"""
Intelligent retry strategies that adapt based on error types and context.
"""

import time
import logging
from typing import Callable, Type, Tuple, Optional, Dict, Any
from functools import wraps
from enum import Enum

from .errors import (
    ScraperError,
    RateLimitError,
    NetworkError,
    AccountNotFoundError,
    PrivateAccountError,
)

logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """Retry strategy types."""
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    FIXED = "fixed"
    ADAPTIVE = "adaptive"


class IntelligentRetry:
    """
    Intelligent retry mechanism that adapts based on error types and context.
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        strategy: RetryStrategy = RetryStrategy.ADAPTIVE,
    ):
        """
        Initialize intelligent retry.
        
        Args:
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            strategy: Retry strategy to use
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.strategy = strategy
        
        # Track retry history for adaptive strategy
        self._retry_history: Dict[str, list] = {}
    
    def _calculate_delay(
        self,
        attempt: int,
        error: Exception,
        retry_after: Optional[float] = None,
    ) -> float:
        """
        Calculate delay based on strategy and error type.
        
        Args:
            attempt: Current attempt number (0-indexed)
            error: The exception that occurred
            retry_after: Suggested retry time from platform (for rate limits)
            
        Returns:
            Delay in seconds
        """
        # Use retry_after if provided (rate limit)
        if retry_after:
            return min(retry_after, self.max_delay)
        
        # Calculate delay based on strategy
        if self.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.initial_delay * (2 ** attempt)
        elif self.strategy == RetryStrategy.LINEAR:
            delay = self.initial_delay * (attempt + 1)
        elif self.strategy == RetryStrategy.FIXED:
            delay = self.initial_delay
        else:  # ADAPTIVE
            # Adaptive: adjust based on error type
            if isinstance(error, RateLimitError):
                # Longer delay for rate limits
                delay = self.initial_delay * (3 ** attempt)
            elif isinstance(error, NetworkError):
                # Moderate delay for network errors
                delay = self.initial_delay * (2 ** attempt)
            else:
                # Standard exponential for other errors
                delay = self.initial_delay * (2 ** attempt)
        
        return min(delay, self.max_delay)
    
    def _should_retry(self, error: Exception, attempt: int) -> bool:
        """
        Determine if we should retry based on error type.
        
        Args:
            error: The exception that occurred
            attempt: Current attempt number
            
        Returns:
            True if should retry, False otherwise
        """
        # Don't retry if max retries exceeded
        if attempt >= self.max_retries:
            return False
        
        # Never retry on permanent errors
        if isinstance(error, AccountNotFoundError):
            return False
        
        # Retry on transient errors
        if isinstance(error, (RateLimitError, NetworkError, ConnectionError, TimeoutError)):
            return True
        
        # Retry on generic scraper errors (might be transient)
        if isinstance(error, ScraperError):
            # Check error message for transient indicators
            error_msg = str(error).lower()
            if any(indicator in error_msg for indicator in ['timeout', 'connection', 'network', 'temporary']):
                return True
        
        # Don't retry on private account errors (permanent)
        if isinstance(error, PrivateAccountError):
            return False
        
        # Default: retry on unknown errors (might be transient)
        return True
    
    def retry(
        self,
        func: Callable,
        *args,
        retryable_exceptions: Tuple[Type[Exception], ...] = (
            RateLimitError, NetworkError, ConnectionError, TimeoutError, ScraperError
        ),
        **kwargs
    ) -> Any:
        """
        Execute function with intelligent retry logic.
        
        Args:
            func: Function to execute
            *args: Function arguments
            retryable_exceptions: Exceptions that should trigger retry
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Last exception if all retries fail
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except retryable_exceptions as e:
                last_exception = e
                
                # Check if we should retry
                if not self._should_retry(e, attempt):
                    logger.debug(f"Not retrying {func.__name__}: {e}")
                    raise
                
                # Calculate delay
                retry_after = getattr(e, 'retry_after', None) if isinstance(e, RateLimitError) else None
                delay = self._calculate_delay(attempt, e, retry_after)
                
                if attempt < self.max_retries:
                    logger.warning(
                        f"Attempt {attempt + 1}/{self.max_retries + 1} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f} seconds (strategy: {self.strategy.value})..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"All {self.max_retries + 1} attempts failed for {func.__name__}")
                    raise
        
        # Should never reach here
        if last_exception:
            raise last_exception


def intelligent_retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    strategy: RetryStrategy = RetryStrategy.ADAPTIVE,
    retryable_exceptions: Tuple[Type[Exception], ...] = (
        RateLimitError, NetworkError, ConnectionError, TimeoutError, ScraperError
    ),
):
    """
    Decorator for intelligent retry with adaptive strategies.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        strategy: Retry strategy to use
        retryable_exceptions: Exceptions that should trigger retry
        
    Example:
        @intelligent_retry(max_retries=5, strategy=RetryStrategy.ADAPTIVE)
        def scrape_account(url):
            ...
    """
    retry_handler = IntelligentRetry(
        max_retries=max_retries,
        initial_delay=initial_delay,
        max_delay=max_delay,
        strategy=strategy,
    )
    
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return retry_handler.retry(
                func,
                *args,
                retryable_exceptions=retryable_exceptions,
                **kwargs
            )
        return wrapper
    return decorator


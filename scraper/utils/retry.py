"""
Retry logic with exponential backoff.
"""

import time
import logging
from functools import wraps
from typing import Callable, Type, Tuple, Optional

from .errors import (
    ScraperError,
    RateLimitError,
    NetworkError,
)

logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (RateLimitError, NetworkError, ConnectionError, TimeoutError),
):
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        retryable_exceptions: Tuple of exceptions that should trigger retry
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    
                    # Check if we should retry
                    if attempt < max_retries:
                        # Handle rate limit errors with retry_after
                        if isinstance(e, RateLimitError) and e.retry_after:
                            delay = min(e.retry_after, max_delay)
                        else:
                            delay = min(initial_delay * (exponential_base ** attempt), max_delay)
                        
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay:.2f} seconds..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed for {func.__name__}")
                        raise
                except Exception as e:
                    # Non-retryable exceptions are raised immediately
                    logger.error(f"Non-retryable error in {func.__name__}: {e}")
                    raise
            
            # Should never reach here, but just in case
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator


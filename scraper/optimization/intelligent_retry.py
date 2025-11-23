"""
Intelligent retry strategies for scrapers.
Adapts retry behavior based on platform responses and historical success rates.
"""
import time
import random
from datetime import datetime, timedelta
from typing import Dict, Optional, Callable
from enum import Enum

class RetryStrategy(Enum):
    """Retry strategy types."""
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    ADAPTIVE = "adaptive"
    FIBONACCI = "fibonacci"

class IntelligentRetry:
    """Intelligent retry mechanism that adapts based on success patterns."""
    
    def __init__(self, max_retries=5, base_delay=1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.success_history = {}  # Track success rates per platform
        self.last_retry_times = {}  # Track last retry times
    
    def calculate_delay(self, attempt: int, strategy: RetryStrategy = RetryStrategy.ADAPTIVE, 
                       platform: Optional[str] = None) -> float:
        """Calculate delay before next retry attempt."""
        if strategy == RetryStrategy.EXPONENTIAL:
            return self.base_delay * (2 ** attempt)
        elif strategy == RetryStrategy.LINEAR:
            return self.base_delay * (attempt + 1)
        elif strategy == RetryStrategy.FIBONACCI:
            fib = [1, 1, 2, 3, 5, 8, 13, 21]
            return self.base_delay * fib[min(attempt, len(fib) - 1)]
        else:  # ADAPTIVE
            return self._adaptive_delay(attempt, platform)
    
    def _adaptive_delay(self, attempt: int, platform: Optional[str] = None) -> float:
        """Calculate adaptive delay based on platform success rate."""
        base_delay = self.base_delay * (2 ** attempt)
        
        if platform and platform in self.success_history:
            success_rate = self.success_history[platform]
            # If platform has low success rate, increase delay
            if success_rate < 0.5:
                base_delay *= 2
            # If platform has high success rate, decrease delay slightly
            elif success_rate > 0.9:
                base_delay *= 0.8
        
        # Add jitter to prevent thundering herd
        jitter = random.uniform(0.8, 1.2)
        return base_delay * jitter
    
    def should_retry(self, attempt: int, error: Exception, platform: Optional[str] = None) -> bool:
        """Determine if we should retry based on error type and attempt count."""
        if attempt >= self.max_retries:
            return False
        
        # Don't retry on certain errors
        non_retryable_errors = (
            ValueError,  # Invalid input
            KeyError,    # Missing data
            AttributeError  # Wrong structure
        )
        
        if isinstance(error, non_retryable_errors):
            return False
        
        # Check platform-specific retry rules
        if platform and platform in self.success_history:
            success_rate = self.success_history[platform]
            # If platform consistently fails, reduce max retries
            if success_rate < 0.3 and attempt >= 2:
                return False
        
        return True
    
    def record_success(self, platform: str):
        """Record successful scrape for platform."""
        if platform not in self.success_history:
            self.success_history[platform] = []
        
        self.success_history[platform].append(True)
        # Keep only last 100 records
        if len(self.success_history[platform]) > 100:
            self.success_history[platform] = self.success_history[platform][-100:]
    
    def record_failure(self, platform: str):
        """Record failed scrape for platform."""
        if platform not in self.success_history:
            self.success_history[platform] = []
        
        self.success_history[platform].append(False)
        # Keep only last 100 records
        if len(self.success_history[platform]) > 100:
            self.success_history[platform] = self.success_history[platform][-100:]
    
    def get_success_rate(self, platform: str) -> float:
        """Get success rate for a platform."""
        if platform not in self.success_history or not self.success_history[platform]:
            return 1.0  # Assume success if no history
        
        history = self.success_history[platform]
        return sum(history) / len(history)
    
    def retry_with_backoff(self, func: Callable, *args, platform: Optional[str] = None, 
                         strategy: RetryStrategy = RetryStrategy.ADAPTIVE, **kwargs):
        """Execute function with intelligent retry logic."""
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                
                # Record success
                if platform:
                    self.record_success(platform)
                
                return result
            
            except Exception as e:
                last_error = e
                
                # Check if we should retry
                if not self.should_retry(attempt, e, platform):
                    break
                
                # Calculate delay
                delay = self.calculate_delay(attempt, strategy, platform)
                
                # Wait before retry
                if attempt < self.max_retries:
                    time.sleep(delay)
        
        # Record failure
        if platform:
            self.record_failure(platform)
        
        # Re-raise last error
        raise last_error

# Global instance
intelligent_retry = IntelligentRetry(max_retries=5, base_delay=1.0)


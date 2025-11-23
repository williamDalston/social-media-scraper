"""
Adaptive rate limiting that adjusts based on platform responses.
"""

import time
import logging
from typing import Optional
from collections import deque

from .rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class AdaptiveRateLimiter(RateLimiter):
    """
    Rate limiter that adapts based on platform responses.
    Automatically adjusts rate limits when receiving 429 errors or successful responses.
    """
    
    def __init__(self, platform: str, requests: Optional[int] = None, window: Optional[int] = None):
        """
        Initialize adaptive rate limiter.
        
        Args:
            platform: Platform name
            requests: Initial number of requests allowed
            window: Initial time window in seconds
        """
        super().__init__(platform, requests, window)
        
        self.original_requests = requests or self.requests
        self.original_window = window or self.window
        self.adaptation_factor = 1.0
        self.min_requests = 1
        self.max_requests = self.original_requests * 2
        
        # Track recent responses
        self._recent_responses: deque = deque(maxlen=20)
        
        logger.info(f"Initialized AdaptiveRateLimiter for {platform}")
    
    def record_response(self, status_code: int):
        """
        Record a response status code to adapt rate limiting.
        
        Args:
            status_code: HTTP status code
        """
        self._recent_responses.append({
            'status_code': status_code,
            'timestamp': time.time(),
        })
        
        # Analyze recent responses
        self._adapt_rate_limit()
    
    def _adapt_rate_limit(self):
        """Adapt rate limit based on recent responses."""
        if len(self._recent_responses) < 5:
            return  # Need more data
        
        # Count rate limit errors in recent responses
        recent_429s = sum(
            1 for r in self._recent_responses
            if r['status_code'] == 429
        )
        
        # Count successful responses
        recent_successes = sum(
            1 for r in self._recent_responses
            if 200 <= r['status_code'] < 300
        )
        
        total_recent = len(self._recent_responses)
        error_rate = recent_429s / total_recent if total_recent > 0 else 0
        success_rate = recent_successes / total_recent if total_recent > 0 else 0
        
        # Adapt based on error rate
        if error_rate > 0.2:  # More than 20% rate limit errors
            # Reduce rate limit
            self.adaptation_factor *= 0.8
            logger.warning(
                f"Reducing rate limit for {self.platform} due to high error rate "
                f"({error_rate:.1%})"
            )
        elif error_rate == 0 and success_rate > 0.9:  # No errors, high success rate
            # Can increase rate limit slightly
            self.adaptation_factor = min(1.2, self.adaptation_factor * 1.05)
            logger.info(
                f"Increasing rate limit for {self.platform} due to good performance"
            )
        else:
            # Maintain current rate
            pass
        
        # Apply adaptation factor
        new_requests = int(self.original_requests * self.adaptation_factor)
        new_requests = max(self.min_requests, min(self.max_requests, new_requests))
        
        if new_requests != self.requests:
            logger.info(
                f"Adapting rate limit for {self.platform}: "
                f"{self.requests} -> {new_requests} requests per {self.window}s"
            )
            self.requests = new_requests
    
    def reset_adaptation(self):
        """Reset adaptation to original values."""
        self.adaptation_factor = 1.0
        self.requests = self.original_requests
        self._recent_responses.clear()
        logger.info(f"Reset rate limit adaptation for {self.platform}")


def get_adaptive_rate_limiter(platform: str) -> AdaptiveRateLimiter:
    """
    Get or create an adaptive rate limiter for a platform.
    
    Args:
        platform: Platform name
        
    Returns:
        AdaptiveRateLimiter instance
    """
    # For now, return a regular rate limiter wrapped
    # In production, replace the rate_limiter module's get_rate_limiter
    from .rate_limiter import RateLimiter as BaseRateLimiter
    limits = BaseRateLimiter.DEFAULT_LIMITS.get(platform, (10, 3600))
    return AdaptiveRateLimiter(platform, limits[0], limits[1])


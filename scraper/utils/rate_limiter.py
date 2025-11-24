"""
Rate limiting per platform.
"""

import time
import threading
from collections import defaultdict
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Thread-safe rate limiter for controlling request frequency.
    """

    # Default rate limits per platform (requests per time window)
    DEFAULT_LIMITS = {
        "x": (15, 900),  # 15 requests per 15 minutes
        "instagram": (10, 3600),  # 10 requests per hour (conservative)
        "facebook": (200, 3600),  # 200 requests per hour (varies by tier)
        "linkedin": (5, 3600),  # 5 requests per hour (very conservative)
        "youtube": (100, 3600),  # 100 requests per hour (quota managed separately)
        "truth_social": (10, 3600),  # 10 requests per hour
        "tiktok": (10, 3600),  # 10 requests per hour (conservative)
    }

    def __init__(
        self,
        platform: str,
        requests: Optional[int] = None,
        window: Optional[int] = None,
    ):
        """
        Initialize rate limiter for a platform.

        Args:
            platform: Platform name
            requests: Number of requests allowed (defaults to platform default)
            window: Time window in seconds (defaults to platform default)
        """
        self.platform = platform
        self.lock = threading.Lock()

        if requests is None or window is None:
            requests, window = self.DEFAULT_LIMITS.get(platform, (10, 3600))

        self.requests = requests
        self.window = window
        self.request_times: list = []

        logger.info(
            f"Rate limiter initialized for {platform}: {requests} requests per {window} seconds"
        )

    def wait_if_needed(self):
        """
        Wait if rate limit would be exceeded, otherwise record the request.
        """
        with self.lock:
            now = time.time()

            # Remove requests outside the time window
            self.request_times = [
                t for t in self.request_times if now - t < self.window
            ]

            # If we're at the limit, wait until the oldest request expires
            if len(self.request_times) >= self.requests:
                oldest_request = min(self.request_times)
                wait_time = (
                    self.window - (now - oldest_request) + 0.1
                )  # Add small buffer
                if wait_time > 0:
                    logger.info(
                        f"Rate limit reached for {self.platform}. Waiting {wait_time:.2f} seconds..."
                    )
                    time.sleep(wait_time)
                    # Clean up again after waiting
                    now = time.time()
                    self.request_times = [
                        t for t in self.request_times if now - t < self.window
                    ]

            # Record this request
            self.request_times.append(time.time())

    def can_make_request(self) -> bool:
        """
        Check if a request can be made without waiting.

        Returns:
            True if request can be made immediately, False otherwise
        """
        with self.lock:
            now = time.time()
            self.request_times = [
                t for t in self.request_times if now - t < self.window
            ]
            return len(self.request_times) < self.requests


# Global rate limiters per platform
_rate_limiters: Dict[str, RateLimiter] = {}
_rate_limiter_lock = threading.Lock()


def get_rate_limiter(platform: str) -> RateLimiter:
    """
    Get or create a rate limiter for a platform.

    Args:
        platform: Platform name

    Returns:
        RateLimiter instance for the platform
    """
    with _rate_limiter_lock:
        if platform not in _rate_limiters:
            _rate_limiters[platform] = RateLimiter(platform)
        return _rate_limiters[platform]

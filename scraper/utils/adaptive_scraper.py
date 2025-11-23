"""
Adaptive scraping algorithms that adjust behavior based on platform responses.
"""

import logging
import time
from typing import Dict, Any, Optional, List
from collections import deque
from enum import Enum

logger = logging.getLogger(__name__)


class ScrapingStrategy(Enum):
    """Scraping strategy types."""
    AGGRESSIVE = "aggressive"  # Fast, may hit rate limits
    BALANCED = "balanced"  # Default, balanced approach
    CONSERVATIVE = "conservative"  # Slow, avoids rate limits
    ADAPTIVE = "adaptive"  # Adjusts based on responses


class AdaptiveScraper:
    """
    Adaptive scraper that adjusts behavior based on platform responses.
    """
    
    def __init__(self, platform: str):
        """
        Initialize adaptive scraper.
        
        Args:
            platform: Platform name
        """
        self.platform = platform
        self.strategy = ScrapingStrategy.BALANCED
        self._response_history: deque = deque(maxlen=50)
        self._success_rate = 1.0
        self._error_rate = 0.0
        logger.info(f"Initialized AdaptiveScraper for {platform}")
    
    def record_response(
        self,
        success: bool,
        status_code: Optional[int] = None,
        duration: Optional[float] = None,
    ):
        """
        Record a scraping response to adapt strategy.
        
        Args:
            success: Whether scraping was successful
            status_code: HTTP status code (if available)
            duration: Request duration in seconds
        """
        self._response_history.append({
            'success': success,
            'status_code': status_code,
            'duration': duration,
            'timestamp': time.time(),
        })
        
        # Update success/error rates
        if len(self._response_history) >= 10:
            recent = list(self._response_history)[-10:]
            self._success_rate = sum(1 for r in recent if r['success']) / len(recent)
            self._error_rate = 1.0 - self._success_rate
        
        # Adapt strategy based on performance
        self._adapt_strategy()
    
    def _adapt_strategy(self):
        """Adapt scraping strategy based on recent performance."""
        if len(self._response_history) < 10:
            return  # Need more data
        
        # Count rate limit errors
        rate_limit_errors = sum(
            1 for r in self._response_history
            if r.get('status_code') == 429
        )
        rate_limit_rate = rate_limit_errors / len(self._response_history)
        
        # Adapt based on error rates
        if rate_limit_rate > 0.2:  # More than 20% rate limit errors
            if self.strategy != ScrapingStrategy.CONSERVATIVE:
                logger.warning(
                    f"Switching to CONSERVATIVE strategy for {self.platform} "
                    f"due to high rate limit errors ({rate_limit_rate:.1%})"
                )
                self.strategy = ScrapingStrategy.CONSERVATIVE
        elif rate_limit_rate == 0 and self._success_rate > 0.95:
            # No rate limit errors and high success rate
            if self.strategy == ScrapingStrategy.CONSERVATIVE:
                logger.info(
                    f"Switching to BALANCED strategy for {self.platform} "
                    f"due to good performance"
                )
                self.strategy = ScrapingStrategy.BALANCED
        elif self._error_rate > 0.5:  # More than 50% errors
            if self.strategy != ScrapingStrategy.CONSERVATIVE:
                logger.warning(
                    f"Switching to CONSERVATIVE strategy for {self.platform} "
                    f"due to high error rate ({self._error_rate:.1%})"
                )
                self.strategy = ScrapingStrategy.CONSERVATIVE
    
    def get_delay(self) -> float:
        """
        Get delay between requests based on current strategy.
        
        Returns:
            Delay in seconds
        """
        if self.strategy == ScrapingStrategy.AGGRESSIVE:
            return 0.5
        elif self.strategy == ScrapingStrategy.BALANCED:
            return 2.0
        elif self.strategy == ScrapingStrategy.CONSERVATIVE:
            return 5.0
        else:  # ADAPTIVE
            # Adjust based on success rate
            if self._success_rate > 0.95:
                return 1.0
            elif self._success_rate > 0.80:
                return 2.0
            else:
                return 5.0
    
    def get_timeout(self) -> int:
        """
        Get request timeout based on current strategy.
        
        Returns:
            Timeout in seconds
        """
        if self.strategy == ScrapingStrategy.AGGRESSIVE:
            return 15
        elif self.strategy == ScrapingStrategy.BALANCED:
            return 30
        else:  # CONSERVATIVE or ADAPTIVE
            return 45
    
    def should_retry(self, error: Exception) -> bool:
        """
        Determine if should retry based on strategy and error.
        
        Args:
            error: The exception that occurred
            
        Returns:
            True if should retry
        """
        # Conservative strategy retries less
        if self.strategy == ScrapingStrategy.CONSERVATIVE:
            # Only retry on rate limits
            from .errors import RateLimitError
            return isinstance(error, RateLimitError)
        
        # Other strategies retry more aggressively
        return True
    
    def get_strategy(self) -> ScrapingStrategy:
        """Get current scraping strategy."""
        return self.strategy
    
    def reset(self):
        """Reset adaptive scraper to initial state."""
        self.strategy = ScrapingStrategy.BALANCED
        self._response_history.clear()
        self._success_rate = 1.0
        self._error_rate = 0.0
        logger.info(f"Reset AdaptiveScraper for {self.platform}")


# Global adaptive scrapers per platform
_adaptive_scrapers: Dict[str, AdaptiveScraper] = {}


def get_adaptive_scraper(platform: str) -> AdaptiveScraper:
    """
    Get or create adaptive scraper for a platform.
    
    Args:
        platform: Platform name
        
    Returns:
        AdaptiveScraper instance
    """
    if platform not in _adaptive_scrapers:
        _adaptive_scrapers[platform] = AdaptiveScraper(platform)
    return _adaptive_scrapers[platform]


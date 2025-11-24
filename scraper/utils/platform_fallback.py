"""
Fallback mechanisms for platform changes and failures.
"""

import logging
from typing import Dict, Any, Optional, List, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class FallbackStrategy(Enum):
    """Fallback strategy types."""

    NONE = "none"  # No fallback
    SIMULATE = "simulate"  # Use simulated data
    CACHE = "cache"  # Use cached data
    PREVIOUS = "previous"  # Use previous snapshot
    MULTIPLE = "multiple"  # Try multiple methods


class PlatformFallback:
    """
    Handles fallback mechanisms when scraping fails or platform changes.
    """

    def __init__(self):
        """Initialize platform fallback."""
        self._fallback_strategies: Dict[str, FallbackStrategy] = {}
        self._fallback_history: Dict[str, List[Dict[str, Any]]] = {}
        logger.info("Initialized PlatformFallback")

    def set_fallback_strategy(
        self,
        platform: str,
        strategy: FallbackStrategy,
    ):
        """
        Set fallback strategy for a platform.

        Args:
            platform: Platform name
            strategy: Fallback strategy to use
        """
        self._fallback_strategies[platform] = strategy
        logger.info(f"Set fallback strategy for {platform}: {strategy.value}")

    def get_fallback_data(
        self,
        platform: str,
        account_key: int,
        fallback_strategy: Optional[FallbackStrategy] = None,
        previous_data: Optional[Dict[str, Any]] = None,
        cached_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get fallback data when scraping fails.

        Args:
            platform: Platform name
            account_key: Account key
            fallback_strategy: Strategy to use (uses platform default if None)
            previous_data: Previous snapshot data
            cached_data: Cached data if available

        Returns:
            Fallback data dictionary or None
        """
        strategy = fallback_strategy or self._fallback_strategies.get(
            platform, FallbackStrategy.PREVIOUS
        )

        if strategy == FallbackStrategy.NONE:
            return None

        # Record fallback usage
        if platform not in self._fallback_history:
            self._fallback_history[platform] = []

        self._fallback_history[platform].append(
            {
                "account_key": account_key,
                "strategy": strategy.value,
                "timestamp": str(
                    logging.Formatter().formatTime(
                        logging.LogRecord(
                            name="",
                            level=0,
                            pathname="",
                            lineno=0,
                            msg="",
                            args=(),
                            exc_info=None,
                        )
                    )
                ),
            }
        )

        # Get data based on strategy
        if strategy == FallbackStrategy.PREVIOUS:
            if previous_data:
                logger.info(
                    f"Using previous snapshot data for {platform} account {account_key}"
                )
                return previous_data.copy()

        elif strategy == FallbackStrategy.CACHE:
            if cached_data:
                logger.info(f"Using cached data for {platform} account {account_key}")
                return cached_data.copy()

        elif strategy == FallbackStrategy.SIMULATE:
            logger.warning(
                f"Using simulated data for {platform} account {account_key} "
                "(scraping failed)"
            )
            # Generate basic simulated data
            return {
                "followers_count": previous_data.get("followers_count", 0)
                if previous_data
                else 0,
                "following_count": previous_data.get("following_count", 0)
                if previous_data
                else 0,
                "posts_count": previous_data.get("posts_count", 0)
                if previous_data
                else 0,
                "likes_count": 0,
                "comments_count": 0,
                "shares_count": 0,
                "is_fallback": True,
                "fallback_strategy": "simulate",
            }

        elif strategy == FallbackStrategy.MULTIPLE:
            # Try multiple strategies in order
            if cached_data:
                logger.info(f"Using cached data (multiple strategy) for {platform}")
                return cached_data.copy()
            elif previous_data:
                logger.info(f"Using previous data (multiple strategy) for {platform}")
                return previous_data.copy()
            else:
                # Last resort: simulate
                return self.get_fallback_data(
                    platform,
                    account_key,
                    FallbackStrategy.SIMULATE,
                    previous_data,
                    cached_data,
                )

        return None

    def detect_platform_change(
        self,
        platform: str,
        error_pattern: str,
    ) -> bool:
        """
        Detect if platform structure has changed based on error patterns.

        Args:
            platform: Platform name
            error_pattern: Error message or pattern

        Returns:
            True if platform change detected
        """
        # Common indicators of platform changes
        change_indicators = [
            "404",
            "not found",
            "page structure",
            "element not found",
            "selector",
            "html structure",
            "api endpoint",
        ]

        error_lower = error_pattern.lower()

        for indicator in change_indicators:
            if indicator in error_lower:
                logger.warning(
                    f"Possible platform change detected for {platform}: {error_pattern}"
                )
                return True

        return False

    def get_fallback_statistics(self, platform: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics on fallback usage.

        Args:
            platform: Platform name (None for all platforms)

        Returns:
            Dictionary with fallback statistics
        """
        if platform:
            history = self._fallback_history.get(platform, [])
            return {
                "platform": platform,
                "total_fallbacks": len(history),
                "by_strategy": {
                    strategy.value: sum(
                        1 for h in history if h["strategy"] == strategy.value
                    )
                    for strategy in FallbackStrategy
                },
            }
        else:
            # All platforms
            total = sum(len(h) for h in self._fallback_history.values())
            return {
                "total_fallbacks": total,
                "by_platform": {p: len(h) for p, h in self._fallback_history.items()},
            }


# Global platform fallback
_platform_fallback: Optional[PlatformFallback] = None


def get_platform_fallback() -> PlatformFallback:
    """Get or create global platform fallback."""
    global _platform_fallback
    if _platform_fallback is None:
        _platform_fallback = PlatformFallback()
    return _platform_fallback

"""
Utility modules for scrapers.
"""

from .errors import (
    ScraperError,
    RateLimitError,
    AuthenticationError,
    AccountNotFoundError,
    PrivateAccountError,
    NetworkError,
)

from .retry import retry_with_backoff
from .rate_limiter import RateLimiter
from .proxy_manager import ProxyManager
from .parsers import parse_follower_count, parse_engagement_metrics
from .validators import validate_scraped_data
from .content_extractor import (
    extract_hashtags,
    extract_mentions,
    extract_urls,
    extract_content_elements,
    format_hashtags_for_storage,
    format_mentions_for_storage,
)
from .sentiment_analyzer import analyze_sentiment, get_tone_from_sentiment
from .cache import SimpleCache, get_cache, cached
from .connection_pool import PlatformConnectionPool, get_connection_pool
from .duplicate_detector import DuplicateDetector, get_duplicate_detector
from .anomaly_detector import AnomalyDetector, get_anomaly_detector
from .health_monitor import ScraperHealthMonitor, get_health_monitor
from .adaptive_rate_limiter import AdaptiveRateLimiter, get_adaptive_rate_limiter
from .data_quality import DataQualityScorer, get_quality_scorer
from .intelligent_retry import IntelligentRetry, intelligent_retry, RetryStrategy
from .result_validator import ResultValidator, get_result_validator
from .data_enrichment import DataEnricher, get_data_enricher
from .data_freshness import DataFreshnessMonitor, get_freshness_monitor
from .adaptive_scraper import AdaptiveScraper, get_adaptive_scraper, ScrapingStrategy
from .platform_health import PlatformHealthMonitor, get_platform_health_monitor
from .metrics_calculator import MetricsCalculator, get_metrics_calculator
from .historical_correlation import HistoricalCorrelator, get_historical_correlator
from .anomaly_correction import AnomalyCorrector, get_anomaly_corrector
from .realtime_validator import RealtimeValidator, get_realtime_validator
from .platform_fallback import PlatformFallback, get_platform_fallback, FallbackStrategy
from .precision_extractor import PrecisionExtractor, get_precision_extractor
from .post_content_scraper import PostContentScraper, get_post_content_scraper

__all__ = [
    "ScraperError",
    "RateLimitError",
    "AuthenticationError",
    "AccountNotFoundError",
    "PrivateAccountError",
    "NetworkError",
    "retry_with_backoff",
    "RateLimiter",
    "ProxyManager",
    "parse_follower_count",
    "parse_engagement_metrics",
    "validate_scraped_data",
    "extract_hashtags",
    "extract_mentions",
    "extract_urls",
    "extract_content_elements",
    "format_hashtags_for_storage",
    "format_mentions_for_storage",
    "analyze_sentiment",
    "get_tone_from_sentiment",
    "SimpleCache",
    "get_cache",
    "cached",
    "PlatformConnectionPool",
    "get_connection_pool",
    "DuplicateDetector",
    "get_duplicate_detector",
    "AnomalyDetector",
    "get_anomaly_detector",
    "ScraperHealthMonitor",
    "get_health_monitor",
    "AdaptiveRateLimiter",
    "get_adaptive_rate_limiter",
    "DataQualityScorer",
    "get_quality_scorer",
    "IntelligentRetry",
    "intelligent_retry",
    "RetryStrategy",
    "ResultValidator",
    "get_result_validator",
    "DataEnricher",
    "get_data_enricher",
    "DataFreshnessMonitor",
    "get_freshness_monitor",
    "AdaptiveScraper",
    "get_adaptive_scraper",
    "ScrapingStrategy",
    "PlatformHealthMonitor",
    "get_platform_health_monitor",
    "MetricsCalculator",
    "get_metrics_calculator",
    "HistoricalCorrelator",
    "get_historical_correlator",
    "AnomalyCorrector",
    "get_anomaly_corrector",
    "RealtimeValidator",
    "get_realtime_validator",
    "PlatformFallback",
    "get_platform_fallback",
    "FallbackStrategy",
    "PrecisionExtractor",
    "get_precision_extractor",
    "PostContentScraper",
    "get_post_content_scraper",
]

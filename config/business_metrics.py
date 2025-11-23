"""
Custom business metrics tracking for the HHS Social Media Scraper.
Tracks business-specific KPIs and metrics.
"""
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
from prometheus_client import Counter, Histogram, Gauge

logger = logging.getLogger(__name__)

# Business metrics
accounts_scraped_today = Counter(
    'business_accounts_scraped_today',
    'Total accounts scraped today',
    ['platform']
)

accounts_scraped_total = Counter(
    'business_accounts_scraped_total',
    'Total accounts scraped (cumulative)',
    ['platform']
)

scraping_success_rate = Gauge(
    'business_scraping_success_rate',
    'Scraping success rate percentage',
    ['platform']
)

daily_active_accounts = Gauge(
    'business_daily_active_accounts',
    'Number of accounts with activity today',
    ['platform']
)

follower_growth_rate = Histogram(
    'business_follower_growth_rate',
    'Follower growth rate percentage',
    ['platform']
)

engagement_rate = Histogram(
    'business_engagement_rate',
    'Engagement rate (engagements / followers)',
    ['platform']
)

data_freshness_hours = Gauge(
    'business_data_freshness_hours',
    'Hours since last successful scrape',
    ['platform']
)

# In-memory tracking (could be moved to Redis for distributed systems)
_daily_stats = defaultdict(lambda: {
    'accounts_scraped': 0,
    'successful_scrapes': 0,
    'failed_scrapes': 0,
    'platforms': defaultdict(int)
})


def record_account_scraped(platform: str, success: bool = True):
    """
    Record that an account was scraped.
    
    Args:
        platform: Platform name
        success: Whether scraping was successful
    """
    platform_lower = platform.lower()
    accounts_scraped_today.labels(platform=platform_lower).inc()
    accounts_scraped_total.labels(platform=platform_lower).inc()
    
    today = datetime.utcnow().date()
    stats = _daily_stats[today]
    stats['accounts_scraped'] += 1
    stats['platforms'][platform_lower] += 1
    
    if success:
        stats['successful_scrapes'] += 1
    else:
        stats['failed_scrapes'] += 1
    
    # Update success rate
    total = stats['successful_scrapes'] + stats['failed_scrapes']
    if total > 0:
        rate = (stats['successful_scrapes'] / total) * 100
        scraping_success_rate.labels(platform=platform_lower).set(rate)


def record_follower_growth(platform: str, growth_percent: float):
    """
    Record follower growth rate.
    
    Args:
        platform: Platform name
        growth_percent: Growth percentage
    """
    follower_growth_rate.labels(platform=platform.lower()).observe(growth_percent)


def record_engagement_rate(platform: str, rate: float):
    """
    Record engagement rate.
    
    Args:
        platform: Platform name
        rate: Engagement rate (engagements / followers)
    """
    engagement_rate.labels(platform=platform.lower()).observe(rate)


def update_data_freshness(platform: str, hours_since_last_scrape: float):
    """
    Update data freshness metric.
    
    Args:
        platform: Platform name
        hours_since_last_scrape: Hours since last successful scrape
    """
    data_freshness_hours.labels(platform=platform.lower()).set(hours_since_last_scrape)


def update_daily_active_accounts(platform: str, count: int):
    """
    Update daily active accounts count.
    
    Args:
        platform: Platform name
        count: Number of active accounts
    """
    daily_active_accounts.labels(platform=platform.lower()).set(count)


def get_business_metrics_summary() -> Dict:
    """
    Get summary of business metrics.
    
    Returns:
        Dictionary with business metrics summary
    """
    today = datetime.utcnow().date()
    stats = _daily_stats[today]
    
    return {
        'date': today.isoformat(),
        'accounts_scraped_today': stats['accounts_scraped'],
        'successful_scrapes': stats['successful_scrapes'],
        'failed_scrapes': stats['failed_scrapes'],
        'success_rate': (
            (stats['successful_scrapes'] / stats['accounts_scraped'] * 100)
            if stats['accounts_scraped'] > 0 else 0
        ),
        'platforms': dict(stats['platforms']),
        'timestamp': datetime.utcnow().isoformat()
    }


def calculate_engagement_rate(followers: int, engagements: int) -> float:
    """
    Calculate engagement rate.
    
    Args:
        followers: Follower count
        engagements: Total engagements
    
    Returns:
        Engagement rate (0-1)
    """
    if followers == 0:
        return 0.0
    return engagements / followers


def calculate_growth_rate(current: int, previous: int) -> float:
    """
    Calculate growth rate percentage.
    
    Args:
        current: Current value
        previous: Previous value
    
    Returns:
        Growth rate percentage
    """
    if previous == 0:
        return 0.0 if current == 0 else 100.0
    return ((current - previous) / previous) * 100


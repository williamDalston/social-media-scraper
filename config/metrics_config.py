"""
Prometheus metrics configuration for the HHS Social Media Scraper.
"""
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
import time

# API Metrics
http_requests_total = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)

# Scraper Metrics
scraper_runs_total = Counter(
    "scraper_runs_total", "Total scraper runs", ["mode", "status"]
)

scraper_duration_seconds = Histogram(
    "scraper_duration_seconds", "Scraper execution duration in seconds", ["mode"]
)

scraper_accounts_scraped = Counter(
    "scraper_accounts_scraped", "Total accounts scraped", ["platform", "status"]
)

# Database Metrics
db_queries_total = Counter("db_queries_total", "Total database queries", ["operation"])

db_query_duration_seconds = Histogram(
    "db_query_duration_seconds", "Database query duration in seconds", ["operation"]
)

# System Metrics
active_jobs = Gauge("active_jobs", "Number of active background jobs")

accounts_total = Gauge(
    "accounts_total", "Total number of accounts in database", ["platform"]
)

latest_snapshot_date = Gauge(
    "latest_snapshot_date_timestamp", "Timestamp of the latest snapshot date"
)

# Parallel scraping metrics
parallel_scraping_workers = Gauge(
    "parallel_scraping_workers", "Number of parallel workers used for scraping"
)

parallel_scraping_accounts_per_second = Gauge(
    "parallel_scraping_accounts_per_second",
    "Accounts scraped per second in parallel mode",
)


def get_metrics():
    """
    Get Prometheus metrics in text format.

    Returns:
        str: Metrics in Prometheus format
    """
    return generate_latest()


def record_request(method, endpoint, status, duration):
    """
    Record HTTP request metrics.

    Args:
        method: HTTP method
        endpoint: Endpoint path
        status: HTTP status code
        duration: Request duration in seconds
    """
    http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
    http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(
        duration
    )


def record_scraper_run(
    mode,
    status,
    duration,
    accounts_scraped=None,
    parallel=False,
    max_workers=None,
    accounts_per_second=None,
):
    """
    Record scraper execution metrics.

    Args:
        mode: Scraper mode (simulated, real)
        status: Status (success, error, partial)
        duration: Execution duration in seconds
        accounts_scraped: Dictionary of platform -> count (optional)
        parallel: Whether parallel scraping was used (optional)
        max_workers: Number of parallel workers (optional)
        accounts_per_second: Scraping rate in accounts/second (optional)
    """
    scraper_runs_total.labels(mode=mode, status=status).inc()
    scraper_duration_seconds.labels(mode=mode).observe(duration)

    if accounts_scraped:
        for platform, count in accounts_scraped.items():
            scraper_accounts_scraped.labels(platform=platform, status=status).inc(count)

    # Record parallel scraping metrics
    if parallel and max_workers is not None:
        parallel_scraping_workers.set(max_workers)

    if accounts_per_second is not None:
        parallel_scraping_accounts_per_second.set(accounts_per_second)


def record_db_query(operation, duration):
    """
    Record database query metrics.

    Args:
        operation: Operation type (select, insert, update, delete)
        duration: Query duration in seconds
    """
    db_queries_total.labels(operation=operation).inc()
    db_query_duration_seconds.labels(operation=operation).observe(duration)

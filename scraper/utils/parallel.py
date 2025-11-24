"""
Parallel scraping utilities for concurrent account scraping.
"""
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Callable, Optional, Tuple
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger(__name__)

class ScrapingMetrics:
    """Track scraping performance metrics."""
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.success_count = 0
        self.error_count = 0
        self.skipped_count = 0
        self.account_times = {}
        self.platform_counts = defaultdict(int)
        
    def start(self):
        """Start timing."""
        self.start_time = time.time()
        
    def finish(self):
        """Finish timing."""
        self.end_time = time.time()
        
    def record_success(self, account_key: int, platform: str, duration: float):
        """Record successful scrape."""
        self.success_count += 1
        self.platform_counts[platform] += 1
        self.account_times[account_key] = duration
        
    def record_error(self, account_key: int, platform: str):
        """Record failed scrape."""
        self.error_count += 1
        self.platform_counts[platform] += 1
        
    def record_skipped(self, account_key: int, platform: str):
        """Record skipped scrape."""
        self.skipped_count += 1
        self.platform_counts[platform] += 1
        
    def get_summary(self) -> Dict:
        """Get metrics summary."""
        total_time = (self.end_time - self.start_time) if self.end_time and self.start_time else 0
        avg_time = sum(self.account_times.values()) / len(self.account_times) if self.account_times else 0
        
        return {
            'total_time': round(total_time, 2),
            'success_count': self.success_count,
            'error_count': self.error_count,
            'skipped_count': self.skipped_count,
            'total_accounts': self.success_count + self.error_count + self.skipped_count,
            'average_time_per_account': round(avg_time, 3),
            'platform_counts': dict(self.platform_counts),
            'accounts_per_second': round(self.success_count / total_time, 2) if total_time > 0 else 0
        }


def scrape_account_parallel(
    account,
    scraper,
    session_factory,
    today,
    rate_limiter: Optional[Dict[str, float]] = None
) -> Tuple[Optional[Dict], Optional[Exception]]:
    """
    Scrape a single account (designed for parallel execution).
    
    Args:
        account: DimAccount instance
        scraper: Scraper instance
        session_factory: Function that returns a database session
        today: Date object for snapshot date
        rate_limiter: Dict mapping platform to last scrape time (for rate limiting)
        
    Returns:
        Tuple of (data_dict, error_exception)
    """
    start_time = time.time()
    session = None
    
    try:
        # Rate limiting per platform (thread-safe)
        if rate_limiter is not None:
            platform = account.platform
            # Get lock if available (passed from parent)
            lock = getattr(rate_limiter, '_lock', None)
            
            if lock:
                with lock:
                    last_scrape = rate_limiter.get(platform, 0)
                    elapsed = time.time() - last_scrape
                    min_interval = 0.5  # Minimum 0.5 seconds between scrapes per platform
                    
                    if elapsed < min_interval:
                        sleep_time = min_interval - elapsed
                        rate_limiter[platform] = time.time() + sleep_time
                    else:
                        rate_limiter[platform] = time.time()
            else:
                # Fallback for non-threaded execution
                last_scrape = rate_limiter.get(platform, 0)
                elapsed = time.time() - last_scrape
                min_interval = 0.5
                
                if elapsed < min_interval:
                    time.sleep(min_interval - elapsed)
                
                rate_limiter[platform] = time.time()
        
        session = session_factory()
        
        # Check if snapshot already exists
        from scraper.schema import FactFollowersSnapshot
        existing = session.query(FactFollowersSnapshot).filter_by(
            account_key=account.account_key,
            snapshot_date=today
        ).first()
        
        if existing:
            duration = time.time() - start_time
            logger.debug(
                f"Snapshot already exists for {account.platform}/{account.handle}",
                extra={'account_key': account.account_key, 'duration': round(duration, 3)}
            )
            return None, None  # Skipped
        
        # Scrape account
        data = scraper.scrape(account)
        
        if data:
            # Update account metadata from scraped data
            from scraper.utils.metrics_calculator import update_account_metadata
            update_account_metadata(account, data)
            
            # Create snapshot
            from scraper.schema import FactFollowersSnapshot
            snapshot = FactFollowersSnapshot(
                account_key=account.account_key,
                snapshot_date=today,
                followers_count=data.get('followers_count', 0),
                following_count=data.get('following_count', 0),
                posts_count=data.get('posts_count', 0),
                likes_count=data.get('likes_count', 0),
                comments_count=data.get('comments_count', 0),
                shares_count=data.get('shares_count', 0),
                subscribers_count=data.get('subscribers_count', 0),  # For YouTube
                video_views=data.get('views_count', 0),  # For YouTube
                engagements_total=0,
                videos_count=data.get('videos_count', 0)  # For YouTube
            )
            snapshot.engagements_total = (
                snapshot.likes_count + 
                snapshot.comments_count + 
                snapshot.shares_count
            )
            
            # Calculate additional metrics
            from scraper.utils.metrics_calculator import calculate_snapshot_metrics
            calculate_snapshot_metrics(snapshot, session, account, data)
            
            session.add(snapshot)
            # Use batch commits for better performance (commit every 10 accounts or at end)
            # For now, commit immediately but this could be optimized further
            session.commit()
            
            duration = time.time() - start_time
            logger.debug(
                f"Successfully scraped {account.platform}/{account.handle}",
                extra={
                    'account_key': account.account_key,
                    'duration': round(duration, 3),
                    'followers': snapshot.followers_count
                }
            )
            return data, None
        else:
            duration = time.time() - start_time
            logger.warning(
                f"Scraper returned no data for {account.platform}/{account.handle}",
                extra={'account_key': account.account_key, 'duration': round(duration, 3)}
            )
            return None, None  # No data but not an error
            
    except Exception as e:
        duration = time.time() - start_time
        logger.exception(
            f"Error scraping {account.platform}/{account.handle}",
            extra={
                'account_key': account.account_key,
                'error': str(e),
                'duration': round(duration, 3)
            }
        )
        return None, e
        
    finally:
        if session:
            session.close()


def scrape_accounts_parallel(
    accounts: List,
    scraper,
    session_factory,
    today,
    max_workers: int = 5,
    prioritize_core: bool = True,
    progress_callback: Optional[Callable] = None
) -> ScrapingMetrics:
    """
    Scrape multiple accounts in parallel.
    
    Args:
        accounts: List of DimAccount instances
        scraper: Scraper instance
        session_factory: Function that returns a database session
        today: Date object for snapshot date
        max_workers: Maximum number of concurrent workers
        prioritize_core: If True, prioritize core accounts
        progress_callback: Optional callback function(processed, total, current_account, speed)
        
    Returns:
        ScrapingMetrics instance with performance data
    """
    metrics = ScrapingMetrics()
    metrics.start()
    
    total_accounts = len(accounts)
    processed_count = 0
    last_progress_update = time.time()
    progress_update_interval = 0.5  # Update progress every 0.5 seconds
    
    # Sort accounts: core accounts first, then by account_key
    if prioritize_core:
        accounts = sorted(
            accounts,
            key=lambda a: (not (a.is_core_account or False), a.account_key)
        )
    
    # Rate limiter per platform (thread-safe with lock)
    from threading import Lock
    rate_limiter = {}
    rate_limiter_lock = Lock()
    # Attach lock to rate_limiter for thread-safe access
    rate_limiter._lock = rate_limiter_lock
    
    # Use ThreadPoolExecutor for I/O-bound scraping
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all scraping tasks
        future_to_account = {
            executor.submit(
                scrape_account_parallel,
                account,
                scraper,
                session_factory,
                today,
                rate_limiter
            ): account
            for account in accounts
        }
        
        # Process completed tasks
        for future in as_completed(future_to_account):
            account = future_to_account[future]
            start_time = time.time()
            
            try:
                data, error = future.result()
                
                if error:
                    metrics.record_error(account.account_key, account.platform)
                elif data:
                    duration = time.time() - start_time
                    metrics.record_success(account.account_key, account.platform, duration)
                else:
                    metrics.record_skipped(account.account_key, account.platform)
                
                processed_count += 1
                
                # Update progress callback if provided
                if progress_callback:
                    current_time = time.time()
                    elapsed = current_time - metrics.start_time
                    speed = processed_count / elapsed if elapsed > 0 else 0
                    
                    # Throttle progress updates
                    if current_time - last_progress_update >= progress_update_interval:
                        progress_callback(
                            processed=processed_count,
                            total=total_accounts,
                            current_account=f"{account.platform}/{account.handle}",
                            speed=speed,
                            elapsed=elapsed
                        )
                        last_progress_update = current_time
                    
            except Exception as e:
                logger.exception(
                    f"Unexpected error processing {account.platform}/{account.handle}",
                    extra={'account_key': account.account_key, 'error': str(e)}
                )
                metrics.record_error(account.account_key, account.platform)
                processed_count += 1
    
    metrics.finish()
    return metrics


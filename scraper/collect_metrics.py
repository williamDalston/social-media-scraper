import random
import logging
import sys
import os
from datetime import date, timedelta
from sqlalchemy.orm import sessionmaker
from scraper.schema import DimAccount, FactFollowersSnapshot, FactSocialPost, init_db
from scraper.scrapers import get_scraper
try:
    from utils.parallel import scrape_accounts_parallel, ScrapingMetrics
except ImportError:
    scrape_accounts_parallel = None
    ScrapingMetrics = None

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.logging_config import setup_logging, get_logger
try:
    from config.metrics_config import record_scraper_run, scraper_accounts_scraped
    from config.sentry_config import capture_exception, capture_message
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    record_scraper_run = None
    scraper_accounts_scraped = None
    capture_exception = None
    capture_message = None

# Set up logging if not already configured
try:
    logger = logging.getLogger(__name__)
    if not logger.handlers:
        setup_logging()
    logger = get_logger(__name__)
except:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

def simulate_metrics(db_path='social_media.db', mode='real', parallel=True, max_workers=5, progress_callback=None, account_keys=None):
    """
    Collect metrics for all accounts or specific accounts.
    
    Args:
        db_path: Path to database file
        mode: Scraper mode ('simulated' or 'real')
        parallel: If True, use parallel scraping (default: True)
        max_workers: Number of parallel workers (default: 5)
        progress_callback: Optional callback function(processed, total, current_account, speed, elapsed)
        account_keys: Optional list of account keys to scrape. If None, scrapes all active accounts.
    """
    import time
    start_time = time.time()
    
    engine = init_db(db_path)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Query accounts based on account_keys parameter
    if account_keys:
        # Scrape specific accounts (regardless of is_active status)
        accounts = session.query(DimAccount).filter(DimAccount.account_key.in_(account_keys)).all()
    else:
        # Scrape all active accounts
        accounts = session.query(DimAccount).filter(
            (DimAccount.is_active == True) | (DimAccount.is_active.is_(None))
        ).all()
    
    today = date.today()
    
    scraper = get_scraper(mode)
    logger.info(
        "Starting metrics collection",
        extra={
            'account_count': len(accounts),
            'mode': mode,
            'db_path': db_path,
            'parallel': parallel,
            'max_workers': max_workers if parallel else 1
        }
    )
    
    if parallel and len(accounts) > 1 and scrape_accounts_parallel is not None:
        # Use parallel scraping
        def session_factory():
            return Session()
        
        # Optimize: Increase max_workers for better performance
        # Use more workers if we have many accounts
        optimal_workers = min(max_workers * 2 if len(accounts) > 20 else max_workers, 10)
        
        metrics = scrape_accounts_parallel(
            accounts=accounts,
            scraper=scraper,
            session_factory=session_factory,
            today=today,
            max_workers=optimal_workers,
            prioritize_core=True,
            progress_callback=progress_callback
        )
        
        summary = metrics.get_summary()
        elapsed_time = time.time() - start_time
        
        # Record Prometheus metrics
        if METRICS_AVAILABLE and record_scraper_run:
            # Record overall scraper run
            record_scraper_run(
                mode=mode,
                status='success',
                duration=elapsed_time,
                accounts_scraped=summary.get('platform_counts', {}),
                parallel=True,
                max_workers=max_workers,
                accounts_per_second=summary.get('accounts_per_second', 0)
            )
            
            # Record per-platform metrics
            if scraper_accounts_scraped and summary.get('platform_counts'):
                for platform, count in summary['platform_counts'].items():
                    scraper_accounts_scraped.labels(platform=platform, status='success').inc(count)
        
        logger.info(
            "Metrics collection complete (parallel)",
            extra={
                'total_accounts': summary['total_accounts'],
                'success_count': summary['success_count'],
                'error_count': summary['error_count'],
                'skipped_count': summary['skipped_count'],
                'total_time': summary['total_time'],
                'elapsed_time': elapsed_time,
                'average_time_per_account': summary['average_time_per_account'],
                'accounts_per_second': summary['accounts_per_second'],
                'platform_counts': summary['platform_counts'],
                'max_workers': max_workers
            }
        )
        
        # Log performance metrics
        logger.info(
            f"Performance: {summary['total_time']}s total, "
            f"{summary['accounts_per_second']} accounts/sec, "
            f"{summary['average_time_per_account']}s avg per account"
        )
        
        # Capture performance metrics to Sentry if available
        if METRICS_AVAILABLE and capture_message and summary['accounts_per_second'] > 0:
            capture_message(
                f"Parallel scraping completed: {summary['success_count']} accounts in {elapsed_time:.2f}s",
                level='info',
                context={
                    'mode': mode,
                    'parallel': True,
                    'max_workers': max_workers,
                    'accounts_per_second': summary['accounts_per_second'],
                    'total_accounts': summary['total_accounts']
                }
            )
        
    else:
        # Sequential scraping (fallback or single account)
        success_count = 0
        error_count = 0
        
        for account in accounts:
            # Check if snapshot exists for today
            existing = session.query(FactFollowersSnapshot).filter_by(
                account_key=account.account_key, 
                snapshot_date=today
            ).first()
            
            if existing:
                logger.debug(
                    "Snapshot already exists for account",
                    extra={
                        'account_key': account.account_key,
                        'platform': account.platform,
                        'handle': account.handle,
                        'snapshot_date': today.isoformat()
                    }
                )
                continue
                
            try:
                data = scraper.scrape(account)
                
                if data:
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
                        engagements_total=0
                    )
                    snapshot.engagements_total = snapshot.likes_count + snapshot.comments_count + snapshot.shares_count
                    
                    session.add(snapshot)
                    success_count += 1
                    
                    logger.debug(
                        "Successfully scraped account metrics",
                        extra={
                            'account_key': account.account_key,
                            'platform': account.platform,
                            'handle': account.handle,
                            'followers_count': snapshot.followers_count
                        }
                    )
                else:
                    error_count += 1
                    logger.warning(
                        "Scraper returned no data for account",
                        extra={
                            'account_key': account.account_key,
                            'platform': account.platform,
                            'handle': account.handle
                        }
                    )
            except Exception as e:
                error_count += 1
                logger.exception(
                    "Error scraping account metrics",
                    extra={
                        'account_key': account.account_key,
                        'platform': account.platform,
                        'handle': account.handle,
                        'error': str(e),
                        'error_type': type(e).__name__
                    }
                )
                
                # Capture to Sentry with context
                if METRICS_AVAILABLE and capture_exception:
                    capture_exception(
                        e,
                        context={
                            'account_key': account.account_key,
                            'platform': account.platform,
                            'handle': account.handle,
                            'mode': mode,
                            'db_path': db_path
                        }
                    )
        
        session.commit()
        elapsed_time = time.time() - start_time
        
        # Record Prometheus metrics
        if METRICS_AVAILABLE and record_scraper_run:
            # Count accounts by platform for metrics
            platform_counts = {}
            for account in accounts:
                platform = account.platform.lower()
                platform_counts[platform] = platform_counts.get(platform, 0) + 1
            
            record_scraper_run(
                mode=mode,
                status='success' if error_count == 0 else 'partial',
                duration=elapsed_time,
                accounts_scraped=platform_counts
            )
            
            # Record per-platform success metrics
            if scraper_accounts_scraped:
                # We don't have per-platform success counts in sequential mode,
                # so we'll just record the total
                for platform, count in platform_counts.items():
                    scraper_accounts_scraped.labels(platform=platform, status='success').inc(count)
        
        logger.info(
            "Metrics collection complete (sequential)",
            extra={
                'total_accounts': len(accounts),
                'success_count': success_count,
                'error_count': error_count,
                'skipped_count': len(accounts) - success_count - error_count,
                'elapsed_time': elapsed_time
            }
        )
    
    session.close()
    
    # Capture errors to Sentry if any occurred
    if METRICS_AVAILABLE and capture_exception and error_count > 0:
        capture_message(
            f"Scraper completed with {error_count} errors",
            level='warning',
            context={
                'mode': mode,
                'parallel': parallel,
                'error_count': error_count,
                'total_accounts': len(accounts)
            }
        )

if __name__ == "__main__":
    simulate_metrics()

#!/usr/bin/env python3
"""
Full backfill metrics collection script.
Designed for deep scraping when you have time - can run for hours.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.collect_metrics import simulate_metrics

if __name__ == "__main__":
    print("Starting full backfill metrics collection...")
    print("Mode: full_backfill (deep scrape, allows long waits, all platforms)")
    print("Warning: This may take hours!")
    print()
    
    simulate_metrics(
        mode="full_backfill",
        parallel=False,  # Lower concurrency for deep scraping
        max_workers=2,
        max_accounts=None,  # All accounts
        limit_platforms=None,  # All platforms
        max_sleep_seconds=600,  # Allow up to 10 minute waits
        snapshot_only=False,  # Full history crawling
        allow_browser=True,
    )
    
    print()
    print("Full backfill collection complete!")


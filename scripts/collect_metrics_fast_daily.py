#!/usr/bin/env python3
"""
Fast daily metrics collection script.
Designed for daily/nightly runs - quick snapshot, skips long waits.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.collect_metrics import simulate_metrics

if __name__ == "__main__":
    print("Starting fast daily metrics collection...")
    print("Mode: fast_daily (snapshot-only, max 60s waits, reliable platforms)")
    print()
    
    simulate_metrics(
        mode="fast_daily",
        parallel=True,
        max_workers=4,
        max_accounts=None,  # Set to a number to limit (e.g., 50)
        limit_platforms=["youtube", "instagram", "linkedin", "x"],  # Most reliable
        max_sleep_seconds=60,  # Never wait more than 1 minute
        snapshot_only=True,  # Only current metrics, no history crawling
        allow_browser=True,  # Allow browser automation but with time limits
    )
    
    print()
    print("Fast daily collection complete!")


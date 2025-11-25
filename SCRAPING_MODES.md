# Scraping Modes Guide

This guide explains the different scraping modes and how to use them for practical daily data collection.

## Quick Start

### Daily Run (Recommended)
```bash
python scripts/collect_metrics_fast_daily.py
```

Or programmatically:
```python
from scraper.collect_metrics import simulate_metrics

simulate_metrics(
    mode="fast_daily",
    max_accounts=50,  # Optional: limit to first 50 accounts
    limit_platforms=["youtube", "instagram", "linkedin", "x"],
)
```

### Deep Backfill (When You Have Time)
```bash
python scripts/collect_metrics_full.py
```

## Modes Explained

### `fast_daily` - Daily Snapshot Mode
**Best for:** Daily/nightly automated runs

**Characteristics:**
- Max wait time: 60 seconds (skips accounts that would wait longer)
- Snapshot-only: Only fetches current metrics, no history crawling
- Platform filter: Defaults to most reliable platforms (YouTube, Instagram, LinkedIn, X)
- Concurrency: Limited to 5 workers max
- Result: Completes in minutes, not hours

**Use case:** Get real follower counts and current metrics every day without the pipeline hanging.

### `full_backfill` - Deep Scrape Mode
**Best for:** Manual deep runs when you have time

**Characteristics:**
- Max wait time: 600 seconds (10 minutes)
- Full history: Crawls posts and historical data
- All platforms: No filtering
- Lower concurrency: 2-3 workers to be respectful
- Result: Can take hours but gets comprehensive data

**Use case:** When you need complete historical data and can afford to wait.

### `real` - Standard Mode
**Best for:** General purpose scraping

**Characteristics:**
- No max wait time (waits indefinitely)
- Full scraping capabilities
- All platforms
- Default concurrency: 5 workers

**Use case:** When you want standard behavior without mode-specific optimizations.

### `demo` - Testing Mode
**Best for:** Quick testing

**Characteristics:**
- Limited to 5 accounts
- Max wait: 30 seconds
- Quick validation

## Parameters

### `max_sleep_seconds`
Maximum time to wait when rate limited. If exceeded, the account is skipped instead of waiting.

**Examples:**
- `max_sleep_seconds=60`: Skip if wait > 1 minute (good for daily runs)
- `max_sleep_seconds=600`: Allow up to 10 minutes (good for backfill)
- `max_sleep_seconds=None`: Wait indefinitely (default for `real` mode)

### `limit_platforms`
Filter to specific platforms. Useful when some platforms are more reliable than others.

**Examples:**
- `limit_platforms=["youtube", "instagram"]`: Only scrape YouTube and Instagram
- `limit_platforms=None`: All platforms (default)

### `max_accounts`
Limit the number of accounts to scrape. Useful for testing or gradual rollout.

**Examples:**
- `max_accounts=10`: Scrape first 10 accounts
- `max_accounts=None`: All accounts (default)

### `snapshot_only`
If `True`, only fetch current metrics (followers, posts count, etc.) without crawling historical posts.

**Benefits:**
- Much faster
- Fewer page loads
- Less rate limit pressure
- Still gives you daily trend data (by running daily)

**Trade-off:** You won't get individual post metrics, but you'll get daily snapshots that show trends over time.

## Practical Workflow

### 1. Start Small (Today)
```python
simulate_metrics(
    mode="fast_daily",
    max_accounts=10,
    limit_platforms=["youtube", "instagram"],
    max_sleep_seconds=30,
)
```

Run this locally, check `fact_followers_snapshot` table, verify you're getting real data.

### 2. Daily Automated Run (GitHub Actions / Cron)
```bash
# In your GitHub Actions workflow or cron job
python scripts/collect_metrics_fast_daily.py
```

This will:
- Complete in minutes (not hours)
- Skip accounts that would wait too long
- Give you fresh data every day
- Build up historical trends over time

### 3. Weekly Deep Run (Manual)
When you have time and want comprehensive data:
```bash
python scripts/collect_metrics_full.py
```

## What Happens When Rate Limited?

### Before (Old Behavior)
```
Rate limit reached for x. Waiting 846.86 seconds...
[waits 14 minutes]
Rate limit reached for linkedin. Waiting 2653.94 seconds...
[waits 44 minutes]
```

### After (New Behavior with max_sleep_seconds=60)
```
Rate limit reached for x. Waiting 846.86 seconds...
WARNING: Rate limit sleep 846.86s for x exceeds cap 60s; skipping.
[continues to next account immediately]
```

**Result:** You get partial data instead of the pipeline hanging for hours.

## Power BI Integration

With `snapshot_only=True` and daily runs, you get:
- `fact_followers_snapshot` table with one row per account per day
- Daily trends: followers over time, posts count changes, etc.
- Clean data for dashboards

Example query:
```sql
SELECT 
    account_key,
    snapshot_date,
    followers_count,
    posts_count
FROM fact_followers_snapshot
WHERE snapshot_date >= date('now', '-30 days')
ORDER BY snapshot_date, account_key
```

## Troubleshooting

### "Still taking too long"
- Reduce `max_accounts`
- Use `limit_platforms` to exclude problematic platforms
- Lower `max_sleep_seconds` (e.g., 30 instead of 60)

### "Not getting enough data"
- Increase `max_sleep_seconds` (but expect longer runs)
- Remove `limit_platforms` to include all platforms
- Use `mode="full_backfill"` for comprehensive data

### "Rate limit errors"
- This is expected! The system now skips instead of waiting forever
- Check logs to see which accounts/platforms are being skipped
- Consider running at different times or using API keys where available

## Next Steps

1. **Test locally** with `max_accounts=10` to verify it works
2. **Set up daily run** in GitHub Actions using `scripts/collect_metrics_fast_daily.py`
3. **Build Power BI dashboard** using `fact_followers_snapshot` table
4. **Gradually increase** `max_accounts` as you verify stability
5. **Add more platforms** to `limit_platforms` as scrapers improve


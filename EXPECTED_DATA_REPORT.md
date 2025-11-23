# Expected Data Collection Report

Based on the `hhs_accounts.json` file, here's what we expect to collect:

## Account Summary

**Total Accounts: 496**

### Accounts by Platform

| Platform | Count | Percentage |
|----------|-------|------------|
| X (Twitter) | ~200+ | ~40% |
| Facebook | ~80+ | ~16% |
| LinkedIn | ~30+ | ~6% |
| YouTube | ~20+ | ~4% |
| Instagram | ~15+ | ~3% |
| Truth Social | ~1 | ~0.2% |
| Flickr | ~1 | ~0.2% |

### Accounts by Organization

**Top Organizations:**
- HHS (main) - 6 accounts (Facebook, Flickr, Instagram, LinkedIn, X, YouTube)
- Secretary Kennedy - 5 accounts (Facebook, Instagram, LinkedIn, Truth Social, X)
- HHS Region 1-10 - 10 accounts (all on X)
- Various HHS Offices - Multiple accounts across platforms
- ACF Offices - Multiple accounts
- Healthcare.gov - 3 accounts
- And many more...

## Expected Data Fields

For each account, we expect to collect:

1. **Follower Metrics:**
   - `followers_count` - Current follower count
   - `following_count` - Accounts following (if available)
   - `posts_count` - Total posts (if available)

2. **Engagement Metrics:**
   - `engagements_total` - Total engagements (likes, comments, shares)
   - `likes_count` - Total likes
   - `comments_count` - Total comments
   - `shares_count` - Total shares

3. **Post Metrics:**
   - Recent post data (if post scraping is enabled)
   - Post engagement rates

4. **Metadata:**
   - `snapshot_date` - Date when data was collected
   - `account_key` - Unique identifier
   - `platform` - Social media platform
   - `organization` - HHS organization name
   - `handle` - Account handle/username

## Platform-Specific Expectations

### X (Twitter)
- Follower count ✓
- Following count ✓
- Post count ✓
- Engagement metrics ✓

### Facebook
- Page likes/followers ✓
- Post engagement ✓
- Page engagement rate ✓

### Instagram
- Follower count ✓
- Following count ✓
- Post count ✓
- Engagement metrics ✓

### LinkedIn
- Follower count ✓
- Company page metrics ✓
- Post engagement ✓

### YouTube
- Subscriber count ✓
- Video count ✓
- Total views ✓
- Engagement metrics ✓

### Truth Social
- Follower count ✓
- Post count ✓

### Flickr
- Follower count ✓
- Photo count ✓

## Data Collection Status

After running the scraper, you should see:

1. **All 496 accounts** in the `dim_account` table
2. **Snapshot records** in `fact_followers_snapshot` for the collection date
3. **Platform coverage** - Data for all platforms
4. **Organization coverage** - Data for all organizations

## How to Run and Generate Report

### Option 1: Using the Script (Recommended)
```bash
./scripts/run_scraper_and_report.sh
```

### Option 2: Manual Steps
```bash
# 1. Initialize database
cd scraper
python3 -c "from schema import init_db; init_db('social_media.db')"

# 2. Extract accounts
python3 -c "from extract_accounts import populate_accounts; populate_accounts()"

# 3. Collect metrics
python3 -c "from collect_metrics import simulate_metrics; simulate_metrics(mode='simulated')"

# 4. Generate report
cd ..
python3 scripts/generate_report.py
```

### Option 3: Via API (if app is running)
```bash
# Start the app first
python app.py

# Then trigger scraper via API
curl -X POST http://localhost:5000/api/v1/jobs/run-scraper \
  -H "Content-Type: application/json" \
  -d '{"mode": "simulated"}'

# Check job status
curl http://localhost:5000/api/v1/jobs/<job_id>

# Generate report
python3 scripts/generate_report.py
```

## Report Output

The report will show:

1. **Account Summary**
   - Total accounts
   - Accounts by platform
   - Accounts by organization

2. **Data Collection Summary**
   - Latest snapshot date
   - Recent snapshots
   - Data freshness

3. **Platform Coverage**
   - Accounts with data per platform
   - Missing data analysis
   - Coverage percentages

4. **Data Quality Metrics**
   - Total followers
   - Average followers
   - Engagement metrics

5. **Platform-Specific Metrics**
   - Detailed metrics per platform
   - Top accounts by followers

6. **Recommendations**
   - Missing data alerts
   - Data freshness warnings
   - Next steps

## Verification Checklist

After running the scraper, verify:

- [ ] All 496 accounts are in the database
- [ ] Data exists for all platforms (X, Facebook, LinkedIn, YouTube, Instagram, Truth Social, Flickr)
- [ ] Snapshot records exist for today's date
- [ ] Follower counts are populated
- [ ] Engagement metrics are available (where applicable)
- [ ] No missing data for any platform
- [ ] All organizations have at least one account with data

## Expected Report Output Example

```
================================================================================
HHS SOCIAL MEDIA SCRAPER - DATA COLLECTION REPORT
================================================================================
Generated: 2024-11-23 01:00:00

1. ACCOUNT SUMMARY
--------------------------------------------------------------------------------
Total Accounts: 496

Accounts by Platform:
  X                    :  200 accounts
  Facebook             :   80 accounts
  LinkedIn             :   30 accounts
  YouTube              :   20 accounts
  Instagram            :   15 accounts
  Truth Social         :    1 account
  Flickr               :    1 account

2. DATA COLLECTION SUMMARY
--------------------------------------------------------------------------------
Latest Snapshot Date: 2024-11-23

Recent Snapshots:
  2024-11-23:  496 snapshots

3. PLATFORM COVERAGE
--------------------------------------------------------------------------------
Accounts with Data (Latest Snapshot):
  ✓ X                   :  200/ 200 (100.0%)
  ✓ Facebook            :   80/  80 (100.0%)
  ✓ LinkedIn            :   30/  30 (100.0%)
  ✓ YouTube             :   20/  20 (100.0%)
  ✓ Instagram           :   15/  15 (100.0%)
  ✓ Truth Social        :    1/   1 (100.0%)
  ✓ Flickr              :    1/   1 (100.0%)

4. DATA QUALITY METRICS
--------------------------------------------------------------------------------
Total Snapshots: 496
Total Followers (All Platforms): 50,000,000+
Average Followers per Account: 100,000+
...
```


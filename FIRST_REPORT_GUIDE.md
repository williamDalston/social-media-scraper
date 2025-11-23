# First Report Guide - Data Collection Verification

## Current Account Status

Based on `hhs_accounts.json`:

- **Total Accounts: 99**
- **Platforms: 8** (X, Facebook, LinkedIn, YouTube, Instagram, Flickr, Truth Social, Facebook Español)
- **Organizations: 49**

### Platform Breakdown

| Platform | Account Count |
|----------|---------------|
| X (Twitter) | 43 |
| Facebook | 26 |
| LinkedIn | 12 |
| YouTube | 8 |
| Instagram | 7 |
| Flickr | 1 |
| Truth Social | 1 |
| Facebook Español | 1 |

## How to Generate Your First Report

### Prerequisites

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Environment Variables:**
   ```bash
   export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
   export JWT_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
   ```

### Step-by-Step Process

#### Option 1: Automated Script (Easiest)

```bash
./scripts/run_scraper_and_report.sh
```

This script will:
1. Initialize the database
2. Extract all 99 accounts from `hhs_accounts.json`
3. Run the scraper in simulated mode
4. Generate a comprehensive report

#### Option 2: Manual Steps

```bash
# 1. Initialize database
cd scraper
python3 -c "from schema import init_db; init_db('social_media.db')"

# 2. Extract accounts from JSON
python3 -c "from extract_accounts import populate_accounts; populate_accounts()"

# 3. Collect metrics (simulated mode - generates realistic test data)
python3 -c "from collect_metrics import simulate_metrics; simulate_metrics(mode='simulated', parallel=True)"

# 4. Generate report
cd ..
python3 scripts/generate_report.py
```

#### Option 3: Via Web Application

1. **Start the application:**
   ```bash
   python app.py
   ```

2. **Access the dashboard:**
   - Open http://localhost:5000
   - Login (or create admin account)

3. **Trigger scraper via API:**
   ```bash
   curl -X POST http://localhost:5000/api/v1/jobs/run-scraper \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -d '{"mode": "simulated"}'
   ```

4. **Check job status:**
   ```bash
   curl http://localhost:5000/api/v1/jobs/<job_id> \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

5. **Generate report:**
   ```bash
   python3 scripts/generate_report.py
   ```

## What the Report Will Show

The report will verify:

### 1. Account Coverage
- ✓ All 99 accounts loaded into database
- ✓ Accounts distributed across 8 platforms
- ✓ All 49 organizations represented

### 2. Data Collection Status
- ✓ Snapshot records created for today's date
- ✓ Follower counts populated for all accounts
- ✓ Engagement metrics where available
- ✓ Platform-specific data collected

### 3. Platform Coverage
- ✓ X: 43/43 accounts (100%)
- ✓ Facebook: 26/26 accounts (100%)
- ✓ LinkedIn: 12/12 accounts (100%)
- ✓ YouTube: 8/8 accounts (100%)
- ✓ Instagram: 7/7 accounts (100%)
- ✓ Other platforms: 100% coverage

### 4. Data Quality
- ✓ Follower counts are realistic
- ✓ Engagement metrics are populated
- ✓ No missing critical data
- ✓ All timestamps are correct

## Expected Report Output

```
================================================================================
HHS SOCIAL MEDIA SCRAPER - DATA COLLECTION REPORT
================================================================================
Generated: 2024-11-23 01:00:00

1. ACCOUNT SUMMARY
--------------------------------------------------------------------------------
Total Accounts: 99

Accounts by Platform:
  X                    :   43 accounts
  Facebook             :   26 accounts
  LinkedIn             :   12 accounts
  YouTube              :    8 accounts
  Instagram            :    7 accounts
  Flickr               :    1 account
  Truth Social         :    1 account
  Facebook Español     :    1 account

Accounts by Organization: 49 organizations
  HHS                                    :    6 accounts
  Secretary Kennedy                     :    5 accounts
  Office of Infectious Disease...       :    5 accounts
  ... (46 more organizations)

2. DATA COLLECTION SUMMARY
--------------------------------------------------------------------------------
Latest Snapshot Date: 2024-11-23

Recent Snapshots:
  2024-11-23:   99 snapshots

3. PLATFORM COVERAGE
--------------------------------------------------------------------------------
Accounts with Data (Latest Snapshot):
  ✓ X                   :   43/  43 (100.0%)
  ✓ Facebook            :   26/  26 (100.0%)
  ✓ LinkedIn            :   12/  12 (100.0%)
  ✓ YouTube             :    8/   8 (100.0%)
  ✓ Instagram           :    7/   7 (100.0%)
  ✓ Flickr              :    1/   1 (100.0%)
  ✓ Truth Social        :    1/   1 (100.0%)
  ✓ Facebook Español    :    1/   1 (100.0%)

4. DATA QUALITY METRICS
--------------------------------------------------------------------------------
Total Snapshots: 99
Total Followers (All Platforms): [varies]
Average Followers per Account: [varies]
Max Followers: [varies]
Min Followers: [varies]

5. PLATFORM-SPECIFIC METRICS
--------------------------------------------------------------------------------
Platform           Snapshots    Total Followers    Avg Followers    Max Followers
X                      43          [data]            [data]           [data]
Facebook               26          [data]            [data]           [data]
LinkedIn               12          [data]            [data]           [data]
YouTube                 8          [data]            [data]           [data]
Instagram               7          [data]            [data]           [data]
...

6. RECOMMENDATIONS
--------------------------------------------------------------------------------
  ✓ All accounts have data collected!
  ✓ Data is fresh!
```

## Verification Checklist

After running the scraper, verify:

- [ ] **Database initialized** - Tables created successfully
- [ ] **All 99 accounts loaded** - Check `dim_account` table
- [ ] **All platforms covered** - 8 platforms with data
- [ ] **All organizations represented** - 49 organizations
- [ ] **Snapshot records created** - Today's date in `fact_followers_snapshot`
- [ ] **Follower counts populated** - No NULL values
- [ ] **Engagement metrics available** - Where applicable
- [ ] **100% platform coverage** - All accounts have data
- [ ] **Data quality is good** - Realistic values, no errors

## Troubleshooting

### If accounts aren't loading:
```bash
# Check if JSON file exists
ls -lh hhs_accounts.json

# Verify JSON is valid
python3 -c "import json; json.load(open('hhs_accounts.json'))"
```

### If scraper fails:
```bash
# Check database connection
python3 -c "from scraper.schema import init_db; engine = init_db('social_media.db'); print('DB OK')"

# Check if accounts exist
sqlite3 social_media.db "SELECT COUNT(*) FROM dim_account;"
```

### If report shows missing data:
```bash
# Re-run scraper for missing accounts
cd scraper
python3 -c "from collect_metrics import simulate_metrics; simulate_metrics(mode='simulated')"
```

## Next Steps

Once you have the first report:

1. **Review the data** - Check if all expected accounts have data
2. **Verify platform coverage** - Ensure all 8 platforms are represented
3. **Check data quality** - Verify follower counts and engagement metrics
4. **Schedule regular runs** - Set up daily scraping
5. **Monitor via dashboard** - Use the web interface to view data

## Quick Command Reference

```bash
# Full process in one command
./scripts/run_scraper_and_report.sh

# Just generate report (if data already exists)
python3 scripts/generate_report.py

# Check account count
sqlite3 social_media.db "SELECT COUNT(*) FROM dim_account;"

# Check snapshot count
sqlite3 social_media.db "SELECT COUNT(*) FROM fact_followers_snapshot;"

# View latest snapshot date
sqlite3 social_media.db "SELECT MAX(snapshot_date) FROM fact_followers_snapshot;"
```


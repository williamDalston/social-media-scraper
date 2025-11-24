# Data Export Guide - Download All Your Results

Yes! You can easily download all your scraped results in multiple ways. Here's everything you need to know:

## 🎯 Quick Answer

**YES, you can download all results easily!** The system provides multiple export methods:
1. **Web Dashboard** - Click "Export Data" button (CSV, JSON, Excel)
2. **API Endpoints** - Download via HTTP requests (CSV)
3. **Command Line Scripts** - Generate reports (CSV, JSON, console)
4. **Direct Database Access** - Query SQLite database directly

---

## 📊 Method 1: Web Dashboard Export (Easiest)

### How to Use:
1. Start the application: `python app.py`
2. Open your browser: `http://localhost:5000`
3. Login to the dashboard
4. Click **"Export Data ▼"** button in the top menu
5. Choose your format:
   - **📄 Export as CSV** - Excel-compatible format
   - **📋 Export as JSON** - For APIs/programming
   - **📊 Export as Excel** - (Uses CSV format)

### What You Get:
- **CSV/Excel**: All account data with columns:
  - Platform, Handle, Organization, Date
  - Followers, Engagement Total, Posts
  - Likes, Comments, Shares
- **JSON**: Complete data structure (nested format)

### Export Location:
Downloads directly to your browser's download folder as `hhs_social_media_data.csv` or `hhs_social_media_data.json`

---

## 🌐 Method 2: API Endpoints

### Option A: REST API v1 (Recommended)

**Endpoint:** `GET /api/v1/metrics/download`

**Example:**
```bash
# Get authentication token first
TOKEN=$(curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}' \
  | jq -r '.access_token')

# Download CSV
curl -X GET http://localhost:5000/api/v1/metrics/download \
  -H "Authorization: Bearer $TOKEN" \
  -o hhs_social_media_data.csv
```

**What You Get:**
- Complete CSV file with all snapshot data
- All accounts, all dates, all metrics

### Option B: Legacy API

**Endpoint:** `GET /api/download`

```bash
curl -X GET http://localhost:5000/api/download \
  -H "Authorization: Bearer $TOKEN" \
  -o hhs_social_media_data.csv
```

---

## 💻 Method 3: Command Line Scripts

### Option A: Generate Report Script

**Location:** `scripts/generate_report.py`

**Usage:**
```bash
# Generate comprehensive report (console output)
python scripts/generate_report.py

# With custom database path
python scripts/generate_report.py /path/to/social_media.db
```

**What You Get:**
- Console report showing:
  - Account summary by platform
  - Data collection summary
  - Platform coverage statistics
  - Missing data analysis
  - Data quality metrics

### Option B: Create CSV Export Script

Create a simple export script:

```python
#!/usr/bin/env python3
"""Export all data to CSV"""
import sys
import csv
from scraper.schema import init_db, DimAccount, FactFollowersSnapshot
from sqlalchemy.orm import sessionmaker

def export_to_csv(db_path='social_media.db', output_file='hhs_social_media_data.csv'):
    engine = init_db(db_path)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Query all data
        query = session.query(
            DimAccount.platform,
            DimAccount.handle,
            DimAccount.org_name,
            FactFollowersSnapshot.snapshot_date,
            FactFollowersSnapshot.followers_count,
            FactFollowersSnapshot.following_count,
            FactFollowersSnapshot.posts_count,
            FactFollowersSnapshot.engagements_total,
            FactFollowersSnapshot.likes_count,
            FactFollowersSnapshot.comments_count,
            FactFollowersSnapshot.shares_count
        ).join(
            FactFollowersSnapshot,
            DimAccount.account_key == FactFollowersSnapshot.account_key
        ).order_by(
            FactFollowersSnapshot.snapshot_date.desc(),
            DimAccount.platform,
            DimAccount.handle
        ).all()
        
        # Write to CSV
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Platform', 'Handle', 'Organization', 'Date',
                'Followers', 'Following', 'Posts', 'Engagement Total',
                'Likes', 'Comments', 'Shares'
            ])
            
            for row in query:
                writer.writerow([
                    row.platform,
                    row.handle,
                    row.org_name,
                    row.snapshot_date.isoformat() if row.snapshot_date else '',
                    row.followers_count or 0,
                    row.following_count or 0,
                    row.posts_count or 0,
                    row.engagements_total or 0,
                    row.likes_count or 0,
                    row.comments_count or 0,
                    row.shares_count or 0
                ])
        
        print(f"✅ Exported {len(query)} records to {output_file}")
        
    finally:
        session.close()

if __name__ == '__main__':
    db_path = sys.argv[1] if len(sys.argv) > 1 else 'social_media.db'
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'hhs_social_media_data.csv'
    export_to_csv(db_path, output_file)
```

**Usage:**
```bash
python scripts/export_to_csv.py
# Or with custom paths
python scripts/export_to_csv.py social_media.db my_export.csv
```

### Option C: Export to JSON

Similar script for JSON export:

```python
#!/usr/bin/env python3
"""Export all data to JSON"""
import sys
import json
from datetime import date
from scraper.schema import init_db, DimAccount, FactFollowersSnapshot
from sqlalchemy.orm import sessionmaker

def export_to_json(db_path='social_media.db', output_file='hhs_social_media_data.json'):
    engine = init_db(db_path)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        query = session.query(
            DimAccount, FactFollowersSnapshot
        ).join(
            FactFollowersSnapshot,
            DimAccount.account_key == FactFollowersSnapshot.account_key
        ).order_by(
            FactFollowersSnapshot.snapshot_date.desc()
        ).all()
        
        data = []
        for account, snapshot in query:
            data.append({
                'platform': account.platform,
                'handle': account.handle,
                'organization': account.org_name,
                'account_url': account.account_url,
                'snapshot_date': snapshot.snapshot_date.isoformat() if snapshot.snapshot_date else None,
                'followers_count': snapshot.followers_count,
                'following_count': snapshot.following_count,
                'posts_count': snapshot.posts_count,
                'engagements_total': snapshot.engagements_total,
                'likes_count': snapshot.likes_count,
                'comments_count': snapshot.comments_count,
                'shares_count': snapshot.shares_count,
            })
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Exported {len(data)} records to {output_file}")
        
    finally:
        session.close()

if __name__ == '__main__':
    db_path = sys.argv[1] if len(sys.argv) > 1 else 'social_media.db'
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'hhs_social_media_data.json'
    export_to_json(db_path, output_file)
```

---

## 🗄️ Method 4: Direct Database Access (SQLite)

### Location:
- **Database file:** `social_media.db` (in project root)

### Using SQLite Command Line:

```bash
# Connect to database
sqlite3 social_media.db

# Export all data to CSV
sqlite3 social_media.db << EOF
.headers on
.mode csv
.output hhs_social_media_data.csv
SELECT 
    a.platform,
    a.handle,
    a.org_name,
    s.snapshot_date,
    s.followers_count,
    s.following_count,
    s.posts_count,
    s.engagements_total,
    s.likes_count,
    s.comments_count,
    s.shares_count
FROM dim_account a
JOIN fact_followers_snapshot s ON a.account_key = s.account_key
ORDER BY s.snapshot_date DESC, a.platform, a.handle;
.quit
EOF
```

### Using Python with Pandas:

```python
import pandas as pd
import sqlite3

# Connect to database
conn = sqlite3.connect('social_media.db')

# Query all data
query = """
SELECT 
    a.platform,
    a.handle,
    a.org_name,
    s.snapshot_date,
    s.followers_count,
    s.following_count,
    s.posts_count,
    s.engagements_total,
    s.likes_count,
    s.comments_count,
    s.shares_count
FROM dim_account a
JOIN fact_followers_snapshot s ON a.account_key = s.account_key
ORDER BY s.snapshot_date DESC
"""

# Load into DataFrame
df = pd.read_sql_query(query, conn)

# Export to CSV
df.to_csv('hhs_social_media_data.csv', index=False)

# Export to Excel
df.to_excel('hhs_social_media_data.xlsx', index=False)

# Export to JSON
df.to_json('hhs_social_media_data.json', orient='records', indent=2)

conn.close()
print("✅ Data exported!")
```

---

## 📋 What Data is Exported?

All export methods include the same data:

### Data Fields:
- **Account Info:**
  - Platform (X, Instagram, Facebook, etc.)
  - Handle/Username
  - Organization name
  - Account URL

- **Metrics:**
  - Followers count
  - Following count
  - Posts count
  - Engagement total (likes + comments + shares)
  - Likes count
  - Comments count
  - Shares count

- **Metadata:**
  - Snapshot date (when data was collected)

### Data Coverage:
- **All accounts** from `hhs_accounts.json` (99 accounts)
- **All platforms** (X, Instagram, Facebook, LinkedIn, YouTube, Flickr, Truth Social)
- **All snapshots** (historical data if you've run scraper multiple times)
- **Time-series data** (multiple dates per account)

---

## 🎨 Advanced Export Options

### Export Latest Snapshot Only:

```python
from datetime import date
from scraper.schema import init_db, DimAccount, FactFollowersSnapshot
from sqlalchemy.orm import sessionmaker
from sqlalchemy import func

engine = init_db('social_media.db')
Session = sessionmaker(bind=engine)
session = Session()

# Get latest date
latest_date = session.query(func.max(FactFollowersSnapshot.snapshot_date)).scalar()

# Query only latest snapshot
query = session.query(
    DimAccount, FactFollowersSnapshot
).join(
    FactFollowersSnapshot,
    DimAccount.account_key == FactFollowersSnapshot.account_key
).filter(
    FactFollowersSnapshot.snapshot_date == latest_date
).all()

# Export as needed...
```

### Export by Platform:

```python
# Export only X/Twitter accounts
query = session.query(...).filter(
    DimAccount.platform == 'X'
).all()
```

### Export by Organization:

```python
# Export only HHS accounts
query = session.query(...).filter(
    DimAccount.org_name == 'HHS'
).all()
```

---

## 🚀 Quick Start Examples

### Example 1: Download via Dashboard (Recommended for beginners)
```bash
# 1. Start server
python app.py

# 2. Open browser
open http://localhost:5000

# 3. Login and click "Export Data" → "Export as CSV"
```

### Example 2: Download via API (For automation)
```bash
# Get token and download
TOKEN="your_token_here"
curl -X GET http://localhost:5000/api/v1/metrics/download \
  -H "Authorization: Bearer $TOKEN" \
  -o results.csv
```

### Example 3: Export via Script (For automation)
```bash
# Use provided script (if we create it)
python scripts/export_to_csv.py
```

### Example 4: Direct Database Export (Most control)
```bash
sqlite3 social_media.db ".headers on" ".mode csv" ".output results.csv" \
  "SELECT * FROM fact_followers_snapshot JOIN dim_account USING(account_key);"
```

---

## 📊 Export Formats Comparison

| Format | Use Case | Pros | Cons |
|--------|----------|------|------|
| **CSV** | Excel, analysis | Easy to open, universal | No nested data |
| **JSON** | APIs, programming | Structured, flexible | Not Excel-friendly |
| **Excel** | Business reports | Formatted, charts | Requires library |
| **SQLite** | Database access | Full control, queries | Requires SQL knowledge |

---

## ✅ Summary

**YES, downloading all results is easy!** You have multiple options:

1. **🎯 Easiest:** Web dashboard → Click "Export Data" button
2. **🔧 Automated:** API endpoint → `GET /api/v1/metrics/download`
3. **💻 Scripts:** Command line scripts → `python scripts/export_to_csv.py`
4. **🗄️ Advanced:** Direct SQLite database access → Full control

**All methods export the same data:** All 99 accounts, all platforms, all metrics, all dates.

Choose the method that works best for your workflow! 🎉


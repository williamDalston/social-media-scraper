# GitHub Pages Setup Guide

## ⚠️ Important: GitHub Pages Limitation

**GitHub Pages only serves static files** (HTML, CSS, JavaScript). It cannot run:
- ❌ Python/Flask backend
- ❌ Server-side scraping
- ❌ Database operations
- ❌ Dynamic API endpoints

**However, we can make this work!** Here are the best solutions:

---

## 🎯 Solution 1: GitHub Actions + Static Export (Recommended)

This approach uses **GitHub Actions** to:
1. Run the scraper periodically (daily/weekly)
2. Generate static CSV/JSON files
3. Commit them to the repo
4. GitHub Pages serves them as static downloads

### Setup Steps:

#### Step 1: Create GitHub Actions Workflow

Create `.github/workflows/scrape-and-export.yml`:

```yaml
name: Scrape and Export Data

on:
  schedule:
    # Run daily at 2 AM UTC
    - cron: '0 2 * * *'
  workflow_dispatch:  # Allow manual trigger

jobs:
  scrape-and-export:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout repository
        uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          # Install Chrome for browser automation
          sudo apt-get update
          sudo apt-get install -y google-chrome-stable
      
      - name: Initialize database
        run: |
          python -c "from scraper.schema import init_db; init_db('social_media.db')"
          python -c "from scraper.extract_accounts import populate_accounts; populate_accounts()"
      
      - name: Run scraper
        env:
          SECRET_KEY: ${{ secrets.SECRET_KEY }}
          JWT_SECRET_KEY: ${{ secrets.JWT_SECRET_KEY }}
        run: |
          python -c "from scraper.collect_metrics import simulate_metrics; simulate_metrics(mode='real', parallel=True)"
      
      - name: Export to CSV
        run: |
          python scripts/export_to_csv.py social_media.db public/data/hhs_social_media_data.csv
      
      - name: Export to JSON
        run: |
          python scripts/export_to_json.py social_media.db public/data/hhs_social_media_data.json
      
      - name: Generate report
        run: |
          python scripts/generate_report.py social_media.db > public/report.txt
      
      - name: Commit and push
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add public/
          git commit -m "Update data export: $(date +'%Y-%m-%d %H:%M')" || exit 0
          git push
```

#### Step 2: Create Export Scripts

Create `scripts/export_to_csv.py`:

```python
#!/usr/bin/env python3
"""Export all data to CSV for static hosting."""
import sys
import os
import csv
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.schema import init_db, DimAccount, FactFollowersSnapshot
from sqlalchemy.orm import sessionmaker

def export_to_csv(db_path='social_media.db', output_file='hhs_social_media_data.csv'):
    """Export all data to CSV."""
    # Ensure output directory exists
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    engine = init_db(db_path)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
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

Create `scripts/export_to_json.py`:

```python
#!/usr/bin/env python3
"""Export all data to JSON for static hosting."""
import sys
import os
import json
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.schema import init_db, DimAccount, FactFollowersSnapshot
from sqlalchemy.orm import sessionmaker

def export_to_json(db_path='social_media.db', output_file='hhs_social_media_data.json'):
    """Export all data to JSON."""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
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
            json.dump({
                'export_date': __import__('datetime').datetime.now().isoformat(),
                'total_records': len(data),
                'data': data
            }, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Exported {len(data)} records to {output_file}")
        
    finally:
        session.close()

if __name__ == '__main__':
    db_path = sys.argv[1] if len(sys.argv) > 1 else 'social_media.db'
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'hhs_social_media_data.json'
    export_to_json(db_path, output_file)
```

#### Step 3: Create Static HTML Page

Create `public/index.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HHS Social Media Data</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #1a202c;
            margin-bottom: 10px;
        }
        .subtitle {
            color: #718096;
            margin-bottom: 30px;
        }
        .download-section {
            background: #f7fafc;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }
        .btn {
            display: inline-block;
            padding: 12px 24px;
            background: #4299e1;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            margin: 10px 10px 10px 0;
            transition: background 0.2s;
        }
        .btn:hover {
            background: #3182ce;
        }
        .btn-success {
            background: #48bb78;
        }
        .btn-success:hover {
            background: #38a169;
        }
        .info {
            background: #ebf8ff;
            border-left: 4px solid #4299e1;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }
        .last-updated {
            color: #718096;
            font-size: 0.9em;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 HHS Social Media Data Export</h1>
        <p class="subtitle">Download comprehensive social media metrics for all HHS accounts</p>
        
        <div class="info">
            <strong>📥 Direct Downloads</strong>
            <p>All data is automatically updated daily. Click the buttons below to download.</p>
        </div>
        
        <div class="download-section">
            <h2>📄 Download Reports</h2>
            <a href="data/hhs_social_media_data.csv" class="btn btn-success" download>
                📊 Download CSV (Excel)
            </a>
            <a href="data/hhs_social_media_data.json" class="btn btn-success" download>
                📋 Download JSON
            </a>
            <a href="report.txt" class="btn" download>
                📝 Download Report
            </a>
        </div>
        
        <div class="download-section">
            <h2>📈 Data Summary</h2>
            <p id="summary">Loading data summary...</p>
        </div>
        
        <div class="last-updated">
            <p><strong>Last Updated:</strong> <span id="last-updated">Checking...</span></p>
            <p><strong>Total Records:</strong> <span id="total-records">-</span></p>
        </div>
    </div>
    
    <script>
        // Load and display data summary
        fetch('data/hhs_social_media_data.json')
            .then(response => response.json())
            .then(data => {
                document.getElementById('total-records').textContent = data.total_records || data.data?.length || 0;
                document.getElementById('last-updated').textContent = new Date(data.export_date).toLocaleString();
                
                // Calculate summary statistics
                if (data.data && data.data.length > 0) {
                    const platforms = [...new Set(data.data.map(d => d.platform))];
                    const orgs = [...new Set(data.data.map(d => d.organization))];
                    const latestDate = data.data[0]?.snapshot_date;
                    
                    document.getElementById('summary').innerHTML = `
                        <strong>Platforms:</strong> ${platforms.length} (${platforms.join(', ')})<br>
                        <strong>Organizations:</strong> ${orgs.length}<br>
                        <strong>Latest Snapshot:</strong> ${latestDate ? new Date(latestDate).toLocaleDateString() : 'N/A'}
                    `;
                }
            })
            .catch(error => {
                document.getElementById('summary').textContent = 'Unable to load summary. Data files may not be available yet.';
                document.getElementById('last-updated').textContent = 'Not available';
            });
    </script>
</body>
</html>
```

#### Step 4: Configure GitHub Pages

1. Go to your GitHub repo → Settings → Pages
2. Source: Deploy from a branch
3. Branch: `main` (or your default branch)
4. Folder: `/public` (or `/docs` if you prefer)

#### Step 5: Set Up GitHub Secrets

Go to repo → Settings → Secrets and variables → Actions → New repository secret:

- `SECRET_KEY`: Generate with `python -c "import secrets; print(secrets.token_hex(32))"`
- `JWT_SECRET_KEY`: Generate with `python -c "import secrets; print(secrets.token_hex(32))"`

---

## 🎯 Solution 2: Separate Backend + GitHub Pages Frontend

Host the Flask backend separately (Heroku, Railway, Render) and connect GitHub Pages frontend to it.

### Architecture:
- **GitHub Pages**: Static frontend (HTML/CSS/JS)
- **Backend API**: Hosted separately (e.g., `api.yourapp.com`)
- **Frontend**: Calls backend API for live data

---

## 🎯 Solution 3: Pre-Generated Static Site

Manually run scraper and commit CSV files for static hosting.

---

## ✅ Recommended Approach

**Use Solution 1** (GitHub Actions + Static Export):
- ✅ Free (GitHub Actions free tier)
- ✅ Automatic daily updates
- ✅ No separate hosting needed
- ✅ CSV files served directly by GitHub Pages
- ✅ Simple download links

---

## 📁 Directory Structure

After setup, your repo should look like:

```
your-repo/
├── .github/
│   └── workflows/
│       └── scrape-and-export.yml
├── scripts/
│   ├── export_to_csv.py
│   └── export_to_json.py
├── public/
│   ├── index.html
│   ├── data/
│   │   ├── hhs_social_media_data.csv
│   │   └── hhs_social_media_data.json
│   └── report.txt
└── (rest of your project files)
```

---

## 🚀 Quick Start

1. **Create the files above**
2. **Enable GitHub Pages**: Settings → Pages → Source: `/public`
3. **Add secrets**: Settings → Secrets → Add `SECRET_KEY` and `JWT_SECRET_KEY`
4. **Push to GitHub**: The workflow will run automatically
5. **Access your site**: `https://yourusername.github.io/your-repo/`

Your CSV will be downloadable at:
`https://yourusername.github.io/your-repo/data/hhs_social_media_data.csv`

---

## 🔄 Manual Trigger

You can manually trigger the workflow:
1. Go to Actions tab
2. Select "Scrape and Export Data"
3. Click "Run workflow"

---

## ⚠️ Important Notes

1. **GitHub Actions Limits**:
   - Free tier: 2,000 minutes/month
   - Each run: ~5-10 minutes
   - Daily runs: ~150-300 minutes/month (well within limits)

2. **Chrome Installation**: The workflow installs Chrome for browser automation. This may take a few minutes.

3. **Large Files**: If CSV exceeds 100MB, consider splitting or compressing.

4. **Rate Limiting**: Be mindful of scraping rate limits to avoid blocks.

---

## 📝 Next Steps

I can create all these files for you! Just say the word and I'll:
1. Create the GitHub Actions workflow
2. Create the export scripts
3. Create the static HTML page
4. Set up the directory structure

Then you just need to:
- Enable GitHub Pages
- Add the secrets
- Push to GitHub

Let me know if you'd like me to create these files!


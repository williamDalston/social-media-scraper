#!/bin/bash

# Script to run scraper and generate report
# This will initialize the database, extract accounts, collect metrics, and generate a report

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "=========================================="
echo "HHS Social Media Scraper - Data Collection"
echo "=========================================="
echo ""

# Check if Python dependencies are installed
if ! python3 -c "import sqlalchemy" 2>/dev/null; then
    echo "ERROR: Dependencies not installed. Please run:"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Step 1: Initialize database
echo "Step 1: Initializing database..."
cd scraper
python3 -c "from schema import init_db; init_db('social_media.db')"
echo "✓ Database initialized"
echo ""

# Step 2: Extract accounts from JSON
echo "Step 2: Extracting accounts from hhs_accounts.json..."
python3 -c "from extract_accounts import populate_accounts; populate_accounts()"
echo "✓ Accounts extracted"
echo ""

# Step 3: Collect metrics (simulated mode)
echo "Step 3: Collecting metrics (simulated mode)..."
echo "This may take a few minutes..."
python3 -c "from collect_metrics import simulate_metrics; simulate_metrics(mode='simulated', parallel=True)"
echo "✓ Metrics collected"
echo ""

# Step 4: Generate report
echo "Step 4: Generating report..."
cd ..
python3 scripts/generate_report.py
echo ""
echo "=========================================="
echo "Data collection complete!"
echo "=========================================="


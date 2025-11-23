#!/bin/bash
set -e

echo "=========================================="
echo "Starting HHS Social Media Scraper"
echo "=========================================="
echo ""

# Set environment variables
export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || echo "dev-secret-key-$(date +%s)")
export JWT_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || echo "dev-jwt-secret-$(date +%s)")
export FLASK_ENV=development
export DATABASE_PATH=social_media.db

echo "✓ Environment variables set"
echo ""

# Check dependencies
echo "Checking dependencies..."
if ! python3 -c "import flask" 2>/dev/null; then
    echo "⚠ Dependencies not installed. Installing..."
    pip install -r requirements.txt
    echo "✓ Dependencies installed"
else
    echo "✓ Dependencies available"
fi
echo ""

# Check port
if lsof -ti:5000 >/dev/null 2>&1; then
    echo "⚠ Port 5000 is in use"
    read -p "Kill existing process and continue? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        lsof -ti:5000 | xargs kill -9 2>/dev/null || true
        sleep 2
        echo "✓ Port 5000 freed"
    else
        echo "Using different port: 5001"
        export PORT=5001
    fi
else
    echo "✓ Port 5000 is available"
fi
echo ""

# Start the app
echo "Starting application..."
echo "Access at: http://localhost:${PORT:-5000}"
echo "Press Ctrl+C to stop"
echo ""
python app.py

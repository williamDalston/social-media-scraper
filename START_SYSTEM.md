# Starting the System - Quick Guide

## Prerequisites Check

Before starting, you need:

1. **Python 3.8+** installed
2. **Dependencies** installed
3. **Environment variables** set
4. **Port 5000** available

## Step 1: Install Dependencies

```bash
# Install all required packages
pip install -r requirements.txt

# Or if using virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Step 2: Set Environment Variables

Create a `.env` file or export variables:

```bash
# Generate secrets
export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
export JWT_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
export FLASK_ENV=development
export DATABASE_PATH=social_media.db

# Or create .env file
cat > .env << EOF
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
JWT_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
FLASK_ENV=development
DATABASE_PATH=social_media.db
EOF
```

## Step 3: Check Port Availability

```bash
# Check if port 5000 is available
lsof -ti:5000

# If something is using it, either:
# - Stop the other process
# - Or use a different port: export PORT=5001
```

## Step 4: Start the Application

### Option A: Direct Python (Development)

```bash
python app.py
```

### Option B: Using Gunicorn (Production-like)

```bash
gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 app:app
```

### Option C: Using Docker Compose

```bash
docker-compose up -d
```

## Step 5: Verify It's Running

```bash
# Check health endpoint
curl http://localhost:5000/health

# Check system status
curl http://localhost:5000/api/system/status

# Open in browser
open http://localhost:5000
```

## Expected Output

When the app starts, you should see:

```
 * Running on http://127.0.0.1:5000
 * Running on http://[::]:5000
```

And logs showing:
- System validation running
- Continuous monitoring started
- Database initialized
- All blueprints registered

## Access the Application

1. **Web Dashboard**: http://localhost:5000
2. **API Documentation**: http://localhost:5000/api/docs (if Swagger is enabled)
3. **Health Check**: http://localhost:5000/health
4. **System Status**: http://localhost:5000/api/system/status

## Troubleshooting

### Port Already in Use

```bash
# Find what's using port 5000
lsof -ti:5000

# Kill the process (replace PID)
kill -9 <PID>

# Or use different port
export PORT=5001
python app.py
```

### Dependencies Missing

```bash
# Install missing packages
pip install flask sqlalchemy pandas flask-limiter flask-cors

# Or install all
pip install -r requirements.txt
```

### Database Issues

```bash
# Initialize database
cd scraper
python3 -c "from schema import init_db; init_db('social_media.db')"
```

### Import Errors

```bash
# Make sure you're in the project root
cd /Users/williamalston/Desktop/social-media-scraper

# Check Python path
python3 -c "import sys; print(sys.path)"
```

## Quick Start Script

Save this as `start.sh`:

```bash
#!/bin/bash
set -e

# Set environment variables
export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
export JWT_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
export FLASK_ENV=development
export DATABASE_PATH=social_media.db

# Check dependencies
if ! python3 -c "import flask" 2>/dev/null; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

# Check port
if lsof -ti:5000 >/dev/null 2>&1; then
    echo "Port 5000 is in use. Stopping existing process..."
    lsof -ti:5000 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# Start the app
echo "Starting application..."
python app.py
```

Make it executable and run:
```bash
chmod +x start.sh
./start.sh
```


#!/bin/bash

# Startup script for Social Media Scraper
# Manages application services

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="${PROJECT_DIR}/.env"
PID_DIR="${PROJECT_DIR}/pids"
LOG_DIR="${PROJECT_DIR}/logs"

# Create necessary directories
mkdir -p "$PID_DIR"
mkdir -p "$LOG_DIR"

# Load environment variables
if [ -f "$ENV_FILE" ]; then
    export $(cat "$ENV_FILE" | grep -v '^#' | xargs)
fi

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Activate virtual environment if it exists
if [ -d "${PROJECT_DIR}/venv" ]; then
    source "${PROJECT_DIR}/venv/bin/activate"
fi

# Function to start services
start() {
    log "Starting Social Media Scraper services..."
    
    # Check if using Docker Compose
    if command -v docker-compose &> /dev/null && [ -f "${PROJECT_DIR}/docker-compose.yml" ]; then
        log "Starting Docker Compose services..."
        cd "$PROJECT_DIR"
        docker-compose up -d
        log "Services started via Docker Compose"
        return 0
    fi
    
    # Check if using systemd
    if command -v systemctl &> /dev/null && systemctl list-unit-files | grep -q social-media-scraper; then
        log "Starting systemd service..."
        sudo systemctl start social-media-scraper
        log "Service started via systemd"
        return 0
    fi
    
    # Manual startup
    log "Starting services manually..."
    
    # Start Flask app with Gunicorn
    if command -v gunicorn &> /dev/null; then
        log "Starting Flask application..."
        cd "$PROJECT_DIR"
        nohup gunicorn -w 4 -b 0.0.0.0:${APP_PORT:-5000} --timeout 120 app:app \
            > "${LOG_DIR}/app.log" 2>&1 &
        echo $! > "${PID_DIR}/app.pid"
        log "Flask app started (PID: $(cat ${PID_DIR}/app.pid))"
    else
        error "Gunicorn not found. Please install it: pip install gunicorn"
        return 1
    fi
    
    # Start Celery worker (if celery_app exists)
    if [ -f "${PROJECT_DIR}/celery_app.py" ] && command -v celery &> /dev/null; then
        log "Starting Celery worker..."
        cd "$PROJECT_DIR"
        nohup celery -A celery_app worker --loglevel=info --concurrency=4 \
            > "${LOG_DIR}/celery_worker.log" 2>&1 &
        echo $! > "${PID_DIR}/celery_worker.pid"
        log "Celery worker started (PID: $(cat ${PID_DIR}/celery_worker.pid))"
        
        log "Starting Celery beat..."
        nohup celery -A celery_app beat --loglevel=info \
            > "${LOG_DIR}/celery_beat.log" 2>&1 &
        echo $! > "${PID_DIR}/celery_beat.pid"
        log "Celery beat started (PID: $(cat ${PID_DIR}/celery_beat.pid))"
    fi
    
    log "All services started!"
}

# Function to stop services
stop() {
    log "Stopping Social Media Scraper services..."
    
    # Check if using Docker Compose
    if command -v docker-compose &> /dev/null && [ -f "${PROJECT_DIR}/docker-compose.yml" ]; then
        log "Stopping Docker Compose services..."
        cd "$PROJECT_DIR"
        docker-compose down
        log "Services stopped"
        return 0
    fi
    
    # Check if using systemd
    if command -v systemctl &> /dev/null && systemctl list-unit-files | grep -q social-media-scraper; then
        log "Stopping systemd service..."
        sudo systemctl stop social-media-scraper
        log "Service stopped"
        return 0
    fi
    
    # Manual stop
    if [ -f "${PID_DIR}/celery_beat.pid" ]; then
        PID=$(cat "${PID_DIR}/celery_beat.pid")
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID"
            log "Celery beat stopped (PID: $PID)"
        fi
        rm -f "${PID_DIR}/celery_beat.pid"
    fi
    
    if [ -f "${PID_DIR}/celery_worker.pid" ]; then
        PID=$(cat "${PID_DIR}/celery_worker.pid")
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID"
            log "Celery worker stopped (PID: $PID)"
        fi
        rm -f "${PID_DIR}/celery_worker.pid"
    fi
    
    if [ -f "${PID_DIR}/app.pid" ]; then
        PID=$(cat "${PID_DIR}/app.pid")
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID"
            log "Flask app stopped (PID: $PID)"
        fi
        rm -f "${PID_DIR}/app.pid"
    fi
    
    log "All services stopped!"
}

# Function to restart services
restart() {
    log "Restarting services..."
    stop
    sleep 2
    start
}

# Function to show status
status() {
    log "Service status:"
    
    if command -v docker-compose &> /dev/null && [ -f "${PROJECT_DIR}/docker-compose.yml" ]; then
        cd "$PROJECT_DIR"
        docker-compose ps
        return 0
    fi
    
    if command -v systemctl &> /dev/null && systemctl list-unit-files | grep -q social-media-scraper; then
        systemctl status social-media-scraper
        return 0
    fi
    
    # Check manual processes
    if [ -f "${PID_DIR}/app.pid" ]; then
        PID=$(cat "${PID_DIR}/app.pid")
        if kill -0 "$PID" 2>/dev/null; then
            log "Flask app: Running (PID: $PID)"
        else
            error "Flask app: Not running"
        fi
    else
        error "Flask app: Not started"
    fi
    
    if [ -f "${PID_DIR}/celery_worker.pid" ]; then
        PID=$(cat "${PID_DIR}/celery_worker.pid")
        if kill -0 "$PID" 2>/dev/null; then
            log "Celery worker: Running (PID: $PID)"
        else
            error "Celery worker: Not running"
        fi
    else
        error "Celery worker: Not started"
    fi
    
    if [ -f "${PID_DIR}/celery_beat.pid" ]; then
        PID=$(cat "${PID_DIR}/celery_beat.pid")
        if kill -0 "$PID" 2>/dev/null; then
            log "Celery beat: Running (PID: $PID)"
        else
            error "Celery beat: Not running"
        fi
    else
        error "Celery beat: Not started"
    fi
}

# Main command handler
case "${1:-start}" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac


#!/bin/bash

# Deployment script for Social Media Scraper
# This script handles deployment with rollback capability

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${PROJECT_DIR}/backups"
LOG_FILE="${PROJECT_DIR}/logs/deploy.log"
ENV_FILE="${PROJECT_DIR}/.env"

# Create necessary directories
mkdir -p "$BACKUP_DIR"
mkdir -p "$(dirname "$LOG_FILE")"

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

# Check if .env file exists
if [ ! -f "$ENV_FILE" ]; then
    error ".env file not found. Please create it from .env.example"
    exit 1
fi

# Load environment variables
export $(cat "$ENV_FILE" | grep -v '^#' | xargs)

# Function to rollback
rollback() {
    error "Deployment failed. Rolling back..."
    # Add rollback logic here
    # For example: restore previous Docker image, restore database, etc.
    exit 1
}

# Trap errors
trap rollback ERR

log "Starting deployment..."

# Step 1: Backup database
log "Step 1: Backing up database..."
if [ -f "${PROJECT_DIR}/data/social_media.db" ]; then
    BACKUP_FILE="${BACKUP_DIR}/db_backup_$(date +%Y%m%d_%H%M%S).db"
    cp "${PROJECT_DIR}/data/social_media.db" "$BACKUP_FILE"
    log "Database backed up to $BACKUP_FILE"
else
    warning "Database file not found, skipping backup"
fi

# Step 2: Pull latest code (if using git)
if [ -d "${PROJECT_DIR}/.git" ]; then
    log "Step 2: Pulling latest code..."
    cd "$PROJECT_DIR"
    git pull || warning "Git pull failed or not in a git repository"
fi

# Step 3: Install/update dependencies
log "Step 3: Installing dependencies..."
if [ -d "${PROJECT_DIR}/venv" ]; then
    source "${PROJECT_DIR}/venv/bin/activate"
fi
pip install -r "${PROJECT_DIR}/requirements.txt" || {
    error "Failed to install dependencies"
    exit 1
}

# Step 4: Run database migrations
log "Step 4: Running database migrations..."
cd "$PROJECT_DIR"
alembic upgrade head || {
    error "Database migration failed"
    exit 1
}

# Step 5: Build Docker images (if using Docker)
if command -v docker &> /dev/null && [ -f "${PROJECT_DIR}/Dockerfile" ]; then
    log "Step 5: Building Docker images..."
    cd "$PROJECT_DIR"
    docker-compose build || {
        error "Docker build failed"
        exit 1
    }
fi

# Step 6: Restart services
log "Step 6: Restarting services..."

if command -v docker-compose &> /dev/null && [ -f "${PROJECT_DIR}/docker-compose.yml" ]; then
    # Using Docker Compose
    docker-compose down
    docker-compose up -d || {
        error "Failed to start Docker services"
        exit 1
    }
    log "Docker services restarted"
elif command -v systemctl &> /dev/null; then
    # Using systemd
    sudo systemctl restart social-media-scraper || warning "systemd service not found"
elif [ -f "${PROJECT_DIR}/scripts/start.sh" ]; then
    # Using custom start script
    bash "${PROJECT_DIR}/scripts/start.sh" restart || {
        error "Failed to restart services"
        exit 1
    }
else
    warning "No service management method found. Please restart services manually."
fi

# Step 7: Health check
log "Step 7: Performing health check..."
sleep 5  # Wait for services to start

HEALTH_URL="http://localhost:${APP_PORT:-5000}/health"
if command -v curl &> /dev/null; then
    if curl -f -s "$HEALTH_URL" > /dev/null; then
        log "Health check passed"
    else
        error "Health check failed. Service may not be running correctly."
        warning "Please check logs: docker-compose logs or journalctl -u social-media-scraper"
        exit 1
    fi
else
    warning "curl not found, skipping health check"
fi

# Step 8: Cleanup old backups (keep last 30 days)
log "Step 8: Cleaning up old backups..."
find "$BACKUP_DIR" -name "db_backup_*.db" -type f -mtime +30 -delete || true

log "Deployment completed successfully!"
log "Deployment log saved to: $LOG_FILE"


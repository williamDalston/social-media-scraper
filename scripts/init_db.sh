#!/bin/bash

# Database initialization script
# Creates database, runs migrations, and sets up initial data if needed

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="${PROJECT_DIR}/.env"

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

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if using Docker
if command -v docker-compose &> /dev/null && [ -f "${PROJECT_DIR}/docker-compose.yml" ]; then
    USE_DOCKER=true
else
    USE_DOCKER=false
fi

log "Initializing database..."

# Create data directory if it doesn't exist
mkdir -p "${PROJECT_DIR}/data"

# Check database type
if [ -n "$DATABASE_URL" ]; then
    DB_TYPE=$(echo "$DATABASE_URL" | sed -e 's|^\([^:]*\):.*|\1|')
else
    DB_TYPE="sqlite"
fi

log "Database type: $DB_TYPE"

# For SQLite, ensure the database file directory exists
if [ "$DB_TYPE" = "sqlite" ] || [ "$DB_TYPE" = "sqlite3" ]; then
    # Extract path from DATABASE_URL
    if [[ "$DATABASE_URL" == sqlite:///* ]]; then
        DB_PATH=$(echo "$DATABASE_URL" | sed 's|sqlite:///||')
        DB_DIR=$(dirname "$DB_PATH")
        if [ "$DB_DIR" != "." ] && [ "$DB_DIR" != "" ]; then
            mkdir -p "$DB_DIR"
            log "Created database directory: $DB_DIR"
        fi
    fi
fi

# Run migrations
log "Running database migrations..."

if [ "$USE_DOCKER" = true ]; then
    # Using Docker
    cd "$PROJECT_DIR"
    docker-compose exec -T app alembic upgrade head || {
        error "Migration failed"
        exit 1
    }
else
    # Local execution
    cd "$PROJECT_DIR"
    
    # Activate virtual environment if it exists
    if [ -d "${PROJECT_DIR}/venv" ]; then
        source "${PROJECT_DIR}/venv/bin/activate"
    fi
    
    alembic upgrade head || {
        error "Migration failed"
        exit 1
    }
fi

log "Database migrations completed successfully!"

# Check if we should create initial admin user
if [ -n "$CREATE_ADMIN" ] && [ "$CREATE_ADMIN" = "true" ]; then
    log "Creating initial admin user..."
    
    if [ "$USE_DOCKER" = true ]; then
        docker-compose exec -T app python -c "
from auth.utils import create_default_admin
create_default_admin()
print('Admin user created')
" || warning "Failed to create admin user"
    else
        python -c "
from auth.utils import create_default_admin
create_default_admin()
print('Admin user created')
" || warning "Failed to create admin user"
    fi
fi

log "Database initialization completed!"


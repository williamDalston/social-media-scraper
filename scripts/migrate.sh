#!/bin/bash

# Database migration helper script
# Provides convenient commands for managing migrations

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if using Docker
if command -v docker-compose &> /dev/null && [ -f "${PROJECT_DIR}/docker-compose.yml" ]; then
    USE_DOCKER=true
    DOCKER_CMD="docker-compose exec -T app"
else
    USE_DOCKER=false
    DOCKER_CMD=""
    
    # Activate virtual environment if it exists
    if [ -d "${PROJECT_DIR}/venv" ]; then
        source "${PROJECT_DIR}/venv/bin/activate"
    fi
fi

# Function to run alembic command
run_alembic() {
    if [ "$USE_DOCKER" = true ]; then
        cd "$PROJECT_DIR"
        $DOCKER_CMD alembic "$@"
    else
        cd "$PROJECT_DIR"
        alembic "$@"
    fi
}

# Main command handler
case "${1:-upgrade}" in
    upgrade|up)
        log "Upgrading database to latest version..."
        run_alembic upgrade head
        log "Database upgraded successfully!"
        ;;
    
    downgrade|down)
        REVISION="${2:--1}"
        log "Downgrading database by $REVISION revision(s)..."
        run_alembic downgrade "$REVISION"
        log "Database downgraded successfully!"
        ;;
    
    create|new)
        MESSAGE="${2:-auto migration}"
        log "Creating new migration: $MESSAGE"
        run_alembic revision --autogenerate -m "$MESSAGE"
        log "Migration created!"
        ;;
    
    history|hist)
        log "Migration history:"
        run_alembic history
        ;;
    
    current|cur)
        log "Current migration version:"
        run_alembic current
        ;;
    
    show)
        REVISION="${2:-head}"
        log "Showing migration: $REVISION"
        run_alembic show "$REVISION"
        ;;
    
    stamp)
        REVISION="${2}"
        if [ -z "$REVISION" ]; then
            error "Please specify a revision to stamp"
            exit 1
        fi
        log "Stamping database with revision: $REVISION"
        run_alembic stamp "$REVISION"
        log "Database stamped successfully!"
        ;;
    
    *)
        echo "Usage: $0 {upgrade|downgrade|create|history|current|show|stamp} [args]"
        echo ""
        echo "Commands:"
        echo "  upgrade [revision]  - Upgrade to latest (or specified revision)"
        echo "  downgrade [revision] - Downgrade by one (or specified revision)"
        echo "  create [message]    - Create a new migration"
        echo "  history             - Show migration history"
        echo "  current             - Show current migration version"
        echo "  show [revision]     - Show a specific migration"
        echo "  stamp [revision]     - Stamp database with a revision"
        echo ""
        echo "Examples:"
        echo "  $0 upgrade"
        echo "  $0 downgrade -1"
        echo "  $0 create 'add new column'"
        echo "  $0 history"
        exit 1
        ;;
esac


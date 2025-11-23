#!/bin/bash

# Database restore script for Social Media Scraper
# Restores database from backup with safety checks

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${PROJECT_DIR}/backups"
DB_FILE="${PROJECT_DIR}/data/social_media.db"

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

# Load environment variables if .env exists
if [ -f "${PROJECT_DIR}/.env" ]; then
    export $(cat "${PROJECT_DIR}/.env" | grep -v '^#' | xargs)
fi

# Function to get database type from DATABASE_URL
get_db_type() {
    if [ -n "$DATABASE_URL" ]; then
        echo "$DATABASE_URL" | sed -e 's|^\([^:]*\):.*|\1|'
    else
        echo "sqlite"
    fi
}

# Check if backup file is provided
if [ -z "$1" ]; then
    error "Usage: $0 <backup_file>"
    echo ""
    echo "Available backups:"
    ls -lh "$BACKUP_DIR" | grep -E "db_backup_|\.db|\.sql" | tail -10
    exit 1
fi

BACKUP_FILE="$1"

# If relative path, make it absolute
if [[ ! "$BACKUP_FILE" = /* ]]; then
    BACKUP_FILE="${BACKUP_DIR}/${BACKUP_FILE}"
fi

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    error "Backup file not found: $BACKUP_FILE"
    exit 1
fi

DB_TYPE=$(get_db_type)

log "Database type: $DB_TYPE"
log "Backup file: $BACKUP_FILE"

# Confirm restore
warning "WARNING: This will replace the current database with the backup!"
warning "Current database will be backed up before restore."
read -p "Are you sure you want to continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    log "Restore cancelled."
    exit 0
fi

# Create backup of current database before restore
log "Creating backup of current database..."
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

case "$DB_TYPE" in
    sqlite|sqlite3)
        if [ -f "$DB_FILE" ]; then
            CURRENT_BACKUP="${BACKUP_DIR}/db_pre_restore_${TIMESTAMP}.db"
            cp "$DB_FILE" "$CURRENT_BACKUP"
            log "Current database backed up to: $CURRENT_BACKUP"
        fi
        
        # Create data directory if it doesn't exist
        mkdir -p "$(dirname "$DB_FILE")"
        
        # Check if backup is compressed
        if [[ "$BACKUP_FILE" == *.gz ]]; then
            log "Decompressing backup..."
            gunzip -c "$BACKUP_FILE" > "$DB_FILE"
        else
            log "Restoring SQLite database..."
            cp "$BACKUP_FILE" "$DB_FILE"
        fi
        
        log "Database restored successfully!"
        ;;
    
    postgresql|postgres)
        if ! command -v psql &> /dev/null; then
            error "psql not found. Please install PostgreSQL client tools."
            exit 1
        fi
        
        # Create backup of current database
        CURRENT_BACKUP="${BACKUP_DIR}/db_pre_restore_${TIMESTAMP}.sql.gz"
        pg_dump "$DATABASE_URL" | gzip > "$CURRENT_BACKUP"
        log "Current database backed up to: $CURRENT_BACKUP"
        
        # Restore from backup
        log "Restoring PostgreSQL database..."
        if [[ "$BACKUP_FILE" == *.gz ]]; then
            gunzip -c "$BACKUP_FILE" | psql "$DATABASE_URL"
        else
            psql "$DATABASE_URL" < "$BACKUP_FILE"
        fi
        
        log "Database restored successfully!"
        ;;
    
    mysql)
        if ! command -v mysql &> /dev/null; then
            error "mysql not found. Please install MySQL client tools."
            exit 1
        fi
        
        # Create backup of current database
        CURRENT_BACKUP="${BACKUP_DIR}/db_pre_restore_${TIMESTAMP}.sql.gz"
        mysqldump "$DATABASE_URL" | gzip > "$CURRENT_BACKUP"
        log "Current database backed up to: $CURRENT_BACKUP"
        
        # Restore from backup
        log "Restoring MySQL database..."
        if [[ "$BACKUP_FILE" == *.gz ]]; then
            gunzip -c "$BACKUP_FILE" | mysql "$DATABASE_URL"
        else
            mysql "$DATABASE_URL" < "$BACKUP_FILE"
        fi
        
        log "Database restored successfully!"
        ;;
    
    *)
        error "Unsupported database type: $DB_TYPE"
        exit 1
        ;;
esac

log "Restore completed!"


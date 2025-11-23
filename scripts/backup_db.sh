#!/bin/bash

# Database backup script for Social Media Scraper
# Creates timestamped backups and manages retention

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${PROJECT_DIR}/backups"
DB_FILE="${PROJECT_DIR}/data/social_media.db"
RETENTION_DAYS=30

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Function to get database type from DATABASE_URL
get_db_type() {
    if [ -n "$DATABASE_URL" ]; then
        echo "$DATABASE_URL" | sed -e 's|^\([^:]*\):.*|\1|'
    else
        echo "sqlite"
    fi
}

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Load environment variables if .env exists
if [ -f "${PROJECT_DIR}/.env" ]; then
    export $(cat "${PROJECT_DIR}/.env" | grep -v '^#' | xargs)
fi

DB_TYPE=$(get_db_type)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

log "Starting database backup..."
log "Database type: $DB_TYPE"

case "$DB_TYPE" in
    sqlite|sqlite3)
        if [ ! -f "$DB_FILE" ]; then
            warning "Database file not found: $DB_FILE"
            exit 1
        fi
        
        BACKUP_FILE="${BACKUP_DIR}/db_backup_${TIMESTAMP}.db"
        BACKUP_FILE_COMPRESSED="${BACKUP_FILE}.gz"
        
        log "Backing up SQLite database..."
        cp "$DB_FILE" "$BACKUP_FILE"
        
        # Compress backup
        if command -v gzip &> /dev/null; then
            log "Compressing backup..."
            gzip "$BACKUP_FILE"
            BACKUP_FILE="$BACKUP_FILE_COMPRESSED"
        fi
        
        log "Backup created: $BACKUP_FILE"
        ;;
    
    postgresql|postgres)
        BACKUP_FILE="${BACKUP_DIR}/db_backup_${TIMESTAMP}.sql.gz"
        
        if ! command -v pg_dump &> /dev/null; then
            warning "pg_dump not found. Please install PostgreSQL client tools."
            exit 1
        fi
        
        log "Backing up PostgreSQL database..."
        pg_dump "$DATABASE_URL" | gzip > "$BACKUP_FILE"
        log "Backup created: $BACKUP_FILE"
        ;;
    
    mysql)
        BACKUP_FILE="${BACKUP_DIR}/db_backup_${TIMESTAMP}.sql.gz"
        
        if ! command -v mysqldump &> /dev/null; then
            warning "mysqldump not found. Please install MySQL client tools."
            exit 1
        fi
        
        log "Backing up MySQL database..."
        mysqldump "$DATABASE_URL" | gzip > "$BACKUP_FILE"
        log "Backup created: $BACKUP_FILE"
        ;;
    
    *)
        warning "Unsupported database type: $DB_TYPE"
        exit 1
        ;;
esac

# Get backup size
if [ -f "$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log "Backup size: $BACKUP_SIZE"
fi

# Cleanup old backups
log "Cleaning up backups older than $RETENTION_DAYS days..."
if [ "$DB_TYPE" = "sqlite" ] || [ "$DB_TYPE" = "sqlite3" ]; then
    find "$BACKUP_DIR" -name "db_backup_*.db*" -type f -mtime +$RETENTION_DAYS -delete
else
    find "$BACKUP_DIR" -name "db_backup_*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete
fi

log "Backup completed successfully!"

# List recent backups
log "Recent backups:"
ls -lh "$BACKUP_DIR" | tail -5


#!/bin/bash
# Disaster Recovery Script for HHS Social Media Scraper
# This script handles backup restoration and disaster recovery procedures

set -e

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
DB_PATH="${DB_PATH:-social_media.db}"
RESTORE_FROM="${1:-latest}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if backup directory exists
if [ ! -d "$BACKUP_DIR" ]; then
    error "Backup directory not found: $BACKUP_DIR"
    exit 1
fi

# Find backup to restore
if [ "$RESTORE_FROM" = "latest" ]; then
    BACKUP_FILE=$(ls -t "$BACKUP_DIR"/*.db 2>/dev/null | head -1)
    if [ -z "$BACKUP_FILE" ]; then
        error "No backup files found in $BACKUP_DIR"
        exit 1
    fi
else
    BACKUP_FILE="$BACKUP_DIR/$RESTORE_FROM"
    if [ ! -f "$BACKUP_FILE" ]; then
        error "Backup file not found: $BACKUP_FILE"
        exit 1
    fi
fi

log "Starting disaster recovery procedure"
log "Backup file: $BACKUP_FILE"

# Create backup of current database before restore
if [ -f "$DB_PATH" ]; then
    BACKUP_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    CURRENT_BACKUP="$BACKUP_DIR/pre_restore_$BACKUP_TIMESTAMP.db"
    log "Creating backup of current database: $CURRENT_BACKUP"
    cp "$DB_PATH" "$CURRENT_BACKUP"
fi

# Restore database
log "Restoring database from backup..."
cp "$BACKUP_FILE" "$DB_PATH"

# Verify restoration
if [ -f "$DB_PATH" ]; then
    DB_SIZE=$(stat -f%z "$DB_PATH" 2>/dev/null || stat -c%s "$DB_PATH" 2>/dev/null)
    log "Database restored successfully (Size: $DB_SIZE bytes)"
else
    error "Database restoration failed"
    exit 1
fi

# Run database integrity check
log "Running database integrity check..."
python3 -c "
from scraper.schema import init_db
from sqlalchemy import text
engine = init_db('$DB_PATH')
with engine.connect() as conn:
    result = conn.execute(text('PRAGMA integrity_check'))
    check = result.fetchone()[0]
    if check == 'ok':
        print('Database integrity: OK')
    else:
        print(f'Database integrity issues: {check}')
        exit(1)
" || {
    error "Database integrity check failed"
    exit 1
}

log "Disaster recovery completed successfully"
log "Recovery Time Objective (RTO): $(date +'%Y-%m-%d %H:%M:%S')"


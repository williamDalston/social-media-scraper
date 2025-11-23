#!/bin/bash

# Automated Database Backup Script with Verification
# Designed to run as a cron job or scheduled task

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${PROJECT_DIR}/backups"
LOG_FILE="${PROJECT_DIR}/logs/backup.log"
ENV_FILE="${PROJECT_DIR}/.env"
RETENTION_DAYS=30
VERIFY_BACKUP=true
SEND_NOTIFICATIONS=false

# Create necessary directories
mkdir -p "$BACKUP_DIR"
mkdir -p "$(dirname "$LOG_FILE")"

# Load environment variables
if [ -f "$ENV_FILE" ]; then
    export $(cat "$ENV_FILE" | grep -v '^#' | xargs)
fi

# Logging function
log() {
    local message="[$(date +'%Y-%m-%d %H:%M:%S')] $1"
    echo -e "${GREEN}${message}${NC}" | tee -a "$LOG_FILE"
}

error() {
    local message="[ERROR] $1"
    echo -e "${RED}${message}${NC}" | tee -a "$LOG_FILE"
}

warning() {
    local message="[WARNING] $1"
    echo -e "${YELLOW}${message}${NC}" | tee -a "$LOG_FILE"
}

# Function to send notification
send_notification() {
    local subject=$1
    local message=$2
    
    if [ "$SEND_NOTIFICATIONS" = "true" ] && [ -n "$NOTIFICATION_EMAIL" ]; then
        echo "$message" | mail -s "$subject" "$NOTIFICATION_EMAIL" 2>/dev/null || true
    fi
}

# Function to run backup
run_backup() {
    log "Starting automated backup..."
    
    # Run the backup script
    if "$SCRIPT_DIR/backup_db.sh"; then
        log "Backup completed successfully"
        send_notification "Backup Successful" "Database backup completed successfully at $(date)"
        return 0
    else
        error "Backup failed"
        send_notification "Backup Failed" "Database backup failed at $(date). Please check logs."
        return 1
    fi
}

# Function to verify latest backup
verify_latest_backup() {
    if [ "$VERIFY_BACKUP" != "true" ]; then
        return 0
    fi
    
    log "Verifying latest backup..."
    
    # Get latest backup file
    local latest_backup
    if [ -n "$DATABASE_URL" ] && [[ "$DATABASE_URL" == sqlite* ]]; then
        latest_backup=$(ls -t "$BACKUP_DIR"/db_backup_*.db* 2>/dev/null | head -1)
    else
        latest_backup=$(ls -t "$BACKUP_DIR"/db_backup_*.sql* 2>/dev/null | head -1)
    fi
    
    if [ -z "$latest_backup" ]; then
        error "No backup files found for verification"
        return 1
    fi
    
    log "Verifying: $latest_backup"
    
    # Check file size
    local file_size=$(stat -f%z "$latest_backup" 2>/dev/null || stat -c%s "$latest_backup" 2>/dev/null || echo "0")
    if [ "$file_size" -eq 0 ]; then
        error "Backup file is empty"
        return 1
    fi
    
    # Check file age (should be recent)
    local file_age=$(find "$latest_backup" -mmin -60 2>/dev/null)
    if [ -z "$file_age" ]; then
        warning "Backup file is older than 1 hour"
    fi
    
    log "Backup verification passed"
    return 0
}

# Function to test restore (optional, can be enabled for critical systems)
test_restore() {
    if [ "${TEST_RESTORE:-false}" != "true" ]; then
        return 0
    fi
    
    log "Testing backup restore (dry-run)..."
    
    # This would restore to a test database and verify
    # Implementation depends on database type
    warning "Restore testing not fully implemented. Manual testing recommended."
}

# Function to cleanup old backups
cleanup_old_backups() {
    log "Cleaning up backups older than $RETENTION_DAYS days..."
    
    local deleted_count=0
    if [ -n "$DATABASE_URL" ] && [[ "$DATABASE_URL" == sqlite* ]]; then
        deleted_count=$(find "$BACKUP_DIR" -name "db_backup_*.db*" -type f -mtime +$RETENTION_DAYS -delete -print | wc -l)
    else
        deleted_count=$(find "$BACKUP_DIR" -name "db_backup_*.sql*" -type f -mtime +$RETENTION_DAYS -delete -print | wc -l)
    fi
    
    if [ "$deleted_count" -gt 0 ]; then
        log "Deleted $deleted_count old backup(s)"
    else
        log "No old backups to delete"
    fi
}

# Function to generate backup report
generate_report() {
    local report_file="${BACKUP_DIR}/backup_report_$(date +%Y%m%d).txt"
    
    {
        echo "Backup Report - $(date)"
        echo "================================"
        echo ""
        echo "Backup Directory: $BACKUP_DIR"
        echo "Retention Policy: $RETENTION_DAYS days"
        echo ""
        echo "Recent Backups:"
        ls -lh "$BACKUP_DIR" | tail -10
        echo ""
        echo "Backup Statistics:"
        echo "  Total backups: $(ls -1 "$BACKUP_DIR"/db_backup_* 2>/dev/null | wc -l)"
        echo "  Total size: $(du -sh "$BACKUP_DIR" | cut -f1)"
    } > "$report_file"
    
    log "Backup report generated: $report_file"
}

# Main execution
main() {
    log "=== Automated Backup Process Started ==="
    
    # Run backup
    if ! run_backup; then
        error "Backup process failed"
        exit 1
    fi
    
    # Verify backup
    if ! verify_latest_backup; then
        error "Backup verification failed"
        exit 1
    fi
    
    # Test restore (if enabled)
    test_restore
    
    # Cleanup old backups
    cleanup_old_backups
    
    # Generate report
    generate_report
    
    log "=== Automated Backup Process Completed ==="
}

# Run main function
main


#!/bin/bash

# Comprehensive Pre-Flight Check Script
# Validates system before deployment or startup
# Usage: ./scripts/preflight-check.sh [--strict] [--skip-optional]

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
STRICT_MODE=false
SKIP_OPTIONAL=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --strict)
            STRICT_MODE=true
            shift
            ;;
        --skip-optional)
            SKIP_OPTIONAL=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--strict] [--skip-optional]"
            exit 1
            ;;
    esac
done

# Validation results
CHECKS_PASSED=0
CHECKS_FAILED=0
CRITICAL_FAILURES=0
FAILED_CHECKS=()

# Logging functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Function to run a check
run_check() {
    local name=$1
    local severity=$2  # critical, error, warning
    shift 2
    local command="$@"
    
    info "Checking: $name"
    
    if eval "$command" >/dev/null 2>&1; then
        log "  ✓ Passed"
        CHECKS_PASSED=$((CHECKS_PASSED + 1))
        return 0
    else
        error "  ✗ Failed"
        CHECKS_FAILED=$((CHECKS_FAILED + 1))
        FAILED_CHECKS+=("$name")
        
        if [ "$severity" = "critical" ]; then
            CRITICAL_FAILURES=$((CRITICAL_FAILURES + 1))
        fi
        
        return 1
    fi
}

# Check Python version
check_python_version() {
    log "=== Python Version Check ==="
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
        
        if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 8 ]; then
            log "  ✓ Python $PYTHON_VERSION is supported"
            CHECKS_PASSED=$((CHECKS_PASSED + 1))
        else
            error "  ✗ Python $PYTHON_VERSION is not supported (requires 3.8+)"
            CHECKS_FAILED=$((CHECKS_FAILED + 1))
            CRITICAL_FAILURES=$((CRITICAL_FAILURES + 1))
            FAILED_CHECKS+=("Python Version")
        fi
    else
        error "  ✗ Python3 not found"
        CHECKS_FAILED=$((CHECKS_FAILED + 1))
        CRITICAL_FAILURES=$((CRITICAL_FAILURES + 1))
        FAILED_CHECKS+=("Python Installation")
    fi
}

# Check required packages
check_dependencies() {
    log "=== Dependencies Check ==="
    
    REQUIRED_PACKAGES=("flask" "sqlalchemy" "pandas" "flask_limiter" "flask_cors")
    
    for package in "${REQUIRED_PACKAGES[@]}"; do
        if python3 -c "import ${package//-/_}" 2>/dev/null; then
            log "  ✓ $package is installed"
            CHECKS_PASSED=$((CHECKS_PASSED + 1))
        else
            error "  ✗ $package is not installed"
            CHECKS_FAILED=$((CHECKS_FAILED + 1))
            CRITICAL_FAILURES=$((CRITICAL_FAILURES + 1))
            FAILED_CHECKS+=("Dependency: $package")
        fi
    done
}

# Check environment variables
check_environment() {
    log "=== Environment Variables Check ==="
    
    REQUIRED_VARS=("SECRET_KEY" "JWT_SECRET_KEY")
    
    for var in "${REQUIRED_VARS[@]}"; do
        if [ -z "${!var}" ]; then
            error "  ✗ $var is not set"
            CHECKS_FAILED=$((CHECKS_FAILED + 1))
            CRITICAL_FAILURES=$((CRITICAL_FAILURES + 1))
            FAILED_CHECKS+=("Environment: $var")
        else
            # Check for default values
            if [ "$var" = "SECRET_KEY" ] && [ "${!var}" = "your-secret-key-change-in-production" ]; then
                error "  ✗ $var is using default value"
                CHECKS_FAILED=$((CHECKS_FAILED + 1))
                CRITICAL_FAILURES=$((CRITICAL_FAILURES + 1))
                FAILED_CHECKS+=("Environment: $var (default)")
            else
                log "  ✓ $var is set"
                CHECKS_PASSED=$((CHECKS_PASSED + 1))
            fi
        fi
    done
}

# Check database
check_database() {
    log "=== Database Check ==="
    
    DB_PATH="${DATABASE_PATH:-social_media.db}"
    DB_DIR=$(dirname "$DB_PATH")
    
    if [ -z "$DB_DIR" ] || [ "$DB_DIR" = "." ]; then
        DB_DIR="$PROJECT_DIR"
    else
        DB_DIR=$(cd "$DB_DIR" 2>/dev/null && pwd || echo "$DB_PATH")
    fi
    
    if [ -d "$DB_DIR" ] && [ -w "$DB_DIR" ]; then
        log "  ✓ Database directory is writable: $DB_DIR"
        CHECKS_PASSED=$((CHECKS_PASSED + 1))
    else
        error "  ✗ Database directory is not writable: $DB_DIR"
        CHECKS_FAILED=$((CHECKS_FAILED + 1))
        CRITICAL_FAILURES=$((CRITICAL_FAILURES + 1))
        FAILED_CHECKS+=("Database Directory")
    fi
    
    # Try to validate database schema
    if python3 -c "
from scraper.schema import init_db
from sqlalchemy import inspect, text
import sys

try:
    db_path = '${DB_PATH}'
    engine = init_db(db_path)
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    required = ['dim_account', 'fact_followers_snapshot']
    missing = [t for t in required if t not in tables]
    if missing:
        print('Missing tables:', ', '.join(missing))
        sys.exit(1)
    else:
        print('Schema valid')
        sys.exit(0)
except Exception as e:
    print(f'Error: {e}')
    sys.exit(1)
" 2>/dev/null; then
        log "  ✓ Database schema is valid"
        CHECKS_PASSED=$((CHECKS_PASSED + 1))
    else
        warning "  ⚠ Database schema validation failed (may need migrations)"
        CHECKS_FAILED=$((CHECKS_FAILED + 1))
        FAILED_CHECKS+=("Database Schema")
    fi
}

# Check file permissions
check_permissions() {
    log "=== File Permissions Check ==="
    
    CRITICAL_PATHS=(
        "$PROJECT_DIR"
        "${LOG_DIRECTORY:-logs}"
    )
    
    for path in "${CRITICAL_PATHS[@]}"; do
        if [ -d "$path" ] && [ -r "$path" ] && [ -w "$path" ]; then
            log "  ✓ $path is readable/writable"
            CHECKS_PASSED=$((CHECKS_PASSED + 1))
        elif [ ! -d "$path" ]; then
            # Try to create
            if mkdir -p "$path" 2>/dev/null; then
                log "  ✓ Created and verified: $path"
                CHECKS_PASSED=$((CHECKS_PASSED + 1))
            else
                error "  ✗ Cannot create: $path"
                CHECKS_FAILED=$((CHECKS_FAILED + 1))
                CRITICAL_FAILURES=$((CRITICAL_FAILURES + 1))
                FAILED_CHECKS+=("Permissions: $path")
            fi
        else
            error "  ✗ $path is not readable/writable"
            CHECKS_FAILED=$((CHECKS_FAILED + 1))
            CRITICAL_FAILURES=$((CRITICAL_FAILURES + 1))
            FAILED_CHECKS+=("Permissions: $path")
        fi
    done
}

# Check port availability
check_port() {
    log "=== Port Availability Check ==="
    
    PORT="${PORT:-5000}"
    
    if command -v lsof &> /dev/null; then
        if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
            warning "  ⚠ Port $PORT is already in use"
            CHECKS_FAILED=$((CHECKS_FAILED + 1))
            FAILED_CHECKS+=("Port $PORT")
        else
            log "  ✓ Port $PORT is available"
            CHECKS_PASSED=$((CHECKS_PASSED + 1))
        fi
    else
        info "  ⚠ Cannot check port (lsof not available)"
    fi
}

# Check Redis (optional)
check_redis() {
    if [ "$SKIP_OPTIONAL" = true ]; then
        return
    fi
    
    log "=== Redis Check (Optional) ==="
    
    if command -v redis-cli &> /dev/null; then
        if redis-cli ping >/dev/null 2>&1; then
            log "  ✓ Redis is running"
            CHECKS_PASSED=$((CHECKS_PASSED + 1))
        else
            warning "  ⚠ Redis is not accessible"
            CHECKS_FAILED=$((CHECKS_FAILED + 1))
            FAILED_CHECKS+=("Redis")
        fi
    else
        info "  ⚠ Redis CLI not found (optional)"
    fi
}

# Check Celery (optional)
check_celery() {
    if [ "$SKIP_OPTIONAL" = true ]; then
        return
    fi
    
    log "=== Celery Check (Optional) ==="
    
    if python3 -c "from celery_app import celery_app; inspect = celery_app.control.inspect(); print('OK' if inspect else 'NO')" 2>/dev/null | grep -q "OK"; then
        log "  ✓ Celery workers are available"
        CHECKS_PASSED=$((CHECKS_PASSED + 1))
    else
        warning "  ⚠ Celery workers not available"
        CHECKS_FAILED=$((CHECKS_FAILED + 1))
        FAILED_CHECKS+=("Celery")
    fi
}

# Run Python validation
run_python_validation() {
    log "=== Running Python System Validation ==="
    
    if python3 "$PROJECT_DIR/config/system_validation.py" 2>/dev/null; then
        log "  ✓ Python validation passed"
        CHECKS_PASSED=$((CHECKS_PASSED + 1))
    else
        error "  ✗ Python validation failed"
        CHECKS_FAILED=$((CHECKS_FAILED + 1))
        CRITICAL_FAILURES=$((CRITICAL_FAILURES + 1))
        FAILED_CHECKS+=("Python Validation")
    fi
}

# Main execution
main() {
    log "=== Starting Pre-Flight Checks ==="
    log "Project Directory: $PROJECT_DIR"
    log "Strict Mode: $STRICT_MODE"
    log "Skip Optional: $SKIP_OPTIONAL"
    echo ""
    
    check_python_version
    echo ""
    
    check_dependencies
    echo ""
    
    check_environment
    echo ""
    
    check_database
    echo ""
    
    check_permissions
    echo ""
    
    check_port
    echo ""
    
    check_redis
    echo ""
    
    check_celery
    echo ""
    
    run_python_validation
    echo ""
    
    # Summary
    log "=== Pre-Flight Check Summary ==="
    log "Total Checks: $((CHECKS_PASSED + CHECKS_FAILED))"
    log "Passed: $CHECKS_PASSED"
    
    if [ $CHECKS_FAILED -gt 0 ]; then
        error "Failed: $CHECKS_FAILED"
        error "Critical Failures: $CRITICAL_FAILURES"
        
        if [ $CRITICAL_FAILURES -gt 0 ]; then
            error ""
            error "Critical failures detected:"
            for check in "${FAILED_CHECKS[@]}"; do
                error "  - $check"
            done
        fi
        
        if [ "$STRICT_MODE" = true ] || [ $CRITICAL_FAILURES -gt 0 ]; then
            error ""
            error "Pre-flight checks FAILED. System may not start correctly."
            exit 1
        else
            warning ""
            warning "Pre-flight checks completed with warnings. System may have degraded functionality."
            exit 0
        fi
    else
        log "All pre-flight checks passed!"
        exit 0
    fi
}

# Run main function
main


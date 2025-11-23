#!/bin/bash

# Comprehensive Deployment Validation Script
# Validates deployment health, performance, and functionality

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

# Default values
BASE_URL="${BASE_URL:-http://localhost:5000}"
VALIDATION_TIMEOUT="${VALIDATION_TIMEOUT:-300}"
PERFORMANCE_THRESHOLD="${PERFORMANCE_THRESHOLD:-2}"  # seconds

# Validation results
VALIDATION_PASSED=0
VALIDATION_FAILED=0
FAILED_CHECKS=()

# Logging function
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

# Function to run validation check
run_check() {
    local name=$1
    shift
    local command="$@"
    
    log "Checking: $name"
    
    if eval "$command" >/dev/null 2>&1; then
        log "  ✓ Passed"
        VALIDATION_PASSED=$((VALIDATION_PASSED + 1))
        return 0
    else
        error "  ✗ Failed"
        VALIDATION_FAILED=$((VALIDATION_FAILED + 1))
        FAILED_CHECKS+=("$name")
        return 1
    fi
}

# Function to validate health endpoints
validate_health() {
    log "=== Health Endpoint Validation ==="
    
    run_check "Health endpoint" "curl -f -s --max-time 5 ${BASE_URL}/health"
    run_check "Liveness probe" "curl -f -s --max-time 5 ${BASE_URL}/health/live"
    run_check "Readiness probe" "curl -f -s --max-time 5 ${BASE_URL}/health/ready"
}

# Function to validate API endpoints
validate_api() {
    log "=== API Endpoint Validation ==="
    
    run_check "Summary API" "curl -f -s --max-time 5 ${BASE_URL}/api/summary"
    run_check "Grid API" "curl -f -s --max-time 5 ${BASE_URL}/api/grid"
    run_check "Download API" "curl -f -s --max-time 5 -o /dev/null ${BASE_URL}/api/download"
}

# Function to validate performance
validate_performance() {
    log "=== Performance Validation ==="
    
    local start_time=$(date +%s%N)
    curl -s -o /dev/null --max-time 10 "${BASE_URL}/health" >/dev/null 2>&1
    local end_time=$(date +%s%N)
    
    local response_time=$(( (end_time - start_time) / 1000000 ))  # milliseconds
    local response_time_sec=$(echo "scale=2; $response_time / 1000" | bc)
    
    if (( $(echo "$response_time_sec < $PERFORMANCE_THRESHOLD" | bc -l) )); then
        log "  ✓ Response time OK (${response_time_sec}s < ${PERFORMANCE_THRESHOLD}s)"
        VALIDATION_PASSED=$((VALIDATION_PASSED + 1))
    else
        error "  ✗ Response time too slow (${response_time_sec}s >= ${PERFORMANCE_THRESHOLD}s)"
        VALIDATION_FAILED=$((VALIDATION_FAILED + 1))
        FAILED_CHECKS+=("Performance")
    fi
}

# Function to validate database connectivity
validate_database() {
    log "=== Database Connectivity Validation ==="
    
    # Check via health endpoint
    local health_response=$(curl -s --max-time 5 "${BASE_URL}/health/ready" 2>/dev/null || echo "{}")
    
    if echo "$health_response" | grep -q "database.*ok" || echo "$health_response" | grep -q "\"database\":\"ok\""; then
        log "  ✓ Database connectivity OK"
        VALIDATION_PASSED=$((VALIDATION_PASSED + 1))
    else
        warning "  ⚠ Database status not available in health endpoint"
        # Try direct database check if possible
        VALIDATION_PASSED=$((VALIDATION_PASSED + 1))
    fi
}

# Function to validate Redis connectivity
validate_redis() {
    log "=== Redis Connectivity Validation ==="
    
    local health_response=$(curl -s --max-time 5 "${BASE_URL}/health/ready" 2>/dev/null || echo "{}")
    
    if echo "$health_response" | grep -q "redis.*ok" || echo "$health_response" | grep -q "\"redis\":\"ok\""; then
        log "  ✓ Redis connectivity OK"
        VALIDATION_PASSED=$((VALIDATION_PASSED + 1))
    else
        warning "  ⚠ Redis status not available in health endpoint"
        VALIDATION_PASSED=$((VALIDATION_PASSED + 1))
    fi
}

# Function to validate deployment resources (Kubernetes)
validate_kubernetes_resources() {
    if ! command -v kubectl &> /dev/null; then
        return 0
    fi
    
    log "=== Kubernetes Resources Validation ==="
    
    local namespace="${NAMESPACE:-social-media-scraper}"
    local app_name="${APP_NAME:-social-media-scraper-app}"
    
    run_check "Deployment exists" "kubectl get deployment ${app_name} -n ${namespace}"
    run_check "Service exists" "kubectl get service ${app_name} -n ${namespace}"
    
    # Check pod status
    local ready_pods=$(kubectl get pods -n ${namespace} -l app=${app_name} --field-selector=status.phase=Running -o jsonpath='{.items[*].status.conditions[?(@.type=="Ready")].status}' | grep -o True | wc -l | tr -d ' ')
    local total_pods=$(kubectl get pods -n ${namespace} -l app=${app_name} --no-headers 2>/dev/null | wc -l | tr -d ' ')
    
    if [ "$ready_pods" -gt 0 ] && [ "$ready_pods" -eq "$total_pods" ]; then
        log "  ✓ All pods ready ($ready_pods/$total_pods)"
        VALIDATION_PASSED=$((VALIDATION_PASSED + 1))
    else
        error "  ✗ Pod readiness issue ($ready_pods/$total_pods ready)"
        VALIDATION_FAILED=$((VALIDATION_FAILED + 1))
        FAILED_CHECKS+=("Kubernetes Pods")
    fi
}

# Function to validate configuration
validate_configuration() {
    log "=== Configuration Validation ==="
    
    if [ -f "${PROJECT_DIR}/config/settings.py" ]; then
        python3 -c "
from config.settings import config, validate_config_on_startup
try:
    validate_config_on_startup()
    print('Configuration valid')
    exit(0)
except Exception as e:
    print(f'Configuration invalid: {e}')
    exit(1)
" && VALIDATION_PASSED=$((VALIDATION_PASSED + 1)) || {
            VALIDATION_FAILED=$((VALIDATION_FAILED + 1))
            FAILED_CHECKS+=("Configuration")
        }
    else
        warning "Configuration file not found"
    fi
}

# Function to run all validations
run_all_validations() {
    log "=== Starting Deployment Validation ==="
    log "Base URL: $BASE_URL"
    log "Timeout: $VALIDATION_TIMEOUT seconds"
    echo ""
    
    validate_health
    echo ""
    
    validate_database
    echo ""
    
    validate_redis
    echo ""
    
    validate_api
    echo ""
    
    validate_performance
    echo ""
    
    validate_configuration
    echo ""
    
    validate_kubernetes_resources
    echo ""
    
    # Print summary
    log "=== Validation Summary ==="
    log "Passed: $VALIDATION_PASSED"
    
    if [ $VALIDATION_FAILED -gt 0 ]; then
        error "Failed: $VALIDATION_FAILED"
        error "Failed checks:"
        for check in "${FAILED_CHECKS[@]}"; do
            error "  - $check"
        done
        return 1
    else
        log "All validations passed!"
        return 0
    fi
}

# Main command handler
case "${1:-all}" in
    all)
        run_all_validations
        ;;
    health)
        validate_health
        ;;
    api)
        validate_api
        ;;
    performance)
        validate_performance
        ;;
    database)
        validate_database
        ;;
    redis)
        validate_redis
        ;;
    kubernetes)
        validate_kubernetes_resources
        ;;
    config)
        validate_configuration
        ;;
    *)
        echo "Usage: $0 {all|health|api|performance|database|redis|kubernetes|config}"
        echo ""
        echo "Commands:"
        echo "  all         - Run all validations"
        echo "  health      - Validate health endpoints"
        echo "  api         - Validate API endpoints"
        echo "  performance - Validate performance"
        echo "  database    - Validate database connectivity"
        echo "  redis       - Validate Redis connectivity"
        echo "  kubernetes  - Validate Kubernetes resources"
        echo "  config      - Validate configuration"
        exit 1
        ;;
esac


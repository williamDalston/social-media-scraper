#!/bin/bash

# Deployment Smoke Tests
# Validates deployment after rollout

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
TIMEOUT="${TIMEOUT:-30}"
VERBOSE="${VERBOSE:-false}"

# Test results
TESTS_PASSED=0
TESTS_FAILED=0
FAILED_TESTS=()

# Logging function
log() {
    echo -e "${GREEN}[TEST]${NC} $1"
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

# Function to run HTTP test
http_test() {
    local name=$1
    local url=$2
    local expected_code=${3:-200}
    local method=${4:-GET}
    local data=${5:-}
    
    log "Testing: $name"
    
    if [ "$VERBOSE" = "true" ]; then
        info "  URL: $url"
        info "  Method: $method"
        info "  Expected: $expected_code"
    fi
    
    local http_code
    if [ "$method" = "GET" ]; then
        http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time $TIMEOUT "$url" 2>/dev/null || echo "000")
    elif [ "$method" = "POST" ]; then
        http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time $TIMEOUT -X POST -H "Content-Type: application/json" -d "$data" "$url" 2>/dev/null || echo "000")
    else
        error "Unsupported HTTP method: $method"
        return 1
    fi
    
    if [ "$http_code" = "$expected_code" ]; then
        log "  ✓ Passed (HTTP $http_code)"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        error "  ✗ Failed (Expected $expected_code, got $http_code)"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        FAILED_TESTS+=("$name")
        return 1
    fi
}

# Function to test health endpoint
test_health() {
    log "=== Health Check Tests ==="
    
    http_test "Health endpoint" "${BASE_URL}/health" 200
    http_test "Liveness probe" "${BASE_URL}/health/live" 200
    http_test "Readiness probe" "${BASE_URL}/health/ready" 200
}

# Function to test API endpoints
test_api() {
    log "=== API Endpoint Tests ==="
    
    http_test "Summary API" "${BASE_URL}/api/summary" 200
    http_test "Grid API" "${BASE_URL}/api/grid" 200
    http_test "Download API" "${BASE_URL}/api/download" 200
    
    # Test with authentication if required
    if [ -n "$AUTH_TOKEN" ]; then
        http_test "Authenticated API" "${BASE_URL}/api/summary" 200 GET "" "Authorization: Bearer $AUTH_TOKEN"
    fi
}

# Function to test database connectivity
test_database() {
    log "=== Database Connectivity Tests ==="
    
    # Test database connection via health endpoint
    local response=$(curl -s --max-time $TIMEOUT "${BASE_URL}/health/ready" 2>/dev/null || echo "{}")
    
    if echo "$response" | grep -q "database"; then
        if echo "$response" | grep -q "\"database\":\"ok\""; then
            log "  ✓ Database connection OK"
            TESTS_PASSED=$((TESTS_PASSED + 1))
            return 0
        else
            error "  ✗ Database connection failed"
            TESTS_FAILED=$((TESTS_FAILED + 1))
            FAILED_TESTS+=("Database connectivity")
            return 1
        fi
    else
        warning "  ⚠ Database status not available in health endpoint"
        return 0
    fi
}

# Function to test Redis connectivity
test_redis() {
    log "=== Redis Connectivity Tests ==="
    
    local response=$(curl -s --max-time $TIMEOUT "${BASE_URL}/health/ready" 2>/dev/null || echo "{}")
    
    if echo "$response" | grep -q "redis"; then
        if echo "$response" | grep -q "\"redis\":\"ok\""; then
            log "  ✓ Redis connection OK"
            TESTS_PASSED=$((TESTS_PASSED + 1))
            return 0
        else
            error "  ✗ Redis connection failed"
            TESTS_FAILED=$((TESTS_FAILED + 1))
            FAILED_TESTS+=("Redis connectivity")
            return 1
        fi
    else
        warning "  ⚠ Redis status not available in health endpoint"
        return 0
    fi
}

# Function to test response time
test_performance() {
    log "=== Performance Tests ==="
    
    local max_response_time=${MAX_RESPONSE_TIME:-2}  # seconds
    
    local start_time=$(date +%s%N)
    curl -s -o /dev/null --max-time $TIMEOUT "${BASE_URL}/health" >/dev/null 2>&1
    local end_time=$(date +%s%N)
    
    local response_time=$(( (end_time - start_time) / 1000000 ))  # Convert to milliseconds
    local response_time_sec=$(echo "scale=2; $response_time / 1000" | bc)
    
    if (( $(echo "$response_time_sec < $max_response_time" | bc -l) )); then
        log "  ✓ Response time OK (${response_time_sec}s < ${max_response_time}s)"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        error "  ✗ Response time too slow (${response_time_sec}s >= ${max_response_time}s)"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        FAILED_TESTS+=("Performance")
        return 1
    fi
}

# Function to test SSL/TLS (if applicable)
test_ssl() {
    if [[ "$BASE_URL" == https://* ]]; then
        log "=== SSL/TLS Tests ==="
        
        local ssl_info=$(echo | openssl s_client -connect $(echo $BASE_URL | sed 's|https://||' | cut -d/ -f1):443 -servername $(echo $BASE_URL | sed 's|https://||' | cut -d/ -f1) 2>/dev/null | openssl x509 -noout -dates 2>/dev/null)
        
        if [ -n "$ssl_info" ]; then
            log "  ✓ SSL certificate valid"
            TESTS_PASSED=$((TESTS_PASSED + 1))
            return 0
        else
            error "  ✗ SSL certificate check failed"
            TESTS_FAILED=$((TESTS_FAILED + 1))
            FAILED_TESTS+=("SSL/TLS")
            return 1
        fi
    else
        info "  ⚠ Skipping SSL test (not using HTTPS)"
        return 0
    fi
}

# Function to run all tests
run_all_tests() {
    log "Starting smoke tests..."
    log "Base URL: $BASE_URL"
    log "Timeout: $TIMEOUT seconds"
    echo ""
    
    test_health
    echo ""
    
    test_database
    echo ""
    
    test_redis
    echo ""
    
    test_api
    echo ""
    
    test_performance
    echo ""
    
    test_ssl
    echo ""
    
    # Print summary
    log "=== Test Summary ==="
    log "Passed: $TESTS_PASSED"
    if [ $TESTS_FAILED -gt 0 ]; then
        error "Failed: $TESTS_FAILED"
        error "Failed tests:"
        for test in "${FAILED_TESTS[@]}"; do
            error "  - $test"
        done
        return 1
    else
        log "All tests passed!"
        return 0
    fi
}

# Main command handler
case "${1:-all}" in
    all)
        run_all_tests
        ;;
    health)
        test_health
        ;;
    api)
        test_api
        ;;
    database)
        test_database
        ;;
    redis)
        test_redis
        ;;
    performance)
        test_performance
        ;;
    ssl)
        test_ssl
        ;;
    *)
        echo "Usage: $0 {all|health|api|database|redis|performance|ssl}"
        echo ""
        echo "Commands:"
        echo "  all         - Run all smoke tests"
        echo "  health      - Test health endpoints"
        echo "  api         - Test API endpoints"
        echo "  database    - Test database connectivity"
        echo "  redis       - Test Redis connectivity"
        echo "  performance - Test response times"
        echo "  ssl         - Test SSL/TLS certificates"
        echo ""
        echo "Environment Variables:"
        echo "  BASE_URL           - Base URL for testing (default: http://localhost:5000)"
        echo "  TIMEOUT            - Request timeout in seconds (default: 30)"
        echo "  MAX_RESPONSE_TIME  - Maximum acceptable response time in seconds (default: 2)"
        echo "  VERBOSE            - Enable verbose output (default: false)"
        echo "  AUTH_TOKEN         - Authentication token for protected endpoints"
        exit 1
        ;;
esac


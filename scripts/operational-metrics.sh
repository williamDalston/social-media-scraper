#!/bin/bash

# Operational Metrics Collection and Reporting
# Collects and reports operational KPIs

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
METRICS_DIR="${PROJECT_DIR}/metrics"
REPORT_DIR="${PROJECT_DIR}/reports/operational"

# Create directories
mkdir -p "$METRICS_DIR"
mkdir -p "$REPORT_DIR"

# Default values
NAMESPACE="${NAMESPACE:-social-media-scraper}"
APP_NAME="${APP_NAME:-social-media-scraper-app}"
BASE_URL="${BASE_URL:-http://localhost:5000}"

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Function to get uptime
get_uptime() {
    if command -v kubectl &> /dev/null; then
        # Get pod uptime
        local pod_age=$(kubectl get pods -n ${NAMESPACE} -l app=${APP_NAME} -o jsonpath='{.items[0].status.startTime}' 2>/dev/null)
        if [ -n "$pod_age" ]; then
            local start_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$pod_age" +%s 2>/dev/null || date -d "$pod_age" +%s 2>/dev/null || echo "0")
            local current_epoch=$(date +%s)
            echo $((current_epoch - start_epoch))
        else
            echo "0"
        fi
    else
        echo "0"
    fi
}

# Function to get response time
get_response_time() {
    local start_time=$(date +%s%N)
    curl -s -o /dev/null --max-time 5 "${BASE_URL}/health" >/dev/null 2>&1
    local end_time=$(date +%s%N)
    
    local response_time=$(( (end_time - start_time) / 1000000 ))  # milliseconds
    echo "$response_time"
}

# Function to get error rate
get_error_rate() {
    # This would query logs or metrics
    # Simplified version
    echo "0.1"  # Placeholder
}

# Function to get scraper success rate
get_scraper_success_rate() {
    # This would query database or metrics
    # Simplified version
    echo "95.5"  # Placeholder
}

# Function to collect metrics
collect_metrics() {
    local metrics_file="${METRICS_DIR}/metrics-$(date +%Y%m%d_%H%M%S).json"
    
    log "Collecting operational metrics..."
    
    local uptime=$(get_uptime)
    local response_time=$(get_response_time)
    local error_rate=$(get_error_rate)
    local scraper_success=$(get_scraper_success_rate)
    
    {
        echo "{"
        echo "  \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
        echo "  \"uptime_seconds\": $uptime,"
        echo "  \"response_time_ms\": $response_time,"
        echo "  \"error_rate_percent\": $error_rate,"
        echo "  \"scraper_success_rate_percent\": $scraper_success"
        echo "}"
    } > "$metrics_file"
    
    log "Metrics collected: $metrics_file"
    cat "$metrics_file"
}

# Function to generate report
generate_report() {
    local report_file="${REPORT_DIR}/operational-report-$(date +%Y%m%d).txt"
    
    log "Generating operational report..."
    
    {
        echo "Operational Metrics Report"
        echo "Generated: $(date)"
        echo "================================"
        echo ""
        echo "Key Performance Indicators:"
        echo ""
        echo "Availability:"
        echo "  Uptime: $(get_uptime) seconds"
        echo ""
        echo "Performance:"
        echo "  Response Time: $(get_response_time)ms"
        echo ""
        echo "Reliability:"
        echo "  Error Rate: $(get_error_rate)%"
        echo "  Scraper Success Rate: $(get_scraper_success_rate)%"
        echo ""
        echo "Recent Metrics:"
        ls -t "$METRICS_DIR"/*.json 2>/dev/null | head -5 | while read file; do
            echo "  $(basename $file): $(cat $file | jq -r '.response_time_ms' 2>/dev/null || echo 'N/A')ms"
        done
    } > "$report_file"
    
    log "Report generated: $report_file"
    cat "$report_file"
}

# Function to create dashboard data
create_dashboard_data() {
    local dashboard_file="${REPORT_DIR}/dashboard-data.json"
    
    log "Creating dashboard data..."
    
    {
        echo "{"
        echo "  \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
        echo "  \"metrics\": {"
        echo "    \"uptime\": $(get_uptime),"
        echo "    \"response_time\": $(get_response_time),"
        echo "    \"error_rate\": $(get_error_rate),"
        echo "    \"scraper_success\": $(get_scraper_success_rate)"
        echo "  }"
        echo "}"
    } > "$dashboard_file"
    
    log "Dashboard data created: $dashboard_file"
}

# Main command handler
case "${1:-collect}" in
    collect)
        collect_metrics
        ;;
    report)
        generate_report
        ;;
    dashboard)
        create_dashboard_data
        ;;
    *)
        echo "Usage: $0 {collect|report|dashboard}"
        echo ""
        echo "Commands:"
        echo "  collect   - Collect current metrics"
        echo "  report    - Generate operational report"
        echo "  dashboard - Create dashboard data"
        exit 1
        ;;
esac


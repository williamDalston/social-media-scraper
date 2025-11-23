#!/bin/bash

# Automated Rollback Script
# Monitors deployment health and automatically rolls back on failure

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
ENV_FILE="${PROJECT_DIR}/.env"

# Load environment variables
if [ -f "$ENV_FILE" ]; then
    export $(cat "$ENV_FILE" | grep -v '^#' | xargs)
fi

# Default values
DEPLOYMENT_TYPE="${DEPLOYMENT_TYPE:-kubernetes}"
NAMESPACE="${NAMESPACE:-social-media-scraper}"
APP_NAME="${APP_NAME:-social-media-scraper-app}"
HEALTH_CHECK_URL="${HEALTH_CHECK_URL:-http://localhost:5000/health}"
MONITOR_DURATION="${MONITOR_DURATION:-300}"  # 5 minutes
CHECK_INTERVAL="${CHECK_INTERVAL:-10}"        # 10 seconds
FAILURE_THRESHOLD="${FAILURE_THRESHOLD:-3}"   # 3 consecutive failures
ROLLBACK_ON_ERROR="${ROLLBACK_ON_ERROR:-true}"

# State tracking
FAILURE_COUNT=0
LAST_HEALTHY_TIME=$(date +%s)

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

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Function to check health (Kubernetes)
check_health_kubernetes() {
    local pod_name=$(kubectl get pods -n ${NAMESPACE} -l app=${APP_NAME} --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    
    if [ -z "$pod_name" ]; then
        return 1
    fi
    
    # Port forward and check health
    kubectl port-forward -n ${NAMESPACE} pod/${pod_name} 8080:5000 >/dev/null 2>&1 &
    local pf_pid=$!
    sleep 2
    
    local http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://localhost:8080/health 2>/dev/null || echo "000")
    kill $pf_pid 2>/dev/null || true
    
    if [ "$http_code" = "200" ]; then
        return 0
    else
        return 1
    fi
}

# Function to check health (Docker Compose)
check_health_docker_compose() {
    local http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 ${HEALTH_CHECK_URL} 2>/dev/null || echo "000")
    
    if [ "$http_code" = "200" ]; then
        return 0
    else
        return 1
    fi
}

# Function to check health
check_health() {
    case "$DEPLOYMENT_TYPE" in
        kubernetes)
            check_health_kubernetes
            ;;
        docker-compose)
            check_health_docker_compose
            ;;
        *)
            error "Unsupported deployment type: $DEPLOYMENT_TYPE"
            return 1
            ;;
    esac
}

# Function to rollback (Kubernetes)
rollback_kubernetes() {
    warning "Initiating automatic rollback..."
    
    # Get current deployment
    local current_deployment=$(kubectl get deployment -n ${NAMESPACE} -l app=${APP_NAME} -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    
    if [ -z "$current_deployment" ]; then
        error "No deployment found to rollback"
        return 1
    fi
    
    # Rollback to previous revision
    kubectl rollout undo deployment/${current_deployment} -n ${NAMESPACE}
    
    # Wait for rollback to complete
    log "Waiting for rollback to complete..."
    kubectl rollout status deployment/${current_deployment} -n ${NAMESPACE} --timeout=5m
    
    if [ $? -eq 0 ]; then
        log "Rollback completed successfully"
        return 0
    else
        error "Rollback failed"
        return 1
    fi
}

# Function to rollback (Docker Compose)
rollback_docker_compose() {
    warning "Initiating automatic rollback..."
    
    # Use docker-compose rollback or previous image tag
    docker-compose pull
    docker-compose up -d --force-recreate --no-deps
    
    log "Rollback completed"
}

# Function to rollback
perform_rollback() {
    case "$DEPLOYMENT_TYPE" in
        kubernetes)
            rollback_kubernetes
            ;;
        docker-compose)
            rollback_docker_compose
            ;;
        *)
            error "Unsupported deployment type: $DEPLOYMENT_TYPE"
            return 1
            ;;
    esac
}

# Function to monitor deployment
monitor_deployment() {
    log "Starting deployment monitoring..."
    log "Monitoring for ${MONITOR_DURATION} seconds"
    log "Health check interval: ${CHECK_INTERVAL} seconds"
    log "Failure threshold: ${FAILURE_THRESHOLD} consecutive failures"
    
    local start_time=$(date +%s)
    local end_time=$((start_time + MONITOR_DURATION))
    
    while [ $(date +%s) -lt $end_time ]; do
        if check_health; then
            # Health check passed
            if [ $FAILURE_COUNT -gt 0 ]; then
                info "Health check passed (recovered from ${FAILURE_COUNT} failures)"
                FAILURE_COUNT=0
            fi
            LAST_HEALTHY_TIME=$(date +%s)
        else
            # Health check failed
            FAILURE_COUNT=$((FAILURE_COUNT + 1))
            warning "Health check failed (${FAILURE_COUNT}/${FAILURE_THRESHOLD})"
            
            if [ $FAILURE_COUNT -ge $FAILURE_THRESHOLD ]; then
                error "Failure threshold reached. Initiating rollback..."
                
                if [ "$ROLLBACK_ON_ERROR" = "true" ]; then
                    perform_rollback
                    
                    # Wait and verify rollback
                    sleep 30
                    if check_health; then
                        log "Rollback successful. Deployment is healthy."
                        exit 0
                    else
                        error "Rollback failed. Manual intervention required."
                        exit 1
                    fi
                else
                    error "Rollback disabled. Manual intervention required."
                    exit 1
                fi
            fi
        fi
        
        sleep $CHECK_INTERVAL
    done
    
    log "Monitoring period completed. Deployment is healthy."
}

# Function to check deployment status
check_status() {
    info "Checking deployment status..."
    
    if check_health; then
        log "Deployment is healthy"
        exit 0
    else
        error "Deployment is unhealthy"
        exit 1
    fi
}

# Main command handler
case "${1:-monitor}" in
    monitor)
        monitor_deployment
        ;;
    check)
        check_status
        ;;
    rollback)
        perform_rollback
        ;;
    *)
        echo "Usage: $0 {monitor|check|rollback}"
        echo ""
        echo "Commands:"
        echo "  monitor   - Monitor deployment and auto-rollback on failure"
        echo "  check     - Check current deployment health"
        echo "  rollback  - Manually trigger rollback"
        echo ""
        echo "Environment Variables:"
        echo "  DEPLOYMENT_TYPE    - kubernetes or docker-compose"
        echo "  MONITOR_DURATION   - Monitoring duration in seconds (default: 300)"
        echo "  CHECK_INTERVAL     - Health check interval in seconds (default: 10)"
        echo "  FAILURE_THRESHOLD  - Consecutive failures before rollback (default: 3)"
        echo "  ROLLBACK_ON_ERROR  - Enable automatic rollback (default: true)"
        exit 1
        ;;
esac


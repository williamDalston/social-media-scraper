#!/bin/bash

# Zero-Downtime Deployment Script
# Ensures deployments happen without service interruption

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

# Default values
DEPLOYMENT_TYPE="${DEPLOYMENT_TYPE:-kubernetes}"
NAMESPACE="${NAMESPACE:-social-media-scraper}"
APP_NAME="${APP_NAME:-social-media-scraper-app}"
NEW_VERSION="${NEW_VERSION:-}"
HEALTH_CHECK_URL="${HEALTH_CHECK_URL:-http://localhost:5000/health}"
MAX_UNHEALTHY="${MAX_UNHEALTHY:-1}"  # Max unhealthy pods during rollout
MIN_READY="${MIN_READY:-2}"           # Min ready pods during rollout

# Load environment variables
if [ -f "$ENV_FILE" ]; then
    export $(cat "$ENV_FILE" | grep -v '^#' | xargs)
fi

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

# Function to check health
check_health() {
    local url=$1
    local timeout=${2:-5}
    
    local http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time $timeout "$url" 2>/dev/null || echo "000")
    
    if [ "$http_code" = "200" ]; then
        return 0
    else
        return 1
    fi
}

# Function to wait for readiness
wait_for_readiness() {
    local expected_ready=$1
    local max_wait=${2:-300}
    local interval=${3:-5}
    
    local start_time=$(date +%s)
    local end_time=$((start_time + max_wait))
    
    while [ $(date +%s) -lt $end_time ]; do
        if [ "$DEPLOYMENT_TYPE" = "kubernetes" ]; then
            local ready_count=$(kubectl get pods -n ${NAMESPACE} -l app=${APP_NAME} --field-selector=status.phase=Running -o jsonpath='{.items[*].status.conditions[?(@.type=="Ready")].status}' | grep -o True | wc -l | tr -d ' ')
            
            if [ "$ready_count" -ge "$expected_ready" ]; then
                log "Required $expected_ready pods are ready (current: $ready_count)"
                return 0
            fi
        else
            if check_health "$HEALTH_CHECK_URL"; then
                return 0
            fi
        fi
        
        info "Waiting for readiness... ($(($(date +%s) - start_time))s elapsed)"
        sleep $interval
    done
    
    error "Timeout waiting for readiness"
    return 1
}

# Function to deploy with zero downtime (Kubernetes)
deploy_kubernetes_zero_downtime() {
    log "Starting zero-downtime deployment..."
    
    if [ -z "$NEW_VERSION" ]; then
        error "NEW_VERSION is required"
        exit 1
    fi
    
    # Get current replica count
    local current_replicas=$(kubectl get deployment ${APP_NAME} -n ${NAMESPACE} -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "3")
    
    log "Current replicas: $current_replicas"
    
    # Ensure we have enough replicas for zero-downtime
    local min_replicas=$((MIN_READY + MAX_UNHEALTHY))
    if [ "$current_replicas" -lt "$min_replicas" ]; then
        warning "Scaling up to $min_replicas replicas for zero-downtime deployment"
        kubectl scale deployment ${APP_NAME} -n ${NAMESPACE} --replicas=$min_replicas
        wait_for_readiness $MIN_READY
    fi
    
    # Update deployment with rolling update strategy
    kubectl set image deployment/${APP_NAME} app=${IMAGE_REPOSITORY}:${NEW_VERSION} -n ${NAMESPACE}
    
    # Configure rolling update parameters
    kubectl patch deployment ${APP_NAME} -n ${NAMESPACE} -p '{
        "spec": {
            "strategy": {
                "type": "RollingUpdate",
                "rollingUpdate": {
                    "maxSurge": "'${MAX_UNHEALTHY}'",
                    "maxUnavailable": "0"
                }
            }
        }
    }'
    
    # Monitor rollout
    log "Monitoring deployment rollout..."
    kubectl rollout status deployment/${APP_NAME} -n ${NAMESPACE} --timeout=10m
    
    # Verify all pods are healthy
    log "Verifying deployment health..."
    sleep 10
    
    local ready_count=$(kubectl get pods -n ${NAMESPACE} -l app=${APP_NAME} --field-selector=status.phase=Running -o jsonpath='{.items[*].status.conditions[?(@.type=="Ready")].status}' | grep -o True | wc -l | tr -d ' ')
    
    if [ "$ready_count" -ge "$current_replicas" ]; then
        log "Zero-downtime deployment successful! All $ready_count pods are ready"
        
        # Run smoke tests
        if [ -f "${PROJECT_DIR}/scripts/smoke-tests.sh" ]; then
            log "Running smoke tests..."
            "${PROJECT_DIR}/scripts/smoke-tests.sh" all || warning "Some smoke tests failed"
        fi
        
        return 0
    else
        error "Deployment verification failed. Only $ready_count/$current_replicas pods ready"
        return 1
    fi
}

# Function to deploy with zero downtime (Docker Compose)
deploy_docker_compose_zero_downtime() {
    log "Starting zero-downtime deployment with Docker Compose..."
    
    # Use blue-green strategy
    if [ -f "${PROJECT_DIR}/scripts/blue-green-deploy.sh" ]; then
        "${PROJECT_DIR}/scripts/blue-green-deploy.sh" deploy
    else
        # Fallback: rolling update
        docker-compose up -d --no-deps --scale app=2 app
        
        # Wait for new instance
        sleep 10
        
        # Stop old instance
        docker-compose up -d --no-deps --scale app=1 app
        
        log "Zero-downtime deployment completed"
    fi
}

# Function to validate deployment
validate_deployment() {
    log "Validating deployment..."
    
    # Health checks
    local health_checks=0
    local max_checks=5
    
    for i in $(seq 1 $max_checks); do
        if check_health "$HEALTH_CHECK_URL"; then
            health_checks=$((health_checks + 1))
        fi
        sleep 2
    done
    
    if [ "$health_checks" -ge 3 ]; then
        log "Health checks passed ($health_checks/$max_checks)"
        return 0
    else
        error "Health checks failed ($health_checks/$max_checks)"
        return 1
    fi
}

# Main deployment function
deploy() {
    if [ -z "$NEW_VERSION" ]; then
        error "NEW_VERSION is required. Set it as environment variable."
        exit 1
    fi
    
    log "=== Zero-Downtime Deployment ==="
    log "Version: $NEW_VERSION"
    log "Type: $DEPLOYMENT_TYPE"
    
    case "$DEPLOYMENT_TYPE" in
        kubernetes)
            deploy_kubernetes_zero_downtime
            ;;
        docker-compose)
            deploy_docker_compose_zero_downtime
            ;;
        *)
            error "Unsupported deployment type: $DEPLOYMENT_TYPE"
            exit 1
            ;;
    esac
    
    # Validate deployment
    if validate_deployment; then
        log "=== Zero-Downtime Deployment Completed Successfully ==="
    else
        error "Deployment validation failed. Consider rollback."
        exit 1
    fi
}

# Main command handler
case "${1:-deploy}" in
    deploy)
        deploy
        ;;
    validate)
        validate_deployment
        ;;
    *)
        echo "Usage: $0 {deploy|validate}"
        echo ""
        echo "Environment Variables:"
        echo "  NEW_VERSION       - New version to deploy (required)"
        echo "  DEPLOYMENT_TYPE   - kubernetes or docker-compose"
        echo "  NAMESPACE         - Kubernetes namespace"
        echo "  APP_NAME          - Application name"
        echo "  MAX_UNHEALTHY     - Max unhealthy pods during rollout"
        echo "  MIN_READY         - Min ready pods during rollout"
        exit 1
        ;;
esac


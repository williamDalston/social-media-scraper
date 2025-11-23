#!/bin/bash

# Detailed Rollback Procedures
# Comprehensive rollback automation and procedures

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
ROLLBACK_VERSION="${ROLLBACK_VERSION:-}"
AUTO_ROLLBACK="${AUTO_ROLLBACK:-false}"

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

# Function to get current version
get_current_version() {
    if [ "$DEPLOYMENT_TYPE" = "kubernetes" ]; then
        kubectl get deployment ${APP_NAME} -n ${NAMESPACE} -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null | cut -d: -f2 || echo "unknown"
    else
        docker-compose images app 2>/dev/null | tail -1 | awk '{print $2}' || echo "unknown"
    fi
}

# Function to get rollback history
get_rollback_history() {
    log "=== Rollback History ==="
    
    if [ "$DEPLOYMENT_TYPE" = "kubernetes" ]; then
        kubectl rollout history deployment/${APP_NAME} -n ${NAMESPACE}
    else
        info "Rollback history not available for Docker Compose"
    fi
}

# Function to rollback to previous version (Kubernetes)
rollback_kubernetes() {
    local target_revision=${1:-}
    
    log "=== Rolling Back Deployment ==="
    
    local current_version=$(get_current_version)
    log "Current version: $current_version"
    
    if [ -n "$target_revision" ]; then
        log "Rolling back to revision: $target_revision"
        kubectl rollout undo deployment/${APP_NAME} -n ${NAMESPACE} --to-revision=$target_revision
    else
        log "Rolling back to previous revision"
        kubectl rollout undo deployment/${APP_NAME} -n ${NAMESPACE}
    fi
    
    # Wait for rollback to complete
    log "Waiting for rollback to complete..."
    kubectl rollout status deployment/${APP_NAME} -n ${NAMESPACE} --timeout=10m
    
    local new_version=$(get_current_version)
    log "Rolled back to version: $new_version"
    
    # Verify rollback
    log "Verifying rollback..."
    sleep 10
    
    if kubectl get pods -n ${NAMESPACE} -l app=${APP_NAME} --field-selector=status.phase=Running | grep -q Running; then
        log "Rollback successful!"
        return 0
    else
        error "Rollback verification failed"
        return 1
    fi
}

# Function to rollback to specific version (Kubernetes)
rollback_to_version() {
    local target_version=$1
    
    if [ -z "$target_version" ]; then
        error "Target version required"
        exit 1
    fi
    
    log "Rolling back to specific version: $target_version"
    
    # Update deployment to target version
    kubectl set image deployment/${APP_NAME} app=${IMAGE_REPOSITORY}:${target_version} -n ${NAMESPACE}
    
    # Wait for rollout
    kubectl rollout status deployment/${APP_NAME} -n ${NAMESPACE} --timeout=10m
    
    log "Rollback to version $target_version completed"
}

# Function to rollback (Docker Compose)
rollback_docker_compose() {
    log "=== Rolling Back Docker Compose Deployment ==="
    
    # Use blue-green rollback
    if [ -f "${PROJECT_DIR}/scripts/blue-green-deploy.sh" ]; then
        "${PROJECT_DIR}/scripts/blue-green-deploy.sh" rollback
    else
        # Fallback: pull previous image and restart
        warning "Manual rollback required for Docker Compose"
        info "Steps:"
        info "1. Update docker-compose.yml with previous image tag"
        info "2. Run: docker-compose pull"
        info "3. Run: docker-compose up -d"
    fi
}

# Function to create rollback plan
create_rollback_plan() {
    local plan_file="${PROJECT_DIR}/rollback-plan-$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "Rollback Plan"
        echo "Generated: $(date)"
        echo "================================"
        echo ""
        echo "Current Deployment:"
        echo "  Type: $DEPLOYMENT_TYPE"
        echo "  Namespace: $NAMESPACE"
        echo "  App: $APP_NAME"
        echo "  Current Version: $(get_current_version)"
        echo ""
        echo "Rollback Options:"
        if [ "$DEPLOYMENT_TYPE" = "kubernetes" ]; then
            echo "  1. Rollback to previous revision"
            echo "  2. Rollback to specific revision"
            echo "  3. Rollback to specific version"
            echo ""
            echo "Available Revisions:"
            kubectl rollout history deployment/${APP_NAME} -n ${NAMESPACE} 2>/dev/null || echo "  (Unable to retrieve)"
        else
            echo "  1. Use blue-green rollback script"
            echo "  2. Manual rollback via docker-compose"
        fi
        echo ""
        echo "Rollback Steps:"
        echo "  1. Identify target version/revision"
        echo "  2. Execute rollback command"
        echo "  3. Verify deployment health"
        echo "  4. Run smoke tests"
        echo "  5. Monitor for issues"
    } > "$plan_file"
    
    log "Rollback plan created: $plan_file"
    cat "$plan_file"
}

# Function to execute rollback
execute_rollback() {
    local target=${1:-previous}
    
    log "=== Executing Rollback ==="
    
    # Confirm rollback
    warning "WARNING: This will rollback the current deployment!"
    read -p "Are you sure you want to proceed? (yes/no): " CONFIRM
    
    if [ "$CONFIRM" != "yes" ]; then
        log "Rollback cancelled"
        return 1
    fi
    
    case "$DEPLOYMENT_TYPE" in
        kubernetes)
            if [ "$target" = "previous" ]; then
                rollback_kubernetes
            elif [[ "$target" =~ ^[0-9]+$ ]]; then
                rollback_kubernetes "$target"
            else
                rollback_to_version "$target"
            fi
            ;;
        docker-compose)
            rollback_docker_compose
            ;;
        *)
            error "Unsupported deployment type: $DEPLOYMENT_TYPE"
            exit 1
            ;;
    esac
    
    # Verify rollback
    log "Verifying rollback..."
    sleep 10
    
    if [ -f "${PROJECT_DIR}/scripts/smoke-tests.sh" ]; then
        log "Running smoke tests after rollback..."
        "${PROJECT_DIR}/scripts/smoke-tests.sh" all || warning "Some smoke tests failed"
    fi
    
    log "Rollback completed"
}

# Main command handler
case "${1:-help}" in
    execute)
        execute_rollback "${2:-previous}"
        ;;
    plan)
        create_rollback_plan
        ;;
    history)
        get_rollback_history
        ;;
    current)
        get_current_version
        ;;
    *)
        echo "Usage: $0 {execute|plan|history|current} [args]"
        echo ""
        echo "Commands:"
        echo "  execute [target]  - Execute rollback (previous, revision#, or version)"
        echo "  plan              - Create rollback plan"
        echo "  history           - Show rollback history"
        echo "  current           - Show current version"
        echo ""
        echo "Examples:"
        echo "  $0 execute previous     # Rollback to previous revision"
        echo "  $0 execute 3           # Rollback to revision 3"
        echo "  $0 execute v1.0.0      # Rollback to version v1.0.0"
        exit 1
        ;;
esac


#!/bin/bash

# Automated Deployment Script
# Complete deployment automation with validation and rollback

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
LOG_FILE="${PROJECT_DIR}/logs/deploy-$(date +%Y%m%d_%H%M%S).log"

# Create logs directory
mkdir -p "$(dirname "$LOG_FILE")"

# Default values
DEPLOYMENT_TYPE="${DEPLOYMENT_TYPE:-kubernetes}"
ENVIRONMENT="${ENVIRONMENT:-staging}"
NEW_VERSION="${NEW_VERSION:-}"
AUTO_ROLLBACK="${AUTO_ROLLBACK:-true}"
VALIDATE_DEPLOYMENT="${VALIDATE_DEPLOYMENT:-true}"
ZERO_DOWNTIME="${ZERO_DOWNTIME:-true}"

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

info() {
    local message="[INFO] $1"
    echo -e "${BLUE}${message}${NC}" | tee -a "$LOG_FILE"
}

# Function to pre-deployment checks
pre_deployment_checks() {
    log "=== Pre-Deployment Checks ==="
    
    # Check required variables
    if [ -z "$NEW_VERSION" ]; then
        error "NEW_VERSION is required"
        exit 1
    fi
    
    # Check deployment type
    if [ "$DEPLOYMENT_TYPE" = "kubernetes" ] && ! command -v kubectl &> /dev/null; then
        error "kubectl not found"
        exit 1
    fi
    
    if [ "$DEPLOYMENT_TYPE" = "docker-compose" ] && ! command -v docker-compose &> /dev/null; then
        error "docker-compose not found"
        exit 1
    fi
    
    # Check connectivity
    if [ "$DEPLOYMENT_TYPE" = "kubernetes" ]; then
        if ! kubectl cluster-info >/dev/null 2>&1; then
            error "Kubernetes cluster not accessible"
            exit 1
        fi
    fi
    
    log "Pre-deployment checks passed"
}

# Function to backup before deployment
backup_before_deploy() {
    log "=== Creating Backup ==="
    
    if [ -f "${PROJECT_DIR}/scripts/backup_db.sh" ]; then
        "${PROJECT_DIR}/scripts/backup_db.sh" || warning "Backup failed, but continuing deployment"
    else
        warning "Backup script not found"
    fi
}

# Function to deploy
deploy() {
    log "=== Deploying Version $NEW_VERSION ==="
    
    if [ "$ZERO_DOWNTIME" = "true" ] && [ -f "${PROJECT_DIR}/scripts/zero-downtime-deploy.sh" ]; then
        log "Using zero-downtime deployment"
        "${PROJECT_DIR}/scripts/zero-downtime-deploy.sh" deploy
    elif [ -f "${PROJECT_DIR}/scripts/deploy.sh" ]; then
        log "Using standard deployment"
        "${PROJECT_DIR}/scripts/deploy.sh"
    else
        error "No deployment script found"
        exit 1
    fi
}

# Function to validate deployment
validate() {
    if [ "$VALIDATE_DEPLOYMENT" != "true" ]; then
        return 0
    fi
    
    log "=== Validating Deployment ==="
    
    if [ -f "${PROJECT_DIR}/scripts/deployment-validator.sh" ]; then
        if "${PROJECT_DIR}/scripts/deployment-validator.sh" all; then
            log "Deployment validation passed"
            return 0
        else
            error "Deployment validation failed"
            return 1
        fi
    else
        warning "Deployment validator not found, skipping validation"
        return 0
    fi
}

# Function to rollback on failure
rollback_on_failure() {
    if [ "$AUTO_ROLLBACK" != "true" ]; then
        return 0
    fi
    
    error "=== Deployment Failed - Initiating Rollback ==="
    
    if [ -f "${PROJECT_DIR}/scripts/rollback-procedures.sh" ]; then
        "${PROJECT_DIR}/scripts/rollback-procedures.sh" execute previous || {
            error "Rollback failed. Manual intervention required."
            exit 1
        }
    else
        error "Rollback script not found. Manual rollback required."
        exit 1
    fi
}

# Function to post-deployment tasks
post_deployment() {
    log "=== Post-Deployment Tasks ==="
    
    # Run smoke tests
    if [ -f "${PROJECT_DIR}/scripts/smoke-tests.sh" ]; then
        log "Running smoke tests..."
        "${PROJECT_DIR}/scripts/smoke-tests.sh" all || warning "Some smoke tests failed"
    fi
    
    # Monitor deployment
    if [ -f "${PROJECT_DIR}/scripts/auto-rollback.sh" ]; then
        log "Starting deployment monitoring..."
        "${PROJECT_DIR}/scripts/auto-rollback.sh" monitor &
        local monitor_pid=$!
        info "Monitoring started (PID: $monitor_pid)"
    fi
}

# Main deployment function
main() {
    log "=== Automated Deployment Started ==="
    log "Environment: $ENVIRONMENT"
    log "Version: $NEW_VERSION"
    log "Type: $DEPLOYMENT_TYPE"
    log "Log file: $LOG_FILE"
    echo ""
    
    # Pre-deployment checks
    if ! pre_deployment_checks; then
        exit 1
    fi
    
    # Backup
    backup_before_deploy
    
    # Deploy
    if ! deploy; then
        rollback_on_failure
        exit 1
    fi
    
    # Validate
    if ! validate; then
        rollback_on_failure
        exit 1
    fi
    
    # Post-deployment
    post_deployment
    
    log "=== Automated Deployment Completed Successfully ==="
    log "Deployment log: $LOG_FILE"
}

# Trap errors
trap 'rollback_on_failure; exit 1' ERR

# Run main function
main


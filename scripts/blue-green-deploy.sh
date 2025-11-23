#!/bin/bash

# Blue-Green Deployment Script
# Deploys new version alongside existing version, then switches traffic

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
NEW_VERSION="${NEW_VERSION:-}"
CURRENT_COLOR="${CURRENT_COLOR:-blue}"
NEW_COLOR="${NEW_COLOR:-green}"
SERVICE_NAME="${SERVICE_NAME:-${APP_NAME}}"

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

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to get current active color
get_active_color() {
    if [ "$DEPLOYMENT_TYPE" = "kubernetes" ]; then
        if command_exists kubectl; then
            # Check service selector to determine active color
            SELECTOR=$(kubectl get svc "$SERVICE_NAME" -n "$NAMESPACE" -o jsonpath='{.spec.selector.color}' 2>/dev/null || echo "")
            if [ -n "$SELECTOR" ]; then
                echo "$SELECTOR"
            else
                echo "$CURRENT_COLOR"
            fi
        fi
    elif [ "$DEPLOYMENT_TYPE" = "docker-compose" ]; then
        # For docker-compose, check which service is running
        if docker-compose ps | grep -q "${APP_NAME}-blue"; then
            echo "blue"
        else
            echo "green"
        fi
    else
        echo "$CURRENT_COLOR"
    fi
}

# Function to deploy new version (Kubernetes)
deploy_kubernetes() {
    log "Deploying new version to Kubernetes..."
    
    ACTIVE_COLOR=$(get_active_color)
    if [ "$ACTIVE_COLOR" = "blue" ]; then
        NEW_COLOR="green"
    else
        NEW_COLOR="blue"
    fi
    
    info "Current active color: $ACTIVE_COLOR"
    info "Deploying to: $NEW_COLOR"
    
    # Create new deployment with color label
    kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ${APP_NAME}-${NEW_COLOR}
  namespace: ${NAMESPACE}
  labels:
    app: ${APP_NAME}
    color: ${NEW_COLOR}
spec:
  replicas: ${REPLICAS:-3}
  selector:
    matchLabels:
      app: ${APP_NAME}
      color: ${NEW_COLOR}
  template:
    metadata:
      labels:
        app: ${APP_NAME}
        color: ${NEW_COLOR}
        version: ${NEW_VERSION}
    spec:
      containers:
      - name: app
        image: ${IMAGE_REPOSITORY}:${NEW_VERSION}
        imagePullPolicy: Always
        ports:
        - containerPort: 5000
        env:
        - name: ENVIRONMENT
          value: ${ENVIRONMENT:-production}
        livenessProbe:
          httpGet:
            path: /health/live
            port: 5000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 5000
          initialDelaySeconds: 10
          periodSeconds: 5
EOF
    
    # Wait for new deployment to be ready
    log "Waiting for new deployment to be ready..."
    kubectl rollout status deployment/${APP_NAME}-${NEW_COLOR} -n ${NAMESPACE} --timeout=5m
    
    if [ $? -eq 0 ]; then
        log "New deployment is ready!"
        return 0
    else
        error "New deployment failed to become ready"
        return 1
    fi
}

# Function to switch traffic (Kubernetes)
switch_traffic_kubernetes() {
    log "Switching traffic to new version..."
    
    ACTIVE_COLOR=$(get_active_color)
    if [ "$ACTIVE_COLOR" = "blue" ]; then
        NEW_COLOR="green"
    else
        NEW_COLOR="blue"
    fi
    
    # Update service selector to point to new color
    kubectl patch service ${SERVICE_NAME} -n ${NAMESPACE} -p "{\"spec\":{\"selector\":{\"color\":\"${NEW_COLOR}\"}}}"
    
    log "Traffic switched to ${NEW_COLOR} deployment"
    
    # Wait a bit and verify
    sleep 10
    
    # Verify new deployment is receiving traffic
    log "Verifying new deployment..."
    kubectl get pods -n ${NAMESPACE} -l app=${APP_NAME},color=${NEW_COLOR}
}

# Function to rollback (Kubernetes)
rollback_kubernetes() {
    warning "Rolling back to previous version..."
    
    ACTIVE_COLOR=$(get_active_color)
    if [ "$ACTIVE_COLOR" = "blue" ]; then
        PREVIOUS_COLOR="green"
    else
        PREVIOUS_COLOR="blue"
    fi
    
    # Switch service back to previous color
    kubectl patch service ${SERVICE_NAME} -n ${NAMESPACE} -p "{\"spec\":{\"selector\":{\"color\":\"${PREVIOUS_COLOR}\"}}}"
    
    log "Rolled back to ${PREVIOUS_COLOR} deployment"
    
    # Optionally delete the failed deployment
    read -p "Delete failed ${ACTIVE_COLOR} deployment? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kubectl delete deployment ${APP_NAME}-${ACTIVE_COLOR} -n ${NAMESPACE}
    fi
}

# Function to deploy new version (Docker Compose)
deploy_docker_compose() {
    log "Deploying new version with Docker Compose..."
    
    ACTIVE_COLOR=$(get_active_color)
    if [ "$ACTIVE_COLOR" = "blue" ]; then
        NEW_COLOR="green"
        OLD_SERVICE="${APP_NAME}-blue"
        NEW_SERVICE="${APP_NAME}-green"
    else
        NEW_COLOR="blue"
        OLD_SERVICE="${APP_NAME}-green"
        NEW_SERVICE="${APP_NAME}-blue"
    fi
    
    # Start new service
    docker-compose up -d ${NEW_SERVICE}
    
    # Wait for health check
    log "Waiting for new service to be healthy..."
    for i in {1..30}; do
        if docker-compose exec -T ${NEW_SERVICE} curl -f http://localhost:5000/health >/dev/null 2>&1; then
            log "New service is healthy!"
            return 0
        fi
        sleep 2
    done
    
    error "New service failed health check"
    return 1
}

# Function to switch traffic (Docker Compose)
switch_traffic_docker_compose() {
    log "Switching traffic to new version..."
    
    # Update nginx/haproxy configuration or use docker-compose service selection
    # This is a simplified version - in production, use a load balancer config
    
    ACTIVE_COLOR=$(get_active_color)
    if [ "$ACTIVE_COLOR" = "blue" ]; then
        NEW_COLOR="green"
        OLD_SERVICE="${APP_NAME}-blue"
        NEW_SERVICE="${APP_NAME}-green"
    else
        NEW_COLOR="blue"
        OLD_SERVICE="${APP_NAME}-green"
        NEW_SERVICE="${APP_NAME}-blue"
    fi
    
    # Stop old service (or scale down)
    docker-compose stop ${OLD_SERVICE}
    
    log "Traffic switched to ${NEW_SERVICE}"
}

# Main deployment function
deploy() {
    if [ -z "$NEW_VERSION" ]; then
        error "NEW_VERSION is required. Set it as environment variable or pass as argument."
        exit 1
    fi
    
    log "Starting blue-green deployment..."
    log "New version: $NEW_VERSION"
    log "Deployment type: $DEPLOYMENT_TYPE"
    
    case "$DEPLOYMENT_TYPE" in
        kubernetes)
            deploy_kubernetes
            if [ $? -eq 0 ]; then
                read -p "Switch traffic to new version? (y/n): " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    switch_traffic_kubernetes
                else
                    warning "New version deployed but traffic not switched. Manual switch required."
                fi
            else
                error "Deployment failed. Not switching traffic."
                exit 1
            fi
            ;;
        docker-compose)
            deploy_docker_compose
            if [ $? -eq 0 ]; then
                read -p "Switch traffic to new version? (y/n): " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    switch_traffic_docker_compose
                else
                    warning "New version deployed but traffic not switched."
                fi
            else
                error "Deployment failed."
                exit 1
            fi
            ;;
        *)
            error "Unsupported deployment type: $DEPLOYMENT_TYPE"
            exit 1
            ;;
    esac
    
    log "Blue-green deployment completed!"
}

# Main command handler
case "${1:-deploy}" in
    deploy)
        deploy
        ;;
    switch)
        if [ "$DEPLOYMENT_TYPE" = "kubernetes" ]; then
            switch_traffic_kubernetes
        elif [ "$DEPLOYMENT_TYPE" = "docker-compose" ]; then
            switch_traffic_docker_compose
        fi
        ;;
    rollback)
        if [ "$DEPLOYMENT_TYPE" = "kubernetes" ]; then
            rollback_kubernetes
        else
            error "Rollback not implemented for $DEPLOYMENT_TYPE"
        fi
        ;;
    status)
        ACTIVE_COLOR=$(get_active_color)
        info "Active deployment color: $ACTIVE_COLOR"
        if [ "$DEPLOYMENT_TYPE" = "kubernetes" ]; then
            kubectl get deployments -n ${NAMESPACE} -l app=${APP_NAME}
            kubectl get pods -n ${NAMESPACE} -l app=${APP_NAME}
        fi
        ;;
    *)
        echo "Usage: $0 {deploy|switch|rollback|status}"
        echo ""
        echo "Commands:"
        echo "  deploy    - Deploy new version (blue-green)"
        echo "  switch    - Switch traffic to new version"
        echo "  rollback  - Rollback to previous version"
        echo "  status    - Show deployment status"
        echo ""
        echo "Environment Variables:"
        echo "  NEW_VERSION       - New version tag (required for deploy)"
        echo "  DEPLOYMENT_TYPE   - kubernetes or docker-compose"
        echo "  NAMESPACE         - Kubernetes namespace"
        echo "  APP_NAME          - Application name"
        echo "  IMAGE_REPOSITORY  - Docker image repository"
        exit 1
        ;;
esac


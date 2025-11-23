#!/bin/bash

# Scaling Procedures and Automation
# Handles both horizontal and vertical scaling

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
SCALE_TYPE="${SCALE_TYPE:-horizontal}"  # horizontal or vertical
TARGET_REPLICAS="${TARGET_REPLICAS:-}"
TARGET_CPU="${TARGET_CPU:-}"
TARGET_MEMORY="${TARGET_MEMORY:-}"

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

# Function to get current replicas
get_current_replicas() {
    if [ "$DEPLOYMENT_TYPE" = "kubernetes" ]; then
        kubectl get deployment ${APP_NAME} -n ${NAMESPACE} -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "0"
    else
        docker-compose ps app 2>/dev/null | grep -c "Up" || echo "0"
    fi
}

# Function to scale horizontally (Kubernetes)
scale_horizontal_kubernetes() {
    local target=$1
    
    if [ -z "$target" ]; then
        error "Target replicas required"
        exit 1
    fi
    
    local current=$(get_current_replicas)
    
    log "Scaling from $current to $target replicas"
    
    kubectl scale deployment ${APP_NAME} -n ${NAMESPACE} --replicas=$target
    
    # Wait for scaling to complete
    log "Waiting for scaling to complete..."
    kubectl rollout status deployment/${APP_NAME} -n ${NAMESPACE} --timeout=5m
    
    # Verify scaling
    local new_count=$(get_current_replicas)
    if [ "$new_count" -eq "$target" ]; then
        log "Scaling successful! Current replicas: $new_count"
        return 0
    else
        error "Scaling verification failed. Expected $target, got $new_count"
        return 1
    fi
}

# Function to scale horizontally (Docker Compose)
scale_horizontal_docker_compose() {
    local target=$1
    
    if [ -z "$target" ]; then
        error "Target replicas required"
        exit 1
    fi
    
    log "Scaling to $target replicas"
    
    docker-compose up -d --scale app=$target
    
    log "Scaling completed"
}

# Function to scale vertically (Kubernetes)
scale_vertical_kubernetes() {
    local cpu=$1
    local memory=$2
    
    if [ -z "$cpu" ] || [ -z "$memory" ]; then
        error "CPU and memory required for vertical scaling"
        exit 1
    fi
    
    log "Scaling vertically: CPU=$cpu, Memory=$memory"
    
    # Update resource limits
    kubectl set resources deployment ${APP_NAME} \
        -n ${NAMESPACE} \
        --limits=cpu=${cpu},memory=${memory} \
        --requests=cpu=${cpu},memory=${memory}
    
    # Restart pods to apply new resources
    kubectl rollout restart deployment/${APP_NAME} -n ${NAMESPACE}
    kubectl rollout status deployment/${APP_NAME} -n ${NAMESPACE} --timeout=5m
    
    log "Vertical scaling completed"
}

# Function to auto-scale based on metrics
auto_scale() {
    log "Auto-scaling based on metrics..."
    
    # Get current metrics
    local cpu_usage=$(kubectl top pods -n ${NAMESPACE} -l app=${APP_NAME} --no-headers 2>/dev/null | awk '{sum+=$2; count++} END {print sum/count}' || echo "0")
    local current_replicas=$(get_current_replicas)
    
    info "Current CPU usage: ${cpu_usage}%"
    info "Current replicas: $current_replicas"
    
    # Determine target replicas
    local target_replicas=$current_replicas
    
    if (( $(echo "$cpu_usage > 70" | bc -l) )); then
        target_replicas=$((current_replicas + 1))
        log "CPU usage high, scaling up to $target_replicas"
    elif (( $(echo "$cpu_usage < 30" | bc -l) )) && [ "$current_replicas" -gt 1 ]; then
        target_replicas=$((current_replicas - 1))
        log "CPU usage low, scaling down to $target_replicas"
    else
        log "CPU usage normal, no scaling needed"
        return 0
    fi
    
    # Execute scaling
    if [ "$DEPLOYMENT_TYPE" = "kubernetes" ]; then
        scale_horizontal_kubernetes $target_replicas
    else
        scale_horizontal_docker_compose $target_replicas
    fi
}

# Main command handler
case "${1:-help}" in
    up)
        if [ "$SCALE_TYPE" = "horizontal" ]; then
            if [ -n "$TARGET_REPLICAS" ]; then
                if [ "$DEPLOYMENT_TYPE" = "kubernetes" ]; then
                    scale_horizontal_kubernetes $TARGET_REPLICAS
                else
                    scale_horizontal_docker_compose $TARGET_REPLICAS
                fi
            else
                error "TARGET_REPLICAS required for horizontal scaling"
                exit 1
            fi
        else
            if [ -n "$TARGET_CPU" ] && [ -n "$TARGET_MEMORY" ]; then
                scale_vertical_kubernetes $TARGET_CPU $TARGET_MEMORY
            else
                error "TARGET_CPU and TARGET_MEMORY required for vertical scaling"
                exit 1
            fi
        fi
        ;;
    down)
        local current=$(get_current_replicas)
        local target=$((current - 1))
        
        if [ "$target" -lt 1 ]; then
            error "Cannot scale below 1 replica"
            exit 1
        fi
        
        if [ "$DEPLOYMENT_TYPE" = "kubernetes" ]; then
            scale_horizontal_kubernetes $target
        else
            scale_horizontal_docker_compose $target
        fi
        ;;
    auto)
        auto_scale
        ;;
    status)
        local current=$(get_current_replicas)
        info "Current replicas: $current"
        
        if [ "$DEPLOYMENT_TYPE" = "kubernetes" ]; then
            kubectl get pods -n ${NAMESPACE} -l app=${APP_NAME}
            kubectl top pods -n ${NAMESPACE} -l app=${APP_NAME} 2>/dev/null || warning "Metrics not available"
        fi
        ;;
    *)
        echo "Usage: $0 {up|down|auto|status}"
        echo ""
        echo "Commands:"
        echo "  up      - Scale up (requires TARGET_REPLICAS or TARGET_CPU/TARGET_MEMORY)"
        echo "  down    - Scale down by 1"
        echo "  auto    - Auto-scale based on metrics"
        echo "  status  - Show current scaling status"
        echo ""
        echo "Environment Variables:"
        echo "  SCALE_TYPE      - horizontal or vertical"
        echo "  TARGET_REPLICAS - Target number of replicas (horizontal)"
        echo "  TARGET_CPU      - Target CPU (vertical)"
        echo "  TARGET_MEMORY   - Target memory (vertical)"
        exit 1
        ;;
esac


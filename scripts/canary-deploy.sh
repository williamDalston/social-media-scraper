#!/bin/bash

# Canary Deployment Script
# Gradually shifts traffic from old to new version

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
DEPLOYMENT_TYPE="${DEPLOYMENT_TYPE:-kubernetes}"
NAMESPACE="${NAMESPACE:-social-media-scraper}"
APP_NAME="${APP_NAME:-social-media-scraper-app}"
NEW_VERSION="${NEW_VERSION:-}"
CANARY_PERCENTAGE="${CANARY_PERCENTAGE:-10}"
STABLE_PERCENTAGE="${STABLE_PERCENTAGE:-90}"

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

# Function to deploy canary (Kubernetes with Istio)
deploy_canary_istio() {
    log "Deploying canary version with Istio..."
    
    # Create canary deployment
    kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ${APP_NAME}-canary
  namespace: ${NAMESPACE}
  labels:
    app: ${APP_NAME}
    version: canary
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ${APP_NAME}
      version: canary
  template:
    metadata:
      labels:
        app: ${APP_NAME}
        version: canary
    spec:
      containers:
      - name: app
        image: ${IMAGE_REPOSITORY}:${NEW_VERSION}
        imagePullPolicy: Always
        ports:
        - containerPort: 5000
EOF
    
    # Create VirtualService for traffic splitting
    kubectl apply -f - <<EOF
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: ${APP_NAME}
  namespace: ${NAMESPACE}
spec:
  hosts:
  - ${APP_NAME}
  http:
  - match:
    - headers:
        canary:
          exact: "true"
    route:
    - destination:
        host: ${APP_NAME}
        subset: canary
      weight: 100
  - route:
    - destination:
        host: ${APP_NAME}
        subset: stable
      weight: ${STABLE_PERCENTAGE}
    - destination:
        host: ${APP_NAME}
        subset: canary
      weight: ${CANARY_PERCENTAGE}
EOF
    
    log "Canary deployed with ${CANARY_PERCENTAGE}% traffic"
}

# Function to increase canary traffic
increase_canary_traffic() {
    local new_percentage=$1
    
    if [ -z "$new_percentage" ]; then
        error "Percentage required"
        exit 1
    fi
    
    if [ "$new_percentage" -lt 0 ] || [ "$new_percentage" -gt 100 ]; then
        error "Percentage must be between 0 and 100"
        exit 1
    fi
    
    local stable_percentage=$((100 - new_percentage))
    
    log "Increasing canary traffic to ${new_percentage}%..."
    
    kubectl apply -f - <<EOF
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: ${APP_NAME}
  namespace: ${NAMESPACE}
spec:
  hosts:
  - ${APP_NAME}
  http:
  - route:
    - destination:
        host: ${APP_NAME}
        subset: stable
      weight: ${stable_percentage}
    - destination:
        host: ${APP_NAME}
        subset: canary
      weight: ${new_percentage}
EOF
    
    log "Canary traffic increased to ${new_percentage}%"
}

# Function to promote canary to stable
promote_canary() {
    log "Promoting canary to stable..."
    
    # Scale up canary to full replicas
    kubectl scale deployment ${APP_NAME}-canary -n ${NAMESPACE} --replicas=3
    
    # Update VirtualService to route 100% to canary
    kubectl apply -f - <<EOF
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: ${APP_NAME}
  namespace: ${NAMESPACE}
spec:
  hosts:
  - ${APP_NAME}
  http:
  - route:
    - destination:
        host: ${APP_NAME}
        subset: canary
      weight: 100
EOF
    
    # Update stable deployment to new version
    kubectl set image deployment/${APP_NAME}-stable app=${IMAGE_REPOSITORY}:${NEW_VERSION} -n ${NAMESPACE}
    kubectl rollout status deployment/${APP_NAME}-stable -n ${NAMESPACE}
    
    # Switch traffic back to stable
    kubectl apply -f - <<EOF
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: ${APP_NAME}
  namespace: ${NAMESPACE}
spec:
  hosts:
  - ${APP_NAME}
  http:
  - route:
    - destination:
        host: ${APP_NAME}
        subset: stable
      weight: 100
EOF
    
    # Delete canary deployment
    kubectl delete deployment ${APP_NAME}-canary -n ${NAMESPACE}
    
    log "Canary promoted to stable"
}

# Function to rollback canary
rollback_canary() {
    warning "Rolling back canary deployment..."
    
    # Route all traffic back to stable
    kubectl apply -f - <<EOF
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: ${APP_NAME}
  namespace: ${NAMESPACE}
spec:
  hosts:
  - ${APP_NAME}
  http:
  - route:
    - destination:
        host: ${APP_NAME}
        subset: stable
      weight: 100
EOF
    
    # Delete canary deployment
    kubectl delete deployment ${APP_NAME}-canary -n ${NAMESPACE}
    
    log "Canary rolled back"
}

# Main command handler
case "${1:-deploy}" in
    deploy)
        if [ -z "$NEW_VERSION" ]; then
            error "NEW_VERSION is required"
            exit 1
        fi
        deploy_canary_istio
        ;;
    increase)
        increase_canary_traffic "${2:-50}"
        ;;
    promote)
        promote_canary
        ;;
    rollback)
        rollback_canary
        ;;
    status)
        info "Canary deployment status:"
        kubectl get deployments -n ${NAMESPACE} -l app=${APP_NAME}
        kubectl get virtualservice ${APP_NAME} -n ${NAMESPACE} -o yaml
        ;;
    *)
        echo "Usage: $0 {deploy|increase|promote|rollback|status} [args]"
        echo ""
        echo "Commands:"
        echo "  deploy <version>     - Deploy canary version"
        echo "  increase <percent>   - Increase canary traffic percentage"
        echo "  promote              - Promote canary to stable"
        echo "  rollback             - Rollback canary deployment"
        echo "  status               - Show canary deployment status"
        exit 1
        ;;
esac


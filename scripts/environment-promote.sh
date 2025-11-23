#!/bin/bash

# Environment Promotion Workflow
# Promotes application from one environment to another

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
FROM_ENV="${FROM_ENV:-development}"
TO_ENV="${TO_ENV:-staging}"
VERSION="${VERSION:-}"
SKIP_TESTS="${SKIP_TESTS:-false}"

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

# Function to validate environment
validate_environment() {
    local env=$1
    
    case "$env" in
        development|staging|production)
            return 0
            ;;
        *)
            error "Invalid environment: $env"
            error "Valid environments: development, staging, production"
            return 1
            ;;
    esac
}

# Function to check promotion path
check_promotion_path() {
    local from=$1
    local to=$2
    
    case "$from:$to" in
        development:staging|staging:production)
            log "Valid promotion path: $from -> $to"
            return 0
            ;;
        development:production)
            warning "Skipping staging environment. Are you sure?"
            read -p "Continue? (yes/no): " CONFIRM
            if [ "$CONFIRM" != "yes" ]; then
                return 1
            fi
            return 0
            ;;
        *)
            error "Invalid promotion path: $from -> $to"
            error "Valid paths: development->staging, staging->production"
            return 1
            ;;
    esac
}

# Function to run tests
run_tests() {
    if [ "$SKIP_TESTS" = "true" ]; then
        warning "Skipping tests"
        return 0
    fi
    
    log "Running tests..."
    
    if [ -f "${PROJECT_DIR}/scripts/smoke-tests.sh" ]; then
        BASE_URL="${BASE_URL:-http://localhost:5000}" "${PROJECT_DIR}/scripts/smoke-tests.sh" all
    else
        warning "Smoke tests script not found"
    fi
}

# Function to promote (Kubernetes/Helm)
promote_helm() {
    log "Promoting with Helm..."
    
    local values_file="config/values-${TO_ENV}.yaml"
    
    if [ ! -f "$values_file" ]; then
        error "Values file not found: $values_file"
        return 1
    fi
    
    # Get image tag from source environment or use provided version
    local image_tag="${VERSION:-$(helm get values social-media-scraper -n ${FROM_ENV} -o json | jq -r '.image.tag' 2>/dev/null || echo 'latest')}"
    
    log "Promoting version: $image_tag"
    
    # Upgrade Helm release
    helm upgrade social-media-scraper ./helm/social-media-scraper \
        -f "$values_file" \
        --set image.tag="$image_tag" \
        --namespace "${TO_ENV}" \
        --create-namespace \
        --wait \
        --timeout 10m
    
    log "Promotion completed"
}

# Function to promote (Docker Compose)
promote_docker_compose() {
    log "Promoting with Docker Compose..."
    
    # Update environment file
    sed -i.bak "s/ENVIRONMENT=.*/ENVIRONMENT=${TO_ENV}/" "${PROJECT_DIR}/.env"
    
    # Pull and restart
    docker-compose pull
    docker-compose up -d
    
    log "Promotion completed"
}

# Function to promote
promote() {
    log "=== Starting Environment Promotion ==="
    log "From: $FROM_ENV"
    log "To: $TO_ENV"
    
    # Validate environments
    if ! validate_environment "$FROM_ENV"; then
        exit 1
    fi
    
    if ! validate_environment "$TO_ENV"; then
        exit 1
    fi
    
    # Check promotion path
    if ! check_promotion_path "$FROM_ENV" "$TO_ENV"; then
        exit 1
    fi
    
    # Run tests in source environment
    log "Running tests in source environment ($FROM_ENV)..."
    if ! run_tests; then
        error "Tests failed in source environment"
        exit 1
    fi
    
    # Promote based on deployment type
    if command -v helm &> /dev/null && [ -f "${PROJECT_DIR}/helm/social-media-scraper/Chart.yaml" ]; then
        promote_helm
    elif [ -f "${PROJECT_DIR}/docker-compose.yml" ]; then
        promote_docker_compose
    else
        error "No deployment method found"
        exit 1
    fi
    
    # Run tests in target environment
    log "Running tests in target environment ($TO_ENV)..."
    sleep 10  # Wait for services to be ready
    if ! run_tests; then
        error "Tests failed in target environment"
        error "Consider rolling back"
        exit 1
    fi
    
    log "=== Environment Promotion Completed ==="
}

# Main command handler
case "${1:-promote}" in
    promote)
        promote
        ;;
    *)
        echo "Usage: $0 promote"
        echo ""
        echo "Environment Variables:"
        echo "  FROM_ENV    - Source environment (default: development)"
        echo "  TO_ENV      - Target environment (default: staging)"
        echo "  VERSION     - Version to promote (optional)"
        echo "  SKIP_TESTS  - Skip tests (default: false)"
        exit 1
        ;;
esac


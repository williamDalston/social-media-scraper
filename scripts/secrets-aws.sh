#!/bin/bash

# AWS Secrets Manager Integration
# Manages secrets using AWS Secrets Manager

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SECRET_NAME="${SECRET_NAME:-social-media-scraper-secrets}"
AWS_REGION="${AWS_REGION:-us-east-1}"
ENV_FILE="${ENV_FILE:-.env}"

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

# Function to check AWS CLI
check_aws() {
    if ! command -v aws &> /dev/null; then
        error "AWS CLI not found. Please install AWS CLI."
        return 1
    fi
    
    if ! aws sts get-caller-identity >/dev/null 2>&1; then
        error "AWS credentials not configured"
        return 1
    fi
    
    log "AWS connection successful"
    return 0
}

# Function to read secret from AWS Secrets Manager
read_secret() {
    local key=$1
    
    if ! check_aws; then
        return 1
    fi
    
    local secret_value=$(aws secretsmanager get-secret-value \
        --secret-id "$SECRET_NAME" \
        --region "$AWS_REGION" \
        --query 'SecretString' \
        --output text 2>/dev/null)
    
    if [ -z "$secret_value" ]; then
        error "Secret not found: $SECRET_NAME"
        return 1
    fi
    
    # Parse JSON and get specific key
    if [ -n "$key" ]; then
        echo "$secret_value" | jq -r ".[\"$key\"] // empty"
    else
        echo "$secret_value"
    fi
}

# Function to write secret to AWS Secrets Manager
write_secret() {
    local key=$1
    local value=$2
    
    if ! check_aws; then
        return 1
    fi
    
    # Check if secret exists
    local existing=$(aws secretsmanager describe-secret \
        --secret-id "$SECRET_NAME" \
        --region "$AWS_REGION" \
        --query 'ARN' \
        --output text 2>/dev/null || echo "")
    
    if [ -z "$existing" ]; then
        # Create new secret
        log "Creating new secret: $SECRET_NAME"
        aws secretsmanager create-secret \
            --name "$SECRET_NAME" \
            --description "Secrets for Social Media Scraper" \
            --secret-string "{\"$key\":\"$value\"}" \
            --region "$AWS_REGION" >/dev/null
    else
        # Update existing secret
        local current=$(read_secret)
        local updated=$(echo "$current" | jq --arg k "$key" --arg v "$value" '. + {($k): $v}')
        
        aws secretsmanager update-secret \
            --secret-id "$SECRET_NAME" \
            --secret-string "$updated" \
            --region "$AWS_REGION" >/dev/null
    fi
    
    log "Secret '$key' written to AWS Secrets Manager"
}

# Function to sync secrets from .env to AWS
sync_to_aws() {
    log "Syncing secrets from .env to AWS Secrets Manager..."
    
    if [ ! -f "$ENV_FILE" ]; then
        error "Environment file not found: $ENV_FILE"
        return 1
    fi
    
    # Build JSON object from .env
    local json_secrets="{"
    local first=true
    
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        [[ "$key" =~ ^#.*$ ]] && continue
        [ -z "$key" ] && continue
        
        # Only sync sensitive keys
        if [[ "$key" =~ ^(SECRET_KEY|JWT_SECRET_KEY|DATABASE_URL|.*PASSWORD|.*API_KEY|.*SECRET)$ ]]; then
            if [ "$first" = true ]; then
                first=false
            else
                json_secrets+=","
            fi
            json_secrets+="\"$key\":\"$value\""
        fi
    done < "$ENV_FILE"
    
    json_secrets+="}"
    
    # Check if secret exists
    local existing=$(aws secretsmanager describe-secret \
        --secret-id "$SECRET_NAME" \
        --region "$AWS_REGION" \
        --query 'ARN' \
        --output text 2>/dev/null || echo "")
    
    if [ -z "$existing" ]; then
        # Create new secret
        aws secretsmanager create-secret \
            --name "$SECRET_NAME" \
            --description "Secrets for Social Media Scraper" \
            --secret-string "$json_secrets" \
            --region "$AWS_REGION" >/dev/null
        log "Secret created in AWS Secrets Manager"
    else
        # Update existing secret
        aws secretsmanager update-secret \
            --secret-id "$SECRET_NAME" \
            --secret-string "$json_secrets" \
            --region "$AWS_REGION" >/dev/null
        log "Secret updated in AWS Secrets Manager"
    fi
}

# Function to list secrets
list_secrets() {
    log "Listing secrets from AWS Secrets Manager..."
    
    if ! check_aws; then
        return 1
    fi
    
    local secret_value=$(read_secret)
    if [ -n "$secret_value" ]; then
        echo "$secret_value" | jq -r 'keys[]' || echo "No secrets found"
    else
        error "Secret not found"
        return 1
    fi
}

# Main command handler
case "${1:-help}" in
    sync-to)
        sync_to_aws
        ;;
    read)
        read_secret "${2:-}"
        ;;
    write)
        write_secret "${2:-}" "${3:-}"
        ;;
    list)
        list_secrets
        ;;
    check)
        check_aws
        ;;
    *)
        echo "Usage: $0 {sync-to|read|write|list|check} [args]"
        echo ""
        echo "Commands:"
        echo "  sync-to          - Sync secrets from .env to AWS Secrets Manager"
        echo "  read <key>       - Read a secret (or all if key not provided)"
        echo "  write <key> <value> - Write a secret"
        echo "  list             - List all secret keys"
        echo "  check            - Check AWS connection"
        echo ""
        echo "Environment Variables:"
        echo "  SECRET_NAME      - AWS Secrets Manager secret name"
        echo "  AWS_REGION       - AWS region"
        exit 1
        ;;
esac


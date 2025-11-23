#!/bin/bash

# HashiCorp Vault Secrets Management Integration
# Manages secrets using Vault

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
VAULT_ADDR="${VAULT_ADDR:-http://localhost:8200}"
VAULT_TOKEN="${VAULT_TOKEN:-}"
VAULT_PATH="${VAULT_PATH:-secret/social-media-scraper}"
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

# Function to check Vault connection
check_vault() {
    if ! command -v vault &> /dev/null; then
        error "Vault CLI not found. Please install HashiCorp Vault."
        return 1
    fi
    
    if [ -z "$VAULT_TOKEN" ]; then
        error "VAULT_TOKEN not set"
        return 1
    fi
    
    export VAULT_ADDR
    export VAULT_TOKEN
    
    if vault status >/dev/null 2>&1; then
        log "Vault connection successful"
        return 0
    else
        error "Vault connection failed"
        return 1
    fi
}

# Function to read secret from Vault
read_secret() {
    local key=$1
    
    if ! check_vault; then
        return 1
    fi
    
    vault kv get -field="$key" "$VAULT_PATH" 2>/dev/null || echo ""
}

# Function to write secret to Vault
write_secret() {
    local key=$1
    local value=$2
    
    if ! check_vault; then
        return 1
    fi
    
    # Read existing secrets
    local existing=$(vault kv get -format=json "$VAULT_PATH" 2>/dev/null | jq -r '.data.data // {}' || echo "{}")
    
    # Add/update secret
    local updated=$(echo "$existing" | jq --arg k "$key" --arg v "$value" '. + {($k): $v}')
    
    # Write back
    echo "$updated" | vault kv put "$VAULT_PATH" - >/dev/null
    
    log "Secret '$key' written to Vault"
}

# Function to sync secrets from .env to Vault
sync_to_vault() {
    log "Syncing secrets from .env to Vault..."
    
    if [ ! -f "$ENV_FILE" ]; then
        error "Environment file not found: $ENV_FILE"
        return 1
    fi
    
    # Read .env and sync sensitive values
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        [[ "$key" =~ ^#.*$ ]] && continue
        [ -z "$key" ] && continue
        
        # Only sync sensitive keys
        if [[ "$key" =~ ^(SECRET_KEY|JWT_SECRET_KEY|DATABASE_URL|.*PASSWORD|.*API_KEY|.*SECRET)$ ]]; then
            write_secret "$key" "$value"
        fi
    done < "$ENV_FILE"
    
    log "Secrets synced to Vault"
}

# Function to sync secrets from Vault to .env
sync_from_vault() {
    log "Syncing secrets from Vault to .env..."
    
    if ! check_vault; then
        return 1
    fi
    
    # Get all secrets from Vault
    local secrets=$(vault kv get -format=json "$VAULT_PATH" 2>/dev/null | jq -r '.data.data // {}')
    
    # Update .env file
    while IFS='=' read -r key value; do
        if [[ "$key" =~ ^(SECRET_KEY|JWT_SECRET_KEY|DATABASE_URL|.*PASSWORD|.*API_KEY|.*SECRET)$ ]]; then
            local vault_value=$(echo "$secrets" | jq -r ".[\"$key\"] // empty")
            if [ -n "$vault_value" ]; then
                # Update .env file (simplified - in production use proper parsing)
                sed -i.bak "s/^${key}=.*/${key}=${vault_value}/" "$ENV_FILE" || true
            fi
        fi
    done < "$ENV_FILE"
    
    log "Secrets synced from Vault"
}

# Function to list secrets
list_secrets() {
    log "Listing secrets from Vault..."
    
    if ! check_vault; then
        return 1
    fi
    
    vault kv get -format=json "$VAULT_PATH" 2>/dev/null | jq -r '.data.data | keys[]' || echo "No secrets found"
}

# Main command handler
case "${1:-help}" in
    sync-to)
        sync_to_vault
        ;;
    sync-from)
        sync_from_vault
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
        check_vault
        ;;
    *)
        echo "Usage: $0 {sync-to|sync-from|read|write|list|check} [args]"
        echo ""
        echo "Commands:"
        echo "  sync-to          - Sync secrets from .env to Vault"
        echo "  sync-from        - Sync secrets from Vault to .env"
        echo "  read <key>       - Read a secret from Vault"
        echo "  write <key> <value> - Write a secret to Vault"
        echo "  list             - List all secrets"
        echo "  check            - Check Vault connection"
        echo ""
        echo "Environment Variables:"
        echo "  VAULT_ADDR       - Vault server address"
        echo "  VAULT_TOKEN      - Vault authentication token"
        echo "  VAULT_PATH       - Vault secret path"
        exit 1
        ;;
esac


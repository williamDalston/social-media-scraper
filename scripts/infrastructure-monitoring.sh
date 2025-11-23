#!/bin/bash

# Infrastructure Monitoring
# Monitors infrastructure health and resources

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
MONITORING_DIR="${PROJECT_DIR}/monitoring"

# Create directories
mkdir -p "$MONITORING_DIR"

# Default values
NAMESPACE="${NAMESPACE:-social-media-scraper}"
CLOUD_PROVIDER="${CLOUD_PROVIDER:-aws}"  # aws, gcp, azure

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

# Function to monitor Kubernetes infrastructure
monitor_kubernetes() {
    log "Monitoring Kubernetes infrastructure..."
    
    # Cluster health
    kubectl cluster-info >/dev/null 2>&1 && log "  ✓ Cluster healthy" || error "  ✗ Cluster unhealthy"
    
    # Node status
    local ready_nodes=$(kubectl get nodes --no-headers 2>/dev/null | grep -c " Ready " || echo "0")
    local total_nodes=$(kubectl get nodes --no-headers 2>/dev/null | wc -l | tr -d ' ')
    log "  Nodes: $ready_nodes/$total_nodes ready"
    
    # Pod status
    local running_pods=$(kubectl get pods -n ${NAMESPACE} --field-selector=status.phase=Running --no-headers 2>/dev/null | wc -l | tr -d ' ')
    local total_pods=$(kubectl get pods -n ${NAMESPACE} --no-headers 2>/dev/null | wc -l | tr -d ' ')
    log "  Pods: $running_pods/$total_pods running"
    
    # Resource usage
    if kubectl top nodes >/dev/null 2>&1; then
        log "  Resource usage:"
        kubectl top nodes --no-headers 2>/dev/null | while read node cpu mem; do
            info "    $node: CPU=$cpu, Memory=$mem"
        done
    fi
}

# Function to monitor AWS infrastructure
monitor_aws() {
    log "Monitoring AWS infrastructure..."
    
    if command -v aws &> /dev/null; then
        # EC2 instances
        local running_instances=$(aws ec2 describe-instances --filters "Name=instance-state-name,Values=running" --query 'Reservations[*].Instances[*].InstanceId' --output text 2>/dev/null | wc -w || echo "0")
        log "  Running EC2 instances: $running_instances"
        
        # RDS instances
        local rds_instances=$(aws rds describe-db-instances --query 'DBInstances[*].DBInstanceIdentifier' --output text 2>/dev/null | wc -w || echo "0")
        log "  RDS instances: $rds_instances"
        
        # ElastiCache clusters
        local cache_clusters=$(aws elasticache describe-cache-clusters --query 'CacheClusters[*].CacheClusterId' --output text 2>/dev/null | wc -w || echo "0")
        log "  ElastiCache clusters: $cache_clusters"
    else
        warning "AWS CLI not found"
    fi
}

# Function to monitor GCP infrastructure
monitor_gcp() {
    log "Monitoring GCP infrastructure..."
    
    if command -v gcloud &> /dev/null; then
        # Compute instances
        local instances=$(gcloud compute instances list --format="value(name)" 2>/dev/null | wc -l | tr -d ' ')
        log "  Compute instances: $instances"
        
        # Cloud SQL instances
        local sql_instances=$(gcloud sql instances list --format="value(name)" 2>/dev/null | wc -l | tr -d ' ')
        log "  Cloud SQL instances: $sql_instances"
        
        # Cloud Run services
        local run_services=$(gcloud run services list --format="value(name)" 2>/dev/null | wc -l | tr -d ' ')
        log "  Cloud Run services: $run_services"
    else
        warning "gcloud CLI not found"
    fi
}

# Function to monitor Azure infrastructure
monitor_azure() {
    log "Monitoring Azure infrastructure..."
    
    if command -v az &> /dev/null; then
        # Virtual machines
        local vms=$(az vm list --query "[].name" -o tsv 2>/dev/null | wc -l | tr -d ' ')
        log "  Virtual machines: $vms"
        
        # SQL databases
        local sql_servers=$(az sql server list --query "[].name" -o tsv 2>/dev/null | wc -l | tr -d ' ')
        log "  SQL servers: $sql_servers"
        
        # Container instances
        local containers=$(az container list --query "[].name" -o tsv 2>/dev/null | wc -l | tr -d ' ')
        log "  Container instances: $containers"
    else
        warning "Azure CLI not found"
    fi
}

# Function to generate monitoring report
generate_report() {
    local report_file="${MONITORING_DIR}/infrastructure-report-$(date +%Y%m%d_%H%M%S).txt"
    
    log "Generating infrastructure monitoring report..."
    
    {
        echo "Infrastructure Monitoring Report"
        echo "Generated: $(date)"
        echo "================================"
        echo ""
        echo "Kubernetes:"
        monitor_kubernetes >> "$report_file" 2>&1 || true
        echo ""
        echo "Cloud Provider ($CLOUD_PROVIDER):"
        case "$CLOUD_PROVIDER" in
            aws)
                monitor_aws >> "$report_file" 2>&1 || true
                ;;
            gcp)
                monitor_gcp >> "$report_file" 2>&1 || true
                ;;
            azure)
                monitor_azure >> "$report_file" 2>&1 || true
                ;;
        esac
    } > "$report_file"
    
    log "Report generated: $report_file"
    cat "$report_file"
}

# Main command handler
case "${1:-monitor}" in
    monitor)
        monitor_kubernetes
        case "$CLOUD_PROVIDER" in
            aws)
                monitor_aws
                ;;
            gcp)
                monitor_gcp
                ;;
            azure)
                monitor_azure
                ;;
        esac
        ;;
    report)
        generate_report
        ;;
    *)
        echo "Usage: $0 {monitor|report}"
        echo ""
        echo "Commands:"
        echo "  monitor - Monitor infrastructure health"
        echo "  report  - Generate monitoring report"
        exit 1
        ;;
esac


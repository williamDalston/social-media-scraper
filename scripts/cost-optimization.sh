#!/bin/bash

# Infrastructure Cost Optimization
# Analyzes and optimizes infrastructure costs

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
COST_DIR="${PROJECT_DIR}/reports/cost"

# Create directories
mkdir -p "$COST_DIR"

# Default values
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

# Function to analyze AWS costs
analyze_aws_costs() {
    log "Analyzing AWS costs..."
    
    if command -v aws &> /dev/null; then
        # Get cost data (requires Cost Explorer API)
        info "Cost analysis (requires AWS Cost Explorer API access)"
        
        # Resource recommendations
        log "Cost optimization recommendations:"
        log "  1. Use Reserved Instances for predictable workloads"
        log "  2. Enable auto-scaling to reduce idle resources"
        log "  3. Use Spot Instances for non-critical workloads"
        log "  4. Review and optimize S3 storage classes"
        log "  5. Enable CloudWatch cost anomaly detection"
    else
        warning "AWS CLI not found"
    fi
}

# Function to analyze GCP costs
analyze_gcp_costs() {
    log "Analyzing GCP costs..."
    
    if command -v gcloud &> /dev/null; then
        # Get billing data
        info "Cost analysis (requires GCP Billing API access)"
        
        # Resource recommendations
        log "Cost optimization recommendations:"
        log "  1. Use committed use discounts for predictable workloads"
        log "  2. Enable auto-scaling for Cloud Run/Cloud Functions"
        log "  3. Use preemptible VMs for non-critical workloads"
        log "  4. Review and optimize Cloud Storage classes"
        log "  5. Enable cost alerts and budgets"
    else
        warning "gcloud CLI not found"
    fi
}

# Function to analyze Azure costs
analyze_azure_costs() {
    log "Analyzing Azure costs..."
    
    if command -v az &> /dev/null; then
        # Get cost data
        info "Cost analysis (requires Azure Cost Management API access)"
        
        # Resource recommendations
        log "Cost optimization recommendations:"
        log "  1. Use Reserved Instances for predictable workloads"
        log "  2. Enable auto-scaling for container instances"
        log "  3. Use Spot VMs for non-critical workloads"
        log "  4. Review and optimize storage tiers"
        log "  5. Enable cost alerts and budgets"
    else
        warning "Azure CLI not found"
    fi
}

# Function to identify unused resources
identify_unused_resources() {
    log "Identifying unused resources..."
    
    case "$CLOUD_PROVIDER" in
        aws)
            # Check for stopped instances
            local stopped_instances=$(aws ec2 describe-instances --filters "Name=instance-state-name,Values=stopped" --query 'Reservations[*].Instances[*].InstanceId' --output text 2>/dev/null | wc -w || echo "0")
            if [ "$stopped_instances" -gt 0 ]; then
                warning "Found $stopped_instances stopped EC2 instances"
            fi
            ;;
        gcp)
            # Check for stopped instances
            local stopped_instances=$(gcloud compute instances list --filter="status:TERMINATED" --format="value(name)" 2>/dev/null | wc -l | tr -d ' ')
            if [ "$stopped_instances" -gt 0 ]; then
                warning "Found $stopped_instances terminated instances"
            fi
            ;;
        azure)
            # Check for deallocated VMs
            local deallocated_vms=$(az vm list --query "[?powerState!='VM running'].name" -o tsv 2>/dev/null | wc -l | tr -d ' ')
            if [ "$deallocated_vms" -gt 0 ]; then
                warning "Found $deallocated_vms deallocated VMs"
            fi
            ;;
    esac
}

# Function to generate cost report
generate_cost_report() {
    local report_file="${COST_DIR}/cost-report-$(date +%Y%m%d).txt"
    
    log "Generating cost optimization report..."
    
    {
        echo "Infrastructure Cost Optimization Report"
        echo "Generated: $(date)"
        echo "================================"
        echo ""
        echo "Cost Analysis:"
        case "$CLOUD_PROVIDER" in
            aws)
                analyze_aws_costs
                ;;
            gcp)
                analyze_gcp_costs
                ;;
            azure)
                analyze_azure_costs
                ;;
        esac
        echo ""
        echo "Unused Resources:"
        identify_unused_resources
        echo ""
        echo "Optimization Recommendations:"
        echo "  1. Review resource sizing"
        echo "  2. Enable auto-scaling"
        echo "  3. Use reserved/preemptible instances"
        echo "  4. Optimize storage classes"
        echo "  5. Set up cost alerts"
    } > "$report_file"
    
    log "Report generated: $report_file"
    cat "$report_file"
}

# Main command handler
case "${1:-analyze}" in
    analyze)
        case "$CLOUD_PROVIDER" in
            aws)
                analyze_aws_costs
                ;;
            gcp)
                analyze_gcp_costs
                ;;
            azure)
                analyze_azure_costs
                ;;
        esac
        identify_unused_resources
        ;;
    report)
        generate_cost_report
        ;;
    *)
        echo "Usage: $0 {analyze|report}"
        echo ""
        echo "Commands:"
        echo "  analyze - Analyze costs and identify optimizations"
        echo "  report  - Generate cost optimization report"
        exit 1
        ;;
esac


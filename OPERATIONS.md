# Operations & Maintenance Guide

This document provides comprehensive operational procedures for the Social Media Scraper in production.

## Table of Contents

- [Overview](#overview)
- [Operational Procedures](#operational-procedures)
- [Maintenance Windows](#maintenance-windows)
- [Capacity Planning](#capacity-planning)
- [Scaling Procedures](#scaling-procedures)
- [Operational Metrics](#operational-metrics)
- [Troubleshooting](#troubleshooting)
- [Runbooks](#runbooks)

---

## Overview

### Operational Objectives

- **Uptime**: 99.9%+ availability
- **Response Time**: < 2 seconds (p95)
- **Data Loss**: Zero data loss
- **Recovery**: Automated recovery from failures
- **Monitoring**: Complete monitoring coverage

---

## Operational Procedures

### Daily Operations

1. **Health Check**
   ```bash
   ./scripts/smoke-tests.sh all
   ```

2. **Monitor Logs**
   ```bash
   # Kubernetes
   kubectl logs -f deployment/social-media-scraper-app -n social-media-scraper
   
   # Docker Compose
   docker-compose logs -f app
   ```

3. **Check Metrics**
   - Review monitoring dashboards
   - Check error rates
   - Verify scraper success rates

### Weekly Operations

1. **Backup Verification**
   ```bash
   ./scripts/automated-backup.sh
   ```

2. **Capacity Review**
   - Review resource usage
   - Check scaling metrics
   - Plan capacity adjustments

3. **Security Review**
   - Review access logs
   - Check for anomalies
   - Update security patches

### Monthly Operations

1. **Disaster Recovery Test**
   ```bash
   ./scripts/disaster-recovery.sh test
   ```

2. **Performance Review**
   - Analyze performance metrics
   - Identify optimization opportunities
   - Update performance baselines

3. **Cost Review**
   - Review cloud costs
   - Optimize resource usage
   - Plan cost reductions

---

## Maintenance Windows

### Scheduled Maintenance

**Frequency**: Monthly (first Sunday, 2:00-4:00 AM UTC)

**Procedures**:

1. **Pre-Maintenance**
   ```bash
   # Notify users
   # Create maintenance ticket
   # Backup database
   ./scripts/backup_db.sh
   ```

2. **During Maintenance**
   ```bash
   # Apply updates
   ./scripts/deploy.sh
   
   # Run migrations
   ./scripts/migrate.sh upgrade
   
   # Verify deployment
   ./scripts/smoke-tests.sh all
   ```

3. **Post-Maintenance**
   ```bash
   # Verify all services
   # Monitor for issues
   # Close maintenance ticket
   ```

### Emergency Maintenance

**Procedures**:

1. Assess urgency
2. Notify stakeholders
3. Execute maintenance
4. Verify functionality
5. Document changes

### Maintenance Window Script

```bash
#!/bin/bash
# scripts/maintenance-window.sh

MAINTENANCE_START=$(date +%s)
MAINTENANCE_DURATION=7200  # 2 hours

# Pre-maintenance tasks
./scripts/backup_db.sh
./scripts/notify-users.sh "Maintenance starting"

# Maintenance tasks
./scripts/deploy.sh
./scripts/migrate.sh upgrade

# Post-maintenance tasks
./scripts/smoke-tests.sh all
./scripts/notify-users.sh "Maintenance complete"
```

---

## Capacity Planning

### Resource Monitoring

**Key Metrics**:
- CPU utilization
- Memory usage
- Database connections
- Network throughput
- Storage usage

### Capacity Planning Tools

**Script**: `scripts/capacity-planning.sh`

```bash
#!/bin/bash
# Capacity planning analysis

# Collect metrics
CPU_USAGE=$(kubectl top pods -n social-media-scraper | awk '{sum+=$2} END {print sum/NR}')
MEMORY_USAGE=$(kubectl top pods -n social-media-scraper | awk '{sum+=$3} END {print sum/NR}')

# Analyze trends
# Generate recommendations
```

### Scaling Triggers

**Horizontal Scaling**:
- CPU > 70% for 5 minutes
- Memory > 80% for 5 minutes
- Queue depth > 1000

**Vertical Scaling**:
- Consistent high resource usage
- Performance degradation
- Capacity planning recommendations

### Capacity Planning Procedures

1. **Monthly Review**
   - Analyze resource usage trends
   - Project future needs
   - Plan capacity adjustments

2. **Quarterly Planning**
   - Review growth projections
   - Plan infrastructure upgrades
   - Budget for capacity increases

---

## Scaling Procedures

### Automatic Scaling

**Kubernetes HPA**:
```yaml
# Already configured in k8s/hpa.yaml
# Automatically scales based on CPU/memory
```

**Manual Scaling**:
```bash
# Kubernetes
kubectl scale deployment social-media-scraper-app -n social-media-scraper --replicas=5

# Docker Compose
docker-compose up -d --scale app=5
```

### Scaling Script

**File**: `scripts/scale.sh`

```bash
#!/bin/bash
# Scaling automation script

TARGET_REPLICAS=$1
CURRENT_REPLICAS=$(kubectl get deployment social-media-scraper-app -n social-media-scraper -o jsonpath='{.spec.replicas}')

log "Scaling from $CURRENT_REPLICAS to $TARGET_REPLICAS replicas"

kubectl scale deployment social-media-scraper-app -n social-media-scraper --replicas=$TARGET_REPLICAS

# Wait for scaling
kubectl rollout status deployment/social-media-scraper-app -n social-media-scraper

log "Scaling completed"
```

### Scaling Procedures

1. **Scale Up**
   - Monitor resource usage
   - Identify scaling triggers
   - Execute scaling
   - Verify new instances

2. **Scale Down**
   - Verify low resource usage
   - Drain connections
   - Scale down gradually
   - Monitor for issues

---

## Operational Metrics

### Key Performance Indicators (KPIs)

**Availability**:
- Uptime percentage
- Downtime incidents
- Mean time to recovery (MTTR)

**Performance**:
- API response times (p50, p95, p99)
- Database query performance
- Cache hit rates

**Reliability**:
- Error rates
- Scraper success rates
- Job completion rates

### Metrics Dashboard

**Location**: Monitoring dashboards (Grafana, CloudWatch, etc.)

**Key Metrics**:
- Request rate
- Error rate
- Response time
- Resource utilization
- Queue depth
- Scraper success rate

### Operational Metrics Script

**File**: `scripts/operational-metrics.sh`

```bash
#!/bin/bash
# Collect and report operational metrics

METRICS_FILE="operational-metrics-$(date +%Y%m%d).json"

{
  echo "{"
  echo "  \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\","
  echo "  \"uptime\": $(get_uptime),"
  echo "  \"response_time_p95\": $(get_response_time_p95),"
  echo "  \"error_rate\": $(get_error_rate),"
  echo "  \"scraper_success_rate\": $(get_scraper_success_rate)"
  echo "}"
} > "$METRICS_FILE"
```

---

## Troubleshooting

### Common Issues

#### Issue: High Error Rate

**Symptoms**:
- Increased error logs
- Failed API requests
- User complaints

**Resolution**:
1. Check application logs
2. Review error patterns
3. Check database connectivity
4. Verify external service status
5. Scale resources if needed

#### Issue: Slow Response Times

**Symptoms**:
- API response times > 2s
- User complaints
- Timeout errors

**Resolution**:
1. Check database performance
2. Review cache hit rates
3. Check resource utilization
4. Optimize queries
5. Scale horizontally

#### Issue: Scraper Failures

**Symptoms**:
- Low scraper success rate
- Failed job logs
- Missing data

**Resolution**:
1. Check scraper logs
2. Verify API keys
3. Check rate limits
4. Review platform changes
5. Update scrapers if needed

---

## Runbooks

### Runbook: Application Deployment

**Trigger**: New version release

**Steps**:
1. Pre-deployment checks
2. Backup database
3. Deploy new version
4. Run migrations
5. Validate deployment
6. Monitor for issues

**Script**: `./scripts/automated-deploy.sh`

### Runbook: Database Migration

**Trigger**: Schema changes

**Steps**:
1. Backup database
2. Review migration
3. Run migration in staging
4. Run migration in production
5. Verify data integrity

**Script**: `./scripts/migrate.sh upgrade`

### Runbook: Scaling Event

**Trigger**: High resource usage

**Steps**:
1. Monitor resource usage
2. Identify scaling need
3. Execute scaling
4. Verify new instances
5. Monitor performance

**Script**: `./scripts/scale.sh <replicas>`

### Runbook: Incident Response

**Trigger**: Production incident

**Steps**:
1. Assess severity
2. Notify team
3. Investigate root cause
4. Execute remediation
5. Verify resolution
6. Post-mortem

---

## Operational Checklists

### Daily Checklist

- [ ] Health checks pass
- [ ] No critical errors
- [ ] Resource usage normal
- [ ] Scraper success rate > 95%
- [ ] Backups completed

### Weekly Checklist

- [ ] Backup verification
- [ ] Security review
- [ ] Performance review
- [ ] Capacity planning
- [ ] Documentation updates

### Monthly Checklist

- [ ] Disaster recovery test
- [ ] Performance optimization
- [ ] Cost review
- [ ] Security audit
- [ ] Capacity planning review

---

**Last Updated**: 2024-01-01


# Disaster Recovery Runbooks

Comprehensive runbooks for disaster recovery scenarios.

## Table of Contents

- [Overview](#overview)
- [Recovery Time Objectives (RTO)](#recovery-time-objectives-rto)
- [Recovery Procedures](#recovery-procedures)
- [Runbooks](#runbooks)
- [Testing Procedures](#testing-procedures)

---

## Overview

### RTO Targets by Severity

| Severity | RTO Target | RTO Maximum | Procedure |
|----------|------------|-------------|-----------|
| Critical | 15 minutes | 30 minutes | Automated failover |
| High | 1 hour | 2 hours | Manual failover |
| Medium | 4 hours | 8 hours | Restore from backup |
| Low | 24 hours | 48 hours | Rebuild infrastructure |

---

## Recovery Time Objectives (RTO)

### Implementation

**File**: `scripts/rto-monitor.sh`

```bash
#!/bin/bash
# RTO Monitoring and Enforcement

RTO_TARGET=900  # 15 minutes in seconds
RTO_START_TIME=$(date +%s)

# Monitor recovery progress
while true; do
    ELAPSED=$(($(date +%s) - RTO_START_TIME))
    
    if [ $ELAPSED -gt $RTO_TARGET ]; then
        error "RTO target exceeded!"
        escalate_incident
    fi
    
    sleep 60
done
```

### RTO Tracking

- **Start Time**: Incident detection time
- **Target Time**: RTO target (e.g., 15 minutes)
- **Current Time**: Elapsed time since incident
- **Status**: On track / At risk / Exceeded

---

## Recovery Procedures

### Procedure 1: Database Corruption

**RTO**: 1-2 hours  
**RPO**: Up to 24 hours

**Steps**:

1. **Assess Damage**
   ```bash
   ./scripts/disaster-recovery.sh assess
   ```

2. **Select Backup**
   ```bash
   ls -lh backups/
   ```

3. **Restore Database**
   ```bash
   ./scripts/disaster-recovery.sh restore backups/db_backup_YYYYMMDD_HHMMSS.db
   ```

4. **Verify Data**
   ```bash
   ./scripts/smoke-tests.sh database
   ```

5. **Restart Services**
   ```bash
   ./scripts/start.sh restart
   ```

### Procedure 2: Complete Site Failure

**RTO**: 15-30 minutes  
**RPO**: Near-zero (with replication)

**Steps**:

1. **Verify Secondary Site**
   ```bash
   curl https://secondary.example.com/health
   ```

2. **Failover**
   ```bash
   ./scripts/disaster-recovery.sh failover
   ```

3. **Update DNS**
   - Change A record to secondary IP
   - Wait for propagation

4. **Verify Failover**
   ```bash
   ./scripts/smoke-tests.sh all
   ```

### Procedure 3: Data Loss

**RTO**: 2-4 hours  
**RPO**: Up to 24 hours

**Steps**:

1. **Identify Data Loss**
   - Review logs
   - Check database
   - Identify affected data

2. **Select Recovery Point**
   - Choose backup before data loss
   - Verify backup integrity

3. **Restore**
   ```bash
   ./scripts/disaster-recovery.sh restore <backup_file>
   ```

4. **Verify Recovery**
   - Check data integrity
   - Verify application functionality

---

## Runbooks

### Runbook: Database Recovery

**Scenario**: Database corruption or data loss

**Prerequisites**:
- Backup available
- Database credentials
- Access to restore script

**Steps**:

1. Stop application services
2. Backup current database (if accessible)
3. Restore from selected backup
4. Run database migrations (if needed)
5. Verify data integrity
6. Restart services
7. Run smoke tests
8. Monitor for issues

**Commands**:
```bash
./scripts/start.sh stop
./scripts/restore_db.sh backups/db_backup_YYYYMMDD_HHMMSS.db
./scripts/migrate.sh upgrade
./scripts/start.sh start
./scripts/smoke-tests.sh all
```

### Runbook: Application Recovery

**Scenario**: Application failure or corruption

**Prerequisites**:
- Deployment scripts
- Previous version available
- Health check endpoints

**Steps**:

1. Identify failure point
2. Rollback to previous version
3. Verify deployment
4. Run smoke tests
5. Monitor for issues

**Commands**:
```bash
./scripts/rollback-procedures.sh execute previous
./scripts/smoke-tests.sh all
./scripts/auto-rollback.sh monitor
```

### Runbook: Infrastructure Recovery

**Scenario**: Complete infrastructure failure

**Prerequisites**:
- Infrastructure as Code
- Terraform state
- Cloud provider access

**Steps**:

1. Assess infrastructure state
2. Restore from Terraform
3. Restore database
4. Deploy application
5. Verify functionality

**Commands**:
```bash
cd terraform/aws  # or gcp, azure
terraform init
terraform plan
terraform apply
./scripts/init_db.sh
./scripts/deploy.sh
```

---

## Testing Procedures

### Monthly DR Test

**Schedule**: First Sunday of each month, 2:00 AM UTC

**Procedure**:

1. **Pre-Test**
   - Notify team
   - Create test environment
   - Document baseline state

2. **Test Execution**
   ```bash
   ./scripts/disaster-recovery.sh test
   ```

3. **Post-Test**
   - Document results
   - Review procedures
   - Update runbooks
   - Restore test environment

### Quarterly Full DR Drill

**Schedule**: Quarterly

**Procedure**:

1. Simulate complete failure
2. Execute full recovery
3. Measure RTO/RPO
4. Document lessons learned
5. Update procedures

---

## RTO Implementation

### RTO Monitoring Script

**File**: `scripts/rto-tracker.sh`

```bash
#!/bin/bash
# RTO Tracking and Alerting

INCIDENT_START_TIME=$(date +%s)
RTO_TARGET=900  # 15 minutes

while true; do
    ELAPSED=$(($(date +%s) - INCIDENT_START_TIME))
    REMAINING=$((RTO_TARGET - ELAPSED))
    
    if [ $REMAINING -lt 0 ]; then
        error "RTO EXCEEDED!"
        escalate
    elif [ $REMAINING -lt 300 ]; then
        warning "RTO at risk: $REMAINING seconds remaining"
    fi
    
    sleep 60
done
```

### RTO Dashboard

**Metrics to Track**:
- Incident start time
- Current elapsed time
- RTO target
- Recovery progress
- Estimated completion time

---

**Last Updated**: 2024-01-01


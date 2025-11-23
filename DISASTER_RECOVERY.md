# Disaster Recovery Procedures

This document outlines disaster recovery procedures for the Social Media Scraper application.

## Table of Contents

- [Overview](#overview)
- [Recovery Objectives](#recovery-objectives)
- [Backup Strategy](#backup-strategy)
- [Recovery Procedures](#recovery-procedures)
- [Failover Procedures](#failover-procedures)
- [Testing](#testing)
- [Contact Information](#contact-information)

---

## Overview

### Recovery Time Objective (RTO)
- **Target**: 1-4 hours
- **Maximum Acceptable**: 8 hours

### Recovery Point Objective (RPO)
- **Target**: 1 hour
- **Maximum Acceptable**: 4 hours

### Critical Systems

1. **Database**: PostgreSQL (primary data store)
2. **Application**: Flask application servers
3. **Cache/Queue**: Redis (Celery broker)
4. **Storage**: Persistent volumes

---

## Recovery Objectives

### RTO and RPO by Severity

| Severity | RTO | RPO | Impact |
|----------|-----|-----|--------|
| Critical | 1 hour | 15 minutes | Complete outage |
| High | 2 hours | 1 hour | Major functionality loss |
| Medium | 4 hours | 4 hours | Partial functionality loss |
| Low | 8 hours | 24 hours | Minor impact |

---

## Backup Strategy

### Automated Backups

- **Frequency**: Daily at 2:00 AM UTC
- **Retention**: 30 days
- **Verification**: Automated verification after each backup
- **Location**: Local backups + cloud storage (S3, GCS, Azure Blob)

### Backup Types

1. **Full Database Backup**
   - Complete database dump
   - Compressed and encrypted
   - Stored with timestamp

2. **Incremental Backups** (if supported)
   - Changes since last full backup
   - Faster restore for recent changes

3. **Point-in-Time Recovery**
   - Transaction logs (WAL files)
   - Enable recovery to specific point in time

### Backup Verification

- **Immediate**: File integrity check
- **Daily**: Restore test to staging environment
- **Weekly**: Full recovery test

---

## Recovery Procedures

### Step 1: Assess Situation

```bash
./scripts/disaster-recovery.sh assess
```

**Check:**
- Database accessibility
- Application responsiveness
- Backup availability
- Network connectivity
- Resource availability

### Step 2: Select Recovery Method

**Option A: Restore from Backup**
- Use if: Data corruption, accidental deletion
- RTO: 1-2 hours
- RPO: Up to 24 hours (last backup)

**Option B: Failover to Secondary Site**
- Use if: Primary site failure
- RTO: 15-30 minutes
- RPO: Near-zero (with replication)

**Option C: Rebuild Infrastructure**
- Use if: Complete infrastructure loss
- RTO: 2-4 hours
- RPO: Up to 24 hours

### Step 3: Execute Recovery

#### Restore from Backup

```bash
# List available backups
ls -lh backups/

# Restore from backup
./scripts/disaster-recovery.sh restore backups/db_backup_20240101_020000.db
```

**Procedure:**
1. Stop application services
2. Backup current database (if accessible)
3. Restore from selected backup
4. Verify data integrity
5. Run database migrations (if needed)
6. Restart services
7. Run smoke tests

#### Failover to Secondary Site

```bash
./scripts/disaster-recovery.sh failover
```

**Procedure:**
1. Verify secondary site is ready
2. Update DNS/routing configuration
3. Verify application is responding
4. Monitor for issues
5. Document failover

### Step 4: Validate Recovery

```bash
# Run smoke tests
./scripts/smoke-tests.sh all

# Check application health
curl http://localhost:5000/health

# Verify data integrity
# (Run data validation queries)
```

### Step 5: Post-Recovery

1. **Document Incident**
   - What happened
   - Recovery steps taken
   - Time to recovery
   - Lessons learned

2. **Monitor**
   - Watch for issues
   - Monitor performance
   - Check error rates

3. **Review**
   - Post-mortem meeting
   - Update procedures
   - Improve backup strategy

---

## Failover Procedures

### Primary to Secondary Site

**Prerequisites:**
- Secondary site configured and tested
- Database replication enabled
- DNS/routing configured for failover

**Procedure:**

1. **Verify Secondary Site**
   ```bash
   # Check secondary site health
   curl https://secondary.example.com/health
   ```

2. **Update DNS**
   - Change A record to secondary site IP
   - TTL should be low (300 seconds) for quick failover

3. **Verify Failover**
   ```bash
   # Wait for DNS propagation
   sleep 60
   
   # Test application
   curl https://api.example.com/health
   ```

4. **Monitor**
   - Check application logs
   - Monitor error rates
   - Verify functionality

### Failback to Primary Site

**Procedure:**

1. **Verify Primary Site**
   - Check all systems operational
   - Verify database synchronization
   - Run health checks

2. **Update DNS**
   - Change A record back to primary site IP

3. **Monitor**
   - Watch for issues
   - Verify data consistency

---

## Testing

### Backup Testing

**Daily:**
- Verify backup completion
- Check backup file integrity
- Verify backup size

**Weekly:**
- Restore backup to test environment
- Verify data integrity
- Test application with restored data

### Recovery Testing

**Monthly:**
- Full disaster recovery drill
- Test restore procedures
- Test failover procedures
- Document results

**Quarterly:**
- Complete infrastructure rebuild test
- Test all recovery procedures
- Update documentation

### Test Checklist

- [ ] Backup restoration works
- [ ] Application starts after restore
- [ ] Data integrity verified
- [ ] All services operational
- [ ] Smoke tests pass
- [ ] Performance acceptable
- [ ] Documentation updated

---

## Backup Retention Policy

### Retention Schedule

| Age | Action |
|-----|--------|
| 0-7 days | Keep all backups |
| 8-30 days | Keep daily backups |
| 31-90 days | Keep weekly backups |
| 91-365 days | Keep monthly backups |
| 366+ days | Archive to long-term storage |

### Cleanup Script

```bash
# Automated cleanup (runs daily)
./scripts/automated-backup.sh
```

---

## Point-in-Time Recovery

### PostgreSQL

**Prerequisites:**
- WAL archiving enabled
- Continuous archiving configured

**Procedure:**

1. **Identify Recovery Point**
   ```sql
   -- Find transaction log sequence
   SELECT pg_current_wal_lsn();
   ```

2. **Restore Base Backup**
   ```bash
   # Restore most recent full backup
   pg_restore -d social_media backup.sql
   ```

3. **Recover to Point in Time**
   ```bash
   # Configure recovery target
   echo "recovery_target_time = '2024-01-01 12:00:00'" >> postgresql.conf
   
   # Start recovery
   pg_ctl start
   ```

### SQLite

SQLite doesn't support point-in-time recovery. Use:
- Frequent backups (hourly for critical data)
- Transaction logs (if using WAL mode)

---

## Contact Information

### On-Call Rotation

- **Primary**: [Contact Info]
- **Secondary**: [Contact Info]
- **Escalation**: [Contact Info]

### Escalation Path

1. **Level 1**: On-call engineer
2. **Level 2**: DevOps team lead
3. **Level 3**: Engineering manager
4. **Level 4**: CTO/VP Engineering

### Communication Channels

- **Slack**: #incidents
- **PagerDuty**: [Service]
- **Email**: incidents@example.com

---

## Recovery Scenarios

### Scenario 1: Database Corruption

**Symptoms:**
- Database errors
- Application crashes
- Data inconsistencies

**Recovery:**
1. Stop application
2. Assess corruption extent
3. Restore from most recent backup
4. Verify data integrity
5. Restart application

**RTO**: 1-2 hours
**RPO**: Up to 24 hours

### Scenario 2: Complete Site Failure

**Symptoms:**
- Site unreachable
- All services down
- Infrastructure unavailable

**Recovery:**
1. Failover to secondary site
2. Verify all services
3. Monitor for issues
4. Plan primary site recovery

**RTO**: 15-30 minutes
**RPO**: Near-zero (with replication)

### Scenario 3: Data Loss

**Symptoms:**
- Missing data
- Incorrect data
- Accidental deletion

**Recovery:**
1. Identify data loss extent
2. Select appropriate backup
3. Restore from backup
4. Verify data recovery
5. Investigate cause

**RTO**: 2-4 hours
**RPO**: Up to 24 hours

---

## Prevention

### Best Practices

1. **Regular Backups**
   - Automated daily backups
   - Verify backup integrity
   - Test restore procedures

2. **Monitoring**
   - Health checks
   - Alerting on failures
   - Proactive monitoring

3. **Redundancy**
   - Multiple replicas
   - Multi-AZ deployment
   - Secondary site

4. **Documentation**
   - Keep procedures updated
   - Document all changes
   - Regular reviews

---

**Last Updated**: 2024-01-01
**Next Review**: 2024-04-01


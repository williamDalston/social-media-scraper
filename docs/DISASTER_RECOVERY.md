# Disaster Recovery Plan

## Overview

This document outlines the disaster recovery procedures for the HHS Social Media Scraper system.

## Recovery Objectives

- **RTO (Recovery Time Objective)**: < 4 hours
- **RPO (Recovery Point Objective)**: < 24 hours (daily backups)

## Backup Strategy

### Automated Backups

- **Frequency**: Daily at 2:00 AM UTC
- **Retention**: 30 days
- **Location**: `./backups/` directory
- **Format**: SQLite database files with timestamp

### Manual Backups

Run backup script:
```bash
./scripts/backup_db.sh
```

### Backup Verification

Backups are verified for:
- File integrity
- Database schema consistency
- Data completeness

## Recovery Procedures

### Database Restoration

1. **Identify the backup to restore**
   ```bash
   ls -lh backups/
   ```

2. **Run disaster recovery script**
   ```bash
   ./scripts/disaster_recovery.sh latest
   # Or specify a backup file:
   ./scripts/disaster_recovery.sh 20240115_020000.db
   ```

3. **Verify restoration**
   - Check database integrity
   - Verify data completeness
   - Test application functionality

### Full System Recovery

1. **Infrastructure Recovery**
   - Restore from infrastructure as code (Terraform/CloudFormation)
   - Provision new servers if needed
   - Configure networking and security

2. **Application Recovery**
   - Deploy application from version control
   - Restore environment variables
   - Restore database from backup

3. **Service Recovery**
   - Start application services
   - Start background workers (Celery)
   - Verify all services are running

4. **Data Recovery**
   - Restore database
   - Verify data integrity
   - Resume data collection

### Partial Recovery Scenarios

#### Database Corruption
1. Stop application
2. Restore from latest backup
3. Verify integrity
4. Restart application

#### Data Loss
1. Identify time of data loss
2. Restore from backup before loss
3. Re-run scrapers for missing period
4. Verify data completeness

#### Service Failure
1. Check service logs
2. Restart failed services
3. Verify service health
4. Monitor for recurrence

## Testing

### Recovery Testing Schedule

- **Monthly**: Test database restoration
- **Quarterly**: Full disaster recovery drill
- **Annually**: Complete system recovery test

### Test Procedures

1. Create test environment
2. Simulate disaster scenario
3. Execute recovery procedures
4. Verify system functionality
5. Document results and improvements

## Monitoring

### Backup Monitoring

- Monitor backup job success/failure
- Alert on backup failures
- Track backup sizes and trends
- Verify backup accessibility

### Recovery Readiness

- Regular backup verification
- Test restoration procedures
- Document recovery times
- Update procedures based on lessons learned

## Contact Information

### On-Call Engineer
- Primary: [Contact Info]
- Secondary: [Contact Info]

### Escalation
- Manager: [Contact Info]
- Director: [Contact Info]

## Post-Recovery

After recovery:

1. **Document incident**
   - What happened
   - Recovery steps taken
   - Time to recovery
   - Data loss (if any)

2. **Post-mortem**
   - Root cause analysis
   - Prevention measures
   - Process improvements

3. **Update procedures**
   - Incorporate lessons learned
   - Update documentation
   - Train team on improvements


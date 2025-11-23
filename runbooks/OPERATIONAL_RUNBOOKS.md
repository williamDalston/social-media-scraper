# Operational Runbooks

This document contains operational runbooks for common scenarios and incidents.

## Table of Contents
1. [System Startup](#system-startup)
2. [Database Issues](#database-issues)
3. [Scraper Failures](#scraper-failures)
4. [High Error Rates](#high-error-rates)
5. [Performance Degradation](#performance-degradation)
6. [Memory Issues](#memory-issues)
7. [Disk Space Issues](#disk-space-issues)
8. [Redis/Cache Issues](#rediscache-issues)
9. [Celery Worker Issues](#celery-worker-issues)
10. [SLO Violations](#slo-violations)

---

## System Startup

### Checklist
- [ ] Verify database is accessible
- [ ] Check Redis connectivity
- [ ] Verify Celery workers are running
- [ ] Check health endpoints
- [ ] Verify logging is working
- [ ] Check disk space
- [ ] Verify environment variables are set

### Commands
```bash
# Check health
curl http://localhost:5000/health

# Check Celery workers
celery -A celery_app inspect active

# Check logs
tail -f logs/app.log
```

---

## Database Issues

### Symptoms
- Database connection errors
- Slow queries
- High query times
- Connection pool exhaustion

### Diagnosis
1. Check database health: `GET /health`
2. Review slow query logs
3. Check database connection pool
4. Review database metrics

### Resolution Steps
1. **Connection Issues**
   - Verify database is running
   - Check connection string
   - Verify network connectivity
   - Check firewall rules

2. **Slow Queries**
   - Review slow query log
   - Add indexes if needed
   - Optimize query patterns
   - Consider query caching

3. **Connection Pool**
   - Increase pool size if needed
   - Check for connection leaks
   - Restart application if necessary

### Escalation
- If database is down: Critical - Contact DBA immediately
- If queries are slow: High - Review and optimize
- If pool exhausted: High - Increase pool size

---

## Scraper Failures

### Symptoms
- Low scraper success rate
- Scraper errors in logs
- No recent data collected
- Platform-specific failures

### Diagnosis
1. Check scraper metrics: `GET /api/admin/status`
2. Review scraper logs
3. Check platform-specific errors
4. Review rate limiting status

### Resolution Steps
1. **General Failures**
   - Check scraper logs for errors
   - Verify network connectivity
   - Check API keys (if using APIs)
   - Review rate limiting

2. **Platform-Specific Failures**
   - Check platform status (maintenance, changes)
   - Review platform-specific error messages
   - Check for authentication issues
   - Verify scraper configuration

3. **Rate Limiting**
   - Reduce scraping frequency
   - Implement backoff strategies
   - Use multiple API keys if available
   - Consider proxy rotation

### Escalation
- Success rate < 80%: High - Investigate immediately
- Success rate < 50%: Critical - Emergency response
- Platform down: Medium - Monitor and wait

---

## High Error Rates

### Symptoms
- Error rate > 10%
- Many 5xx errors
- API failures
- User complaints

### Diagnosis
1. Check error metrics: `GET /metrics`
2. Review error logs
3. Check Sentry for errors
4. Review recent deployments

### Resolution Steps
1. **Immediate Actions**
   - Check system health
   - Review recent changes
   - Check error logs
   - Verify dependencies

2. **Error Analysis**
   - Identify error patterns
   - Check for common causes
   - Review stack traces
   - Check external dependencies

3. **Mitigation**
   - Rollback recent changes if needed
   - Enable circuit breakers
   - Add retry logic
   - Scale resources if needed

### Escalation
- Error rate > 20%: Critical - Immediate response
- Error rate > 10%: High - Investigate within 1 hour
- Error rate > 5%: Medium - Monitor and investigate

---

## Performance Degradation

### Symptoms
- Slow API response times
- High latency
- Timeout errors
- User complaints about slowness

### Diagnosis
1. Check performance metrics
2. Review slow queries
3. Check resource usage
4. Review recent changes

### Resolution Steps
1. **API Performance**
   - Check response time metrics
   - Identify slow endpoints
   - Review query performance
   - Check cache hit rates

2. **Database Performance**
   - Review slow queries
   - Add indexes if needed
   - Optimize queries
   - Check connection pool

3. **Resource Constraints**
   - Check CPU usage
   - Check memory usage
   - Check disk I/O
   - Scale resources if needed

### Escalation
- P95 > 5s: Critical - Immediate investigation
- P95 > 2s: High - Investigate within 2 hours
- P95 > 1s: Medium - Monitor and optimize

---

## Memory Issues

### Symptoms
- High memory usage
- Memory leaks
- Out of memory errors
- System slowdowns

### Diagnosis
1. Check memory metrics: `GET /api/admin/status`
2. Review memory leak detection
3. Check process memory usage
4. Review recent changes

### Resolution Steps
1. **High Memory Usage**
   - Check memory metrics
   - Identify memory-intensive operations
   - Review caching strategies
   - Check for memory leaks

2. **Memory Leaks**
   - Enable memory tracking
   - Review memory snapshots
   - Identify leak sources
   - Fix memory leaks

3. **Immediate Actions**
   - Restart application if needed
   - Increase memory limits
   - Scale horizontally
   - Optimize memory usage

### Escalation
- Memory > 90%: High - Investigate immediately
- Memory leak detected: High - Fix within 24 hours
- OOM errors: Critical - Immediate response

---

## Disk Space Issues

### Symptoms
- Disk usage > 90%
- Write failures
- Log rotation failures
- System warnings

### Diagnosis
1. Check disk usage: `GET /health`
2. Review log file sizes
3. Check database size
4. Review retention policies

### Resolution Steps
1. **Immediate Actions**
   - Clean up old log files
   - Archive old data
   - Remove temporary files
   - Increase disk space if needed

2. **Log Management**
   - Review log retention policies
   - Clean up old logs
   - Optimize log rotation
   - Consider log aggregation

3. **Data Management**
   - Archive old snapshots
   - Review data retention
   - Optimize database
   - Consider data partitioning

### Escalation
- Disk > 95%: Critical - Immediate cleanup
- Disk > 90%: High - Cleanup within 2 hours
- Disk > 80%: Medium - Plan cleanup

---

## Redis/Cache Issues

### Symptoms
- Cache misses
- Redis connection errors
- Slow cache operations
- Cache not working

### Diagnosis
1. Check Redis health: `GET /health`
2. Review cache metrics
3. Check Redis logs
4. Verify Redis connectivity

### Resolution Steps
1. **Connection Issues**
   - Verify Redis is running
   - Check connection string
   - Verify network connectivity
   - Restart Redis if needed

2. **Performance Issues**
   - Check Redis memory usage
   - Review cache hit rates
   - Optimize cache keys
   - Consider cache warming

3. **Fallback**
   - System should fallback to simple cache
   - Verify fallback is working
   - Monitor cache performance

### Escalation
- Redis down: Medium - System should continue with fallback
- Cache misses > 50%: High - Investigate
- Slow cache: Medium - Optimize

---

## Celery Worker Issues

### Symptoms
- Jobs not processing
- Workers not responding
- Job queue backing up
- Worker errors

### Diagnosis
1. Check Celery status: `GET /health`
2. Review worker logs
3. Check job queue depth
4. Review worker metrics

### Resolution Steps
1. **Worker Not Running**
   - Start Celery workers
   - Check worker logs
   - Verify Redis connectivity
   - Check worker configuration

2. **Job Queue Backup**
   - Scale workers if needed
   - Review job processing time
   - Optimize slow jobs
   - Check for stuck jobs

3. **Worker Errors**
   - Review worker logs
   - Check for resource issues
   - Restart workers if needed
   - Fix job errors

### Escalation
- No workers running: High - Start workers immediately
- Queue depth > 1000: High - Scale workers
- Worker errors: Medium - Investigate and fix

---

## SLO Violations

### Symptoms
- SLO status not "met"
- Service degradation
- User impact
- Alert notifications

### Diagnosis
1. Check SLO status: `GET /api/admin/slo`
2. Review SLO metrics
3. Identify root cause
4. Check related systems

### Resolution Steps
1. **Identify Violation**
   - Check which SLO is violated
   - Review SLO metrics
   - Identify root cause
   - Check related alerts

2. **Immediate Actions**
   - Address root cause
   - Implement fixes
   - Monitor recovery
   - Verify SLO compliance

3. **Prevention**
   - Review SLO targets
   - Optimize systems
   - Add monitoring
   - Improve resilience

### Escalation
- Critical SLO violation: Critical - Immediate response
- High SLO violation: High - Fix within SLA window
- Medium SLO violation: Medium - Investigate and fix

---

## Emergency Contacts

- **On-Call Engineer**: Check `/api/admin/oncall`
- **Database Team**: [Contact Info]
- **Infrastructure Team**: [Contact Info]
- **Security Team**: [Contact Info]

---

## Post-Incident Checklist

After resolving an incident:
- [ ] Document incident in incident management system
- [ ] Update runbooks if needed
- [ ] Schedule post-incident review
- [ ] Create action items
- [ ] Update monitoring/alerting
- [ ] Communicate resolution to stakeholders


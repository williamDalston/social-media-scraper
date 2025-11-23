# Troubleshooting Guide

## Common Issues and Solutions

### Authentication Issues

#### Problem: "Invalid username or password"
**Solution:**
- Verify username/email is correct
- Check if account is locked (too many failed attempts)
- Reset password if needed: `POST /api/auth/password-reset/request`

#### Problem: "Token expired"
**Solution:**
- Use refresh token to get new access token: `POST /api/auth/refresh`
- Re-login if refresh token expired

#### Problem: "MFA verification required"
**Solution:**
- Complete MFA setup: `POST /api/auth/mfa/setup`
- Use authenticator app to get TOTP code
- Verify: `POST /api/auth/mfa/verify`

### API Issues

#### Problem: "Rate limit exceeded"
**Solution:**
- Wait for rate limit window to reset
- Check `X-RateLimit-Reset` header for reset time
- Implement exponential backoff in your client
- Request higher rate limits if needed (contact admin)

#### Problem: "404 Not Found" on endpoints
**Solution:**
- Verify endpoint URL is correct
- Check API version (v1, v2, etc.)
- Ensure authentication token is valid
- Check Swagger docs: `/api/docs`

#### Problem: "500 Internal Server Error"
**Solution:**
- Check application logs
- Verify database connectivity
- Check Redis connection (if using caching)
- Review error details in response

### Database Issues

#### Problem: "Database locked"
**Solution:**
- Close other database connections
- Check for long-running queries
- Restart application if needed
- For SQLite: ensure single writer

#### Problem: "Migration errors"
**Solution:**
- Check Alembic version: `alembic current`
- Review migration files
- Run migrations: `alembic upgrade head`
- Backup database before migrations

### Scraper Issues

#### Problem: "Scraper returns no data"
**Solution:**
- Check platform API keys are set
- Verify account URLs are correct
- Check scraper logs for errors
- Test with simulated mode first
- Verify network connectivity

#### Problem: "Rate limited by platform"
**Solution:**
- Reduce scraping frequency
- Use platform APIs instead of scraping
- Implement longer delays between requests
- Check platform-specific rate limits

#### Problem: "Data quality issues"
**Solution:**
- Review data validation errors
- Check scraper result validation
- Verify platform structure hasn't changed
- Update scraper if platform changed

### Performance Issues

#### Problem: "Slow API responses"
**Solution:**
- Check cache hit rates
- Review database query performance
- Verify indexes are created
- Check for N+1 query problems
- Monitor database connection pool

#### Problem: "High memory usage"
**Solution:**
- Review query result sizes
- Implement pagination
- Check for memory leaks
- Monitor cache sizes
- Review worker memory limits

#### Problem: "Cache not working"
**Solution:**
- Verify Redis is running
- Check Redis connection string
- Review cache configuration
- Check cache TTL settings
- Monitor cache hit/miss rates

### Deployment Issues

#### Problem: "Docker build fails"
**Solution:**
- Check Dockerfile syntax
- Verify base image exists
- Review dependency installation
- Check for platform-specific issues
- Clear Docker cache: `docker builder prune`

#### Problem: "Kubernetes deployment fails"
**Solution:**
- Check pod logs: `kubectl logs <pod-name>`
- Verify image exists in registry
- Check resource limits
- Review health check configuration
- Verify secrets/configmaps exist

#### Problem: "Zero-downtime deployment fails"
**Solution:**
- Verify health checks are working
- Check readiness probes
- Review deployment strategy
- Ensure sufficient replicas
- Check resource availability

### Monitoring Issues

#### Problem: "Metrics not appearing"
**Solution:**
- Verify Prometheus is scraping
- Check metrics endpoint: `/metrics`
- Review metric configuration
- Check network connectivity
- Verify service discovery

#### Problem: "Alerts not firing"
**Solution:**
- Check alerting rules
- Verify alert manager configuration
- Review notification channels
- Check alert thresholds
- Test alert manually

### Security Issues

#### Problem: "CSRF token errors"
**Solution:**
- Include CSRF token in requests
- Verify CSRF protection is configured
- Check token expiration
- Review CORS settings

#### Problem: "OAuth login fails"
**Solution:**
- Verify OAuth credentials
- Check redirect URIs match
- Review OAuth provider settings
- Check callback URL configuration

## Diagnostic Commands

### Check System Health

```bash
# Health check
curl http://localhost:5000/health

# Detailed health
curl http://localhost:5000/health/ready
```

### Check Database

```bash
# SQLite
sqlite3 social_media.db ".tables"
sqlite3 social_media.db "SELECT COUNT(*) FROM dim_account;"

# PostgreSQL
psql -d social_media -c "\dt"
```

### Check Redis

```bash
redis-cli ping
redis-cli info stats
```

### Check Logs

```bash
# Application logs
tail -f logs/app.log

# Docker logs
docker-compose logs -f app

# Kubernetes logs
kubectl logs -f deployment/social-media-scraper-app
```

### Check Performance

```bash
# Query stats
curl http://localhost:5000/api/production/query-stats

# Cache stats
curl http://localhost:5000/api/production/cache-stats

# SLO status
curl http://localhost:5000/api/production/slo
```

## Getting Help

1. **Check Documentation**
   - [README.md](../README.md)
   - [API Documentation](./API_USAGE.md)
   - [Deployment Guide](../DEPLOYMENT.md)

2. **Review Logs**
   - Application logs
   - Error tracking (Sentry)
   - System logs

3. **Contact Support**
   - Create an issue on GitHub
   - Check existing issues
   - Review troubleshooting docs

4. **Debug Mode**
   - Enable debug logging: `LOG_LEVEL=DEBUG`
   - Enable Flask debug mode (development only)
   - Use debugger for breakpoints

## Prevention

### Best Practices

1. **Monitor Regularly**
   - Set up alerts
   - Review metrics daily
   - Check logs weekly

2. **Test Before Deploy**
   - Run tests locally
   - Test in staging
   - Verify health checks

3. **Backup Regularly**
   - Automated daily backups
   - Test restore procedures
   - Keep multiple backups

4. **Document Changes**
   - Document configuration changes
   - Track deployment history
   - Maintain runbooks

5. **Stay Updated**
   - Update dependencies
   - Apply security patches
   - Review best practices


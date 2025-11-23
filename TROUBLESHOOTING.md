# Troubleshooting Guide

Common issues and solutions for the HHS Social Media Scraper.

---

## 📋 Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Installation Issues](#installation-issues)
- [Service Startup Issues](#service-startup-issues)
- [Database Issues](#database-issues)
- [Redis Issues](#redis-issues)
- [Scraper Issues](#scraper-issues)
- [API Issues](#api-issues)
- [Authentication Issues](#authentication-issues)
- [Performance Issues](#performance-issues)
- [Deployment Issues](#deployment-issues)

---

## 🔍 Quick Diagnostics

### Health Check

```bash
# Check application health
curl http://localhost:5000/health

# Check service status
docker-compose ps
# or
make status

# Check logs
make logs
# or
docker-compose logs -f app
```

### Common Diagnostic Commands

```bash
# View all logs
make logs

# Check configuration
make config

# Test database connection
docker-compose exec app python -c "from scraper.schema import init_db; engine = init_db('social_media.db'); print('Database OK')"

# Test Redis connection
docker-compose exec app python -c "import redis; r = redis.from_url('redis://localhost:6379/0'); r.ping(); print('Redis OK')"

# Check API documentation
curl http://localhost:5000/api/docs
```

---

## 🚀 Installation Issues

### Issue: Docker not found

**Symptoms:**
```bash
docker: command not found
```

**Solution:**
- Install Docker Desktop or Docker Engine
- Verify installation: `docker --version`
- Ensure Docker daemon is running

### Issue: Docker Compose not found

**Symptoms:**
```bash
docker-compose: command not found
```

**Solution:**
- Docker Compose v2 is included with Docker Desktop
- Use `docker compose` (no hyphen) instead of `docker-compose`
- Or install Docker Compose separately

### Issue: Port already in use

**Symptoms:**
```
Error: bind: address already in use
```

**Solution:**
```bash
# Option 1: Change port in .env
APP_PORT=5001

# Option 2: Stop conflicting service
lsof -ti:5000 | xargs kill -9

# Option 3: Use different port in docker-compose.yml
ports:
  - "5001:5000"
```

### Issue: Permission denied

**Symptoms:**
```
Permission denied: /var/run/docker.sock
```

**Solution:**
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Log out and log back in
# Or use sudo (not recommended)
```

---

## 🏃 Service Startup Issues

### Issue: Services won't start

**Symptoms:**
```bash
docker-compose up
# Exits with error
```

**Diagnosis:**
```bash
# Check logs
docker-compose logs app

# Check service status
docker-compose ps
```

**Common Causes & Solutions:**

1. **Missing environment variables:**
   ```bash
   # Ensure .env file exists
   cp .env.example .env
   # Edit .env with required values
   ```

2. **Invalid configuration:**
   ```bash
   # Validate configuration
   make config
   ```

3. **Port conflicts:**
   ```bash
   # Check what's using the port
   lsof -i :5000
   # Change port if needed
   ```

4. **Docker daemon not running:**
   ```bash
   # Start Docker daemon
   sudo systemctl start docker  # Linux
   # Or start Docker Desktop
   ```

### Issue: Database initialization fails

**Symptoms:**
```
Error creating database tables
```

**Solution:**
```bash
# Re-initialize database
make init-db

# Or manually
docker-compose exec app python -c "from scraper.schema import init_db; init_db('social_media.db')"

# Check database permissions
ls -la social_media.db
```

### Issue: Redis connection fails

**Symptoms:**
```
Error connecting to Redis
```

**Solution:**
```bash
# Check Redis is running
docker-compose ps redis

# Check Redis logs
docker-compose logs redis

# Test Redis connection
docker-compose exec app python -c "import redis; r = redis.from_url('redis://localhost:6379/0'); print(r.ping())"

# Restart Redis
docker-compose restart redis
```

---

## 🗄️ Database Issues

### Issue: Database locked

**Symptoms:**
```
sqlite3.OperationalError: database is locked
```

**Solution:**
```bash
# Check for other processes using database
lsof social_media.db

# Stop all services
docker-compose down

# Restart services
docker-compose up -d
```

### Issue: Migration errors

**Symptoms:**
```
Alembic migration failed
```

**Solution:**
```bash
# Check migration status
docker-compose exec app alembic current

# View migration history
docker-compose exec app alembic history

# Run migrations
docker-compose exec app alembic upgrade head

# If needed, rollback and re-run
docker-compose exec app alembic downgrade -1
docker-compose exec app alembic upgrade head
```

### Issue: Connection pool exhausted

**Symptoms:**
```
QueuePool limit of size X overflow Y reached
```

**Solution:**
```bash
# Increase pool size in .env
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30

# Restart services
docker-compose restart app
```

### Issue: Database file not found

**Symptoms:**
```
sqlite3.OperationalError: no such file or directory
```

**Solution:**
```bash
# Create database directory
mkdir -p data

# Initialize database
make init-db

# Check DATABASE_PATH in .env
DATABASE_PATH=data/social_media.db
```

---

## 🔴 Redis Issues

### Issue: Redis not responding

**Symptoms:**
```
Connection refused to Redis
```

**Solution:**
```bash
# Check Redis container
docker-compose ps redis

# Check Redis logs
docker-compose logs redis

# Restart Redis
docker-compose restart redis

# Verify Redis URL in .env
REDIS_URL=redis://localhost:6379/0
```

### Issue: Cache not working

**Symptoms:**
- Slow API responses
- No cache hits

**Solution:**
```bash
# Check Redis connection
docker-compose exec app python -c "from cache.redis_client import redis_client; print(redis_client.ping())"

# Check cache configuration
grep CACHE_TYPE .env

# Verify Redis is accessible
docker-compose exec app redis-cli -h redis ping
```

### Issue: Redis memory limit reached

**Symptoms:**
```
OOM command not allowed when used memory > 'maxmemory'
```

**Solution:**
```bash
# Increase Redis memory limit in docker-compose.yml
redis:
  command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru

# Or clear Redis cache
docker-compose exec redis redis-cli FLUSHALL
```

---

## 🕷️ Scraper Issues

### Issue: Scrapers failing

**Symptoms:**
- Scraper jobs failing
- No data collected

**Diagnosis:**
```bash
# Check scraper logs
docker-compose logs worker

# Check job status
curl http://localhost:5000/api/v1/jobs/status \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Common Causes & Solutions:**

1. **Rate limiting:**
   ```bash
   # Check rate limit settings
   # Adjust in scraper/utils/rate_limiter.py
   ```

2. **Platform changes:**
   ```bash
   # Update scraper for platform changes
   # Check scraper/platforms/*.py
   ```

3. **API keys missing:**
   ```bash
   # Set required API keys in .env
   YOUTUBE_API_KEY=your-key
   TWITTER_BEARER_TOKEN=your-token
   ```

4. **Network issues:**
   ```bash
   # Test network connectivity
   docker-compose exec app curl -I https://x.com
   ```

### Issue: Scrapers timing out

**Symptoms:**
```
Timeout waiting for scraper response
```

**Solution:**
```bash
# Increase timeout in .env
SCRAPER_TIMEOUT=60

# Or in scraper/config.py
```

### Issue: Rate limit errors

**Symptoms:**
```
429 Too Many Requests
```

**Solution:**
```bash
# Reduce worker count
SCRAPER_MAX_WORKERS=2

# Increase rate limit delays
# Edit scraper/utils/rate_limiter.py
```

---

## 🌐 API Issues

### Issue: API endpoints return 401

**Symptoms:**
```
401 Unauthorized
```

**Solution:**
```bash
# Login first
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'

# Use token in requests
curl -X GET http://localhost:5000/api/v1/metrics/summary \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Issue: API endpoints return 403

**Symptoms:**
```
403 Forbidden
```

**Solution:**
- Check user role has required permissions
- Verify role in JWT token
- Use admin account for admin endpoints

### Issue: API validation errors

**Symptoms:**
```
422 Validation Error
```

**Solution:**
- Check request format matches API schema
- Verify required fields are present
- Check data types match expected format
- See API documentation at `/api/docs`

### Issue: API slow responses

**Symptoms:**
- Slow API response times

**Diagnosis:**
```bash
# Check performance endpoint
curl http://localhost:5000/api/performance

# Check cache status
curl http://localhost:5000/health
```

**Solutions:**
```bash
# Enable Redis caching
REDIS_URL=redis://localhost:6379/0

# Check database indexes
# See docs/PERFORMANCE_OPTIMIZATION_GUIDE.md
```

---

## 🔐 Authentication Issues

### Issue: Cannot login

**Symptoms:**
```
Invalid username or password
```

**Solution:**
```bash
# Check if user exists
docker-compose exec app python -c "from models.user import User; from sqlalchemy.orm import sessionmaker; from scraper.schema import init_db; engine = init_db('social_media.db'); Session = sessionmaker(bind=engine); session = Session(); users = session.query(User).all(); print([u.username for u in users])"

# Create admin user
docker-compose exec app python -c "from auth.utils import create_default_admin; create_default_admin()"

# Reset password (if needed)
# Use password reset endpoint
```

### Issue: JWT token expired

**Symptoms:**
```
Token has expired
```

**Solution:**
```bash
# Refresh token
curl -X POST http://localhost:5000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "YOUR_REFRESH_TOKEN"}'

# Or login again
```

### Issue: MFA not working

**Symptoms:**
- Cannot complete MFA setup
- MFA codes not accepted

**Solution:**
```bash
# Check time synchronization
# MFA requires accurate system time

# Verify MFA secret
# Check in database or re-enroll
```

---

## ⚡ Performance Issues

### Issue: Slow database queries

**Symptoms:**
- Slow API responses
- Database query timeouts

**Diagnosis:**
```bash
# Check slow queries
# Enable query logging in database

# Check indexes
docker-compose exec app python scripts/add_indexes.py
```

**Solutions:**
```bash
# Add database indexes
# See scripts/add_indexes.py

# Optimize queries
# See docs/PERFORMANCE_OPTIMIZATION_GUIDE.md

# Increase connection pool
DB_POOL_SIZE=20
```

### Issue: High memory usage

**Symptoms:**
- Container memory limits reached
- Out of memory errors

**Solution:**
```bash
# Check memory usage
docker stats

# Reduce worker concurrency
CELERY_WORKER_CONCURRENCY=2

# Reduce scraper workers
SCRAPER_MAX_WORKERS=3

# Increase container memory limits in docker-compose.yml
```

### Issue: Slow scraper execution

**Symptoms:**
- Scrapers take too long
- Jobs timeout

**Solution:**
```bash
# Increase workers for parallel processing
SCRAPER_MAX_WORKERS=10

# Optimize scraper configuration
# See scraper/config.py

# Check network connectivity
# Ensure stable internet connection
```

---

## 🚀 Deployment Issues

### Issue: Kubernetes pods not starting

**Symptoms:**
```
Pod status: CrashLoopBackOff
```

**Diagnosis:**
```bash
# Check pod logs
kubectl logs -n social-media-scraper <pod-name>

# Check pod events
kubectl describe pod -n social-media-scraper <pod-name>
```

**Common Causes:**
- Missing secrets/configmaps
- Incorrect environment variables
- Resource limits too low
- Database connection issues

### Issue: Health checks failing

**Symptoms:**
```
Readiness probe failed
```

**Solution:**
```bash
# Check health endpoint manually
kubectl exec -n social-media-scraper <pod-name> -- curl http://localhost:5000/health

# Adjust health check settings in deployment
# See k8s/deployment-app.yaml
```

### Issue: Database migrations failing in K8s

**Symptoms:**
- Migrations don't run
- Database schema out of date

**Solution:**
```bash
# Run migrations manually
kubectl exec -n social-media-scraper <pod-name> -- alembic upgrade head

# Or use init container
# See k8s/deployment-app.yaml
```

---

## 🔧 Advanced Troubleshooting

### Enable Debug Logging

```bash
# In .env
LOG_LEVEL=DEBUG
FLASK_DEBUG=True

# Restart services
docker-compose restart app
```

### Check System Resources

```bash
# Docker resources
docker stats

# Disk space
df -h

# Memory
free -h

# CPU
top
```

### Inspect Container

```bash
# Get shell access
docker-compose exec app bash

# Check Python environment
docker-compose exec app python --version

# Check installed packages
docker-compose exec app pip list
```

### Database Inspection

```bash
# SQLite browser
sqlite3 social_media.db

# Check tables
.tables

# Check schema
.schema dim_account

# Query data
SELECT * FROM dim_account LIMIT 5;
```

---

## 📞 Getting More Help

### Logs Location

- **Application logs**: `docker-compose logs app`
- **Worker logs**: `docker-compose logs worker`
- **Redis logs**: `docker-compose logs redis`
- **All logs**: `docker-compose logs`

### Useful Commands

```bash
# View all logs
make logs

# Check configuration
make config

# Check health
make health

# View service status
make status

# Restart services
make restart

# Rebuild services
make rebuild
```

### Documentation

- **[QUICK_START.md](./QUICK_START.md)** - Getting started guide
- **[DEPLOYMENT.md](./DEPLOYMENT.md)** - Deployment guide
- **[CONFIGURATION.md](./CONFIGURATION.md)** - Configuration reference
- **[API_USAGE.md](./docs/API_USAGE.md)** - API documentation

---

## ✅ Still Having Issues?

1. **Check logs** for error messages
2. **Verify configuration** matches your environment
3. **Check documentation** for your specific issue
4. **Review GitHub issues** for similar problems
5. **Create a new issue** with:
   - Error messages
   - Steps to reproduce
   - Configuration (without secrets)
   - Logs (sanitized)

---

**Remember**: Most issues can be resolved by checking logs and configuration! 🔍


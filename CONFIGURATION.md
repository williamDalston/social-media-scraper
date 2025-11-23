# Configuration Guide

Complete reference for configuring the HHS Social Media Scraper application.

---

## 📋 Table of Contents

- [Quick Configuration](#quick-configuration)
- [Environment Variables](#environment-variables)
- [Application Configuration](#application-configuration)
- [Database Configuration](#database-configuration)
- [Redis Configuration](#redis-configuration)
- [Scraper Configuration](#scraper-configuration)
- [Security Configuration](#security-configuration)
- [Monitoring Configuration](#monitoring-configuration)
- [Environment-Specific Settings](#environment-specific-settings)

---

## ⚡ Quick Configuration

### Minimum Required Settings

Create a `.env` file in the project root:

```bash
# Copy template
cp .env.example .env

# Minimum required variables
SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
DATABASE_PATH=social_media.db
```

---

## 🔧 Environment Variables

### Application Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FLASK_ENV` | No | `production` | Flask environment (development, production, testing) |
| `FLASK_DEBUG` | No | `False` | Enable Flask debug mode |
| `APP_PORT` | No | `5000` | Application port |
| `APP_HOST` | No | `0.0.0.0` | Application host |
| `SECRET_KEY` | **Yes** | - | Flask secret key for sessions |
| `JWT_SECRET_KEY` | **Yes** | - | JWT token signing key |

### Database Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_PATH` | No | `social_media.db` | SQLite database path |
| `DATABASE_URL` | No | - | PostgreSQL connection URL (overrides DATABASE_PATH) |
| `DB_POOL_SIZE` | No | `5` | Database connection pool size |
| `DB_MAX_OVERFLOW` | No | `10` | Max overflow connections |

**PostgreSQL Example:**
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/social_media
```

### Redis Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis connection URL |
| `REDIS_HOST` | No | `localhost` | Redis host |
| `REDIS_PORT` | No | `6379` | Redis port |
| `REDIS_DB` | No | `0` | Redis database number |
| `REDIS_PASSWORD` | No | - | Redis password |

**Example:**
```bash
REDIS_URL=redis://:password@localhost:6379/0
```

### Celery Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CELERY_BROKER_URL` | No | `redis://localhost:6379/0` | Celery broker URL |
| `CELERY_RESULT_BACKEND` | No | `redis://localhost:6379/0` | Celery result backend |
| `CELERY_WORKER_CONCURRENCY` | No | `4` | Number of worker processes |
| `CELERY_TASK_SOFT_TIME_LIMIT` | No | `3600` | Task soft time limit (seconds) |
| `CELERY_TASK_TIME_LIMIT` | No | `7200` | Task hard time limit (seconds) |

### Security Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CORS_ORIGINS` | No | `http://localhost:5000` | Allowed CORS origins (comma-separated) |
| `RATE_LIMIT_STORAGE` | No | `memory://` | Rate limit storage (memory:// or redis://) |
| `JWT_ACCESS_TOKEN_EXPIRES` | No | `86400` | Access token expiration (seconds) |
| `JWT_REFRESH_TOKEN_EXPIRES` | No | `604800` | Refresh token expiration (seconds) |
| `SESSION_COOKIE_SECURE` | No | `True` | Secure session cookies (HTTPS only) |
| `SESSION_COOKIE_HTTPONLY` | No | `True` | HTTP-only session cookies |

### OAuth2 Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_CLIENT_ID` | No | - | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | No | - | Google OAuth client secret |
| `MICROSOFT_CLIENT_ID` | No | - | Microsoft OAuth client ID |
| `MICROSOFT_CLIENT_SECRET` | No | - | Microsoft OAuth client secret |
| `GITHUB_CLIENT_ID` | No | - | GitHub OAuth client ID |
| `GITHUB_CLIENT_SECRET` | No | - | GitHub OAuth client secret |

### Monitoring Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `LOG_FORMAT` | No | `text` | Log format (text or json) |
| `LOG_FILE` | No | - | Log file path (optional) |
| `SENTRY_DSN` | No | - | Sentry DSN for error tracking |
| `ENVIRONMENT` | No | `production` | Environment name (dev, staging, production) |
| `RELEASE_VERSION` | No | - | Release version for tracking |

### Scraper Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SCRAPER_MODE` | No | `simulated` | Scraper mode (simulated, real) |
| `SCRAPER_MAX_WORKERS` | No | `5` | Maximum parallel scraper workers |
| `SCRAPER_TIMEOUT` | No | `30` | Request timeout (seconds) |
| `SCRAPER_RETRIES` | No | `3` | Number of retries on failure |
| `YOUTUBE_API_KEY` | No | - | YouTube Data API key |
| `TWITTER_BEARER_TOKEN` | No | - | Twitter API bearer token |

### Cache Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CACHE_TYPE` | No | `redis` | Cache type (redis, simple) |
| `CACHE_REDIS_URL` | No | `redis://localhost:6379/1` | Redis cache URL |
| `CACHE_DEFAULT_TIMEOUT` | No | `300` | Default cache timeout (seconds) |

---

## 🏗️ Application Configuration

### Configuration Files

Configuration can be set via:
1. Environment variables (`.env` file)
2. Configuration files (`config/settings.py`)
3. Environment-specific configs (`config/values-*.yaml`)

### Environment-Specific Configuration

The application supports environment-specific configuration:

- **Development**: `config/values-dev.yaml`
- **Staging**: `config/values-staging.yaml`
- **Production**: `config/values-prod.yaml`

Load with:
```bash
ENVIRONMENT=dev        # Loads values-dev.yaml
ENVIRONMENT=staging    # Loads values-staging.yaml
ENVIRONMENT=production # Loads values-prod.yaml
```

---

## 🗄️ Database Configuration

### SQLite (Default)

```bash
DATABASE_PATH=social_media.db
```

### PostgreSQL (Recommended for Production)

```bash
DATABASE_URL=postgresql://user:password@host:5432/database
```

**Connection Pool Settings:**
```bash
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_RECYCLE=3600
```

### Database Migrations

```bash
# Run migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "Description"

# Rollback migration
alembic downgrade -1
```

---

## 🔴 Redis Configuration

### Local Redis

```bash
REDIS_URL=redis://localhost:6379/0
```

### Redis with Password

```bash
REDIS_URL=redis://:password@localhost:6379/0
```

### Redis Cluster

```bash
REDIS_URL=redis://node1:6379,node2:6379,node3:6379/0
```

### Redis Configuration for Production

- Enable persistence (AOF or RDB)
- Set appropriate memory limits
- Configure eviction policies
- Enable replication for high availability

---

## 🕷️ Scraper Configuration

### Scraper Settings

Configure in `scraper/config.py` or via environment:

```bash
# Scraper behavior
SCRAPER_MODE=real                    # real or simulated
SCRAPER_MAX_WORKERS=5                # Parallel workers
SCRAPER_TIMEOUT=30                   # Request timeout
SCRAPER_RETRIES=3                    # Retry attempts

# Platform-specific settings
YOUTUBE_API_KEY=your-youtube-api-key
TWITTER_BEARER_TOKEN=your-twitter-token
```

### Rate Limiting

Rate limits are configured per platform in `scraper/utils/rate_limiter.py`:

- X (Twitter): 15 requests per 15 minutes
- Instagram: 10 requests per hour
- Facebook: 10 requests per hour
- LinkedIn: 5 requests per hour
- YouTube: 10,000 units per day (API quota)
- Truth Social: 5 requests per minute

---

## 🔐 Security Configuration

### Authentication

```bash
# JWT Configuration
JWT_SECRET_KEY=your-secret-key-min-32-chars
JWT_ACCESS_TOKEN_EXPIRES=86400      # 24 hours
JWT_REFRESH_TOKEN_EXPIRES=604800    # 7 days

# Session Configuration
SESSION_COOKIE_SECURE=True          # HTTPS only
SESSION_COOKIE_HTTPONLY=True        # No JavaScript access
SESSION_COOKIE_SAMESITE=Lax         # CSRF protection
```

### Rate Limiting

```bash
# Global rate limits
RATE_LIMIT_DEFAULT=100 per hour
RATE_LIMIT_STORAGE=redis://localhost:6379/0

# Per-endpoint limits configured in app.py
```

### CORS

```bash
# Allowed origins (comma-separated)
CORS_ORIGINS=http://localhost:5000,https://yourdomain.com
```

---

## 📊 Monitoring Configuration

### Logging

```bash
# Log level
LOG_LEVEL=INFO                       # DEBUG, INFO, WARNING, ERROR, CRITICAL

# Log format
LOG_FORMAT=json                      # text or json

# Log file (optional)
LOG_FILE=/var/log/app.log

# Daily log rotation
ENABLE_DAILY_LOGS=true
```

### Sentry (Error Tracking)

```bash
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
ENVIRONMENT=production
RELEASE_VERSION=1.0.0
SENTRY_TRACES_SAMPLE_RATE=0.1        # 10% of transactions traced
```

### Prometheus Metrics

Metrics are automatically exported at `/metrics` endpoint.

---

## 🌍 Environment-Specific Settings

### Development

```bash
FLASK_ENV=development
FLASK_DEBUG=True
LOG_LEVEL=DEBUG
LOG_FORMAT=text
DATABASE_PATH=social_media_dev.db
SCRAPER_MODE=simulated
```

### Staging

```bash
FLASK_ENV=production
FLASK_DEBUG=False
LOG_LEVEL=INFO
LOG_FORMAT=json
DATABASE_URL=postgresql://user:pass@staging-db:5432/social_media
SCRAPER_MODE=real
```

### Production

```bash
FLASK_ENV=production
FLASK_DEBUG=False
LOG_LEVEL=WARNING
LOG_FORMAT=json
LOG_FILE=/var/log/app.log
DATABASE_URL=postgresql://user:pass@prod-db:5432/social_media
REDIS_URL=redis://prod-redis:6379/0
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
ENVIRONMENT=production
```

---

## ✅ Configuration Validation

### Validate Configuration

```bash
# Check configuration
python -c "from config.settings import validate_config; validate_config()"

# Or use Makefile
make config
```

### Generate Secrets

```bash
# Generate SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"

# Generate JWT_SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"

# Generate password hash
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('your-password'))"
```

---

## 🔄 Configuration Priority

Configuration is loaded in this order (later overrides earlier):

1. **Default values** (in code)
2. **Environment-specific YAML** (`config/values-*.yaml`)
3. **Environment variables** (`.env` file)
4. **Runtime configuration** (command line, etc.)

---

## 📝 Example Configuration Files

### Minimal `.env` (Development)

```bash
SECRET_KEY=dev-secret-key-change-in-production
JWT_SECRET_KEY=dev-jwt-secret-change-in-production
DATABASE_PATH=social_media.db
FLASK_ENV=development
LOG_LEVEL=DEBUG
```

### Production `.env`

```bash
# Application
FLASK_ENV=production
SECRET_KEY=<generated-secret-key>
JWT_SECRET_KEY=<generated-jwt-secret>

# Database
DATABASE_URL=postgresql://user:password@db-host:5432/social_media

# Redis
REDIS_URL=redis://:password@redis-host:6379/0

# Celery
CELERY_BROKER_URL=redis://:password@redis-host:6379/0
CELERY_RESULT_BACKEND=redis://:password@redis-host:6379/0

# Logging
LOG_LEVEL=WARNING
LOG_FORMAT=json
LOG_FILE=/var/log/app.log

# Monitoring
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
ENVIRONMENT=production
RELEASE_VERSION=1.0.0

# Security
CORS_ORIGINS=https://yourdomain.com
SESSION_COOKIE_SECURE=True

# Scrapers
SCRAPER_MODE=real
YOUTUBE_API_KEY=your-youtube-api-key
```

---

## 🆘 Troubleshooting

### Configuration Issues

**Configuration not loading:**
- Check `.env` file exists in project root
- Verify environment variable names (case-sensitive)
- Check for typos in variable names

**Database connection errors:**
- Verify `DATABASE_URL` or `DATABASE_PATH` is correct
- Check database credentials
- Ensure database server is running

**Redis connection errors:**
- Verify `REDIS_URL` is correct
- Check Redis server is running
- Verify network connectivity

**See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for more help**

---

**Need help?** Check the [documentation](./README.md) or [troubleshooting guide](./TROUBLESHOOTING.md).


# Agent 5: OBSERVABILITY_SPECIALIST (Eli)
## Production Enhancement: Monitoring, Logging & Observability

### 🎯 Mission
Implement comprehensive logging, error tracking, health checks, and monitoring to ensure system reliability and enable quick troubleshooting in production.

---

## 📋 Detailed Tasks

### 1. Structured Logging

#### 1.1 Logging Configuration
- **File:** `config/logging_config.py`
- Configure:
  - Log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  - Log format (JSON for production, readable for dev)
  - Log rotation (size-based, time-based)
  - Multiple handlers (console, file, external service)

#### 1.2 Structured Logging
- **Package:** `python-json-logger` or `structlog`
- Log format:
  - Timestamp
  - Log level
  - Logger name
  - Message
  - Context (user_id, request_id, account_key, etc.)
  - Stack traces for errors

#### 1.3 Logging Middleware
- **File:** `middleware/logging_middleware.py`
- Log:
  - All HTTP requests (method, path, status, duration)
  - Request/response sizes
  - User agent, IP address
  - Authentication status
  - Error responses

#### 1.4 Application Logging
- Replace all `print()` statements with proper logging
- Add logging to:
  - Scraper execution
  - Database operations
  - API endpoints
  - Background jobs
  - Error conditions

---

### 2. Error Tracking

#### 2.1 Sentry Integration
- **Package:** `sentry-sdk[flask]`
- **File:** `config/sentry_config.py`
- Configure:
  - DSN from environment
  - Environment (dev, staging, prod)
  - Release version
  - User context
  - Breadcrumbs

#### 2.2 Error Capture
- Capture:
  - Unhandled exceptions
  - API errors (4xx, 5xx)
  - Scraper failures
  - Database errors
  - Background job failures

#### 2.3 Error Context
- Add context to errors:
  - User information
  - Request details
  - Account/platform being scraped
  - Job ID (if applicable)
  - Stack traces

#### 2.4 Error Alerting
- Configure alerts for:
  - Critical errors (5xx)
  - High error rate
  - Scraper failures
  - Database connection issues

---

### 3. Health Checks

#### 3.1 Health Endpoint
- **File:** `app.py` (add routes)
- Endpoints:
  - `GET /health` - Basic health check
  - `GET /health/ready` - Readiness probe (Kubernetes)
  - `GET /health/live` - Liveness probe (Kubernetes)

#### 3.2 Health Check Components
- Check:
  - Database connectivity
  - Redis connectivity (if using Celery)
  - External API availability (optional)
  - Disk space
  - Memory usage

#### 3.3 Health Status Response
- Return:
  - Overall status (healthy, degraded, unhealthy)
  - Component statuses
  - Timestamp
  - Version information

---

### 4. Metrics Collection

#### 4.1 Application Metrics
- **Package:** `prometheus-client` (optional)
- Track:
  - API request count by endpoint
  - API response times
  - Error rates
  - Scraper success/failure rates
  - Database query times
  - Background job durations

#### 4.2 Custom Metrics
- Metrics:
  - Accounts scraped per day
  - Average scraping time
  - Cache hit/miss rates
  - Active users
  - Job queue length

#### 4.3 Metrics Endpoint
- **Endpoint:** `GET /metrics` (Prometheus format)
- Expose metrics for scraping

---

### 5. Monitoring Dashboard

#### 5.1 Admin Dashboard
- **File:** `templates/admin_dashboard.html`
- Display:
  - System health status
  - Recent errors (from Sentry or logs)
  - Active background jobs
  - API performance metrics
  - Scraper statistics
  - Database statistics

#### 5.2 Real-time Updates
- Use WebSocket or polling for:
  - Job progress
  - Error notifications
  - System status changes

#### 5.3 Log Viewer (Optional)
- Simple log viewer in admin dashboard
- Filter by level, time, component
- Search functionality

---

## 📁 File Structure to Create

```
config/
├── __init__.py
├── logging_config.py
└── sentry_config.py

middleware/
├── __init__.py
└── logging_middleware.py

templates/
└── admin_dashboard.html

static/
└── js/
    └── admin_dashboard.js
```

---

## 🔧 Dependencies to Add

Add to `requirements.txt`:
```
sentry-sdk[flask]>=1.38.0
python-json-logger>=2.0.7
prometheus-client>=0.18.0    # Optional
```

---

## ✅ Acceptance Criteria

- [ ] Structured logging is implemented
- [ ] All print statements replaced with logging
- [ ] Sentry is integrated and capturing errors
- [ ] Health check endpoints work
- [ ] Metrics are collected (optional)
- [ ] Admin dashboard displays monitoring data
- [ ] Logs are properly formatted and rotated
- [ ] Error context is captured

---

## 🧪 Testing Requirements

- Test logging output
- Test error capture
- Test health checks
- Test metrics collection
- Test admin dashboard

---

## 📝 Implementation Details

### Logging Configuration Example:
```python
import logging
from pythonjsonlogger import jsonlogger

logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger = logging.getLogger()
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)
```

### Sentry Configuration:
```python
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

sentry_sdk.init(
    dsn=os.getenv('SENTRY_DSN'),
    integrations=[FlaskIntegration()],
    environment=os.getenv('ENVIRONMENT', 'development'),
    traces_sample_rate=0.1
)
```

### Health Check Example:
```python
@app.route('/health')
def health():
    checks = {
        'database': check_database(),
        'redis': check_redis(),
    }
    status = 'healthy' if all(checks.values()) else 'unhealthy'
    return jsonify({'status': status, 'checks': checks})
```

---

## 🚀 Getting Started

1. Create branch: `git checkout -b feature/agent-5-observability`
2. Install dependencies: `pip install -r requirements.txt`
3. Set up logging configuration
4. Replace print statements with logging
5. Integrate Sentry
6. Add health check endpoints
7. Add metrics collection (optional)
8. Create admin dashboard
9. Test all components
10. Update documentation

---

## 🔧 Environment Variables

Add to `.env`:
```
# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json  # or 'text' for development

# Sentry
SENTRY_DSN=https://...
ENVIRONMENT=production

# Health Checks
HEALTH_CHECK_TIMEOUT=5
```

---

## 📊 Monitoring Best Practices

- **Log Levels:** Use appropriate levels (DEBUG for dev, INFO for prod)
- **Log Rotation:** Rotate logs to prevent disk fill
- **Error Context:** Always include context with errors
- **Performance:** Don't log sensitive data
- **Retention:** Set log retention policies
- **Alerting:** Set up alerts for critical errors

---

## 🔍 Log Examples

### Request Logging:
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "logger": "flask.request",
  "message": "GET /api/summary",
  "status": 200,
  "duration_ms": 45,
  "user_id": "user123",
  "ip": "192.168.1.1"
}
```

### Error Logging:
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "ERROR",
  "logger": "scraper",
  "message": "Failed to scrape account",
  "account_key": 123,
  "platform": "X",
  "error": "Rate limit exceeded",
  "stack_trace": "..."
}
```

---

## ⚠️ Important Considerations

- **Privacy:** Don't log sensitive user data
- **Performance:** Async logging for high-volume scenarios
- **Cost:** Monitor log storage costs
- **Compliance:** Ensure logging meets compliance requirements
- **Debugging:** Keep detailed logs for troubleshooting
- **Security:** Secure log access

---

**Agent Eli - Ready to observe everything! 📊**


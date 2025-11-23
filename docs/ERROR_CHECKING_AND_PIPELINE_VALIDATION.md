# Error Checking and Pipeline Validation System

This document describes the comprehensive error checking and pipeline validation system implemented for the social media scraper project.

## Overview

The system provides:
- **System Validation**: Comprehensive startup and runtime checks
- **Pipeline Validation**: End-to-end data pipeline validation
- **Error Detection**: Enhanced error detection with automatic classification and fix suggestions
- **Continuous Monitoring**: Background monitoring with automatic alerting
- **Pre-Flight Checks**: Deployment validation before startup
- **Health Dashboard**: API endpoints for system status and diagnostics

## Components

### 1. System Validation (`config/system_validation.py`)

Validates all system components on startup and runtime.

**Features:**
- Environment variable validation
- Python version checks
- Dependency verification
- Database connectivity and schema validation
- Configuration validation
- File permissions checks
- Port availability checks
- Optional service checks (Redis, Celery)

**Usage:**

```python
from config.system_validation import SystemValidator, validate_system_on_startup

# Run all validations
validator = SystemValidator()
all_passed, results = validator.validate_all(skip_optional=False)

# Validate on startup (raises SystemExit on critical failures)
validate_system_on_startup(skip_optional=False)
```

**Command Line:**

```bash
python config/system_validation.py
```

### 2. Pipeline Validation (`config/pipeline_checks.py`)

Validates the entire data pipeline from input to output.

**Stages Validated:**
- **Input**: Account data files, CSV uploads, upload directories
- **Scraping**: Scraper modules, platform scrapers, retry logic
- **Processing**: Data models, validation modules
- **Storage**: Database tables, cache connectivity
- **Output**: API modules, export libraries
- **Monitoring**: Logging, metrics, health checks

**Usage:**

```python
from config.pipeline_checks import PipelineValidator, validate_pipeline

# Run all pipeline checks
all_passed, summary = validate_pipeline()

# Or use validator directly
validator = PipelineValidator()
all_passed, results = validator.validate_all()
summary = validator.get_summary()
```

### 3. Error Detection (`config/error_detection.py`)

Enhanced error detection with automatic classification and fix suggestions.

**Features:**
- Automatic error classification (Database, Network, Authentication, etc.)
- Severity assessment (Critical, High, Medium, Low)
- Stack trace extraction
- Context capture (file, line, function, module)
- Fix suggestions with step-by-step instructions
- Error pattern tracking
- Error summary and statistics

**Usage:**

```python
from config.error_detection import detect_error, get_error_summary, get_fix_suggestion

try:
    # Your code that might raise an exception
    pass
except Exception as e:
    # Detect and analyze error
    error_context = detect_error(e, context={
        'request_id': 'req-123',
        'user_id': 'user-456',
        'account_key': 'account-789'
    })
    
    # Get fix suggestion
    fix = get_fix_suggestion(error_context)
    if fix:
        print(f"Fix: {fix.description}")
        for step in fix.steps:
            print(f"  - {step}")
    
    # Get error summary
    summary = get_error_summary(timedelta(hours=24))
    print(f"Total errors in last 24h: {summary['total_errors']}")
```

### 4. Continuous Monitoring (`config/continuous_monitoring.py`)

Background monitoring system that runs periodic checks and sends alerts.

**Default Checks:**
- System validation (every 30 minutes)
- Pipeline validation (every 30 minutes)
- Health checks (every 5 minutes)
- Error summary (every 5 minutes)
- Alert rules (every 5 minutes)

**Usage:**

```python
from config.continuous_monitoring import start_monitoring, stop_monitoring, get_monitor

# Start monitoring (typically in app startup)
start_monitoring()

# Get monitor status
monitor = get_monitor()
status = monitor.get_status()

# Stop monitoring (typically in app shutdown)
stop_monitoring()
```

**Custom Checks:**

```python
from config.continuous_monitoring import get_monitor

monitor = get_monitor()

def my_custom_check():
    # Your check logic
    return {'success': True, 'message': 'Check passed'}

monitor.add_check(
    name="custom_check",
    check_function=my_custom_check,
    interval_seconds=600  # 10 minutes
)

# Add alert callback
def alert_callback(alert_type, message, details):
    print(f"Alert: {alert_type} - {message}")
    # Send email, Slack notification, etc.

monitor.add_alert_callback(alert_callback)
```

### 5. Pre-Flight Checks (`scripts/preflight-check.sh`)

Bash script for deployment validation before startup.

**Usage:**

```bash
# Run all checks
./scripts/preflight-check.sh

# Strict mode (exit on any failure)
./scripts/preflight-check.sh --strict

# Skip optional checks (Redis, Celery)
./scripts/preflight-check.sh --skip-optional
```

**Checks Performed:**
- Python version
- Required dependencies
- Environment variables
- Database connectivity and schema
- File permissions
- Port availability
- Optional services (Redis, Celery)
- Python system validation

### 6. System Health API (`api/system_health.py`)

REST API endpoints for system status and diagnostics.

**Endpoints:**

- `GET /api/system/validation` - System validation results
- `GET /api/system/pipeline` - Pipeline validation results
- `GET /api/system/health` - Comprehensive health checks
- `GET /api/system/errors` - Error summary and statistics
- `GET /api/system/status` - Overall system status
- `GET /api/system/diagnostics` - Full diagnostic information

**Example Requests:**

```bash
# Get system validation
curl http://localhost:5000/api/system/validation

# Get pipeline validation
curl http://localhost:5000/api/system/pipeline

# Get comprehensive health
curl http://localhost:5000/api/system/health

# Get error summary (last 24 hours)
curl http://localhost:5000/api/system/errors?time_window=24

# Get overall status
curl http://localhost:5000/api/system/status

# Get diagnostics
curl http://localhost:5000/api/system/diagnostics
```

## Integration

### Application Startup

Add to `app.py`:

```python
from config.system_validation import validate_system_on_startup
from config.continuous_monitoring import start_monitoring

# Validate system on startup
if os.getenv('FLASK_ENV') == 'production':
    validate_system_on_startup(skip_optional=False)

# Start continuous monitoring
start_monitoring()
```

### Error Handling Middleware

Add to error handlers:

```python
from config.error_detection import detect_error, get_fix_suggestion

@app.errorhandler(Exception)
def handle_exception(error):
    error_context = detect_error(error, context={
        'request_id': request.headers.get('X-Request-ID'),
        'user_id': getattr(request, 'user_id', None),
        'path': request.path,
        'method': request.method
    })
    
    fix = get_fix_suggestion(error_context)
    
    logger.error(f"Error: {error_context.error_message}", extra={
        'error_context': error_context.to_dict(),
        'fix_suggestion': fix.to_dict() if fix else None
    })
    
    # Return error response
    return jsonify({
        'error': error_context.error_message,
        'category': error_context.category.value,
        'severity': error_context.severity.value,
        'fix_suggestion': fix.to_dict() if fix else None
    }), 500
```

## CI/CD Integration

### GitHub Actions

The system is integrated into CI/CD pipelines:

**CI Pipeline** (`.github/workflows/ci.yml`):
- Runs system validation
- Runs pipeline validation
- Pre-flight checks (non-blocking)

**Deploy Pipeline** (`.github/workflows/deploy.yml`):
- Pre-deploy validation (strict mode)
- System validation (blocking)
- Pipeline validation (blocking)

## Best Practices

1. **Run Pre-Flight Checks Before Deployment**
   ```bash
   ./scripts/preflight-check.sh --strict
   ```

2. **Monitor System Health Regularly**
   - Check `/api/system/status` endpoint
   - Review error summaries
   - Monitor alert notifications

3. **Use Error Detection in Exception Handlers**
   - Always use `detect_error()` to capture context
   - Log fix suggestions for easier troubleshooting
   - Track error patterns

4. **Customize Monitoring Checks**
   - Add application-specific checks
   - Set appropriate intervals
   - Configure alert callbacks

5. **Review Validation Results**
   - Check validation summaries regularly
   - Address warnings before they become errors
   - Keep fix suggestions documented

## Troubleshooting

### System Validation Fails

1. Check error messages and fix suggestions
2. Review environment variables
3. Verify dependencies are installed
4. Check file permissions
5. Review database connectivity

### Pipeline Validation Fails

1. Check which stage failed
2. Verify required files exist
3. Check database schema
4. Review scraper configuration
5. Verify API modules are importable

### Continuous Monitoring Not Working

1. Check monitor status: `GET /api/system/diagnostics`
2. Review monitor logs
3. Verify check functions are working
4. Check alert callback configuration

### Errors Not Being Detected

1. Ensure `detect_error()` is called in exception handlers
2. Check error detection is imported
3. Review error context capture
4. Verify error history is being stored

## Configuration

### Environment Variables

- `MONITOR_CHECK_INTERVAL`: Monitoring check interval in seconds (default: 300)
- `FLASK_ENV`: Environment (development, staging, production)
- `DATABASE_PATH`: Database file path
- `LOG_DIRECTORY`: Log directory path

### Monitoring Configuration

Customize monitoring in `config/continuous_monitoring.py`:

```python
monitor = get_monitor()

# Add custom check
monitor.add_check(
    name="my_check",
    check_function=my_check_function,
    interval_seconds=600,
    enabled=True
)

# Add alert callback
def my_alert_callback(alert_type, message, details):
    # Send to Slack, email, etc.
    pass

monitor.add_alert_callback(my_alert_callback)
```

## Summary

The error checking and pipeline validation system provides:

✅ **Comprehensive Validation**: System and pipeline checks
✅ **Error Detection**: Automatic classification and fix suggestions
✅ **Continuous Monitoring**: Background health checks and alerts
✅ **Pre-Flight Checks**: Deployment validation
✅ **Health Dashboard**: API endpoints for status and diagnostics
✅ **Easy Troubleshooting**: Detailed error context and fix suggestions

This system ensures the application is running correctly and makes it easy to pinpoint and fix errors when they occur.


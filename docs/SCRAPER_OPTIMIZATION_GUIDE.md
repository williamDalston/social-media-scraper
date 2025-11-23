# Scraper Performance Optimization Guide

## Overview

This guide covers optimization strategies for achieving the best possible scraper results and performance.

---

## Performance Targets

- **Success Rate**: > 95%
- **Execution Time (p95)**: < 5 seconds per account
- **Execution Time (p99)**: < 10 seconds per account
- **Data Accuracy**: > 98%

---

## Optimization Strategies

### 1. Parallel Scraping

Use parallel scraping for multiple accounts:

```python
from scraper.utils.parallel import scrape_accounts_parallel

metrics = scrape_accounts_parallel(
    accounts=accounts,
    scraper=scraper,
    session_factory=Session,
    today=today,
    max_workers=5  # Adjust based on CPU cores
)
```

### 2. Intelligent Queuing

Prioritize core accounts:

```python
# Core accounts are processed first
accounts = sorted(
    accounts,
    key=lambda a: (not (a.is_core_account or False), a.account_key)
)
```

### 3. Rate Limiting

Respect platform rate limits:

```python
# Minimum 0.5 seconds between scrapes per platform
min_interval = 0.5
if elapsed < min_interval:
    time.sleep(min_interval - elapsed)
```

### 4. Error Handling

Implement retry logic with exponential backoff:

```python
from scraper.utils.retry import retry_with_backoff

@retry_with_backoff(max_retries=3, base_delay=1.0)
def scrape_account(account):
    # Scraping logic
    pass
```

### 5. Resource Optimization

Monitor and optimize resource usage:

- Adjust `max_workers` based on CPU cores
- Monitor memory usage
- Track execution times
- Optimize database writes

---

## Monitoring

### Scraper Metrics

Track scraper performance:

```bash
# Get scraper statistics
curl -H "Authorization: Bearer <token>" \
  http://localhost:5000/api/performance
```

Key metrics:
- Success rate (target: > 95%)
- Execution times (p95, p99)
- Error rates by platform
- Accounts per second

### Performance Tracking

The system tracks:
- Execution time per account
- Success/failure rates
- Platform-specific metrics
- Resource usage

---

## Best Practices

1. **Worker Count**: Set `max_workers` to 2-4x CPU cores
2. **Rate Limiting**: Respect platform limits (0.5s minimum)
3. **Prioritization**: Process core accounts first
4. **Error Handling**: Retry with exponential backoff
5. **Monitoring**: Track metrics and optimize bottlenecks
6. **Resource Management**: Monitor CPU and memory usage

---

## Troubleshooting

### Low Success Rate

1. Check error logs for patterns
2. Review rate limiting settings
3. Verify platform API keys
4. Check network connectivity

### Slow Execution

1. Increase worker count (if CPU allows)
2. Review rate limiting delays
3. Optimize database writes
4. Check for blocking operations

### High Error Rate

1. Review platform-specific errors
2. Check API key validity
3. Verify network stability
4. Review retry logic

---

## Additional Resources

- [Production Performance Guide](./PRODUCTION_PERFORMANCE_GUIDE.md)
- [Performance Optimization Guide](./PERFORMANCE_OPTIMIZATION_GUIDE.md)


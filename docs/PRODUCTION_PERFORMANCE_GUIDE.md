# Production Performance Optimization Guide

## Overview

This guide provides comprehensive guidance for optimizing the HHS Social Media Scraper for production workloads. It covers performance tuning, monitoring, alerting, and best practices.

---

## Table of Contents

1. [Performance SLAs](#performance-slas)
2. [Performance Monitoring](#performance-monitoring)
3. [Cache Optimization](#cache-optimization)
4. [Database Optimization](#database-optimization)
5. [API Performance](#api-performance)
6. [Frontend Performance](#frontend-performance)
7. [Scraper Performance](#scraper-performance)
8. [Performance Tuning](#performance-tuning)
9. [Alerting and Troubleshooting](#alerting-and-troubleshooting)

---

## Performance SLAs

### Defined SLAs

The system tracks the following performance SLAs:

#### API Response Time
- **p95 Target**: < 500ms
- **p99 Target**: < 2 seconds
- **Warning Threshold**: 80% of target (400ms p95, 1.6s p99)

#### Database Query Time
- **p95 Target**: < 100ms
- **p99 Target**: < 500ms

#### Cache Hit Rate
- **Target**: > 80%
- **Warning**: < 70%

#### Scraper Execution Time
- **p95 Target**: < 5 seconds
- **p99 Target**: < 10 seconds

#### Frontend Load Time
- **p95 Target**: < 2 seconds
- **p99 Target**: < 3 seconds

### Checking SLA Status

```bash
# Get SLA status
curl -H "Authorization: Bearer <token>" \
  http://localhost:5000/api/performance/sla

# Get performance summary
curl -H "Authorization: Bearer <token>" \
  http://localhost:5000/api/performance
```

### SLA Monitoring

SLAs are automatically tracked and violations are logged. Use the `/api/performance/sla` endpoint to check current status.

---

## Performance Monitoring

### Metrics Tracked

The system tracks the following performance metrics:

1. **API Metrics**
   - Response times (avg, min, max, p95, p99)
   - Request counts
   - Error rates

2. **Cache Metrics**
   - Hit/miss rates
   - Operation times
   - L1 and L2 cache performance

3. **Database Metrics**
   - Query execution times
   - Slow query detection
   - Connection pool statistics

4. **Scraper Metrics**
   - Execution times
   - Success/failure rates
   - Platform-specific metrics

### Accessing Metrics

```bash
# Get all performance metrics
curl -H "Authorization: Bearer <token>" \
  http://localhost:5000/api/performance

# Get cache performance
curl -H "Authorization: Bearer <token>" \
  http://localhost:5000/api/performance/cache

# Get performance recommendations
curl -H "Authorization: Bearer <token>" \
  http://localhost:5000/api/performance/recommendations
```

### Performance Dashboards

The system provides several endpoints for monitoring:

- `/api/performance` - Overall performance metrics
- `/api/performance/sla` - SLA status and compliance
- `/api/performance/alerts` - Active alerts and history
- `/api/performance/cache` - Cache performance details
- `/api/performance/recommendations` - Optimization recommendations

---

## Cache Optimization

### Multi-Level Caching

The system uses a two-level cache architecture:

- **L1 Cache (Memory)**: Fast, local cache with 60s TTL
- **L2 Cache (Redis)**: Distributed cache with 300s TTL

### Cache Configuration

```python
# Environment variables for cache tuning
CACHE_L1_MAXSIZE=1000      # L1 cache max size
CACHE_L1_TTL=60            # L1 cache TTL (seconds)
CACHE_L2_TTL=300           # L2 cache TTL (seconds)
CACHE_DEFAULT_TIMEOUT=300  # Default cache timeout
```

### Cache Warming

Cache warming is automatically performed on application startup for:
- Summary data (all accounts)
- Top 5 accounts by followers
- Frequently accessed data

### Cache Monitoring

Monitor cache performance:

```bash
# Get cache statistics
curl -H "Authorization: Bearer <token>" \
  http://localhost:5000/api/performance/cache
```

Key metrics to watch:
- Overall hit rate (target: > 80%)
- L1 vs L2 hit rates
- Cache operation times
- Error rates

### Cache Optimization Tips

1. **Increase TTLs** for stable data (e.g., account lists)
2. **Implement cache warming** for frequently accessed data
3. **Monitor hit rates** and adjust TTLs accordingly
4. **Use appropriate cache keys** for efficient invalidation
5. **Monitor L1 vs L2** performance to optimize cache levels

---

## Database Optimization

### Connection Pooling

The system uses optimized connection pooling:

```python
# Production settings
DB_POOL_SIZE=10           # Base pool size
DB_MAX_OVERFLOW=20        # Maximum overflow connections
DB_POOL_TIMEOUT=30        # Connection timeout (seconds)
DB_POOL_RECYCLE=3600      # Connection recycle time (1 hour)
```

### Query Optimization

1. **Use Indexes**: All frequently queried columns are indexed
2. **Avoid N+1 Queries**: Use `joinedload()` for relationships
3. **Limit Result Sets**: Use pagination for large datasets
4. **Monitor Slow Queries**: Check `/api/performance` for slow query detection

### Database Monitoring

```bash
# Check database performance
curl -H "Authorization: Bearer <token>" \
  http://localhost:5000/api/performance
```

Look for:
- Query execution times (p95 should be < 100ms)
- Slow query count
- Connection pool utilization

### Query Profiling

Enable query profiling in development:

```python
# In app.py
enable_profiling = os.getenv('ENABLE_QUERY_PROFILING', 'false').lower() == 'true'
```

---

## API Performance

### Response Time Targets

- **Cached responses**: < 50ms
- **Database queries**: < 200ms
- **Uncached responses**: < 1 second

### Optimization Strategies

1. **Caching**: All list endpoints are cached
2. **Pagination**: Large datasets are paginated
3. **Compression**: Responses are compressed with gzip
4. **Field Selection**: Use `?fields=...` to reduce payload size
5. **Streaming**: Large exports use streaming

### API Monitoring

Monitor API performance:

```bash
# Get API statistics
curl -H "Authorization: Bearer <token>" \
  http://localhost:5000/api/performance
```

Key metrics:
- Response times by endpoint
- Error rates
- Request counts

---

## Frontend Performance

### Optimization Strategies

1. **Code Splitting**: JavaScript is split into modules
2. **Lazy Loading**: Charts load on demand
3. **Caching**: API responses cached in browser (5 min TTL)
4. **Debouncing**: Input handlers debounced (300ms)
5. **Service Worker**: Offline support and asset caching

### Frontend Monitoring

Monitor frontend performance using browser DevTools:
- Network tab: Check load times
- Performance tab: Check rendering performance
- Lighthouse: Run performance audits

### CDN Integration

For production, configure CDN for static assets:

```python
# In app.py or config
CDN_BASE_URL = os.getenv('CDN_BASE_URL', '')
```

See `docs/cdn_integration.md` for detailed CDN setup.

---

## Scraper Performance

### Parallel Scraping

The system supports parallel scraping:

```python
# In collect_metrics.py
simulate_metrics(
    parallel=True,
    max_workers=5  # Adjust based on system resources
)
```

### Optimization Tips

1. **Worker Count**: Adjust `max_workers` based on CPU cores
2. **Rate Limiting**: Respect platform rate limits (0.5s per platform)
3. **Prioritization**: Core accounts processed first
4. **Error Handling**: Retry failed scrapes with exponential backoff

### Scraper Monitoring

Monitor scraper performance:

```bash
# Get scraper statistics
curl -H "Authorization: Bearer <token>" \
  http://localhost:5000/api/performance
```

Key metrics:
- Success rate (target: > 95%)
- Execution times
- Error rates by platform

---

## Performance Tuning

### Automatic Tuning

The system provides automatic performance tuning based on environment:

```bash
# Get tuning configuration
curl -H "Authorization: Bearer <token>" \
  -H "X-Role: admin" \
  http://localhost:5000/api/performance/tuning
```

### Manual Tuning

Adjust environment variables:

```bash
# Database
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40

# Cache
CACHE_L1_MAXSIZE=2000
CACHE_L1_TTL=120
CACHE_L2_TTL=600

# Workers
CELERY_MAX_WORKERS=10
CELERY_PREFETCH=8
```

### Performance Recommendations

Get automated recommendations:

```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:5000/api/performance/recommendations
```

---

## Alerting and Troubleshooting

### Performance Alerts

The system automatically alerts on:

1. **API Response Time**
   - Warning: p95 > 1s
   - Critical: p95 > 2s

2. **Database Query Time**
   - Warning: p95 > 500ms

3. **Cache Hit Rate**
   - Warning: < 70%

4. **Scraper Performance**
   - Warning: p95 > 10s

5. **Error Rates**
   - Warning: > 5%

### Checking Alerts

```bash
# Get active alerts
curl -H "Authorization: Bearer <token>" \
  http://localhost:5000/api/performance/alerts
```

### Troubleshooting

#### Slow API Responses

1. Check cache hit rate: `/api/performance/cache`
2. Review slow queries: Check database metrics
3. Verify connection pool: Check pool utilization
4. Review recommendations: `/api/performance/recommendations`

#### Low Cache Hit Rate

1. Increase cache TTLs for stable data
2. Implement cache warming
3. Review cache invalidation strategy
4. Check Redis connectivity

#### Database Performance Issues

1. Review slow queries: Check query statistics
2. Verify indexes: Ensure all frequently queried columns are indexed
3. Check connection pool: Adjust pool size if needed
4. Review query patterns: Use `joinedload()` to avoid N+1 queries

#### Scraper Performance Issues

1. Adjust worker count: Increase `max_workers` if CPU allows
2. Review rate limiting: Ensure platform limits are respected
3. Check error logs: Review scraper error patterns
4. Optimize scraping order: Prioritize core accounts

---

## Best Practices

### Production Checklist

- [ ] Performance SLAs defined and monitored
- [ ] Cache hit rate > 80%
- [ ] API p95 response time < 500ms
- [ ] Database query p95 < 100ms
- [ ] Scraper success rate > 95%
- [ ] Alerts configured and tested
- [ ] Performance monitoring dashboard accessible
- [ ] Cache warming implemented
- [ ] Connection pooling optimized
- [ ] Query profiling enabled in development

### Regular Maintenance

1. **Weekly**: Review performance metrics and recommendations
2. **Monthly**: Analyze trends and optimize slow queries
3. **Quarterly**: Review and adjust SLAs based on actual performance
4. **As Needed**: Respond to alerts and performance issues

### Performance Testing

Run performance tests regularly:

```bash
# Load testing
locust -f locustfile.py --host=http://localhost:5000

# Performance benchmarks
pytest tests/performance/test_benchmarks.py
```

---

## Additional Resources

- [Cache Optimization Guide](./cache/optimization_guide.md)
- [Database Read Replicas](./database_read_replicas.md)
- [Database Partitioning](./database_partitioning.md)
- [CDN Integration](./cdn_integration.md)
- [Performance Optimization Guide](./PERFORMANCE_OPTIMIZATION_GUIDE.md)

---

## Support

For performance issues or questions:
1. Check `/api/performance/recommendations` for automated suggestions
2. Review alert history: `/api/performance/alerts`
3. Check logs for detailed error information
4. Review this guide for optimization strategies


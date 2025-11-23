# Performance Optimization Guide

## Overview

This comprehensive guide covers all performance optimizations implemented in the HHS Social Media Scraper application.

## Table of Contents

1. [Caching Strategy](#caching-strategy)
2. [Database Optimization](#database-optimization)
3. [API Performance](#api-performance)
4. [Frontend Optimization](#frontend-optimization)
5. [Scraper Performance](#scraper-performance)
6. [Monitoring & Profiling](#monitoring--profiling)
7. [Performance Testing](#performance-testing)

---

## Caching Strategy

### Multi-Level Caching

The application uses a two-level caching system:

- **L1 (Memory)**: Fast, in-process LRU cache
  - TTL: 60 seconds
  - Max Size: 1000 items
  - Use Case: Hot data, frequently accessed

- **L2 (Redis)**: Distributed cache
  - TTL: 300-900 seconds (endpoint-dependent)
  - Use Case: Shared across processes, larger datasets

### Cache Configuration

```python
from cache.multi_level import get_multi_cache

multi_cache = get_multi_cache()
value = multi_cache.get('key')
multi_cache.set('key', data, ttl=300)
```

### Cache Warming

Pre-populate cache with frequently accessed data:

```python
from cache.warming import get_warmer

warmer = get_warmer()
warmer.warm_summary(get_summary_func)
warmer.warm_top_accounts(accounts, get_history_func, limit=10)
```

### Cache Invalidation

Tag-based invalidation for related data:

```python
from cache.invalidation import (
    invalidate_by_tag,
    invalidate_on_snapshot_create
)

# Invalidate by tag
invalidate_by_tag('summary')

# Invalidate on data change
invalidate_on_snapshot_create(account_key, platform, handle)
```

### Cache Analytics

Monitor cache performance:

```python
from cache.analytics import get_analytics

analytics = get_analytics()
stats = analytics.get_all_stats()
recommendations = analytics.get_recommendations()
```

---

## Database Optimization

### Indexes

All frequently queried columns are indexed:

- `dim_account.platform`
- `dim_account.handle`
- `dim_account.platform, handle` (composite)
- `fact_followers_snapshot.account_key`
- `fact_followers_snapshot.snapshot_date`
- `fact_followers_snapshot.account_key, snapshot_date` (composite)

### Connection Pooling

Optimized connection pooling for production databases:

```python
# Environment variables
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
```

### Query Optimization

- Use `joinedload()` for eager loading
- Avoid N+1 queries
- Use `func.max()` for aggregations
- Limit result sets with pagination

### Query Profiling

Profile slow queries:

```python
from scraper.utils.query_profiler import get_profiler, setup_query_listening

# Set up profiling
engine = init_db(db_path, enable_profiling=True)

# Get statistics
profiler = get_profiler()
stats = profiler.get_all_stats()
recommendations = profiler.get_recommendations()
```

### Read Replicas

For production, configure read replicas:

```bash
DATABASE_URL=postgresql://...  # Primary (writes)
DATABASE_READ_REPLICA_URL=postgresql://...  # Replica (reads)
ENABLE_READ_REPLICA=true
```

See [database_read_replicas.md](./database_read_replicas.md) for setup.

### Partitioning

For large datasets, implement date-based partitioning:

See [database_partitioning.md](./database_partitioning.md) for strategies.

---

## API Performance

### Pagination

All list endpoints support pagination:

```python
GET /api/grid?page=1&per_page=50
GET /api/accounts?page=1&per_page=100
```

### Response Compression

Automatic compression via Flask-Compress:

- JSON responses compressed
- Large payloads optimized
- Reduces bandwidth usage

### Field Selection

Request only needed fields:

```python
GET /api/summary?fields=platform,handle,followers
```

### Request Batching

Batch multiple requests:

```python
POST /api/batch
{
  "requests": [
    {"method": "GET", "path": "/api/summary"},
    {"method": "GET", "path": "/api/history/x/hhsgov"}
  ]
}
```

### Response Streaming

For large datasets, use streaming:

```python
from api.streaming import stream_json_response

@app.route('/api/large-dataset')
def large_dataset():
    def generate():
        for item in query_results:
            yield item
    return stream_json_response(generate())
```

---

## Frontend Optimization

### Code Splitting

JavaScript is split into modules:

- `dashboard.js` - Main dashboard logic
- Chart.js loaded lazily
- Grid.js loaded on demand

### Lazy Loading

- Charts loaded only when needed
- Grid.js loaded when grid tab opened
- Assets loaded on demand

### Service Worker

Offline support and caching:

- Static assets cached
- API responses cached
- Offline fallback

### Asset Optimization

- CSS extracted to separate file
- JavaScript minified (in production)
- Assets versioned for cache busting

### CDN Integration

Configure CDN for static assets:

See [cdn_integration.md](./cdn_integration.md) for setup.

---

## Scraper Performance

### Parallel Scraping

Scrape multiple accounts concurrently:

```python
from scraper.collect_metrics import simulate_metrics

simulate_metrics(
    db_path='social_media.db',
    mode='simulated',
    parallel=True,
    max_workers=5
)
```

### Rate Limiting

Per-platform rate limiting prevents API throttling:

- Minimum 0.5s between requests per platform
- Thread-safe implementation
- Configurable intervals

### Queue Prioritization

- Core accounts processed first
- Failed accounts retried
- User-requested accounts prioritized

---

## Monitoring & Profiling

### Performance Metrics

Access performance metrics:

```bash
GET /api/performance
```

Returns:
- API response times
- Cache hit rates
- Database query times
- Scraper execution metrics

### Query Profiling

Enable query profiling:

```python
engine = init_db(db_path, enable_profiling=True)
```

### Performance Profiling Tools

Use profiling tools:

```python
from tools.profiler import profile_function, time_function

@time_function
def my_function():
    # Function code
    pass

# Profile with cProfile
profile_function(my_function)
```

---

## Performance Testing

### Benchmarking

Run performance benchmarks:

```bash
pytest tests/performance/test_benchmarks.py -v
```

### Load Testing

Test under load:

```bash
pytest tests/performance/test_load.py -v
```

### Regression Testing

Check for performance regressions:

```bash
pytest tests/performance/test_regression.py -v
```

---

## Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| API Response (cached) | < 200ms | ✅ |
| API Response (uncached) | < 1s | ✅ |
| Database Query | < 100ms | ✅ |
| Cache Hit Rate | > 80% | ✅ |
| Scraper (per account) | < 30s | ✅ |
| Frontend Load | < 2s | ✅ |

---

## Best Practices

### 1. Caching
- Cache frequently accessed data
- Use appropriate TTLs
- Invalidate on writes
- Monitor hit rates

### 2. Database
- Use indexes on frequently queried columns
- Avoid N+1 queries
- Use pagination for large datasets
- Profile slow queries

### 3. API
- Implement pagination
- Use field selection
- Enable compression
- Stream large responses

### 4. Frontend
- Lazy load assets
- Use code splitting
- Implement service worker
- Optimize bundle sizes

### 5. Monitoring
- Track key metrics
- Set up alerts
- Profile regularly
- Test for regressions

---

## Troubleshooting

### Slow API Responses

1. Check cache hit rate
2. Profile database queries
3. Review query execution plans
4. Check connection pool usage

### High Memory Usage

1. Review cache sizes
2. Check for memory leaks
3. Profile memory usage
4. Optimize data structures

### Database Performance

1. Review query profiles
2. Check index usage
3. Analyze slow queries
4. Consider partitioning

---

## Tools & Utilities

### Cache Tools
- `cache/multi_level.py` - Multi-level cache
- `cache/warming.py` - Cache warming
- `cache/analytics.py` - Cache analytics
- `cache/invalidation.py` - Cache invalidation

### Database Tools
- `scraper/utils/query_profiler.py` - Query profiling
- `scripts/add_indexes.py` - Index creation

### API Tools
- `api/batching.py` - Request batching
- `api/field_selection.py` - Field selection
- `api/streaming.py` - Response streaming

### Testing Tools
- `tests/performance/` - Performance tests
- `tools/profiler.py` - Profiling tools

---

## Further Reading

- [Cache Optimization Guide](../cache/optimization_guide.md)
- [Database Read Replicas](./database_read_replicas.md)
- [Database Partitioning](./database_partitioning.md)
- [CDN Integration](./cdn_integration.md)

---

**Last Updated**: Phase 2 Completion
**Version**: 2.0


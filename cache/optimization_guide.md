# Cache Optimization Guide

## Overview

This guide provides recommendations for optimizing cache performance based on analytics and best practices.

## Cache Architecture

### Multi-Level Caching
- **L1 (Memory)**: Fast, in-process cache with LRU eviction
- **L2 (Redis)**: Distributed cache shared across processes

### Cache Levels
1. **L1 Cache**: 60s TTL, 1000 items max
2. **L2 Cache**: 300s TTL, unlimited (Redis memory)

## Optimization Strategies

### 1. Cache Key Design

**Best Practices:**
- Use consistent naming: `{type}:{identifier}`
- Include version in key if data structure changes
- Keep keys short but descriptive

**Examples:**
```
summary:latest
history:x:hhsgov
account:12345
grid:page:1
```

### 2. TTL Configuration

**Recommended TTLs:**
- **Summary data**: 5 minutes (300s)
- **History data**: 10 minutes (600s)
- **Grid data**: 5 minutes (300s)
- **Account list**: 15 minutes (900s)
- **L1 cache**: 60 seconds (for hot data)

**Factors to Consider:**
- Data update frequency
- User access patterns
- Data freshness requirements

### 3. Cache Warming

**When to Warm:**
- Application startup
- After scheduled data updates
- Before peak usage periods

**What to Warm:**
- Top 10 most accessed accounts
- Summary data
- First 3 pages of grid data

**Example:**
```python
from cache.warming import get_warmer

warmer = get_warmer()
warmer.warm_summary(get_summary_func)
warmer.warm_top_accounts(accounts, get_history_func, limit=10)
```

### 4. Cache Invalidation

**Strategies:**
- **Time-based**: Let TTL expire naturally
- **Event-based**: Invalidate on data changes
- **Tag-based**: Invalidate related entries

**Best Practices:**
- Invalidate immediately on writes
- Use tags for related data
- Batch invalidations when possible

**Example:**
```python
from cache.invalidation import invalidate_on_snapshot_create

# When new snapshot created
invalidate_on_snapshot_create(account_key, platform, handle)
```

### 5. Hit Rate Optimization

**Target Hit Rates:**
- Overall: > 80%
- Summary: > 90%
- History: > 70%
- Grid: > 60%

**Improving Hit Rate:**
1. Increase TTL for stable data
2. Implement cache warming
3. Optimize cache key patterns
4. Review invalidation strategies

### 6. Memory Management

**L1 Cache:**
- Monitor size vs maxsize
- Adjust maxsize based on memory available
- Review TTL to balance freshness vs hit rate

**L2 Cache (Redis):**
- Monitor Redis memory usage
- Set maxmemory policy (allkeys-lru recommended)
- Use Redis eviction policies

### 7. Performance Monitoring

**Key Metrics:**
- Hit rate by pattern
- Operation timings (avg, p95, p99)
- Cache size trends
- Memory usage

**Monitoring:**
```python
from cache.analytics import get_analytics

analytics = get_analytics()
stats = analytics.get_all_stats()
recommendations = analytics.get_recommendations()
```

## Common Issues & Solutions

### Issue: Low Hit Rate
**Symptoms:** Hit rate < 50%
**Solutions:**
- Increase TTL for stable data
- Implement cache warming
- Review invalidation frequency
- Optimize cache key patterns

### Issue: High Memory Usage
**Symptoms:** Cache size near maxsize
**Solutions:**
- Increase maxsize if memory available
- Reduce TTL for less critical data
- Implement more aggressive eviction
- Review cache key patterns (remove duplicates)

### Issue: Slow Cache Operations
**Symptoms:** Avg operation time > 10ms
**Solutions:**
- Check Redis connection health
- Optimize serialization
- Review network latency
- Consider L1 cache for hot data

### Issue: Stale Data
**Symptoms:** Users see outdated information
**Solutions:**
- Reduce TTL
- Improve invalidation on writes
- Use event-based invalidation
- Implement cache versioning

## Performance Targets

| Metric | Target | Warning | Critical |
|--------|--------|---------|----------|
| Overall Hit Rate | > 80% | 50-80% | < 50% |
| L1 Hit Rate | > 60% | 40-60% | < 40% |
| Operation Time (L1) | < 1ms | 1-5ms | > 5ms |
| Operation Time (L2) | < 5ms | 5-20ms | > 20ms |
| L1 Size Usage | < 80% | 80-95% | > 95% |

## Best Practices Summary

1. **Design cache keys carefully** - Consistent, descriptive, versioned
2. **Set appropriate TTLs** - Balance freshness vs hit rate
3. **Warm frequently accessed data** - Improve initial hit rate
4. **Invalidate on writes** - Ensure data consistency
5. **Monitor performance** - Track metrics and adjust
6. **Use multi-level caching** - L1 for hot, L2 for distributed
7. **Optimize based on patterns** - Different strategies for different data types

## Tools & Utilities

### Cache Analytics
```python
from cache.analytics import get_analytics
analytics = get_analytics()
stats = analytics.get_all_stats()
```

### Cache Warming
```python
from cache.warming import get_warmer
warmer = get_warmer()
warmer.warm_all(warm_functions)
```

### Cache Invalidation
```python
from cache.invalidation import (
    invalidate_by_tag,
    invalidate_on_snapshot_create,
    invalidate_platform_cache
)
```

## Further Reading

- Redis Best Practices: https://redis.io/docs/manual/patterns/
- Caching Strategies: https://en.wikipedia.org/wiki/Cache_(computing)
- Multi-Level Caching: https://en.wikipedia.org/wiki/Multi-level_cache


# Agent 8: PERFORMANCE_SPECIALIST (Harper)
## Production Enhancement: Performance & Optimization

### 🎯 Mission
Optimize application performance through caching, database optimization, API improvements, and frontend enhancements to ensure fast response times and scalability.

---

## 📋 Detailed Tasks

### 1. Caching Strategy

#### 1.1 Redis Caching Setup
- **Package:** `redis` and `flask-caching`
- **File:** `cache/redis_client.py`
- Configure:
  - Redis connection
  - Cache configuration
  - Cache key naming conventions
  - TTL (Time To Live) settings

#### 1.2 API Response Caching
- **File:** `app.py` (add caching decorators)
- Cache:
  - `/api/summary` - 5 minutes
  - `/api/history/<platform>/<handle>` - 10 minutes
  - `/api/grid` - 5 minutes
  - Account list - 15 minutes

#### 1.3 Cache Invalidation
- **File:** `cache/invalidation.py`
- Invalidate cache on:
  - New snapshot created
  - Account updated
  - Scraper completes
  - Manual cache clear

#### 1.4 Cache Keys
- Use consistent key format:
  - `summary:latest`
  - `history:{platform}:{handle}`
  - `account:{account_key}`
  - `grid:all`

---

### 2. Database Optimization

#### 2.1 Database Indexes
- **File:** `alembic/versions/002_add_indexes.py`
- Add indexes on:
  - `dim_account.platform`
  - `dim_account.handle`
  - `fact_followers_snapshot.account_key`
  - `fact_followers_snapshot.snapshot_date`
  - `fact_followers_snapshot.account_key, snapshot_date` (composite)

#### 2.2 Query Optimization
- **File:** `app.py` (optimize queries)
- Optimize:
  - Use `joinedload` for eager loading
  - Avoid N+1 queries
  - Use select_related for joins
  - Add query result caching

#### 2.3 Connection Pooling
- **File:** `scraper/schema.py` (modify init_db)
- Configure:
  - Connection pool size
  - Max overflow
  - Pool timeout
  - Connection recycling

#### 2.4 Database Query Analysis
- Add query logging in development
- Identify slow queries
- Optimize based on analysis

---

### 3. API Performance

#### 3.1 Pagination
- **File:** `app.py` (modify endpoints)
- Add pagination to:
  - `/api/grid` - Paginate results
  - `/api/summary` - Optional pagination
  - Account list endpoints

#### 3.2 Response Compression
- **Package:** `flask-compress`
- **File:** `app.py`
- Compress responses:
  - JSON responses
  - Large payloads
  - Static files

#### 3.3 Lazy Loading
- Implement lazy loading for:
  - Large datasets
  - Related data
  - Optional fields

#### 3.4 JSON Serialization Optimization
- Use efficient JSON serialization
- Optimize date formatting
- Minimize response payload size

---

### 4. Frontend Optimization

#### 4.1 Dashboard Performance
- **File:** `templates/dashboard.html`
- Optimize:
  - Lazy load charts
  - Virtual scrolling for account list
  - Debounce search inputs
  - Cache API responses in frontend

#### 4.2 Data Pagination
- Add pagination to:
  - Account sidebar list
  - Data grid
  - Chart data loading

#### 4.3 Loading States
- Add:
  - Skeleton loaders
  - Loading spinners
  - Progress indicators
  - Optimistic UI updates

#### 4.4 Code Splitting (Optional)
- Split JavaScript if using build tools
- Lazy load chart libraries
- Minimize initial bundle size

---

### 5. Scraper Performance

#### 5.1 Parallel Scraping
- **File:** `scraper/utils/parallel.py`
- Implement:
  - Async/await for I/O operations
  - Thread pool for CPU-bound tasks
  - Concurrent scraping of multiple accounts
  - Rate limit per platform

#### 5.2 Scraping Queue Prioritization
- Prioritize:
  - Core accounts first
  - Recently active accounts
  - Failed accounts (retry)
  - User-requested accounts

#### 5.3 Performance Metrics
- Track:
  - Scraping time per account
  - Success/failure rates
  - Average response time
  - Queue processing time

---

## 📁 File Structure to Create

```
cache/
├── __init__.py
├── redis_client.py
└── invalidation.py

scraper/
└── utils/
    └── parallel.py
```

---

## 🔧 Dependencies to Add

Add to `requirements.txt`:
```
flask-caching>=2.1.0
flask-compress>=1.13
redis>=5.0.0
```

---

## ✅ Acceptance Criteria

- [ ] Redis caching is implemented
- [ ] API responses are cached appropriately
- [ ] Database indexes are added
- [ ] Queries are optimized
- [ ] Pagination is implemented
- [ ] Frontend is optimized
- [ ] Scraper performance is improved
- [ ] Performance metrics are tracked

---

## 🧪 Testing Requirements

- Test cache hit/miss rates
- Test query performance
- Test pagination
- Test parallel scraping
- Load testing (optional)
- Performance benchmarking

---

## 📝 Implementation Details

### Redis Caching Example:
```python
from flask_caching import Cache

cache = Cache(config={
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_URL': os.getenv('REDIS_URL')
})

@app.route('/api/summary')
@cache.cached(timeout=300)  # 5 minutes
def api_summary():
    # ... existing code
```

### Database Index Example:
```python
# In Alembic migration
def upgrade():
    op.create_index('ix_fact_snapshot_account_date', 
                   'fact_followers_snapshot', 
                   ['account_key', 'snapshot_date'])
```

### Pagination Example:
```python
from flask import request

@app.route('/api/grid')
def api_grid():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    query = session.query(...)
    paginated = query.paginate(page=page, per_page=per_page)
    
    return jsonify({
        'data': paginated.items,
        'total': paginated.total,
        'page': page,
        'per_page': per_page,
        'pages': paginated.pages
    })
```

### Parallel Scraping Example:
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def scrape_accounts_parallel(accounts):
    with ThreadPoolExecutor(max_workers=5) as executor:
        tasks = [executor.submit(scrape_account, acc) for acc in accounts]
        results = await asyncio.gather(*tasks)
    return results
```

---

## 🚀 Getting Started

1. Create branch: `git checkout -b feature/agent-8-performance`
2. Install dependencies: `pip install -r requirements.txt`
3. Set up Redis caching
4. Add caching to API endpoints
5. Create database migration for indexes
6. Optimize database queries
7. Add pagination to endpoints
8. Optimize frontend
9. Implement parallel scraping
10. Test performance improvements

---

## 📊 Performance Targets

- API response time: < 200ms (cached), < 1s (uncached)
- Database queries: < 100ms
- Scraper execution: < 30s per account
- Frontend load time: < 2s
- Cache hit rate: > 80%

---

## 🔍 Performance Monitoring

- Track:
  - API response times
  - Cache hit/miss rates
  - Database query times
  - Scraper execution times
  - Frontend load times
  - Error rates

---

## ⚠️ Important Considerations

- **Cache Invalidation:** Ensure cache is invalidated when data changes
- **Memory Usage:** Monitor Redis memory usage
- **Database Size:** Monitor database growth
- **Rate Limits:** Respect platform rate limits when parallelizing
- **Resource Limits:** Set appropriate limits for workers/threads
- **Monitoring:** Track performance metrics continuously

---

## 🎯 Optimization Checklist

- [ ] Redis caching implemented
- [ ] Cache invalidation working
- [ ] Database indexes added
- [ ] Queries optimized
- [ ] Pagination added
- [ ] Response compression enabled
- [ ] Frontend optimized
- [ ] Parallel scraping implemented
- [ ] Performance metrics tracked
- [ ] Load testing completed

---

**Agent Harper - Ready to optimize! ⚡**


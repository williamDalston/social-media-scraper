# Frontend Performance Optimization Guide

## Overview

This guide covers frontend performance optimization strategies for the HHS Social Media Scraper dashboard.

---

## Performance Targets

- **Page Load Time**: < 2 seconds (p95)
- **Time to Interactive**: < 3 seconds
- **First Contentful Paint**: < 1.5 seconds
- **API Response Time**: < 500ms (cached)

---

## Optimization Strategies

### 1. Code Splitting

JavaScript is split into modules for lazy loading:

```javascript
// Dashboard loads on demand
import { Chart } from 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js';
```

### 2. Lazy Loading

Charts and heavy components load on demand:

```javascript
// Lazy load charts after a delay
chartLoadTimeout = setTimeout(() => {
    updateCharts(handle, data);
}, 50);
```

### 3. Caching

API responses are cached in the browser:

```javascript
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes
const apiCache = new Map();
```

### 4. Debouncing

Input handlers are debounced to reduce API calls:

```javascript
const debouncedLoadHistory = debounce(loadHistory, 300);
```

### 5. Service Worker

Offline support and asset caching:

```javascript
// Service worker caches static assets
self.addEventListener('fetch', (event) => {
    event.respondWith(
        caches.match(event.request)
            .then(response => response || fetch(event.request))
    );
});
```

---

## CDN Integration

### Configuration

Set CDN base URL in environment:

```bash
CDN_BASE_URL=https://cdn.example.com
```

### Implementation

Static assets are served via CDN in production:

```html
<link href="https://cdn.example.com/static/css/dashboard.css" rel="stylesheet" />
```

See `docs/cdn_integration.md` for detailed setup.

---

## Performance Monitoring

### Frontend Metrics

The dashboard includes performance monitoring:

```javascript
// Monitor page load
window.frontendPerformanceMonitor.recordPageLoad();

// Get stats
const stats = window.frontendPerformanceMonitor.getStats();
```

### Metrics Tracked

- Page load time
- API call durations
- Render performance
- Error tracking

### Accessing Metrics

```bash
# Get frontend performance stats
curl -H "Authorization: Bearer <token>" \
  http://localhost:5000/api/performance/frontend
```

---

## Best Practices

1. **Minimize Bundle Size**: Use code splitting and tree shaking
2. **Optimize Images**: Use appropriate formats and sizes
3. **Reduce HTTP Requests**: Combine CSS/JS files
4. **Use CDN**: Serve static assets from CDN
5. **Enable Compression**: Use gzip/brotli compression
6. **Cache Strategically**: Cache static assets and API responses
7. **Monitor Performance**: Track metrics and optimize bottlenecks

---

## Troubleshooting

### Slow Page Load

1. Check network tab for slow resources
2. Verify CDN is configured correctly
3. Review bundle sizes
4. Check cache hit rates

### Slow API Calls

1. Verify caching is working
2. Check backend performance
3. Review network latency
4. Consider API batching

### High Error Rate

1. Check browser console for errors
2. Review error tracking
3. Verify API endpoints
4. Check CORS configuration

---

## Additional Resources

- [Production Performance Guide](./PRODUCTION_PERFORMANCE_GUIDE.md)
- [CDN Integration](./cdn_integration.md)
- [Performance Optimization Guide](./PERFORMANCE_OPTIMIZATION_GUIDE.md)


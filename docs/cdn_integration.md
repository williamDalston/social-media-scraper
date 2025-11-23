# CDN Integration Guide

## Overview

This guide describes how to integrate a Content Delivery Network (CDN) for static assets and API responses.

## CDN Benefits

- **Faster Load Times**: Assets served from edge locations closer to users
- **Reduced Server Load**: Offload static asset serving
- **Better Scalability**: Handle traffic spikes
- **Global Distribution**: Improved performance worldwide

## Supported CDNs

### Cloudflare
- Free tier available
- Easy integration
- Automatic HTTPS
- DDoS protection

### AWS CloudFront
- Integrated with AWS services
- Pay-as-you-go pricing
- Advanced caching rules

### Fastly
- High performance
- Real-time purging
- Advanced edge computing

## Configuration

### Environment Variables

```bash
# CDN Configuration
CDN_ENABLED=true
CDN_URL=https://cdn.example.com
CDN_STATIC_PREFIX=/static
CDN_CACHE_TTL=31536000  # 1 year for static assets
```

### Static Assets

Configure CDN to cache:
- `/static/css/*` - CSS files
- `/static/js/*` - JavaScript files
- `/static/images/*` - Images (if any)

### Cache Headers

The application sets appropriate cache headers:

```python
from flask import send_from_directory

@app.route('/static/<path:filename>')
def static_files(filename):
    response = send_from_directory('static', filename)
    response.headers['Cache-Control'] = 'public, max-age=31536000'  # 1 year
    response.headers['CDN-Cache-Control'] = 'public, max-age=31536000'
    return response
```

## Implementation

### 1. Update Static Asset URLs

In templates, use CDN URL when available:

```html
<link rel="stylesheet" href="{{ cdn_url }}/static/css/dashboard.css">
<script src="{{ cdn_url }}/static/js/dashboard.js"></script>
```

### 2. Cache Invalidation

When assets change, purge CDN cache:

```python
def purge_cdn_cache(paths: List[str]):
    """Purge CDN cache for specified paths."""
    if not os.getenv('CDN_ENABLED'):
        return
    
    # Implementation depends on CDN provider
    # Example for Cloudflare:
    # cloudflare_api.purge_cache(paths)
    pass
```

### 3. Asset Versioning

Use versioned filenames for cache busting:

```html
<link rel="stylesheet" href="/static/css/dashboard.v1.2.3.css">
```

Or use query parameters:

```html
<link rel="stylesheet" href="/static/css/dashboard.css?v=1.2.3">
```

## CDN Setup Examples

### Cloudflare

1. Add your domain to Cloudflare
2. Update DNS records
3. Enable caching
4. Configure cache rules

### AWS CloudFront

1. Create CloudFront distribution
2. Set origin to your application
3. Configure behaviors
4. Set up SSL certificate

### Fastly

1. Create service
2. Configure backend
3. Set up VCL (Varnish Configuration Language)
4. Deploy

## Cache Strategies

### Static Assets
- **TTL**: 1 year (31536000 seconds)
- **Strategy**: Cache forever, use versioning for updates

### API Responses
- **TTL**: 5-15 minutes (depending on endpoint)
- **Strategy**: Cache with invalidation on updates

### HTML Pages
- **TTL**: 0 (no cache) or very short (5 minutes)
- **Strategy**: Always fresh content

## Monitoring

Track CDN performance:
- Cache hit rate
- Response times
- Bandwidth usage
- Error rates

## Best Practices

1. **Version Assets**: Use versioned filenames for cache busting
2. **Compress Assets**: Enable gzip/brotli compression
3. **Set Headers**: Proper cache-control headers
4. **Monitor Performance**: Track CDN metrics
5. **Purge Strategically**: Only purge when necessary

## Testing

Test CDN integration:
1. Verify assets load from CDN
2. Check cache headers
3. Test cache invalidation
4. Monitor performance improvements


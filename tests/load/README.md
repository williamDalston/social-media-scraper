# Load Testing Suite

This directory contains load testing scripts using Locust.

## Running Load Tests

### Basic Usage

```bash
# Install locust
pip install locust

# Run load tests
locust -f tests/load/locustfile.py --host=http://localhost:5000
```

### With Custom Parameters

```bash
# Run with specific number of users and spawn rate
locust -f tests/load/locustfile.py \
    --host=http://localhost:5000 \
    --users=100 \
    --spawn-rate=10 \
    --run-time=5m
```

### Headless Mode (CI/CD)

```bash
locust -f tests/load/locustfile.py \
    --host=http://localhost:5000 \
    --users=50 \
    --spawn-rate=5 \
    --run-time=2m \
    --headless \
    --html=load_test_report.html
```

## Test Scenarios

1. **SocialMediaScraperUser**: Authenticated users performing common operations
2. **AnonymousUser**: Unauthenticated users attempting access

## Performance Targets

- API response time: < 200ms (p95)
- Error rate: < 1%
- Throughput: > 100 requests/second

## Monitoring

During load tests, monitor:
- Response times (p50, p95, p99)
- Error rates
- Throughput (requests/second)
- Server resource usage (CPU, memory)


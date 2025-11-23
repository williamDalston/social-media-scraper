# Phase 2 Testing Enhancements

## Overview

Phase 2 introduces advanced testing capabilities including property-based testing, chaos engineering, security testing, performance testing, and quality metrics tracking.

## New Test Categories

### Property-Based Testing (`tests/property/`)
Uses Hypothesis library to generate random inputs and verify properties hold true.

**Run:**
```bash
pytest tests/property/ -v
```

**Key Features:**
- Random input generation
- Edge case discovery
- Property verification
- Configurable test examples

### Contract Testing (`tests/contract/`)
Verifies API endpoints maintain their contracts (request/response formats).

**Run:**
```bash
pytest tests/contract/ -v
```

**Key Features:**
- API structure validation
- Response format verification
- Error response testing
- Version compatibility checks

### Chaos Engineering (`tests/chaos/`)
Injects failures to verify system resilience.

**Run:**
```bash
pytest tests/chaos/ -v
```

**Key Features:**
- Database failure simulation
- Network failure injection
- Memory pressure tests
- Concurrent operation tests
- Data corruption scenarios

### Performance Testing (`tests/performance/`)
Tests system performance under load.

**Run:**
```bash
pytest tests/performance/ -v
pytest tests/performance/ -m benchmark  # Benchmark tests
```

**Key Features:**
- API endpoint performance
- Database operation benchmarks
- Scraper performance tests
- Load testing with Locust

### Security Testing (`tests/security/`)
OWASP Top 10 and security best practices.

**Run:**
```bash
pytest tests/security/ -v
```

**Key Features:**
- OWASP Top 10 coverage
- Injection attack tests
- XSS protection
- CSRF protection
- Input validation

### End-to-End Browser Tests (`tests/e2e/`)
Playwright-based browser automation tests.

**Run:**
```bash
pytest tests/e2e/ -v
```

**Key Features:**
- Real browser testing
- User interaction simulation
- Page navigation tests
- Visual verification

## Test Utilities

### Test Data Factories (`tests/factories.py`)
Factory Boy integration for creating test data.

**Usage:**
```python
from tests.factories import DimAccountFactory, FactFollowersSnapshotFactory

account = DimAccountFactory()
snapshot = FactFollowersSnapshotFactory(account=account)
```

### Database Seeding (`tests/fixtures/db_seed.py`)
Utilities for seeding test databases.

**Usage:**
```python
from tests.fixtures.db_seed import seed_basic_data, seed_large_dataset

accounts = seed_basic_data(session, num_accounts=10, days_of_history=30)
```

## Load Testing

### Locust Configuration
Load testing with Locust.

**Run:**
```bash
locust -f locustfile.py
# Access web UI at http://localhost:8089
```

**Features:**
- Simulated user behavior
- Configurable load patterns
- Real-time metrics
- Distributed load testing

## Security Scanning

### Automated Security Scanning
- **Bandit**: Python security linter
- **Safety**: Dependency vulnerability scanner

**Run:**
```bash
bandit -r scraper/ app.py
safety check
```

**CI Integration:**
- Weekly automated scans
- PR security checks
- Report artifacts

## Quality Metrics

### Quality Report Generator
Automated quality metrics collection.

**Run:**
```bash
python scripts/generate_quality_report.py
```

**Metrics Tracked:**
- Test coverage percentage
- Test count
- Dependency vulnerabilities
- Security issues
- Overall quality status

## CI/CD Integration

### New Workflows
1. **Security Scanning** (`.github/workflows/security-scan.yml`)
   - Weekly security scans
   - PR security checks
   - Bandit + Safety integration

2. **Quality Metrics** (`.github/workflows/quality-metrics.yml`)
   - Weekly quality reports
   - Manual trigger support
   - Trend tracking

## Running All Phase 2 Tests

```bash
# All Phase 2 tests
pytest tests/property/ tests/contract/ tests/chaos/ tests/performance/ tests/security/ tests/e2e/ -v

# With parallel execution
pytest -n auto tests/

# With coverage
pytest --cov=scraper --cov=app --cov-report=html tests/
```

## Test Markers

- `@pytest.mark.slow` - Slow-running tests
- `@pytest.mark.e2e` - End-to-end browser tests
- `@pytest.mark.benchmark` - Performance benchmark tests
- `@pytest.mark.requires_auth` - Tests requiring authentication

**Run by marker:**
```bash
pytest -m "not slow"  # Skip slow tests
pytest -m e2e         # Only E2E tests
pytest -m benchmark   # Only benchmarks
```

## Best Practices

1. **Property-Based Tests**: Use for finding edge cases automatically
2. **Contract Tests**: Run before API changes to detect breaking changes
3. **Chaos Tests**: Verify system resilience under failure conditions
4. **Performance Tests**: Establish baselines and detect regressions
5. **Security Tests**: Run regularly to catch vulnerabilities early
6. **E2E Tests**: Use for critical user flows

## Documentation

- See `TESTING.md` for general testing guide
- See `tests/README.md` for Phase 1 test documentation
- See `AGENT_2_PHASE_2_SUMMARY.md` for complete Phase 2 summary


# Testing Guide

This document provides comprehensive information about testing in the HHS Social Media Scraper project.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=scraper --cov=app --cov-report=html

# View coverage report
open htmlcov/index.html
```

## Test Structure

### Unit Tests (`tests/unit/`)
- **test_scrapers.py**: Tests for scraper classes and factory functions
- **test_schema.py**: Tests for database models and relationships
- **test_extract_accounts.py**: Tests for account extraction utilities
- **test_collect_metrics.py**: Tests for metrics collection
- **test_backfill.py**: Tests for historical data backfilling
- **test_main.py**: Tests for CLI interface

### Integration Tests (`tests/integration/`)
- **test_api.py**: Tests for all API endpoints
- **test_database.py**: Tests for database operations and queries
- **test_scraper_flow.py**: End-to-end scraper execution tests
- **test_upload.py**: CSV file upload functionality tests
- **test_auth.py**: Authentication tests (if auth is available)

## Test Fixtures

### Database Fixtures
- `test_db_path`: Temporary database file path (session-scoped)
- `db_engine`: SQLAlchemy engine (function-scoped)
- `db_session`: Database session with auto-cleanup (function-scoped)

### Application Fixtures
- `app`: Flask test application
- `client`: Flask test client for making requests

### Data Fixtures
- `sample_account`: Pre-created DimAccount instance
- `sample_snapshot`: Pre-created FactFollowersSnapshot instance
- `multiple_accounts`: Multiple test accounts for bulk operations

## Writing Tests

### Example: Unit Test
```python
def test_scraper_returns_data(db_session, sample_account):
    """Test that scraper returns valid data."""
    from scraper.scrapers import SimulatedScraper
    
    scraper = SimulatedScraper()
    result = scraper.scrape(sample_account)
    
    assert result is not None
    assert 'followers_count' in result
    assert result['followers_count'] > 0
```

### Example: Integration Test
```python
def test_api_summary_endpoint(client, db_session, sample_account):
    """Test API summary endpoint."""
    from scraper.schema import FactFollowersSnapshot
    from datetime import date
    
    # Create snapshot
    snapshot = FactFollowersSnapshot(
        account_key=sample_account.account_key,
        snapshot_date=date.today(),
        followers_count=1000
    )
    db_session.add(snapshot)
    db_session.commit()
    
    # Test endpoint
    response = client.get('/api/summary')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) > 0
```

## Test Utilities

Use helper functions from `tests/utils.py`:

```python
from tests.utils import create_test_account, create_test_snapshot

def test_my_function(db_session):
    account = create_test_account(
        db_session,
        platform='X',
        handle='test',
        org_name='HHS'
    )
    # ... test code
```

## Running Specific Tests

```bash
# Run specific test file
pytest tests/unit/test_scrapers.py

# Run specific test class
pytest tests/unit/test_scrapers.py::TestSimulatedScraper

# Run specific test
pytest tests/unit/test_scrapers.py::TestSimulatedScraper::test_simulated_scraper_returns_data

# Run by marker
pytest -m unit
pytest -m integration
pytest -m "not slow"

# Run only failed tests
pytest --lf

# Run with verbose output
pytest -v

# Run with print statements visible
pytest -s
```

## Coverage

### View Coverage Report
```bash
pytest --cov=scraper --cov=app --cov-report=html
open htmlcov/index.html
```

### Coverage Goals
- Overall: 80%+
- Core modules: 85%+
- Schema: 90%+

### Excluding Code from Coverage
Add `# pragma: no cover` to lines you want to exclude:
```python
def debug_function():  # pragma: no cover
    print("Debug info")
```

## CI/CD

Tests automatically run on:
- Push to `main` or `develop` branches
- Pull requests
- Multiple Python versions (3.9, 3.10, 3.11)

See `.github/workflows/tests.yml` for configuration.

## Pre-commit Hooks

Pre-commit hooks ensure code quality before commits:
- Code formatting (black)
- Import sorting (isort)
- Linting (flake8)
- Running tests

Install:
```bash
pip install pre-commit
pre-commit install
```

## Debugging Tests

### Run with PDB
```bash
pytest --pdb
```

### Print statements
```bash
pytest -s
```

### Verbose output
```bash
pytest -vv
```

### Show local variables on failure
```bash
pytest -l
```

## Common Issues

### Database Locked
- Tests use temporary databases that are cleaned up automatically
- If you see lock errors, ensure previous test runs completed

### Import Errors
- Run tests from project root: `pytest` (not `python -m pytest tests/`)
- Ensure all dependencies are installed: `pip install -r requirements.txt`

### Fixture Errors
- Check fixture scope matches test needs
- Ensure fixtures are properly imported in `conftest.py`

### Coverage Issues
- Some files may have low coverage due to optional dependencies
- Focus on testing core functionality first

## Best Practices

1. **Test Independence**: Each test should work in isolation
2. **Clear Names**: Use descriptive test names that explain what's being tested
3. **AAA Pattern**: Arrange, Act, Assert
4. **One Assertion**: Focus each test on one behavior
5. **Mock External Dependencies**: Don't make real API calls in tests
6. **Test Edge Cases**: Test error conditions and boundary cases
7. **Keep Tests Fast**: Use mocks and fixtures to avoid slow operations

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)


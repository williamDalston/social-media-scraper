# Test Suite Documentation

This directory contains the comprehensive test suite for the HHS Social Media Scraper project.

## Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared pytest fixtures
├── utils.py                 # Test utilities and helpers
├── unit/                    # Unit tests
│   ├── test_scrapers.py
│   ├── test_schema.py
│   ├── test_extract_accounts.py
│   ├── test_collect_metrics.py
│   └── test_backfill.py
└── integration/            # Integration tests
    ├── test_api.py
    ├── test_database.py
    ├── test_scraper_flow.py
    └── test_upload.py
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run with coverage
```bash
pytest --cov=scraper --cov=app --cov-report=html
```

### Run specific test file
```bash
pytest tests/unit/test_scrapers.py
```

### Run specific test
```bash
pytest tests/unit/test_scrapers.py::TestSimulatedScraper::test_simulated_scraper_returns_data
```

### Run with verbose output
```bash
pytest -v
```

### Run only failed tests
```bash
pytest --lf
```

## Test Categories

Tests are marked with pytest markers:
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.api` - API endpoint tests
- `@pytest.mark.slow` - Slow-running tests

Run specific categories:
```bash
pytest -m unit
pytest -m integration
pytest -m "not slow"  # Skip slow tests
```

## Fixtures

### Database Fixtures
- `test_db_path` - Temporary database file path
- `db_engine` - SQLAlchemy engine for test database
- `db_session` - Database session (auto-cleaned)

### Application Fixtures
- `app` - Flask test application
- `client` - Flask test client

### Data Fixtures
- `sample_account` - Sample DimAccount instance
- `sample_snapshot` - Sample FactFollowersSnapshot instance
- `multiple_accounts` - Multiple test accounts

## Test Utilities

The `tests/utils.py` module provides helper functions:
- `temp_database()` - Context manager for temporary databases
- `create_test_account()` - Helper to create test accounts
- `create_test_snapshot()` - Helper to create test snapshots
- `clear_database()` - Clear all database tables

## Coverage Goals

- Overall: 80%+
- `scraper/` module: 85%+
- `app.py`: 80%+
- `schema.py`: 90%+

## CI/CD

Tests run automatically on:
- Push to main/develop branches
- Pull requests
- Python 3.9, 3.10, 3.11

Coverage reports are generated and can be uploaded to Codecov.

## Pre-commit Hooks

Pre-commit hooks run:
- Code formatting (black)
- Import sorting (isort)
- Linting (flake8)
- Tests (pytest)

Install hooks:
```bash
pre-commit install
```

## Writing New Tests

### Unit Test Example
```python
def test_my_function(db_session):
    """Test description."""
    # Arrange
    account = create_test_account(db_session, platform='X', handle='test')
    
    # Act
    result = my_function(account)
    
    # Assert
    assert result is not None
    assert result['status'] == 'success'
```

### Integration Test Example
```python
def test_api_endpoint(client, db_session, sample_account):
    """Test API endpoint."""
    response = client.get('/api/summary')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) > 0
```

## Best Practices

1. **Isolation**: Each test should be independent
2. **Cleanup**: Use fixtures for automatic cleanup
3. **Naming**: Use descriptive test names
4. **AAA Pattern**: Arrange, Act, Assert
5. **Edge Cases**: Test error conditions and edge cases
6. **Mocking**: Mock external dependencies (APIs, file system)

## Troubleshooting

### Database Issues
- Tests use temporary databases that are cleaned up automatically
- If you see database errors, check that fixtures are properly scoped

### Import Errors
- Ensure you're running tests from the project root
- Check that all dependencies are installed: `pip install -r requirements.txt`

### Coverage Issues
- Some files may have low coverage due to optional dependencies
- Focus on testing core functionality first


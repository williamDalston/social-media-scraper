# Agent 2: QA_SPECIALIST (Blake)
## Production Enhancement: Testing & Quality Assurance

### 🎯 Mission
Create a comprehensive test suite covering unit tests, integration tests, and API tests with high code coverage to ensure code quality and reliability.

---

## 📋 Detailed Tasks

### 1. Test Infrastructure Setup

#### 1.1 Pytest Configuration
- **File:** `pytest.ini`
- Configure:
  - Test discovery patterns
  - Coverage settings
  - Output formatting
  - Markers for test categories

#### 1.2 Test Fixtures
- **File:** `tests/conftest.py`
- Create fixtures:
  - `app` - Flask test client
  - `db_session` - Test database session
  - `test_client` - Authenticated test client
  - `sample_account` - Sample DimAccount
  - `sample_snapshot` - Sample FactFollowersSnapshot
  - `mock_scraper` - Mock scraper for testing

#### 1.3 Test Database Setup
- Use SQLite in-memory database for tests
- Create/drop tables before/after tests
- Seed test data fixtures

---

### 2. Unit Tests

#### 2.1 Scraper Tests
- **File:** `tests/unit/test_scrapers.py`
- Test:
  - `SimulatedScraper.scrape()` returns valid data
  - `RealScraper.scrape()` handles errors gracefully
  - `get_scraper()` returns correct scraper type
  - Scraper handles missing data
  - Scraper handles network errors

#### 2.2 Schema Tests
- **File:** `tests/unit/test_schema.py`
- Test:
  - Database model creation
  - Relationships (DimAccount -> FactFollowersSnapshot)
  - Field validations
  - Foreign key constraints
  - Model serialization

#### 2.3 Utility Function Tests
- **File:** `tests/unit/test_extract_accounts.py`
- Test:
  - `extract_handle()` for each platform
  - `populate_accounts()` creates accounts correctly
  - Handles duplicate accounts
  - Handles invalid URLs
  - Handles missing JSON fields

#### 2.4 Metrics Collection Tests
- **File:** `tests/unit/test_collect_metrics.py`
- Test:
  - `simulate_metrics()` creates snapshots
  - Prevents duplicate snapshots for same date
  - Calculates engagements_total correctly
  - Handles missing accounts

#### 2.5 Backfill Tests
- **File:** `tests/unit/test_backfill.py`
- Test:
  - `backfill_history()` creates historical data
  - Skips existing snapshots
  - Generates realistic growth patterns
  - Handles edge cases (no accounts, etc.)

---

### 3. Integration Tests

#### 3.1 API Endpoint Tests
- **File:** `tests/integration/test_api.py`
- Test all endpoints:
  - `GET /` - Dashboard loads
  - `GET /api/summary` - Returns latest metrics
  - `GET /api/history/<platform>/<handle>` - Returns history
  - `GET /api/grid` - Returns all data
  - `GET /api/download` - Downloads CSV
  - `POST /upload` - Uploads and processes CSV
  - `POST /api/run-scraper` - Triggers scraper

#### 3.2 Database Integration Tests
- **File:** `tests/integration/test_database.py`
- Test:
  - Account creation and retrieval
  - Snapshot creation and querying
  - Joins between tables
  - Data integrity
  - Transaction rollback on errors

#### 3.3 Scraper Flow Tests
- **File:** `tests/integration/test_scraper_flow.py`
- Test:
  - Full scraper execution flow
  - Account extraction → Metrics collection
  - Error handling in full flow
  - Data persistence

#### 3.4 File Upload Tests
- **File:** `tests/integration/test_upload.py`
- Test:
  - CSV file upload
  - Invalid file types rejected
  - File size limits
  - CSV parsing and account creation
  - Error handling for malformed CSV

---

### 4. Test Coverage

#### 4.1 Coverage Configuration
- **Package:** `pytest-cov`
- Target: 80%+ code coverage
- Exclude:
  - `venv/`
  - `__pycache__/`
  - Test files themselves
  - Migration files

#### 4.2 Coverage Reports
- Generate HTML coverage report
- Generate terminal coverage report
- Add coverage badge to README (optional)

---

### 5. CI/CD Integration

#### 5.1 GitHub Actions Workflow
- **File:** `.github/workflows/tests.yml`
- Configure:
  - Run tests on push and PR
  - Test on Python 3.9, 3.10, 3.11
  - Generate coverage reports
  - Upload coverage to codecov (optional)
  - Fail on coverage below threshold

#### 5.2 Pre-commit Hooks
- **File:** `.pre-commit-config.yaml`
- Hooks:
  - Run tests
  - Check code formatting (black, flake8)
  - Check imports (isort)
  - Run linter

---

## 📁 File Structure to Create

```
tests/
├── __init__.py
├── conftest.py                    # Shared fixtures
├── unit/
│   ├── __init__.py
│   ├── test_scrapers.py
│   ├── test_schema.py
│   ├── test_extract_accounts.py
│   ├── test_collect_metrics.py
│   └── test_backfill.py
├── integration/
│   ├── __init__.py
│   ├── test_api.py
│   ├── test_database.py
│   ├── test_scraper_flow.py
│   └── test_upload.py
└── fixtures/
    ├── sample_accounts.json
    └── sample_csv.csv

.github/
└── workflows/
    └── tests.yml

pytest.ini
.pre-commit-config.yaml
```

---

## 🔧 Dependencies to Add

Add to `requirements.txt`:
```
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-flask>=1.2.0
pytest-mock>=3.11.0
coverage>=7.3.0
```

Add to `requirements-dev.txt` (optional):
```
black>=23.0.0
flake8>=6.1.0
isort>=5.12.0
pre-commit>=3.4.0
```

---

## ✅ Acceptance Criteria

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Code coverage is 80% or higher
- [ ] Tests run in CI/CD pipeline
- [ ] Pre-commit hooks work
- [ ] Test documentation is clear
- [ ] Tests are maintainable and well-organized

---

## 🧪 Test Examples

### Example Unit Test:
```python
def test_simulated_scraper_returns_data():
    scraper = SimulatedScraper()
    account = DimAccount(platform='X', handle='test', org_name='HHS')
    result = scraper.scrape(account)
    assert 'followers_count' in result
    assert result['followers_count'] > 0
```

### Example Integration Test:
```python
def test_api_summary_returns_data(client, db_session, sample_account):
    snapshot = FactFollowersSnapshot(
        account_key=sample_account.account_key,
        snapshot_date=date.today(),
        followers_count=1000
    )
    db_session.add(snapshot)
    db_session.commit()
    
    response = client.get('/api/summary')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) > 0
```

---

## 📝 Testing Best Practices

- Use descriptive test names
- Follow AAA pattern (Arrange, Act, Assert)
- Test edge cases and error conditions
- Mock external dependencies (APIs, file system)
- Keep tests independent and isolated
- Use fixtures for common setup
- Test both success and failure paths

---

## 🚀 Getting Started

1. Create branch: `git checkout -b feature/agent-2-testing`
2. Install test dependencies: `pip install -r requirements.txt`
3. Set up pytest configuration
4. Create test directory structure
5. Write fixtures in conftest.py
6. Write unit tests first
7. Write integration tests
8. Set up CI/CD
9. Achieve coverage target
10. Document test procedures

---

## 📊 Coverage Goals

- `scraper/` module: 85%+
- `app.py`: 80%+
- `schema.py`: 90%+
- Overall: 80%+

---

**Agent Blake - Ready to ensure quality! 🧪**


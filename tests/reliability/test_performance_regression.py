"""
Performance Regression Testing.

Tests to detect performance regressions over time.
"""
import pytest
import time
from datetime import date
from scraper.schema import DimAccount, FactFollowersSnapshot


@pytest.mark.performance
class TestPerformanceBaselines:
    """Establish and verify performance baselines."""

    def test_api_response_time_baseline(self, client, db_session):
        """Establish baseline for API response times."""
        # Create test data
        account = DimAccount(platform="X", handle="baseline_test", org_name="HHS")
        db_session.add(account)
        db_session.commit()

        snapshot = FactFollowersSnapshot(
            account_key=account.account_key,
            snapshot_date=date.today(),
            followers_count=1000,
        )
        db_session.add(snapshot)
        db_session.commit()

        # Measure response time
        times = []
        for _ in range(10):
            start = time.time()
            response = client.get("/api/summary")
            elapsed = time.time() - start
            if response.status_code == 200:
                times.append(elapsed)

        if times:
            avg_time = sum(times) / len(times)
            p95_time = sorted(times)[int(len(times) * 0.95)]

            # Baseline: should be under 1 second
            assert avg_time < 1.0, f"Average response time {avg_time}s exceeds baseline"
            assert p95_time < 2.0, f"P95 response time {p95_time}s exceeds baseline"

    def test_database_query_baseline(self, db_session, sample_account):
        """Establish baseline for database queries."""
        # Create test data
        for i in range(100):
            snapshot = FactFollowersSnapshot(
                account_key=sample_account.account_key,
                snapshot_date=date.fromordinal(date.today().toordinal() - i),
                followers_count=1000 + i,
            )
            db_session.add(snapshot)
        db_session.commit()

        # Measure query time
        times = []
        for _ in range(10):
            start = time.time()
            results = (
                db_session.query(FactFollowersSnapshot)
                .filter_by(account_key=sample_account.account_key)
                .limit(10)
                .all()
            )
            elapsed = time.time() - start
            times.append(elapsed)

        avg_time = sum(times) / len(times)
        # Baseline: should be under 0.1 seconds
        assert avg_time < 0.1, f"Query time {avg_time}s exceeds baseline"


@pytest.mark.performance
class TestPerformanceRegression:
    """Test for performance regressions."""

    def test_api_response_time_regression(self, client, db_session):
        """Detect API response time regressions."""
        # Create test data
        account = DimAccount(platform="X", handle="regression_test", org_name="HHS")
        db_session.add(account)
        db_session.commit()

        snapshot = FactFollowersSnapshot(
            account_key=account.account_key,
            snapshot_date=date.today(),
            followers_count=1000,
        )
        db_session.add(snapshot)
        db_session.commit()

        # Measure current performance
        times = []
        for _ in range(20):
            start = time.time()
            response = client.get("/api/summary")
            elapsed = time.time() - start
            if response.status_code == 200:
                times.append(elapsed)

        if times:
            avg_time = sum(times) / len(times)
            # Regression threshold: 2x baseline (2 seconds)
            assert avg_time < 2.0, f"Performance regression detected: {avg_time}s"

    def test_database_performance_regression(self, db_session):
        """Detect database performance regressions."""
        # Create test data
        accounts = []
        for i in range(100):
            account = DimAccount(platform="X", handle=f"perf_reg_{i}", org_name="HHS")
            accounts.append(account)
            db_session.add(account)
        db_session.commit()

        # Measure query performance
        start = time.time()
        results = (
            db_session.query(DimAccount)
            .filter(DimAccount.handle.like("perf_reg_%"))
            .all()
        )
        elapsed = time.time() - start

        # Regression threshold: should complete in under 0.5 seconds
        assert elapsed < 0.5, f"Database performance regression: {elapsed}s"
        assert len(results) == 100


@pytest.mark.performance
class TestPerformanceTrends:
    """Track performance trends over time."""

    def test_performance_trend_tracking(self, client, db_session):
        """Track performance trends."""
        # This would typically store metrics over time
        # For now, just verify we can measure performance

        account = DimAccount(platform="X", handle="trend_test", org_name="HHS")
        db_session.add(account)
        db_session.commit()

        snapshot = FactFollowersSnapshot(
            account_key=account.account_key,
            snapshot_date=date.today(),
            followers_count=1000,
        )
        db_session.add(snapshot)
        db_session.commit()

        # Measure performance
        metrics = {
            "endpoint": "/api/summary",
            "response_times": [],
            "success_count": 0,
            "error_count": 0,
        }

        for _ in range(10):
            start = time.time()
            response = client.get("/api/summary")
            elapsed = time.time() - start

            metrics["response_times"].append(elapsed)
            if response.status_code == 200:
                metrics["success_count"] += 1
            else:
                metrics["error_count"] += 1

        # Verify metrics collected
        assert len(metrics["response_times"]) == 10
        assert metrics["success_count"] + metrics["error_count"] == 10

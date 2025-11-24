"""
Performance regression testing.
"""
import time
import json
import os
from pathlib import Path
from typing import Dict, Optional
import pytest


class PerformanceRegression:
    """Performance regression testing utilities."""

    def __init__(self, baseline_file: str = "performance_baseline.json"):
        """
        Initialize regression tester.

        Args:
            baseline_file: Path to baseline performance metrics
        """
        self.baseline_file = Path(baseline_file)
        self.baseline = self._load_baseline()

    def _load_baseline(self) -> Dict:
        """Load baseline performance metrics."""
        if self.baseline_file.exists():
            with open(self.baseline_file, "r") as f:
                return json.load(f)
        return {}

    def save_baseline(self, metrics: Dict):
        """Save current metrics as baseline."""
        with open(self.baseline_file, "w") as f:
            json.dump(metrics, f, indent=2)
        self.baseline = metrics

    def check_regression(
        self, endpoint: str, current_time: float, threshold: float = 0.2
    ) -> Dict:
        """
        Check if performance has regressed.

        Args:
            endpoint: Endpoint name
            current_time: Current response time
            threshold: Regression threshold (20% by default)

        Returns:
            Regression check results
        """
        if endpoint not in self.baseline:
            return {
                "endpoint": endpoint,
                "status": "no_baseline",
                "current": current_time,
                "message": "No baseline available",
            }

        baseline_time = self.baseline[endpoint].get("avg_time", 0)
        if baseline_time == 0:
            return {
                "endpoint": endpoint,
                "status": "no_baseline",
                "current": current_time,
            }

        regression = (current_time - baseline_time) / baseline_time
        is_regression = regression > threshold

        return {
            "endpoint": endpoint,
            "status": "regression" if is_regression else "ok",
            "current": current_time,
            "baseline": baseline_time,
            "regression_percent": regression * 100,
            "threshold": threshold * 100,
            "is_regression": is_regression,
        }

    def update_baseline(self, endpoint: str, metrics: Dict):
        """Update baseline for an endpoint."""
        if "endpoints" not in self.baseline:
            self.baseline["endpoints"] = {}

        self.baseline["endpoints"][endpoint] = metrics
        self.save_baseline(self.baseline)


@pytest.fixture
def regression_tester():
    """Performance regression tester fixture."""
    return PerformanceRegression()


def test_api_summary_regression(regression_tester, client):
    """Test for performance regression in /api/summary."""
    # Measure current performance
    times = []
    for _ in range(10):
        start = time.time()
        client.get("/api/summary")
        times.append(time.time() - start)

    avg_time = sum(times) / len(times)

    # Check against baseline
    result = regression_tester.check_regression("api_summary", avg_time)

    if result["status"] == "regression":
        pytest.fail(
            f"Performance regression detected: {result['regression_percent']:.1f}% "
            f"slower than baseline ({result['baseline']*1000:.2f}ms -> {result['current']*1000:.2f}ms)"
        )
    elif result["status"] == "no_baseline":
        # Save as new baseline
        regression_tester.update_baseline("api_summary", {"avg_time": avg_time})
        print(f"Saved new baseline for api_summary: {avg_time*1000:.2f}ms")
    else:
        print(
            f"Performance OK: {avg_time*1000:.2f}ms (baseline: {result['baseline']*1000:.2f}ms)"
        )


def test_api_history_regression(regression_tester, client):
    """Test for performance regression in /api/history."""
    times = []
    for _ in range(10):
        start = time.time()
        client.get("/api/history/x/testhandle")
        times.append(time.time() - start)

    avg_time = sum(times) / len(times)
    result = regression_tester.check_regression("api_history", avg_time)

    if result["status"] == "regression":
        pytest.fail(
            f"Performance regression: {result['regression_percent']:.1f}% slower"
        )
    elif result["status"] == "no_baseline":
        regression_tester.update_baseline("api_history", {"avg_time": avg_time})


def test_cache_performance_regression(regression_tester):
    """Test for cache performance regression."""
    from cache.multi_level import get_multi_cache

    multi_cache = get_multi_cache()

    # Measure cache get performance
    times = []
    multi_cache.set("test_key", {"data": "test"})
    for _ in range(100):
        start = time.time()
        multi_cache.get("test_key")
        times.append(time.time() - start)

    avg_time = sum(times) / len(times)
    result = regression_tester.check_regression("cache_get", avg_time, threshold=0.5)

    if result["status"] == "regression":
        pytest.fail(
            f"Cache performance regression: {result['regression_percent']:.1f}% slower"
        )
    elif result["status"] == "no_baseline":
        regression_tester.update_baseline("cache_get", {"avg_time": avg_time})

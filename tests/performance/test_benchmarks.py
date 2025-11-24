"""
Performance benchmarking suite.
"""
import time
import statistics
from typing import Dict, List
import pytest
from flask import Flask
from flask.testing import FlaskClient


class PerformanceBenchmark:
    """Performance benchmarking utilities."""
    
    def __init__(self):
        self.results = []
    
    def benchmark_endpoint(self, client: FlaskClient, method: str, path: str, 
                          iterations: int = 10, **kwargs) -> Dict:
        """
        Benchmark an API endpoint.
        
        Args:
            client: Flask test client
            method: HTTP method
            path: Endpoint path
            iterations: Number of iterations
            **kwargs: Additional request arguments
            
        Returns:
            Benchmark results dictionary
        """
        times = []
        errors = 0
        
        for _ in range(iterations):
            start = time.time()
            try:
                response = getattr(client, method.lower())(path, **kwargs)
                if response.status_code >= 400:
                    errors += 1
            except Exception:
                errors += 1
            finally:
                elapsed = time.time() - start
                times.append(elapsed)
        
        return {
            'endpoint': path,
            'method': method,
            'iterations': iterations,
            'avg_time': statistics.mean(times),
            'min_time': min(times),
            'max_time': max(times),
            'median_time': statistics.median(times),
            'p95_time': self._percentile(times, 95),
            'p99_time': self._percentile(times, 99),
            'errors': errors,
            'success_rate': ((iterations - errors) / iterations * 100) if iterations > 0 else 0
        }
    
    def benchmark_cache_performance(self, cache_func, iterations: int = 100) -> Dict:
        """Benchmark cache operations."""
        times = []
        for _ in range(iterations):
            start = time.time()
            cache_func()
            times.append(time.time() - start)
        
        return {
            'operation': 'cache',
            'iterations': iterations,
            'avg_time': statistics.mean(times),
            'min_time': min(times),
            'max_time': max(times),
            'p95_time': self._percentile(times, 95),
        }
    
    def benchmark_database_query(self, query_func, iterations: int = 10) -> Dict:
        """Benchmark database query performance."""
        times = []
        for _ in range(iterations):
            start = time.time()
            query_func()
            times.append(time.time() - start)
        
        return {
            'operation': 'database_query',
            'iterations': iterations,
            'avg_time': statistics.mean(times),
            'min_time': min(times),
            'max_time': max(times),
            'p95_time': self._percentile(times, 95),
        }
    
    def _percentile(self, data: list, percentile: float) -> float:
        """Calculate percentile."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]


@pytest.fixture
def perf_benchmark():
    """Performance benchmark fixture (renamed to avoid conflict with pytest-benchmark)."""
    return PerformanceBenchmark()


def test_api_summary_performance(perf_benchmark, client):
    """Benchmark /api/summary endpoint."""
    result = perf_benchmark.benchmark_endpoint(client, 'GET', '/api/summary', iterations=20)
    
    # Assertions
    assert result['avg_time'] < 1.0, f"Average time {result['avg_time']}s exceeds 1s target"
    assert result['p95_time'] < 2.0, f"P95 time {result['p95_time']}s exceeds 2s target"
    assert result['success_rate'] == 100, "All requests should succeed"
    
    print(f"\n/api/summary Performance:")
    print(f"  Avg: {result['avg_time']*1000:.2f}ms")
    print(f"  P95: {result['p95_time']*1000:.2f}ms")
    print(f"  P99: {result['p99_time']*1000:.2f}ms")


def test_api_history_performance(perf_benchmark, client):
    """Benchmark /api/history endpoint."""
    # Need a valid account first
    result = perf_benchmark.benchmark_endpoint(
        client, 'GET', '/api/history/x/testhandle', iterations=20
    )
    
    assert result['avg_time'] < 1.0
    assert result['success_rate'] >= 90  # May have 404s for non-existent accounts


def test_api_grid_performance(perf_benchmark, client):
    """Benchmark /api/grid endpoint."""
    result = perf_benchmark.benchmark_endpoint(client, 'GET', '/api/grid', iterations=10)
    
    assert result['avg_time'] < 2.0  # Grid can be slower due to more data
    print(f"\n/api/grid Performance:")
    print(f"  Avg: {result['avg_time']*1000:.2f}ms")


def test_cache_performance(perf_benchmark):
    """Benchmark cache operations."""
    from cache.multi_level import get_multi_cache
    
    multi_cache = get_multi_cache()
    
    # Test cache set
    set_result = perf_benchmark.benchmark_cache_performance(
        lambda: multi_cache.set('test_key', {'data': 'test'}), 
        iterations=100
    )
    
    # Test cache get
    get_result = perf_benchmark.benchmark_cache_performance(
        lambda: multi_cache.get('test_key'),
        iterations=100
    )
    
    assert set_result['avg_time'] < 0.01  # 10ms
    assert get_result['avg_time'] < 0.005  # 5ms
    
    print(f"\nCache Performance:")
    print(f"  Set Avg: {set_result['avg_time']*1000:.2f}ms")
    print(f"  Get Avg: {get_result['avg_time']*1000:.2f}ms")


def test_database_query_performance(perf_benchmark, db_session):
    """Benchmark database query performance."""
    from scraper.schema import DimAccount, FactFollowersSnapshot
    from sqlalchemy import func
    
    # Benchmark latest date query
    def query_latest_date():
        return db_session.query(
            func.max(FactFollowersSnapshot.snapshot_date)
        ).scalar()
    
    result = perf_benchmark.benchmark_database_query(query_latest_date, iterations=20)
    
    assert result['avg_time'] < 0.1  # 100ms
    print(f"\nDatabase Query Performance:")
    print(f"  Avg: {result['avg_time']*1000:.2f}ms")


"""
Load testing scenarios.
"""
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict
import pytest


class LoadTest:
    """Load testing utilities."""
    
    def __init__(self):
        self.results = []
    
    def run_concurrent_requests(self, client_func, num_threads: int = 10, 
                                requests_per_thread: int = 10) -> Dict:
        """
        Run concurrent requests to simulate load.
        
        Args:
            client_func: Function that makes a request (returns response)
            num_threads: Number of concurrent threads
            requests_per_thread: Requests per thread
            
        Returns:
            Load test results
        """
        start_time = time.time()
        results = {
            'success': 0,
            'errors': 0,
            'times': [],
            'status_codes': {}
        }
        
        def make_requests():
            thread_results = []
            for _ in range(requests_per_thread):
                req_start = time.time()
                try:
                    response = client_func()
                    elapsed = time.time() - req_start
                    thread_results.append({
                        'success': True,
                        'status': response.status_code if hasattr(response, 'status_code') else 200,
                        'time': elapsed
                    })
                except Exception as e:
                    elapsed = time.time() - req_start
                    thread_results.append({
                        'success': False,
                        'error': str(e),
                        'time': elapsed
                    })
            return thread_results
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(make_requests) for _ in range(num_threads)]
            
            for future in as_completed(futures):
                thread_results = future.result()
                for result in thread_results:
                    if result['success']:
                        results['success'] += 1
                        status = result.get('status', 200)
                        results['status_codes'][status] = results['status_codes'].get(status, 0) + 1
                    else:
                        results['errors'] += 1
                    results['times'].append(result['time'])
        
        total_time = time.time() - start_time
        total_requests = num_threads * requests_per_thread
        
        return {
            'total_requests': total_requests,
            'success': results['success'],
            'errors': results['errors'],
            'success_rate': (results['success'] / total_requests * 100) if total_requests > 0 else 0,
            'total_time': total_time,
            'requests_per_second': total_requests / total_time if total_time > 0 else 0,
            'avg_time': sum(results['times']) / len(results['times']) if results['times'] else 0,
            'min_time': min(results['times']) if results['times'] else 0,
            'max_time': max(results['times']) if results['times'] else 0,
            'status_codes': results['status_codes']
        }


@pytest.fixture
def load_test():
    """Load test fixture."""
    return LoadTest()


def test_concurrent_summary_requests(load_test, client):
    """Test concurrent requests to /api/summary."""
    def make_request():
        return client.get('/api/summary')
    
    result = load_test.run_concurrent_requests(
        make_request,
        num_threads=20,
        requests_per_thread=5
    )
    
    assert result['success_rate'] >= 95, f"Success rate {result['success_rate']}% below 95%"
    assert result['requests_per_second'] > 10, "Should handle at least 10 req/s"
    
    print(f"\nLoad Test - /api/summary:")
    print(f"  Total Requests: {result['total_requests']}")
    print(f"  Success Rate: {result['success_rate']:.1f}%")
    print(f"  Requests/sec: {result['requests_per_second']:.2f}")
    print(f"  Avg Response Time: {result['avg_time']*1000:.2f}ms")


def test_concurrent_history_requests(load_test, client):
    """Test concurrent requests to /api/history."""
    def make_request():
        return client.get('/api/history/x/testhandle')
    
    result = load_test.run_concurrent_requests(
        make_request,
        num_threads=10,
        requests_per_thread=5
    )
    
    assert result['success_rate'] >= 90
    print(f"\nLoad Test - /api/history:")
    print(f"  Success Rate: {result['success_rate']:.1f}%")
    print(f"  Requests/sec: {result['requests_per_second']:.2f}")


def test_sustained_load(load_test, client):
    """Test sustained load over time."""
    def make_request():
        return client.get('/api/summary')
    
    # Run for 30 seconds
    start = time.time()
    results = []
    
    while time.time() - start < 30:
        result = load_test.run_concurrent_requests(
            make_request,
            num_threads=10,
            requests_per_thread=1
        )
        results.append(result)
        time.sleep(1)
    
    # Analyze results
    avg_success_rate = sum(r['success_rate'] for r in results) / len(results)
    avg_rps = sum(r['requests_per_second'] for r in results) / len(results)
    
    assert avg_success_rate >= 95, "Success rate should remain high under sustained load"
    
    print(f"\nSustained Load Test (30s):")
    print(f"  Avg Success Rate: {avg_success_rate:.1f}%")
    print(f"  Avg Requests/sec: {avg_rps:.2f}")

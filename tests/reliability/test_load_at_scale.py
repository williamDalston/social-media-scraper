"""
Load Testing at Scale.

Tests for system behavior under production-scale loads.
"""
import pytest
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from scraper.schema import DimAccount, FactFollowersSnapshot


@pytest.mark.load
@pytest.mark.slow
class TestScaledLoad:
    """Load tests at production scale."""
    
    def test_high_concurrency_api_requests(self, client, db_session):
        """Test API under high concurrency."""
        # Create test data
        accounts = []
        for i in range(50):
            account = DimAccount(
                platform='X',
                handle=f'load_test_{i}',
                org_name='HHS'
            )
            db_session.add(account)
            accounts.append(account)
        db_session.commit()
        
        today = date.today()
        for account in accounts:
            snapshot = FactFollowersSnapshot(
                account_key=account.account_key,
                snapshot_date=today,
                followers_count=1000
            )
            db_session.add(snapshot)
        db_session.commit()
        
        # High concurrency test
        num_threads = 50
        requests_per_thread = 10
        
        results = {'success': 0, 'errors': 0, 'times': []}
        
        def make_requests():
            thread_results = []
            for _ in range(requests_per_thread):
                start = time.time()
                try:
                    response = client.get('/api/summary')
                    elapsed = time.time() - start
                    if response.status_code < 500:
                        results['success'] += 1
                    else:
                        results['errors'] += 1
                    results['times'].append(elapsed)
                except Exception:
                    results['errors'] += 1
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(make_requests) for _ in range(num_threads)]
            for future in as_completed(futures):
                future.result()
        
        total = results['success'] + results['errors']
        if total > 0:
            success_rate = results['success'] / total * 100
            avg_time = sum(results['times']) / len(results['times']) if results['times'] else 0
            
            # Should maintain high success rate under load
            assert success_rate >= 95, f"Success rate {success_rate}% below 95%"
            # Should maintain reasonable response times
            assert avg_time < 2.0, f"Average response time {avg_time}s too high"
    
    def test_large_dataset_query_performance(self, db_session):
        """Test query performance with large datasets."""
        # Create large dataset
        account = DimAccount(platform='X', handle='large_test', org_name='HHS')
        db_session.add(account)
        db_session.commit()
        
        # Create many snapshots
        snapshots = []
        for i in range(1000):
            snapshot = FactFollowersSnapshot(
                account_key=account.account_key,
                snapshot_date=date.fromordinal(date.today().toordinal() - (i % 365)),
                followers_count=1000 + i
            )
            snapshots.append(snapshot)
            db_session.add(snapshot)
        db_session.commit()
        
        # Test query performance
        start = time.time()
        results = db_session.query(FactFollowersSnapshot).filter_by(
            account_key=account.account_key
        ).order_by(FactFollowersSnapshot.snapshot_date.desc()).limit(100).all()
        elapsed = time.time() - start
        
        # Should query quickly even with large dataset
        assert elapsed < 1.0
        assert len(results) == 100
    
    def test_bulk_operations_at_scale(self, db_session):
        """Test bulk operations performance."""
        # Bulk account creation
        start = time.time()
        accounts = []
        for i in range(500):
            account = DimAccount(
                platform='X',
                handle=f'bulk_scale_{i}',
                org_name='HHS'
            )
            accounts.append(account)
            db_session.add(account)
        db_session.commit()
        elapsed = time.time() - start
        
        # Should complete in reasonable time
        assert elapsed < 5.0
        assert len(accounts) == 500


@pytest.mark.load
@pytest.mark.slow
class TestSustainedLoad:
    """Tests for sustained load over time."""
    
    def test_sustained_api_load(self, client, db_session):
        """Test API under sustained load."""
        # Create test data
        account = DimAccount(platform='X', handle='sustained_test', org_name='HHS')
        db_session.add(account)
        db_session.commit()
        
        snapshot = FactFollowersSnapshot(
            account_key=account.account_key,
            snapshot_date=date.today(),
            followers_count=1000
        )
        db_session.add(snapshot)
        db_session.commit()
        
        # Run sustained load for 60 seconds
        duration = 60
        start_time = time.time()
        request_count = 0
        errors = 0
        
        while time.time() - start_time < duration:
            try:
                response = client.get('/api/summary')
                request_count += 1
                if response.status_code >= 500:
                    errors += 1
            except Exception:
                errors += 1
            
            time.sleep(0.1)  # 10 requests per second
        
        # Should maintain high availability
        if request_count > 0:
            error_rate = errors / request_count * 100
            assert error_rate < 5, f"Error rate {error_rate}% too high"
    
    def test_memory_stability_under_load(self, db_session):
        """Test memory stability under sustained load."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform many operations
        for i in range(100):
            account = DimAccount(
                platform='X',
                handle=f'memory_load_{i}',
                org_name='HHS'
            )
            db_session.add(account)
            if i % 10 == 0:
                db_session.commit()
        
        db_session.commit()
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (under 100MB for this test)
        assert memory_increase < 100, f"Memory increased by {memory_increase}MB"


@pytest.mark.load
@pytest.mark.slow
class TestPeakLoad:
    """Tests for peak load scenarios."""
    
    def test_peak_traffic_handling(self, client, db_session):
        """Test handling of peak traffic spikes."""
        # Create test data
        for i in range(20):
            account = DimAccount(platform='X', handle=f'peak_{i}', org_name='HHS')
            db_session.add(account)
        db_session.commit()
        
        # Simulate traffic spike
        num_threads = 100
        requests_per_thread = 5
        
        results = {'success': 0, 'errors': 0}
        
        def spike_request():
            for _ in range(requests_per_thread):
                try:
                    response = client.get('/api/summary')
                    if response.status_code < 500:
                        results['success'] += 1
                    else:
                        results['errors'] += 1
                except Exception:
                    results['errors'] += 1
        
        start = time.time()
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(spike_request) for _ in range(num_threads)]
            for future in as_completed(futures):
                future.result()
        elapsed = time.time() - start
        
        total = results['success'] + results['errors']
        if total > 0:
            success_rate = results['success'] / total * 100
            rps = total / elapsed if elapsed > 0 else 0
            
            # Should handle peak load
            assert success_rate >= 90, f"Success rate {success_rate}% below 90%"
            assert rps > 50, f"Requests per second {rps} too low"


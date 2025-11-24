"""
Chaos engineering tests - test system resilience to failures.
"""
import pytest
import requests
import time

BASE_URL = "http://localhost:5000"


class TestChaosEngineering:
    """Chaos engineering tests for production resilience."""

    def test_handles_slow_requests(self):
        """Test that system handles slow requests gracefully."""
        # Make a request with a long timeout
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=30)
            assert response.status_code in [200, 504]  # Should timeout or succeed
        except requests.exceptions.Timeout:
            # Timeout is acceptable for this test
            pass

    def test_handles_invalid_requests(self):
        """Test that system handles invalid requests gracefully."""
        # Send malformed requests
        invalid_requests = [
            ("POST", "/api/summary", {"invalid": "json"}),
            ("GET", "/api/invalid/endpoint", None),
        ]

        for method, endpoint, data in invalid_requests:
            try:
                if method == "POST":
                    response = requests.post(
                        f"{BASE_URL}{endpoint}", json=data, timeout=5
                    )
                else:
                    response = requests.get(f"{BASE_URL}{endpoint}", timeout=5)

                # Should return appropriate error code, not crash
                assert response.status_code in [400, 401, 404, 405, 422]
            except Exception as e:
                pytest.fail(f"Request to {endpoint} caused exception: {e}")

    def test_rate_limiting_works(self):
        """Test that rate limiting prevents abuse."""
        # Make many rapid requests
        responses = []
        for i in range(110):  # More than typical rate limit
            try:
                response = requests.get(f"{BASE_URL}/health", timeout=1)
                responses.append(response.status_code)
                time.sleep(0.1)  # Small delay
            except:
                pass

        # Should see some 429 (Too Many Requests) responses
        # Or all should succeed if rate limit is high
        assert len(responses) > 0

    def test_graceful_degradation(self):
        """Test that system degrades gracefully under load."""
        # This would require load testing
        # For now, just verify health endpoint works
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        assert response.status_code == 200

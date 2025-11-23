"""
Production smoke tests - quick tests to verify system is operational.
"""
import pytest
import requests
import time
from datetime import datetime

BASE_URL = "http://localhost:5000"

class TestProductionSmoke:
    """Smoke tests for production deployment."""
    
    def test_health_endpoint(self):
        """Test that health endpoint responds."""
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert 'status' in data
    
    def test_api_accessible(self):
        """Test that API is accessible."""
        # Try to access a public endpoint
        response = requests.get(f"{BASE_URL}/api/auth/oauth/providers", timeout=5)
        # Should return 200 or 401 (if auth required)
        assert response.status_code in [200, 401]
    
    def test_database_connectivity(self):
        """Test that database is accessible."""
        # This would require authentication, but we can test the endpoint exists
        response = requests.get(f"{BASE_URL}/api/summary", timeout=5)
        # Should return 401 (unauthorized) or 200 (if no auth required)
        assert response.status_code in [200, 401]
    
    def test_response_time(self):
        """Test that response times are acceptable."""
        start = time.time()
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        duration = time.time() - start
        
        assert response.status_code == 200
        assert duration < 2.0  # Should respond in under 2 seconds
    
    def test_cors_headers(self):
        """Test that CORS headers are present."""
        response = requests.options(f"{BASE_URL}/api/summary", timeout=5)
        # CORS headers should be present
        assert 'Access-Control-Allow-Origin' in response.headers or response.status_code == 405
    
    def test_security_headers(self):
        """Test that security headers are present."""
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        
        # Check for security headers
        assert 'X-Content-Type-Options' in response.headers
        assert response.headers['X-Content-Type-Options'] == 'nosniff'
        
        # X-Frame-Options should be present
        assert 'X-Frame-Options' in response.headers

@pytest.fixture(scope="class")
def wait_for_service():
    """Wait for service to be ready."""
    max_retries = 30
    for i in range(max_retries):
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=2)
            if response.status_code == 200:
                return
        except:
            pass
        time.sleep(1)
    pytest.skip("Service not available")

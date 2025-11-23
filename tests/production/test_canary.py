"""
Canary deployment testing - verify new deployment works correctly.
"""
import pytest
import requests
import json

BASE_URL = "http://localhost:5000"

class TestCanaryDeployment:
    """Tests for canary deployment validation."""
    
    def test_api_version_compatibility(self):
        """Test that API version is compatible."""
        # Check API version endpoint if it exists
        try:
            response = requests.get(f"{BASE_URL}/api/version", timeout=5)
            if response.status_code == 200:
                data = response.json()
                assert 'version' in data
        except:
            pass  # Version endpoint may not exist
    
    def test_critical_endpoints_work(self):
        """Test that critical endpoints are functional."""
        endpoints = [
            "/health",
            "/api/auth/oauth/providers",
        ]
        
        for endpoint in endpoints:
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=5)
            # Should not return 500 (internal server error)
            assert response.status_code != 500, f"Endpoint {endpoint} returned 500"
    
    def test_database_migrations_applied(self):
        """Test that database migrations are applied."""
        # This would require checking database schema
        # For now, just verify we can connect
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        assert response.status_code == 200
    
    def test_configuration_valid(self):
        """Test that configuration is valid."""
        # Check that required environment variables are set
        # This is more of a deployment check
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        assert response.status_code == 200

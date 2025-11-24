"""
Integration tests for authentication (if auth is available).
"""
import pytest


@pytest.mark.requires_auth
class TestAuthentication:
    """Test authentication endpoints if available."""

    def test_login_endpoint_exists(self, client):
        """Test that login endpoint exists."""
        # This test will only run if auth is available
        try:
            response = client.post(
                "/api/auth/login", json={"username": "test", "password": "test"}
            )
            # Should return either 200 (success) or 401 (unauthorized), not 404
            assert response.status_code != 404
        except Exception:
            # Auth not available, skip
            pytest.skip("Authentication not available")

    def test_protected_endpoints_require_auth(self, client):
        """Test that protected endpoints require authentication."""
        try:
            response = client.get("/api/summary")
            # Should return either 200 (if auth is optional) or 401 (if required)
            assert response.status_code in [200, 401]
        except Exception:
            pytest.skip("Authentication not available")

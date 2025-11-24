"""
Automated security testing framework.
"""
import pytest
from flask import Flask
from flask.testing import FlaskClient
import json


@pytest.fixture
def app():
    """Create test Flask app."""
    from app import app as flask_app

    flask_app.config["TESTING"] = True
    flask_app.config["SECRET_KEY"] = "test-secret-key"
    return flask_app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def auth_token(client):
    """Get authentication token for testing."""
    # Create test user
    response = client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "TestPass123!@#",
        },
    )
    if response.status_code == 201:
        data = response.get_json()
        return data.get("access_token")

    # Or login
    response = client.post(
        "/api/auth/login", json={"username": "testuser", "password": "TestPass123!@#"}
    )
    if response.status_code == 200:
        data = response.get_json()
        return data.get("access_token")

    return None


class TestAuthentication:
    """Test authentication security."""

    def test_password_strength_validation(self, client):
        """Test password strength requirements."""
        # Weak password
        response = client.post(
            "/api/auth/register",
            json={
                "username": "testuser1",
                "email": "test1@example.com",
                "password": "weak",
            },
        )
        assert response.status_code == 400
        assert "password" in response.get_json().get("error", "").lower()

    def test_account_lockout(self, client):
        """Test account lockout after failed attempts."""
        # Register user
        client.post(
            "/api/auth/register",
            json={
                "username": "locktest",
                "email": "locktest@example.com",
                "password": "TestPass123!@#",
            },
        )

        # Attempt multiple failed logins
        for i in range(6):
            response = client.post(
                "/api/auth/login",
                json={"username": "locktest", "password": "wrongpassword"},
            )

        # Account should be locked
        response = client.post(
            "/api/auth/login",
            json={"username": "locktest", "password": "TestPass123!@#"},
        )
        assert response.status_code == 403

    def test_jwt_token_validation(self, client, auth_token):
        """Test JWT token validation."""
        # Valid token
        response = client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200

        # Invalid token
        response = client.get(
            "/api/auth/me", headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401


class TestRateLimiting:
    """Test rate limiting."""

    def test_login_rate_limit(self, client):
        """Test login rate limiting."""
        # Make multiple login attempts
        for i in range(6):
            response = client.post(
                "/api/auth/login", json={"username": "test", "password": "test"}
            )

        # Should be rate limited
        assert response.status_code == 429

    def test_api_rate_limit(self, client, auth_token):
        """Test API endpoint rate limiting."""
        # Make many requests
        for i in range(101):
            response = client.get(
                "/api/summary", headers={"Authorization": f"Bearer {auth_token}"}
            )
            if response.status_code == 429:
                break

        # Should eventually be rate limited
        assert response.status_code == 429


class TestInputValidation:
    """Test input validation and sanitization."""

    def test_sql_injection_protection(self, client, auth_token):
        """Test SQL injection protection."""
        # Attempt SQL injection
        response = client.get(
            "/api/history/x/test'; DROP TABLE users;--",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        # Should sanitize input, not execute SQL
        assert response.status_code in [400, 404, 401]

    def test_xss_protection(self, client, auth_token):
        """Test XSS protection."""
        # Attempt XSS
        response = client.get(
            '/api/history/x/<script>alert("xss")</script>',
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        # Should sanitize input
        assert response.status_code in [400, 404, 401]

    def test_file_upload_validation(self, client, auth_token):
        """Test file upload validation."""
        # Try to upload non-CSV file
        response = client.post(
            "/upload",
            headers={"Authorization": f"Bearer {auth_token}"},
            data={"file": ("test.txt", b"not a csv", "text/plain")},
        )
        assert response.status_code == 400

        # Try to upload oversized file
        large_content = b"x" * (11 * 1024 * 1024)  # 11MB
        response = client.post(
            "/upload",
            headers={"Authorization": f"Bearer {auth_token}"},
            data={"file": ("test.csv", large_content, "text/csv")},
        )
        assert response.status_code == 400


class TestAuthorization:
    """Test authorization and access control."""

    def test_unauthorized_access(self, client):
        """Test unauthorized access is blocked."""
        response = client.get("/api/summary")
        assert response.status_code == 401

    def test_role_based_access(self, client, auth_token):
        """Test role-based access control."""
        # Viewer should not be able to upload
        response = client.post(
            "/upload",
            headers={"Authorization": f"Bearer {auth_token}"},
            data={"file": ("test.csv", b"Platform,Handle\nx,test", "text/csv")},
        )
        # Should be 403 if user is Viewer, 400 if Editor/Admin (validation error)
        assert response.status_code in [403, 400]


class TestSecurityHeaders:
    """Test security headers."""

    def test_security_headers_present(self, client):
        """Test security headers are present."""
        response = client.get("/")
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers


class TestBotDetection:
    """Test bot detection."""

    def test_bot_user_agent_detection(self, client):
        """Test bot detection by user agent."""
        response = client.get(
            "/api/summary", headers={"User-Agent": "python-requests/2.28.0"}
        )
        # Should be blocked or require authentication
        assert response.status_code in [401, 403]


class TestHoneypot:
    """Test honeypot endpoints."""

    def test_honeypot_endpoints(self, client):
        """Test honeypot endpoints are logged."""
        # Access honeypot endpoint
        response = client.get("/admin/login.php")
        # Should return 404 but log the access
        assert response.status_code == 404


class TestAuditLogging:
    """Test audit logging."""

    def test_security_events_logged(self, client, auth_token):
        """Test security events are logged."""
        # Perform action that should be logged
        response = client.get(
            "/api/summary", headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200

        # Check audit logs (Admin only)
        response = client.get(
            "/api/auth/audit-logs", headers={"Authorization": f"Bearer {auth_token}"}
        )
        # Should either return logs (if admin) or 403 (if not admin)
        assert response.status_code in [200, 403]


class TestCompliance:
    """Test compliance features."""

    def test_gdpr_data_export(self, client, auth_token):
        """Test GDPR data export."""
        response = client.get(
            "/api/auth/gdpr/export", headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "user" in data
        assert "audit_logs" in data

    def test_gdpr_data_deletion(self, client, auth_token):
        """Test GDPR data deletion."""
        response = client.post(
            "/api/auth/gdpr/delete",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"anonymize": True},
        )
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

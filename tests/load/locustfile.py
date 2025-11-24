"""
Load testing suite using Locust.
Tests API endpoints under various load conditions.
"""
from locust import HttpUser, task, between
import random


class SocialMediaScraperUser(HttpUser):
    """Simulates a user interacting with the social media scraper API."""

    wait_time = between(1, 3)  # Wait 1-3 seconds between requests

    def on_start(self):
        """Called when a simulated user starts."""
        # Login to get authentication token
        self.login()

    def login(self):
        """Login and store authentication token."""
        # For load testing, use a test account
        # In production, create dedicated test accounts
        response = self.client.post(
            "/api/auth/login",
            json={"username": "test_user", "password": "test_password"},
        )

        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            # If login fails, continue without auth (some endpoints may work)
            self.token = None
            self.headers = {}

    @task(3)
    def get_summary(self):
        """Get summary of all accounts (most common operation)."""
        self.client.get("/api/summary", headers=self.headers)

    @task(2)
    def get_history(self):
        """Get history for a random account."""
        platforms = ["X", "Instagram", "Facebook", "LinkedIn", "YouTube"]
        handles = ["HHSGov", "test", "example"]

        platform = random.choice(platforms)
        handle = random.choice(handles)

        self.client.get(f"/api/history/{platform}/{handle}", headers=self.headers)

    @task(1)
    def get_grid(self):
        """Get full data grid."""
        self.client.get("/api/grid", headers=self.headers)

    @task(1)
    def get_current_user(self):
        """Get current user info."""
        self.client.get("/api/auth/me", headers=self.headers)

    @task(1)
    def health_check(self):
        """Check system health."""
        self.client.get("/health")


class AnonymousUser(HttpUser):
    """Simulates anonymous/unauthenticated users."""

    wait_time = between(2, 5)

    @task(5)
    def health_check(self):
        """Anonymous users can check health."""
        self.client.get("/health")

    @task(1)
    def try_unauthorized_access(self):
        """Attempt to access protected endpoints (should fail)."""
        self.client.get("/api/summary")  # Should return 401

"""
Locust load testing configuration.

Run with: locust -f locustfile.py
Access web UI at: http://localhost:8089
"""
from locust import HttpUser, task, between
import random


class SocialMediaScraperUser(HttpUser):
    """Simulated user for load testing."""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    
    def on_start(self):
        """Called when a user starts."""
        # Could add authentication here if needed
        pass
    
    @task(3)
    def get_summary(self):
        """Test /api/summary endpoint."""
        self.client.get("/api/summary", name="summary")
    
    @task(2)
    def get_grid(self):
        """Test /api/grid endpoint."""
        self.client.get("/api/grid", name="grid")
    
    @task(1)
    def get_history(self):
        """Test /api/history endpoint."""
        platforms = ['X', 'Instagram', 'Facebook', 'YouTube']
        handles = ['test', 'hhs', 'nih', 'cdc']
        platform = random.choice(platforms)
        handle = random.choice(handles)
        self.client.get(f"/api/history/{platform}/{handle}", name="history")
    
    @task(1)
    def get_download(self):
        """Test /api/download endpoint."""
        self.client.get("/api/download", name="download")
    
    @task(1)
    def get_dashboard(self):
        """Test dashboard page."""
        self.client.get("/", name="dashboard")


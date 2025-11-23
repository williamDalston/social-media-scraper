"""
Configuration for E2E tests.
"""
import pytest
from playwright.sync_api import sync_playwright, Browser

@pytest.fixture(scope="session")
def browser() -> Browser:
    """Create a browser instance for E2E tests."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()

@pytest.fixture
def base_url():
    """Base URL for the application."""
    return "http://localhost:5000"


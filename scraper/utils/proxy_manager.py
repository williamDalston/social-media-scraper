"""
Proxy management for scrapers (optional feature).
"""

import os
import random
import logging
from typing import List, Optional
import requests

logger = logging.getLogger(__name__)


class ProxyManager:
    """
    Manages proxy rotation for scrapers.
    """

    def __init__(self, proxies: Optional[List[str]] = None):
        """
        Initialize proxy manager.

        Args:
            proxies: List of proxy URLs (e.g., ['http://proxy1:8080', 'http://proxy2:8080'])
                     If None, loads from PROXY_LIST environment variable (comma-separated)
        """
        if proxies is None:
            proxy_env = os.getenv("PROXY_LIST", "")
            proxies = [p.strip() for p in proxy_env.split(",") if p.strip()]

        self.proxies = proxies
        self.current_proxy_index = 0
        self.failed_proxies = set()

        if self.proxies:
            logger.info(f"Proxy manager initialized with {len(self.proxies)} proxies")
        else:
            logger.info("Proxy manager initialized without proxies (direct connection)")

    def get_proxy(self) -> Optional[dict]:
        """
        Get the next proxy in rotation.

        Returns:
            Proxy dict for requests library, or None if no proxies available
        """
        if not self.proxies:
            return None

        # Filter out failed proxies
        available_proxies = [p for p in self.proxies if p not in self.failed_proxies]

        if not available_proxies:
            # Reset failed proxies if all are marked as failed
            logger.warning("All proxies marked as failed. Resetting...")
            self.failed_proxies.clear()
            available_proxies = self.proxies

        # Round-robin selection
        proxy = available_proxies[self.current_proxy_index % len(available_proxies)]
        self.current_proxy_index += 1

        return {
            "http": proxy,
            "https": proxy,
        }

    def mark_proxy_failed(self, proxy: Optional[str]):
        """
        Mark a proxy as failed.

        Args:
            proxy: Proxy URL that failed
        """
        if proxy:
            self.failed_proxies.add(proxy)
            logger.warning(f"Marked proxy as failed: {proxy}")

    def test_proxy(self, proxy: str, timeout: int = 5) -> bool:
        """
        Test if a proxy is working.

        Args:
            proxy: Proxy URL to test
            timeout: Timeout in seconds

        Returns:
            True if proxy is working, False otherwise
        """
        try:
            proxies = {"http": proxy, "https": proxy}
            response = requests.get(
                "https://httpbin.org/ip", proxies=proxies, timeout=timeout
            )
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Proxy test failed for {proxy}: {e}")
            return False

    def get_working_proxy(self) -> Optional[dict]:
        """
        Get a working proxy by testing available ones.

        Returns:
            Working proxy dict, or None if none available
        """
        if not self.proxies:
            return None

        # Try each proxy until we find one that works
        for proxy in self.proxies:
            if proxy in self.failed_proxies:
                continue

            if self.test_proxy(proxy):
                return {"http": proxy, "https": proxy}
            else:
                self.mark_proxy_failed(proxy)

        # If all failed, return None (will use direct connection)
        logger.warning("No working proxies found. Using direct connection.")
        return None


# Global proxy manager instance
_proxy_manager: Optional[ProxyManager] = None


def get_proxy_manager() -> ProxyManager:
    """
    Get or create the global proxy manager.

    Returns:
        ProxyManager instance
    """
    global _proxy_manager
    if _proxy_manager is None:
        _proxy_manager = ProxyManager()
    return _proxy_manager

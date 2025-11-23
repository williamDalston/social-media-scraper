"""
Connection pooling for HTTP requests per platform.
"""

import logging
from typing import Dict, Optional
from requests.adapters import HTTPAdapter
from requests.sessions import Session
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class PlatformConnectionPool:
    """
    Manages HTTP connection pools per platform for better performance.
    """
    
    def __init__(self):
        """Initialize connection pool manager."""
        self._pools: Dict[str, Session] = {}
        logger.info("Initialized PlatformConnectionPool")
    
    def get_session(self, platform: str) -> Session:
        """
        Get or create a session for a platform.
        
        Args:
            platform: Platform name
            
        Returns:
            Requests Session with connection pooling
        """
        if platform not in self._pools:
            session = Session()
            
            # Configure retry strategy
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["GET", "POST"]
            )
            
            # Create adapter with connection pooling
            adapter = HTTPAdapter(
                pool_connections=10,  # Number of connection pools to cache
                pool_maxsize=20,  # Maximum number of connections to save in the pool
                max_retries=retry_strategy,
            )
            
            session.mount("http://", adapter)
            session.mount("https://", adapter)
            
            self._pools[platform] = session
            logger.info(f"Created connection pool for {platform}")
        
        return self._pools[platform]
    
    def close_all(self):
        """Close all connection pools."""
        for platform, session in self._pools.items():
            session.close()
            logger.debug(f"Closed connection pool for {platform}")
        self._pools.clear()


# Global connection pool manager
_pool_manager: Optional[PlatformConnectionPool] = None


def get_connection_pool() -> PlatformConnectionPool:
    """Get or create global connection pool manager."""
    global _pool_manager
    if _pool_manager is None:
        _pool_manager = PlatformConnectionPool()
    return _pool_manager


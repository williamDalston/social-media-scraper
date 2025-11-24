"""
Cache warming strategies for pre-populating frequently accessed data.
"""
import logging
from typing import List, Callable, Optional
from datetime import datetime, timedelta
from .redis_client import cache, is_cache_available
from .multi_level import get_multi_cache
from .metrics import get_metrics

logger = logging.getLogger(__name__)


class CacheWarmer:
    """Cache warming utility for pre-populating cache."""

    def __init__(self):
        self.multi_cache = get_multi_cache()
        self.metrics = get_metrics()

    def warm_summary(self, get_summary_func: Callable):
        """Warm summary cache."""
        try:
            logger.info("Warming summary cache...")
            data = get_summary_func()
            if data:
                self.multi_cache.set("summary:latest", data, ttl=300)
                logger.info("Summary cache warmed successfully")
                return True
        except Exception as e:
            logger.error(f"Failed to warm summary cache: {e}")
        return False

    def warm_history(self, platform: str, handle: str, get_history_func: Callable):
        """Warm history cache for specific account."""
        try:
            logger.info(f"Warming history cache for {platform}/{handle}...")
            data = get_history_func(platform, handle)
            if data:
                key = f"history:{platform}:{handle}"
                self.multi_cache.set(key, data, ttl=600)
                logger.info(f"History cache warmed for {platform}/{handle}")
                return True
        except Exception as e:
            logger.error(f"Failed to warm history cache for {platform}/{handle}: {e}")
        return False

    def warm_top_accounts(
        self, accounts: List[dict], get_history_func: Callable, limit: int = 10
    ):
        """Warm cache for top N accounts by followers."""
        try:
            logger.info(f"Warming cache for top {limit} accounts...")
            # Sort by followers (descending)
            sorted_accounts = sorted(
                accounts, key=lambda x: x.get("followers", 0), reverse=True
            )

            warmed = 0
            for account in sorted_accounts[:limit]:
                if self.warm_history(
                    account.get("platform"),
                    account.get("handle"),
                    lambda p, h: get_history_func(p, h),
                ):
                    warmed += 1

            logger.info(f"Warmed cache for {warmed}/{limit} top accounts")
            return warmed
        except Exception as e:
            logger.error(f"Failed to warm top accounts cache: {e}")
        return 0

    def warm_grid_data(self, get_grid_func: Callable, pages: int = 3):
        """Warm grid data cache for first N pages."""
        try:
            logger.info(f"Warming grid cache for first {pages} pages...")
            for page in range(1, pages + 1):
                data = get_grid_func(page=page, per_page=50)
                if data:
                    key = f"grid:page:{page}"
                    self.multi_cache.set(key, data, ttl=300)
            logger.info(f"Grid cache warmed for {pages} pages")
            return True
        except Exception as e:
            logger.error(f"Failed to warm grid cache: {e}")
        return False

    def warm_all(self, warm_functions: dict):
        """
        Warm all caches using provided functions.

        Args:
            warm_functions: Dict with keys like 'summary', 'top_accounts', 'grid'
                          and values as callable functions
        """
        results = {}

        # Warm summary
        if "summary" in warm_functions:
            results["summary"] = self.warm_summary(warm_functions["summary"])

        # Warm top accounts
        if "top_accounts" in warm_functions:
            accounts = warm_functions.get("accounts_list", [])
            if accounts and "history" in warm_functions:
                results["top_accounts"] = self.warm_top_accounts(
                    accounts, warm_functions["history"]
                )

        # Warm grid
        if "grid" in warm_functions:
            results["grid"] = self.warm_grid_data(warm_functions["grid"])

        return results


def warm_cache_on_startup(app, db_session_factory):
    """
    Warm cache on application startup.

    Args:
        app: Flask application
        db_session_factory: Function that returns database session
    """
    try:
        logger.info("Starting cache warming on startup...")
        warmer = CacheWarmer()

        def get_summary():
            from scraper.schema import DimAccount, FactFollowersSnapshot
            from sqlalchemy import func

            session = db_session_factory()
            try:
                latest_date = session.query(
                    func.max(FactFollowersSnapshot.snapshot_date)
                ).scalar()
                if not latest_date:
                    return []

                results = (
                    session.query(DimAccount, FactFollowersSnapshot)
                    .join(FactFollowersSnapshot)
                    .filter(FactFollowersSnapshot.snapshot_date == latest_date)
                    .all()
                )

                return [
                    {
                        "platform": acc.platform,
                        "handle": acc.handle,
                        "followers": snap.followers_count or 0,
                        "engagement": snap.engagements_total or 0,
                        "posts": snap.posts_count or 0,
                    }
                    for acc, snap in results
                ]
            finally:
                session.close()

        def get_history(platform, handle):
            from scraper.schema import DimAccount, FactFollowersSnapshot

            session = db_session_factory()
            try:
                account = (
                    session.query(DimAccount)
                    .filter_by(platform=platform, handle=handle)
                    .first()
                )
                if not account:
                    return None

                history = (
                    session.query(FactFollowersSnapshot)
                    .filter_by(account_key=account.account_key)
                    .order_by(FactFollowersSnapshot.snapshot_date)
                    .all()
                )

                return {
                    "dates": [h.snapshot_date.isoformat() for h in history],
                    "followers": [h.followers_count or 0 for h in history],
                    "engagement": [h.engagements_total or 0 for h in history],
                }
            finally:
                session.close()

        # Warm summary
        summary_data = get_summary()
        warmer.warm_summary(lambda: summary_data)

        # Warm top accounts
        if summary_data:
            warmer.warm_top_accounts(
                summary_data, get_history, limit=5  # Warm top 5 accounts
            )

        logger.info("Cache warming completed")
    except Exception as e:
        logger.error(f"Cache warming failed: {e}", exc_info=True)


# Global warmer instance
_warmer = None


def get_warmer() -> CacheWarmer:
    """Get or create global cache warmer instance."""
    global _warmer
    if _warmer is None:
        _warmer = CacheWarmer()
    return _warmer

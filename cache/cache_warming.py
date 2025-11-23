"""
Cache warming strategies for critical data.
Pre-populates cache with frequently accessed data.
"""
import logging
from typing import List, Callable, Optional
from datetime import datetime, timedelta
from cache.multilevel_cache import get_multilevel_cache

logger = logging.getLogger(__name__)

class CacheWarmer:
    """Manages cache warming for critical data."""
    
    def __init__(self):
        self.warming_tasks: List[Callable] = []
        self.last_warmed = {}
    
    def register_warming_task(self, task: Callable, name: str, interval_minutes: int = 5):
        """Register a cache warming task."""
        self.warming_tasks.append({
            'task': task,
            'name': name,
            'interval': interval_minutes,
            'last_run': None
        })
        logger.info(f"Registered cache warming task: {name}")
    
    def warm_cache(self, task_name: Optional[str] = None):
        """Warm cache for all tasks or specific task."""
        cache = get_multilevel_cache()
        
        tasks_to_run = self.warming_tasks
        if task_name:
            tasks_to_run = [t for t in self.warming_tasks if t['name'] == task_name]
        
        for task_info in tasks_to_run:
            try:
                task = task_info['task']
                name = task_info['name']
                
                # Check if we need to run (based on interval)
                last_run = task_info.get('last_run')
                interval = timedelta(minutes=task_info['interval'])
                
                if last_run and datetime.utcnow() - last_run < interval:
                    logger.debug(f"Skipping {name} - not yet due")
                    continue
                
                logger.info(f"Warming cache: {name}")
                start_time = datetime.utcnow()
                
                # Execute warming task
                task()
                
                task_info['last_run'] = datetime.utcnow()
                duration = (datetime.utcnow() - start_time).total_seconds()
                logger.info(f"Cache warming completed: {name} (took {duration:.2f}s)")
                
            except Exception as e:
                logger.error(f"Cache warming failed for {task_info['name']}: {e}")
    
    def warm_all(self):
        """Warm all registered caches."""
        logger.info("Starting cache warming for all tasks")
        self.warm_cache()
        logger.info("Cache warming completed")

# Global cache warmer instance
_cache_warmer = CacheWarmer()

def get_cache_warmer() -> CacheWarmer:
    """Get global cache warmer instance."""
    return _cache_warmer

def warm_summary_cache():
    """Warm the summary cache."""
    from app import get_db_session
    from scraper.schema import DimAccount, FactFollowersSnapshot
    
    session = get_db_session()
    try:
        # Get latest snapshot date
        latest_date = session.query(FactFollowersSnapshot.snapshot_date).order_by(
            FactFollowersSnapshot.snapshot_date.desc()
        ).first()
        
        if latest_date:
            latest_date = latest_date[0]
            # Query will be cached when accessed
            results = session.query(DimAccount, FactFollowersSnapshot).join(
                FactFollowersSnapshot
            ).filter(
                FactFollowersSnapshot.snapshot_date == latest_date
            ).all()
            
            # Access the data to trigger caching
            _ = [r for r in results]
    finally:
        session.close()

def warm_account_list_cache():
    """Warm the account list cache."""
    from app import get_db_session
    from scraper.schema import DimAccount
    
    session = get_db_session()
    try:
        accounts = session.query(DimAccount).all()
        # Access to trigger caching
        _ = [acc for acc in accounts]
    finally:
        session.close()

# Register default warming tasks
def register_default_warming_tasks():
    """Register default cache warming tasks."""
    warmer = get_cache_warmer()
    warmer.register_warming_task(warm_summary_cache, "summary", interval_minutes=5)
    warmer.register_warming_task(warm_account_list_cache, "account_list", interval_minutes=10)


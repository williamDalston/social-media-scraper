"""
Log retention policy management.
Handles log file rotation, cleanup, and retention policies.
"""
import os
import logging
import glob
from typing import List, Optional
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class LogRetentionPolicy:
    """Manages log retention policies."""
    
    def __init__(self, log_directory: str = 'logs', 
                 max_file_size_mb: int = 100,
                 max_files: int = 10,
                 retention_days: int = 30):
        self.log_directory = Path(log_directory)
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self.max_files = max_files
        self.retention_days = retention_days
        self.log_directory.mkdir(parents=True, exist_ok=True)
    
    def cleanup_old_logs(self) -> int:
        """
        Remove log files older than retention period.
        
        Returns:
            Number of files deleted
        """
        if not self.log_directory.exists():
            return 0
        
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        deleted_count = 0
        
        for log_file in self.log_directory.glob('*.log*'):
            try:
                file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_mtime < cutoff_date:
                    log_file.unlink()
                    deleted_count += 1
                    logger.info(f"Deleted old log file: {log_file}")
            except Exception as e:
                logger.error(f"Error deleting log file {log_file}: {e}")
        
        return deleted_count
    
    def enforce_file_count_limit(self) -> int:
        """
        Enforce maximum number of log files.
        
        Returns:
            Number of files deleted
        """
        if not self.log_directory.exists():
            return 0
        
        log_files = sorted(
            self.log_directory.glob('*.log*'),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )
        
        deleted_count = 0
        if len(log_files) > self.max_files:
            for log_file in log_files[self.max_files:]:
                try:
                    log_file.unlink()
                    deleted_count += 1
                    logger.info(f"Deleted log file to enforce limit: {log_file}")
                except Exception as e:
                    logger.error(f"Error deleting log file {log_file}: {e}")
        
        return deleted_count
    
    def get_log_files(self) -> List[dict]:
        """
        Get list of log files with metadata.
        
        Returns:
            List of dictionaries with file information
        """
        if not self.log_directory.exists():
            return []
        
        log_files = []
        for log_file in self.log_directory.glob('*.log*'):
            try:
                stat = log_file.stat()
                log_files.append({
                    'name': log_file.name,
                    'path': str(log_file),
                    'size_mb': stat.st_size / (1024 * 1024),
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'age_days': (datetime.now() - datetime.fromtimestamp(stat.st_mtime)).days
                })
            except Exception as e:
                logger.error(f"Error getting info for {log_file}: {e}")
        
        return sorted(log_files, key=lambda x: x['modified'], reverse=True)
    
    def get_total_log_size_mb(self) -> float:
        """
        Get total size of all log files in MB.
        
        Returns:
            Total size in MB
        """
        if not self.log_directory.exists():
            return 0.0
        
        total_size = 0
        for log_file in self.log_directory.glob('*.log*'):
            try:
                total_size += log_file.stat().st_size
            except Exception as e:
                logger.error(f"Error getting size for {log_file}: {e}")
        
        return total_size / (1024 * 1024)
    
    def apply_retention_policy(self) -> dict:
        """
        Apply all retention policies.
        
        Returns:
            Dictionary with cleanup results
        """
        old_logs_deleted = self.cleanup_old_logs()
        excess_files_deleted = self.enforce_file_count_limit()
        total_size_mb = self.get_total_log_size_mb()
        
        return {
            'old_logs_deleted': old_logs_deleted,
            'excess_files_deleted': excess_files_deleted,
            'total_files_deleted': old_logs_deleted + excess_files_deleted,
            'total_log_size_mb': round(total_size_mb, 2),
            'retention_days': self.retention_days,
            'max_files': self.max_files,
            'timestamp': datetime.utcnow().isoformat()
        }


def get_log_retention_policy() -> LogRetentionPolicy:
    """Get or create log retention policy from environment."""
    import os
    
    return LogRetentionPolicy(
        log_directory=os.getenv('LOG_DIRECTORY', 'logs'),
        max_file_size_mb=int(os.getenv('LOG_MAX_FILE_SIZE_MB', '100')),
        max_files=int(os.getenv('LOG_MAX_FILES', '10')),
        retention_days=int(os.getenv('LOG_RETENTION_DAYS', '30'))
    )


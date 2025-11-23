"""
Job tracking model for Celery tasks.
"""
import json
from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Index
from scraper.schema import Base
from datetime import datetime

class Job(Base):
    """Model for tracking background job status and progress."""
    __tablename__ = 'job'
    
    id = Column(Integer, primary_key=True)
    job_id = Column(String, unique=True, nullable=False, index=True)  # Celery task ID
    job_type = Column(String, nullable=False, index=True)  # scrape_all, scrape_account, scrape_platform, backfill_account
    status = Column(String, nullable=False, default='pending', index=True)  # pending, running, completed, failed, cancelled
    progress = Column(Float, default=0.0)  # Percentage 0-100
    result = Column(Text)  # JSON result data
    error_message = Column(Text)  # Error message if failed
    account_key = Column(Integer, index=True)  # Associated account if applicable
    platform = Column(String, index=True)  # Platform if applicable
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Composite indexes for common queries
    __table_args__ = (
        Index('ix_job_status_created', 'status', 'created_at'),
        Index('ix_job_type_status', 'job_type', 'status'),
    )
    
    def __repr__(self):
        return f"<Job(job_id='{self.job_id}', type='{self.job_type}', status='{self.status}')>"
    
    def to_dict(self):
        """Convert job to dictionary for API responses."""
        result_data = None
        if self.result:
            try:
                result_data = json.loads(self.result)
            except (json.JSONDecodeError, TypeError):
                result_data = self.result
        
        return {
            'id': self.id,
            'job_id': self.job_id,
            'job_type': self.job_type,
            'status': self.status,
            'progress': round(self.progress, 2) if self.progress else 0.0,
            'result': result_data,
            'error_message': self.error_message,
            'account_key': self.account_key,
            'platform': self.platform,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }


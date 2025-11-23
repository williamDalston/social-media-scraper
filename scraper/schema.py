from sqlalchemy import create_engine, Column, Integer, String, Boolean, Date, DateTime, ForeignKey, Float, Text
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class DimAccount(Base):
    __tablename__ = 'dim_account'

    account_key = Column(Integer, primary_key=True)
    platform = Column(String, nullable=False) # x, instagram, tiktok, youtube, truth_social
    handle = Column(String, nullable=False)
    account_id = Column(String) # Platform internal ID
    account_display_name = Column(String)
    account_url = Column(String)
    org_id = Column(String) # HHS, NIH, CDC, etc.
    org_name = Column(String)
    owner_team = Column(String) # ASPA_DCD, DIG_ANALYT, etc.
    is_core_account = Column(Boolean, default=False)
    account_type = Column(String) # official dept, sub-brand, campaign, leader/personal
    
    # Risk/Governance
    is_leader_account = Column(Boolean, default=False)
    requires_preclearance = Column(Boolean, default=False)
    sensitivity_level = Column(String) # Low/Medium/High

    # Platform specific extras (stored as JSON or separate columns if critical)
    verified_status = Column(String) # X: None, Blue, Org, Gov

    def __repr__(self):
        return f"<DimAccount(platform='{self.platform}', handle='{self.handle}')>"

class FactFollowersSnapshot(Base):
    __tablename__ = 'fact_followers_snapshot'

    snapshot_id = Column(Integer, primary_key=True)
    account_key = Column(Integer, ForeignKey('dim_account.account_key'), nullable=False)
    snapshot_date = Column(Date, nullable=False)
    
    followers_count = Column(Integer)
    following_count = Column(Integer)
    listed_count = Column(Integer) # X
    subscribers_count = Column(Integer) # YouTube
    
    # Activity metrics (daily grain)
    posts_count = Column(Integer) # New posts today
    stories_count = Column(Integer)
    videos_count = Column(Integer)
    live_streams_count = Column(Integer)

    # Engagement Summary (daily grain)
    likes_count = Column(Integer)
    comments_count = Column(Integer)
    shares_count = Column(Integer)
    video_views = Column(Integer)
    engagements_total = Column(Integer)

    account = relationship("DimAccount")

class FactSocialPost(Base):
    __tablename__ = 'fact_social_post'

    post_key = Column(Integer, primary_key=True)
    account_key = Column(Integer, ForeignKey('dim_account.account_key'), nullable=False)
    platform = Column(String)
    post_id = Column(String, nullable=False) # Platform ID
    post_url = Column(String)
    post_datetime_utc = Column(DateTime)
    post_type = Column(String) # text, image, video, etc.
    caption_text = Column(Text)
    hashtags = Column(Text)
    mentions = Column(Text)
    
    # Flags
    is_reply = Column(Boolean, default=False)
    is_retweet = Column(Boolean, default=False)
    
    # Metrics
    likes_count = Column(Integer)
    comments_count = Column(Integer)
    shares_count = Column(Integer)
    views_count = Column(Integer)
    impressions = Column(Integer)
    clicks = Column(Integer)

    # Content Classification
    topic_primary = Column(String)
    topic_secondary = Column(String)
    priority_area = Column(String)
    tone = Column(String)
    
    # Risk
    has_sensitive_topic_flag = Column(Boolean, default=False)
    fact_checked = Column(Boolean, default=False)

    account = relationship("DimAccount")

# Import Job model to ensure it's included in schema
def init_db(db_path='social_media.db'):
    # Import Job model to register it with Base
    from models.job import Job  # noqa: F401
    
    # Configure connection for SQLite
    # SQLite doesn't support connection pooling like PostgreSQL/MySQL
    # Use NullPool for SQLite to avoid connection issues
    from sqlalchemy.pool import NullPool
    engine = create_engine(
        f'sqlite:///{db_path}',
        poolclass=NullPool,  # Use NullPool for SQLite
        connect_args={
            'check_same_thread': False,  # Allow multi-threaded access
            'timeout': 20  # Connection timeout in seconds
        },
        echo=False  # Set to True for SQL query logging in development
    )
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    # Add indexes if they don't exist
    _ensure_indexes(engine, db_path)
    
    return engine

def _ensure_indexes(engine, db_path):
    """
    Ensure database indexes exist for performance optimization.
    """
    import sqlite3
    
    # Get raw connection for index creation
    conn = engine.raw_connection()
    cursor = conn.cursor()
    
    indexes = [
        # DimAccount indexes
        ("CREATE INDEX IF NOT EXISTS ix_dim_account_platform ON dim_account(platform)",),
        ("CREATE INDEX IF NOT EXISTS ix_dim_account_handle ON dim_account(handle)",),
        ("CREATE INDEX IF NOT EXISTS ix_dim_account_platform_handle ON dim_account(platform, handle)",),
        
        # FactFollowersSnapshot indexes
        ("CREATE INDEX IF NOT EXISTS ix_fact_snapshot_account_key ON fact_followers_snapshot(account_key)",),
        ("CREATE INDEX IF NOT EXISTS ix_fact_snapshot_snapshot_date ON fact_followers_snapshot(snapshot_date)",),
        ("CREATE INDEX IF NOT EXISTS ix_fact_snapshot_account_date ON fact_followers_snapshot(account_key, snapshot_date)",),
        
        # FactSocialPost indexes (if table exists)
        ("CREATE INDEX IF NOT EXISTS ix_fact_post_account_key ON fact_social_post(account_key)",),
        ("CREATE INDEX IF NOT EXISTS ix_fact_post_datetime ON fact_social_post(post_datetime_utc)",),
        ("CREATE INDEX IF NOT EXISTS ix_fact_post_account_datetime ON fact_social_post(account_key, post_datetime_utc)",),
        
        # Job table indexes
        ("CREATE INDEX IF NOT EXISTS ix_job_status ON job(status)",),
        ("CREATE INDEX IF NOT EXISTS ix_job_job_type ON job(job_type)",),
        ("CREATE INDEX IF NOT EXISTS ix_job_created_at ON job(created_at)",),
        ("CREATE INDEX IF NOT EXISTS ix_job_account_key ON job(account_key)",),
        ("CREATE INDEX IF NOT EXISTS ix_job_platform ON job(platform)",),
        ("CREATE INDEX IF NOT EXISTS ix_job_status_created ON job(status, created_at)",),
        ("CREATE INDEX IF NOT EXISTS ix_job_type_status ON job(job_type, status)",),
    ]
    
    for index_sql, in indexes:
        try:
            cursor.execute(index_sql)
        except sqlite3.OperationalError:
            # Table might not exist yet, skip silently
            pass
    
    conn.commit()
    conn.close()

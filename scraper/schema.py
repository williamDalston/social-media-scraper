print(">>> [schema.py] USING NEW FIXED VERSION – 2025-01-24 <<<", flush=True)

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
    is_active = Column(Boolean, default=True)  # Whether account should be scraped
    
    # Risk/Governance
    is_leader_account = Column(Boolean, default=False)
    requires_preclearance = Column(Boolean, default=False)
    sensitivity_level = Column(String) # Low/Medium/High

    # Platform specific extras (stored as JSON or separate columns if critical)
    verified_status = Column(String) # X: None, Blue, Org, Gov
    
    # Account metadata
    account_created_date = Column(Date)  # When account was created
    account_category = Column(String)  # Platform-specific category (e.g., Government, Organization)
    bio_text = Column(Text)  # Account bio/description
    bio_link = Column(String)  # Link in bio (Instagram, X, etc.)
    profile_image_url = Column(String)  # Profile picture URL

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
    
    # Calculated metrics (computed from raw data)
    engagement_rate = Column(Float)  # (engagements / followers) * 100
    follower_growth_rate = Column(Float)  # Daily/weekly growth %
    follower_growth_absolute = Column(Integer)  # Net follower change
    posts_per_day = Column(Float)  # Average posting frequency
    
    # Video-specific metrics (YouTube)
    total_video_views = Column(Integer)  # Lifetime video views (YouTube)
    average_views_per_video = Column(Float)  # Calculated: total_views / video_count

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

# Module-level test to verify the file is being loaded
import sys
sys.stderr.write("[SCHEMA.PY] Module loaded successfully\n")
sys.stderr.flush()

def _construct_sqlite_url(db_path: str) -> str:
    """
    Construct a valid SQLite URL from a database path.
    
    Args:
        db_path: Database path (can be relative, absolute, or already a SQLite URL)
        
    Returns:
        Valid SQLite URL string in the format sqlite:///path
    """
    import os
    from sqlalchemy.engine.url import URL as SQLAlchemyURL, make_url
    
    # If already a valid SQLite URL, validate and return
    if db_path.startswith('sqlite:///'):
        # Validate it's a proper URL
        try:
            make_url(db_path)
            return db_path
        except Exception:
            pass  # Fall through to reconstruction
    elif db_path.startswith('sqlite://'):
        # Missing third slash - fix it
        fixed = db_path.replace('sqlite://', 'sqlite:///', 1)
        try:
            make_url(fixed)
            return fixed
        except Exception:
            pass  # Fall through to reconstruction
    
    # Convert to absolute path and use SQLAlchemy's URL.create() for reliability
    try:
        if os.path.isabs(db_path):
            abs_path = os.path.normpath(db_path).replace('\\', '/')
        else:
            abs_path = os.path.abspath(db_path).replace('\\', '/')
        
        # Use SQLAlchemy's URL.create() which handles the format correctly
        sqlite_url_obj = SQLAlchemyURL.create(
            drivername='sqlite',
            database=abs_path
        )
        sqlite_url = str(sqlite_url_obj)
        
        # Validate the constructed URL
        make_url(sqlite_url)
        return sqlite_url
    except Exception:
        # Fallback: simple relative path format
        normalized = db_path.replace('\\', '/').lstrip('/')
        sqlite_url = f'sqlite:///{normalized}'
        
        # Validate fallback URL
        try:
            make_url(sqlite_url)
            return sqlite_url
        except Exception as e:
            raise ValueError(
                f"Failed to construct valid SQLite URL from '{db_path}'. "
                f"Error: {e}"
            ) from e

def init_db(db_path=None, enable_profiling: bool = False):
    """
    Initialize database with optimized connection pooling.
    
    Args:
        db_path: Database path or connection string
            - SQLite: 'social_media.db', 'sqlite:///path/to.db', or 'sqlite:///./relative.db'
            - PostgreSQL: 'postgresql://user:pass@host:port/db'
            - MySQL: 'mysql://user:pass@host:port/db'
            - If None, uses DATABASE_URL env var or defaults to 'sqlite:///social_media.db'
        enable_profiling: Enable query profiling
        
    Returns:
        SQLAlchemy engine
        
    Raises:
        ValueError: If db_path is invalid or cannot be parsed
    """
    import os
    import sys
    from sqlalchemy import create_engine
    from sqlalchemy.pool import NullPool, QueuePool
    from sqlalchemy.engine.url import make_url
    
    # Step 1: Determine the database URL
    # Priority: db_path argument > DATABASE_URL env var > default SQLite
    if db_path:
        # db_path was explicitly provided - use it
        url = str(db_path).strip()
        if not url:
            raise ValueError("db_path cannot be empty")
        
        # If it's a plain filename ending in .db, construct SQLite URL
        if url.endswith('.db') and not url.startswith(('sqlite://', 'postgresql://', 'mysql://')):
            # Use helper function to construct valid SQLite URL
            url = _construct_sqlite_url(url)
        elif not url.startswith(('sqlite://', 'postgresql://', 'mysql://')):
            # No URL scheme and not .db - assume SQLite with relative path
            url = _construct_sqlite_url(url)
    else:
        # No db_path provided - check environment variable
        url = os.getenv("DATABASE_URL")
        if not url or not url.strip():
            # No DATABASE_URL set - use sensible SQLite default
            url = _construct_sqlite_url("social_media.db")
        else:
            url = url.strip()
    
    # Step 2: Validate the URL before creating engine
    if not url or not url.strip():
        raise ValueError("Database URL is empty or invalid")
    
    # Try to parse the URL to catch errors early
    try:
        parsed_url = make_url(url)
        print(f"Using database URL: {parsed_url}", file=sys.stderr, flush=True)
    except Exception as url_error:
        raise ValueError(f"Could not parse database URL '{url}': {url_error}") from url_error
    
    # Step 3: Determine database type and create appropriate engine
    is_sqlite = url.startswith('sqlite://')
    is_production = url.startswith(('postgresql://', 'mysql://'))
    
    try:
        if is_sqlite:
            # SQLite configuration
            engine = create_engine(
                url,
                poolclass=NullPool,
                connect_args={
                    'check_same_thread': False,
                    'timeout': 20
                },
                echo=False,
                future=True
            )
        elif is_production:
            # Production database (PostgreSQL/MySQL) configuration
            try:
                from config.performance_tuning import PerformanceTuner
                tuner = PerformanceTuner()
                pool_config = tuner.optimize_database_connections()
                engine = create_engine(
                    url,
                    poolclass=QueuePool,
                    future=True,
                    **pool_config
                )
            except ImportError:
                # PerformanceTuner not available - use default config
                engine = create_engine(
                    url,
                    poolclass=QueuePool,
                    future=True
                )
        else:
            raise ValueError(
                f"Unrecognized database URL format: {url}. "
                "Supported formats: sqlite:///path, postgresql://..., mysql://..."
            )
    except Exception as e:
        raise ValueError(f"Failed to create database engine with URL '{url}': {e}") from e
    
    # Step 4: Import Job model to ensure it's registered
    try:
        from models.job import Job  # noqa: F401
    except ImportError:
        pass  # Job model might not exist in all setups
    
    # Step 5: Set up query monitoring if profiling enabled
    if enable_profiling:
        try:
            from config.database_performance import setup_query_monitoring
            setup_query_monitoring(engine)
        except Exception:
            pass
        try:
            from scraper.utils.query_profiler import setup_query_listening
            setup_query_listening(engine)
        except Exception:
            pass
    
    # Step 6: Create all tables
    Base.metadata.create_all(engine)
    
    # Step 7: Add indexes for SQLite databases
    if is_sqlite:
        _ensure_indexes(engine, url)
    
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
        ("CREATE INDEX IF NOT EXISTS ix_dim_account_org_name ON dim_account(org_name)",),
        ("CREATE INDEX IF NOT EXISTS ix_dim_account_is_core ON dim_account(is_core_account)",),
        ("CREATE INDEX IF NOT EXISTS ix_dim_account_platform_core ON dim_account(platform, is_core_account)",),
        
        # FactFollowersSnapshot indexes
        ("CREATE INDEX IF NOT EXISTS ix_fact_snapshot_account_key ON fact_followers_snapshot(account_key)",),
        ("CREATE INDEX IF NOT EXISTS ix_fact_snapshot_snapshot_date ON fact_followers_snapshot(snapshot_date)",),
        ("CREATE INDEX IF NOT EXISTS ix_fact_snapshot_account_date ON fact_followers_snapshot(account_key, snapshot_date)",),
        ("CREATE INDEX IF NOT EXISTS ix_fact_snapshot_date_desc ON fact_followers_snapshot(snapshot_date DESC)",),
        ("CREATE INDEX IF NOT EXISTS ix_fact_snapshot_followers ON fact_followers_snapshot(followers_count)",),
        ("CREATE INDEX IF NOT EXISTS ix_fact_snapshot_engagement ON fact_followers_snapshot(engagements_total)",),
        ("CREATE INDEX IF NOT EXISTS ix_fact_snapshot_engagement_rate ON fact_followers_snapshot(engagement_rate)",),
        ("CREATE INDEX IF NOT EXISTS ix_fact_snapshot_growth_rate ON fact_followers_snapshot(follower_growth_rate)",),
        
        # DimAccount indexes for new fields
        ("CREATE INDEX IF NOT EXISTS ix_dim_account_created_date ON dim_account(account_created_date)",),
        ("CREATE INDEX IF NOT EXISTS ix_dim_account_category ON dim_account(account_category)",),
        
        # FactSocialPost indexes (if table exists)
        ("CREATE INDEX IF NOT EXISTS ix_fact_post_account_key ON fact_social_post(account_key)",),
        ("CREATE INDEX IF NOT EXISTS ix_fact_post_datetime ON fact_social_post(post_datetime_utc)",),
        ("CREATE INDEX IF NOT EXISTS ix_fact_post_account_datetime ON fact_social_post(account_key, post_datetime_utc)",),
        ("CREATE INDEX IF NOT EXISTS ix_fact_post_platform ON fact_social_post(platform)",),
        ("CREATE INDEX IF NOT EXISTS ix_fact_post_datetime_desc ON fact_social_post(post_datetime_utc DESC)",),
        
        # Job table indexes
        ("CREATE INDEX IF NOT EXISTS ix_job_status ON job(status)",),
        ("CREATE INDEX IF NOT EXISTS ix_job_job_type ON job(job_type)",),
        ("CREATE INDEX IF NOT EXISTS ix_job_created_at ON job(created_at)",),
        ("CREATE INDEX IF NOT EXISTS ix_job_account_key ON job(account_key)",),
        ("CREATE INDEX IF NOT EXISTS ix_job_platform ON job(platform)",),
        ("CREATE INDEX IF NOT EXISTS ix_job_status_created ON job(status, created_at)",),
        ("CREATE INDEX IF NOT EXISTS ix_job_type_status ON job(job_type, status)",),
        ("CREATE INDEX IF NOT EXISTS ix_job_created_desc ON job(created_at DESC)",),
    ]
    
    for index_sql, in indexes:
        try:
            cursor.execute(index_sql)
        except sqlite3.OperationalError:
            # Table might not exist yet, skip silently
            pass
    
    conn.commit()
    conn.close()

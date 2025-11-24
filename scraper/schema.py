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

def init_db(db_path='social_media.db', enable_profiling: bool = False):
    """
    Initialize database with optimized connection pooling.
    
    Args:
        db_path: Database path or connection string
            - SQLite: 'social_media.db', 'sqlite:///path/to.db', or 'sqlite:///./relative.db'
            - PostgreSQL: 'postgresql://user:pass@host:port/db'
            - MySQL: 'mysql://user:pass@host:port/db'
        enable_profiling: Enable query profiling
        
    Returns:
        SQLAlchemy engine
        
    Raises:
        ValueError: If db_path is invalid or cannot be parsed
    """
    # ============================================================================
    # ULTIMATE FIRST CHECK - This MUST be the very first thing that happens
    # ============================================================================
    # Convert to string and check for .db extension BEFORE any imports
    # This prevents ANY possibility of the path being misidentified
    import sys
    import os
    
    # Force stderr output immediately
    sys.stderr.write(f"[INIT_DB] Function called with db_path='{db_path}' (type: {type(db_path).__name__})\n")
    sys.stderr.flush()
    
    # Convert to string safely
    try:
        db_path_str = str(db_path).strip() if db_path else ''
    except Exception as conv_error:
        sys.stderr.write(f"[INIT_DB] Error converting db_path to string: {conv_error}\n")
        sys.stderr.flush()
        db_path_str = ''
    
    # SIMPLEST POSSIBLE CHECK - just look for .db at the end (case insensitive)
    is_db_file = False
    if db_path_str:
        db_lower = db_path_str.lower()
        is_db_file = db_lower.endswith('.db')
        sys.stderr.write(f"[INIT_DB] Checking .db: db_path_str='{db_path_str}', is_db_file={is_db_file}\n")
        sys.stderr.flush()
    
    if is_db_file:
        # This is a .db file - handle as SQLite immediately
        sys.stderr.write(f"[INIT_DB ULTIMATE] DETECTED .db FILE: '{db_path_str}' - Handling as SQLite\n")
        sys.stderr.flush()
        
        # Now import what we need
        from sqlalchemy import create_engine
        from sqlalchemy.pool import NullPool
        
        # Construct SQLite URL
        if db_path_str.startswith('sqlite:///'):
            sqlite_url = db_path_str
        elif db_path_str.startswith('sqlite://'):
            sqlite_url = db_path_str.replace('sqlite://', 'sqlite:///', 1)
        else:
            # Make absolute and normalize - be very careful here
            try:
                # Get current working directory
                cwd = os.getcwd()
                sys.stderr.write(f"[INIT_DB ULTIMATE] CWD: '{cwd}'\n")
                sys.stderr.flush()
                
                # Make absolute path
                if os.path.isabs(db_path_str):
                    abs_path = db_path_str
                else:
                    abs_path = os.path.abspath(db_path_str)
                
                sys.stderr.write(f"[INIT_DB ULTIMATE] Absolute path: '{abs_path}'\n")
                sys.stderr.flush()
                
                # Normalize path separators - MUST use forward slashes
                # Remove any backslashes first
                normalized = abs_path.replace('\\', '/')
                # Remove double slashes (but preserve sqlite:///)
                while '//' in normalized and not normalized.startswith('sqlite://'):
                    normalized = normalized.replace('//', '/')
                
                sys.stderr.write(f"[INIT_DB ULTIMATE] Normalized path: '{normalized}'\n")
                sys.stderr.flush()
                
                # Construct SQLite URL - ensure it starts with sqlite:///
                if normalized.startswith('/'):
                    # Unix-style absolute path
                    sqlite_url = f'sqlite://{normalized}'
                else:
                    # Relative or Windows path
                    sqlite_url = f'sqlite:///{normalized}'
                    
            except Exception as path_error:
                sys.stderr.write(f"[INIT_DB ULTIMATE] Path normalization error: {path_error}\n")
                sys.stderr.flush()
                # Ultimate fallback - use the string as-is with sqlite:/// prefix
                simple_path = db_path_str.replace('\\', '/').replace('//', '/')
                sqlite_url = f'sqlite:///{simple_path}'
        
        sys.stderr.write(f"[INIT_DB ULTIMATE] SQLite URL before validation: '{sqlite_url}'\n")
        sys.stderr.flush()
        
        # CRITICAL VALIDATION: Ensure URL is in correct format
        # SQLite URLs must be: sqlite:///path or sqlite:///./path or sqlite:////absolute/path
        if not sqlite_url.startswith('sqlite://'):
            # Completely wrong - rebuild from scratch
            sys.stderr.write(f"[INIT_DB ULTIMATE] URL doesn't start with sqlite://, rebuilding...\n")
            sys.stderr.flush()
            simple = db_path_str.replace('\\', '/')
            sqlite_url = f'sqlite:///{simple}'
        elif sqlite_url.startswith('sqlite://') and not sqlite_url.startswith('sqlite:///'):
            # Missing the third slash
            sqlite_url = sqlite_url.replace('sqlite://', 'sqlite:///', 1)
        
        # Final validation
        if not sqlite_url.startswith('sqlite:///'):
            # Last resort - just prepend sqlite:/// to the original string
            sys.stderr.write(f"[INIT_DB ULTIMATE] Final validation failed, using last resort...\n")
            sys.stderr.flush()
            sqlite_url = f'sqlite:///{db_path_str}'
        
        sys.stderr.write(f"[INIT_DB ULTIMATE] Final validated SQLite URL: '{sqlite_url}'\n")
        sys.stderr.flush()
        
        # One more check - ensure URL is not empty and is a string
        if not sqlite_url or not isinstance(sqlite_url, str):
            raise ValueError(f"Invalid SQLite URL after all fixes: '{sqlite_url}' (type: {type(sqlite_url).__name__})")
        
        # Ensure it's at least 11 characters (sqlite:/// + something)
        if len(sqlite_url) < 11:
            raise ValueError(f"SQLite URL too short: '{sqlite_url}'")
        
        # CRITICAL: Validate URL with SQLAlchemy's URL parser BEFORE create_engine
        try:
            from sqlalchemy.engine.url import make_url
            sys.stderr.write(f"[INIT_DB ULTIMATE] Validating URL with SQLAlchemy parser...\n")
            sys.stderr.flush()
            # Try to parse the URL - this will raise an error if invalid
            parsed_url = make_url(sqlite_url)
            sys.stderr.write(f"[INIT_DB ULTIMATE] URL validation SUCCESS: {parsed_url}\n")
            sys.stderr.flush()
        except Exception as url_error:
            sys.stderr.write(f"[INIT_DB ULTIMATE] URL validation FAILED: {url_error}\n")
            sys.stderr.write(f"[INIT_DB ULTIMATE] Invalid URL was: '{sqlite_url}'\n")
            sys.stderr.write(f"[INIT_DB ULTIMATE] Original db_path was: '{db_path_str}'\n")
            sys.stderr.flush()
            # Try to fix it one more time
            if not sqlite_url.startswith('sqlite:///'):
                fixed_url = f'sqlite:///{db_path_str}'
                sys.stderr.write(f"[INIT_DB ULTIMATE] Trying fixed URL: '{fixed_url}'\n")
                sys.stderr.flush()
                try:
                    make_url(fixed_url)
                    sqlite_url = fixed_url
                    sys.stderr.write(f"[INIT_DB ULTIMATE] Fixed URL is valid!\n")
                    sys.stderr.flush()
                except Exception:
                    raise ValueError(
                        f"SQLite URL validation failed. Original: '{db_path_str}', "
                        f"Constructed: '{sqlite_url}', Fixed: '{fixed_url}'. "
                        f"Error: {url_error}"
                    ) from url_error
            else:
                raise ValueError(
                    f"SQLite URL validation failed for: '{sqlite_url}' (from '{db_path_str}'). "
                    f"Error: {url_error}"
                ) from url_error
        
        # Create engine
        try:
            sys.stderr.write(f"[INIT_DB ULTIMATE] Calling create_engine with validated URL: '{sqlite_url}'\n")
            sys.stderr.flush()
            engine = create_engine(
                sqlite_url,
                poolclass=NullPool,
                connect_args={'check_same_thread': False, 'timeout': 20},
                echo=False
            )
            sys.stderr.write(f"[INIT_DB ULTIMATE] create_engine SUCCESS!\n")
            sys.stderr.flush()
            
            # Import Job model
            from models.job import Job  # noqa: F401
            
            # Initialize
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
            
            Base.metadata.create_all(engine)
            _ensure_indexes(engine, db_path_str)
            sys.stderr.write(f"[INIT_DB ULTIMATE] Complete initialization SUCCESS!\n")
            sys.stderr.flush()
            return engine
        except Exception as e:
            sys.stderr.write(f"[INIT_DB ULTIMATE] ERROR in create_engine: {e}\n")
            sys.stderr.flush()
            import traceback
            traceback.print_exc(file=sys.stderr)
            raise ValueError(f"Failed to create SQLite engine (ultimate check) with URL '{sqlite_url}': {e}") from e
    
    # If we get here, it's not a .db file - continue with normal logic
    sys.stderr.write(f"[INIT_DB] Not a .db file, continuing with normal detection\n")
    sys.stderr.flush()
    
    # Now do normal imports and processing
    from sqlalchemy import create_engine
    from sqlalchemy.pool import NullPool, QueuePool
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Continue with normalization and other logic for non-.db files
        print(f"[INIT_DB ULTIMATE CHECK] Detected .db file at START: '{db_path_str}'", file=sys.stderr, flush=True)
        # Construct SQLite URL immediately
        if db_path_str.startswith('sqlite:///'):
            sqlite_url = db_path_str
        elif db_path_str.startswith('sqlite://'):
            sqlite_url = db_path_str.replace('sqlite://', 'sqlite:///', 1)
        else:
            # Make absolute path - handle errors gracefully
            try:
                if not os.path.isabs(db_path_str):
                    abs_path = os.path.abspath(db_path_str)
                else:
                    abs_path = db_path_str
                
                # Validate absolute path
                if not abs_path or not isinstance(abs_path, str):
                    raise ValueError(f"Invalid absolute path: {abs_path}")
                
                # Normalize path separators - ensure forward slashes only
                normalized = abs_path.replace('\\', '/')
                # Remove any double slashes (but keep sqlite:///)
                while '//' in normalized and not normalized.startswith('sqlite:///'):
                    normalized = normalized.replace('//', '/')
                
                # Construct SQLite URL
                sqlite_url = f'sqlite:///{normalized}'
            except Exception as path_error:
                # Ultimate fallback - use the original path as-is
                print(f"[INIT_DB ULTIMATE CHECK] Path normalization failed: {path_error}, using simple URL", file=sys.stderr, flush=True)
                # Just prepend sqlite:/// to the original path
                sqlite_url = f'sqlite:///{db_path_str.replace(os.sep, "/")}'
        
        # CRITICAL: Validate URL format before using
        print(f"[INIT_DB ULTIMATE CHECK] SQLite URL before validation: '{sqlite_url}'", file=sys.stderr, flush=True)
        
        if not sqlite_url:
            raise ValueError("SQLite URL is empty in ultimate check")
        if not isinstance(sqlite_url, str):
            raise ValueError(f"SQLite URL must be a string, got {type(sqlite_url).__name__}")
        if not sqlite_url.startswith('sqlite:///'):
            # Try to fix it
            if sqlite_url.startswith('sqlite://'):
                sqlite_url = sqlite_url.replace('sqlite://', 'sqlite:///', 1)
            else:
                sqlite_url = f'sqlite:///{sqlite_url}'
            print(f"[INIT_DB ULTIMATE CHECK] Fixed SQLite URL: '{sqlite_url}'", file=sys.stderr, flush=True)
        
        # Final validation
        if not sqlite_url.startswith('sqlite:///'):
            raise ValueError(f"Invalid SQLite URL format after fixes: '{sqlite_url}' (original: '{db_path_str}')")
        
        print(f"[INIT_DB ULTIMATE CHECK] Validated SQLite URL: '{sqlite_url}'", file=sys.stderr, flush=True)
        
        # Create engine immediately with comprehensive error handling
        try:
            print(f"[INIT_DB ULTIMATE CHECK] About to call create_engine with: '{sqlite_url}'", file=sys.stderr, flush=True)
            engine = create_engine(
                sqlite_url,
                poolclass=NullPool,
                connect_args={'check_same_thread': False, 'timeout': 20},
                echo=False
            )
            print(f"[INIT_DB ULTIMATE CHECK] create_engine call succeeded!", file=sys.stderr, flush=True)
            print(f"[INIT_DB ULTIMATE CHECK] Engine created successfully!", file=sys.stderr, flush=True)
            
            # Import Job model
            from models.job import Job  # noqa: F401
            
            # Continue with initialization
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
            
            # Base is already defined at module level
            Base.metadata.create_all(engine)
            _ensure_indexes(engine, db_path_str)
            return engine
        except Exception as e:
            print(f"[INIT_DB ULTIMATE CHECK] Error creating engine: {e}", file=sys.stderr, flush=True)
            raise ValueError(f"Failed to create SQLite engine (ultimate check) with URL '{sqlite_url}': {e}") from e
    
    # PREEMPTIVE VALIDATION: Use the normalization utility to catch errors early
    try:
        from scraper.utils.db_path_normalizer import normalize_db_path, validate_sqlite_url
        normalized_path, sqlite_url, is_sqlite = normalize_db_path(db_path)
        
        # Log the normalization result
        print(f"[INIT_DB] Normalized path: '{db_path}' -> is_sqlite={is_sqlite}, sqlite_url='{sqlite_url}'", file=sys.stderr, flush=True)
        logger.info(f"[INIT_DB] Normalized: db_path='{db_path}' -> is_sqlite={is_sqlite}")
        
    except ImportError:
        # Fallback if normalization utility not available
        print(f"[INIT_DB WARNING] db_path_normalizer not available, using fallback logic", file=sys.stderr, flush=True)
        normalized_path = db_path
        sqlite_url = None
        is_sqlite = None  # Will be determined below
    except Exception as norm_error:
        # If normalization fails, log and continue with original path
        print(f"[INIT_DB WARNING] Normalization failed: {norm_error}, using original path", file=sys.stderr, flush=True)
        logger.warning(f"Path normalization failed: {norm_error}")
        normalized_path = db_path
        sqlite_url = None
        is_sqlite = None
    
    # Import Job model to register it with Base
    from models.job import Job  # noqa: F401
    
    # Validate db_path (basic validation)
    if not db_path:
        raise ValueError("Database path cannot be empty or None")
    if not isinstance(db_path, str):
        raise ValueError(f"Database path must be a string, got {type(db_path).__name__}")
    
    db_path = db_path.strip()
    if not db_path:
        raise ValueError("Database path cannot be empty after stripping whitespace")
    
    # CRITICAL SAFETY CHECK: If normalization says it's SQLite, handle it immediately
    if is_sqlite is True and sqlite_url:
        # We already have a validated SQLite URL from normalization
        print(f"[INIT_DB] Using pre-normalized SQLite URL: '{sqlite_url}'", file=sys.stderr, flush=True)
        if not validate_sqlite_url(sqlite_url):
            raise ValueError(f"Normalized SQLite URL is invalid: '{sqlite_url}'")
        
        try:
            engine = create_engine(
                sqlite_url,
                poolclass=NullPool,
                connect_args={
                    'check_same_thread': False,
                    'timeout': 20
                },
                echo=False
            )
            print(f"[INIT_DB] SQLite engine created successfully with URL: '{sqlite_url}'", file=sys.stderr, flush=True)
            
            # Continue with initialization
            if enable_profiling:
                try:
                    from config.database_performance import setup_query_monitoring
                    setup_query_monitoring(engine)
                except Exception as e:
                    logger.warning(f"Could not set up database monitoring: {e}")
                try:
                    from scraper.utils.query_profiler import setup_query_listening
                    setup_query_listening(engine)
                except Exception as e:
                    logger.warning(f"Could not set up query profiling: {e}")
            
            Base.metadata.create_all(engine)
            _ensure_indexes(engine, normalized_path)
            return engine
        except Exception as e:
            raise ValueError(f"Failed to create SQLite engine with pre-normalized URL '{sqlite_url}': {e}") from e
    
    # Fallback detection if normalization didn't work or wasn't available
    # This should rarely be needed, but provides a safety net
    # CRITICAL SAFETY CHECK: If it ends in .db, it's ALWAYS SQLite, no exceptions
    db_path_lower = db_path.lower()
    is_db_file = ('.db' in db_path_lower) and (db_path_lower.endswith('.db'))
    
    # Force check - if it contains .db anywhere, treat as SQLite
    # This is a final safety net in case normalization failed
    if is_db_file or 'social_media.db' in db_path or db_path == 'social_media.db':
        print(f"[INIT_DB FALLBACK] Using fallback .db detection for: '{db_path}'", file=sys.stderr, flush=True)
        # Force SQLite handling - construct URL and return early
        try:
            # Log explicitly to help debug CI/CD issues - do this FIRST
            print(f"[INIT_DB DEBUG] ENTERED .db check block. db_path='{db_path}'", file=sys.stderr, flush=True)
            logger.info(f"[INIT_DB] Force-detected SQLite from .db extension: db_path='{db_path}'")
            
            # Handle both 'sqlite:///' and plain filenames
            if db_path.startswith('sqlite:///'):
                sqlite_url = db_path
            elif db_path.startswith('sqlite://'):
                sqlite_url = db_path.replace('sqlite://', 'sqlite:///', 1)
            else:
                # Convert to absolute path for CI/CD compatibility
                try:
                    if not os.path.isabs(db_path):
                        # Relative path - make it absolute
                        abs_path = os.path.abspath(db_path)
                    else:
                        abs_path = db_path
                    # Ensure proper SQLite URL format with forward slashes
                    # Remove any backslashes and ensure forward slashes
                    normalized_path = abs_path.replace('\\', '/').replace('//', '/')
                    sqlite_url = f'sqlite:///{normalized_path}'
                except Exception as path_error:
                    # Fallback to simple construction if path resolution fails
                    print(f"[INIT_DB DEBUG] Path resolution failed: {path_error}, using simple URL", file=sys.stderr, flush=True)
                    sqlite_url = f'sqlite:///{db_path.replace(os.sep, "/")}'
            
            # Validate URL format before using it
            if not sqlite_url.startswith('sqlite:///'):
                raise ValueError(f"Invalid SQLite URL constructed: '{sqlite_url}' from db_path: '{db_path}'")
            
            print(f"[INIT_DB DEBUG] Constructed SQLite URL: '{sqlite_url}'", file=sys.stderr, flush=True)
            print(f"[INIT_DB DEBUG] About to call create_engine with URL: '{sqlite_url}'", file=sys.stderr, flush=True)
            
            engine = create_engine(
                sqlite_url,
                poolclass=NullPool,
                connect_args={
                    'check_same_thread': False,
                    'timeout': 20
                },
                echo=False
            )
            print(f"[INIT_DB DEBUG] create_engine succeeded!", file=sys.stderr, flush=True)
            # Continue with rest of initialization (tables, indexes, etc.)
            # But skip the detection logic below
            if enable_profiling:
                try:
                    from config.database_performance import setup_query_monitoring
                    setup_query_monitoring(engine)
                except Exception as e:
                    logger.warning(f"Could not set up database monitoring: {e}")
                try:
                    from scraper.utils.query_profiler import setup_query_listening
                    setup_query_listening(engine)
                except Exception as e:
                    logger.warning(f"Could not set up query profiling: {e}")
            
            Base.metadata.create_all(engine)
            _ensure_indexes(engine, db_path)
            return engine
        except Exception as e:
            raise ValueError(f"Failed to create SQLite engine (forced detection) with URL '{sqlite_url}': {e}") from e
    
    # If we get here, it's not a .db file, continue with normal detection
    # Normalize and detect database type with comprehensive validation
    db_path_lower = db_path.lower()
    has_url_scheme = '://' in db_path
    
    # SQLite detection - be very explicit
    # Priority order:
    # 1. Explicitly starts with sqlite://
    # 2. Ends with .db (most common indicator)
    # 3. No URL scheme and doesn't start with postgresql/mysql
    is_sqlite = False
    is_production_db = False
    
    if db_path.startswith('sqlite://'):
        is_sqlite = True
        logger.debug(f"Detected SQLite from explicit sqlite:// prefix: {db_path}")
    elif db_path.endswith('.db'):
        is_sqlite = True
        logger.debug(f"Detected SQLite from .db extension: {db_path}")
    elif db_path.startswith('postgresql://') or db_path.startswith('postgresql+'):
        is_production_db = True
        logger.debug(f"Detected PostgreSQL database: {db_path}")
    elif db_path.startswith('mysql://') or db_path.startswith('mysql+'):
        is_production_db = True
        logger.debug(f"Detected MySQL database: {db_path}")
    elif not has_url_scheme:
        # No URL scheme and not a production DB - assume SQLite
        is_sqlite = True
        logger.debug(f"Detected SQLite from lack of URL scheme: {db_path}")
    else:
        # Has URL scheme but not recognized - error
        raise ValueError(
            f"Unrecognized database URL format: {db_path!r}. "
            "Supported formats:\n"
            "  - SQLite: 'social_media.db', 'sqlite:///path/to.db'\n"
            "  - PostgreSQL: 'postgresql://user:pass@host:port/db'\n"
            "  - MySQL: 'mysql://user:pass@host:port/db'"
        )
    
    # Create engine based on database type
    engine = None
    
    if is_sqlite:
        # SQLite configuration - use NullPool
        # Construct proper SQLite URL
        if db_path.startswith('sqlite:///'):
            sqlite_url = db_path
        elif db_path.startswith('sqlite://'):
            # Handle sqlite:// format (should be sqlite:///)
            sqlite_url = db_path.replace('sqlite://', 'sqlite:///', 1)
        else:
            # Relative or absolute file path - convert to SQLite URL
            sqlite_url = f'sqlite:///{db_path}'
        
        logger.info(f"Creating SQLite engine with URL: {sqlite_url}")
        try:
            engine = create_engine(
                sqlite_url,
                poolclass=NullPool,  # Use NullPool for SQLite
                connect_args={
                    'check_same_thread': False,  # Allow multi-threaded access
                    'timeout': 20  # Connection timeout in seconds
                },
                echo=False  # Set to True for SQL query logging in development
            )
        except Exception as e:
            raise ValueError(
                f"Failed to create SQLite engine with URL '{sqlite_url}': {e}. "
                f"Original db_path: {db_path!r}"
            ) from e
            
    elif is_production_db:
        # Production database configuration - use QueuePool with optimization
        # CRITICAL: Double-check this is actually a production DB URL, not a SQLite file
        if db_path.endswith('.db') or (not '://' in db_path):
            # This should have been caught earlier, but handle it as SQLite anyway
            logger.warning(
                f"Database path '{db_path}' looks like SQLite but was flagged as production DB. "
                "Falling back to SQLite handling."
            )
            # Treat as SQLite
            if db_path.startswith('sqlite:///'):
                sqlite_url = db_path
            elif db_path.startswith('sqlite://'):
                sqlite_url = db_path.replace('sqlite://', 'sqlite:///', 1)
            else:
                sqlite_url = f'sqlite:///{db_path}'
            
            try:
                engine = create_engine(
                    sqlite_url,
                    poolclass=NullPool,
                    connect_args={
                        'check_same_thread': False,
                        'timeout': 20
                    },
                    echo=False
                )
            except Exception as e:
                raise ValueError(f"Failed to create SQLite engine (fallback) with URL '{sqlite_url}': {e}") from e
        else:
            # Validate that db_path looks like a valid database URL
            if not (db_path.startswith('postgresql://') or 
                    db_path.startswith('postgresql+psycopg2://') or
                    db_path.startswith('mysql://') or
                    db_path.startswith('mysql+pymysql://')):
                raise ValueError(
                    f"Invalid production database URL format: {db_path!r}. "
                    "Expected format: postgresql://user:pass@host:port/db or mysql://user:pass@host:port/db"
                )
            
            logger.info(f"Creating production database engine: {db_path[:50]}...")  # Log partial URL for security
            try:
                from config.performance_tuning import PerformanceTuner
                tuner = PerformanceTuner()
                pool_config = tuner.optimize_database_connections()
                
                engine = create_engine(
                    db_path,
                    poolclass=QueuePool,
                    **pool_config
                )
            except ImportError:
                # PerformanceTuner not available - use default config
                logger.warning("PerformanceTuner not available, using default pool configuration")
                engine = create_engine(
                    db_path,
                    poolclass=QueuePool
                )
            except Exception as e:
                raise ValueError(f"Failed to create production database engine with URL '{db_path}': {e}") from e
    else:
        # This should never happen due to validation above, but handle it anyway
        # If we get here, it means the path has a URL scheme we don't recognize
        # But if it ends in .db, treat it as SQLite as a last resort
        if db_path.endswith('.db'):
            logger.warning(
                f"Database path '{db_path}' has unrecognized URL scheme but ends in .db. "
                "Treating as SQLite."
            )
            sqlite_url = f'sqlite:///{db_path}'
            try:
                engine = create_engine(
                    sqlite_url,
                    poolclass=NullPool,
                    connect_args={
                        'check_same_thread': False,
                        'timeout': 20
                    },
                    echo=False
                )
            except Exception as e:
                raise ValueError(f"Failed to create SQLite engine (last resort) with URL '{sqlite_url}': {e}") from e
        else:
            raise ValueError(
                f"Unable to determine database type from path: {db_path!r}. "
                "This is a bug - please report it."
            )
    
    # Verify engine was created
    if engine is None:
        raise RuntimeError(f"Failed to create database engine for path: {db_path!r}")
    
    # Set up query monitoring if profiling enabled
    if enable_profiling:
        try:
            from config.database_performance import setup_query_monitoring
            setup_query_monitoring(engine)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Could not set up database monitoring: {e}")
        
        # Set up query profiling if enabled
        try:
            from scraper.utils.query_profiler import setup_query_listening
            setup_query_listening(engine)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Could not set up query profiling: {e}")
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    # Add indexes if they don't exist (SQLite only)
    # Check if SQLite for index creation (reuse detection logic)
    if is_sqlite:
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

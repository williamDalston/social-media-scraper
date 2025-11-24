import pytest
import os
import tempfile
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from flask import Flask

# Import app and models
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.schema import Base, DimAccount, FactFollowersSnapshot, init_db

# Try to import app, but handle missing dependencies gracefully
try:
    from app import app as flask_app, get_db_session

    APP_AVAILABLE = True
except (ImportError, ModuleNotFoundError) as e:
    # Create a minimal Flask app for testing if main app can't be imported
    flask_app = Flask(__name__)
    flask_app.config["TESTING"] = True
    APP_AVAILABLE = False
    # Only print warning if it's not a known missing dependency
    if "flask_limiter" not in str(e) and "cache" not in str(e):
        print(f"Warning: Could not import main app: {e}. Using minimal test app.")


@pytest.fixture(scope="session")
def test_db_path():
    """Create a temporary database file for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    # Cleanup
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture(scope="function")
def db_engine(test_db_path):
    """Create a test database engine."""
    engine = create_engine(f"sqlite:///{test_db_path}")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create a test database session."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    # Clear any existing data
    from scraper.schema import FactSocialPost, FactFollowersSnapshot, DimAccount

    session.query(FactSocialPost).delete()
    session.query(FactFollowersSnapshot).delete()
    session.query(DimAccount).delete()
    session.commit()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def app(test_db_path):
    """Create Flask test app with test database."""
    flask_app.config["TESTING"] = True
    flask_app.config["DATABASE"] = test_db_path

    if APP_AVAILABLE:
        # Override get_db_session to use test database
        def get_test_db_session():
            engine = create_engine(f"sqlite:///{test_db_path}")
            Base.metadata.create_all(engine)
            Session = sessionmaker(bind=engine)
            return Session()

        # Monkey patch the get_db_session function
        import app as app_module

        original_get_db = app_module.get_db_session
        app_module.get_db_session = get_test_db_session

        yield flask_app

        # Restore original
        app_module.get_db_session = original_get_db
    else:
        # Minimal app for testing
        yield flask_app


@pytest.fixture
def client(app):
    """Create Flask test client."""
    return app.test_client()


@pytest.fixture
def sample_account(db_session):
    """Create a sample DimAccount for testing."""
    account = DimAccount(
        platform="X",
        handle="test_handle",
        org_name="HHS",
        account_display_name="HHS on X",
        account_url="https://x.com/test_handle",
        is_core_account=True,
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


@pytest.fixture
def sample_snapshot(db_session, sample_account):
    """Create a sample FactFollowersSnapshot for testing."""
    snapshot = FactFollowersSnapshot(
        account_key=sample_account.account_key,
        snapshot_date=date.today(),
        followers_count=1000,
        following_count=100,
        posts_count=5,
        likes_count=500,
        comments_count=50,
        shares_count=100,
        engagements_total=650,
    )
    db_session.add(snapshot)
    db_session.commit()
    db_session.refresh(snapshot)
    return snapshot


@pytest.fixture
def multiple_accounts(db_session):
    """Create multiple sample accounts for testing."""
    accounts = []
    platforms = ["X", "Instagram", "Facebook", "YouTube"]
    for i, platform in enumerate(platforms):
        account = DimAccount(
            platform=platform,
            handle=f"test_handle_{i}",
            org_name="HHS" if i == 0 else "NIH",
            account_display_name=f"Test on {platform}",
            account_url=f"https://{platform.lower()}.com/test_handle_{i}",
            is_core_account=(i == 0),
        )
        db_session.add(account)
        accounts.append(account)
    db_session.commit()
    for account in accounts:
        db_session.refresh(account)
    return accounts


# E2E test fixtures
@pytest.fixture(scope="session")
def live_server(app):
    """Create a live server for E2E tests."""
    from flask import Flask
    from werkzeug.serving import make_server
    import threading

    server = make_server("127.0.0.1", 0, app)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    yield server

    server.shutdown()

"""
Test utilities and helpers.
"""
import os
import tempfile
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from scraper.schema import Base, init_db


@contextmanager
def temp_database():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        engine = create_engine(f"sqlite:///{path}")
        Base.metadata.create_all(engine)
        yield path, engine
    finally:
        if os.path.exists(path):
            os.unlink(path)


def create_test_account(session, platform="X", handle="test", org_name="HHS", **kwargs):
    """Helper to create a test account."""
    from scraper.schema import DimAccount

    account = DimAccount(
        platform=platform,
        handle=handle,
        org_name=org_name,
        account_url=f"https://{platform.lower()}.com/{handle}",
        account_display_name=f"{org_name} on {platform}",
        **kwargs,
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


def create_test_snapshot(session, account_key, snapshot_date, **kwargs):
    """Helper to create a test snapshot."""
    from scraper.schema import FactFollowersSnapshot

    snapshot = FactFollowersSnapshot(
        account_key=account_key,
        snapshot_date=snapshot_date,
        followers_count=kwargs.get("followers_count", 1000),
        engagements_total=kwargs.get("engagements_total", 500),
        **kwargs,
    )
    session.add(snapshot)
    session.commit()
    session.refresh(snapshot)
    return snapshot


def clear_database(session):
    """Clear all data from database tables."""
    from scraper.schema import FactSocialPost, FactFollowersSnapshot, DimAccount

    session.query(FactSocialPost).delete()
    session.query(FactFollowersSnapshot).delete()
    session.query(DimAccount).delete()
    session.commit()

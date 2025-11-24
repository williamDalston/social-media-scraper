"""
Unit tests for init_db function to prevent regression errors.
"""
import pytest
import tempfile
import os
from scraper.schema import init_db


def test_init_db_with_sqlite_filename():
    """Test that 'social_media.db' is correctly identified as SQLite."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "social_media.db")
        engine = init_db(db_path)
        assert engine is not None
        # Verify it's SQLite by checking the URL
        assert "sqlite" in str(engine.url).lower()


def test_init_db_with_sqlite_url():
    """Test that sqlite:/// URLs work correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        sqlite_url = f"sqlite:///{db_path}"
        engine = init_db(sqlite_url)
        assert engine is not None
        assert "sqlite" in str(engine.url).lower()


def test_init_db_with_relative_path():
    """Test that relative paths ending in .db are handled correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        try:
            engine = init_db("test.db")
            assert engine is not None
            assert "sqlite" in str(engine.url).lower()
        finally:
            os.chdir("/")  # Reset to avoid issues


def test_init_db_invalid_path():
    """Test that invalid paths raise appropriate errors."""
    with pytest.raises(ValueError):
        init_db("")

    with pytest.raises(ValueError):
        init_db(None)

    with pytest.raises(ValueError):
        init_db(123)  # Not a string


def test_init_db_unrecognized_format():
    """Test that unrecognized database formats raise errors."""
    with pytest.raises(ValueError, match="Unrecognized database URL format"):
        init_db("invalid://database/path")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

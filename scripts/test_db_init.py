#!/usr/bin/env python3
"""
Test script for database initialization.
This can be run in CI/CD to verify init_db works correctly.
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_init_db():
    """Test that init_db works with 'social_media.db'."""
    print("Testing init_db with 'social_media.db'...", file=sys.stderr, flush=True)

    try:
        from scraper.schema import init_db

        print("✓ Successfully imported init_db", file=sys.stderr, flush=True)

        # Test with the exact string used in CI/CD
        db_path = "social_media.db"
        print(f"Testing with db_path: '{db_path}'", file=sys.stderr, flush=True)

        engine = init_db(db_path)
        print("✓ init_db succeeded!", file=sys.stderr, flush=True)
        print(f"✓ Engine URL: {engine.url}", file=sys.stderr, flush=True)

        # Verify it's SQLite
        if "sqlite" not in str(engine.url).lower():
            print(
                f"✗ ERROR: Expected SQLite engine, got: {engine.url}",
                file=sys.stderr,
                flush=True,
            )
            return False

        print("✓ Engine is SQLite as expected", file=sys.stderr, flush=True)
        return True

    except Exception as e:
        print(f"✗ ERROR: {e}", file=sys.stderr, flush=True)
        import traceback

        traceback.print_exc(file=sys.stderr)
        return False


if __name__ == "__main__":
    success = test_init_db()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
CI-safe database initialization script.
This script handles all edge cases and provides detailed diagnostics.
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def main():
    """Initialize database with comprehensive error handling."""
    # Use absolute path to avoid working directory issues
    db_path = os.path.abspath("social_media.db")

    print("=" * 80)
    print("DATABASE INITIALIZATION (CI)")
    print("=" * 80)
    print(f"Working directory: {os.getcwd()}")
    print(f"Project root: {project_root}")
    print(f"Database path: {db_path}")
    print(f"Database file exists (before): {os.path.exists(db_path)}")
    print()

    try:
        # Import with error handling
        print("Step 1: Importing modules...")
        from scraper.schema import init_db, Base

        print("✓ Successfully imported init_db and Base")
        print()

        # Try multiple path formats to ensure compatibility
        # CRITICAL: Always use explicit SQLite URL format to prevent ArgumentError
        # Never use bare filenames - they cause "Could not parse SQLAlchemy URL" errors
        print("Step 2: Initializing database...")
        test_paths = [
            "sqlite:///social_media.db",  # Explicit SQLite URL (recommended - prevents ArgumentError)
            f"sqlite:///{db_path}",  # Full URL with absolute path
        ]
        # NOTE: Removed bare filename fallbacks ('social_media.db', db_path)
        # because they cause ArgumentError if old schema.py code is running

        engine = None
        last_error = None

        for test_path in test_paths:
            try:
                print(f"  Trying: {test_path}")
                engine = init_db(test_path)
                print(f"✓ Success with: {test_path}")
                print(f"  Engine URL: {engine.url}")
                break
            except Exception as e:
                last_error = e
                print(f"  ✗ Failed with {test_path}: {e}")
                continue

        if engine is None:
            raise Exception(f"All path formats failed. Last error: {last_error}")

        print()

        # Verify database was created
        print("Step 3: Verifying database...")
        if os.path.exists(db_path):
            size = os.path.getsize(db_path)
            print(f"✓ Database file exists: {db_path}")
            print(f"  File size: {size} bytes")
        else:
            # Check if it was created with a relative path
            rel_path = "social_media.db"
            if os.path.exists(rel_path):
                print(f"✓ Database file exists (relative path): {rel_path}")
                print(f"  File size: {os.path.getsize(rel_path)} bytes")
            else:
                raise Exception("Database file was not created!")

        # Verify tables exist
        from sqlalchemy import inspect

        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"✓ Tables created: {len(tables)} tables")
        print(f"  Tables: {', '.join(tables)}")

        # Verify indexes (for SQLite)
        if "sqlite" in str(engine.url).lower():
            conn = engine.raw_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
            )
            indexes = [row[0] for row in cursor.fetchall()]
            conn.close()
            print(f"✓ Indexes created: {len(indexes)} indexes")

        engine.dispose()

        print()
        print("=" * 80)
        print("✓ DATABASE INITIALIZATION SUCCESSFUL")
        print("=" * 80)
        return 0

    except Exception as e:
        print()
        print("=" * 80)
        print("✗ DATABASE INITIALIZATION FAILED")
        print("=" * 80)
        print(f"Error: {e}")
        print()
        print("Full traceback:")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

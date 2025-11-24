#!/usr/bin/env python3
"""
Diagnostic script to debug init_db() issues in CI.
This script tests all the scenarios that might fail.
"""
import os
import sys
import traceback
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("=" * 80)
print("INIT_DB DIAGNOSTIC SCRIPT")
print("=" * 80)
print(f"Python version: {sys.version}")
print(f"Working directory: {os.getcwd()}")
print(f"Project root: {project_root}")
print(f"Python path: {sys.path[:3]}")
print()

# Test 1: Can we import the module?
print("TEST 1: Module Import")
print("-" * 80)
try:
    from scraper.schema import init_db, Base, _construct_sqlite_url, _ensure_indexes

    print(
        "✓ Successfully imported init_db, Base, _construct_sqlite_url, _ensure_indexes"
    )
except Exception as e:
    print(f"✗ FAILED to import: {e}")
    traceback.print_exc()
    sys.exit(1)
print()

# Test 2: Can we import Job model?
print("TEST 2: Job Model Import")
print("-" * 80)
try:
    from models.job import Job

    print("✓ Successfully imported Job model")
except ImportError as e:
    print(f"⚠ Job model import failed (this is OK if it doesn't exist): {e}")
except Exception as e:
    print(f"✗ Unexpected error importing Job: {e}")
    traceback.print_exc()
print()

# Test 3: Test _construct_sqlite_url with various inputs
print("TEST 3: _construct_sqlite_url Function")
print("-" * 80)
test_cases = [
    "social_media.db",
    "sqlite:///social_media.db",
    "sqlite://social_media.db",  # Missing third slash
    os.path.abspath("social_media.db"),
]

for test_input in test_cases:
    try:
        result = _construct_sqlite_url(test_input)
        print(f"✓ Input: '{test_input}' → Output: '{result}'")
    except Exception as e:
        print(f"✗ Input: '{test_input}' → ERROR: {e}")
        traceback.print_exc()
print()

# Test 4: Test init_db with different inputs
print("TEST 4: init_db() with Different Inputs")
print("-" * 80)
test_db_paths = [
    "social_media.db",
    "sqlite:///social_media.db",
    os.path.abspath("social_media.db"),
]

for db_path in test_db_paths:
    # Clean up any existing database
    if os.path.exists("social_media.db"):
        try:
            os.remove("social_media.db")
        except:
            pass

    try:
        print(f"\nTesting with: '{db_path}'")
        engine = init_db(db_path)
        print(f"✓ Success! Engine created: {engine}")
        print(f"  Engine URL: {engine.url}")

        # Verify tables were created
        from sqlalchemy import inspect

        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"  Tables created: {tables}")

        # Verify indexes
        if "sqlite" in str(engine.url).lower():
            conn = engine.raw_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
            )
            indexes = [row[0] for row in cursor.fetchall()]
            conn.close()
            print(f"  Indexes created: {len(indexes)} indexes")

        engine.dispose()

    except Exception as e:
        print(f"✗ FAILED with '{db_path}': {e}")
        traceback.print_exc()
        print()
print()

# Test 5: Test the exact command used in CI
print("TEST 5: Exact CI Command Simulation")
print("-" * 80)
if os.path.exists("social_media.db"):
    try:
        os.remove("social_media.db")
    except:
        pass

try:
    # This is exactly what CI runs
    from scraper.schema import init_db

    engine = init_db("sqlite:///social_media.db")
    print("✓ CI command simulation SUCCESS")
    print(f"  Database file exists: {os.path.exists('social_media.db')}")
    if os.path.exists("social_media.db"):
        print(f"  Database file size: {os.path.getsize('social_media.db')} bytes")
    engine.dispose()
except Exception as e:
    print(f"✗ CI command simulation FAILED: {e}")
    traceback.print_exc()
    sys.exit(1)
print()

# Test 6: Check for potential import issues
print("TEST 6: Import Dependency Check")
print("-" * 80)
dependencies = [
    "sqlalchemy",
    "sqlalchemy.engine",
    "sqlalchemy.orm",
    "sqlalchemy.pool",
]

for dep in dependencies:
    try:
        __import__(dep)
        print(f"✓ {dep}")
    except ImportError as e:
        print(f"✗ {dep}: {e}")
print()

# Test 7: Check file permissions
print("TEST 7: File System Permissions")
print("-" * 80)
test_file = "test_write_permissions.db"
try:
    with open(test_file, "w") as f:
        f.write("test")
    os.remove(test_file)
    print("✓ Can create and delete files in current directory")
except Exception as e:
    print(f"✗ Cannot write to current directory: {e}")
print()

print("=" * 80)
print("DIAGNOSTIC COMPLETE")
print("=" * 80)

#!/usr/bin/env python3
"""
Simulate the exact CI workflow to identify issues.
This replicates the exact sequence of commands from GitHub Actions.
"""
import os
import sys
from pathlib import Path

# Add project root to path (simulating CI environment)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("=" * 80)
print("CI WORKFLOW SIMULATION")
print("=" * 80)
print(f"Working directory: {os.getcwd()}")
print(f"Project root: {project_root}")
print()

# Step 1: Set environment variables (like CI does)
print("STEP 1: Setting environment variables")
print("-" * 80)
os.environ["DATABASE_URL"] = "sqlite:///social_media.db"
print(f"✓ DATABASE_URL = {os.environ.get('DATABASE_URL')}")
print()

# Step 2: Initialize database (exact CI command)
print("STEP 2: Initialize database (CI command)")
print("-" * 80)
try:
    # This is exactly what CI runs:
    # python -c "from scraper.schema import init_db; init_db('sqlite:///social_media.db')"
    from scraper.schema import init_db

    engine = init_db("sqlite:///social_media.db")
    print("✓ Database initialized successfully")
    print(f"  Engine URL: {engine.url}")
    print(f"  Database file exists: {os.path.exists('social_media.db')}")
    if os.path.exists("social_media.db"):
        print(f"  Database file size: {os.path.getsize('social_media.db')} bytes")
    engine.dispose()
except Exception as e:
    print(f"✗ FAILED: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
print()

# Step 3: Populate accounts (next CI step)
print("STEP 3: Populate accounts (CI command)")
print("-" * 80)
try:
    # This is what CI runs:
    # python -c "from scraper.extract_accounts import populate_accounts; populate_accounts()"
    from scraper.extract_accounts import populate_accounts

    # Check if hhs_accounts.json exists
    json_path = "hhs_accounts.json"
    if not os.path.exists(json_path):
        print(f"⚠ {json_path} not found, creating minimal test file")
        import json

        test_data = [
            {"platform": "X", "url": "https://x.com/test", "organization": "HHS"}
        ]
        with open(json_path, "w") as f:
            json.dump(test_data, f)
        print(f"✓ Created test {json_path}")

    # populate_accounts uses default db_path='social_media.db' (relative path)
    # But we initialized with 'sqlite:///social_media.db'
    # This should work because init_db() handles both formats
    populate_accounts(json_path=json_path, db_path="social_media.db")
    print("✓ Accounts populated successfully")

except Exception as e:
    print(f"✗ FAILED: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
print()

# Step 4: Verify database state
print("STEP 4: Verify database state")
print("-" * 80)
try:
    from scraper.schema import init_db, DimAccount
    from sqlalchemy.orm import sessionmaker

    engine = init_db(
        "social_media.db"
    )  # Using relative path like populate_accounts does
    Session = sessionmaker(bind=engine)
    session = Session()

    account_count = session.query(DimAccount).count()
    print(f"✓ Database accessible")
    print(f"  Accounts in database: {account_count}")

    session.close()
    engine.dispose()

except Exception as e:
    print(f"✗ FAILED: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
print()

# Step 5: Test path resolution issue
print("STEP 5: Test path resolution")
print("-" * 80)
print("Testing different path formats:")
test_paths = [
    "social_media.db",
    "sqlite:///social_media.db",
    os.path.abspath("social_media.db"),
]

for path in test_paths:
    try:
        from scraper.schema import init_db

        # Use a unique test database for each
        test_db = f"test_{path.replace('/', '_').replace(':', '_')}.db"
        if os.path.exists(test_db):
            os.remove(test_db)

        engine = init_db(path if path != "social_media.db" else test_db)
        print(f"✓ '{path}' → {engine.url}")
        engine.dispose()
        if os.path.exists(test_db):
            os.remove(test_db)
    except Exception as e:
        print(f"✗ '{path}' → ERROR: {e}")

print()
print("=" * 80)
print("CI WORKFLOW SIMULATION COMPLETE")
print("=" * 80)

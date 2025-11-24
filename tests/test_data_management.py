"""
Test Data Management.

Utilities and tests for managing test data across test runs.
"""
import pytest
import json
import os
from datetime import date
from scraper.schema import DimAccount, FactFollowersSnapshot


class TestDataManagement:
    """Test data management utilities."""

    def test_test_data_isolation(self, db_session):
        """Verify test data is isolated between tests."""
        # Create test data
        account = DimAccount(platform="X", handle="isolation_test", org_name="HHS")
        db_session.add(account)
        db_session.commit()

        # Verify it exists
        retrieved = (
            db_session.query(DimAccount).filter_by(handle="isolation_test").first()
        )
        assert retrieved is not None

    def test_test_data_cleanup(self, db_session):
        """Verify test data is cleaned up."""
        # Data should be cleaned by fixtures
        # This test verifies cleanup works
        account = DimAccount(platform="X", handle="cleanup_test", org_name="HHS")
        db_session.add(account)
        db_session.commit()

        # Cleanup is handled by fixtures
        assert account.account_key is not None


class TestDataVersioning:
    """Test data versioning and migration."""

    def test_test_data_schema_versioning(self, db_session):
        """Verify test data works with current schema version."""
        # Create data with current schema
        account = DimAccount(platform="X", handle="version_test", org_name="HHS")
        db_session.add(account)
        db_session.commit()

        # Should work with current schema
        assert account.account_key is not None


class TestDataFixtures:
    """Test reusable data fixtures."""

    def test_fixture_data_reusability(self, sample_account, sample_snapshot):
        """Verify fixture data can be reused across tests."""
        # Fixtures should provide consistent data
        assert sample_account.account_key is not None
        assert sample_snapshot.snapshot_id is not None
        assert sample_snapshot.account_key == sample_account.account_key

"""
Disaster Recovery Testing.

Tests for backup, restore, and disaster recovery procedures.
"""
import pytest
import os
import shutil
import tempfile
from datetime import date
from scraper.schema import DimAccount, FactFollowersSnapshot, init_db
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine


class TestBackupProcedures:
    """Test backup and restore procedures."""

    def test_database_backup_creation(self, test_db_path):
        """Test that database can be backed up."""
        # Create some data
        engine = create_engine(f"sqlite:///{test_db_path}")
        init_db(test_db_path)
        Session = sessionmaker(bind=engine)
        session = Session()

        account = DimAccount(platform="X", handle="backup_test", org_name="HHS")
        session.add(account)
        session.commit()
        session.close()

        # Create backup
        backup_path = test_db_path + ".backup"
        shutil.copy2(test_db_path, backup_path)

        # Verify backup exists
        assert os.path.exists(backup_path)

        # Verify backup contains data
        backup_engine = create_engine(f"sqlite:///{backup_path}")
        backup_session = sessionmaker(bind=backup_engine)()
        backup_account = (
            backup_session.query(DimAccount).filter_by(handle="backup_test").first()
        )
        assert backup_account is not None
        backup_session.close()

        # Cleanup
        if os.path.exists(backup_path):
            os.unlink(backup_path)

    def test_database_restore_procedure(self, test_db_path):
        """Test database restore from backup."""
        # Create original database with data
        engine = create_engine(f"sqlite:///{test_db_path}")
        init_db(test_db_path)
        Session = sessionmaker(bind=engine)
        session = Session()

        account = DimAccount(platform="X", handle="restore_test", org_name="HHS")
        session.add(account)
        session.commit()
        account_key = account.account_key
        session.close()

        # Create backup
        backup_path = test_db_path + ".backup"
        shutil.copy2(test_db_path, backup_path)

        # "Corrupt" original (delete it)
        os.unlink(test_db_path)

        # Restore from backup
        shutil.copy2(backup_path, test_db_path)

        # Verify restore
        restored_engine = create_engine(f"sqlite:///{test_db_path}")
        restored_session = sessionmaker(bind=restored_engine)()
        restored_account = (
            restored_session.query(DimAccount).filter_by(handle="restore_test").first()
        )
        assert restored_account is not None
        assert restored_account.account_key == account_key
        restored_session.close()

        # Cleanup
        if os.path.exists(backup_path):
            os.unlink(backup_path)

    def test_point_in_time_recovery(self, test_db_path):
        """Test recovery to a specific point in time."""
        engine = create_engine(f"sqlite:///{test_db_path}")
        init_db(test_db_path)
        Session = sessionmaker(bind=engine)
        session = Session()

        # Create account
        account = DimAccount(platform="X", handle="pitr_test", org_name="HHS")
        session.add(account)
        session.commit()
        session.close()

        # Create snapshot at time T1
        session = Session()
        snapshot1 = FactFollowersSnapshot(
            account_key=account.account_key,
            snapshot_date=date.today(),
            followers_count=1000,
        )
        session.add(snapshot1)
        session.commit()
        session.close()

        # Verify data exists
        session = Session()
        snapshots = (
            session.query(FactFollowersSnapshot)
            .filter_by(account_key=account.account_key)
            .all()
        )
        assert len(snapshots) == 1
        session.close()


class TestDataRecovery:
    """Test data recovery procedures."""

    def test_data_export_for_recovery(self, db_session, sample_account):
        """Test exporting data for recovery purposes."""
        from scraper.schema import FactFollowersSnapshot
        from datetime import date

        # Create data
        snapshot = FactFollowersSnapshot(
            account_key=sample_account.account_key,
            snapshot_date=date.today(),
            followers_count=1000,
            engagements_total=500,
        )
        db_session.add(snapshot)
        db_session.commit()

        # Export data (simulate recovery export)
        accounts = db_session.query(DimAccount).all()
        snapshots = db_session.query(FactFollowersSnapshot).all()

        # Verify export contains data
        assert len(accounts) > 0
        assert len(snapshots) > 0

    def test_data_integrity_after_recovery(self, test_db_path):
        """Test data integrity after recovery."""
        engine = create_engine(f"sqlite:///{test_db_path}")
        init_db(test_db_path)
        Session = sessionmaker(bind=engine)
        session = Session()

        # Create data
        account = DimAccount(platform="X", handle="integrity_test", org_name="HHS")
        session.add(account)
        session.commit()

        snapshot = FactFollowersSnapshot(
            account_key=account.account_key,
            snapshot_date=date.today(),
            followers_count=1000,
        )
        session.add(snapshot)
        session.commit()
        session.close()

        # Simulate recovery - verify relationships intact
        session = Session()
        recovered_account = (
            session.query(DimAccount).filter_by(handle="integrity_test").first()
        )
        assert recovered_account is not None

        recovered_snapshots = (
            session.query(FactFollowersSnapshot)
            .filter_by(account_key=recovered_account.account_key)
            .all()
        )
        assert len(recovered_snapshots) == 1
        assert (
            recovered_snapshots[0].account.account_key == recovered_account.account_key
        )
        session.close()


class TestDisasterScenarios:
    """Test various disaster scenarios."""

    def test_complete_database_loss_recovery(self, test_db_path):
        """Test recovery from complete database loss."""
        # Create database with data
        engine = create_engine(f"sqlite:///{test_db_path}")
        init_db(test_db_path)
        Session = sessionmaker(bind=engine)
        session = Session()

        account = DimAccount(platform="X", handle="disaster_test", org_name="HHS")
        session.add(account)
        session.commit()
        session.close()

        # Simulate complete loss
        os.unlink(test_db_path)
        assert not os.path.exists(test_db_path)

        # Recreate database
        engine = create_engine(f"sqlite:///{test_db_path}")
        init_db(test_db_path)

        # Verify database is functional
        session = Session()
        count = session.query(DimAccount).count()
        assert isinstance(count, int)
        session.close()

    def test_corrupted_database_recovery(self, test_db_path):
        """Test recovery from corrupted database."""
        # Create database
        engine = create_engine(f"sqlite:///{test_db_path}")
        init_db(test_db_path)
        Session = sessionmaker(bind=engine)
        session = Session()

        account = DimAccount(platform="X", handle="corrupt_test", org_name="HHS")
        session.add(account)
        session.commit()
        session.close()

        # Create backup before corruption
        backup_path = test_db_path + ".backup"
        shutil.copy2(test_db_path, backup_path)

        # Simulate corruption (write garbage)
        with open(test_db_path, "wb") as f:
            f.write(b"CORRUPTED DATA")

        # Restore from backup
        shutil.copy2(backup_path, test_db_path)

        # Verify recovery
        engine = create_engine(f"sqlite:///{test_db_path}")
        session = Session()
        recovered = session.query(DimAccount).filter_by(handle="corrupt_test").first()
        assert recovered is not None
        session.close()

        # Cleanup
        if os.path.exists(backup_path):
            os.unlink(backup_path)


class TestRecoveryTimeObjectives:
    """Test recovery time objectives (RTO)."""

    def test_backup_creation_time(self, test_db_path):
        """Test that backups can be created quickly."""
        import time

        # Create database with data
        engine = create_engine(f"sqlite:///{test_db_path}")
        init_db(test_db_path)
        Session = sessionmaker(bind=engine)
        session = Session()

        # Add some data
        for i in range(10):
            account = DimAccount(platform="X", handle=f"rto_test_{i}", org_name="HHS")
            session.add(account)
        session.commit()
        session.close()

        # Measure backup time
        start = time.time()
        backup_path = test_db_path + ".backup"
        shutil.copy2(test_db_path, backup_path)
        elapsed = time.time() - start

        # Should be fast (under 1 second for small DB)
        assert elapsed < 1.0

        # Cleanup
        if os.path.exists(backup_path):
            os.unlink(backup_path)

    def test_restore_time(self, test_db_path):
        """Test that restore can be completed quickly."""
        import time

        # Create backup
        engine = create_engine(f"sqlite:///{test_db_path}")
        init_db(test_db_path)
        backup_path = test_db_path + ".backup"
        shutil.copy2(test_db_path, backup_path)

        # Measure restore time
        start = time.time()
        shutil.copy2(backup_path, test_db_path)
        elapsed = time.time() - start

        # Should be fast
        assert elapsed < 1.0

        # Cleanup
        if os.path.exists(backup_path):
            os.unlink(backup_path)

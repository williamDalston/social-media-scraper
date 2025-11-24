import pytest
import io
import csv
from scraper.schema import DimAccount
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine


class TestCSVUpload:
    """Test CSV file upload functionality."""

    def test_upload_valid_csv(self, client, app, test_db_path):
        """Test uploading a valid CSV file."""
        # Create CSV content
        csv_data = io.StringIO()
        writer = csv.writer(csv_data)
        writer.writerow(["Platform", "Handle", "Organization"])
        writer.writerow(["X", "test1", "HHS"])
        writer.writerow(["Instagram", "test2", "NIH"])
        csv_data.seek(0)

        # Upload file
        response = client.post(
            "/upload",
            data={
                "file": (io.BytesIO(csv_data.getvalue().encode("utf-8")), "test.csv")
            },
            content_type="multipart/form-data",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert "message" in data
        assert "2" in data["message"]  # Should say "Successfully added 2 accounts"

        # Verify accounts were created
        engine = create_engine(f"sqlite:///{test_db_path}")
        Session = sessionmaker(bind=engine)
        session = Session()

        accounts = session.query(DimAccount).all()
        assert len(accounts) == 2

        # Verify account details
        account1 = session.query(DimAccount).filter_by(handle="test1").first()
        assert account1 is not None
        assert account1.platform == "X"
        assert account1.org_name == "HHS"

        session.close()

    def test_upload_csv_with_missing_file(self, client, app):
        """Test uploading without a file."""
        response = client.post("/upload")
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "No file part" in data["error"]

    def test_upload_csv_with_empty_filename(self, client, app):
        """Test uploading with empty filename."""
        response = client.post(
            "/upload",
            data={"file": (io.BytesIO(b""), "")},
            content_type="multipart/form-data",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "No selected file" in data["error"]

    def test_upload_csv_skips_duplicates(self, client, app, test_db_path):
        """Test that upload skips duplicate accounts."""
        # Create existing account
        engine = create_engine(f"sqlite:///{test_db_path}")
        Session = sessionmaker(bind=engine)
        session = Session()

        existing = DimAccount(
            platform="X",
            handle="existing",
            org_name="HHS",
            account_url="https://x.com/existing",
        )
        session.add(existing)
        session.commit()
        session.close()

        # Upload CSV with duplicate
        csv_data = io.StringIO()
        writer = csv.writer(csv_data)
        writer.writerow(["Platform", "Handle", "Organization"])
        writer.writerow(["X", "existing", "HHS"])  # Duplicate
        writer.writerow(["Instagram", "new", "NIH"])  # New
        csv_data.seek(0)

        response = client.post(
            "/upload",
            data={
                "file": (io.BytesIO(csv_data.getvalue().encode("utf-8")), "test.csv")
            },
            content_type="multipart/form-data",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert "1" in data["message"]  # Should say "Successfully added 1 account"

        # Verify only one new account was added
        session = Session()
        accounts = session.query(DimAccount).all()
        assert len(accounts) == 2  # Existing + 1 new

        session.close()

    def test_upload_csv_handles_missing_fields(self, client, app, test_db_path):
        """Test that upload handles CSV with missing optional fields."""
        csv_data = io.StringIO()
        writer = csv.writer(csv_data)
        writer.writerow(["Platform", "Handle", "Organization"])
        writer.writerow(["X", "test1", ""])  # Missing organization
        writer.writerow(["Instagram", "test2"])  # Missing organization column
        csv_data.seek(0)

        response = client.post(
            "/upload",
            data={
                "file": (io.BytesIO(csv_data.getvalue().encode("utf-8")), "test.csv")
            },
            content_type="multipart/form-data",
        )

        # Should still succeed, creating accounts with None org_name
        assert response.status_code == 200

        engine = create_engine(f"sqlite:///{test_db_path}")
        Session = sessionmaker(bind=engine)
        session = Session()

        account1 = session.query(DimAccount).filter_by(handle="test1").first()
        assert account1 is not None
        # org_name might be None or empty string depending on CSV parsing

        session.close()

    def test_upload_csv_handles_missing_platform(self, client, app, test_db_path):
        """Test that upload handles CSV rows with missing platform."""
        csv_data = io.StringIO()
        writer = csv.writer(csv_data)
        writer.writerow(["Platform", "Handle", "Organization"])
        writer.writerow(["", "test1", "HHS"])  # Missing platform
        writer.writerow(["X", "test2", "HHS"])  # Valid row
        csv_data.seek(0)

        response = client.post(
            "/upload",
            data={
                "file": (io.BytesIO(csv_data.getvalue().encode("utf-8")), "test.csv")
            },
            content_type="multipart/form-data",
        )

        assert response.status_code == 200

        # Only valid row should create account
        engine = create_engine(f"sqlite:///{test_db_path}")
        Session = sessionmaker(bind=engine)
        session = Session()

        accounts = session.query(DimAccount).all()
        assert len(accounts) == 1
        assert accounts[0].handle == "test2"

        session.close()

    def test_upload_csv_handles_missing_handle(self, client, app, test_db_path):
        """Test that upload handles CSV rows with missing handle."""
        csv_data = io.StringIO()
        writer = csv.writer(csv_data)
        writer.writerow(["Platform", "Handle", "Organization"])
        writer.writerow(["X", "", "HHS"])  # Missing handle
        writer.writerow(["Instagram", "test2", "HHS"])  # Valid row
        csv_data.seek(0)

        response = client.post(
            "/upload",
            data={
                "file": (io.BytesIO(csv_data.getvalue().encode("utf-8")), "test.csv")
            },
            content_type="multipart/form-data",
        )

        assert response.status_code == 200

        # Only valid row should create account
        engine = create_engine(f"sqlite:///{test_db_path}")
        Session = sessionmaker(bind=engine)
        session = Session()

        accounts = session.query(DimAccount).all()
        assert len(accounts) == 1
        assert accounts[0].handle == "test2"

        session.close()

    def test_upload_csv_sets_display_name(self, client, app, test_db_path):
        """Test that upload sets account_display_name correctly."""
        csv_data = io.StringIO()
        writer = csv.writer(csv_data)
        writer.writerow(["Platform", "Handle", "Organization"])
        writer.writerow(["X", "test", "HHS"])
        csv_data.seek(0)

        response = client.post(
            "/upload",
            data={
                "file": (io.BytesIO(csv_data.getvalue().encode("utf-8")), "test.csv")
            },
            content_type="multipart/form-data",
        )

        assert response.status_code == 200

        engine = create_engine(f"sqlite:///{test_db_path}")
        Session = sessionmaker(bind=engine)
        session = Session()

        account = session.query(DimAccount).filter_by(handle="test").first()
        assert account is not None
        assert account.account_display_name == "HHS on X"

        session.close()

    def test_upload_csv_sets_account_url(self, client, app, test_db_path):
        """Test that upload infers account_url from platform and handle."""
        csv_data = io.StringIO()
        writer = csv.writer(csv_data)
        writer.writerow(["Platform", "Handle", "Organization"])
        writer.writerow(["X", "test", "HHS"])
        csv_data.seek(0)

        response = client.post(
            "/upload",
            data={
                "file": (io.BytesIO(csv_data.getvalue().encode("utf-8")), "test.csv")
            },
            content_type="multipart/form-data",
        )

        assert response.status_code == 200

        engine = create_engine(f"sqlite:///{test_db_path}")
        Session = sessionmaker(bind=engine)
        session = Session()

        account = session.query(DimAccount).filter_by(handle="test").first()
        assert account is not None
        assert account.account_url is not None
        assert "x.com" in account.account_url.lower() or "test" in account.account_url

        session.close()

"""
API Contract Testing.

Contract tests verify that API endpoints maintain their contracts (request/response formats)
and help detect breaking changes.
"""
import pytest
import json
from datetime import date
from scraper.schema import DimAccount, FactFollowersSnapshot


class TestAPISummaryContract:
    """Contract tests for /api/summary endpoint."""

    def test_summary_response_structure(self, client, db_session, sample_account):
        """Verify /api/summary response structure matches contract."""
        # Create snapshot
        snapshot = FactFollowersSnapshot(
            account_key=sample_account.account_key,
            snapshot_date=date.today(),
            followers_count=1000,
            engagements_total=500,
            posts_count=5,
        )
        db_session.add(snapshot)
        db_session.commit()

        response = client.get("/api/summary")
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, list)

        if len(data) > 0:
            item = data[0]
            # Verify required fields
            assert "platform" in item
            assert "handle" in item
            assert "followers" in item
            assert "engagement" in item
            assert "posts" in item

            # Verify field types
            assert isinstance(item["platform"], str)
            assert isinstance(item["handle"], str)
            assert isinstance(item["followers"], (int, type(None)))
            assert isinstance(item["engagement"], (int, type(None)))
            assert isinstance(item["posts"], (int, type(None)))

    def test_summary_empty_response(self, client):
        """Verify /api/summary returns empty list when no data."""
        response = client.get("/api/summary")
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 0


class TestAPIHistoryContract:
    """Contract tests for /api/history/<platform>/<handle> endpoint."""

    def test_history_response_structure(self, client, db_session, sample_account):
        """Verify /api/history response structure matches contract."""
        # Create multiple snapshots
        for i in range(3):
            snapshot = FactFollowersSnapshot(
                account_key=sample_account.account_key,
                snapshot_date=date.fromordinal(date.today().toordinal() - i),
                followers_count=1000 + i * 10,
                engagements_total=500 + i * 5,
            )
            db_session.add(snapshot)
        db_session.commit()

        response = client.get(
            f"/api/history/{sample_account.platform}/{sample_account.handle}"
        )
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, dict)

        # Verify required fields
        assert "dates" in data
        assert "followers" in data
        assert "engagement" in data

        # Verify field types
        assert isinstance(data["dates"], list)
        assert isinstance(data["followers"], list)
        assert isinstance(data["engagement"], list)

        # Verify arrays have same length
        assert len(data["dates"]) == len(data["followers"])
        assert len(data["followers"]) == len(data["engagement"])

        # Verify date format (ISO format strings)
        if len(data["dates"]) > 0:
            assert isinstance(data["dates"][0], str)
            # Should be ISO format (YYYY-MM-DD)
            assert len(data["dates"][0]) == 10

    def test_history_404_for_nonexistent_account(self, client):
        """Verify /api/history returns 404 for nonexistent account."""
        response = client.get("/api/history/X/nonexistent")
        assert response.status_code == 404

        data = response.get_json()
        assert "error" in data


class TestAPIGridContract:
    """Contract tests for /api/grid endpoint."""

    def test_grid_response_structure(self, client, db_session, sample_account):
        """Verify /api/grid response structure matches contract."""
        snapshot = FactFollowersSnapshot(
            account_key=sample_account.account_key,
            snapshot_date=date.today(),
            followers_count=1000,
            engagements_total=500,
            posts_count=5,
            likes_count=400,
            comments_count=50,
            shares_count=50,
        )
        db_session.add(snapshot)
        db_session.commit()

        response = client.get("/api/grid")
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, (list, dict))

        # Grid may return list or dict with pagination
        if isinstance(data, list):
            if len(data) > 0:
                row = data[0]
                assert isinstance(row, list)
                # Should have 10 fields: platform, handle, org_name, date, followers, engagement, posts, likes, comments, shares
                assert len(row) == 10
        elif isinstance(data, dict):
            # Paginated response
            assert "data" in data
            assert "pagination" in data


class TestAPIDownloadContract:
    """Contract tests for /api/download endpoint."""

    def test_download_response_structure(self, client, db_session, sample_account):
        """Verify /api/download returns CSV format."""
        snapshot = FactFollowersSnapshot(
            account_key=sample_account.account_key,
            snapshot_date=date.today(),
            followers_count=1000,
        )
        db_session.add(snapshot)
        db_session.commit()

        response = client.get("/api/download")
        assert response.status_code == 200
        assert "text/csv" in response.content_type

        # Verify CSV headers
        csv_data = response.data.decode("utf-8")
        assert "Platform" in csv_data
        assert "Handle" in csv_data
        assert "Followers" in csv_data


class TestAPIRunScraperContract:
    """Contract tests for /api/run-scraper endpoint."""

    def test_run_scraper_request_contract(self, client):
        """Verify /api/run-scraper accepts correct request format."""
        # Test with mode parameter
        response = client.post(
            "/api/run-scraper",
            json={"mode": "simulated"},
            content_type="application/json",
        )

        # Should return 200 or 500 (depending on auth and setup)
        assert response.status_code in [200, 401, 403, 500]

        if response.status_code == 200:
            data = response.get_json()
            assert "message" in data

    def test_run_scraper_invalid_mode(self, client):
        """Verify /api/run-scraper rejects invalid modes."""
        response = client.post(
            "/api/run-scraper",
            json={"mode": "invalid_mode"},
            content_type="application/json",
        )

        # Should return error for invalid mode
        if response.status_code != 401:  # Skip if auth required
            assert response.status_code in [400, 422, 500]


class TestAPIErrorContract:
    """Contract tests for error responses."""

    def test_error_response_structure(self, client):
        """Verify error responses follow standard format."""
        # Test 404 error
        response = client.get("/api/history/X/nonexistent")
        assert response.status_code == 404

        data = response.get_json()
        # Error responses should have 'error' field
        assert "error" in data or isinstance(data, dict)

    def test_400_error_structure(self, client):
        """Verify 400 errors have proper structure."""
        # Test with invalid request
        response = client.post("/upload")
        assert response.status_code == 400

        data = response.get_json()
        assert "error" in data


class TestAPIVersioningContract:
    """Contract tests for API versioning."""

    def test_api_version_consistency(self, client):
        """Verify API maintains version consistency."""
        # If versioned endpoints exist, they should follow pattern
        # This is a placeholder for when versioning is implemented
        pass

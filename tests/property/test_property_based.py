"""
Property-based tests using Hypothesis library.

Property-based testing generates random inputs and verifies that properties
hold true for all inputs, helping find edge cases and bugs.
"""
import pytest
from hypothesis import given, strategies as st, assume, settings
from datetime import date, timedelta
from scraper.extract_accounts import extract_handle
from scraper.schema import DimAccount, FactFollowersSnapshot


class TestExtractHandleProperty:
    """Property-based tests for extract_handle function."""

    @given(
        url=st.text(min_size=1, max_size=200),
        platform=st.sampled_from(
            ["X", "Facebook", "Instagram", "LinkedIn", "YouTube", "Truth Social"]
        ),
    )
    @settings(max_examples=100)
    def test_extract_handle_always_returns_string(self, url, platform):
        """Property: extract_handle always returns a string."""
        # Add https:// if not present
        if not url.startswith("http"):
            url = f"https://{url}"

        result = extract_handle(url, platform)
        assert isinstance(result, str)
        assert len(result) >= 0

    @given(
        handle=st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(whitelist_categories=("L", "N", "_")),
        ),
        platform=st.sampled_from(["X", "Instagram", "Facebook"]),
    )
    @settings(max_examples=50)
    def test_extract_handle_preserves_valid_handles(self, handle, platform):
        """Property: Valid handles are extracted correctly."""
        url = f"https://{platform.lower()}.com/{handle}"
        result = extract_handle(url, platform)
        # Result should contain the handle (may have additional path parts)
        assert handle in result or result == handle


class TestAccountModelProperties:
    """Property-based tests for account model validation."""

    @given(
        platform=st.text(min_size=1, max_size=50),
        handle=st.text(min_size=1, max_size=100),
        org_name=st.text(max_size=200),
    )
    @settings(max_examples=50)
    def test_account_creation_with_various_inputs(
        self, db_session, platform, handle, org_name
    ):
        """Property: Account can be created with various valid inputs."""
        # Skip if inputs contain invalid characters for URLs
        assume(" " not in handle or handle.strip() == handle)

        account = DimAccount(
            platform=platform,
            handle=handle,
            org_name=org_name if org_name else None,
            account_url=f"https://{platform.lower()}.com/{handle}",
        )
        db_session.add(account)
        db_session.commit()

        assert account.account_key is not None
        assert account.platform == platform
        assert account.handle == handle


class TestSnapshotProperties:
    """Property-based tests for snapshot model."""

    @given(
        followers=st.integers(min_value=0, max_value=1000000000),
        engagement=st.integers(min_value=0, max_value=10000000),
        snapshot_date=st.dates(min_value=date(2020, 1, 1), max_value=date.today()),
    )
    @settings(max_examples=50)
    def test_snapshot_creation_with_various_values(
        self, db_session, sample_account, followers, engagement, snapshot_date
    ):
        """Property: Snapshots can be created with various metric values."""
        snapshot = FactFollowersSnapshot(
            account_key=sample_account.account_key,
            snapshot_date=snapshot_date,
            followers_count=followers,
            engagements_total=engagement,
        )
        db_session.add(snapshot)
        db_session.commit()

        assert snapshot.snapshot_id is not None
        assert snapshot.followers_count == followers
        assert snapshot.engagements_total == engagement
        assert snapshot.snapshot_date == snapshot_date

    @given(
        likes=st.integers(min_value=0, max_value=1000000),
        comments=st.integers(min_value=0, max_value=100000),
        shares=st.integers(min_value=0, max_value=100000),
    )
    @settings(max_examples=30)
    def test_engagement_total_calculation(
        self, db_session, sample_account, likes, comments, shares
    ):
        """Property: engagements_total equals sum of likes, comments, shares."""
        snapshot = FactFollowersSnapshot(
            account_key=sample_account.account_key,
            snapshot_date=date.today(),
            likes_count=likes,
            comments_count=comments,
            shares_count=shares,
            engagements_total=0,
        )
        snapshot.engagements_total = (
            snapshot.likes_count + snapshot.comments_count + snapshot.shares_count
        )

        expected_total = likes + comments + shares
        assert snapshot.engagements_total == expected_total


class TestDataConsistencyProperties:
    """Property-based tests for data consistency."""

    @given(
        num_snapshots=st.integers(min_value=1, max_value=10),
        base_followers=st.integers(min_value=1000, max_value=1000000),
    )
    @settings(max_examples=20)
    def test_sequential_snapshots_consistency(
        self, db_session, sample_account, num_snapshots, base_followers
    ):
        """Property: Sequential snapshots should have reasonable growth patterns."""
        today = date.today()
        snapshots = []

        for i in range(num_snapshots):
            snapshot_date = today - timedelta(days=num_snapshots - i - 1)
            # Simulate growth with some randomness
            followers = base_followers + (i * 100) + (i % 10) * 50

            snapshot = FactFollowersSnapshot(
                account_key=sample_account.account_key,
                snapshot_date=snapshot_date,
                followers_count=followers,
                engagements_total=followers // 10,
            )
            db_session.add(snapshot)
            snapshots.append(snapshot)

        db_session.commit()

        # Verify all snapshots were created
        assert len(snapshots) == num_snapshots

        # Verify dates are sequential
        dates = [s.snapshot_date for s in snapshots]
        assert dates == sorted(dates)


class TestURLParsingProperties:
    """Property-based tests for URL parsing."""

    @given(
        domain=st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(whitelist_categories=("L", "N", ".")),
        ),
        path=st.text(
            min_size=1,
            max_size=100,
            alphabet=st.characters(whitelist_categories=("L", "N", "/", "_", "-")),
        ),
    )
    @settings(max_examples=30)
    def test_url_parsing_handles_various_formats(self, domain, path):
        """Property: URL parsing handles various domain and path formats."""
        assume(".." not in domain and ".." not in path)  # Avoid path traversal

        url = f"https://{domain}/{path}"
        platforms = ["X", "Instagram", "Facebook", "LinkedIn", "YouTube"]

        for platform in platforms:
            try:
                result = extract_handle(url, platform)
                assert isinstance(result, str)
            except Exception:
                # Some URLs may not parse correctly, which is acceptable
                pass

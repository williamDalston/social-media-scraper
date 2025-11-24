"""
Data quality testing - validation, accuracy, completeness.
"""
import pytest
from scraper.optimization.result_validation import ResultValidator
from scraper.schema import DimAccount, FactFollowersSnapshot


class TestDataValidation:
    """Test data validation rules."""

    def test_validate_followers_count(self):
        """Test followers count validation."""
        validator = ResultValidator()

        # Valid cases
        assert validator._validate_followers(1000, "X", "test")[0] == True
        assert validator._validate_followers(0, "X", "test")[0] == True

        # Invalid cases
        assert validator._validate_followers(-1, "X", "test")[0] == False
        assert (
            validator._validate_followers(1000000000, "X", "test")[0] == False
        )  # Too high

    def test_validate_engagement_metrics(self):
        """Test engagement metrics validation."""
        validator = ResultValidator()

        # Valid
        assert validator._validate_engagement(100, "X", "test")[0] == True

        # Invalid
        assert validator._validate_engagement(-1, "X", "test")[0] == False
        assert (
            validator._validate_engagement(20000000, "X", "test")[0] == False
        )  # Too high

    def test_validate_result_completeness(self):
        """Test that results contain required fields."""
        validator = ResultValidator()

        # Complete result
        complete_result = {
            "followers_count": 1000,
            "following_count": 500,
            "posts_count": 10,
            "likes_count": 100,
            "comments_count": 20,
            "shares_count": 5,
        }
        is_valid, errors = validator.validate_result(complete_result, "X", "test")
        assert is_valid == True

        # Incomplete result
        incomplete_result = {"followers_count": 1000}
        is_valid, errors = validator.validate_result(incomplete_result, "X", "test")
        assert is_valid == False
        assert len(errors) > 0

    def test_quality_score_calculation(self):
        """Test quality score calculation."""
        validator = ResultValidator()

        # High quality result
        good_result = {
            "followers_count": 1000,
            "following_count": 500,
            "posts_count": 10,
        }
        score = validator.calculate_quality_score(good_result, "X", "test")
        assert 0 <= score <= 1
        assert score > 0.5  # Should be reasonably high

        # Low quality result (missing fields)
        bad_result = {"followers_count": 1000}
        score = validator.calculate_quality_score(bad_result, "X", "test")
        assert score < 0.5  # Should be lower


class TestDataAccuracy:
    """Test data accuracy."""

    def test_follower_count_accuracy(self):
        """Test that follower counts are within reasonable ranges."""
        # This would require comparing with known values
        # For now, test validation rules
        validator = ResultValidator()

        # Test various follower counts
        test_cases = [
            (100, True),
            (1000, True),
            (1000000, True),
            (-1, False),
            (10000000000, False),  # Unreasonably high
        ]

        for count, expected_valid in test_cases:
            is_valid, _ = validator._validate_followers(count, "X", "test")
            assert (
                is_valid == expected_valid
            ), f"Follower count {count} validation failed"


class TestDataCompleteness:
    """Test data completeness."""

    def test_required_fields_present(self):
        """Test that all required fields are present in results."""
        required_fields = ["followers_count", "following_count", "posts_count"]

        validator = ResultValidator()

        for field in required_fields:
            result = {f: 100 for f in required_fields if f != field}
            is_valid, errors = validator.validate_result(result, "X", "test")
            assert is_valid == False
            assert any(
                f"missing required field" in err.lower() or field in err.lower()
                for err in errors
            )

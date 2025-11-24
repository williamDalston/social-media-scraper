"""
Data quality scoring and reporting.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class DataQualityScorer:
    """
    Scores data quality for scraped data.
    """

    def __init__(self):
        """Initialize data quality scorer."""
        logger.info("Initialized DataQualityScorer")

    def score_snapshot(self, snapshot_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Score quality of a snapshot.

        Args:
            snapshot_data: Snapshot data dictionary

        Returns:
            Dictionary with quality score and details:
            {
                'score': float (0.0 to 1.0),
                'completeness': float,
                'validity': float,
                'consistency': float,
                'issues': List[str]
            }
        """
        issues = []
        completeness_score = 0.0
        validity_score = 0.0
        consistency_score = 0.0

        # Required fields
        required_fields = ["followers_count", "following_count", "posts_count"]
        present_fields = sum(
            1 for field in required_fields if snapshot_data.get(field) is not None
        )
        completeness_score = present_fields / len(required_fields)

        if completeness_score < 1.0:
            issues.append(
                f"Missing {len(required_fields) - present_fields} required fields"
            )

        # Validity checks
        valid_count = 0
        total_checks = 0

        # Check followers_count
        followers = snapshot_data.get("followers_count")
        if followers is not None:
            total_checks += 1
            if isinstance(followers, int) and followers >= 0:
                valid_count += 1
            else:
                issues.append(f"Invalid followers_count: {followers}")

        # Check following_count
        following = snapshot_data.get("following_count")
        if following is not None:
            total_checks += 1
            if isinstance(following, int) and following >= 0:
                valid_count += 1
            else:
                issues.append(f"Invalid following_count: {following}")

        # Check posts_count
        posts = snapshot_data.get("posts_count")
        if posts is not None:
            total_checks += 1
            if isinstance(posts, int) and posts >= 0:
                valid_count += 1
            else:
                issues.append(f"Invalid posts_count: {posts}")

        validity_score = valid_count / total_checks if total_checks > 0 else 0.0

        # Consistency checks
        # Check if followers > following (usually true)
        if followers is not None and following is not None:
            if followers < following:
                issues.append("Followers count is less than following count (unusual)")
                consistency_score = 0.5
            else:
                consistency_score = 1.0
        else:
            consistency_score = 1.0

        # Overall score (weighted average)
        overall_score = (
            completeness_score * 0.4 + validity_score * 0.4 + consistency_score * 0.2
        )

        return {
            "score": round(overall_score, 3),
            "completeness": round(completeness_score, 3),
            "validity": round(validity_score, 3),
            "consistency": round(consistency_score, 3),
            "issues": issues,
        }

    def score_post(self, post_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Score quality of a post.

        Args:
            post_data: Post data dictionary

        Returns:
            Dictionary with quality score and details
        """
        issues = []
        completeness_score = 0.0
        validity_score = 0.0

        # Required fields
        required_fields = ["post_id", "account_key"]
        present_fields = sum(
            1 for field in required_fields if post_data.get(field) is not None
        )
        completeness_score = present_fields / len(required_fields)

        # Validity checks
        valid_count = 0
        total_checks = 0

        # Check post_id
        post_id = post_data.get("post_id")
        if post_id:
            total_checks += 1
            if isinstance(post_id, str) and len(post_id) > 0:
                valid_count += 1
            else:
                issues.append("Invalid post_id")

        # Check caption_text (optional but good to have)
        caption = post_data.get("caption_text")
        if caption:
            total_checks += 1
            if isinstance(caption, str) and len(caption) > 0:
                valid_count += 1
            else:
                issues.append("Invalid caption_text")

        validity_score = valid_count / total_checks if total_checks > 0 else 1.0

        # Overall score
        overall_score = completeness_score * 0.6 + validity_score * 0.4

        return {
            "score": round(overall_score, 3),
            "completeness": round(completeness_score, 3),
            "validity": round(validity_score, 3),
            "issues": issues,
        }

    def generate_quality_report(
        self,
        snapshots: List[Dict[str, Any]],
        posts: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a data quality report.

        Args:
            snapshots: List of snapshot data dictionaries
            posts: Optional list of post data dictionaries

        Returns:
            Dictionary with quality report
        """
        if not snapshots:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "snapshot_count": 0,
                "post_count": 0,
                "average_snapshot_score": 0.0,
                "average_post_score": 0.0,
                "summary": "No data to analyze",
            }

        # Score all snapshots
        snapshot_scores = [self.score_snapshot(s) for s in snapshots]
        avg_snapshot_score = sum(s["score"] for s in snapshot_scores) / len(
            snapshot_scores
        )

        # Score posts if provided
        post_scores = []
        if posts:
            post_scores = [self.score_post(p) for p in posts]

        avg_post_score = (
            sum(s["score"] for s in post_scores) / len(post_scores)
            if post_scores
            else 0.0
        )

        # Collect all issues
        all_issues = []
        for score in snapshot_scores:
            all_issues.extend(score.get("issues", []))
        for score in post_scores:
            all_issues.extend(score.get("issues", []))

        # Count issues by type
        issue_counts = {}
        for issue in all_issues:
            issue_type = issue.split(":")[0] if ":" in issue else issue
            issue_counts[issue_type] = issue_counts.get(issue_type, 0) + 1

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "snapshot_count": len(snapshots),
            "post_count": len(posts) if posts else 0,
            "average_snapshot_score": round(avg_snapshot_score, 3),
            "average_post_score": round(avg_post_score, 3),
            "total_issues": len(all_issues),
            "issue_counts": issue_counts,
            "summary": f"Analyzed {len(snapshots)} snapshots and {len(posts) if posts else 0} posts. "
            f"Average quality score: {avg_snapshot_score:.2%}",
        }


# Global data quality scorer
_quality_scorer: Optional[DataQualityScorer] = None


def get_quality_scorer() -> DataQualityScorer:
    """Get or create global data quality scorer."""
    global _quality_scorer
    if _quality_scorer is None:
        _quality_scorer = DataQualityScorer()
    return _quality_scorer

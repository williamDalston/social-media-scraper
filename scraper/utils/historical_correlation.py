"""
Historical data correlation and analysis.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class HistoricalCorrelator:
    """
    Correlates current data with historical patterns.
    """

    def __init__(self):
        """Initialize historical correlator."""
        self._historical_data: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        logger.info("Initialized HistoricalCorrelator")

    def add_snapshot(self, account_key: int, snapshot: Dict[str, Any]):
        """
        Add a snapshot to historical data.

        Args:
            account_key: Account key
            snapshot: Snapshot data dictionary
        """
        # Add timestamp if not present
        if "snapshot_date" not in snapshot:
            snapshot["snapshot_date"] = datetime.utcnow().date().isoformat()

        self._historical_data[account_key].append(snapshot)

        # Keep only recent history (last 90 days)
        cutoff_date = datetime.utcnow().date() - timedelta(days=90)
        self._historical_data[account_key] = [
            s
            for s in self._historical_data[account_key]
            if datetime.fromisoformat(s.get("snapshot_date", "2000-01-01")).date()
            >= cutoff_date
        ]

        # Sort by date (most recent first)
        self._historical_data[account_key].sort(
            key=lambda x: x.get("snapshot_date", ""), reverse=True
        )

    def correlate_with_history(
        self,
        account_key: int,
        current_snapshot: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Correlate current snapshot with historical data.

        Args:
            account_key: Account key
            current_snapshot: Current snapshot data

        Returns:
            Dictionary with correlation results:
            {
                'is_consistent': bool,
                'correlation_score': float,
                'anomalies': List[str],
                'trends': Dict[str, Any]
            }
        """
        if account_key not in self._historical_data:
            return {
                "is_consistent": True,
                "correlation_score": 1.0,
                "anomalies": [],
                "trends": {},
                "message": "No historical data available",
            }

        history = self._historical_data[account_key]

        if len(history) < 3:
            return {
                "is_consistent": True,
                "correlation_score": 1.0,
                "anomalies": [],
                "trends": {},
                "message": "Insufficient historical data",
            }

        anomalies = []
        correlation_score = 1.0

        # Compare with recent history
        recent = history[:7]  # Last 7 snapshots

        # Check follower count consistency
        current_followers = current_snapshot.get("followers_count", 0) or 0
        historical_followers = [s.get("followers_count", 0) or 0 for s in recent]

        if historical_followers:
            avg_followers = sum(historical_followers) / len(historical_followers)
            max_followers = max(historical_followers)
            min_followers = min(historical_followers)

            # Check for unusual changes
            if current_followers > max_followers * 1.2:
                anomalies.append(
                    f"Followers increased unusually: {current_followers} vs max {max_followers}"
                )
                correlation_score -= 0.2
            elif current_followers < min_followers * 0.8:
                anomalies.append(
                    f"Followers decreased unusually: {current_followers} vs min {min_followers}"
                )
                correlation_score -= 0.2

        # Calculate trends
        trends = self._calculate_trends(history, current_snapshot)

        correlation_score = max(0.0, min(1.0, correlation_score))

        return {
            "is_consistent": len(anomalies) == 0,
            "correlation_score": round(correlation_score, 3),
            "anomalies": anomalies,
            "trends": trends,
            "historical_data_points": len(history),
        }

    def _calculate_trends(
        self,
        history: List[Dict[str, Any]],
        current: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Calculate trends from historical data.

        Args:
            history: Historical snapshots
            current: Current snapshot

        Returns:
            Dictionary with trend information
        """
        trends = {}

        # Follower trend
        followers_history = [s.get("followers_count", 0) or 0 for s in history]
        current_followers = current.get("followers_count", 0) or 0

        if len(followers_history) >= 2:
            # Calculate average daily change
            oldest = followers_history[-1]
            newest = followers_history[0]

            if oldest > 0:
                total_change = newest - oldest
                days = len(followers_history)
                avg_daily_change = total_change / days if days > 0 else 0

                trends["follower_trend"] = {
                    "direction": "up" if avg_daily_change > 0 else "down",
                    "average_daily_change": round(avg_daily_change, 2),
                    "total_change": total_change,
                }

        # Engagement trend
        engagement_history = [
            (s.get("likes_count", 0) or 0)
            + (s.get("comments_count", 0) or 0)
            + (s.get("shares_count", 0) or 0)
            for s in history
        ]

        if engagement_history:
            avg_engagement = sum(engagement_history) / len(engagement_history)
            current_engagement = (
                (current.get("likes_count", 0) or 0)
                + (current.get("comments_count", 0) or 0)
                + (current.get("shares_count", 0) or 0)
            )

            trends["engagement_trend"] = {
                "current": current_engagement,
                "average": round(avg_engagement, 2),
                "direction": "up" if current_engagement > avg_engagement else "down",
            }

        return trends

    def get_historical_summary(self, account_key: int) -> Dict[str, Any]:
        """
        Get summary of historical data for an account.

        Args:
            account_key: Account key

        Returns:
            Dictionary with historical summary
        """
        if account_key not in self._historical_data:
            return {
                "data_points": 0,
                "date_range": None,
            }

        history = self._historical_data[account_key]

        if not history:
            return {
                "data_points": 0,
                "date_range": None,
            }

        dates = [s.get("snapshot_date") for s in history if s.get("snapshot_date")]

        return {
            "data_points": len(history),
            "date_range": {
                "earliest": min(dates) if dates else None,
                "latest": max(dates) if dates else None,
            },
            "followers_range": {
                "min": min(s.get("followers_count", 0) or 0 for s in history),
                "max": max(s.get("followers_count", 0) or 0 for s in history),
                "average": sum(s.get("followers_count", 0) or 0 for s in history)
                / len(history),
            },
        }


# Global historical correlator
_historical_correlator: Optional[HistoricalCorrelator] = None


def get_historical_correlator() -> HistoricalCorrelator:
    """Get or create global historical correlator."""
    global _historical_correlator
    if _historical_correlator is None:
        _historical_correlator = HistoricalCorrelator()
    return _historical_correlator

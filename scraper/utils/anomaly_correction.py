"""
Anomaly detection and automatic correction.
"""

import logging
from typing import Dict, Any, Optional, List

from .anomaly_detector import get_anomaly_detector
from .historical_correlation import get_historical_correlator

logger = logging.getLogger(__name__)


class AnomalyCorrector:
    """
    Detects and corrects data anomalies.
    """

    def __init__(self):
        """Initialize anomaly corrector."""
        self.anomaly_detector = get_anomaly_detector()
        self.historical_correlator = get_historical_correlator()
        logger.info("Initialized AnomalyCorrector")

    def detect_and_correct(
        self,
        account_key: int,
        current_data: Dict[str, Any],
        previous_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Detect and correct anomalies in data.

        Args:
            account_key: Account key
            current_data: Current snapshot data
            previous_data: Previous snapshot data

        Returns:
            Dictionary with correction results:
            {
                'original_data': Dict,
                'corrected_data': Dict,
                'corrections_applied': List[str],
                'anomalies_detected': List[str],
                'confidence': float
            }
        """
        original_data = current_data.copy()
        corrected_data = current_data.copy()
        corrections_applied = []
        anomalies_detected = []

        # Detect anomalies
        anomaly_result = self.anomaly_detector.detect_anomalies(
            account_key, current_data, threshold=3.0
        )

        if anomaly_result["has_anomalies"]:
            anomalies_detected = anomaly_result["anomalies"]

            # Attempt corrections
            for anomaly in anomalies_detected:
                correction = self._correct_anomaly(
                    account_key, corrected_data, anomaly, previous_data
                )

                if correction:
                    corrections_applied.append(correction)

        # Correlate with history
        correlation = self.historical_correlator.correlate_with_history(
            account_key, corrected_data
        )

        # Calculate confidence
        confidence = 1.0
        if anomalies_detected:
            confidence -= len(anomalies_detected) * 0.1
        if not correlation["is_consistent"]:
            confidence -= 0.2
        confidence = max(0.0, min(1.0, confidence))

        return {
            "original_data": original_data,
            "corrected_data": corrected_data,
            "corrections_applied": corrections_applied,
            "anomalies_detected": anomalies_detected,
            "confidence": round(confidence, 3),
            "correlation": correlation,
        }

    def _correct_anomaly(
        self,
        account_key: int,
        data: Dict[str, Any],
        anomaly: str,
        previous_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Attempt to correct a specific anomaly.

        Args:
            account_key: Account key
            data: Data dictionary to correct
            anomaly: Anomaly description
            previous_data: Previous snapshot data

        Returns:
            Correction description if correction applied, None otherwise
        """
        # Parse anomaly to extract metric and value
        # Example: "followers_count: increase of 5.23 standard deviations (current: 1000000, mean: 500000)"

        if "followers_count" in anomaly:
            # Check if we can use previous data to correct
            if previous_data and "followers_count" in previous_data:
                previous_value = previous_data.get("followers_count", 0)
                current_value = data.get("followers_count", 0)

                # If change is too large, might be a scraping error
                # Use previous value as fallback (conservative approach)
                if abs(current_value - previous_value) > previous_value * 0.5:
                    logger.warning(
                        f"Large change detected for account {account_key}. "
                        f"Previous: {previous_value}, Current: {current_value}"
                    )
                    # Don't auto-correct, just flag it
                    return None

        # For other anomalies, log but don't auto-correct
        logger.debug(f"Anomaly detected but not auto-corrected: {anomaly}")
        return None

    def validate_correction(
        self,
        original: Dict[str, Any],
        corrected: Dict[str, Any],
    ) -> bool:
        """
        Validate that a correction is reasonable.

        Args:
            original: Original data
            corrected: Corrected data

        Returns:
            True if correction is valid, False otherwise
        """
        # Check that correction doesn't change data too drastically
        for key in ["followers_count", "following_count", "posts_count"]:
            if key in original and key in corrected:
                original_val = original.get(key, 0) or 0
                corrected_val = corrected.get(key, 0) or 0

                if original_val > 0:
                    change_pct = (
                        abs((corrected_val - original_val) / original_val) * 100
                    )
                    if change_pct > 50:  # More than 50% change
                        logger.warning(
                            f"Correction changes {key} by {change_pct:.1f}%, "
                            "which seems excessive"
                        )
                        return False

        return True


# Global anomaly corrector
_anomaly_corrector: Optional[AnomalyCorrector] = None


def get_anomaly_corrector() -> AnomalyCorrector:
    """Get or create global anomaly corrector."""
    global _anomaly_corrector
    if _anomaly_corrector is None:
        _anomaly_corrector = AnomalyCorrector()
    return _anomaly_corrector

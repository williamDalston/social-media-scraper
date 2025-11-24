"""
SLO/SLA (Service Level Objective/Agreement) tracking and monitoring.
Tracks service availability, latency, error rates, and other SLAs.
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import deque, defaultdict
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SLO:
    """Service Level Objective definition."""

    name: str
    metric: str  # 'availability', 'latency', 'error_rate', 'throughput'
    target: float  # Target value (e.g., 99.9 for 99.9% availability)
    window_minutes: int = 60  # Time window for evaluation
    enabled: bool = True


@dataclass
class SLOMeasurement:
    """SLO measurement result."""

    slo_name: str
    timestamp: datetime
    value: float
    target: float
    status: str  # 'met', 'at_risk', 'breached'
    window_start: datetime
    window_end: datetime


class SLOTracker:
    """Tracks SLOs and calculates compliance."""

    def __init__(self):
        self.slos: Dict[str, SLO] = {}
        self.measurements: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._setup_default_slos()

    def _setup_default_slos(self):
        """Set up default SLOs for the application."""
        # Availability SLO: 99.9% uptime
        self.add_slo(
            SLO(
                name="api_availability",
                metric="availability",
                target=99.9,
                window_minutes=60,
            )
        )

        # Latency SLO: 95% of requests < 2 seconds
        self.add_slo(
            SLO(
                name="api_latency_p95",
                metric="latency_p95",
                target=2000.0,  # milliseconds
                window_minutes=60,
            )
        )

        # Error rate SLO: < 1% error rate
        self.add_slo(
            SLO(
                name="api_error_rate",
                metric="error_rate",
                target=1.0,  # percentage
                window_minutes=60,
            )
        )

        # Scraper success rate SLO: > 95% success rate
        self.add_slo(
            SLO(
                name="scraper_success_rate",
                metric="success_rate",
                target=95.0,  # percentage
                window_minutes=1440,  # 24 hours
            )
        )

    def add_slo(self, slo: SLO):
        """Add or update an SLO."""
        self.slos[slo.name] = slo
        logger.info(f"Added SLO: {slo.name} - {slo.metric} target: {slo.target}")

    def record_metric(
        self, slo_name: str, value: float, timestamp: Optional[datetime] = None
    ):
        """
        Record a metric value for SLO tracking.

        Args:
            slo_name: Name of the SLO
            value: Metric value
            timestamp: Timestamp (defaults to now)
        """
        if slo_name not in self.slos:
            logger.warning(f"SLO {slo_name} not found")
            return

        if timestamp is None:
            timestamp = datetime.utcnow()

        self.measurements[slo_name].append({"timestamp": timestamp, "value": value})

    def evaluate_slo(self, slo_name: str) -> Optional[SLOMeasurement]:
        """
        Evaluate an SLO and return measurement.

        Args:
            slo_name: Name of the SLO to evaluate

        Returns:
            SLOMeasurement or None if SLO not found
        """
        if slo_name not in self.slos:
            return None

        slo = self.slos[slo_name]
        if not slo.enabled:
            return None

        # Get measurements in the time window
        window_end = datetime.utcnow()
        window_start = window_end - timedelta(minutes=slo.window_minutes)

        relevant_measurements = [
            m
            for m in self.measurements[slo_name]
            if window_start <= m["timestamp"] <= window_end
        ]

        if not relevant_measurements:
            return None

        # Calculate metric value based on type
        if slo.metric == "availability":
            # Availability = (successful requests / total requests) * 100
            total = len(relevant_measurements)
            successful = sum(
                1 for m in relevant_measurements if m["value"] < 500
            )  # HTTP < 500
            value = (successful / total * 100) if total > 0 else 0
            status = "met" if value >= slo.target else "breached"

        elif slo.metric == "latency_p95":
            # P95 latency
            values = sorted([m["value"] for m in relevant_measurements])
            if values:
                p95_index = int(len(values) * 0.95)
                value = values[p95_index] if p95_index < len(values) else values[-1]
            else:
                value = 0
            status = "met" if value <= slo.target else "breached"

        elif slo.metric == "error_rate":
            # Error rate percentage
            total = len(relevant_measurements)
            errors = sum(1 for m in relevant_measurements if m["value"] >= 400)
            value = (errors / total * 100) if total > 0 else 0
            status = "met" if value <= slo.target else "breached"

        elif slo.metric == "success_rate":
            # Success rate percentage
            total = len(relevant_measurements)
            successful = sum(
                1 for m in relevant_measurements if m["value"] == 1
            )  # 1 = success
            value = (successful / total * 100) if total > 0 else 0
            status = "met" if value >= slo.target else "breached"

        else:
            # Default: average value
            values = [m["value"] for m in relevant_measurements]
            value = sum(values) / len(values) if values else 0
            status = "met" if value >= slo.target else "breached"

        # Determine if at risk (within 5% of target)
        if status == "met":
            if slo.metric in ["availability", "success_rate"]:
                if value < slo.target * 1.05:  # Within 5% of target
                    status = "at_risk"
            elif slo.metric in ["latency_p95", "error_rate"]:
                if value > slo.target * 0.95:  # Within 5% of target
                    status = "at_risk"

        return SLOMeasurement(
            slo_name=slo_name,
            timestamp=window_end,
            value=value,
            target=slo.target,
            status=status,
            window_start=window_start,
            window_end=window_end,
        )

    def evaluate_all_slos(self) -> Dict[str, SLOMeasurement]:
        """Evaluate all enabled SLOs."""
        results = {}
        for slo_name in self.slos:
            measurement = self.evaluate_slo(slo_name)
            if measurement:
                results[slo_name] = measurement
        return results

    def get_slo_compliance(self, slo_name: str, days: int = 30) -> Dict:
        """
        Get SLO compliance over a period.

        Args:
            slo_name: Name of the SLO
            days: Number of days to analyze

        Returns:
            Dictionary with compliance statistics
        """
        if slo_name not in self.slos:
            return {}

        # Evaluate SLO multiple times over the period
        # (In production, this would query historical data)
        evaluations = []
        for i in range(days):
            # Simulate daily evaluation
            pass

        # For now, return current evaluation
        measurement = self.evaluate_slo(slo_name)
        if not measurement:
            return {}

        return {
            "slo_name": slo_name,
            "current_status": measurement.status,
            "current_value": measurement.value,
            "target": measurement.target,
            "compliance_percent": (measurement.value / measurement.target * 100)
            if measurement.target > 0
            else 0,
            "window_minutes": self.slos[slo_name].window_minutes,
        }


# Global SLO tracker instance
slo_tracker = SLOTracker()


def record_slo_metric(
    slo_name: str, value: float, timestamp: Optional[datetime] = None
):
    """Convenience function to record SLO metric."""
    slo_tracker.record_metric(slo_name, value, timestamp)


def get_slo_status() -> Dict:
    """Get status of all SLOs."""
    evaluations = slo_tracker.evaluate_all_slos()

    return {
        "slos": {
            name: {
                "status": measurement.status,
                "value": measurement.value,
                "target": measurement.target,
                "compliance": (measurement.value / measurement.target * 100)
                if measurement.target > 0
                else 0,
                "window_start": measurement.window_start.isoformat(),
                "window_end": measurement.window_end.isoformat(),
            }
            for name, measurement in evaluations.items()
        },
        "timestamp": datetime.utcnow().isoformat(),
    }

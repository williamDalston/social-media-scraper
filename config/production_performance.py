"""
Production performance optimization and SLA tracking.
"""
import os
import time
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import deque
from threading import Lock
from enum import Enum

logger = logging.getLogger(__name__)


class SLAStatus(Enum):
    """SLA status levels."""

    MET = "met"
    WARNING = "warning"
    VIOLATED = "violated"
    UNKNOWN = "unknown"


class PerformanceSLA:
    """Performance SLA definition and tracking."""

    def __init__(
        self,
        name: str,
        metric: str,
        target_p95: float,
        target_p99: float,
        warning_threshold: float = 0.8,
        unit: str = "seconds",
    ):
        """
        Initialize performance SLA.

        Args:
            name: SLA name
            metric: Metric name to track
            target_p95: Target p95 latency in seconds
            target_p99: Target p99 latency in seconds
            warning_threshold: Warning threshold (0.8 = 80% of target)
            unit: Unit of measurement
        """
        self.name = name
        self.metric = metric
        self.target_p95 = target_p95
        self.target_p99 = target_p99
        self.warning_threshold = warning_threshold
        self.unit = unit
        self._lock = Lock()
        self._measurements = deque(maxlen=10000)  # Keep last 10k measurements

    def record(self, value: float, timestamp: Optional[datetime] = None):
        """Record a measurement."""
        if timestamp is None:
            timestamp = datetime.utcnow()

        with self._lock:
            self._measurements.append({"value": value, "timestamp": timestamp})

    def get_status(self) -> Tuple[SLAStatus, Dict]:
        """
        Get current SLA status.

        Returns:
            Tuple of (status, details)
        """
        with self._lock:
            if not self._measurements:
                return SLAStatus.UNKNOWN, {"message": "No measurements yet"}

            # Get recent measurements (last hour)
            cutoff = datetime.utcnow() - timedelta(hours=1)
            recent = [m for m in self._measurements if m["timestamp"] >= cutoff]

            if not recent:
                return SLAStatus.UNKNOWN, {"message": "No recent measurements"}

            values = sorted([m["value"] for m in recent])
            p95_idx = int(len(values) * 0.95)
            p99_idx = int(len(values) * 0.99)

            p95 = values[p95_idx] if p95_idx < len(values) else values[-1]
            p99 = values[p99_idx] if p99_idx < len(values) else values[-1]

            # Check violations
            p95_violated = p95 > self.target_p95
            p99_violated = p99 > self.target_p99

            # Check warnings
            p95_warning = p95 > (self.target_p95 * self.warning_threshold)
            p99_warning = p99 > (self.target_p99 * self.warning_threshold)

            if p95_violated or p99_violated:
                status = SLAStatus.VIOLATED
            elif p95_warning or p99_warning:
                status = SLAStatus.WARNING
            else:
                status = SLAStatus.MET

            details = {
                "p95": round(p95, 3),
                "p99": round(p99, 3),
                "target_p95": self.target_p95,
                "target_p99": self.target_p99,
                "p95_violated": p95_violated,
                "p99_violated": p99_violated,
                "p95_warning": p95_warning,
                "p99_warning": p99_warning,
                "sample_count": len(recent),
                "unit": self.unit,
            }

            return status, details

    def get_stats(self) -> Dict:
        """Get detailed statistics."""
        with self._lock:
            if not self._measurements:
                return {"count": 0}

            values = [m["value"] for m in self._measurements]
            sorted_values = sorted(values)

            return {
                "count": len(values),
                "min": min(values) if values else 0,
                "max": max(values) if values else 0,
                "avg": sum(values) / len(values) if values else 0,
                "p50": sorted_values[int(len(sorted_values) * 0.50)]
                if sorted_values
                else 0,
                "p95": sorted_values[int(len(sorted_values) * 0.95)]
                if sorted_values
                else 0,
                "p99": sorted_values[int(len(sorted_values) * 0.99)]
                if sorted_values
                else 0,
                "target_p95": self.target_p95,
                "target_p99": self.target_p99,
            }


class ProductionPerformanceManager:
    """Manages production performance SLAs and optimization."""

    def __init__(self):
        """Initialize performance manager."""
        self._lock = Lock()
        self._slas: Dict[str, PerformanceSLA] = {}

        # Define production SLAs
        self._initialize_slas()

    def _initialize_slas(self):
        """Initialize production SLAs."""
        # API Response Time SLAs
        self._slas["api_response_p95"] = PerformanceSLA(
            name="API Response Time (p95)",
            metric="api_response",
            target_p95=0.5,  # 500ms p95
            target_p99=1.0,  # 1s p99
            unit="seconds",
        )

        self._slas["api_response_p99"] = PerformanceSLA(
            name="API Response Time (p99)",
            metric="api_response",
            target_p95=0.5,
            target_p99=2.0,  # 2s p99
            unit="seconds",
        )

        # Database Query SLAs
        self._slas["db_query_p95"] = PerformanceSLA(
            name="Database Query Time (p95)",
            metric="db_query",
            target_p95=0.1,  # 100ms p95
            target_p99=0.5,  # 500ms p99
            unit="seconds",
        )

        # Cache Performance SLAs
        self._slas["cache_hit_rate"] = PerformanceSLA(
            name="Cache Hit Rate",
            metric="cache_hit_rate",
            target_p95=80.0,  # 80% hit rate
            target_p99=75.0,  # 75% hit rate
            unit="percent",
        )

        # Scraper Performance SLAs
        self._slas["scraper_execution_p95"] = PerformanceSLA(
            name="Scraper Execution Time (p95)",
            metric="scraper_execution",
            target_p95=5.0,  # 5s p95
            target_p99=10.0,  # 10s p99
            unit="seconds",
        )

        # Frontend Load Time SLAs
        self._slas["frontend_load_p95"] = PerformanceSLA(
            name="Frontend Load Time (p95)",
            metric="frontend_load",
            target_p95=2.0,  # 2s p95
            target_p99=3.0,  # 3s p99
            unit="seconds",
        )

    def record_metric(
        self, metric_name: str, value: float, timestamp: Optional[datetime] = None
    ):
        """Record a performance metric."""
        # Find matching SLA
        for sla_name, sla in self._slas.items():
            if sla.metric == metric_name:
                sla.record(value, timestamp)
                break

    def get_sla_status(self, sla_name: Optional[str] = None) -> Dict:
        """
        Get SLA status for a specific SLA or all SLAs.

        Args:
            sla_name: Specific SLA name, or None for all

        Returns:
            Dictionary with SLA statuses
        """
        with self._lock:
            if sla_name:
                if sla_name not in self._slas:
                    return {"error": f"SLA {sla_name} not found"}

                sla = self._slas[sla_name]
                status, details = sla.get_status()
                return {
                    "sla_name": sla_name,
                    "name": sla.name,
                    "status": status.value,
                    "details": details,
                    "stats": sla.get_stats(),
                }
            else:
                # Return all SLAs
                result = {}
                for name, sla in self._slas.items():
                    status, details = sla.get_status()
                    result[name] = {
                        "name": sla.name,
                        "status": status.value,
                        "details": details,
                        "stats": sla.get_stats(),
                    }
                return result

    def check_violations(self) -> List[Dict]:
        """
        Check for SLA violations.

        Returns:
            List of violations
        """
        violations = []

        with self._lock:
            for sla_name, sla in self._slas.items():
                status, details = sla.get_status()

                if status == SLAStatus.VIOLATED:
                    violations.append(
                        {
                            "sla_name": sla_name,
                            "name": sla.name,
                            "status": status.value,
                            "details": details,
                            "severity": "high"
                            if details.get("p95_violated")
                            else "medium",
                        }
                    )
                elif status == SLAStatus.WARNING:
                    violations.append(
                        {
                            "sla_name": sla_name,
                            "name": sla.name,
                            "status": status.value,
                            "details": details,
                            "severity": "warning",
                        }
                    )

        return violations

    def get_performance_summary(self) -> Dict:
        """Get overall performance summary."""
        with self._lock:
            violations = self.check_violations()
            sla_statuses = self.get_sla_status()

            total_slas = len(self._slas)
            met_count = sum(
                1 for s in sla_statuses.values() if s["status"] == SLAStatus.MET.value
            )
            warning_count = sum(
                1
                for s in sla_statuses.values()
                if s["status"] == SLAStatus.WARNING.value
            )
            violated_count = sum(
                1
                for s in sla_statuses.values()
                if s["status"] == SLAStatus.VIOLATED.value
            )

            return {
                "total_slas": total_slas,
                "met": met_count,
                "warnings": warning_count,
                "violations": violated_count,
                "compliance_rate": (met_count / total_slas * 100)
                if total_slas > 0
                else 0,
                "violations": violations,
                "timestamp": datetime.utcnow().isoformat(),
            }


# Global instance
_performance_manager: Optional[ProductionPerformanceManager] = None
_performance_manager_lock = Lock()


def get_performance_manager() -> ProductionPerformanceManager:
    """Get global performance manager instance."""
    global _performance_manager
    with _performance_manager_lock:
        if _performance_manager is None:
            _performance_manager = ProductionPerformanceManager()
        return _performance_manager


def record_performance_metric(
    metric_name: str, value: float, timestamp: Optional[datetime] = None
):
    """Record a performance metric."""
    manager = get_performance_manager()
    manager.record_metric(metric_name, value, timestamp)


def get_sla_status(sla_name: Optional[str] = None) -> Dict:
    """Get SLA status."""
    manager = get_performance_manager()
    return manager.get_sla_status(sla_name)


def check_performance_violations() -> List[Dict]:
    """Check for performance violations."""
    manager = get_performance_manager()
    return manager.check_violations()


def get_performance_summary() -> Dict:
    """Get performance summary."""
    manager = get_performance_manager()
    return manager.get_performance_summary()

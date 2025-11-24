"""
Performance SLAs (Service Level Agreements) definition and tracking.
"""
from dataclasses import dataclass
from typing import Dict, Optional
from datetime import datetime, timedelta


@dataclass
class PerformanceSLA:
    """Performance SLA definition."""

    name: str
    metric: str  # 'response_time', 'throughput', 'error_rate'
    target: float  # Target value
    unit: str  # 'ms', 'rps', 'percent'
    severity: str  # 'critical', 'warning'
    description: str


class PerformanceSLATracker:
    """Tracks performance SLAs."""

    def __init__(self):
        self.slas = {
            "api_response_time_p95": PerformanceSLA(
                name="API Response Time (p95)",
                metric="response_time",
                target=200.0,  # 200ms
                unit="ms",
                severity="critical",
                description="95th percentile API response time should be under 200ms",
            ),
            "api_response_time_p99": PerformanceSLA(
                name="API Response Time (p99)",
                metric="response_time",
                target=500.0,  # 500ms
                unit="ms",
                severity="warning",
                description="99th percentile API response time should be under 500ms",
            ),
            "api_throughput": PerformanceSLA(
                name="API Throughput",
                metric="throughput",
                target=100.0,  # 100 requests/second
                unit="rps",
                severity="critical",
                description="API should handle at least 100 requests per second",
            ),
            "database_query_time": PerformanceSLA(
                name="Database Query Time",
                metric="query_time",
                target=100.0,  # 100ms
                unit="ms",
                severity="critical",
                description="Database queries should complete in under 100ms (p95)",
            ),
            "cache_hit_rate": PerformanceSLA(
                name="Cache Hit Rate",
                metric="hit_rate",
                target=80.0,  # 80%
                unit="percent",
                severity="warning",
                description="Cache hit rate should be above 80%",
            ),
            "scraper_success_rate": PerformanceSLA(
                name="Scraper Success Rate",
                metric="success_rate",
                target=95.0,  # 95%
                unit="percent",
                severity="critical",
                description="Scraper success rate should be above 95%",
            ),
        }

    def check_sla_compliance(self, metric_name: str, current_value: float) -> Dict:
        """Check if current value meets SLA."""
        if metric_name not in self.slas:
            return {"error": "SLA not found"}

        sla = self.slas[metric_name]

        # Determine if value meets target based on metric type
        if sla.metric in ["response_time", "query_time"]:
            # Lower is better
            meets_sla = current_value <= sla.target
        else:
            # Higher is better (throughput, hit_rate, success_rate)
            meets_sla = current_value >= sla.target

        return {
            "sla_name": sla.name,
            "target": sla.target,
            "current": current_value,
            "unit": sla.unit,
            "meets_sla": meets_sla,
            "severity": sla.severity,
            "status": "compliant" if meets_sla else "non-compliant",
        }

    def get_all_sla_status(self, metrics: Dict[str, float]) -> Dict:
        """Get status for all SLAs."""
        status = {}
        for metric_name, current_value in metrics.items():
            if metric_name in self.slas:
                status[metric_name] = self.check_sla_compliance(
                    metric_name, current_value
                )
        return status


# Global SLA tracker
performance_sla_tracker = PerformanceSLATracker()

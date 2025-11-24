"""
Data insights and recommendations engine.
Analyzes data patterns and provides actionable insights.
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class Insight:
    """Represents a data insight."""

    insight_id: str
    category: str  # 'performance', 'quality', 'usage', 'trend'
    title: str
    description: str
    severity: str  # 'info', 'warning', 'critical'
    confidence: float  # 0.0 to 1.0
    recommendation: str
    metadata: Dict
    timestamp: datetime


class DataInsightsEngine:
    """Generates insights and recommendations from data."""

    def __init__(self):
        self.insights: List[Insight] = []
        self.insight_counter = 0

    def analyze_performance(self) -> List[Insight]:
        """Analyze performance data and generate insights."""
        insights = []

        try:
            from config.performance_monitoring import (
                get_query_statistics,
                get_slow_queries,
            )
            from config.slo_sla_tracking import get_slo_status

            query_stats = get_query_statistics()
            slow_queries = get_slow_queries(limit=5)
            slo_status = get_slo_status()
        except ImportError:
            return []

        # Query performance insights
        if query_stats.get("p95_duration", 0) > 1.0:
            self.insight_counter += 1
            insight = Insight(
                insight_id=f"PERF-{self.insight_counter:04d}",
                category="performance",
                title="Slow Query Performance",
                description=f"P95 query duration is {query_stats['p95_duration']:.2f}s, exceeding 1s target",
                severity="warning",
                confidence=0.9,
                recommendation="Review slow queries and add indexes or optimize queries",
                metadata={"p95_duration": query_stats["p95_duration"]},
                timestamp=datetime.utcnow(),
            )
            insights.append(insight)
            self.insights.append(insight)

        # Slow query insights
        if len(slow_queries) > 10:
            self.insight_counter += 1
            insight = Insight(
                insight_id=f"PERF-{self.insight_counter:04d}",
                category="performance",
                title="High Number of Slow Queries",
                description=f"{len(slow_queries)} slow queries detected",
                severity="warning",
                confidence=0.85,
                recommendation="Investigate and optimize frequently slow queries",
                metadata={"slow_query_count": len(slow_queries)},
                timestamp=datetime.utcnow(),
            )
            insights.append(insight)
            self.insights.append(insight)

        # SLO insights
        if slo_status.get("slos"):
            for slo_name, slo_data in slo_status["slos"].items():
                if slo_data["status"] != "met":
                    self.insight_counter += 1
                    insight = Insight(
                        insight_id=f"SLO-{self.insight_counter:04d}",
                        category="performance",
                        title=f"SLO Violation: {slo_name}",
                        description=f"SLO {slo_name} is {slo_data['status']} (value: {slo_data['value']:.2f}, target: {slo_data['target']})",
                        severity="critical"
                        if slo_data["status"] == "breached"
                        else "warning",
                        confidence=1.0,
                        recommendation=f"Address issues affecting {slo_name} to meet SLO",
                        metadata=slo_data,
                        timestamp=datetime.utcnow(),
                    )
                    insights.append(insight)
                    self.insights.append(insight)

        return insights

    def analyze_data_quality(self) -> List[Insight]:
        """Analyze data quality and generate insights."""
        insights = []

        try:
            from config.business_metrics import get_business_metrics_summary

            metrics = get_business_metrics_summary()
        except ImportError:
            return []

        # Scraping success rate insights
        success_rate = metrics.get("success_rate", 100)
        if success_rate < 95:
            self.insight_counter += 1
            insight = Insight(
                insight_id=f"QUAL-{self.insight_counter:04d}",
                category="quality",
                title="Low Scraping Success Rate",
                description=f"Scraping success rate is {success_rate:.1f}% (target: >95%)",
                severity="warning",
                confidence=0.95,
                recommendation="Investigate scraper failures and improve success rate",
                metadata={"success_rate": success_rate},
                timestamp=datetime.utcnow(),
            )
            insights.append(insight)
            self.insights.append(insight)

        return insights

    def analyze_usage_patterns(self) -> List[Insight]:
        """Analyze usage patterns and generate insights."""
        insights = []

        try:
            from config.usage_analytics import usage_analytics

            usage_summary = usage_analytics.get_usage_summary(hours=168)  # 7 days
            endpoint_usage = usage_analytics.get_endpoint_usage(hours=168)
        except ImportError:
            return []

        # Identify underutilized endpoints
        if endpoint_usage:
            total_calls = sum(endpoint_usage.values())
            avg_calls = total_calls / len(endpoint_usage) if endpoint_usage else 0

            underutilized = [
                (endpoint, count)
                for endpoint, count in endpoint_usage.items()
                if count < avg_calls * 0.1  # Less than 10% of average
            ]

            if underutilized:
                self.insight_counter += 1
                insight = Insight(
                    insight_id=f"USAGE-{self.insight_counter:04d}",
                    category="usage",
                    title="Underutilized Endpoints",
                    description=f"{len(underutilized)} endpoints have low usage",
                    severity="info",
                    confidence=0.8,
                    recommendation="Consider documenting or deprecating underutilized endpoints",
                    metadata={"underutilized_endpoints": underutilized},
                    timestamp=datetime.utcnow(),
                )
                insights.append(insight)
                self.insights.append(insight)

        return insights

    def analyze_trends(self) -> List[Insight]:
        """Analyze trends and generate insights."""
        insights = []

        try:
            from config.trend_analysis import trend_analyzer

            # Analyze key metrics
            metrics_to_analyze = ["api_latency", "scraper_success_rate", "error_rate"]

            for metric in metrics_to_analyze:
                trend = trend_analyzer.calculate_trend(metric)
                if not trend:
                    continue

                if (
                    trend.get("direction") == "decreasing"
                    and trend.get("change_percent", 0) < -10
                ):
                    self.insight_counter += 1
                    insight = Insight(
                        insight_id=f"TREND-{self.insight_counter:04d}",
                        category="trend",
                        title=f"Declining Trend: {metric}",
                        description=f"{metric} is decreasing by {abs(trend.get('change_percent', 0)):.1f}%",
                        severity="warning",
                        confidence=0.85,
                        recommendation=f"Investigate why {metric} is declining",
                        metadata=trend,
                        timestamp=datetime.utcnow(),
                    )
                    insights.append(insight)
                    self.insights.append(insight)
        except ImportError:
            pass

        return insights

    def generate_all_insights(self) -> List[Insight]:
        """Generate all insights."""
        all_insights = []
        all_insights.extend(self.analyze_performance())
        all_insights.extend(self.analyze_data_quality())
        all_insights.extend(self.analyze_usage_patterns())
        all_insights.extend(self.analyze_trends())

        return sorted(
            all_insights,
            key=lambda x: (
                {"critical": 0, "warning": 1, "info": 2}.get(x.severity, 3),
                -x.confidence,
            ),
        )

    def get_recent_insights(
        self, hours: int = 24, category: Optional[str] = None
    ) -> List[Insight]:
        """Get recent insights."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        insights = [i for i in self.insights if i.timestamp >= cutoff]

        if category:
            insights = [i for i in insights if i.category == category]

        return sorted(insights, key=lambda x: x.timestamp, reverse=True)


# Global insights engine instance
insights_engine = DataInsightsEngine()

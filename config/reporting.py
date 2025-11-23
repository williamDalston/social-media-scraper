"""
Automated reporting system.
Generates performance reports, trend reports, and executive summaries.
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Report:
    """Represents a generated report."""
    report_id: str
    report_type: str  # 'performance', 'trend', 'executive', 'usage'
    title: str
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    data: Dict
    insights: List[str]
    recommendations: List[str]


class ReportGenerator:
    """Generates various types of reports."""
    
    def __init__(self):
        self.reports: List[Report] = []
        self.report_counter = 0
    
    def generate_performance_report(self, period_days: int = 7) -> Report:
        """
        Generate performance report.
        
        Args:
            period_days: Number of days to analyze
        
        Returns:
            Performance report
        """
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=period_days)
        
        # Gather performance data
        try:
            from config.performance_monitoring import get_query_statistics, get_resource_usage_trends
            from config.slo_sla_tracking import get_slo_status
            
            query_stats = get_query_statistics()
            resource_trends = get_resource_usage_trends()
            slo_status = get_slo_status()
        except ImportError:
            query_stats = {}
            resource_trends = {}
            slo_status = {}
        
        # Generate insights
        insights = []
        recommendations = []
        
        if query_stats.get('p95_duration', 0) > 1.0:
            insights.append(f"P95 query duration is {query_stats['p95_duration']:.2f}s (target: <1s)")
            recommendations.append("Consider optimizing slow queries or adding indexes")
        
        if resource_trends.get('memory', {}).get('rss_mb', 0) > 1000:
            insights.append(f"Memory usage is {resource_trends['memory']['rss_mb']:.1f}MB")
            recommendations.append("Monitor for memory leaks and consider optimizing memory usage")
        
        # Check SLO compliance
        if slo_status.get('slos'):
            for slo_name, slo_data in slo_status['slos'].items():
                if slo_data['status'] != 'met':
                    insights.append(f"SLO {slo_name} is {slo_data['status']}")
                    recommendations.append(f"Investigate and fix issues affecting {slo_name}")
        
        self.report_counter += 1
        report = Report(
            report_id=f"PERF-{self.report_counter:04d}",
            report_type='performance',
            title=f"Performance Report - {period_days} days",
            generated_at=datetime.utcnow(),
            period_start=period_start,
            period_end=period_end,
            data={
                'query_statistics': query_stats,
                'resource_trends': resource_trends,
                'slo_status': slo_status
            },
            insights=insights,
            recommendations=recommendations
        )
        
        self.reports.append(report)
        return report
    
    def generate_trend_report(self, metric_name: str, period_days: int = 30) -> Report:
        """
        Generate trend report for a metric.
        
        Args:
            metric_name: Name of the metric
            period_days: Number of days to analyze
        
        Returns:
            Trend report
        """
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=period_days)
        
        try:
            from config.trend_analysis import trend_analyzer
            
            trend = trend_analyzer.calculate_trend(metric_name)
            forecast = trend_analyzer.forecast(metric_name, periods=7)
        except ImportError:
            trend = {}
            forecast = []
        
        insights = []
        recommendations = []
        
        if trend.get('direction') == 'increasing':
            insights.append(f"{metric_name} is trending upward ({trend.get('change_percent', 0):.1f}% change)")
        elif trend.get('direction') == 'decreasing':
            insights.append(f"{metric_name} is trending downward ({trend.get('change_percent', 0):.1f}% change)")
            recommendations.append(f"Investigate why {metric_name} is decreasing")
        
        self.report_counter += 1
        report = Report(
            report_id=f"TREND-{self.report_counter:04d}",
            report_type='trend',
            title=f"Trend Report: {metric_name}",
            generated_at=datetime.utcnow(),
            period_start=period_start,
            period_end=period_end,
            data={
                'metric_name': metric_name,
                'trend': trend,
                'forecast': forecast
            },
            insights=insights,
            recommendations=recommendations
        )
        
        self.reports.append(report)
        return report
    
    def generate_executive_report(self, period_days: int = 30) -> Report:
        """
        Generate executive summary report.
        
        Args:
            period_days: Number of days to analyze
        
        Returns:
            Executive report
        """
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=period_days)
        
        # Gather high-level metrics
        try:
            from config.business_metrics import get_business_metrics_summary
            from config.usage_analytics import usage_analytics
            from config.slo_sla_tracking import get_slo_status
            
            business_metrics = get_business_metrics_summary()
            usage_summary = usage_analytics.get_usage_summary(hours=period_days * 24)
            slo_status = get_slo_status()
        except ImportError:
            business_metrics = {}
            usage_summary = {}
            slo_status = {}
        
        # Generate executive insights
        insights = []
        recommendations = []
        
        # Business metrics insights
        if business_metrics.get('success_rate', 100) < 95:
            insights.append(f"Scraping success rate is {business_metrics.get('success_rate', 0):.1f}% (target: >95%)")
            recommendations.append("Investigate scraper failures and improve success rate")
        
        # Usage insights
        if usage_summary.get('active_users', 0) > 0:
            insights.append(f"{usage_summary.get('active_users', 0)} active users in the last {period_days} days")
        
        # SLO insights
        if slo_status.get('slos'):
            met_count = sum(1 for s in slo_status['slos'].values() if s['status'] == 'met')
            total_count = len(slo_status['slos'])
            insights.append(f"{met_count}/{total_count} SLOs are being met")
            
            if met_count < total_count:
                recommendations.append("Address SLO violations to improve service quality")
        
        self.report_counter += 1
        report = Report(
            report_id=f"EXEC-{self.report_counter:04d}",
            report_type='executive',
            title=f"Executive Summary - {period_days} days",
            generated_at=datetime.utcnow(),
            period_start=period_start,
            period_end=period_end,
            data={
                'business_metrics': business_metrics,
                'usage_summary': usage_summary,
                'slo_status': slo_status
            },
            insights=insights,
            recommendations=recommendations
        )
        
        self.reports.append(report)
        return report
    
    def generate_usage_report(self, period_days: int = 7) -> Report:
        """
        Generate usage analytics report.
        
        Args:
            period_days: Number of days to analyze
        
        Returns:
            Usage report
        """
        period_end = datetime.utcnow()
        period_start = period_end - timedelta(days=period_days)
        
        try:
            from config.usage_analytics import usage_analytics
            
            usage_summary = usage_analytics.get_usage_summary(hours=period_days * 24)
            endpoint_usage = usage_analytics.get_endpoint_usage(hours=period_days * 24)
            feature_usage = usage_analytics.get_feature_usage(hours=period_days * 24)
            active_users = usage_analytics.get_active_users(hours=period_days * 24)
        except ImportError:
            usage_summary = {}
            endpoint_usage = {}
            feature_usage = {}
            active_users = []
        
        insights = []
        recommendations = []
        
        # Top endpoints
        if endpoint_usage:
            top_endpoint = max(endpoint_usage.items(), key=lambda x: x[1])
            insights.append(f"Most used endpoint: {top_endpoint[0]} ({top_endpoint[1]} calls)")
        
        # Active users
        insights.append(f"{len(active_users)} active users")
        
        # Feature usage
        if feature_usage:
            top_feature = max(feature_usage.items(), key=lambda x: x[1])
            insights.append(f"Most used feature: {top_feature[0]} ({top_feature[1]} uses)")
        
        self.report_counter += 1
        report = Report(
            report_id=f"USAGE-{self.report_counter:04d}",
            report_type='usage',
            title=f"Usage Report - {period_days} days",
            generated_at=datetime.utcnow(),
            period_start=period_start,
            period_end=period_end,
            data={
                'usage_summary': usage_summary,
                'endpoint_usage': endpoint_usage,
                'feature_usage': feature_usage,
                'active_users_count': len(active_users)
            },
            insights=insights,
            recommendations=recommendations
        )
        
        self.reports.append(report)
        return report
    
    def get_recent_reports(self, report_type: Optional[str] = None, limit: int = 10) -> List[Report]:
        """Get recent reports."""
        reports = self.reports
        
        if report_type:
            reports = [r for r in reports if r.report_type == report_type]
        
        return sorted(reports, key=lambda x: x.generated_at, reverse=True)[:limit]


# Global report generator instance
report_generator = ReportGenerator()


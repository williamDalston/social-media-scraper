"""
Analytics API endpoints.
Provides endpoints for trend analysis, usage analytics, and comparative analysis.
"""
import logging
from flask import Blueprint, jsonify, request
from auth.decorators import require_auth, require_any_role
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/analytics")


@analytics_bp.route("/trends", methods=["GET"])
@require_any_role(["Admin", "Viewer"])
def get_trends():
    """Get trend analysis for metrics."""
    try:
        from config.trend_analysis import trend_analyzer

        metric_name = request.args.get("metric", type=str)
        window_minutes = request.args.get("window_minutes", type=int)

        if metric_name:
            trend = trend_analyzer.calculate_trend(metric_name, window_minutes)
            forecast = trend_analyzer.forecast(metric_name, periods=7) if trend else []

            return jsonify(
                {
                    "metric": metric_name,
                    "trend": trend,
                    "forecast": forecast,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
        else:
            # Return trends for all tracked metrics
            trends = {}
            for metric_name in trend_analyzer.metric_data.keys():
                trend = trend_analyzer.calculate_trend(metric_name)
                if trend:
                    trends[metric_name] = trend

            return jsonify(
                {"trends": trends, "timestamp": datetime.utcnow().isoformat()}
            )
    except Exception as e:
        logger.exception("Failed to get trends")
        return jsonify({"error": str(e)}), 500


@analytics_bp.route("/compare", methods=["GET"])
@require_any_role(["Admin", "Viewer"])
def compare_periods():
    """Compare metrics between two time periods."""
    try:
        from config.trend_analysis import trend_analyzer

        metric_name = request.args.get("metric", type=str)
        period1_start = request.args.get("period1_start", type=str)
        period1_end = request.args.get("period1_end", type=str)
        period2_start = request.args.get("period2_start", type=str)
        period2_end = request.args.get("period2_end", type=str)

        if not all(
            [metric_name, period1_start, period1_end, period2_start, period2_end]
        ):
            return jsonify({"error": "All parameters required"}), 400

        try:
            p1_start = datetime.fromisoformat(period1_start.replace("Z", "+00:00"))
            p1_end = datetime.fromisoformat(period1_end.replace("Z", "+00:00"))
            p2_start = datetime.fromisoformat(period2_start.replace("Z", "+00:00"))
            p2_end = datetime.fromisoformat(period2_end.replace("Z", "+00:00"))
        except ValueError:
            return jsonify({"error": "Invalid date format"}), 400

        comparison = trend_analyzer.compare_periods(
            metric_name, p1_start, p1_end, p2_start, p2_end
        )

        return jsonify(
            {"comparison": comparison, "timestamp": datetime.utcnow().isoformat()}
        )
    except Exception as e:
        logger.exception("Failed to compare periods")
        return jsonify({"error": str(e)}), 500


@analytics_bp.route("/usage", methods=["GET"])
@require_any_role(["Admin", "Viewer"])
def get_usage_analytics():
    """Get usage analytics."""
    try:
        from config.usage_analytics import usage_analytics

        hours = request.args.get("hours", 24, type=int)
        user_id = request.args.get("user_id", type=str)

        if user_id:
            activity = usage_analytics.get_user_activity(user_id, hours=hours)
            return jsonify(
                {
                    "user_id": user_id,
                    "activity": [
                        {
                            "event_type": e.event_type,
                            "endpoint": e.endpoint,
                            "timestamp": e.timestamp.isoformat(),
                            "metadata": e.metadata,
                        }
                        for e in activity
                    ],
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
        else:
            summary = usage_analytics.get_usage_summary(hours=hours)
            endpoint_usage = usage_analytics.get_endpoint_usage(hours=hours)
            feature_usage = usage_analytics.get_feature_usage(hours=hours)
            active_users = usage_analytics.get_active_users(hours=hours)

            return jsonify(
                {
                    "summary": summary,
                    "endpoint_usage": endpoint_usage,
                    "feature_usage": feature_usage,
                    "active_users": active_users,
                    "active_user_count": len(active_users),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
    except Exception as e:
        logger.exception("Failed to get usage analytics")
        return jsonify({"error": str(e)}), 500


@analytics_bp.route("/benchmarks", methods=["GET"])
@require_any_role(["Admin", "Viewer"])
def get_benchmarks():
    """Get performance benchmarks."""
    try:
        from config.performance_benchmarking import performance_benchmarker

        summary = performance_benchmarker.get_benchmark_summary()

        return jsonify(
            {"benchmarks": summary, "timestamp": datetime.utcnow().isoformat()}
        )
    except Exception as e:
        logger.exception("Failed to get benchmarks")
        return jsonify({"error": str(e)}), 500

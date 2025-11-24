"""
Performance SLA API endpoints.
"""
from flask import Blueprint, jsonify
from datetime import datetime
from auth.decorators import require_auth, require_any_role
from config.performance_slas import performance_sla_tracker
from cache import get_metrics
from scraper.optimization.db_optimization import get_query_stats

performance_sla_bp = Blueprint(
    "performance_slas", __name__, url_prefix="/api/performance/slas"
)


@performance_sla_bp.route("/status", methods=["GET"])
@require_auth
@require_any_role(["Admin", "Viewer"])
def get_performance_sla_status():
    """Get performance SLA compliance status."""
    try:
        # Get current metrics
        cache_metrics = get_metrics()
        query_stats = get_query_stats()

        # Build metrics dictionary
        metrics = {
            "api_response_time_p95": cache_metrics.get("p95_response_time", 0),
            "api_response_time_p99": cache_metrics.get("p99_response_time", 0),
            "api_throughput": cache_metrics.get("requests_per_second", 0),
            "database_query_time": query_stats.get("p95_time", 0)
            * 1000,  # Convert to ms
            "cache_hit_rate": cache_metrics.get("cache_hit_rate", 0)
            * 100,  # Convert to percent
            "scraper_success_rate": cache_metrics.get("scraper_success_rate", 0)
            * 100,  # Convert to percent
        }

        # Get SLA status
        sla_status = performance_sla_tracker.get_all_sla_status(metrics)

        # Calculate overall compliance
        total_slas = len(sla_status)
        compliant_slas = sum(
            1 for s in sla_status.values() if s.get("meets_sla", False)
        )
        compliance_rate = (compliant_slas / total_slas * 100) if total_slas > 0 else 0

        return (
            jsonify(
                {
                    "slas": sla_status,
                    "overall_compliance": {
                        "rate": compliance_rate,
                        "compliant": compliant_slas,
                        "total": total_slas,
                    },
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ),
            200,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

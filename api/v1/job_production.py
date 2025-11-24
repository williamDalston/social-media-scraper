"""
Production job management and monitoring API endpoints.
"""
from flask_restx import Namespace, Resource, fields
from flask import request
from auth.decorators import require_any_role
from tasks.production_optimization import (
    calculate_optimal_schedule_time,
    intelligent_backoff,
    get_worker_scaling_recommendation,
    optimize_job_distribution,
    get_resource_usage_optimization,
)
from tasks.scaling import get_scaling_strategy, implement_auto_scaling
from tasks.job_checkpointing import (
    save_job_checkpoint,
    load_job_checkpoint,
    resume_job_from_checkpoint,
    save_job_state,
    load_job_state,
)
from tasks.job_alerting import (
    check_job_failures_and_alert,
    check_sla_violations_and_alert,
    check_queue_backlog_and_alert,
    check_worker_health_and_alert,
)
from tasks.job_management import get_job_performance_analytics, calculate_job_sla_status
from tasks.utils import get_db_session
from models.job import Job

ns = Namespace("job-production", description="Production job management and monitoring")

# Response models
scaling_recommendation_model = ns.model(
    "ScalingRecommendation",
    {
        "current_workers": fields.Integer(description="Current worker count"),
        "recommended_workers": fields.Integer(description="Recommended worker count"),
        "scale_up": fields.Boolean(description="Whether to scale up"),
        "scale_down": fields.Boolean(description="Whether to scale down"),
        "reason": fields.String(description="Reason for recommendation"),
    },
)

optimization_recommendation_model = ns.model(
    "OptimizationRecommendation",
    {
        "type": fields.String(description="Type of recommendation"),
        "severity": fields.String(description="Severity level"),
        "message": fields.String(description="Recommendation message"),
        "suggestion": fields.String(description="Suggested action"),
    },
)


@ns.route("/scaling/recommendation")
@ns.doc(security="Bearer Auth")
class ScalingRecommendation(Resource):
    """Get worker scaling recommendations."""

    @ns.doc("get_scaling_recommendation")
    @ns.marshal_with(scaling_recommendation_model)
    @ns.response(200, "Success")
    @ns.response(401, "Unauthorized")
    @require_any_role(["Admin", "Editor"])
    def get(self):
        """Get worker scaling recommendation based on queue depth."""
        return get_worker_scaling_recommendation()


@ns.route("/scaling/strategy")
@ns.doc(security="Bearer Auth")
class ScalingStrategy(Resource):
    """Get horizontal scaling strategy."""

    @ns.doc("get_scaling_strategy")
    @ns.response(200, "Success")
    @ns.response(401, "Unauthorized")
    @require_any_role(["Admin", "Editor"])
    def get(self):
        """Get horizontal scaling strategy and recommendations."""
        from tasks.scaling import get_scaling_strategy

        return get_scaling_strategy()


@ns.route("/distribution/optimize")
@ns.doc(security="Bearer Auth")
class OptimizeDistribution(Resource):
    """Optimize job distribution across workers."""

    @ns.doc("optimize_distribution")
    @ns.response(200, "Success")
    @ns.response(401, "Unauthorized")
    @require_any_role(["Admin", "Editor"])
    def post(self):
        """Optimize job distribution across workers."""
        return optimize_job_distribution()


@ns.route("/optimization/recommendations")
@ns.doc(security="Bearer Auth")
class OptimizationRecommendations(Resource):
    """Get resource usage optimization recommendations."""

    @ns.doc("get_optimization_recommendations")
    @ns.response(200, "Success")
    @ns.response(401, "Unauthorized")
    @require_any_role(["Admin", "Editor", "Viewer"])
    def get(self):
        """Get recommendations for resource usage optimization."""
        return get_resource_usage_optimization()


@ns.route("/<job_id>/checkpoint")
@ns.doc(security="Bearer Auth")
@ns.param("job_id", "Job ID")
class JobCheckpoint(Resource):
    """Manage job checkpoints."""

    @ns.doc("save_checkpoint")
    @ns.response(200, "Success")
    @ns.response(401, "Unauthorized")
    @require_any_role(["Admin", "Editor"])
    def post(self, job_id):
        """Save a checkpoint for a job."""
        data = request.get_json() or {}
        checkpoint_data = data.get("checkpoint_data", {})
        checkpoint_name = data.get("checkpoint_name", "default")

        success = save_job_checkpoint(job_id, checkpoint_data, checkpoint_name)
        return {"success": success, "checkpoint_name": checkpoint_name}

    @ns.doc("load_checkpoint")
    @ns.response(200, "Success")
    @ns.response(401, "Unauthorized")
    @require_any_role(["Admin", "Editor", "Viewer"])
    def get(self, job_id):
        """Load a checkpoint for a job."""
        checkpoint_name = request.args.get("checkpoint_name", "default")
        checkpoint = load_job_checkpoint(job_id, checkpoint_name)

        if checkpoint:
            return {"checkpoint_name": checkpoint_name, "data": checkpoint}
        else:
            return {"checkpoint_name": checkpoint_name, "data": None}, 404


@ns.route("/<job_id>/resume")
@ns.doc(security="Bearer Auth")
@ns.param("job_id", "Job ID")
class ResumeJobFromCheckpoint(Resource):
    """Resume a job from checkpoint."""

    @ns.doc("resume_from_checkpoint")
    @ns.response(200, "Success")
    @ns.response(401, "Unauthorized")
    @require_any_role(["Admin", "Editor"])
    def post(self, job_id):
        """Resume a job from a checkpoint."""
        data = request.get_json() or {}
        checkpoint_name = data.get("checkpoint_name", "default")

        checkpoint = resume_job_from_checkpoint(job_id, checkpoint_name)

        if checkpoint:
            return {"success": True, "checkpoint_data": checkpoint}
        else:
            return {"success": False, "message": "No checkpoint found"}, 404


@ns.route("/alerts/check")
@ns.doc(security="Bearer Auth")
class CheckAlerts(Resource):
    """Check for job alerts."""

    @ns.doc("check_alerts")
    @ns.response(200, "Success")
    @ns.response(401, "Unauthorized")
    @require_any_role(["Admin", "Editor"])
    def get(self):
        """Check for various job alerts."""
        alerts = {
            "failures": check_job_failures_and_alert(),
            "sla_violations": check_sla_violations_and_alert(),
            "queue_backlog": check_queue_backlog_and_alert(),
            "worker_health": check_worker_health_and_alert(),
        }

        return alerts


@ns.route("/performance/analytics")
@ns.doc(security="Bearer Auth")
class PerformanceAnalytics(Resource):
    """Get comprehensive job performance analytics."""

    @ns.doc("get_performance_analytics")
    @ns.param("days", "Number of days to analyze", type=int, default=30)
    @ns.response(200, "Success")
    @ns.response(401, "Unauthorized")
    @require_any_role(["Admin", "Editor", "Viewer"])
    def get(self):
        """Get comprehensive job performance analytics."""
        days = request.args.get("days", 30, type=int)
        analytics = get_job_performance_analytics(days)

        # Add optimization recommendations
        optimization = get_resource_usage_optimization()
        analytics["optimization_recommendations"] = optimization.get(
            "recommendations", []
        )

        return analytics

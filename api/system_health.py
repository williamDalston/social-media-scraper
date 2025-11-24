"""
System health and error dashboard API endpoints.
Provides comprehensive system status, validation results, and error information.
"""
import os
import logging
from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from config.system_validation import SystemValidator, validate_system_on_startup
from config.pipeline_checks import PipelineValidator, validate_pipeline
from config.error_detection import (
    ErrorDetector,
    get_error_summary,
    get_fix_suggestion,
    ErrorCategory,
    ErrorSeverity,
)
from config.health_checks import run_health_checks, get_overall_health

logger = logging.getLogger(__name__)

system_health_bp = Blueprint("system_health", __name__, url_prefix="/api/system")


@system_health_bp.route("/validation", methods=["GET"])
def get_system_validation():
    """
    Get comprehensive system validation results.

    Query parameters:
        - skip_optional: Skip optional checks (default: false)

    Returns:
        JSON with validation results
    """
    try:
        skip_optional = request.args.get("skip_optional", "false").lower() == "true"

        validator = SystemValidator()
        all_passed, results = validator.validate_all(skip_optional=skip_optional)
        summary = validator.get_summary()

        return (
            jsonify(
                {
                    "status": "success",
                    "all_passed": all_passed,
                    "summary": summary,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ),
            200,
        )
    except Exception as e:
        logger.exception("Error getting system validation")
        return jsonify({"status": "error", "message": str(e)}), 500


@system_health_bp.route("/pipeline", methods=["GET"])
def get_pipeline_validation():
    """
    Get pipeline validation results.

    Returns:
        JSON with pipeline validation results
    """
    try:
        all_passed, results = validate_pipeline()
        validator = PipelineValidator()
        summary = validator.get_summary()

        return (
            jsonify(
                {
                    "status": "success",
                    "all_passed": all_passed,
                    "summary": summary,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ),
            200,
        )
    except Exception as e:
        logger.exception("Error getting pipeline validation")
        return jsonify({"status": "error", "message": str(e)}), 500


@system_health_bp.route("/health", methods=["GET"])
def get_comprehensive_health():
    """
    Get comprehensive health check results.

    Query parameters:
        - include_optional: Include optional checks (default: true)
        - use_cache: Use cached results (default: true)

    Returns:
        JSON with health check results
    """
    try:
        include_optional = (
            request.args.get("include_optional", "true").lower() == "true"
        )
        use_cache = request.args.get("use_cache", "true").lower() == "true"

        db_path = os.getenv("DATABASE_PATH", "social_media.db")
        results = run_health_checks(
            db_path=db_path, include_optional=include_optional, use_cache=use_cache
        )

        overall_health = get_overall_health(results)

        return (
            jsonify(
                {
                    "status": "success",
                    "overall_health": overall_health,
                    "checks": {
                        name: result.to_dict() for name, result in results.items()
                    },
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ),
            200,
        )
    except Exception as e:
        logger.exception("Error getting health checks")
        return jsonify({"status": "error", "message": str(e)}), 500


@system_health_bp.route("/errors", methods=["GET"])
def get_errors():
    """
    Get error summary and recent errors.

    Query parameters:
        - time_window: Time window in hours (default: 24)
        - category: Filter by category
        - severity: Filter by severity
        - limit: Limit number of results (default: 100)

    Returns:
        JSON with error summary
    """
    try:
        time_window_hours = int(request.args.get("time_window", 24))
        category_filter = request.args.get("category")
        severity_filter = request.args.get("severity")
        limit = int(request.args.get("limit", 100))

        time_window = timedelta(hours=time_window_hours)
        summary = get_error_summary(time_window)

        # Apply filters if provided
        if category_filter or severity_filter:
            # This would require access to error history
            # For now, return summary
            pass

        return (
            jsonify(
                {
                    "status": "success",
                    "summary": summary,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ),
            200,
        )
    except Exception as e:
        logger.exception("Error getting error summary")
        return jsonify({"status": "error", "message": str(e)}), 500


@system_health_bp.route("/status", methods=["GET"])
def get_system_status():
    """
    Get overall system status combining all checks.

    Returns:
        JSON with comprehensive system status
    """
    try:
        # Run all checks
        system_validator = SystemValidator()
        system_passed, system_results = system_validator.validate_all(
            skip_optional=False
        )
        system_summary = system_validator.get_summary()

        pipeline_passed, pipeline_summary = validate_pipeline()

        db_path = os.getenv("DATABASE_PATH", "social_media.db")
        health_results = run_health_checks(
            db_path=db_path, include_optional=True, use_cache=False
        )
        overall_health = get_overall_health(health_results)

        error_summary = get_error_summary(timedelta(hours=24))

        # Determine overall status
        overall_status = "healthy"
        if not system_passed or not pipeline_passed:
            overall_status = "unhealthy"
        elif overall_health != "healthy":
            overall_status = "degraded"
        elif error_summary["total_errors"] > 100:
            overall_status = "degraded"

        return (
            jsonify(
                {
                    "status": "success",
                    "overall_status": overall_status,
                    "system_validation": {
                        "passed": system_passed,
                        "summary": system_summary,
                    },
                    "pipeline_validation": {
                        "passed": pipeline_passed,
                        "summary": pipeline_summary,
                    },
                    "health_checks": {
                        "overall": overall_health,
                        "checks": {
                            name: result.to_dict()
                            for name, result in health_results.items()
                        },
                    },
                    "errors": error_summary,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ),
            200,
        )
    except Exception as e:
        logger.exception("Error getting system status")
        return (
            jsonify(
                {"status": "error", "message": str(e), "overall_status": "unknown"}
            ),
            500,
        )


@system_health_bp.route("/diagnostics", methods=["GET"])
def get_diagnostics():
    """
    Get diagnostic information for troubleshooting.

    Returns:
        JSON with diagnostic information
    """
    try:
        diagnostics = {
            "environment": {
                "python_version": os.sys.version,
                "flask_env": os.getenv("FLASK_ENV", "development"),
                "database_path": os.getenv("DATABASE_PATH", "social_media.db"),
                "log_directory": os.getenv("LOG_DIRECTORY", "logs"),
            },
            "system_validation": None,
            "pipeline_validation": None,
            "health_checks": None,
            "recent_errors": None,
        }

        # Get system validation
        try:
            validator = SystemValidator()
            _, _ = validator.validate_all(skip_optional=True)
            diagnostics["system_validation"] = validator.get_summary()
        except Exception as e:
            diagnostics["system_validation"] = {"error": str(e)}

        # Get pipeline validation
        try:
            _, pipeline_summary = validate_pipeline()
            diagnostics["pipeline_validation"] = pipeline_summary
        except Exception as e:
            diagnostics["pipeline_validation"] = {"error": str(e)}

        # Get health checks
        try:
            db_path = os.getenv("DATABASE_PATH", "social_media.db")
            health_results = run_health_checks(
                db_path=db_path, include_optional=False, use_cache=False
            )
            diagnostics["health_checks"] = {
                name: result.to_dict() for name, result in health_results.items()
            }
        except Exception as e:
            diagnostics["health_checks"] = {"error": str(e)}

        # Get recent errors
        try:
            diagnostics["recent_errors"] = get_error_summary(timedelta(hours=1))
        except Exception as e:
            diagnostics["recent_errors"] = {"error": str(e)}

        return (
            jsonify(
                {
                    "status": "success",
                    "diagnostics": diagnostics,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ),
            200,
        )
    except Exception as e:
        logger.exception("Error getting diagnostics")
        return jsonify({"status": "error", "message": str(e)}), 500

"""
Horizontal scaling and auto-scaling utilities.
"""
import logging
import os
from tasks.job_management import get_queue_depth, get_job_backlog, get_worker_health
from tasks.production_optimization import get_worker_scaling_recommendation

logger = logging.getLogger(__name__)


def get_scaling_strategy():
    """
    Get horizontal scaling strategy recommendations.

    Returns:
        dict: Scaling strategy
    """
    backlog = get_job_backlog()
    worker_health = get_worker_health()
    scaling_rec = get_worker_scaling_recommendation()

    return {
        "current_state": {
            "workers": worker_health.get("total_workers", 0),
            "active_workers": worker_health.get("active_workers", 0),
            "pending_jobs": backlog.get("total_pending", 0),
            "queue_depth": backlog.get("scraping_queue_depth", 0),
        },
        "recommendation": scaling_rec,
        "scaling_strategy": {
            "scale_up_threshold": 50,  # Scale up if pending > 50
            "scale_down_threshold": 5,  # Scale down if pending < 5
            "min_workers": 1,
            "max_workers": int(os.getenv("MAX_WORKERS", "10")),
            "target_workers": scaling_rec.get("recommended_workers", 1),
        },
    }


def implement_auto_scaling():
    """
    Implement auto-scaling based on queue depth.
    This would integrate with container orchestration (K8s, Docker Swarm, etc.)

    Returns:
        dict: Auto-scaling action taken
    """
    scaling_strategy = get_scaling_strategy()
    recommendation = scaling_strategy["recommendation"]
    strategy = scaling_strategy["scaling_strategy"]

    current_workers = recommendation["current_workers"]
    target_workers = strategy["target_workers"]

    if recommendation["scale_up"]:
        # Scale up logic
        # In production, this would:
        # 1. Call K8s API to scale deployment
        # 2. Or call Docker Swarm API
        # 3. Or trigger cloud auto-scaling (AWS, GCP, Azure)

        logger.info(
            f"Auto-scaling: Scale up from {current_workers} to {target_workers} workers"
        )

        return {
            "action": "scale_up",
            "from_workers": current_workers,
            "to_workers": target_workers,
            "reason": recommendation["reason"],
        }

    elif recommendation["scale_down"] and current_workers > strategy["min_workers"]:
        # Scale down logic
        logger.info(
            f"Auto-scaling: Scale down from {current_workers} to {target_workers} workers"
        )

        return {
            "action": "scale_down",
            "from_workers": current_workers,
            "to_workers": max(strategy["min_workers"], target_workers),
            "reason": "Low queue depth",
        }

    return {
        "action": "no_action",
        "current_workers": current_workers,
        "reason": "Workers are appropriately scaled",
    }


def optimize_job_distribution_horizontal():
    """
    Optimize job distribution for horizontal scaling.

    Returns:
        dict: Distribution optimization
    """
    from tasks.production_optimization import optimize_job_distribution

    distribution = optimize_job_distribution()

    if distribution.get("needs_rebalancing"):
        # In production, would implement job rebalancing
        # This could involve:
        # 1. Revoking tasks from overloaded workers
        # 2. Re-queuing them for underloaded workers
        # 3. Adjusting worker priorities

        logger.info("Job distribution needs rebalancing")
        return {
            "action": "rebalance_needed",
            "distribution": distribution,
            "recommendation": "Consider rebalancing jobs across workers",
        }

    return {"action": "no_action", "distribution": distribution, "status": "balanced"}

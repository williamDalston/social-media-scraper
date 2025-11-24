"""
Request batching and aggregation utilities for API performance.
"""
import json
from typing import List, Dict, Any, Optional
from flask import request, jsonify
from functools import wraps


class BatchRequest:
    """Batch request handler for multiple API calls in one request."""

    def __init__(self):
        self.requests = []

    def add_request(
        self,
        method: str,
        path: str,
        params: Optional[Dict] = None,
        body: Optional[Dict] = None,
    ):
        """
        Add a request to the batch.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path
            params: Query parameters
            body: Request body (for POST/PUT)
        """
        self.requests.append(
            {"method": method, "path": path, "params": params or {}, "body": body}
        )

    def execute(self, app, session_factory):
        """
        Execute all batched requests.

        Args:
            app: Flask application
            session_factory: Database session factory

        Returns:
            List of responses
        """
        results = []
        for req in self.requests:
            try:
                # Create a test request context
                with app.test_request_context(
                    req["path"],
                    method=req["method"],
                    query_string=req["params"],
                    json=req.get("body"),
                ):
                    # Import and call the appropriate handler
                    result = self._execute_single_request(req, app, session_factory)
                    results.append({"path": req["path"], "status": 200, "data": result})
            except Exception as e:
                results.append({"path": req["path"], "status": 500, "error": str(e)})
        return results

    def _execute_single_request(self, req: Dict, app, session_factory):
        """Execute a single request from the batch."""
        # This would need to be implemented based on your route handlers
        # For now, return a placeholder
        return {"message": "Batch request executed"}


def batch_requests(max_requests: int = 10):
    """
    Decorator for batch request endpoint.

    Args:
        max_requests: Maximum number of requests in a batch
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not request.is_json:
                return jsonify({"error": "Content-Type must be application/json"}), 400

            data = request.get_json()
            requests = data.get("requests", [])

            if len(requests) > max_requests:
                return (
                    jsonify(
                        {"error": f"Maximum {max_requests} requests allowed per batch"}
                    ),
                    400,
                )

            batch = BatchRequest()
            for req in requests:
                batch.add_request(
                    req.get("method", "GET"),
                    req.get("path"),
                    req.get("params"),
                    req.get("body"),
                )

            # Execute batch
            from flask import current_app
            from scraper.schema import get_db_session

            results = batch.execute(current_app, get_db_session)

            return jsonify({"results": results, "count": len(results)})

        return wrapper

    return decorator


def aggregate_responses(responses: List[Dict]) -> Dict:
    """
    Aggregate multiple API responses into a single response.

    Args:
        responses: List of response dictionaries

    Returns:
        Aggregated response
    """
    aggregated = {
        "data": [],
        "errors": [],
        "total": len(responses),
        "success_count": 0,
        "error_count": 0,
    }

    for response in responses:
        if response.get("status") == 200:
            aggregated["data"].append(response.get("data"))
            aggregated["success_count"] += 1
        else:
            aggregated["errors"].append(
                {"path": response.get("path"), "error": response.get("error")}
            )
            aggregated["error_count"] += 1

    return aggregated

"""
Log viewer API endpoints.
Provides log search, filtering, and viewing capabilities.
"""
import os
import re
import logging
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from pathlib import Path

logger = logging.getLogger(__name__)

log_viewer_bp = Blueprint("log_viewer", __name__, url_prefix="/api/logs")


@log_viewer_bp.route("/files")
def list_log_files():
    """List available log files."""
    try:
        from config.log_retention import get_log_retention_policy

        policy = get_log_retention_policy()
        files = policy.get_log_files()

        return jsonify(
            {"files": files, "total_size_mb": round(policy.get_total_log_size_mb(), 2)}
        )
    except Exception as e:
        logger.exception("Error listing log files")
        return jsonify({"error": str(e)}), 500


@log_viewer_bp.route("/search")
def search_logs():
    """
    Search logs with filtering.

    Query parameters:
        - file: Log file name (optional)
        - level: Log level filter (optional)
        - search: Text search (optional)
        - start_time: Start time (ISO format, optional)
        - end_time: End time (ISO format, optional)
        - limit: Maximum number of results (default: 100)
    """
    try:
        from config.log_retention import get_log_retention_policy

        policy = get_log_retention_policy()
        file_name = request.args.get("file")
        level_filter = request.args.get("level")
        search_text = request.args.get("search")
        start_time = request.args.get("start_time")
        end_time = request.args.get("end_time")
        limit = int(request.args.get("limit", 100))

        # Parse time filters
        start_dt = datetime.fromisoformat(start_time) if start_time else None
        end_dt = datetime.fromisoformat(end_time) if end_time else None

        # Get log files to search
        if file_name:
            log_files = [f for f in policy.get_log_files() if f["name"] == file_name]
        else:
            log_files = policy.get_log_files()[:5]  # Limit to 5 most recent

        results = []

        for file_info in log_files:
            file_path = Path(file_info["path"])
            if not file_path.exists():
                continue

            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, 1):
                        if len(results) >= limit:
                            break

                        # Apply filters
                        if level_filter and level_filter.upper() not in line.upper():
                            continue

                        if search_text and search_text.lower() not in line.lower():
                            continue

                        # Try to parse timestamp from log line
                        line_time = _extract_timestamp(line)
                        if line_time:
                            if start_dt and line_time < start_dt:
                                continue
                            if end_dt and line_time > end_dt:
                                continue

                        results.append(
                            {
                                "file": file_info["name"],
                                "line_number": line_num,
                                "content": line.rstrip(),
                                "timestamp": line_time.isoformat()
                                if line_time
                                else None,
                            }
                        )
            except Exception as e:
                logger.error(f"Error reading log file {file_path}: {e}")

        return jsonify({"results": results, "count": len(results), "limit": limit})
    except Exception as e:
        logger.exception("Error searching logs")
        return jsonify({"error": str(e)}), 500


@log_viewer_bp.route("/tail/<file_name>")
def tail_log(file_name: str):
    """
    Get last N lines from a log file.

    Query parameters:
        - lines: Number of lines to return (default: 100)
    """
    try:
        from config.log_retention import get_log_retention_policy

        policy = get_log_retention_policy()
        lines = int(request.args.get("lines", 100))

        file_path = policy.log_directory / file_name
        if not file_path.exists():
            return jsonify({"error": "File not found"}), 404

        # Read last N lines
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            all_lines = f.readlines()
            tail_lines = all_lines[-lines:]

        return jsonify(
            {
                "file": file_name,
                "lines": [line.rstrip() for line in tail_lines],
                "total_lines": len(all_lines),
            }
        )
    except Exception as e:
        logger.exception(f"Error tailing log file {file_name}")
        return jsonify({"error": str(e)}), 500


def _extract_timestamp(line: str) -> Optional[datetime]:
    """Extract timestamp from log line."""
    # Try common log formats
    patterns = [
        r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})",  # ISO format
        r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})",  # Standard format
    ]

    for pattern in patterns:
        match = re.search(pattern, line)
        if match:
            try:
                timestamp_str = match.group(1).replace("T", " ")
                return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            except:
                pass

    return None

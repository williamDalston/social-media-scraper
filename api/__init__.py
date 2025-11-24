"""
API utilities for performance optimization.
"""
from .batching import BatchRequest, batch_requests, aggregate_responses
from .field_selection import parse_fields, select_fields, apply_field_selection
from .streaming import stream_json_response, stream_query_results, stream_csv_response

__all__ = [
    "BatchRequest",
    "batch_requests",
    "aggregate_responses",
    "parse_fields",
    "select_fields",
    "apply_field_selection",
    "stream_json_response",
    "stream_query_results",
    "stream_csv_response",
]

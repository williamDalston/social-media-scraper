"""
API response streaming for large datasets.
"""
import json
from typing import Iterator, Dict, Any
from flask import Response, stream_with_context
from sqlalchemy.orm import Query


def stream_json_response(data_iterator: Iterator[Dict], status: int = 200):
    """
    Stream JSON response for large datasets.

    Args:
        data_iterator: Iterator yielding dictionaries
        status: HTTP status code

    Returns:
        Flask Response with streaming JSON
    """

    def generate():
        yield "["
        first = True
        for item in data_iterator:
            if not first:
                yield ","
            yield json.dumps(item)
            first = False
        yield "]"

    return Response(
        stream_with_context(generate()), mimetype="application/json", status=status
    )


def stream_query_results(query: Query, batch_size: int = 100):
    """
    Stream database query results in batches.

    Args:
        query: SQLAlchemy query
        batch_size: Number of items per batch

    Yields:
        Dictionaries representing query results
    """
    offset = 0
    while True:
        batch = query.offset(offset).limit(batch_size).all()
        if not batch:
            break

        for item in batch:
            # Convert to dict (simplified - adjust based on your models)
            if hasattr(item, "__dict__"):
                yield {k: v for k, v in item.__dict__.items() if not k.startswith("_")}
            else:
                yield item

        if len(batch) < batch_size:
            break

        offset += batch_size


def stream_csv_response(data_iterator: Iterator[Dict], headers: list):
    """
    Stream CSV response for large datasets.

    Args:
        data_iterator: Iterator yielding dictionaries
        headers: List of CSV column headers

    Returns:
        Flask Response with streaming CSV
    """
    import csv
    import io

    def generate():
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        yield output.getvalue()
        output.seek(0)
        output.truncate(0)

        for item in data_iterator:
            row = [item.get(h, "") for h in headers]
            writer.writerow(row)
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    return Response(
        stream_with_context(generate()),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=data.csv"},
    )

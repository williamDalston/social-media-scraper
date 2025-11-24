"""
Metrics API namespace.

Endpoints for retrieving social media metrics and data.
"""

from flask_restx import Namespace, Resource, fields
from flask import request, send_file
from sqlalchemy.orm import sessionmaker
from scraper.schema import DimAccount, FactFollowersSnapshot, init_db
import io
import csv
import os
from datetime import datetime
from api.errors import NotFoundError, BadRequestError
from api.schemas import (
    SummaryItemSchema,
    HistoryDataSchema,
    GridRowSchema,
    PlatformHandleParamsSchema,
)
from api.validators import serialize_response
from auth.decorators import require_auth

ns = Namespace("metrics", description="Social media metrics and data operations")

# Flask-RESTX models for documentation
summary_item_model = ns.model(
    "SummaryItem",
    {
        "platform": fields.String(description="Social media platform"),
        "handle": fields.String(description="Account handle"),
        "followers": fields.Integer(description="Follower count"),
        "engagement": fields.Integer(description="Total engagements"),
        "posts": fields.Integer(description="Post count"),
    },
)

history_data_model = ns.model(
    "HistoryData",
    {
        "dates": fields.List(fields.Date(), description="Snapshot dates"),
        "followers": fields.List(
            fields.Integer(), description="Follower counts over time"
        ),
        "engagement": fields.List(
            fields.Integer(), description="Engagement totals over time"
        ),
    },
)

grid_row_model = ns.model(
    "GridRow",
    {
        "platform": fields.String(),
        "handle": fields.String(),
        "org_name": fields.String(),
        "snapshot_date": fields.Date(),
        "followers_count": fields.Integer(),
        "engagements_total": fields.Integer(),
        "posts_count": fields.Integer(),
        "likes_count": fields.Integer(),
        "comments_count": fields.Integer(),
        "shares_count": fields.Integer(),
    },
)

error_model = ns.model(
    "Error",
    {
        "error": fields.Nested(
            ns.model(
                "ErrorDetail",
                {
                    "code": fields.String(description="Error code"),
                    "message": fields.String(description="Error message"),
                    "details": fields.Raw(description="Additional error details"),
                },
            )
        )
    },
)


# Helper function
def get_db_session():
    db_path = os.getenv("DATABASE_PATH", "social_media.db")
    engine = init_db(db_path)
    Session = sessionmaker(bind=engine)
    return Session()


@ns.route("/summary")
@ns.doc(security="Bearer Auth")
class Summary(Resource):
    """Get summary metrics for all accounts at latest snapshot date."""

    @ns.doc("get_summary")
    @ns.marshal_list_with(summary_item_model)
    @ns.response(200, "Success")
    @ns.response(401, "Unauthorized", error_model)
    @require_auth
    def get(self):
        """
        Get summary metrics for all accounts.

        Returns metrics for all accounts at the most recent snapshot date.
        """
        session = get_db_session()

        try:
            # Get latest snapshot date
            latest_date = (
                session.query(FactFollowersSnapshot.snapshot_date)
                .order_by(FactFollowersSnapshot.snapshot_date.desc())
                .first()
            )

            if not latest_date:
                return []

            latest_date = latest_date[0]

            # Get metrics for latest date
            results = (
                session.query(DimAccount, FactFollowersSnapshot)
                .join(FactFollowersSnapshot)
                .filter(FactFollowersSnapshot.snapshot_date == latest_date)
                .all()
            )

            data = []
            for account, snapshot in results:
                data.append(
                    {
                        "platform": account.platform,
                        "handle": account.handle,
                        "followers": snapshot.followers_count,
                        "engagement": snapshot.engagements_total,
                        "posts": snapshot.posts_count,
                    }
                )

            return data
        finally:
            session.close()


@ns.route("/history/<string:platform>/<string:handle>")
@ns.doc(security="Bearer Auth")
class History(Resource):
    """Get historical metrics for a specific account."""

    @ns.doc("get_history")
    @ns.param(
        "platform",
        "Social media platform",
        _in="path",
        required=True,
        enum=["X", "Instagram", "Facebook", "LinkedIn", "YouTube", "Truth Social"],
    )
    @ns.param("handle", "Account handle", _in="path", required=True)
    @ns.marshal_with(history_data_model)
    @ns.response(200, "Success")
    @ns.response(401, "Unauthorized", error_model)
    @ns.response(404, "Account not found", error_model)
    @require_auth
    def get(self, platform, handle):
        """
        Get historical metrics for a specific account.

        Returns follower counts and engagement metrics over time.
        """
        session = get_db_session()

        try:
            account = (
                session.query(DimAccount)
                .filter_by(platform=platform, handle=handle)
                .first()
            )

            if not account:
                raise NotFoundError(
                    resource_type="Account", resource_id=f"{platform}/{handle}"
                )

            history = (
                session.query(FactFollowersSnapshot)
                .filter_by(account_key=account.account_key)
                .order_by(FactFollowersSnapshot.snapshot_date)
                .all()
            )

            data = {
                "dates": [h.snapshot_date.isoformat() for h in history],
                "followers": [h.followers_count for h in history],
                "engagement": [h.engagements_total for h in history],
            }

            return data
        finally:
            session.close()


@ns.route("/grid")
@ns.doc(security="Bearer Auth")
class Grid(Resource):
    """Get all metrics data in grid format."""

    @ns.doc("get_grid")
    @ns.marshal_list_with(grid_row_model)
    @ns.response(200, "Success")
    @ns.response(401, "Unauthorized", error_model)
    @require_auth
    def get(self):
        """
        Get all metrics data in grid format.

        Returns all account metrics with all snapshot data.
        """
        session = get_db_session()

        try:
            query = (
                session.query(
                    DimAccount.platform,
                    DimAccount.handle,
                    DimAccount.org_name,
                    FactFollowersSnapshot.snapshot_date,
                    FactFollowersSnapshot.followers_count,
                    FactFollowersSnapshot.engagements_total,
                    FactFollowersSnapshot.posts_count,
                    FactFollowersSnapshot.likes_count,
                    FactFollowersSnapshot.comments_count,
                    FactFollowersSnapshot.shares_count,
                )
                .join(FactFollowersSnapshot)
                .all()
            )

            data = []
            for row in query:
                data.append(
                    {
                        "platform": row.platform,
                        "handle": row.handle,
                        "org_name": row.org_name,
                        "snapshot_date": row.snapshot_date.isoformat()
                        if row.snapshot_date
                        else None,
                        "followers_count": row.followers_count,
                        "engagements_total": row.engagements_total,
                        "posts_count": row.posts_count,
                        "likes_count": row.likes_count,
                        "comments_count": row.comments_count,
                        "shares_count": row.shares_count,
                    }
                )

            return data
        finally:
            session.close()


@ns.route("/download")
@ns.doc(security="Bearer Auth")
class Download(Resource):
    """Download all metrics data as CSV."""

    @ns.doc("download_csv")
    @ns.produces(["text/csv"])
    @ns.response(200, "CSV file download")
    @ns.response(401, "Unauthorized", error_model)
    @require_auth
    def get(self):
        """
        Download all metrics data as CSV file.

        Returns a CSV file with all account and snapshot data.
        """
        session = get_db_session()

        try:
            query = (
                session.query(
                    DimAccount.platform,
                    DimAccount.handle,
                    DimAccount.org_name,
                    FactFollowersSnapshot.snapshot_date,
                    FactFollowersSnapshot.followers_count,
                    FactFollowersSnapshot.engagements_total,
                    FactFollowersSnapshot.posts_count,
                    FactFollowersSnapshot.likes_count,
                    FactFollowersSnapshot.comments_count,
                    FactFollowersSnapshot.shares_count,
                )
                .join(FactFollowersSnapshot)
                .all()
            )

            # Convert to CSV
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(
                [
                    "Platform",
                    "Handle",
                    "Organization",
                    "Date",
                    "Followers",
                    "Engagement Total",
                    "Posts",
                    "Likes",
                    "Comments",
                    "Shares",
                ]
            )

            for row in query:
                writer.writerow(
                    [
                        row.platform,
                        row.handle,
                        row.org_name,
                        row.snapshot_date.isoformat() if row.snapshot_date else "",
                        row.followers_count or "",
                        row.engagements_total or "",
                        row.posts_count or "",
                        row.likes_count or "",
                        row.comments_count or "",
                        row.shares_count or "",
                    ]
                )

            output.seek(0)

            return send_file(
                io.BytesIO(output.getvalue().encode("utf-8")),
                mimetype="text/csv",
                as_attachment=True,
                download_name="hhs_social_media_data.csv",
            )
        finally:
            session.close()

"""
Post-incident review system.
Tracks and manages post-incident reviews and action items.
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ReviewStatus(Enum):
    """Post-incident review status."""

    PENDING = "pending"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class ActionItem:
    """Action item from post-incident review."""

    item_id: str
    title: str
    description: str
    assigned_to: str
    due_date: Optional[datetime] = None
    status: str = "open"  # 'open', 'in_progress', 'completed', 'cancelled'
    priority: str = "medium"  # 'low', 'medium', 'high', 'critical'
    completed_at: Optional[datetime] = None
    completed_by: Optional[str] = None


@dataclass
class PostIncidentReview:
    """Post-incident review document."""

    review_id: str
    incident_id: str
    scheduled_for: datetime
    status: ReviewStatus
    participants: List[str]
    timeline: List[Dict] = field(default_factory=list)
    root_cause: Optional[str] = None
    impact_assessment: Optional[str] = None
    action_items: List[ActionItem] = field(default_factory=list)
    lessons_learned: List[str] = field(default_factory=list)
    improvements: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


class PostIncidentReviewManager:
    """Manages post-incident reviews."""

    def __init__(self):
        self.reviews: Dict[str, PostIncidentReview] = {}
        self.review_counter = 0

    def create_review(
        self, incident_id: str, scheduled_for: datetime, participants: List[str]
    ) -> PostIncidentReview:
        """
        Create a post-incident review.

        Args:
            incident_id: Incident ID to review
            scheduled_for: When review is scheduled
            participants: List of participant user IDs

        Returns:
            Created review
        """
        self.review_counter += 1
        review_id = f"PIR-{self.review_counter:04d}"

        review = PostIncidentReview(
            review_id=review_id,
            incident_id=incident_id,
            scheduled_for=scheduled_for,
            status=ReviewStatus.SCHEDULED,
            participants=participants,
        )

        self.reviews[review_id] = review

        logger.info(
            f"Created post-incident review: {review_id} for incident {incident_id}"
        )
        return review

    def start_review(self, review_id: str, started_by: str):
        """Start a review."""
        if review_id not in self.reviews:
            return False

        review = self.reviews[review_id]
        review.status = ReviewStatus.IN_PROGRESS

        review.timeline.append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "action": "review_started",
                "user": started_by,
            }
        )

        return True

    def add_action_item(
        self,
        review_id: str,
        title: str,
        description: str,
        assigned_to: str,
        priority: str = "medium",
        due_date: Optional[datetime] = None,
    ) -> ActionItem:
        """Add an action item to a review."""
        if review_id not in self.reviews:
            return None

        review = self.reviews[review_id]
        item_id = f"AI-{len(review.action_items) + 1:03d}"

        action_item = ActionItem(
            item_id=item_id,
            title=title,
            description=description,
            assigned_to=assigned_to,
            priority=priority,
            due_date=due_date,
        )

        review.action_items.append(action_item)

        review.timeline.append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "action": "action_item_added",
                "item_id": item_id,
                "assigned_to": assigned_to,
            }
        )

        return action_item

    def complete_action_item(self, review_id: str, item_id: str, completed_by: str):
        """Mark an action item as completed."""
        if review_id not in self.reviews:
            return False

        review = self.reviews[review_id]
        for item in review.action_items:
            if item.item_id == item_id:
                item.status = "completed"
                item.completed_at = datetime.utcnow()
                item.completed_by = completed_by

                review.timeline.append(
                    {
                        "timestamp": datetime.utcnow().isoformat(),
                        "action": "action_item_completed",
                        "item_id": item_id,
                        "completed_by": completed_by,
                    }
                )

                return True

        return False

    def complete_review(
        self,
        review_id: str,
        root_cause: str,
        impact_assessment: str,
        lessons_learned: List[str],
        improvements: List[str],
        completed_by: str,
    ):
        """Complete a review."""
        if review_id not in self.reviews:
            return False

        review = self.reviews[review_id]
        review.status = ReviewStatus.COMPLETED
        review.completed_at = datetime.utcnow()
        review.root_cause = root_cause
        review.impact_assessment = impact_assessment
        review.lessons_learned = lessons_learned
        review.improvements = improvements

        review.timeline.append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "action": "review_completed",
                "completed_by": completed_by,
            }
        )

        logger.info(f"Post-incident review completed: {review_id}")
        return True

    def get_review(self, review_id: str) -> Optional[PostIncidentReview]:
        """Get review by ID."""
        return self.reviews.get(review_id)

    def get_pending_reviews(self) -> List[PostIncidentReview]:
        """Get pending/scheduled reviews."""
        return [
            r
            for r in self.reviews.values()
            if r.status in [ReviewStatus.PENDING, ReviewStatus.SCHEDULED]
        ]

    def get_open_action_items(
        self, review_id: Optional[str] = None
    ) -> List[ActionItem]:
        """Get open action items."""
        items = []

        reviews = (
            [self.reviews[review_id]]
            if review_id and review_id in self.reviews
            else self.reviews.values()
        )

        for review in reviews:
            items.extend(
                [
                    item
                    for item in review.action_items
                    if item.status in ["open", "in_progress"]
                ]
            )

        return items


# Global review manager instance
review_manager = PostIncidentReviewManager()

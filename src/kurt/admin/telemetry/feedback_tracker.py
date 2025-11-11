"""Feedback-specific telemetry tracking.

Extends base telemetry infrastructure with feedback events.
"""

from typing import Literal, Optional

from kurt.admin.telemetry.config import is_telemetry_enabled
from kurt.admin.telemetry.tracker import track_event

IssueCategory = Literal["tone", "structure", "info", "comprehension", "length", "examples", "other"]


def track_feedback_submitted(
    rating: int,
    has_comment: bool = False,
    issue_category: Optional[IssueCategory] = None,
) -> None:
    """Track user feedback submission.

    Args:
        rating: User rating (1-5)
        has_comment: Whether user provided text feedback
        issue_category: Category of identified issue (if rating <= 3)
    """
    if not is_telemetry_enabled():
        return

    properties = {
        "rating": rating,
        "has_comment": has_comment,
        "issue_category": issue_category,
    }

    # Remove None values
    properties = {k: v for k, v in properties.items() if v is not None}

    track_event("feedback_submitted", properties)

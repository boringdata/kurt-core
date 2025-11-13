"""Feedback-specific telemetry tracking.

Extends base telemetry infrastructure with feedback events.
"""

from typing import Optional

from kurt.admin.telemetry.config import is_telemetry_enabled
from kurt.admin.telemetry.tracker import track_event


def track_feedback_submitted(
    passed: bool,
    comment: Optional[str] = None,
) -> None:
    """Track user feedback submission.

    Args:
        passed: Whether output met expectations (True = pass, False = fail)
        comment: Optional freeform feedback comment
    """
    if not is_telemetry_enabled():
        return

    properties = {
        "passed": passed,
        "has_comment": comment is not None and len(comment.strip()) > 0,
        "comment_length": len(comment) if comment else 0,
    }

    track_event("feedback_submitted", properties)

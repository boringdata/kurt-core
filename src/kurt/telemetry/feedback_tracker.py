"""Feedback-specific telemetry tracking.

Extends base telemetry infrastructure with feedback events.
"""

from typing import Literal, Optional

from kurt.telemetry.config import is_telemetry_enabled
from kurt.telemetry.tracker import track_event

FeedbackType = Literal["content_quality", "project_plan", "workflow_retrospective"]
IssueCategory = Literal["tone", "structure", "info", "tasks", "timeline", "phase_usefulness"]
ImprovementType = Literal["update_rule", "update_workflow", "update_config", "extract_new_rule"]


def track_feedback_submitted(
    feedback_type: FeedbackType,
    rating: int,
    has_comment: bool = False,
    issue_identified: bool = False,
    issue_category: Optional[IssueCategory] = None,
    skill_name: Optional[str] = None,
    operation: Optional[str] = None,
    workflow_used: bool = False,
    has_analytics: bool = False,
    execution_count: int = 1,
    prompted: bool = False,
) -> None:
    """Track user feedback submission.

    Args:
        feedback_type: Type of feedback loop
        rating: User rating (1-5)
        has_comment: Whether user provided text feedback
        issue_identified: Whether user identified specific issue
        issue_category: Category of identified issue
        skill_name: Name of skill being rated
        operation: Operation being rated
        workflow_used: Whether project used workflow
        has_analytics: Whether analytics configured
        execution_count: Nth execution of operation
        prompted: Whether automatic prompt or explicit request
    """
    if not is_telemetry_enabled():
        return

    properties = {
        "feedback_type": feedback_type,
        "rating": rating,
        "has_comment": has_comment,
        "issue_identified": issue_identified,
        "issue_category": issue_category,
        "skill_name": skill_name,
        "operation": operation,
        "workflow_used": workflow_used,
        "has_analytics": has_analytics,
        "execution_count": execution_count,
        "prompted": prompted,
    }

    # Remove None values
    properties = {k: v for k, v in properties.items() if v is not None}

    track_event("feedback_submitted", properties)


def track_improvement_suggested(
    feedback_type: FeedbackType,
    issue_category: IssueCategory,
    improvement_type: ImprovementType,
    user_response: Literal["accepted", "rejected", "dismissed"],
    rule_type: Optional[str] = None,
    rule_age_days: Optional[int] = None,
    content_count: Optional[int] = None,
) -> None:
    """Track improvement suggestion.

    Args:
        feedback_type: Type of feedback loop
        issue_category: Issue that triggered suggestion
        improvement_type: Type of improvement suggested
        user_response: How user responded to suggestion
        rule_type: Type of rule (if applicable)
        rule_age_days: Days since rule last updated
        content_count: Number of content pieces since last update
    """
    if not is_telemetry_enabled():
        return

    properties = {
        "feedback_type": feedback_type,
        "issue_category": issue_category,
        "improvement_type": improvement_type,
        "user_response": user_response,
        "rule_type": rule_type,
        "rule_age_days": rule_age_days,
        "content_count": content_count,
    }

    properties = {k: v for k, v in properties.items() if v is not None}

    track_event("improvement_suggested", properties)


def track_improvement_executed(
    improvement_type: ImprovementType,
    command: str,
    success: bool,
    duration_ms: int,
    rule_type: Optional[str] = None,
    content_analyzed: Optional[int] = None,
    rules_updated: Optional[int] = None,
) -> None:
    """Track improvement execution.

    Args:
        improvement_type: Type of improvement
        command: High-level command executed
        success: Whether command succeeded
        duration_ms: Execution duration
        rule_type: Type of rule (if applicable)
        content_analyzed: Number of content pieces analyzed
        rules_updated: Number of rule files modified
    """
    if not is_telemetry_enabled():
        return

    properties = {
        "improvement_type": improvement_type,
        "command": command,
        "success": success,
        "duration_ms": duration_ms,
        "rule_type": rule_type,
        "content_analyzed": content_analyzed,
        "rules_updated": rules_updated,
    }

    properties = {k: v for k, v in properties.items() if v is not None}

    track_event("improvement_executed", properties)


def track_improvement_validated(
    improvement_type: ImprovementType,
    days_since_improvement: int,
    issue_resolved: bool,
    rule_type: Optional[str] = None,
    subsequent_rating: Optional[int] = None,
) -> None:
    """Track improvement validation (next usage).

    Args:
        improvement_type: Type of improvement
        days_since_improvement: Days between improvement and validation
        issue_resolved: Whether same issue not reported again
        rule_type: Type of rule (if applicable)
        subsequent_rating: Rating on next feedback
    """
    if not is_telemetry_enabled():
        return

    properties = {
        "improvement_type": improvement_type,
        "days_since_improvement": days_since_improvement,
        "issue_resolved": issue_resolved,
        "rule_type": rule_type,
        "subsequent_rating": subsequent_rating,
    }

    properties = {k: v for k, v in properties.items() if v is not None}

    track_event("improvement_validated", properties)


def track_workflow_phase_rated(
    phase_type: str,
    phase_position: int,
    total_phases: int,
    usefulness_rating: int,
    duration_accurate: bool,
    tasks_complete: bool,
    suggested_change: bool = False,
    change_type: Optional[str] = None,
) -> None:
    """Track workflow phase rating in retrospective.

    Args:
        phase_type: Generic phase type
        phase_position: Position in workflow (1-indexed)
        total_phases: Total phases in workflow
        usefulness_rating: Rating (1-5)
        duration_accurate: Whether duration estimate was accurate
        tasks_complete: Whether all tasks were relevant
        suggested_change: Whether user suggested change
        change_type: Type of suggested change
    """
    if not is_telemetry_enabled():
        return

    properties = {
        "phase_type": phase_type,
        "phase_position": phase_position,
        "total_phases": total_phases,
        "usefulness_rating": usefulness_rating,
        "duration_accurate": duration_accurate,
        "tasks_complete": tasks_complete,
        "suggested_change": suggested_change,
        "change_type": change_type,
    }

    properties = {k: v for k, v in properties.items() if v is not None}

    track_event("workflow_phase_rated", properties)


def track_feedback_loop_completed(
    feedback_type: FeedbackType,
    loop_duration_days: int,
    suggestions_made: int,
    improvements_accepted: int,
    improvements_successful: int,
    issue_resolved: bool,
    subsequent_rating_change: int,
) -> None:
    """Track complete feedback loop from feedback to validation.

    Args:
        feedback_type: Type of feedback loop
        loop_duration_days: Days from feedback to validation
        suggestions_made: Number of suggestions offered
        improvements_accepted: Number accepted
        improvements_successful: Number that executed successfully
        issue_resolved: Whether original issue resolved
        subsequent_rating_change: Change in rating (-4 to +4)
    """
    if not is_telemetry_enabled():
        return

    properties = {
        "feedback_type": feedback_type,
        "loop_duration_days": loop_duration_days,
        "suggestions_made": suggestions_made,
        "improvements_accepted": improvements_accepted,
        "improvements_successful": improvements_successful,
        "issue_resolved": issue_resolved,
        "subsequent_rating_change": subsequent_rating_change,
    }

    track_event("feedback_loop_completed", properties)

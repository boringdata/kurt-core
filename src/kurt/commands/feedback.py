"""Kurt CLI - Feedback telemetry logging commands."""

import click
from rich.console import Console

from kurt.telemetry.feedback_tracker import (
    track_feedback_loop_completed,
    track_feedback_submitted,
    track_improvement_executed,
    track_improvement_suggested,
    track_improvement_validated,
)

console = Console()


@click.group()
def feedback():
    """Log feedback telemetry events (called by Claude Code plugin)."""
    pass


@feedback.command("log-submission")
@click.option("--type", "feedback_type", required=True,
              type=click.Choice(["content_quality", "project_plan"]),
              help="Type of feedback loop")
@click.option("--rating", required=True, type=int, help="User rating (1-5)")
@click.option("--has-comment", is_flag=True, default=False, help="Whether user provided text feedback")
@click.option("--issue-identified", is_flag=True, default=False, help="Whether user identified specific issue")
@click.option("--issue-category",
              type=click.Choice(["tone", "structure", "info", "tasks", "timeline", "phase_usefulness"]),
              help="Category of identified issue")
@click.option("--skill", "skill_name", help="Name of skill being rated")
@click.option("--operation", help="Operation being rated")
@click.option("--has-analytics", is_flag=True, default=False, help="Whether analytics configured")
@click.option("--execution-count", type=int, default=1, help="Nth execution of operation")
@click.option("--prompted", is_flag=True, default=False, help="Whether automatic prompt or explicit request")
@click.option("--event-id", required=True, help="UUID of feedback event")
def log_submission(
    feedback_type: str,
    rating: int,
    has_comment: bool,
    issue_identified: bool,
    issue_category: str,
    skill_name: str,
    operation: str,
    has_analytics: bool,
    execution_count: int,
    prompted: bool,
    event_id: str,
):
    """
    Log a feedback submission event.

    This is called by the Claude Code feedback-skill when a user submits feedback.

    Example:
        kurt feedback log-submission --type content_quality --rating 3 --event-id abc123
    """
    track_feedback_submitted(
        feedback_type=feedback_type,
        rating=rating,
        has_comment=has_comment,
        issue_identified=issue_identified,
        issue_category=issue_category,
        skill_name=skill_name,
        operation=operation,
        has_analytics=has_analytics,
        execution_count=execution_count,
        prompted=prompted,
    )

    console.print(f"[dim]✓ Logged feedback submission: {event_id}[/dim]")


@feedback.command("log-suggestion")
@click.option("--feedback-type", required=True,
              type=click.Choice(["content_quality", "project_plan"]),
              help="Type of feedback loop")
@click.option("--issue-category", required=True,
              type=click.Choice(["tone", "structure", "info", "tasks", "timeline", "phase_usefulness"]),
              help="Issue that triggered suggestion")
@click.option("--improvement-type", required=True,
              type=click.Choice(["update_rule", "update_config", "extract_new_rule"]),
              help="Type of improvement suggested")
@click.option("--user-response", required=True,
              type=click.Choice(["accepted", "rejected", "dismissed"]),
              help="How user responded to suggestion")
@click.option("--rule-type", help="Type of rule (if applicable)")
@click.option("--rule-age-days", type=int, help="Days since rule last updated")
@click.option("--content-count", type=int, help="Number of content pieces since last update")
@click.option("--event-id", required=True, help="UUID of suggestion event")
def log_suggestion(
    feedback_type: str,
    issue_category: str,
    improvement_type: str,
    user_response: str,
    rule_type: str,
    rule_age_days: int,
    content_count: int,
    event_id: str,
):
    """
    Log an improvement suggestion event.

    This is called by the Claude Code feedback-skill when an improvement is suggested.

    Example:
        kurt feedback log-suggestion --feedback-type content_quality --issue-category tone \\
            --improvement-type update_rule --user-response accepted --event-id def456
    """
    track_improvement_suggested(
        feedback_type=feedback_type,
        issue_category=issue_category,
        improvement_type=improvement_type,
        user_response=user_response,
        rule_type=rule_type,
        rule_age_days=rule_age_days,
        content_count=content_count,
    )

    console.print(f"[dim]✓ Logged improvement suggestion: {event_id}[/dim]")


@feedback.command("log-improvement")
@click.option("--type", "improvement_type", required=True,
              type=click.Choice(["update_rule", "update_config", "extract_new_rule"]),
              help="Type of improvement")
@click.option("--command", required=True, help="High-level command executed")
@click.option("--success", required=True, type=bool, help="Whether command succeeded")
@click.option("--duration-ms", required=True, type=int, help="Execution duration in milliseconds")
@click.option("--rule-type", help="Type of rule (if applicable)")
@click.option("--content-analyzed", type=int, help="Number of content pieces analyzed")
@click.option("--rules-updated", type=int, help="Number of rule files modified")
@click.option("--event-id", required=True, help="UUID of improvement event")
def log_improvement(
    improvement_type: str,
    command: str,
    success: bool,
    duration_ms: int,
    rule_type: str,
    content_analyzed: int,
    rules_updated: int,
    event_id: str,
):
    """
    Log an improvement execution event.

    This is called by the Claude Code feedback-skill when an improvement is executed.

    Example:
        kurt feedback log-improvement --type update_rule --command "writing-rules-skill style --update" \\
            --success true --duration-ms 5230 --event-id ghi789
    """
    track_improvement_executed(
        improvement_type=improvement_type,
        command=command,
        success=success,
        duration_ms=duration_ms,
        rule_type=rule_type,
        content_analyzed=content_analyzed,
        rules_updated=rules_updated,
    )

    console.print(f"[dim]✓ Logged improvement execution: {event_id}[/dim]")


@feedback.command("log-validation")
@click.option("--improvement-id", required=True, help="UUID of improvement being validated")
@click.option("--improvement-type", required=True,
              type=click.Choice(["update_rule", "update_config", "extract_new_rule"]),
              help="Type of improvement")
@click.option("--days-since", required=True, type=int, help="Days since improvement")
@click.option("--issue-resolved", required=True, type=bool, help="Whether issue was resolved")
@click.option("--rule-type", help="Type of rule (if applicable)")
@click.option("--rating", type=int, help="Rating on next usage (1-5)")
@click.option("--event-id", required=True, help="UUID of validation event")
def log_validation(
    improvement_id: str,
    improvement_type: str,
    days_since: int,
    issue_resolved: bool,
    rule_type: str,
    rating: int,
    event_id: str,
):
    """
    Log an improvement validation event.

    This is called by the Claude Code feedback-skill when an improvement is validated.

    Example:
        kurt feedback log-validation --improvement-id def456 --improvement-type update_rule \\
            --days-since 3 --issue-resolved true --rating 4 --event-id jkl012
    """
    track_improvement_validated(
        improvement_type=improvement_type,
        days_since_improvement=days_since,
        issue_resolved=issue_resolved,
        rule_type=rule_type,
        subsequent_rating=rating,
    )

    console.print(f"[dim]✓ Logged improvement validation: {event_id}[/dim]")


@feedback.command("log-loop-completed")
@click.option("--feedback-type", required=True,
              type=click.Choice(["content_quality", "project_plan"]),
              help="Type of feedback loop")
@click.option("--loop-duration-days", required=True, type=int, help="Days from feedback to validation")
@click.option("--suggestions-made", required=True, type=int, help="Number of suggestions offered")
@click.option("--improvements-accepted", required=True, type=int, help="Number accepted")
@click.option("--improvements-successful", required=True, type=int, help="Number that executed successfully")
@click.option("--issue-resolved", required=True, type=bool, help="Whether original issue resolved")
@click.option("--rating-change", required=True, type=int, help="Change in rating (-4 to +4)")
@click.option("--event-id", required=True, help="UUID of loop completion event")
def log_loop_completed(
    feedback_type: str,
    loop_duration_days: int,
    suggestions_made: int,
    improvements_accepted: int,
    improvements_successful: int,
    issue_resolved: bool,
    rating_change: int,
    event_id: str,
):
    """
    Log a complete feedback loop event.

    This is called by the Claude Code feedback-skill when a full loop completes.

    Example:
        kurt feedback log-loop-completed --feedback-type content_quality \\
            --loop-duration-days 3 --suggestions-made 2 --improvements-accepted 1 \\
            --improvements-successful 1 --issue-resolved true --rating-change 2 \\
            --event-id pqr678
    """
    track_feedback_loop_completed(
        feedback_type=feedback_type,
        loop_duration_days=loop_duration_days,
        suggestions_made=suggestions_made,
        improvements_accepted=improvements_accepted,
        improvements_successful=improvements_successful,
        issue_resolved=issue_resolved,
        subsequent_rating_change=rating_change,
    )

    console.print(f"[dim]✓ Logged loop completion: {event_id}[/dim]")

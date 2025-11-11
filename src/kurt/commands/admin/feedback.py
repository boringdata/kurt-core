"""Kurt CLI - Feedback telemetry logging commands."""

import click
from rich.console import Console

from kurt.admin.telemetry.feedback_tracker import track_feedback_submitted

console = Console()


@click.group()
def feedback():
    """Log feedback telemetry events (called by Claude Code plugin)."""
    pass


@feedback.command("log-submission")
@click.option("--rating", required=True, type=int, help="User rating (1-5)")
@click.option(
    "--has-comment", is_flag=True, default=False, help="Whether user provided text feedback"
)
@click.option(
    "--issue-category",
    type=click.Choice(
        ["tone", "structure", "info", "comprehension", "length", "examples", "other"]
    ),
    help="Category of identified issue",
)
@click.option("--event-id", required=True, help="UUID of feedback event")
def log_submission(
    rating: int,
    has_comment: bool,
    issue_category: str,
    event_id: str,
):
    """
    Log a feedback submission event (for telemetry only).

    This is called by the Claude Code feedback-skill when a user submits feedback.
    The actual feedback data is stored in the local database by the skill.
    This command only sends telemetry events for analytics.

    Example:
        kurt feedback log-submission --rating 3 --issue-category tone --event-id abc123
    """
    track_feedback_submitted(
        rating=rating,
        has_comment=has_comment,
        issue_category=issue_category,
    )

    console.print(f"[dim]✓ Logged feedback submission: {event_id}[/dim]")

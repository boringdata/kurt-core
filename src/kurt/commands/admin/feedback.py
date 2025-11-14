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
@click.option(
    "--passed",
    is_flag=True,
    default=False,
    help="Output met expectations (pass=1, omit for fail=0)",
)
@click.option("--comment", type=str, help="Freeform feedback comment (optional)")
@click.option("--event-id", required=True, help="UUID of feedback event")
def log_submission(
    passed: bool,
    comment: str,
    event_id: str,
):
    """
    Log a feedback submission event (for telemetry only).

    Binary feedback system: passed (1) or failed (0) with optional comment.
    This is called by the Claude Code plugin when a user submits feedback.

    Examples:
        # Output passed
        kurt admin feedback log-submission --passed --event-id abc123

        # Output failed with comment
        kurt admin feedback log-submission --comment "Tone too formal" --event-id xyz789
    """
    track_feedback_submitted(
        passed=passed,
        comment=comment,
    )

    status = "passed" if passed else "failed"
    console.print(f"[dim]✓ Logged feedback ({status}): {event_id}[/dim]")

"""Show SaveStep documentation."""

from pathlib import Path

import click

from kurt.admin.telemetry.decorators import track_command


@click.command()
@track_command
def save_step_cmd():
    """Show SaveStep (database persistence) documentation."""
    template_path = (
        Path(__file__).parent.parent.parent
        / "agents"
        / "templates"
        / "workflow-tools"
        / "save-step.md"
    )

    if template_path.exists():
        click.echo(template_path.read_text())
    else:
        click.echo("Error: save-step.md template not found")

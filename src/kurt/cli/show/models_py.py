"""Show models.py documentation."""

from pathlib import Path

import click

from kurt.admin.telemetry.decorators import track_command


@click.command()
@track_command
def models_py_cmd():
    """Show models.py (SQLModel table definitions) documentation."""
    template_path = (
        Path(__file__).parent.parent.parent
        / "agents"
        / "templates"
        / "workflow-tools"
        / "models-py.md"
    )

    if template_path.exists():
        click.echo(template_path.read_text())
    else:
        click.echo("Error: models-py.md template not found")

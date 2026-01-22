"""Show tools.py documentation."""

from pathlib import Path

import click

from kurt.admin.telemetry.decorators import track_command


@click.command()
@track_command
def tools_py_cmd():
    """Show tools.py (DBOS step functions) documentation."""
    template_path = (
        Path(__file__).parent.parent.parent
        / "agents"
        / "templates"
        / "workflow-tools"
        / "tools-py.md"
    )

    if template_path.exists():
        click.echo(template_path.read_text())
    else:
        click.echo("Error: tools-py.md template not found")

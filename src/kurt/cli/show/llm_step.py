"""Show LLMStep documentation."""

from pathlib import Path

import click

from kurt.admin.telemetry.decorators import track_command


@click.command()
@track_command
def llm_step_cmd():
    """Show LLMStep (batch LLM processing) documentation."""
    template_path = (
        Path(__file__).parent.parent.parent
        / "agents"
        / "templates"
        / "workflow-tools"
        / "llm-step.md"
    )

    if template_path.exists():
        click.echo(template_path.read_text())
    else:
        click.echo("Error: llm-step.md template not found")

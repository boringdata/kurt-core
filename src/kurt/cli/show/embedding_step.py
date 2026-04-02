"""Show EmbeddingStep documentation."""

from pathlib import Path

import click

from kurt.admin.telemetry.decorators import track_command


@click.command()
@track_command
def embedding_step_cmd():
    """Show EmbeddingStep (vector embeddings) documentation."""
    template_path = (
        Path(__file__).parent.parent.parent
        / "agents"
        / "templates"
        / "workflow-tools"
        / "embedding-step.md"
    )

    if template_path.exists():
        click.echo(template_path.read_text())
    else:
        click.echo("Error: embedding-step.md template not found")

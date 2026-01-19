"""Show Kurt Cloud setup and migration instructions."""

from pathlib import Path

import click

from kurt.admin.telemetry.decorators import track_command


def _get_template_path() -> Path:
    """Get path to cloud setup template file."""
    return Path(__file__).parent / "templates" / "cloud-setup.txt"


@click.command()
@track_command
def cloud_setup_cmd():
    """Show instructions for Kurt Cloud setup and migration."""
    template_path = _get_template_path()
    content = template_path.read_text()
    click.echo(content.strip())

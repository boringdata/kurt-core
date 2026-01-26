"""Admin CLI commands."""

from __future__ import annotations

import click

from .feedback import feedback
from .migrate import migrate
from .telemetry import telemetry
from kurt.cli.sync import sync_group


@click.group()
def admin():
    """Administrative commands."""
    pass


admin.add_command(feedback)
admin.add_command(migrate)
admin.add_command(telemetry)
admin.add_command(sync_group, name="sync")

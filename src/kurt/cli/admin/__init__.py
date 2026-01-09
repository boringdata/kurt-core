"""Admin CLI commands."""

from __future__ import annotations

import click

from .feedback import feedback
from .migrate import migrate
from .telemetry import telemetry


@click.group()
def admin():
    """Administrative commands."""
    pass


admin.add_command(feedback)
admin.add_command(migrate)
admin.add_command(telemetry)

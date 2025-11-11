"""Administrative commands for Kurt management."""

import click

from .feedback import feedback
from .migrate import migrate
from .project import project
from .telemetry import telemetry


@click.group()
def admin():
    """
    Administrative commands for Kurt management.

    \b
    Available commands:
    - feedback: Log feedback and telemetry events
    - migrate: Database schema migrations
    - telemetry: Manage usage analytics
    - project: Manage Kurt projects
    """
    pass


# Register all admin commands
admin.add_command(feedback)
admin.add_command(migrate)
admin.add_command(telemetry)
admin.add_command(project)

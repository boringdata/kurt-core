"""Authentication CLI commands for Kurt Cloud."""

import click

from .commands import logout, status, whoami


@click.group()
def auth():
    """Authenticate with Kurt Cloud.

    Login to sync your local Kurt data with a shared Postgres database.
    """
    pass


# Note: login command is now in kurt.cli.cloud (uses browser + polling)
auth.add_command(logout)
auth.add_command(status)
auth.add_command(whoami)

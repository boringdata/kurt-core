"""Authentication CLI commands for Kurt Cloud."""

import click

from .commands import login, logout, status, whoami


@click.group()
def auth():
    """Authenticate with Kurt Cloud.

    Login to sync your local Kurt data with a shared Postgres database.
    """
    pass


auth.add_command(login)
auth.add_command(logout)
auth.add_command(status)
auth.add_command(whoami)

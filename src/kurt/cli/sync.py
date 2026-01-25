"""Sync commands for Git+Dolt version control.

Groups all synchronization and branch management commands:
- pull: Pull changes from Git and Dolt remotes
- push: Push changes to Git and Dolt remotes
- branch: Branch management (create, list, switch, delete)
- merge: Merge branches atomically across Git and Dolt
"""

import click

from kurt.cli.branch import branch_group
from kurt.cli.merge import merge_cmd
from kurt.cli.remote import pull_cmd, push_cmd


@click.group(name="sync")
def sync_group():
    """
    Git+Dolt version control operations.

    \b
    Commands:
      pull     Pull changes from remote
      push     Push changes to remote
      branch   Branch management
      merge    Merge branches
    """
    pass


sync_group.add_command(pull_cmd, name="pull")
sync_group.add_command(push_cmd, name="push")
sync_group.add_command(branch_group, name="branch")
sync_group.add_command(merge_cmd, name="merge")

"""Document management commands.

Groups all document-related commands:
- list: List documents with filters
- get: Get document details by ID or URL
- delete: Delete documents by ID, URL pattern, or filters
"""

import click

from kurt.documents.cli import delete_cmd, get_cmd, list_cmd


@click.group(name="docs")
def docs_group():
    """
    Document management commands.

    \b
    Commands:
      list     List documents with filters
      get      Get document details
      delete   Delete documents
    """
    pass


docs_group.add_command(list_cmd, name="list")
docs_group.add_command(get_cmd, name="get")
docs_group.add_command(delete_cmd, name="delete")

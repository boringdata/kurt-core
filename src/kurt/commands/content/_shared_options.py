"""Shared CLI options for content commands.

This module provides reusable Click options to ensure consistency across commands.
All filter options use the same help text and parameter names.
"""

import click

# Common filter options
include_option = click.option(
    "--include",
    "include_pattern",
    help="Filter documents by glob pattern (matches source_url or content_path)",
)

in_cluster_option = click.option(
    "--in-cluster",
    help="Filter documents in specified cluster",
)

with_status_option = click.option(
    "--with-status",
    type=click.Choice(["NOT_FETCHED", "FETCHED", "ERROR"], case_sensitive=False),
    help="Filter by ingestion status (NOT_FETCHED, FETCHED, ERROR)",
)

with_content_type_option = click.option(
    "--with-content-type",
    help="Filter by content type (tutorial, guide, blog, reference, etc.)",
)

ids_option = click.option(
    "--ids",
    help="Comma-separated document IDs (supports partial UUIDs, URLs, file paths)",
)

limit_option = click.option(
    "--limit",
    type=int,
    help="Maximum number of documents to process/display",
)

exclude_option = click.option(
    "--exclude",
    "exclude_pattern",
    help="Exclude documents matching glob pattern",
)


# Compose filter groups
def add_filter_options(
    include: bool = True,
    ids: bool = True,
    cluster: bool = True,
    status: bool = True,
    content_type: bool = True,
    limit: bool = True,
    exclude: bool = False,
):
    """
    Decorator to add standard filter options to a command.

    Args:
        include: Add --include option (default: True)
        ids: Add --ids option (default: True)
        cluster: Add --in-cluster option (default: True)
        status: Add --with-status option (default: True)
        content_type: Add --with-content-type option (default: True)
        limit: Add --limit option (default: True)
        exclude: Add --exclude option (default: False)

    Usage:
        @click.command("index")
        @click.argument("identifier", required=False)
        @add_filter_options()  # Adds all standard filters
        @click.option("--force", is_flag=True)
        def index(identifier, include_pattern, ids, in_cluster, with_status,
                  with_content_type, limit, force):
            ...
    """

    def decorator(f):
        # Apply options in reverse order (Click requirement)
        if exclude:
            f = exclude_option(f)
        if limit:
            f = limit_option(f)
        if content_type:
            f = with_content_type_option(f)
        if status:
            f = with_status_option(f)
        if cluster:
            f = in_cluster_option(f)
        if ids:
            f = ids_option(f)
        if include:
            f = include_option(f)
        return f

    return decorator

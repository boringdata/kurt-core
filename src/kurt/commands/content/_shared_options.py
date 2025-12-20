"""Shared CLI options for content commands.

This module provides reusable Click options to ensure consistency across commands.
All filter options use the same help text and parameter names.
"""

import click

# =============================================================================
# Filter Options
# =============================================================================

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

# =============================================================================
# Output Format Options
# =============================================================================

format_option = click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "text"], case_sensitive=False),
    default="text",
    help="Output format (json for AI agents, text for humans)",
)

format_table_option = click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "table"], case_sensitive=False),
    default="table",
    help="Output format (json for AI agents, table for humans)",
)

# =============================================================================
# Safety/Confirmation Options
# =============================================================================

dry_run_option = click.option(
    "--dry-run",
    is_flag=True,
    help="Preview what would happen without making changes",
)

yes_option = click.option(
    "--yes",
    "-y",
    "yes_flag",
    is_flag=True,
    help="Skip confirmation prompts (for automation/CI)",
)

force_option_deprecated = click.option(
    "--force",
    is_flag=True,
    hidden=True,
    help="[DEPRECATED: use --yes/-y] Skip confirmation prompts",
)

# =============================================================================
# Background/Workflow Options
# =============================================================================

background_option = click.option(
    "--background",
    is_flag=True,
    help="Run as background workflow (non-blocking)",
)

priority_option = click.option(
    "--priority",
    type=int,
    default=10,
    help="Priority for background execution (1=highest, default=10)",
)


# =============================================================================
# Composed Decorators
# =============================================================================


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


def add_output_options(table_format: bool = False):
    """
    Decorator to add output format option.

    Args:
        table_format: Use table/json instead of text/json (default: False)
    """

    def decorator(f):
        if table_format:
            f = format_table_option(f)
        else:
            f = format_option(f)
        return f

    return decorator


def add_background_options():
    """
    Decorator to add --background and --priority options for pipeline commands.

    Usage:
        @click.command("fetch")
        @add_background_options()
        def fetch(background, priority):
            ...
    """

    def decorator(f):
        # Apply in reverse order (Click requirement)
        f = priority_option(f)
        f = background_option(f)
        return f

    return decorator


def add_confirmation_options(with_deprecated_force: bool = False):
    """
    Decorator to add --yes/-y and --dry-run options.

    Args:
        with_deprecated_force: Also add hidden --force for backwards compat
    """

    def decorator(f):
        # Apply in reverse order (Click requirement)
        if with_deprecated_force:
            f = force_option_deprecated(f)
        f = yes_option(f)
        f = dry_run_option(f)
        return f

    return decorator

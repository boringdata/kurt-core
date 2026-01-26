"""CLI command for map tool."""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console

from kurt.admin.telemetry.decorators import track_command
from kurt.tools.core import (
    add_background_options,
    create_pending_run,
    dry_run_option,
    format_option,
    limit_option,
    print_json,
    run_tool_with_tracking,
    spawn_background_run,
)

console = Console()
@click.command("map")
@click.argument("source", required=False)
@click.option("--url", help="URL to discover content from (sitemap or crawl)")
@click.option("--folder", help="Local folder path to discover files from")
@click.option("--cms", help="CMS platform to sync from (e.g., sanity:production)")
@click.option("--sitemap-path", help="Override sitemap location (e.g., /custom-sitemap.xml)")
@click.option(
    "--method",
    type=click.Choice(["auto", "sitemap", "crawl", "folder", "cms"], case_sensitive=False),
    default="auto",
    help="Discovery method",
)
@click.option("--max-depth", type=int, help="Maximum crawl depth (1-5)")
@click.option("--allow-external", is_flag=True, help="Allow crawling to external domains")
@click.option("--include", "include_patterns", help="Glob patterns to include (comma-separated)")
@click.option("--exclude", "exclude_patterns", help="Glob patterns to exclude (comma-separated)")
@limit_option
@add_background_options()
@dry_run_option
@format_option
@track_command
def map_cmd(
    source: str | None,
    url: str | None,
    folder: str | None,
    cms: str | None,
    sitemap_path: str | None,
    method: str,
    max_depth: int | None,
    allow_external: bool,
    include_patterns: str | None,
    exclude_patterns: str | None,
    limit: int | None,
    background: bool,
    priority: int,
    dry_run: bool,
    output_format: str,
):
    """
    Discover content sources and create document records.

    \b
    Examples:
        kurt content map https://example.com
        kurt content map --folder ./docs
        kurt content map --cms sanity:production
        kurt content map --url https://example.com --method sitemap
        kurt content map --dry-run
    """
    # Determine source type
    source_url = url or (source if source and source.startswith(("http://", "https://")) else None)
    source_folder = folder or (
        source if source and not source.startswith(("http://", "https://")) else None
    )
    cms_platform = None
    cms_instance = None

    if cms:
        parts = cms.split(":")
        cms_platform = parts[0]
        cms_instance = parts[1] if len(parts) > 1 else "default"

    if method == "folder":
        source_folder = source_folder or source
    elif method == "cms" and source and not cms_platform:
        parts = source.split(":")
        cms_platform = parts[0]
        cms_instance = parts[1] if len(parts) > 1 else "default"

    # Validate we have a source
    if not any([source_url, source_folder, cms_platform]):
        if output_format == "json":
            print_json(
                {"status": "error", "message": "No source specified. Use --url, --folder, or --cms"}
            )
        else:
            console.print("[red]Error:[/red] No source specified")
            console.print("[dim]Use --url, --folder, or --cms to specify a source[/dim]")
        return

    tool_source = "url" if source_url else "file" if source_folder else "cms"

    from kurt.tools.map.config import MapConfig
    from kurt.tools.map.utils import parse_patterns

    config = MapConfig.from_config(
        "map",
        source_url=source_url,
        source_folder=source_folder,
        cms_platform=cms_platform,
        cms_instance=cms_instance,
        discovery_method=method.lower(),
        sitemap_path=sitemap_path,
        max_depth=max_depth,
        max_pages=limit or 1000,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
        dry_run=dry_run,
    )

    # Determine depth: use config value if set, otherwise use sensible defaults
    # For crawl mode: user explicitly wants crawling, depth=1 is sensible default
    # For auto mode: depth=0 means "sitemap only, no crawl fallback"
    # For sitemap mode: depth is irrelevant (sitemap provides all URLs)
    depth = config.max_depth
    if depth is None and config.discovery_method == "crawl":
        depth = 1  # Default depth for explicit crawl mode
    elif depth is None:
        depth = 0  # Default for auto/sitemap modes (no crawl fallback unless user sets depth)

    params = {
        "source": tool_source,
        "url": config.source_url,
        "path": config.source_folder,
        "cms_platform": config.cms_platform,
        "cms_instance": config.cms_instance,
        "depth": depth,
        "max_pages": config.max_pages,
        "include_patterns": list(parse_patterns(config.include_patterns)),
        "exclude_patterns": list(parse_patterns(config.exclude_patterns)),
        "discovery_method": config.discovery_method.lower(),
        "sitemap_path": config.sitemap_path,
        "allow_external": allow_external or config.allow_external,
        "dry_run": config.dry_run,
    }

    cli_command = "kurt " + " ".join(sys.argv[1:])

    if background:
        run_id = create_pending_run(
            "map",
            params,
            project_root=str(Path.cwd()),
            cli_command=cli_command,
            priority=priority,
        )
        spawn_background_run(
            "map",
            params,
            run_id=run_id,
            project_root=str(Path.cwd()),
            cli_command=cli_command,
            priority=priority,
        )

        if output_format == "json":
            print_json({"run_id": run_id, "background": True})
        else:
            console.print(f"[green]✓[/green] Mapping started (run_id: {run_id})")
            console.print("[dim]Use 'kurt workflow status <run_id>' to check status[/dim]")
        return

    run_id, result = run_tool_with_tracking(
        "map",
        params,
        project_root=str(Path.cwd()),
        cli_command=cli_command,
        priority=priority,
    )

    if output_format == "json":
        print_json({"run_id": run_id, **result})
        return

    rows = result.get("data", [])
    discovered = sum(1 for row in rows if row.get("is_new"))
    errors = sum(1 for row in rows if row.get("status") == "ERROR")
    console.print(f"[green]✓[/green] Discovered {len(rows)} document(s)")
    console.print(f"[dim]{discovered} new, {len(rows) - discovered} existing, {errors} errors[/dim]")
    if dry_run:
        console.print("[dim]Dry run - no documents were saved[/dim]")

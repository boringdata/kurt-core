"""CLI command for map workflow."""

from __future__ import annotations

import click
from rich.console import Console

from kurt_new.admin.telemetry.decorators import track_command
from kurt_new.cli.options import add_background_options, dry_run_option, format_option, limit_option
from kurt_new.cli.output import print_json, print_workflow_status

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
@click.option("--include", "include_patterns", help="Glob patterns to include")
@click.option("--exclude", "exclude_patterns", help="Glob patterns to exclude")
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
        kurt content map https://example.com           # Map from URL (auto-detect sitemap/crawl)
        kurt content map --folder ./docs               # Map local folder
        kurt content map --cms sanity:production       # Map from CMS
        kurt content map --url https://example.com --method sitemap  # Force sitemap
        kurt content map --dry-run                     # Preview without saving
    """
    from .config import MapConfig
    from .workflow import run_map

    # Determine source type
    source_url = url or source if source and source.startswith(("http://", "https://")) else None
    source_folder = folder or (
        source if source and not source.startswith(("http://", "https://")) else None
    )

    # Parse CMS config
    cms_platform = None
    cms_instance = None
    if cms:
        parts = cms.split(":")
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

    # Build config
    config = MapConfig.from_config(
        "map",
        source_url=source_url,
        source_folder=source_folder,
        cms_platform=cms_platform,
        cms_instance=cms_instance,
        discovery_method=method,
        sitemap_path=sitemap_path,
        max_depth=max_depth,
        max_pages=limit or 1000,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
        dry_run=dry_run,
    )

    if output_format != "json":
        source_desc = source_url or source_folder or f"{cms_platform}:{cms_instance}"
        console.print(f"[dim]Mapping content from: {source_desc}[/dim]")

    # Run workflow
    result = run_map(config, background=background, priority=priority)

    # Output result
    if output_format == "json":
        print_json(result)
    else:
        workflow_id = result.get("workflow_id")
        if workflow_id:
            print_workflow_status(workflow_id)
        else:
            rows = result.get("rows", [])
            console.print(f"[green]✓[/green] Discovered {len(rows)} document(s)")
            if result.get("dry_run"):
                console.print("[dim]Dry run - no documents were saved[/dim]")

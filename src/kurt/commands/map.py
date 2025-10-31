"""Map command - discover content without downloading."""

import click
from rich.console import Console

console = Console()


@click.group()
def map_cmd():
    """Discover content (creates NOT_FETCHED documents, no download/LLM)."""
    pass


@map_cmd.command("url")
@click.argument("url")
@click.option(
    "--sitemap-path",
    type=str,
    help="Override sitemap location (default: auto-detect at /sitemap.xml)",
)
@click.option(
    "--include-blogrolls",
    is_flag=True,
    help="Enable LLM blogroll date extraction (max 50 pages analyzed, warns about LLM cost)",
)
@click.option(
    "--max-depth",
    type=int,
    help="Maximum crawl depth for spider-based discovery (only used if no sitemap found)",
)
@click.option(
    "--max-pages",
    type=int,
    default=1000,
    help="Max pages to discover per operation (default: 1000, prevents runaway discovery)",
)
@click.option(
    "--allow-external",
    is_flag=True,
    help="Follow and include links to external domains during crawling",
)
@click.option(
    "--include",
    "include_patterns",
    multiple=True,
    help="Include URL pattern (glob matching source_url, repeatable)",
)
@click.option(
    "--exclude",
    "exclude_patterns",
    multiple=True,
    help="Exclude URL pattern (glob matching source_url, repeatable)",
)
@click.option(
    "--cluster-urls",
    is_flag=True,
    help="Cluster discovered URLs into topics (opt-in, uses LLM, creates 5-10 clusters, links ALL documents, warns if >500 docs)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview discovery without creating records (safe for testing, no DB changes)",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "text"]),
    default="text",
    help="Output format for AI agents",
)
def map_url(
    url: str,
    sitemap_path: str,
    include_blogrolls: bool,
    max_depth: int,
    max_pages: int,
    allow_external: bool,
    include_patterns: tuple,
    exclude_patterns: tuple,
    cluster_urls: bool,
    dry_run: bool,
    output_format: str,
):
    """
    Discover content from web sources (auto-detects sitemap, falls back to crawl).

    Examples:
        # Discover from sitemap
        kurt map url https://example.com

        # Discover with custom sitemap path
        kurt map url https://example.com --sitemap-path /custom-sitemap.xml

        # Discover with crawling
        kurt map url https://example.com --max-depth 5

        # Discover with filters
        kurt map url https://example.com --include "*/docs/*" --exclude "*/api/*"

        # Discover and cluster immediately
        kurt map url https://example.com --cluster-urls
    """
    from kurt.ingestion.map import map_url_content

    try:
        # Display mode indicator
        if dry_run:
            console.print("[bold]DRY RUN - Preview only[/bold]\n")

        console.print(f"[cyan]Discovering content from:[/cyan] {url}\n")

        # Call ingestion layer (handles dry-run and clustering logic)
        result = map_url_content(
            url=url,
            sitemap_path=sitemap_path,
            include_blogrolls=include_blogrolls,
            max_depth=max_depth,
            max_pages=max_pages,
            allow_external=allow_external,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            dry_run=dry_run,
            cluster_urls=cluster_urls,
        )

        # Display results
        if output_format == "json":
            import json

            console.print(json.dumps(result, indent=2, default=str))
        else:
            if result.get("dry_run"):
                console.print(f"[green]✓ Would discover {result['total']} pages[/green]")
            else:
                console.print(f"[green]✓ Discovered {result['total']} pages[/green]")
                console.print(f"  New: {result['new']}")
                console.print(f"  Existing: {result['existing']}")
            console.print(f"  Method: {result['method']}")

            # Show sample URLs
            if result["discovered"]:
                console.print("\n[bold]Sample URLs:[/bold]")
                for item in result["discovered"][:5]:
                    # Handle both string URLs (dry-run) and dict objects (normal mode)
                    if isinstance(item, str):
                        console.print(f"  • {item}")
                    else:
                        console.print(f"  • {item.get('url', item.get('path', 'N/A'))}")
                if len(result["discovered"]) > 5:
                    console.print(f"  [dim]... and {len(result['discovered']) - 5} more[/dim]")

            # Display clustering results if applicable
            if result.get("cluster_count"):
                console.print(f"\n[green]✓ Created {result['cluster_count']} clusters[/green]")

            # Clustering tip (if not clustered)
            if result["total"] >= 50 and not cluster_urls:
                # Generate pattern based on user's URL
                from urllib.parse import urlparse

                parsed = urlparse(url)
                domain = parsed.netloc.replace("www.", "")
                example_pattern = f"*{domain}*"

                console.print(
                    f'\n[dim]💡 Tip: Cluster these URLs with [cyan]kurt cluster-urls --include "{example_pattern}"[/cyan] (or just [cyan]kurt cluster-urls[/cyan] for all)[/dim]'
                )
                console.print(
                    f'[dim]💡 Tip: Explore URLs by depth with [cyan]kurt content list --include "{example_pattern}" --max-depth 2[/cyan][/dim]'
                )

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        import traceback

        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise click.Abort()


@map_cmd.command("folder")
@click.argument("path")
@click.option(
    "--include", "include_patterns", multiple=True, help="Include file pattern (glob, repeatable)"
)
@click.option(
    "--exclude", "exclude_patterns", multiple=True, help="Exclude file pattern (glob, repeatable)"
)
@click.option("--dry-run", is_flag=True, help="Preview without creating records")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "text"]),
    default="text",
    help="Output format",
)
def map_folder(
    path: str,
    include_patterns: tuple,
    exclude_patterns: tuple,
    dry_run: bool,
    output_format: str,
):
    """
    Discover content from local folder (scans .md and .mdx only).

    Examples:
        # Discover from folder
        kurt map folder ./docs

        # Discover with filters
        kurt map folder ./docs --include "*/guides/*" --exclude "*/draft/*"

        # Preview without creating records
        kurt map folder ./docs --dry-run
    """
    from pathlib import Path

    from kurt.ingestion.map import map_folder_content

    folder = Path(path)

    if not folder.exists():
        console.print(f"[red]Error:[/red] Folder not found: {path}")
        raise click.Abort()

    if not folder.is_dir():
        console.print(f"[red]Error:[/red] Not a directory: {path}")
        raise click.Abort()

    try:
        # Display mode indicator
        if dry_run:
            console.print("[bold]DRY RUN - Preview only[/bold]\n")

        console.print(f"[cyan]Discovering content from:[/cyan] {path}\n")

        # Call ingestion layer (handles dry-run logic)
        result = map_folder_content(
            folder_path=path,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            dry_run=dry_run,
        )

        # Display results
        if output_format == "json":
            import json

            console.print(json.dumps(result, indent=2, default=str))
        else:
            if result.get("dry_run"):
                console.print(f"[green]✓ Would discover {result['total']} files[/green]")
            else:
                console.print(f"[green]✓ Discovered {result['total']} files[/green]")
                console.print(f"  New: {result['new']}")
                console.print(f"  Existing: {result['existing']}")

            # Show sample files
            if result["discovered"]:
                console.print("\n[bold]Sample files:[/bold]")
                for item in result["discovered"][:5]:
                    # Handle both string paths (dry-run) and dict objects (normal mode)
                    if isinstance(item, str):
                        console.print(f"  • {item}")
                    elif "error" in item:
                        console.print(f"  ✗ {item['path']} - {item['error']}")
                    else:
                        console.print(f"  • {item['path']}")
                if len(result["discovered"]) > 5:
                    console.print(f"  [dim]... and {len(result['discovered']) - 5} more[/dim]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        import traceback

        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise click.Abort()

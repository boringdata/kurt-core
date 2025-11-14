"""Map command - discover content without downloading."""

import click
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

from kurt.admin.telemetry.decorators import track_command
from kurt.utils.url_utils import get_domain_from_url

console = Console()


@click.group()
def map_cmd():
    """
    Discover content without downloading or using LLM.

    \b
    Creates NOT_FETCHED document records from:
    - Web sitemaps or crawling (map url)
    - Local folders (map folder)
    - CMS platforms (map cms)

    \b
    Workflow: map → cluster-urls → fetch --in-cluster "ClusterName"
    """
    pass


@map_cmd.command("url")
@track_command
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
@click.option(
    "--background",
    is_flag=True,
    help="Run as background workflow (non-blocking, useful for long crawls/clustering)",
)
@click.option(
    "--priority",
    type=int,
    default=10,
    help="Priority for background execution (1=highest, default=10)",
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
    background: bool,
    priority: int,
):
    """
    Discover URLs from web sources without downloading content.

    \b
    Discovery methods:
    1. Sitemap (preferred): Auto-detects at /sitemap.xml
    2. Crawling (fallback): Spiders the site if no sitemap found

    \b
    What it creates:
    - Document records with status: NOT_FETCHED
    - No content download, no LLM usage
    - Fast discovery of entire site structure

    \b
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
    from kurt.content.map import map_url_content

    try:
        from kurt.commands.content._live_display import (
            print_command_summary,
            print_intro_block,
            print_stage_header,
        )

        # Dry-run mode bypasses workflow system (no DB writes)
        if dry_run:
            print_intro_block(
                console,
                [
                    "[bold]DRY RUN - Preview only[/bold]",
                    f"Discovering content from: {url}\n",
                ],
            )

            result = map_url_content(
                url=url,
                sitemap_path=sitemap_path,
                include_blogrolls=include_blogrolls,
                max_depth=max_depth,
                max_pages=max_pages,
                allow_external=allow_external,
                include_patterns=include_patterns,
                exclude_patterns=exclude_patterns,
                dry_run=True,
                cluster_urls=False,  # No clustering in dry-run
                progress=None,
            )
        else:
            # Use workflow system for background mode only
            # For foreground, use original function with progress UI
            if background:
                from kurt.workflows.cli_helpers import run_with_background_support
                from kurt.workflows.map import map_url_workflow

                result = run_with_background_support(
                    workflow_func=map_url_workflow,
                    workflow_args={
                        "url": url,
                        "sitemap_path": sitemap_path,
                        "include_blogrolls": include_blogrolls,
                        "max_depth": max_depth,
                        "max_pages": max_pages,
                        "allow_external": allow_external,
                        "include_patterns": include_patterns,
                        "exclude_patterns": exclude_patterns,
                        "cluster_urls": cluster_urls,
                    },
                    background=True,
                    workflow_id=None,
                    priority=priority,
                )
                return  # Background mode complete, exit early

            # Foreground mode: use original function with progress UI
            print_intro_block(console, [f"Discovering content from: {url}\n"])

            print_stage_header(console, 1, "DISCOVER CONTENT")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console,
            ) as progress:
                result = map_url_content(
                    url=url,
                    sitemap_path=sitemap_path,
                    include_blogrolls=include_blogrolls,
                    max_depth=max_depth,
                    max_pages=max_pages,
                    allow_external=allow_external,
                    include_patterns=include_patterns,
                    exclude_patterns=exclude_patterns,
                    dry_run=False,
                    cluster_urls=cluster_urls,
                    progress=progress,
                )

        # Display results
        if output_format == "json":
            import json

            console.print(json.dumps(result, indent=2, default=str))
        else:
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

            # Build summary
            summary_items = []
            if result.get("dry_run"):
                summary_items.append(("ℹ", "Would discover", f"{result['total']} page(s)"))
            else:
                summary_items.extend(
                    [
                        ("✓", "Discovered", f"{result['total']} page(s)"),
                        ("✓", "New", f"{result['new']} page(s)"),
                        ("ℹ", "Existing", f"{result['existing']} page(s)"),
                    ]
                )

            summary_items.append(("ℹ", "Method", result["method"]))

            if result.get("cluster_count"):
                summary_items.append(("✓", "Clusters created", str(result["cluster_count"])))

            print_command_summary(console, "Summary", summary_items)

            # Clustering tip (if not clustered)
            if result["total"] >= 50 and not cluster_urls:
                # Generate pattern based on user's URL (using centralized utility)
                domain = get_domain_from_url(url, strip_www=True)
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
@track_command
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
    Discover markdown files from local folder.

    \b
    What it scans:
    - Recursively finds .md and .mdx files
    - Creates NOT_FETCHED document records
    - No content reading or LLM usage

    \b
    Examples:
        # Discover from folder
        kurt map folder ./docs

        # Discover with filters
        kurt map folder ./docs --include "*/guides/*" --exclude "*/draft/*"

        # Preview without creating records
        kurt map folder ./docs --dry-run
    """
    from pathlib import Path

    from kurt.content.map import map_folder_content

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

        # Create progress context
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            # Call ingestion layer (handles dry-run logic)
            result = map_folder_content(
                folder_path=path,
                include_patterns=include_patterns,
                exclude_patterns=exclude_patterns,
                dry_run=dry_run,
                progress=progress,
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


@map_cmd.command("cms")
@track_command
@click.option(
    "--platform",
    type=click.Choice(["sanity", "contentful", "wordpress"]),
    required=True,
    help="CMS platform (sanity, contentful, wordpress)",
)
@click.option(
    "--instance",
    type=str,
    help="Instance name (prod, staging, etc). Uses 'default' or first instance if not specified.",
)
@click.option(
    "--content-type",
    type=str,
    help="Filter by content type",
)
@click.option(
    "--status",
    type=click.Choice(["draft", "published"]),
    help="Filter by status (draft or published)",
)
@click.option(
    "--limit",
    type=int,
    help="Maximum number of documents to discover",
)
@click.option(
    "--cluster-urls",
    is_flag=True,
    help="Cluster discovered documents into topics (opt-in, uses LLM)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview discovery without creating records",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "text"]),
    default="text",
    help="Output format",
)
def map_cms(
    platform: str,
    instance: str,
    content_type: str,
    status: str,
    limit: int,
    cluster_urls: bool,
    dry_run: bool,
    output_format: str,
):
    """
    Discover content from CMS (creates NOT_FETCHED documents, no download/LLM).

    Examples:
        # Discover all content from Sanity
        kurt map cms --platform sanity --instance prod

        # Discover and cluster
        kurt map cms --platform sanity --instance prod --cluster-urls

        # Discover specific content type
        kurt map cms --platform sanity --content-type article

        # Discover with filters
        kurt map cms --platform sanity --status published --limit 100

        # Preview without creating records
        kurt map cms --platform sanity --dry-run
    """
    from kurt.content.map import map_cms_content
    from kurt.integrations.cms.config import list_platform_instances, platform_configured

    # Check if platform is configured
    if not platform_configured(platform):
        console.print(f"[red]Error:[/red] CMS platform '{platform}' is not configured.")
        console.print(f"\n[dim]Run 'kurt cms onboard --platform {platform}' to configure.[/dim]")
        raise click.Abort()

    # If no instance specified, get default/first instance
    if not instance:
        instances = list_platform_instances(platform)
        instance = instances[0] if instances else "default"
        if len(instances) > 1:
            console.print(
                f"[yellow]No instance specified. Using '{instance}'. "
                f"Available: {', '.join(instances)}[/yellow]\n"
            )

    try:
        # Display mode indicator
        if dry_run:
            console.print("[bold]DRY RUN - Preview only[/bold]\n")

        console.print(f"[cyan]Discovering content from:[/cyan] {platform}/{instance}\n")

        # Create progress context
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            # Call ingestion layer
            result = map_cms_content(
                platform=platform,
                instance=instance,
                content_type=content_type,
                status=status,
                limit=limit,
                cluster_urls=cluster_urls,
                dry_run=dry_run,
                progress=progress,
            )

        # Display results
        if output_format == "json":
            import json

            console.print(json.dumps(result, indent=2, default=str))
        else:
            action = "Would discover" if result.get("dry_run") else "Discovered"
            console.print(
                f"[green]✓ {action} {result['total']} documents from {platform}/{instance}[/green]"
            )

            if not result.get("dry_run"):
                console.print(f"  New: {result['new']}")
                console.print(f"  Existing: {result['existing']}")

            # Show sample documents
            if result["discovered"]:
                console.print("\n[bold]Sample documents:[/bold]")
                for doc in result["discovered"][:5]:
                    if isinstance(doc, dict):
                        console.print(f"  • {doc.get('title', 'Untitled')} ({doc['content_type']})")
                    else:
                        console.print(f"  • {doc}")
                if len(result["discovered"]) > 5:
                    console.print(f"  [dim]... and {len(result['discovered']) - 5} more[/dim]")

            # Show clustering message if enabled
            if cluster_urls and not result.get("dry_run"):
                console.print(
                    "\n[dim]💡 Documents will be clustered. View with: "
                    "[cyan]kurt cluster-urls[/cyan][/dim]"
                )

            # Show next steps
            console.print(
                f'\n[dim]💡 Next: Fetch content with [cyan]kurt fetch --include "{platform}/{instance}/*"[/cyan][/dim]'
            )

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        import traceback

        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise click.Abort()

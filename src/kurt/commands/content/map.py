"""Map command - discover content without downloading."""

import click
from rich.console import Console

from kurt.admin.telemetry.decorators import track_command
from kurt.commands.content._shared_options import (
    add_background_options,
    add_output_options,
    dry_run_option,
)
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
    help="Cluster discovered URLs into topics (opt-in, uses LLM, creates 5-10 clusters)",
)
@dry_run_option
@add_output_options()
@add_background_options()
def map_url(
    url: str,
    sitemap_path: str,
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
        kurt content map url https://example.com

        # Discover with custom sitemap path
        kurt content map url https://example.com --sitemap-path /custom-sitemap.xml

        # Discover with crawling
        kurt content map url https://example.com --max-depth 5

        # Discover with filters
        kurt content map url https://example.com --include "*/docs/*" --exclude "*/api/*"

        # Discover and cluster immediately
        kurt content map url https://example.com --cluster-urls

        # Run in background
        kurt content map url https://example.com --background
    """
    from kurt.core.display import display_summary, print_info
    from kurt.models.landing.discovery import DiscoveryConfig
    from kurt.workflows.cli_helpers import dbos_cleanup_context, run_pipeline_simple

    with dbos_cleanup_context():
        try:
            # Create DiscoveryConfig with runtime values
            discovery_config = DiscoveryConfig(
                source_url=url,
                max_pages=max_pages,
                max_depth=max_depth,
                allow_external=allow_external,
                include_patterns=",".join(include_patterns) if include_patterns else None,
                exclude_patterns=",".join(exclude_patterns) if exclude_patterns else None,
                dry_run=dry_run,
            )

            # Run workflow (display handled by framework)
            workflow_result = run_pipeline_simple(
                target="landing.discovery",
                model_configs={"landing.discovery": discovery_config},
                background=background,
                priority=priority,
            )

            # Background mode returns early
            if background:
                return

            # Extract stats from pipeline result
            discovery_result = workflow_result.get("landing.discovery", {})
            documents_discovered = discovery_result.get("documents_discovered", 0)
            documents_existing = discovery_result.get("documents_existing", 0)
            discovery_method = discovery_result.get("discovery_method", "unknown")
            is_dry_run = discovery_result.get("dry_run", False)

            # Handle clustering if requested (skip for dry_run)
            cluster_count = None
            if cluster_urls and documents_discovered > 0 and not is_dry_run:
                import asyncio

                from kurt.core import run_pipeline_workflow
                from kurt.utils.filtering import DocumentFilters

                print_info("Clustering discovered documents...")
                cluster_result = asyncio.run(
                    run_pipeline_workflow(
                        target="staging.topic_clustering", filters=DocumentFilters()
                    )
                )
                cluster_count = cluster_result.get("clusters_discovered", 0)

            # Display results
            if output_format == "json":
                import json

                result = {
                    "discovered": discovery_result.get("discovered_urls", []) if is_dry_run else [],
                    "total": documents_discovered + documents_existing,
                    "new": documents_discovered,
                    "existing": documents_existing,
                    "method": discovery_method,
                    "dry_run": is_dry_run,
                }
                if cluster_count is not None:
                    result["cluster_count"] = cluster_count
                console.print(json.dumps(result, indent=2, default=str))
            else:
                # Build summary stats
                total = documents_discovered + documents_existing
                if is_dry_run:
                    summary_stats = {"would_discover": f"{total} page(s)"}
                else:
                    summary_stats = {
                        "discovered": f"{total} page(s)",
                        "new": f"{documents_discovered} page(s)",
                    }
                    if documents_existing > 0:
                        summary_stats["existing"] = f"{documents_existing} page(s)"
                    if cluster_count:
                        summary_stats["clusters_created"] = cluster_count

                display_summary(summary_stats, console=console, show_time=False)
                console.print(f"  [dim]ℹ Method: {discovery_method}[/dim]")

                # Clustering tip (if not clustered)
                if total >= 50 and not cluster_urls:
                    domain = get_domain_from_url(url, strip_www=True)
                    example_pattern = f"*{domain}*"
                    console.print(
                        f'\n[dim]💡 Tip: Cluster with [cyan]kurt content cluster-urls --include "{example_pattern}"[/cyan][/dim]'
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
@dry_run_option
@add_output_options()
@add_background_options()
def map_folder(
    path: str,
    include_patterns: tuple,
    exclude_patterns: tuple,
    dry_run: bool,
    output_format: str,
    background: bool,
    priority: int,
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
        kurt content map folder ./docs

        # Discover with filters
        kurt content map folder ./docs --include "*/guides/*" --exclude "*/draft/*"

        # Preview without creating records
        kurt content map folder ./docs --dry-run

        # Run in background
        kurt content map folder ./docs --background
    """
    from pathlib import Path

    from kurt.core.display import display_summary
    from kurt.models.landing.discovery import DiscoveryConfig
    from kurt.workflows.cli_helpers import dbos_cleanup_context, run_pipeline_simple

    folder = Path(path)

    if not folder.exists():
        console.print(f"[red]Error:[/red] Folder not found: {path}")
        raise click.Abort()

    if not folder.is_dir():
        console.print(f"[red]Error:[/red] Not a directory: {path}")
        raise click.Abort()

    with dbos_cleanup_context():
        try:
            # Create DiscoveryConfig with runtime values
            discovery_config = DiscoveryConfig(
                source_folder=str(folder.absolute()),
                include_patterns=",".join(include_patterns) if include_patterns else None,
                exclude_patterns=",".join(exclude_patterns) if exclude_patterns else None,
                dry_run=dry_run,
            )

            # Run workflow (display handled by framework)
            workflow_result = run_pipeline_simple(
                target="landing.discovery",
                model_configs={"landing.discovery": discovery_config},
                background=background,
                priority=priority,
            )

            # Background mode returns early
            if background:
                return

            # Extract stats
            discovery_result = workflow_result.get("landing.discovery", {})
            documents_discovered = discovery_result.get("documents_discovered", 0)
            documents_existing = discovery_result.get("documents_existing", 0)
            is_dry_run = discovery_result.get("dry_run", False)

            # Display results
            if output_format == "json":
                import json

                result = {
                    "discovered": discovery_result.get("discovered_urls", []) if is_dry_run else [],
                    "total": documents_discovered + documents_existing,
                    "new": documents_discovered,
                    "existing": documents_existing,
                    "dry_run": is_dry_run,
                }
                console.print(json.dumps(result, indent=2, default=str))
            else:
                total = documents_discovered + documents_existing
                if is_dry_run:
                    summary_stats = {"would_discover": f"{total} file(s)"}
                else:
                    summary_stats = {
                        "discovered": f"{total} file(s)",
                        "new": f"{documents_discovered} file(s)",
                    }
                    if documents_existing > 0:
                        summary_stats["existing"] = f"{documents_existing} file(s)"

                display_summary(summary_stats, console=console, show_time=False)

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            import traceback

            console.print(f"[dim]{traceback.format_exc()}[/dim]")
            raise click.Abort()


@map_cmd.command("cms")
@track_command
@click.option(
    "--platform",
    type=click.Choice(["sanity"]),
    required=True,
    help="CMS platform (currently only sanity is supported)",
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
@dry_run_option
@add_output_options()
@add_background_options()
def map_cms(
    platform: str,
    instance: str,
    content_type: str,
    status: str,
    limit: int,
    cluster_urls: bool,
    dry_run: bool,
    output_format: str,
    background: bool,
    priority: int,
):
    """
    Discover content from CMS (creates NOT_FETCHED documents, no download/LLM).

    Examples:
        # Discover all content from Sanity
        kurt content map cms --platform sanity --instance prod

        # Discover and cluster
        kurt content map cms --platform sanity --instance prod --cluster-urls

        # Discover specific content type
        kurt content map cms --platform sanity --content-type article

        # Discover with filters
        kurt content map cms --platform sanity --status published --limit 100

        # Preview without creating records
        kurt content map cms --platform sanity --dry-run

        # Run in background
        kurt content map cms --platform sanity --background
    """
    from kurt.core.display import display_summary, print_info
    from kurt.integrations.cms.config import list_platform_instances, platform_configured
    from kurt.models.landing.discovery import DiscoveryConfig
    from kurt.workflows.cli_helpers import dbos_cleanup_context, run_pipeline_simple

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

    with dbos_cleanup_context():
        try:
            # Create DiscoveryConfig with runtime values
            discovery_config = DiscoveryConfig(
                cms_platform=platform,
                cms_instance=instance,
                max_pages=limit if limit is not None else 1000,
                dry_run=dry_run,
            )

            # Run workflow (display handled by framework)
            workflow_result = run_pipeline_simple(
                target="landing.discovery",
                model_configs={"landing.discovery": discovery_config},
                background=background,
                priority=priority,
            )

            # Background mode returns early
            if background:
                return

            # Extract stats
            discovery_result = workflow_result.get("landing.discovery", {})
            documents_discovered = discovery_result.get("documents_discovered", 0)
            documents_existing = discovery_result.get("documents_existing", 0)
            is_dry_run = discovery_result.get("dry_run", False)

            # Handle clustering if requested
            cluster_count = None
            if cluster_urls and documents_discovered > 0 and not is_dry_run:
                import asyncio

                from kurt.core import run_pipeline_workflow
                from kurt.utils.filtering import DocumentFilters

                print_info("Clustering discovered documents...")
                cluster_result = asyncio.run(
                    run_pipeline_workflow(
                        target="staging.topic_clustering", filters=DocumentFilters()
                    )
                )
                cluster_count = cluster_result.get("clusters_discovered", 0)

            # Display results
            if output_format == "json":
                import json

                result = {
                    "total": documents_discovered + documents_existing,
                    "new": documents_discovered,
                    "existing": documents_existing,
                    "dry_run": is_dry_run,
                }
                if cluster_count is not None:
                    result["cluster_count"] = cluster_count
                console.print(json.dumps(result, indent=2, default=str))
            else:
                total = documents_discovered + documents_existing
                if is_dry_run:
                    summary_stats = {
                        "would_discover": f"{total} document(s) from {platform}/{instance}"
                    }
                else:
                    summary_stats = {
                        "discovered": f"{total} document(s) from {platform}/{instance}",
                        "new": f"{documents_discovered} document(s)",
                    }
                    if documents_existing > 0:
                        summary_stats["existing"] = f"{documents_existing} document(s)"
                    if cluster_count:
                        summary_stats["clusters_created"] = cluster_count

                display_summary(summary_stats, console=console, show_time=False)

                # Show next steps
                console.print(
                    f'\n[dim]💡 Next: Fetch content with [cyan]kurt content fetch --include "{platform}/{instance}/*"[/cyan][/dim]'
                )

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            import traceback

            console.print(f"[dim]{traceback.format_exc()}[/dim]")
            raise click.Abort()

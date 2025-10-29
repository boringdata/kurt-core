"""URL-based content addition - handles single and multi-page URLs."""

import click
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

console = Console()


def handle_url_add(
    url: str,
    *,
    fetch_only: bool = False,
    discover_only: bool = False,
    dry_run: bool = False,
    url_contains: str = None,
    url_starts_with: str = None,
    limit: int = None,
    force: bool = False,
    max_concurrent: int = 5,
    discover_dates: bool = False,
    max_blogrolls: int = 10,
    fetch_engine: str = None,
):
    """
    Handle adding content from URLs.

    Args:
        url: URL to add
        fetch_only: Only fetch, skip indexing
        discover_only: Only discover, skip fetch and index
        dry_run: Preview only, no changes
        url_contains: Filter URLs containing this string
        url_starts_with: Filter URLs starting with this prefix
        limit: Maximum number of pages to process
        force: Skip confirmation prompts
        max_concurrent: Max parallel downloads
        discover_dates: Discover publish dates from blogrolls
        max_blogrolls: Maximum blogroll pages to scrape
        fetch_engine: Fetch engine override ('firecrawl' or 'trafilatura')
    """
    from kurt.ingestion.add import (
        add_multiple_pages,
        add_single_page,
        group_urls_by_path_prefix,
        is_single_page_url,
        should_confirm_batch,
    )

    # Validate mutually exclusive flags
    if sum([fetch_only, discover_only, dry_run]) > 1:
        console.print(
            "[red]Error:[/red] Only one of --fetch-only, --discover-only, or --dry-run can be used"
        )
        raise click.Abort()

    try:
        # Single page mode
        if is_single_page_url(url):
            if dry_run:
                console.print(f"[cyan]Would add:[/cyan] {url}")
                return

            console.print(f"[cyan]Adding single page:[/cyan] {url}")

            # Call business logic
            result = add_single_page(
                url,
                fetch=not discover_only,
                index=(not fetch_only and not discover_only),
                fetch_engine=fetch_engine,
            )

            # Display results
            if result["created"]:
                console.print(f"[green]✓[/green] Created document: {result['doc_id']}")
            else:
                console.print(f"[yellow]Document already exists:[/yellow] {result['doc_id']}")

            if result["fetched"]:
                fetch_result = result["fetch_result"]
                console.print(f"[green]✓[/green] Fetched: {fetch_result['title']}")
                console.print(f"  Content: {fetch_result['content_length']} characters")
                if fetch_result.get("content_path"):
                    console.print(f"  Path: {fetch_result['content_path']}")

            if result["indexed"]:
                index_result = result["index_result"]
                console.print(f"[green]✓[/green] Indexed: {index_result['content_type']}")
                if index_result.get("topics"):
                    console.print(f"  Topics: {', '.join(index_result['topics'][:3])}")

            console.print(f"\n[green]✓ Done![/green] Document ID: [cyan]{result['doc_id']}[/cyan]")
            return

        # Multi-page mode
        console.print(f"[cyan]Discovering pages from:[/cyan] {url}")
        if discover_dates:
            console.print(
                f"[dim]Will discover publish dates from up to {max_blogrolls} blogroll/changelog pages[/dim]"
            )

        # Dry-run: just preview discovery
        if dry_run:
            from kurt.ingestion.map import map_sitemap

            docs = map_sitemap(
                url, fetch_all=False, discover_blogrolls=discover_dates, max_blogrolls=max_blogrolls
            )

            # Apply filters for preview
            if url_contains:
                docs = [d for d in docs if url_contains in d["url"]]
            if url_starts_with:
                docs = [d for d in docs if d["url"].startswith(url_starts_with)]
            if limit:
                docs = docs[:limit]

            console.print(f"[green]✓[/green] Found {len(docs)} pages")
            console.print("\n[yellow]Dry run - no changes made[/yellow]")
            console.print("\n[bold]Would add:[/bold]")
            for doc in docs[:10]:
                console.print(f"  • {doc['url']}")
            if len(docs) > 10:
                console.print(f"  ... and {len(docs) - 10} more")
            return

        # Call business logic function
        result = add_multiple_pages(
            url,
            url_contains=url_contains,
            url_starts_with=url_starts_with,
            limit=limit,
            fetch=(not discover_only),
            index=(not fetch_only and not discover_only),
            max_concurrent=max_concurrent,
            discover_dates=discover_dates,
            max_blogrolls=max_blogrolls,
        )

        # Display discovery results
        console.print(f"[green]✓[/green] Discovered {result['discovered']} pages")
        console.print(f"[green]Created:[/green] {result['created']} new documents")
        if result["discovered"] - result["created"] > 0:
            console.print(
                f"[yellow]Skipped:[/yellow] {result['discovered'] - result['created']} existing documents"
            )

        # Show filtering info
        if url_contains:
            console.print(f"[dim]Filtered by contains: '{url_contains}'[/dim]")
        if url_starts_with:
            console.print(f"[dim]Filtered by starts with: '{url_starts_with}'[/dim]")
        if limit:
            console.print(f"[dim]Limited to: {limit} pages[/dim]")

        # Discover-only mode - stop here
        if discover_only:
            console.print(f"\n[green]✓ Done![/green] Discovered {result['discovered']} documents")
            console.print(
                "\n[yellow]Tip:[/yellow] Fetch with: [cyan]kurt content fetch --all[/cyan]"
            )
            return

        # Ask for confirmation if needed
        if result["created"] > 0 and should_confirm_batch(result["created"], force):
            console.print(f"\n[yellow]This will fetch {result['created']} pages.[/yellow]")

            # Show grouped paths
            path_groups = group_urls_by_path_prefix(result["created_docs"])
            console.print("\n[bold]Pages by section:[/bold]")
            for prefix, count in sorted(path_groups.items(), key=lambda x: -x[1])[:5]:
                console.print(f"  {prefix}/* ({count} pages)")
            if len(path_groups) > 5:
                console.print(f"  ... and {len(path_groups) - 5} more sections")

            if not click.confirm("\nContinue?", default=False):
                console.print("[yellow]Aborted[/yellow]")
                return

        # Display fetch results with progress bar
        if result["created"] > 0 and not discover_only:
            console.print(f"\n[cyan]Fetching {result['created']} documents...[/cyan]")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("Fetching...", total=result["created"])
                progress.update(task, completed=result["created"])

            console.print(f"[green]✓ Fetched:[/green] {result['fetched']} documents")

            if "fetch_results" in result:
                failed = [r for r in result["fetch_results"] if not r["success"]]
                if failed:
                    console.print(f"[red]✗ Failed:[/red] {len(failed)} documents")
                    for r in failed[:3]:
                        console.print(f"  [dim]{r.get('error', 'Unknown error')}[/dim]")

        # Fetch-only mode - stop here
        if fetch_only:
            console.print(f"\n[green]✓ Done![/green] Fetched {result['fetched']} documents")
            console.print(
                "\n[yellow]Tip:[/yellow] Index with: [cyan]kurt content index --all[/cyan]"
            )
            return

        # Display index results
        if result["indexed"] > 0:
            console.print(f"[green]✓ Indexed:[/green] {result['indexed']} documents")

        # Final summary
        console.print("\n[bold green]✓ Done![/bold green]")
        console.print(f"  Discovered: {result['discovered']} pages")
        console.print(f"  Fetched: {result['fetched']} documents")
        console.print(f"  Indexed: {result['indexed']} documents")

    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        import traceback

        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise click.Abort()

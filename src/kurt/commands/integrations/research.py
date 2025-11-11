"""Research integration CLI commands."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from kurt.admin.telemetry.decorators import track_command
from kurt.integrations.research.config import get_source_config, source_configured

console = Console()


def get_adapter(source: str):
    """Get research adapter instance for the specified source."""
    config = get_source_config(source)

    if source == "perplexity":
        from kurt.integrations.research.perplexity import PerplexityAdapter

        return PerplexityAdapter(config)
    elif source == "tavily":
        raise NotImplementedError("Tavily support coming soon")
    elif source == "exa":
        raise NotImplementedError("Exa support coming soon")
    else:
        raise ValueError(f"Unsupported research source: {source}")


@click.group()
def research():
    """Research integration for discovering topics and gathering information."""
    pass


@research.command("search")
@click.argument("query")
@click.option("--source", default="perplexity", help="Research source (perplexity, tavily, exa)")
@click.option(
    "--recency", type=click.Choice(["hour", "day", "week", "month"]), help="Time filter for results"
)
@click.option("--model", help="Override default model")
@click.option("--save", is_flag=True, help="Save results to sources/research/")
@click.option(
    "--output", type=click.Choice(["markdown", "json"]), default="markdown", help="Output format"
)
@track_command
def search_cmd(
    query: str, source: str, recency: Optional[str], model: Optional[str], save: bool, output: str
):
    """
    Execute research query.

    Examples:
        kurt research search "AI coding tools news today"
        kurt research search "developer tools trends" --recency week
        kurt research search "GitHub Copilot updates" --save
    """
    try:
        # Check if source is configured
        if not source_configured(source):
            console.print(f"[red]Error:[/red] {source.capitalize()} not configured")
            console.print("Add your API key to .kurt/research-config.json")
            console.print("See .kurt/README.md for setup instructions")
            raise click.Abort()

        adapter = get_adapter(source)

        # Show progress while researching
        console.print(f"[cyan]Researching:[/cyan] {query}")
        if recency:
            console.print(f"[dim]Recency: {recency}[/dim]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[cyan]Analyzing sources..."),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("research", total=None)

            # Execute search (this will block while API processes)
            result = adapter.search(query=query, recency=recency, model=model)

        # Display results
        console.print()
        console.print(f"[green]✓ Research complete[/green] ({result.response_time_seconds:.1f}s)")
        console.print(f"[bold]{query}[/bold]")
        console.print()

        if output == "json":
            print(json.dumps(result.to_dict(), indent=2, default=str))
        else:
            # Display answer
            console.print(result.answer)
            console.print()

            # Display sources
            if result.citations:
                console.print(f"[bold]Sources ({len(result.citations)}):[/bold]")
                for i, citation in enumerate(result.citations[:10], 1):
                    console.print(f"  [{i}] {citation.url}")
                if len(result.citations) > 10:
                    console.print(f"  ... and {len(result.citations) - 10} more")

        # Save if requested
        if save:
            # Create output directory
            sources_dir = Path("sources/research")
            sources_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename
            date_str = datetime.now().strftime("%Y-%m-%d")
            # Sanitize query for filename
            safe_query = "".join(c if c.isalnum() or c in (" ", "-") else "" for c in query)
            safe_query = safe_query.replace(" ", "-").lower()[:50]
            filename = f"{date_str}-{safe_query}.md"
            filepath = sources_dir / filename

            # Save as markdown
            with open(filepath, "w") as f:
                f.write(result.to_markdown())

            console.print()
            console.print(f"[green]✓ Saved to:[/green] {filepath}")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@research.command("list")
@click.option("--limit", type=int, default=20, help="Number of results to show")
@track_command
def list_cmd(limit: int):
    """
    List recent research results.

    Shows markdown files saved in sources/research/

    Example:
        kurt research list
        kurt research list --limit 10
    """
    try:
        sources_dir = Path("sources/research")

        if not sources_dir.exists():
            console.print("[yellow]No research results found[/yellow]")
            console.print('Run: [cyan]kurt research search "your query" --save[/cyan]')
            return

        # Find all markdown files
        md_files = sorted(
            sources_dir.glob("**/*.md"), key=lambda p: p.stat().st_mtime, reverse=True
        )

        if not md_files:
            console.print("[yellow]No research results found[/yellow]")
            return

        console.print(f"[bold]Recent Research ({len(md_files)} results)[/bold]\n")

        for filepath in md_files[:limit]:
            # Read frontmatter to get metadata
            try:
                with open(filepath, "r") as f:
                    content = f.read()
                    if content.startswith("---"):
                        import yaml

                        parts = content.split("---", 2)
                        if len(parts) >= 3:
                            frontmatter = yaml.safe_load(parts[1])
                            query = frontmatter.get("research_query", filepath.stem)
                            date = frontmatter.get("research_date", "")
                            sources_count = frontmatter.get("sources_count", 0)

                            console.print(f"[cyan]{filepath.name}[/cyan]")
                            console.print(f"  Query: {query}")
                            console.print(f"  Date: {str(date)[:10] if date else 'unknown'}")
                            console.print(f"  Sources: {sources_count}")
                            console.print()
            except Exception:
                console.print(f"[yellow]Could not read:[/yellow] {filepath.name}")
                console.print()

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@research.command("get")
@click.argument("filename")
@track_command
def get_cmd(filename: str):
    """
    Display a specific research result.

    Args:
        filename: Name of the research file (with or without .md extension)

    Example:
        kurt research get 2025-10-27-ai-coding-tools
    """
    try:
        sources_dir = Path("sources/research")

        # Add .md extension if not present
        if not filename.endswith(".md"):
            filename = f"{filename}.md"

        filepath = sources_dir / filename

        if not filepath.exists():
            console.print(f"[red]Error:[/red] Research result not found: {filename}")
            console.print("Run [cyan]kurt research list[/cyan] to see available results")
            raise click.Abort()

        # Read and display
        with open(filepath, "r") as f:
            content = f.read()

        # Parse frontmatter and display
        if content.startswith("---"):
            import yaml

            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = yaml.safe_load(parts[1])
                body = parts[2].strip()

                console.print("[bold cyan]Research Result[/bold cyan]")
                console.print(f"[dim]File: {filename}[/dim]\n")

                console.print(f"[bold]Query:[/bold] {frontmatter.get('research_query', 'N/A')}")
                console.print(
                    f"[bold]Date:[/bold] {str(frontmatter.get('research_date', 'N/A'))[:19]}"
                )
                console.print(f"[bold]Source:[/bold] {frontmatter.get('research_source', 'N/A')}")
                console.print(
                    f"[bold]Sources:[/bold] {frontmatter.get('sources_count', 0)} citations"
                )
                console.print()

                console.print(body)
        else:
            console.print(content)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@research.command("reddit")
@click.option("--subreddit", "-s", required=True, help="Subreddit name (e.g., dataengineering)")
@click.option(
    "--timeframe",
    "-t",
    type=click.Choice(["hour", "day", "week", "month"]),
    default="day",
    help="Time filter",
)
@click.option(
    "--sort", type=click.Choice(["hot", "new", "top", "rising"]), default="hot", help="Sort order"
)
@click.option("--limit", type=int, default=25, help="Maximum posts to fetch")
@click.option("--keywords", help="Comma-separated keywords to filter by")
@click.option("--min-score", type=int, default=0, help="Minimum score threshold")
@click.option(
    "--output", type=click.Choice(["table", "json"]), default="table", help="Output format"
)
@track_command
def reddit_cmd(
    subreddit: str,
    timeframe: str,
    sort: str,
    limit: int,
    keywords: Optional[str],
    min_score: int,
    output: str,
):
    """
    Monitor Reddit for trending discussions.

    Examples:
        kurt research reddit -s dataengineering --timeframe day
        kurt research reddit -s "datascience+machinelearning" --keywords "dbt,fivetran"
        kurt research reddit -s analytics --min-score 50 --output json
    """
    try:
        from kurt.integrations.research.monitoring.reddit import RedditAdapter

        adapter = RedditAdapter()

        # Parse keywords
        keyword_list = [k.strip() for k in keywords.split(",")] if keywords else None

        # Get posts
        console.print(f"[cyan]Monitoring:[/cyan] r/{subreddit}")
        if keyword_list:
            console.print(f"[dim]Keywords: {', '.join(keyword_list)}[/dim]")

        signals = adapter.get_subreddit_posts(
            subreddit=subreddit,
            timeframe=timeframe,
            sort=sort,
            limit=limit,
            keywords=keyword_list,
            min_score=min_score,
        )

        if not signals:
            console.print("[yellow]No posts found matching criteria[/yellow]")
            return

        # Display results
        console.print()
        console.print(f"[green]✓ Found {len(signals)} posts[/green]")
        console.print()

        if output == "json":
            print(json.dumps([s.to_dict() for s in signals], indent=2, default=str))
        else:
            from rich.table import Table

            table = Table(show_header=True)
            table.add_column("#", style="dim", width=4)
            table.add_column("Title", style="cyan", no_wrap=False, max_width=60)
            table.add_column("Score", justify="right", style="green")
            table.add_column("Comments", justify="right", style="yellow")
            table.add_column("Relevance", justify="right", style="magenta")

            for i, signal in enumerate(signals, 1):
                table.add_row(
                    str(i),
                    signal.title[:60] + "..." if len(signal.title) > 60 else signal.title,
                    str(signal.score),
                    str(signal.comment_count),
                    f"{signal.relevance_score:.2f}",
                )

            console.print(table)
            console.print()
            console.print("[dim]Use --output json to see full details including URLs[/dim]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@research.command("hackernews")
@click.option(
    "--timeframe",
    "-t",
    type=click.Choice(["hour", "day", "week", "month"]),
    default="day",
    help="Time filter",
)
@click.option("--keywords", help="Comma-separated keywords to filter by")
@click.option("--min-score", type=int, default=10, help="Minimum score threshold")
@click.option("--limit", type=int, default=30, help="Maximum stories to fetch")
@click.option(
    "--output", type=click.Choice(["table", "json"]), default="table", help="Output format"
)
@track_command
def hackernews_cmd(
    timeframe: str, keywords: Optional[str], min_score: int, limit: int, output: str
):
    """
    Monitor Hacker News for trending tech discussions.

    Examples:
        kurt research hackernews --timeframe day
        kurt research hackernews --keywords "dbt,data pipeline" --min-score 50
        kurt research hackernews --timeframe week --output json
    """
    try:
        from kurt.integrations.research.monitoring.hackernews import HackerNewsAdapter

        adapter = HackerNewsAdapter()

        # Parse keywords
        keyword_list = [k.strip() for k in keywords.split(",")] if keywords else None

        # Get stories
        console.print(f"[cyan]Monitoring:[/cyan] Hacker News ({timeframe})")
        if keyword_list:
            console.print(f"[dim]Keywords: {', '.join(keyword_list)}[/dim]")

        # Map timeframe to hours
        timeframe_hours = {"hour": 1, "day": 24, "week": 168, "month": 720}

        signals = adapter.get_recent(
            hours=timeframe_hours[timeframe], keywords=keyword_list, min_score=min_score
        )

        # Apply limit
        signals = signals[:limit]

        if not signals:
            console.print("[yellow]No stories found matching criteria[/yellow]")
            return

        # Display results
        console.print()
        console.print(f"[green]✓ Found {len(signals)} stories[/green]")
        console.print()

        if output == "json":
            print(json.dumps([s.to_dict() for s in signals], indent=2, default=str))
        else:
            from rich.table import Table

            table = Table(show_header=True)
            table.add_column("#", style="dim", width=4)
            table.add_column("Title", style="cyan", no_wrap=False, max_width=60)
            table.add_column("Points", justify="right", style="green")
            table.add_column("Comments", justify="right", style="yellow")
            table.add_column("Relevance", justify="right", style="magenta")

            for i, signal in enumerate(signals, 1):
                table.add_row(
                    str(i),
                    signal.title[:60] + "..." if len(signal.title) > 60 else signal.title,
                    str(signal.score),
                    str(signal.comment_count),
                    f"{signal.relevance_score:.2f}",
                )

            console.print(table)
            console.print()
            console.print("[dim]Use --output json to see full details including URLs[/dim]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@research.command("feeds")
@click.argument("feed_url")
@click.option("--since", help="Only show entries since (e.g., '7 days', '24 hours')")
@click.option("--keywords", help="Comma-separated keywords to filter by")
@click.option("--limit", type=int, default=50, help="Maximum entries to fetch")
@click.option(
    "--output", type=click.Choice(["table", "json"]), default="table", help="Output format"
)
@track_command
def feeds_cmd(
    feed_url: str, since: Optional[str], keywords: Optional[str], limit: int, output: str
):
    """
    Monitor RSS/Atom feeds for new content.

    Examples:
        kurt research feeds https://blog.getdbt.com/rss.xml
        kurt research feeds https://fivetran.com/blog/rss.xml --since "7 days"
        kurt research feeds https://airbyte.com/blog/rss.xml --keywords "connector" --output json
    """
    try:
        from datetime import timedelta

        from kurt.integrations.research.monitoring.feeds import FeedAdapter

        adapter = FeedAdapter()

        # Parse since parameter
        since_dt = None
        if since:
            # Simple parsing (e.g., "7 days", "24 hours")
            parts = since.split()
            if len(parts) == 2:
                value = int(parts[0])
                unit = parts[1].lower()
                if unit.startswith("day"):
                    since_dt = datetime.now() - timedelta(days=value)
                elif unit.startswith("hour"):
                    since_dt = datetime.now() - timedelta(hours=value)
                elif unit.startswith("week"):
                    since_dt = datetime.now() - timedelta(weeks=value)

        # Parse keywords
        keyword_list = [k.strip() for k in keywords.split(",")] if keywords else None

        # Get feed entries
        console.print(f"[cyan]Monitoring feed:[/cyan] {feed_url}")
        if since_dt:
            console.print(f"[dim]Since: {since_dt.strftime('%Y-%m-%d %H:%M')}[/dim]")
        if keyword_list:
            console.print(f"[dim]Keywords: {', '.join(keyword_list)}[/dim]")

        signals = adapter.get_feed_entries(
            feed_url=feed_url, since=since_dt, keywords=keyword_list, limit=limit
        )

        if not signals:
            console.print("[yellow]No entries found matching criteria[/yellow]")
            return

        # Display results
        console.print()
        console.print(f"[green]✓ Found {len(signals)} entries[/green]")
        console.print()

        if output == "json":
            print(json.dumps([s.to_dict() for s in signals], indent=2, default=str))
        else:
            from rich.table import Table

            table = Table(show_header=True)
            table.add_column("#", style="dim", width=4)
            table.add_column("Title", style="cyan", no_wrap=False, max_width=50)
            table.add_column("Published", style="white")
            table.add_column("Domain", style="blue")

            for i, signal in enumerate(signals, 1):
                table.add_row(
                    str(i),
                    signal.title[:50] + "..." if len(signal.title) > 50 else signal.title,
                    signal.timestamp.strftime("%Y-%m-%d %H:%M") if signal.timestamp else "Unknown",
                    signal.domain or "N/A",
                )

            console.print(table)
            console.print()
            console.print(
                "[dim]Use --output json to see full details including URLs and snippets[/dim]"
            )

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@research.command("monitor")
@click.argument("project_path")
@click.option("--save/--no-save", default=True, help="Save signals to project")
@click.option(
    "--output", type=click.Choice(["summary", "json"]), default="summary", help="Output format"
)
@track_command
def monitor_cmd(project_path: str, save: bool, output: str):
    """
    Run monitoring for a project based on its monitoring-config.yaml.

    Examples:
        kurt research monitor projects/competitor-watch
        kurt research monitor projects/ai-coding-news --save
        kurt research monitor projects/my-project --output json
    """
    try:
        from datetime import datetime, timedelta
        from pathlib import Path

        from kurt.integrations.research.monitoring.config import (
            get_enabled_sources,
            get_project_signals_dir,
            load_monitoring_config,
            monitoring_config_exists,
            validate_monitoring_config,
        )
        from kurt.integrations.research.monitoring.feeds import FeedAdapter
        from kurt.integrations.research.monitoring.hackernews import HackerNewsAdapter
        from kurt.integrations.research.monitoring.reddit import RedditAdapter

        # Check if monitoring config exists
        if not monitoring_config_exists(project_path):
            console.print(f"[red]Error:[/red] No monitoring config found in {project_path}")
            console.print("Create monitoring-config.yaml in your project directory")
            console.print("See projects/.monitoring-config-template.yaml for example")
            raise click.Abort()

        # Load config
        config = load_monitoring_config(project_path)

        # Validate config
        warnings = validate_monitoring_config(config)
        if warnings:
            console.print("[yellow]Configuration warnings:[/yellow]")
            for warning in warnings:
                console.print(f"  - {warning}")
            console.print()

        project_name = config.get("project_name", Path(project_path).name)
        console.print(f"[cyan]Monitoring project:[/cyan] {project_name}")
        console.print()

        # Get enabled sources
        enabled_sources = get_enabled_sources(config)
        if not enabled_sources:
            console.print("[yellow]No monitoring sources enabled[/yellow]")
            return

        all_signals = []

        # Monitor Reddit
        if "reddit" in enabled_sources:
            reddit_config = config["sources"]["reddit"]
            subreddits = reddit_config.get("subreddits", [])
            keywords = reddit_config.get("keywords", [])
            min_score = reddit_config.get("min_score", 10)
            timeframe = reddit_config.get("timeframe", "day")

            if subreddits:
                console.print(
                    f"[cyan]→[/cyan] Monitoring Reddit: {', '.join(f'r/{s}' for s in subreddits)}"
                )
                adapter = RedditAdapter()

                for subreddit in subreddits:
                    try:
                        signals = adapter.get_subreddit_posts(
                            subreddit=subreddit,
                            timeframe=timeframe,
                            keywords=keywords if keywords else None,
                            min_score=min_score,
                        )
                        # Associate with project
                        for signal in signals:
                            signal.project = project_name
                        all_signals.extend(signals)
                    except Exception as e:
                        console.print(
                            f"  [yellow]Warning: Failed to fetch r/{subreddit}: {e}[/yellow]"
                        )

        # Monitor Hacker News
        if "hackernews" in enabled_sources:
            hn_config = config["sources"]["hackernews"]
            keywords = hn_config.get("keywords", [])
            min_score = hn_config.get("min_score", 50)
            timeframe = hn_config.get("timeframe", "day")

            console.print("[cyan]→[/cyan] Monitoring Hacker News")
            adapter = HackerNewsAdapter()

            timeframe_hours = {"hour": 1, "day": 24, "week": 168, "month": 720}

            try:
                signals = adapter.get_recent(
                    hours=timeframe_hours[timeframe],
                    keywords=keywords if keywords else None,
                    min_score=min_score,
                )
                # Associate with project
                for signal in signals:
                    signal.project = project_name
                all_signals.extend(signals)
            except Exception as e:
                console.print(f"  [yellow]Warning: Failed to fetch HN: {e}[/yellow]")

        # Monitor RSS feeds
        if "feeds" in enabled_sources:
            feeds_config = config["sources"]["feeds"]
            feed_urls = feeds_config.get("urls", [])
            since_str = feeds_config.get("since", "7 days")

            if feed_urls:
                console.print(f"[cyan]→[/cyan] Monitoring {len(feed_urls)} RSS feeds")
                adapter = FeedAdapter()

                # Parse since parameter
                since_dt = None
                parts = since_str.split()
                if len(parts) == 2:
                    value = int(parts[0])
                    unit = parts[1].lower()
                    if unit.startswith("day"):
                        since_dt = datetime.now() - timedelta(days=value)
                    elif unit.startswith("hour"):
                        since_dt = datetime.now() - timedelta(hours=value)
                    elif unit.startswith("week"):
                        since_dt = datetime.now() - timedelta(weeks=value)

                for feed_info in feed_urls:
                    feed_url = feed_info.get("url") if isinstance(feed_info, dict) else feed_info
                    feed_name = (
                        feed_info.get("name", feed_url) if isinstance(feed_info, dict) else feed_url
                    )
                    feed_keywords = (
                        feed_info.get("keywords", []) if isinstance(feed_info, dict) else []
                    )

                    try:
                        signals = adapter.get_feed_entries(
                            feed_url=feed_url,
                            since=since_dt,
                            keywords=feed_keywords if feed_keywords else None,
                        )
                        # Associate with project
                        for signal in signals:
                            signal.project = project_name
                        all_signals.extend(signals)
                    except Exception as e:
                        console.print(
                            f"  [yellow]Warning: Failed to fetch {feed_name}: {e}[/yellow]"
                        )

        # Sort by relevance
        all_signals.sort(key=lambda s: s.relevance_score, reverse=True)

        # Display results
        console.print()
        console.print(f"[green]✓ Found {len(all_signals)} total signals[/green]")

        if not all_signals:
            return

        # Save signals if requested
        if save:
            signals_dir = get_project_signals_dir(project_path)
            date_str = datetime.now().strftime("%Y-%m-%d")
            signal_file = signals_dir / f"{date_str}-signals.json"

            # Save as JSON
            with open(signal_file, "w") as f:
                json.dump([s.to_dict() for s in all_signals], f, indent=2, default=str)

            console.print(f"[green]✓ Saved signals to:[/green] {signal_file}")

        # Output
        if output == "json":
            print(json.dumps([s.to_dict() for s in all_signals], indent=2, default=str))
        else:
            # Show top 10 signals
            console.print()
            console.print("[bold]Top Signals:[/bold]")
            console.print()

            from rich.table import Table

            table = Table(show_header=True)
            table.add_column("#", style="dim", width=4)
            table.add_column("Source", style="blue", width=8)
            table.add_column("Title", style="cyan", no_wrap=False, max_width=50)
            table.add_column("Score", justify="right", style="green")
            table.add_column("Relevance", justify="right", style="magenta")

            for i, signal in enumerate(all_signals[:10], 1):
                source_display = {
                    "reddit": f"r/{signal.subreddit}" if signal.subreddit else "reddit",
                    "hackernews": "HN",
                    "rss": signal.domain[:15] if signal.domain else "RSS",
                }.get(signal.source, signal.source)

                table.add_row(
                    str(i),
                    source_display,
                    signal.title[:50] + "..." if len(signal.title) > 50 else signal.title,
                    str(signal.score),
                    f"{signal.relevance_score:.2f}",
                )

            console.print(table)

            if len(all_signals) > 10:
                console.print()
                console.print(f"[dim]... and {len(all_signals) - 10} more signals[/dim]")
                console.print("[dim]Use --output json to see all signals[/dim]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()

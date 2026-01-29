"""CLI commands for map and fetch operations with backward compatibility."""

import click
import warnings
from typing import Optional

from kurt.tools.map.subcommands import (
    MapDocSubcommand,
    MapProfileSubcommand,
    MapPostsSubcommand,
)
from kurt.tools.fetch.subcommands import (
    FetchDocSubcommand,
    FetchProfileSubcommand,
    FetchPostsSubcommand,
)


@click.group("tools")
def tools_cli():
    """Tools for web mapping and content fetching."""
    pass


@tools_cli.group("map")
def map_group():
    """Discover content URLs and metadata."""
    pass


@tools_cli.group("fetch")
def fetch_group():
    """Fetch and extract content."""
    pass


# Map commands
@map_group.command("doc")
@click.argument("url")
@click.option(
    "--depth",
    default=3,
    help="Crawl depth limit",
    type=int,
)
@click.option(
    "--include-pattern",
    default=None,
    help="URL inclusion regex pattern",
)
@click.option(
    "--exclude-pattern",
    default=None,
    help="URL exclusion regex pattern",
)
@click.option(
    "--engine",
    default="crawl",
    type=click.Choice(["crawl", "sitemap", "rss"]),
    help="Mapper engine",
)
def map_doc(url: str, depth: int, include_pattern: Optional[str], exclude_pattern: Optional[str], engine: str):
    """Discover document URLs from a website."""
    click.echo(f"Mapping documents from {url} with depth={depth}")
    click.echo(f"  Include pattern: {include_pattern}")
    click.echo(f"  Exclude pattern: {exclude_pattern}")
    click.echo(f"  Engine: {engine}")


@map_group.command("profile")
@click.argument("query")
@click.option(
    "--platform",
    required=True,
    type=click.Choice(["twitter", "linkedin", "instagram", "youtube"]),
    help="Social platform to search",
)
@click.option(
    "--limit",
    default=100,
    help="Maximum results",
    type=int,
)
def map_profile(query: str, platform: str, limit: int):
    """Discover social media profiles matching a query."""
    click.echo(f"Mapping {platform} profiles for query: {query}")
    click.echo(f"  Limit: {limit}")


@map_group.command("posts")
@click.argument("source", required=False)
@click.option(
    "--limit",
    default=100,
    help="Maximum results",
    type=int,
)
@click.option(
    "--since",
    default=None,
    help="Date filter (YYYY-MM-DD)",
)
@click.option(
    "--platform",
    default=None,
    help="Platform filter",
)
def map_posts(source: Optional[str], limit: int, since: Optional[str], platform: Optional[str]):
    """Discover social media posts."""
    click.echo(f"Mapping posts from source: {source}")
    click.echo(f"  Limit: {limit}")
    if since:
        click.echo(f"  Since: {since}")
    if platform:
        click.echo(f"  Platform: {platform}")


# Fetch commands
@fetch_group.command("doc")
@click.argument("urls", nargs=-1, required=True)
@click.option(
    "--engine",
    default="trafilatura",
    type=click.Choice(["trafilatura", "firecrawl", "apify"]),
    help="Fetch engine",
)
def fetch_doc(urls: tuple, engine: str):
    """Fetch document content from URLs."""
    click.echo(f"Fetching {len(urls)} documents using {engine} engine")
    for url in urls:
        click.echo(f"  {url}")


@fetch_group.command("profile")
@click.argument("urls", nargs=-1, required=True)
@click.option(
    "--platform",
    required=True,
    type=click.Choice(["twitter", "linkedin", "instagram"]),
    help="Platform to fetch from",
)
def fetch_profile(urls: tuple, platform: str):
    """Fetch full profile details from social platforms."""
    click.echo(f"Fetching {len(urls)} {platform} profiles")
    for url in urls:
        click.echo(f"  {url}")


@fetch_group.command("posts")
@click.argument("urls", nargs=-1, required=True)
@click.option(
    "--platform",
    required=True,
    type=click.Choice(["twitter", "linkedin", "instagram"]),
    help="Platform to fetch from",
)
def fetch_posts(urls: tuple, platform: str):
    """Fetch full post content from social platforms."""
    click.echo(f"Fetching {len(urls)} {platform} posts")
    for url in urls:
        click.echo(f"  {url}")


# Deprecated aliases for backward compatibility
@map_group.command("discover")
@click.argument("url")
@click.option("--depth", default=3, type=int)
@click.option("--pattern", default=None)
def map_discover(url: str, depth: int, pattern: Optional[str]):
    """Deprecated: Use 'map doc' instead."""
    warnings.warn(
        "Command 'map discover' is deprecated. Use 'map doc' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    click.echo(f"(Deprecated) Discovering documents from {url}")


@fetch_group.command("content")
@click.argument("urls", nargs=-1, required=True)
def fetch_content(urls: tuple):
    """Deprecated: Use 'fetch doc' instead."""
    warnings.warn(
        "Command 'fetch content' is deprecated. Use 'fetch doc' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    click.echo(f"(Deprecated) Fetching {len(urls)} documents")


if __name__ == "__main__":
    tools_cli()

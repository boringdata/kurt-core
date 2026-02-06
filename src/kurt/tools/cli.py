"""CLI commands for map and fetch operations with backward compatibility."""

import warnings
from typing import Optional

import click

from kurt.tools.fetch.core import FetcherConfig
from kurt.tools.fetch.engines import EngineRegistry as FetchEngineRegistry
from kurt.tools.fetch.engines.apify import ApifyFetcherConfig
from kurt.tools.fetch.subcommands import (
    FetchDocSubcommand,
    FetchPostsSubcommand,
    FetchProfileSubcommand,
)
from kurt.tools.map.core import MapperConfig
from kurt.tools.map.engines import EngineRegistry as MapEngineRegistry
from kurt.tools.map.engines.apify import ApifyEngine, ApifyMapperConfig
from kurt.tools.map.subcommands import (
    MapDocSubcommand,
    MapPostsSubcommand,
    MapProfileSubcommand,
)


@click.group("tools")
def tools_cli():
    """Tools for web mapping and content fetching."""
    pass


# Alias for main CLI registration
tools_group = tools_cli


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
    type=click.Choice(["crawl", "sitemap", "rss", "cms", "folder"]),
    help="Mapper engine",
)
def map_doc(url: str, depth: int, include_pattern: Optional[str], exclude_pattern: Optional[str], engine: str):
    """Discover document URLs from a website."""
    try:
        config = MapperConfig(
            max_depth=depth,
            include_pattern=include_pattern,
            exclude_pattern=exclude_pattern,
        )

        # Select mapper engine from registry
        try:
            engine_class = MapEngineRegistry.get(engine)
            mapper = engine_class(config)
        except KeyError:
            click.echo(f"Error: Unknown engine '{engine}'", err=True)
            raise SystemExit(1)

        subcommand = MapDocSubcommand(mapper)
        results = subcommand.run(url, depth=depth, include_pattern=include_pattern, exclude_pattern=exclude_pattern)

        # Output results
        click.echo(f"Discovered {len(results)} documents:")
        for result in results:
            click.echo(result.url)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


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
    try:
        config = ApifyMapperConfig(max_items=limit, platform=platform)
        mapper = ApifyEngine(config)
        subcommand = MapProfileSubcommand(mapper)
        results = subcommand.run(query, platform=platform, limit=limit)

        click.echo(f"Discovered {len(results)} {platform} profiles:")
        for result in results:
            click.echo(f"{result.url} (@{result.username})")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


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
    try:
        config = ApifyMapperConfig(max_items=limit, platform=platform)
        mapper = ApifyEngine(config)
        subcommand = MapPostsSubcommand(mapper)
        results = subcommand.run(source or "", limit=limit, since=since)

        click.echo(f"Discovered {len(results)} posts:")
        for result in results:
            click.echo(f"{result.url}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


# Fetch commands
@fetch_group.command("doc")
@click.argument("urls", nargs=-1, required=True)
@click.option(
    "--engine",
    default="trafilatura",
    type=click.Choice(["trafilatura", "httpx", "firecrawl", "apify", "tavily", "twitterapi"]),
    help="Fetch engine",
)
def fetch_doc(urls: tuple, engine: str):
    """Fetch document content from URLs."""
    try:
        config = FetcherConfig()

        # Select fetcher engine from registry
        try:
            engine_class = FetchEngineRegistry.get(engine)
            fetcher = engine_class(config)
        except KeyError:
            click.echo(f"Error: Unknown engine '{engine}'", err=True)
            raise SystemExit(1)

        subcommand = FetchDocSubcommand(fetcher)
        results = subcommand.run(list(urls))

        click.echo(f"Fetched {len(results)} documents:")
        for result in results:
            click.echo(f"URL: {result.url}")
            click.echo(f"Content length: {len(result.content_text)} chars")
            click.echo()
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@fetch_group.command("profile")
@click.argument("urls", nargs=-1, required=True)
@click.option(
    "--platform",
    required=False,
    type=click.Choice(["twitter", "linkedin", "instagram"]),
    help="Platform to fetch from (auto-detected for twitterapi engine)",
)
@click.option(
    "--engine",
    default="apify",
    type=click.Choice(["apify", "twitterapi"]),
    help="Fetch engine",
)
def fetch_profile(urls: tuple, platform: Optional[str], engine: str):
    """Fetch full profile details from social platforms."""
    try:
        # TwitterAPI engine doesn't need platform (auto-detects from URL)
        if engine == "twitterapi":
            from kurt.tools.fetch.engines.twitterapi import TwitterApiFetcher

            fetcher = TwitterApiFetcher()
            for url in urls:
                result = fetcher.fetch(url)
                if result.success:
                    click.echo(result.content)
                else:
                    click.echo(f"Error: {result.error}", err=True)
            return

        # Apify engine requires platform
        if not platform:
            click.echo("Error: --platform is required for apify engine", err=True)
            raise SystemExit(1)

        config = ApifyFetcherConfig(platform=platform)

        # Select fetcher engine from registry
        try:
            engine_class = FetchEngineRegistry.get(engine)
            fetcher = engine_class(config)
        except KeyError:
            click.echo(f"Error: Unknown engine '{engine}'", err=True)
            raise SystemExit(1)

        subcommand = FetchProfileSubcommand(fetcher)
        results = subcommand.run(list(urls), platform=platform)

        click.echo(f"Fetched {len(results)} {platform} profiles:")
        for result in results:
            click.echo(f"Username: @{result.username}")
            click.echo(f"Bio: {result.bio[:100] if result.bio else 'N/A'}...")
            click.echo()
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@fetch_group.command("posts")
@click.argument("urls", nargs=-1, required=True)
@click.option(
    "--platform",
    required=True,
    type=click.Choice(["twitter", "linkedin", "instagram"]),
    help="Platform to fetch from",
)
@click.option(
    "--engine",
    default="apify",
    type=click.Choice(["apify"]),
    help="Fetch engine",
)
def fetch_posts(urls: tuple, platform: str, engine: str):
    """Fetch full post content from social platforms."""
    try:
        config = ApifyFetcherConfig(platform=platform)

        # Select fetcher engine from registry
        try:
            engine_class = FetchEngineRegistry.get(engine)
            fetcher = engine_class(config)
        except KeyError:
            click.echo(f"Error: Unknown engine '{engine}'", err=True)
            raise SystemExit(1)

        subcommand = FetchPostsSubcommand(fetcher)
        results = subcommand.run(list(urls), platform=platform)

        click.echo(f"Fetched {len(results)} {platform} posts:")
        for result in results:
            click.echo(f"Post ID: {result.post_id}")
            click.echo(f"Content: {result.content_text[:100]}...")
            click.echo(f"Likes: {result.likes_count}, Replies: {result.replies_count}")
            click.echo()
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


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

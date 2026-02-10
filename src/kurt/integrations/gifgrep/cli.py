"""
CLI commands for GIF search.
"""

import json

import click

from kurt.integrations.gifgrep.client import GifgrepClient, GifgrepError


@click.group()
def gif_group():
    """
    GIF search integration.

    Search for GIFs using the Tenor API.

    \b
    Commands:
      search    Search GIFs by keyword
      trending  Get trending GIFs
      random    Get a random GIF for a query

    \b
    Configuration:
      Set TENOR_API_KEY env var for higher rate limits.
      Without an API key, uses Tenor's public demo key.
    """
    pass


@gif_group.command("search")
@click.argument("query", nargs=-1, required=True)
@click.option(
    "--limit", "-n",
    default=10,
    type=click.IntRange(1, 50),
    help="Number of results (1-50).",
)
@click.option(
    "--filter",
    "content_filter",
    type=click.Choice(["off", "low", "medium", "high"]),
    default="medium",
    help="Content safety filter level.",
)
@click.option(
    "--json", "output_json",
    is_flag=True,
    help="Output as JSON.",
)
@click.option(
    "--urls-only",
    is_flag=True,
    help="Output only GIF URLs (one per line).",
)
def search_cmd(query, limit, content_filter, output_json, urls_only):
    """
    Search for GIFs by keyword.

    \b
    Examples:
      kurt integrations gif search funny cat
      kurt integrations gif search "thumbs up" --limit 5
      kurt integrations gif search celebration --json
      kurt integrations gif search success --urls-only
    """
    query_str = " ".join(query)

    try:
        client = GifgrepClient()
        results = client.search(query_str, limit=limit, content_filter=content_filter)

        if not results:
            if output_json:
                click.echo(json.dumps([]))
            else:
                click.echo(f"No GIFs found for '{query_str}'")
            return

        if output_json:
            click.echo(json.dumps([r.to_dict() for r in results], indent=2))
        elif urls_only:
            for gif in results:
                click.echo(gif.url)
        else:
            for i, gif in enumerate(results, 1):
                click.echo(f"\n{i}. {gif.title or '(no title)'}")
                click.echo(f"   URL: {gif.url}")
                if gif.preview_url and gif.preview_url != gif.url:
                    click.echo(f"   Preview: {gif.preview_url}")
                click.echo(f"   Size: {gif.width}x{gif.height}")
                if gif.tags:
                    click.echo(f"   Tags: {', '.join(gif.tags[:5])}")

    except GifgrepError as e:
        raise click.ClickException(str(e))


@gif_group.command("trending")
@click.option(
    "--limit", "-n",
    default=10,
    type=click.IntRange(1, 50),
    help="Number of results (1-50).",
)
@click.option(
    "--filter",
    "content_filter",
    type=click.Choice(["off", "low", "medium", "high"]),
    default="medium",
    help="Content safety filter level.",
)
@click.option(
    "--json", "output_json",
    is_flag=True,
    help="Output as JSON.",
)
@click.option(
    "--urls-only",
    is_flag=True,
    help="Output only GIF URLs (one per line).",
)
def trending_cmd(limit, content_filter, output_json, urls_only):
    """
    Get trending GIFs.

    \b
    Examples:
      kurt integrations gif trending
      kurt integrations gif trending --limit 20 --json
    """
    try:
        client = GifgrepClient()
        results = client.trending(limit=limit, content_filter=content_filter)

        if not results:
            if output_json:
                click.echo(json.dumps([]))
            else:
                click.echo("No trending GIFs found")
            return

        if output_json:
            click.echo(json.dumps([r.to_dict() for r in results], indent=2))
        elif urls_only:
            for gif in results:
                click.echo(gif.url)
        else:
            click.echo("Trending GIFs:")
            for i, gif in enumerate(results, 1):
                click.echo(f"\n{i}. {gif.title or '(no title)'}")
                click.echo(f"   URL: {gif.url}")
                click.echo(f"   Size: {gif.width}x{gif.height}")

    except GifgrepError as e:
        raise click.ClickException(str(e))


@gif_group.command("random")
@click.argument("query", nargs=-1, required=True)
@click.option(
    "--filter",
    "content_filter",
    type=click.Choice(["off", "low", "medium", "high"]),
    default="medium",
    help="Content safety filter level.",
)
@click.option(
    "--json", "output_json",
    is_flag=True,
    help="Output as JSON.",
)
def random_cmd(query, content_filter, output_json):
    """
    Get a random GIF for a search query.

    \b
    Examples:
      kurt integrations gif random success
      kurt integrations gif random "high five" --json
    """
    query_str = " ".join(query)

    try:
        client = GifgrepClient()
        result = client.random(query_str, content_filter=content_filter)

        if not result:
            if output_json:
                click.echo(json.dumps(None))
            else:
                click.echo(f"No GIF found for '{query_str}'")
            return

        if output_json:
            click.echo(json.dumps(result.to_dict(), indent=2))
        else:
            click.echo(f"Random GIF for '{query_str}':")
            click.echo(f"  Title: {result.title or '(no title)'}")
            click.echo(f"  URL: {result.url}")
            if result.preview_url and result.preview_url != result.url:
                click.echo(f"  Preview: {result.preview_url}")
            click.echo(f"  Size: {result.width}x{result.height}")

    except GifgrepError as e:
        raise click.ClickException(str(e))

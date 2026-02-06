"""CLI commands for tool operations."""

import click

from kurt.tools.analytics.cli import analytics_group
from kurt.tools.fetch.cli import fetch_cmd
from kurt.tools.map.cli import map_cmd
from kurt.tools.research.cli import research_group
from kurt.tools.signals.cli import signals_group


@click.group("tools")
def tools_group():
    """
    Tools for content discovery, extraction, and monitoring.

    \b
    Commands:
      map        Discover content URLs from websites, folders, or CMS
      fetch      Fetch and extract content from URLs
      research   Execute research queries via Perplexity
      signals    Monitor Reddit, HackerNews, and RSS feeds
      analytics  Sync domain analytics from PostHog/GA4/Plausible
    """
    pass


tools_group.add_command(map_cmd, "map")
tools_group.add_command(fetch_cmd, "fetch")
tools_group.add_command(research_group, "research")
tools_group.add_command(signals_group, "signals")
tools_group.add_command(analytics_group, "analytics")

# Alias for main CLI registration
tools_cli = tools_group

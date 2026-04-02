"""CLI commands for tool operations."""

import click

from kurt.tools.analytics.cli import analytics_group
from kurt.tools.fetch.cli import fetch_cmd
from kurt.tools.map.cli import map_cmd
from kurt.tools.provider_cli import (
    check_cmd,
    info_cmd,
    list_tools_cmd,
    new_provider_cmd,
    new_tool_cmd,
    providers_cmd,
)
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

    \b
    Provider management:
      list       List all tools and their providers
      info       Show detailed tool information
      providers  List providers for a specific tool
      check      Validate tool/provider requirements
    """
    pass


tools_group.add_command(map_cmd, "map")
tools_group.add_command(fetch_cmd, "fetch")
tools_group.add_command(research_group, "research")
tools_group.add_command(signals_group, "signals")
tools_group.add_command(analytics_group, "analytics")

# Provider management commands
tools_group.add_command(list_tools_cmd, "list")
tools_group.add_command(info_cmd, "info")
tools_group.add_command(providers_cmd, "providers")
tools_group.add_command(check_cmd, "check")
tools_group.add_command(new_tool_cmd, "new")
tools_group.add_command(new_provider_cmd, "new-provider")

# Alias for main CLI registration
tools_cli = tools_group

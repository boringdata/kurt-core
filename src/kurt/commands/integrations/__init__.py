"""Integration commands for external services."""

import click

from .analytics import analytics
from .cms import cms
from .research import research


@click.group()
def integrations():
    """
    Integrate with external services.

    \b
    Available integrations:
    - analytics: PostHog and analytics platforms
    - cms: CMS platforms (Sanity, Contentful, etc.)
    - research: Research and topic discovery
    """
    pass


# Register all integration commands
integrations.add_command(analytics)
integrations.add_command(cms)
integrations.add_command(research)

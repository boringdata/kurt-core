"""CLI commands for integrations.

Aggregates CLI commands from all integration modules.
"""

import click

from kurt_new.integrations.cms.cli import cms_group
from kurt_new.integrations.domains_analytics.cli import analytics_group
from kurt_new.integrations.research.cli import research_group as research_setup_group


@click.group()
def integrations_group():
    """
    External service integrations.

    \b
    Integrations:
      cms         CMS platforms (Sanity, Contentful, WordPress)
      analytics   Domain analytics (PostHog, GA4, Plausible)
      research    Research APIs (Perplexity)
    """
    pass


integrations_group.add_command(cms_group, "cms")
integrations_group.add_command(analytics_group, "analytics")
integrations_group.add_command(research_setup_group, "research")

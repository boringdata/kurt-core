"""CLI commands for integrations.

Aggregates CLI commands from all integration modules.
"""

import click

from kurt_new.integrations.cms.cli import cms_group
from kurt_new.integrations.domains_analytics.cli import analytics_group


@click.group()
def integrations_group():
    """
    External service integrations.

    \b
    Integrations:
      cms         CMS platforms (Sanity, Contentful, WordPress)
      analytics   Domain analytics (PostHog, GA4, Plausible)
    """
    pass


integrations_group.add_command(cms_group, "cms")
integrations_group.add_command(analytics_group, "analytics")

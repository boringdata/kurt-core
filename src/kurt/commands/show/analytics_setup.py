"""Show analytics integration setup instructions."""

import click


@click.command()
def analytics_setup_cmd():
    """Show instructions for analytics integration setup."""
    content = """
═══════════════════════════════════════════════════════════════════
ANALYTICS INTEGRATION
═══════════════════════════════════════════════════════════════════

Kurt can analyze web analytics to assist with project planning and
content performance analysis (currently supports PostHog).

═══════════════════════════════════════════════════════════════════
SETUP
═══════════════════════════════════════════════════════════════════

CHECK EXISTING:
kurt integrations analytics list

CONFIGURE NEW:
kurt integrations analytics onboard [domain] --platform {platform}

═══════════════════════════════════════════════════════════════════
USAGE
═══════════════════════════════════════════════════════════════════

SYNC DATA:
kurt integrations analytics sync [domain]

QUERY ANALYTICS:
kurt integrations analytics query [domain]

  • Filter by traffic, trends, URL patterns
  • Find high-traffic pages not yet indexed:
    kurt integrations analytics query [domain] --missing-docs

QUERY WITH DOCUMENTS:
kurt content list --with-analytics

  • Documents enriched with analytics data
  • Useful for prioritization and performance analysis

═══════════════════════════════════════════════════════════════════
"""
    click.echo(content.strip())

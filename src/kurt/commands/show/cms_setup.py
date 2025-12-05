"""Show CMS integration setup instructions."""

import click


@click.command()
def cms_setup_cmd():
    """Show instructions for CMS integration setup."""
    content = """
═══════════════════════════════════════════════════════════════════
CMS INTEGRATION
═══════════════════════════════════════════════════════════════════

Kurt supports CMS integrations for reading and publishing content.
Currently only Sanity is supported; Contentful and WordPress are
coming soon.

═══════════════════════════════════════════════════════════════════
READING FROM CMS
═══════════════════════════════════════════════════════════════════

CHECK CONFIGURATION:
kurt integrations cms status

IF NOT CONFIGURED:
kurt integrations cms onboard --platform {platform}

FETCH CONTENT:
kurt content fetch {cms-url}

  • Automatically uses CMS adapters
  • For detailed workflow, run: kurt show source-workflow

═══════════════════════════════════════════════════════════════════
KEEPING CMS CONTENT UP TO DATE
═══════════════════════════════════════════════════════════════════

Periodically update sources to discover new or modified content.

See "Updating Existing Sources" section in:
  kurt show source-workflow

═══════════════════════════════════════════════════════════════════
PUBLISHING TO CMS
═══════════════════════════════════════════════════════════════════

PUBLISH AS DRAFT:
kurt integrations cms publish --file {path} --content-type {type}

⚠️  IMPORTANT:
  • Kurt only creates drafts, never publishes to live status
  • User must review and publish manually in CMS

═══════════════════════════════════════════════════════════════════
"""
    click.echo(content.strip())

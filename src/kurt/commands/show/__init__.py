"""Show commands - display instructions and available options."""

import click

from .format_templates import format_templates_cmd
from .plan_updates import plan_updates_cmd
from .source_gathering import source_gathering_cmd


@click.group()
def show():
    """
    Show instructions and available options.

    \b
    Available commands:
    - format-templates: List available format templates
    - source-gathering: Display source gathering strategy
    - plan-updates: Show plan.md update checklist
    """
    pass


# Register all subcommands
show.add_command(format_templates_cmd, name="format-templates")
show.add_command(source_gathering_cmd, name="source-gathering")
show.add_command(plan_updates_cmd, name="plan-updates")

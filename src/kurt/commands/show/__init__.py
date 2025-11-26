"""Show commands - display instructions and available options."""

import click

from .analytics_setup import analytics_setup_cmd
from .cms_setup import cms_setup_cmd
from .discovery_methods import discovery_methods_cmd
from .feedback_workflow import feedback_workflow_cmd
from .format_templates import format_templates_cmd
from .plan_template_workflow import plan_template_workflow_cmd
from .profile_workflow import profile_workflow_cmd
from .project_workflow import project_workflow_cmd
from .source_gathering import source_gathering_cmd
from .source_workflow import source_workflow_cmd
from .template_workflow import template_workflow_cmd


@click.group()
def show():
    """
    Show instructions and available options.

    \b
    Available commands:
    - format-templates: List available format templates
    - source-gathering: Display source gathering strategy
    - project-workflow: Instructions for creating/editing projects
    - source-workflow: Instructions for adding sources
    - template-workflow: Instructions for creating/customizing templates
    - profile-workflow: Instructions for creating/editing writer profile
    - plan-template-workflow: Instructions for modifying plan template
    - feedback-workflow: Instructions for collecting feedback
    - discovery-methods: Methods for discovering existing content
    - cms-setup: CMS integration setup
    - analytics-setup: Analytics integration setup
    """
    pass


# Register all subcommands
show.add_command(format_templates_cmd, name="format-templates")
show.add_command(source_gathering_cmd, name="source-gathering")
show.add_command(project_workflow_cmd, name="project-workflow")
show.add_command(source_workflow_cmd, name="source-workflow")
show.add_command(template_workflow_cmd, name="template-workflow")
show.add_command(profile_workflow_cmd, name="profile-workflow")
show.add_command(plan_template_workflow_cmd, name="plan-template-workflow")
show.add_command(feedback_workflow_cmd, name="feedback-workflow")
show.add_command(discovery_methods_cmd, name="discovery-methods")
show.add_command(cms_setup_cmd, name="cms-setup")
show.add_command(analytics_setup_cmd, name="analytics-setup")

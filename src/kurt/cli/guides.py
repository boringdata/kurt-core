"""Kurt guides - Interactive prompts/guides for agents.

These are distinct from workflows (automated agent tasks in workflows/).
Guides provide step-by-step instructions for agents to follow interactively.
"""

import click

from kurt.cli.show.discovery_methods import discovery_methods_cmd
from kurt.cli.show.feedback_workflow import feedback_workflow_cmd
from kurt.cli.show.format_templates import format_templates_cmd
from kurt.cli.show.plan_template_workflow import plan_template_workflow_cmd
from kurt.cli.show.profile_workflow import profile_workflow_cmd
from kurt.cli.show.project_workflow import project_workflow_cmd
from kurt.cli.show.source_gathering import source_gathering_cmd
from kurt.cli.show.source_workflow import source_workflow_cmd
from kurt.cli.show.template_workflow import template_workflow_cmd


@click.group()
def guides():
    """
    Interactive guides for agents.

    These provide step-by-step instructions for agents to follow.
    Different from workflows (automated tasks in workflows/).

    \b
    Available guides:
    - project: Create/edit writing projects
    - source: Add sources (URLs, CMS, pasted content)
    - template: Create/customize format templates
    - profile: Create/edit writer profile
    - plan-template: Modify the base plan template
    - feedback: Collect user feedback
    - discovery: Methods for discovering existing content
    - formats: List available format templates
    - source-gathering: Display source gathering strategy
    """
    pass


# Register guides with short names
guides.add_command(project_workflow_cmd, name="project")
guides.add_command(source_workflow_cmd, name="source")
guides.add_command(template_workflow_cmd, name="template")
guides.add_command(profile_workflow_cmd, name="profile")
guides.add_command(plan_template_workflow_cmd, name="plan-template")
guides.add_command(feedback_workflow_cmd, name="feedback")
guides.add_command(discovery_methods_cmd, name="discovery")
guides.add_command(format_templates_cmd, name="formats")
guides.add_command(source_gathering_cmd, name="source-gathering")

# Export for lazy loading
guides_group = guides

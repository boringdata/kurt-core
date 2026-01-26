"""Show commands - display instructions and available options.

Note: Some setup/help commands have been moved to their respective modules:
- analytics-setup -> kurt connect analytics help
- cloud-setup -> kurt cloud help
- cms-setup -> kurt connect cms help
"""

import click

from .discovery_methods import discovery_methods_cmd
from .embedding_step import embedding_step_cmd
from .feedback_workflow import feedback_workflow_cmd
from .format_templates import format_templates_cmd
from .llm_step import llm_step_cmd
from .models_py import models_py_cmd
from .plan_template_workflow import plan_template_workflow_cmd
from .profile_workflow import profile_workflow_cmd
from .project_workflow import project_workflow_cmd
from .save_step import save_step_cmd
from .source_gathering import source_gathering_cmd
from .source_workflow import source_workflow_cmd
from .template_workflow import template_workflow_cmd
from .tools_py import tools_py_cmd
from .workflow_create import workflow_create_cmd


@click.group()
def show():
    """
    Show instructions and available options.

    \b
    Workflow Tool Documentation:
    - save-step: SaveStep database persistence documentation
    - llm-step: LLMStep batch processing documentation
    - embedding-step: EmbeddingStep vector embeddings documentation
    - models-py: SQLModel table definitions guide
    - tools-py: Custom workflow functions guide
    - workflow-create: Instructions for creating user workflows with tools

    \b
    Agent Workflow Instructions:
    - format-templates: List available format templates
    - source-gathering: Display source gathering strategy
    - project-workflow: Instructions for creating/editing projects
    - source-workflow: Instructions for adding sources
    - template-workflow: Instructions for creating/customizing templates
    - profile-workflow: Instructions for creating/editing writer profile
    - plan-template-workflow: Instructions for modifying plan template
    - feedback-workflow: Instructions for collecting feedback
    - discovery-methods: Methods for discovering existing content

    \b
    Moved Commands (now in their respective modules):
    - Analytics setup: kurt connect analytics help
    - CMS setup: kurt connect cms help
    - Cloud setup: kurt cloud help
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
show.add_command(workflow_create_cmd, name="workflow-create")

# Workflow tool documentation
show.add_command(save_step_cmd, name="save-step")
show.add_command(llm_step_cmd, name="llm-step")
show.add_command(embedding_step_cmd, name="embedding-step")
show.add_command(models_py_cmd, name="models-py")
show.add_command(tools_py_cmd, name="tools-py")

# Export for lazy loading
show_group = show

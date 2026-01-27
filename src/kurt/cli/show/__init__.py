"""Help commands - documentation and tool references.

Agent guides have moved to: kurt guides
"""

import click

from .embedding_step import embedding_step_cmd
from .llm_step import llm_step_cmd
from .models_py import models_py_cmd
from .save_step import save_step_cmd
from .tools_py import tools_py_cmd
from .workflow_create import workflow_create_cmd


@click.group()
def show():
    """
    Documentation and tool references.

    \b
    Tool Documentation:
    - save-step: SaveStep database persistence documentation
    - llm-step: LLMStep batch processing documentation
    - embedding-step: EmbeddingStep vector embeddings documentation
    - models-py: SQLModel table definitions guide
    - tools-py: Custom workflow functions guide
    - workflow-create: Instructions for creating agent workflows

    \b
    Agent Guides (moved to 'kurt guides'):
    - kurt guides project: Create/edit writing projects
    - kurt guides source: Add sources
    - kurt guides template: Create/customize templates
    - kurt guides profile: Create/edit writer profile

    \b
    Integration Help:
    - kurt connect analytics help
    - kurt connect cms help
    - kurt cloud help
    """
    pass


# Tool documentation
show.add_command(workflow_create_cmd, name="workflow-create")

# Workflow tool documentation
show.add_command(save_step_cmd, name="save-step")
show.add_command(llm_step_cmd, name="llm-step")
show.add_command(embedding_step_cmd, name="embedding-step")
show.add_command(models_py_cmd, name="models-py")
show.add_command(tools_py_cmd, name="tools-py")

# Export for lazy loading
show_group = show

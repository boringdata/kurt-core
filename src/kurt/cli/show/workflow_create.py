"""Show workflow creation instructions."""

import click

from kurt.admin.telemetry.decorators import track_command


@click.command()
@track_command
def workflow_create_cmd():
    """Show instructions for creating user workflows with tools."""
    content = """
═══════════════════════════════════════════════════════════════════
WORKFLOW CREATION GUIDE (TOML Format)
═══════════════════════════════════════════════════════════════════

WHEN TO USE THIS WORKFLOW
─────────────────────────────────────────────────────────────────
When a user wants to create a custom workflow with:
- Agent automation (workflow.toml)
- Custom DBOS tools (tools.py)
- Database persistence (models.py)

═══════════════════════════════════════════════════════════════════
WORKFLOW TYPES
═══════════════════════════════════════════════════════════════════

1. AGENT-DRIVEN (simple)
   - Single .toml file with [agent] section
   - Claude orchestrates everything
   - Good for: exploration, analysis, simple tasks

2. DBOS-DRIVEN (complex)
   - Directory with workflow.toml + tools.py + models.py
   - [steps.xxx] sections define DAG
   - Good for: pipelines, data processing, multi-step tasks

═══════════════════════════════════════════════════════════════════
STRUCTURE: AGENT-DRIVEN (Simple)
═══════════════════════════════════════════════════════════════════

workflows/my-workflow.toml   # Single flat file

─────────────────────────────────────────────────────────────────
EXAMPLE: Agent-Driven Workflow
─────────────────────────────────────────────────────────────────

```toml
[workflow]
name = "competitor-tracker"
title = "Competitor Analysis"
description = "Track and analyze competitors"

[agent]
model = "claude-sonnet-4-20250514"
max_turns = 20
allowed_tools = ["Bash", "Read", "Write", "Glob", "Grep"]
permission_mode = "bypassPermissions"
prompt = \"\"\"
Analyze competitors for {{company}}.

## Task

1. Research competitor websites
2. Extract key information
3. Save report to reports/competitors-{{date}}.md

## Output

Provide a summary of findings.
\"\"\"

[guardrails]
max_tokens = 150000
max_tool_calls = 100
max_time = 600

[inputs]
company = "Acme Corp"

tags = ["analysis", "automation"]
```

═══════════════════════════════════════════════════════════════════
STRUCTURE: DBOS-DRIVEN (Complex)
═══════════════════════════════════════════════════════════════════

workflows/data_pipeline/
├── workflow.toml    # Config + step definitions
├── tools.py         # @DBOS.step() functions
└── models.py        # SQLModel tables

─────────────────────────────────────────────────────────────────
EXAMPLE: DBOS-Driven Workflow (workflow.toml)
─────────────────────────────────────────────────────────────────

```toml
[workflow]
name = "data-pipeline"
title = "Data Processing Pipeline"
description = "Fetch, enrich with LLM, save to database"

[inputs]
source_url = "https://api.example.com/items"
max_items = 100

[steps.fetch]
type = "function"
function = "fetch_items"

[steps.enrich]
type = "llm"
depends_on = ["fetch"]
prompt_template = \"\"\"
Analyze this item:
Title: {title}
Content: {content}

Return JSON with: summary, keywords, sentiment
\"\"\"
output_schema = "EnrichmentOutput"

[steps.analyze]
type = "agent"
depends_on = ["enrich"]
model = "claude-sonnet-4-20250514"
max_turns = 10
prompt = \"\"\"
Review the enriched items from {outputs.enrich}.

Save analysis using:
```bash
kurt agent tool save-to-db --table=analysis --data='{"key": "value"}'
```
\"\"\"

[steps.report]
type = "function"
depends_on = ["analyze"]
function = "generate_report"

[guardrails]
max_tokens = 200000
max_tool_calls = 150
max_time = 900

tags = ["pipeline", "dbos-driven"]
```

─────────────────────────────────────────────────────────────────
STEP TYPES
─────────────────────────────────────────────────────────────────

type = "function"    # Call @DBOS.step() from tools.py
  function = "function_name"

type = "agent"       # Spawn Claude Code subprocess
  model = "claude-sonnet-4-20250514"
  max_turns = 10
  prompt = "..."

type = "llm"         # Batch LLM processing via LLMStep
  prompt_template = "..."
  output_schema = "ModelName"  # From models.py

─────────────────────────────────────────────────────────────────
EXAMPLE: tools.py
─────────────────────────────────────────────────────────────────

```python
\"\"\"DBOS step functions for data_pipeline workflow.\"\"\"

from dbos import DBOS


@DBOS.step()
def fetch_items(context: dict) -> dict:
    \"\"\"Fetch items from source.\"\"\"
    inputs = context.get("inputs", {})
    url = inputs.get("source_url")

    import httpx
    response = httpx.get(url)
    items = response.json()

    return {"items": items, "count": len(items)}


@DBOS.step()
def generate_report(context: dict) -> dict:
    \"\"\"Generate final report.\"\"\"
    outputs = context.get("outputs", {})
    return {"status": "completed", "summary": "..."}
```

─────────────────────────────────────────────────────────────────
EXAMPLE: models.py
─────────────────────────────────────────────────────────────────

```python
\"\"\"SQLModel tables for data_pipeline workflow.\"\"\"

from typing import Optional
from pydantic import BaseModel
from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


# Output schema for LLM step
class EnrichmentOutput(BaseModel):
    summary: str
    keywords: list[str]
    sentiment: str


# Database table
class AnalysisResult(SQLModel, table=True):
    __tablename__ = "analysis"

    id: Optional[int] = Field(default=None, primary_key=True)
    workflow_id: str = Field(index=True)
    item_id: str
    summary: str
    keywords: list[str] = Field(default_factory=list, sa_column=Column(JSON))
```

═══════════════════════════════════════════════════════════════════
TEMPLATE VARIABLES
═══════════════════════════════════════════════════════════════════

In prompts, use double braces:

{{input_name}}     - From [inputs] section
{{date}}           - Current date (YYYY-MM-DD)
{{datetime}}       - ISO timestamp
{{project_root}}   - Project directory

In step prompts, reference previous outputs:

{outputs.step_name}        - Full output from step
{outputs.fetch.items}      - Nested value

═══════════════════════════════════════════════════════════════════
AGENT TOOLS (for type="agent" steps)
═══════════════════════════════════════════════════════════════════

Agents can use these CLI commands to persist data:

# Save to database
kurt agent tool save-to-db --table=TABLE --data='{"key": "value"}'

# Batch LLM processing
kurt agent tool llm --prompt="Analyze: {text}" --data='[{"text": "..."}]'

# Generate embeddings
kurt agent tool embedding --texts='["text1", "text2"]' --output=embeddings.json

═══════════════════════════════════════════════════════════════════
STEPS TO CREATE A WORKFLOW
═══════════════════════════════════════════════════════════════════

1. ASK user what the workflow should do
2. DECIDE: agent-driven (simple) or DBOS-driven (complex)?

For AGENT-DRIVEN:
3. CREATE workflows/{name}.toml with [workflow] + [agent] sections
4. VALIDATE: kurt agents validate workflows/{name}.toml
5. TEST: kurt agents run {name} --foreground

For DBOS-DRIVEN:
3. CREATE workflows/{name}/ directory
4. WRITE workflow.toml with [steps.xxx] sections
5. WRITE tools.py with @DBOS.step() functions
6. WRITE models.py with SQLModel tables (if needed)
7. VALIDATE: kurt agents validate workflows/{name}/
8. TEST: kurt agents run {name} --foreground

═══════════════════════════════════════════════════════════════════
CLI COMMANDS
═══════════════════════════════════════════════════════════════════

# List workflows
kurt agents list

# Show details
kurt agents show {name}

# Validate
kurt agents validate
kurt agents validate workflows/my-workflow.toml

# Run
kurt agents run {name}
kurt agents run {name} --foreground
kurt agents run {name} --input company="MyCompany"

# Create from template
kurt agents create --name my-workflow
kurt agents create --name my-pipeline --with-steps --with-tools

# Initialize with examples
kurt agents init

═══════════════════════════════════════════════════════════════════
DETAILED DOCUMENTATION
═══════════════════════════════════════════════════════════════════

For detailed documentation on each component:

# Agent tools documentation
kurt show save-step      # Database persistence (SaveStep)
kurt show llm-step       # Batch LLM processing (LLMStep)
kurt show embedding-step # Vector embeddings (EmbeddingStep)

# File format guides
kurt show models-py      # SQLModel table definitions
kurt show tools-py       # DBOS step functions

═══════════════════════════════════════════════════════════════════
"""
    click.echo(content.strip())

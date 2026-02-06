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
- Built-in tools (map, fetch, llm, embed, sql, write-db)
- Custom Python functions
- Database persistence (Dolt tables)

═══════════════════════════════════════════════════════════════════
WORKFLOW TYPES
═══════════════════════════════════════════════════════════════════

1. AGENT-DRIVEN (simple)
   - Single .toml file with [agent] section
   - Claude orchestrates everything
   - Good for: exploration, analysis, simple tasks

2. TOOL-DRIVEN (pipelines)
   - Single .toml file with [steps.xxx] sections
   - Uses built-in tools: map, fetch, llm, embed, sql, write-db
   - Good for: data pipelines, batch processing, ETL

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
STRUCTURE: TOOL-DRIVEN (Pipeline)
═══════════════════════════════════════════════════════════════════

workflows/data_pipeline.toml   # Single file with step definitions

─────────────────────────────────────────────────────────────────
EXAMPLE: Tool-Driven Workflow (workflow.toml)
─────────────────────────────────────────────────────────────────

```toml
[workflow]
name = "data-pipeline"
description = "Map, fetch, and analyze website content"

[inputs]
source_url = { type = "string", default = "https://example.com" }
limit = { type = "int", default = 10 }

# Step 1: Discover URLs from source
[steps.discover]
type = "map"
[steps.discover.config]
source = "url"
url = "{{source_url}}"
depth = 1
max_pages = 50

# Step 2: Fetch content (receives input_data from discover)
[steps.fetch_docs]
type = "fetch"
depends_on = ["discover"]
[steps.fetch_docs.config]
engine = "trafilatura"
limit = "{{limit:int}}"

# Step 3: Query results with SQL
[steps.query]
type = "sql"
depends_on = ["fetch_docs"]
[steps.query.config]
query = "SELECT document_id, url, fetch_status FROM documents LIMIT 10"

# Step 4: Enrich with LLM
[steps.enrich]
type = "llm"
depends_on = ["fetch_docs"]
[steps.enrich.config]
prompt = "Summarize this content: {{content}}"
model = "gpt-4o-mini"

# Step 5: Generate embeddings
[steps.embed]
type = "embed"
depends_on = ["fetch_docs"]
[steps.embed.config]
model = "text-embedding-3-small"
batch_size = 100
```

─────────────────────────────────────────────────────────────────
BUILT-IN TOOL TYPES
─────────────────────────────────────────────────────────────────

type = "map"        # Discover URLs from websites, folders, or CMS
  config.source     # "url" | "folder" | "cms"
  config.url        # Source URL to crawl
  config.depth      # Crawl depth (default: 1)
  config.max_pages  # Max pages to discover

type = "fetch"      # Fetch and extract content
  config.engine     # "trafilatura" | "httpx" | "firecrawl"
  config.limit      # Max items to process

type = "llm"        # Batch LLM processing
  config.prompt     # Prompt template with {{field}} variables
  config.model      # Model name (gpt-4o-mini, claude-3-haiku, etc.)

type = "embed"      # Generate embeddings
  config.model      # Embedding model name
  config.batch_size # Batch size (default: 100)

type = "sql"        # Query Dolt database
  config.query      # SQL query string

type = "write-db"   # Write data to Dolt database
  config.table      # Target table name
  config.mode       # Write mode: insert, upsert, replace

type = "function"   # Call custom Python function
  function = "module.function_name"

type = "agent"      # Spawn Claude Code subprocess
  model = "claude-sonnet-4-20250514"
  max_turns = 10
  prompt = "..."

─────────────────────────────────────────────────────────────────
CUSTOM PYTHON FUNCTIONS
─────────────────────────────────────────────────────────────────

Create a tools.py file in your workflow directory:

workflows/my_pipeline/
├── workflow.toml
└── tools.py

```python
\"\"\"Custom functions for my_pipeline workflow.\"\"\"

def process_items(context: dict) -> dict:
    \"\"\"Process items from previous step.\"\"\"
    input_data = context.get("input_data", [])
    inputs = context.get("inputs", {})

    results = []
    for item in input_data:
        # Transform each item
        results.append({
            "id": item.get("document_id"),
            "processed": True,
        })

    return {"items": results, "count": len(results)}


def generate_report(context: dict) -> dict:
    \"\"\"Generate final report.\"\"\"
    outputs = context.get("outputs", {})
    return {"status": "completed", "summary": "..."}
```

Reference in workflow.toml:

```toml
[steps.process]
type = "function"
function = "process_items"  # Function name from tools.py
depends_on = ["fetch"]
```

═══════════════════════════════════════════════════════════════════
DATA FLOW BETWEEN STEPS
═══════════════════════════════════════════════════════════════════

Steps pass data via:
- input_data: List of items from previous step(s)
- outputs: Dict of all previous step outputs

Example: map → fetch → llm
1. map outputs: [{"url": "...", "document_id": "..."}, ...]
2. fetch receives input_data from map
3. llm receives input_data from fetch

═══════════════════════════════════════════════════════════════════
TEMPLATE VARIABLES
═══════════════════════════════════════════════════════════════════

In prompts, use double braces:

{{input_name}}     - From [inputs] section
{{date}}           - Current date (YYYY-MM-DD)
{{datetime}}       - ISO timestamp
{{project_root}}   - Project directory

Type hints for inputs:
{{limit:int}}      - Convert to integer
{{enabled:bool}}   - Convert to boolean

In step prompts, reference previous outputs:

{outputs.step_name}        - Full output from step
{outputs.fetch.items}      - Nested value

═══════════════════════════════════════════════════════════════════
STEPS TO CREATE A WORKFLOW
═══════════════════════════════════════════════════════════════════

1. ASK user what the workflow should do
2. DECIDE: agent-driven (simple) or tool-driven (pipeline)?

For AGENT-DRIVEN:
3. CREATE workflows/{name}.toml with [workflow] + [agent] sections
4. VALIDATE: kurt agents validate workflows/{name}.toml
5. TEST: kurt agents run {name} --foreground

For TOOL-DRIVEN:
3. CREATE workflows/{name}.toml with [steps.xxx] sections
4. ADD custom tools.py if needed (for type="function")
5. TEST: kurt run workflows/{name}.toml --dry-run
6. RUN: kurt run workflows/{name}.toml

═══════════════════════════════════════════════════════════════════
CLI COMMANDS
═══════════════════════════════════════════════════════════════════

# Run workflow (tool-driven)
kurt run workflows/my-pipeline.toml
kurt run workflows/my-pipeline.toml --dry-run
kurt run workflows/my-pipeline.toml -i source_url=https://example.com

# Test workflow
kurt test workflows/my-pipeline.toml

# Agent workflows
kurt agents list
kurt agents run {name}
kurt agents run {name} --foreground
kurt agents validate workflows/{name}.toml

# Direct tool commands (for testing)
kurt map https://example.com --depth 1
kurt fetch --limit 10
kurt sql "SELECT * FROM documents LIMIT 5"
kurt llm --prompt "Summarize: {{content}}"
kurt embed --model text-embedding-3-small

═══════════════════════════════════════════════════════════════════
DETAILED DOCUMENTATION
═══════════════════════════════════════════════════════════════════

For detailed documentation on each component:

# Tool documentation
kurt tool map --help
kurt tool fetch --help
kurt tool llm --help
kurt tool embed --help
kurt tool sql --help

# Show command help
kurt show models-py      # SQLModel table definitions

═══════════════════════════════════════════════════════════════════
"""
    click.echo(content.strip())

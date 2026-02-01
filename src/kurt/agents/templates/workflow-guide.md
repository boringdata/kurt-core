# Kurt Workflow Guide

This guide explains how to build custom workflows in Kurt. There are two formats:

1. **TOML Format** (recommended) - Step-driven DAG workflows
2. **Markdown Format** - Agent-driven workflows with YAML frontmatter

## Quick Start

### TOML Workflow (Step-Driven)

Create `workflows/my-workflow.toml`:

```toml
[workflow]
name = "my-workflow"
description = "Process and analyze data"

[inputs.url]
type = "string"
required = true

[inputs.max_items]
type = "int"
default = 100

[steps.fetch]
type = "function"
function = "fetch_data"

[steps.analyze]
type = "llm"
depends_on = ["fetch"]
config.prompt_template = "Analyze this data: {{outputs.fetch.content}}"
config.output_schema = "AnalysisResult"

[steps.save]
type = "function"
depends_on = ["analyze"]
function = "save_results"
```

### Markdown Workflow (Agent-Driven)

Create `workflows/my-workflow.md`:

```markdown
---
name: my-workflow
title: My Agent Workflow
agent:
  model: claude-sonnet-4-20250514
  max_turns: 15
guardrails:
  max_tokens: 100000
inputs:
  task: "default task"
---

# Instructions

Your agent instructions go here...
```

---

## TOML Workflow Format (Detailed)

### Directory Structure

```
workflows/
  my-workflow/
    workflow.toml    # Workflow definition
    models.py        # Pydantic models for LLM output schemas
    tools.py         # Python functions for type="function" steps
```

Or single-file:
```
workflows/
  my-workflow.toml   # Standalone workflow
```

### [workflow] Section (Required)

```toml
[workflow]
name = "my-workflow"           # Unique identifier (kebab-case)
description = "What it does"   # Optional description
```

### [inputs] Section (Optional)

Define workflow input parameters:

```toml
[inputs.url]
type = "string"      # string | int | float | bool
required = true      # default: false

[inputs.limit]
type = "int"
default = 50         # default value if not provided

[inputs.verbose]
type = "bool"
default = false
```

### [steps] Section (Required)

Each step has a type and optional dependencies:

```toml
[steps.step_name]
type = "function"              # Step type (see below)
depends_on = ["other_step"]    # Run after these steps
continue_on_error = false      # Continue workflow if step fails
```

### Step Types

| Type | Description | Config Keys |
|------|-------------|-------------|
| `function` | Run Python function from `tools.py` | `function` |
| `llm` | LLM extraction with structured output | `prompt_template`, `output_schema` |
| `embed` | Generate embeddings | `input_column`, `model` |
| `map` | Map URLs (sitemap/crawl) | `url`, `depth`, `patterns` |
| `fetch` | Fetch content from URLs | `engine`, `pending` |
| `sql` | Execute SQL query | `query` |
| `agent` | Run Claude agent | `prompt`, `model`, `max_turns` |
| `write` | Write to file | `path`, `content` |

#### function Step

```toml
[steps.fetch_data]
type = "function"
function = "fetch_data"  # Function name in tools.py
```

In `tools.py`:
```python
def fetch_data(context: dict) -> dict:
    inputs = context.get("inputs", {})
    url = inputs.get("url")
    # ... fetch logic ...
    return {"content": data, "count": len(data)}
```

#### llm Step

```toml
[steps.extract]
type = "llm"
depends_on = ["fetch"]
config.prompt_template = """
Extract entities from:
{{outputs.fetch.content}}
"""
config.output_schema = "ExtractedEntities"  # Class in models.py
```

In `models.py`:
```python
from pydantic import BaseModel

class ExtractedEntities(BaseModel):
    entities: list[str]
    sentiment: str
```

#### agent Step

```toml
[steps.analyze]
type = "agent"
depends_on = ["fetch"]
config.model = "claude-sonnet-4-20250514"
config.max_turns = 10
config.prompt = """
Analyze the following data and provide insights:
{{outputs.fetch.content}}
"""
```

### Template Variables

Use `{{variable}}` syntax in prompts:

- `{{inputs.name}}` - Input parameter value
- `{{outputs.step_name.key}}` - Output from previous step
- `{{date}}` - Current date (YYYY-MM-DD)
- `{{datetime}}` - ISO timestamp

### Complete Example

```toml
[workflow]
name = "competitor-analysis"
description = "Analyze competitor content"

[inputs.competitor_url]
type = "string"
required = true

[inputs.depth]
type = "int"
default = 2

# Step 1: Map site structure
[steps.map_site]
type = "map"
config.url = "{{inputs.competitor_url}}"
config.depth = "{{inputs.depth}}"

# Step 2: Fetch content
[steps.fetch_content]
type = "fetch"
depends_on = ["map_site"]
config.engine = "trafilatura"

# Step 3: Analyze with LLM
[steps.analyze]
type = "llm"
depends_on = ["fetch_content"]
config.prompt_template = """
Analyze this competitor content:
{{outputs.fetch_content.content}}

Extract: topics, tone, target audience
"""
config.output_schema = "CompetitorAnalysis"

# Step 4: Save results
[steps.save]
type = "function"
depends_on = ["analyze"]
function = "save_analysis"
```

---

## Markdown Workflow Format (Agent-Driven)

### Frontmatter Fields

```yaml
---
name: my-workflow           # Required: unique ID
title: My Workflow          # Required: display name
description: |              # Optional: description
  What this workflow does.

agent:
  model: claude-sonnet-4-20250514  # Model to use
  max_turns: 15                     # Max conversation turns
  allowed_tools:                    # Allowed Claude tools
    - Bash
    - Read
    - Write
    - Glob
    - Grep
  permission_mode: bypassPermissions  # auto | bypassPermissions

guardrails:
  max_tokens: 100000       # Max tokens per run
  max_tool_calls: 50       # Max tool invocations
  max_time: 300            # Max seconds

schedule:                  # Optional: cron scheduling
  cron: "0 9 * * 1-5"     # Weekdays at 9am
  timezone: "UTC"
  enabled: true

inputs:                    # Runtime parameters
  task: "default value"
  target_url: ""

tags: [automation, daily]  # For filtering
---
```

### Body (Agent Instructions)

Everything after the frontmatter is the agent prompt:

```markdown
---
name: daily-report
title: Daily Report Generator
agent:
  model: claude-sonnet-4-20250514
  max_turns: 20
inputs:
  report_type: "summary"
---

# Daily Report Generator

Generate a {{report_type}} report for today ({{date}}).

## Steps

1. Read the latest data from `data/metrics.json`
2. Analyze trends compared to yesterday
3. Generate report in `reports/{{date}}-{{report_type}}.md`

## Output Format

The report should include:
- Key metrics summary
- Notable changes
- Recommendations
```

---

## CLI Commands

```bash
# List workflows
kurt agents list
kurt agents list --tag automation

# Validate workflow files
kurt agents validate
kurt agents validate workflows/my-workflow.toml

# Run workflow
kurt agents run my-workflow
kurt agents run my-workflow --foreground
kurt agents run my-workflow --input url="https://example.com"

# View history
kurt agents history my-workflow --limit 10

# Initialize example workflow
kurt agents init
```

---

## Best Practices

1. **Use TOML for data pipelines** - Step-driven DAG is better for deterministic workflows
2. **Use Markdown for exploratory tasks** - Agent-driven is better for open-ended work
3. **Keep steps small** - Each step should do one thing well
4. **Use `depends_on`** - Make dependencies explicit for parallel execution
5. **Set guardrails** - Always configure max_tokens and max_time
6. **Test locally first** - Use `--dry-run` when available

---

## Related Templates

- [tools-py.md](workflow-tools/tools-py.md) - Writing step functions
- [models-py.md](workflow-tools/models-py.md) - Pydantic output schemas
- [llm-step.md](workflow-tools/llm-step.md) - LLM step configuration
- [save-step.md](workflow-tools/save-step.md) - Database persistence

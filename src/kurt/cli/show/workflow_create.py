"""Show workflow creation instructions."""

import click

from kurt.admin.telemetry.decorators import track_command


@click.command()
@track_command
def workflow_create_cmd():
    """Show instructions for creating user workflows with tools."""
    content = """
═══════════════════════════════════════════════════════════════════
WORKFLOW CREATION GUIDE
═══════════════════════════════════════════════════════════════════

WHEN TO USE THIS WORKFLOW
─────────────────────────────────────────────────────────────────
When a user wants to create a custom workflow with:
- Agent automation (workflow.md)
- Custom DBOS tools (tools.py)
- Database persistence (schema.yaml)

═══════════════════════════════════════════════════════════════════
WORKFLOW STRUCTURE
═══════════════════════════════════════════════════════════════════

All workflow files go in: workflows/{workflow_name}/

workflows/competitor_tracker/
├── workflow.md      # Required: agent prompt + config
├── tools.py         # Optional: custom DBOS tools
└── schema.yaml      # Optional: database tables

─────────────────────────────────────────────────────────────────
NAMING CONVENTIONS
─────────────────────────────────────────────────────────────────

• Folder name: snake_case (e.g., competitor_tracker)
• workflow.md name field: kebab-case (e.g., competitor-tracker)
• Tools: descriptive function names (e.g., analyze_competitor)
• Tables: prefixed by workflow (e.g., competitors, competitor_products)

═══════════════════════════════════════════════════════════════════
FILE 1: workflow.md (Required)
═══════════════════════════════════════════════════════════════════

```markdown
---
name: competitor-tracker
title: Competitor Analysis Tracker
description: |
  Track and analyze competitors automatically.

agent:
  model: claude-sonnet-4-20250514
  max_turns: 20
  allowed_tools:
    - Bash
    - Read
    - Write
    - Edit
    - Glob
    - Grep

guardrails:
  max_tokens: 150000
  max_tool_calls: 100
  max_time: 600

inputs:
  company: "Acme Corp"
  urls: "https://competitor1.com"

tags: [analysis, automation]
---

# Competitor Tracker

Analyze competitors for {{company}}.

## Available Tools

Custom tools from tools.py:
- `analyze_competitor(url)` - Fetch, analyze, and store competitor data

## Task

1. For each URL in {{urls}}, call the analyze tool
2. Generate a comparison report
3. Save to reports/competitors-{{date}}.md

## Output

Summary of findings.
```

─────────────────────────────────────────────────────────────────
TEMPLATE VARIABLES
─────────────────────────────────────────────────────────────────

• {{input_name}} - from inputs section
• {{date}} - current date (YYYY-MM-DD)
• {{datetime}} - ISO timestamp
• {{time}} - HH:MM
• {{weekday}} - day name
• {{project_root}} - project directory

═══════════════════════════════════════════════════════════════════
FILE 2: tools.py (Optional)
═══════════════════════════════════════════════════════════════════

Tools are DBOS workflows that use building blocks.

```python
\"\"\"Custom tools for competitor_tracker workflow.\"\"\"

from __future__ import annotations
from typing import Any
import pandas as pd
from dbos import DBOS
from pydantic import BaseModel
from kurt.core import LLMStep, EmbeddingStep, get_session


# Output schema for LLM
class AnalysisOutput(BaseModel):
    company_name: str
    strengths: list[str]
    weaknesses: list[str]
    summary: str


# Tool = DBOS workflow
@DBOS.workflow()
def analyze_competitor(url: str) -> dict[str, Any]:
    \"\"\"Fetch, analyze, embed, and store competitor data.\"\"\"

    # Step 1: Fetch content
    content = fetch_url(url)

    # Step 2: LLM analysis
    analysis = run_analysis(content)

    # Step 3: Persist (transaction from workflow)
    save_analysis(url, analysis)

    return analysis


# Pure computation step
@DBOS.step()
def fetch_url(url: str) -> str:
    \"\"\"Fetch URL content.\"\"\"
    import httpx
    response = httpx.get(url, timeout=30)
    return response.text


# Step using LLMStep building block
@DBOS.step()
def run_analysis(content: str) -> dict:
    \"\"\"Analyze content with LLM.\"\"\"
    df = pd.DataFrame([{"content": content}])

    step = LLMStep(
        name="analyze",
        input_columns=["content"],
        prompt_template="Analyze this competitor:\\n{content}",
        output_schema=AnalysisOutput,
        llm_fn=_call_llm,
    )

    result_df = step.run(df)
    return result_df.to_dict("records")[0]


# Database transaction - ONLY called from workflow
@DBOS.transaction()
def save_analysis(url: str, analysis: dict) -> None:
    \"\"\"Persist to workflow schema.\"\"\"
    with get_session() as db:
        db.execute(
            \"\"\"
            INSERT INTO competitors (url, company_name, strengths, weaknesses, summary)
            VALUES (:url, :company_name, :strengths, :weaknesses, :summary)
            \"\"\",
            {"url": url, **analysis}
        )


def _call_llm(prompt: str) -> tuple[AnalysisOutput, dict]:
    \"\"\"LLM call - returns (result, metrics).\"\"\"
    import litellm

    response = litellm.completion(
        model="claude-sonnet-4-20250514",
        messages=[{"role": "user", "content": prompt}],
    )

    # Parse response into schema
    result = AnalysisOutput.model_validate_json(
        response.choices[0].message.content
    )

    metrics = {
        "tokens_in": response.usage.prompt_tokens,
        "tokens_out": response.usage.completion_tokens,
    }

    return result, metrics
```

─────────────────────────────────────────────────────────────────
DBOS PATTERNS
─────────────────────────────────────────────────────────────────

• @DBOS.workflow() - Orchestrates steps and transactions
• @DBOS.step() - Pure computation, can call other steps
• @DBOS.transaction() - DB operations, ONLY from workflows

⚠️  CRITICAL: Transactions must be called from workflows, not steps!

─────────────────────────────────────────────────────────────────
BUILDING BLOCKS
─────────────────────────────────────────────────────────────────

LLMStep - Batch LLM processing:
  step = LLMStep(
      name="step_name",
      input_columns=["col1"],
      prompt_template="Process {col1}",
      output_schema=OutputModel,
      llm_fn=my_llm_fn,
      concurrency=3,
  )
  result_df = step.run(df)

EmbeddingStep - Batch embeddings:
  step = EmbeddingStep(
      name="embed",
      input_column="text",
      output_column="embedding",
  )
  result_df = step.run(df)

═══════════════════════════════════════════════════════════════════
FILE 3: schema.yaml (Optional)
═══════════════════════════════════════════════════════════════════

Tables are created in wf_{workflow_name} schema automatically.

```yaml
# Database schema for competitor_tracker
# Tables created in: wf_competitor_tracker

tables:
  competitors:
    columns:
      url: str!              # ! = NOT NULL
      company_name: str!
      strengths: json        # list stored as JSON
      weaknesses: json
      summary: text
      embedding: bytes       # for vectors
    indexes:
      - url
      - company_name

  competitor_products:
    columns:
      competitor_id: int!
      name: str!
      price: float
    foreign_keys:
      competitor_id: competitors.id
    indexes:
      - competitor_id

# Auto-added to all tables:
# - id (primary key)
# - created_at (timestamp)
# - updated_at (timestamp)
# - user_id (multi-tenancy)
# - workspace_id (multi-tenancy)
```

─────────────────────────────────────────────────────────────────
COLUMN TYPES
─────────────────────────────────────────────────────────────────

str       VARCHAR           Short text
str!      VARCHAR NOT NULL  Required short text
text      TEXT              Long text
int       INTEGER           Integer
float     REAL/FLOAT        Decimal
bool      BOOLEAN           True/False
json      JSON/JSONB        JSON data
bytes     BYTEA/BLOB        Binary (embeddings)
datetime  TIMESTAMP         Date and time
date      DATE              Date only

═══════════════════════════════════════════════════════════════════
STEPS TO CREATE A WORKFLOW
═══════════════════════════════════════════════════════════════════

1. ASK user what the workflow should do
2. CREATE workflows/{name}/ directory
3. WRITE workflow.md with agent config + prompt
4. If persistence needed:
   - WRITE schema.yaml with table definitions
   - WRITE tools.py with DBOS tools
5. VALIDATE: kurt agents validate workflows/{name}/workflow.md
6. TEST: kurt agents run {name} --foreground

═══════════════════════════════════════════════════════════════════
RUNNING WORKFLOWS
═══════════════════════════════════════════════════════════════════

# List workflows
kurt agents list

# Run in background
kurt agents run competitor-tracker

# Run with custom inputs
kurt agents run competitor-tracker --input company="MyCompany"

# Run in foreground (blocking)
kurt agents run competitor-tracker --foreground

# Show workflow details
kurt agents show competitor-tracker

═══════════════════════════════════════════════════════════════════
"""
    click.echo(content.strip())

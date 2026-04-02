"""Show tools.py documentation."""

import click

from kurt.admin.telemetry.decorators import track_command


@click.command()
@track_command
def tools_py_cmd():
    """Show tools.py (custom workflow functions) documentation."""
    content = """
═══════════════════════════════════════════════════════════════════
CUSTOM WORKFLOW FUNCTIONS (tools.py)
═══════════════════════════════════════════════════════════════════

OVERVIEW
─────────────────────────────────────────────────────────────────
Create custom Python functions to use in TOML workflows.
Functions receive workflow context and return results.

═══════════════════════════════════════════════════════════════════
FILE LOCATION
═══════════════════════════════════════════════════════════════════

Place tools.py next to your workflow.toml:

workflows/my_pipeline/
├── workflow.toml
└── tools.py

═══════════════════════════════════════════════════════════════════
FUNCTION SIGNATURE
═══════════════════════════════════════════════════════════════════

```python
def my_function(context: dict) -> dict:
    \"\"\"Description of what this function does.\"\"\"

    # Access workflow inputs
    inputs = context.get("inputs", {})
    source_url = inputs.get("source_url")

    # Access data from previous steps
    input_data = context.get("input_data", [])

    # Access outputs from specific steps
    outputs = context.get("outputs", {})
    fetch_results = outputs.get("fetch", {})

    # Your logic here
    results = []
    for item in input_data:
        results.append({"processed": True, **item})

    # Return results (passed to next step)
    return {"items": results, "count": len(results)}
```

═══════════════════════════════════════════════════════════════════
CONTEXT OBJECT
═══════════════════════════════════════════════════════════════════

The context dict contains:

{
    "inputs": {                    # Workflow [inputs] values
        "source_url": "...",
        "limit": 10
    },
    "input_data": [...],           # Data from depends_on steps
    "outputs": {                   # All previous step outputs
        "step_name": {...}
    },
    "workflow_id": "...",          # Unique run ID
    "step_name": "my_step"         # Current step name
}

═══════════════════════════════════════════════════════════════════
USING IN WORKFLOW.TOML
═══════════════════════════════════════════════════════════════════

```toml
[steps.process]
type = "function"
function = "my_function"     # Function name from tools.py
depends_on = ["fetch"]       # Receives fetch output as input_data

[steps.report]
type = "function"
function = "generate_report"
depends_on = ["process"]
```

═══════════════════════════════════════════════════════════════════
EXAMPLE: COMPLETE TOOLS.PY
═══════════════════════════════════════════════════════════════════

```python
\"\"\"Custom functions for data_pipeline workflow.\"\"\"

import json
from datetime import datetime
from pathlib import Path


def filter_items(context: dict) -> dict:
    \"\"\"Filter items based on criteria.\"\"\"
    input_data = context.get("input_data", [])
    inputs = context.get("inputs", {})
    min_length = inputs.get("min_length", 100)

    filtered = [
        item for item in input_data
        if len(item.get("content", "")) >= min_length
    ]

    return {"items": filtered, "filtered_count": len(filtered)}


def generate_report(context: dict) -> dict:
    \"\"\"Generate markdown report from processed data.\"\"\"
    outputs = context.get("outputs", {})
    workflow_id = context.get("workflow_id", "unknown")

    # Gather stats from all steps
    stats = {
        step: len(data.get("items", data.get("results", [])))
        for step, data in outputs.items()
    }

    # Write report
    report_path = Path(f"reports/report-{datetime.now():%Y%m%d}.md")
    report_path.parent.mkdir(exist_ok=True)
    report_path.write_text(f\"\"\"# Pipeline Report

Workflow ID: {workflow_id}
Generated: {datetime.now().isoformat()}

## Statistics

{json.dumps(stats, indent=2)}
\"\"\")

    return {"report_path": str(report_path), "stats": stats}
```

═══════════════════════════════════════════════════════════════════
ACCESSING DOLT DATABASE
═══════════════════════════════════════════════════════════════════

```python
from kurt.db import get_database_client

def query_documents(context: dict) -> dict:
    \"\"\"Query documents from Dolt.\"\"\"
    db = get_database_client()

    results = db.query(
        "SELECT id, url, fetch_status FROM documents WHERE fetch_status = ?",
        ["success"]
    )

    return {"documents": results, "count": len(results)}
```

═══════════════════════════════════════════════════════════════════
TIPS
═══════════════════════════════════════════════════════════════════

1. Keep functions pure when possible (no side effects)
2. Return serializable data (dicts, lists, strings, numbers)
3. Use input_data for data from previous steps
4. Use outputs for accessing specific step results
5. Handle empty input_data gracefully
6. Log progress for long-running operations

═══════════════════════════════════════════════════════════════════
"""
    click.echo(content.strip())

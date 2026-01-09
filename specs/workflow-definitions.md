# Workflow Definitions Feature Specification

## Overview

Enable users to define workflows as Markdown files with YAML frontmatter. These workflows are executed by a Claude Code agent running inside DBOS workflows, providing durability, monitoring, and real-time event streaming.

## Goals

1. **Simple authoring**: Workflows are plain Markdown files - easy to write, version, and share
2. **Agent execution**: Claude Code SDK executes the workflow instructions programmatically
3. **DBOS integration**: Full durability, retry support, and event streaming via DBOS
4. **Real-time monitoring**: Live progress tracking via events and streams
5. **Scheduled execution**: Optional cron-based scheduling via frontmatter

## File Structure

```
.kurt/
├── workflows/                    # Workflow definitions directory
│   ├── daily-research.md        # Example: daily research workflow
│   ├── weekly-signals.md        # Example: weekly signal monitoring
│   └── content-pipeline.md      # Example: content processing pipeline
```

## Workflow File Format

### Frontmatter Schema

```yaml
---
name: daily-research                    # Required: unique identifier
title: Daily Research Summary           # Required: human-readable title
description: |                          # Optional: detailed description
  Researches trending topics and
  generates a daily summary report.

schedule:                               # Optional: cron scheduling
  cron: "0 9 * * *"                    # Run at 9 AM daily
  timezone: Europe/Zurich              # Optional: defaults to UTC
  enabled: true                        # Optional: defaults to true

agent:                                  # Optional: agent configuration
  model: claude-sonnet-4-20250514      # Optional: model to use
  max_turns: 50                        # Optional: max agent turns
  allowed_tools:                       # Optional: restrict tools
    - Bash
    - Read
    - Write
    - Edit
    - Glob
    - Grep
  permission_mode: bypassPermissions   # Optional: auto, bypassPermissions (default for workflows)

guardrails:                             # Optional: safety limits
  max_tokens: 500000                   # Max total tokens (in + out) per run
  max_tool_calls: 200                  # Max tool invocations per run
  max_time: 3600                       # Max execution time in seconds

inputs:                                 # Optional: parameterized inputs
  - name: topics
    type: string[]
    default: ["AI", "startups"]
    description: Topics to research
  - name: depth
    type: enum
    options: [shallow, medium, deep]
    default: medium

tags: [research, daily, automated]      # Optional: for filtering/organization
---
```

### Body Format

The Markdown body contains the prompt/instructions for the Claude Code agent:

```markdown
---
name: daily-research
title: Daily Research Summary
schedule:
  cron: "0 9 * * *"
inputs:
  - name: topics
    type: string[]
    default: ["AI", "startups"]
---

# Daily Research Workflow

You are running inside the Kurt project. Your task is to perform daily research.

## Instructions

1. **Research Phase**
   - Use `kurt research search` to query Perplexity for each topic in {{topics}}
   - Focus on news from the last 24 hours
   - Depth level: {{depth}}

2. **Signal Monitoring**
   - Run `kurt signals reddit` for relevant subreddits
   - Run `kurt signals hackernews` for top stories
   - Filter for signals matching the research topics

3. **Report Generation**
   - Compile findings into a structured report
   - Save to `reports/daily-{date}.md`
   - Include:
     - Executive summary (3-5 bullet points)
     - Key findings per topic
     - Notable signals with links
     - Recommended actions

4. **Database Storage**
   - Persist important signals to the database
   - Tag with today's date and topics

## Success Criteria

- Report file created with meaningful content
- At least 3 signals persisted per topic
- No errors in workflow execution
```

## Architecture

### Components

The agent workflows module lives under `src/kurt/workflows/agents/`, alongside other workflow types.

```
src/kurt/
├── workflows/
│   ├── fetch/                       # Existing: content fetching
│   ├── map/                         # Existing: URL discovery
│   ├── research/                    # Existing: research queries
│   ├── signals/                     # Existing: signal monitoring
│   │
│   └── agents/                      # NEW: agent-based workflows from markdown
│       ├── __init__.py
│       ├── parser.py                # Parse MD + frontmatter (Pydantic models)
│       ├── executor.py              # DBOS workflow + Claude Code SDK
│       ├── scheduler.py             # DBOS @scheduled registration
│       ├── registry.py              # File-based definition loading
│       └── cli.py                   # CLI commands
```

**Why under `workflows/`?**
- It's still a workflow, just agent-based instead of code-based
- Consistent with existing workflow organization
- Reuses existing infrastructure: DBOS, LLMTracer, tracking hooks

### Data Models

No custom database tables or models needed. Everything is stored by DBOS:

- **Workflow definitions**: `.md` files in `.kurt/workflows/` (source of truth)
- **Workflow runs**: DBOS `dbos_workflow_status` table
- **Events**: DBOS `dbos_workflow_events` table (key-value state)
- **Streams**: DBOS `dbos_workflow_streams` table (append-only logs)

### Event Streams Schema

DBOS streams are used for real-time monitoring. Each workflow publishes to these stream keys:

#### `agent_events` Stream

```python
# Published for every significant agent action
{
    "type": "text" | "tool_use" | "tool_result" | "turn_complete" | "guardrail_triggered" | "error",
    "timestamp": 1704067200.123,
    "data": {
        # For type="text"
        "content": "Agent output text...",

        # For type="tool_use"
        "tool": "Bash",
        "input": {"command": "npm test"},

        # For type="tool_result"
        "tool": "Bash",
        "success": True,
        "output_preview": "All tests passed...",
        "error": None,  # or error message if failed

        # For type="turn_complete"
        "turn": 5,
        "tokens_in": 1200,
        "tokens_out": 450,
        "total_tokens": 15000,

        # For type="guardrail_triggered"
        "reason": "max_tokens (500000) exceeded: 512345",

        # For type="error"
        "message": "Tool execution failed",
        "code": "TOOL_ERROR",
    }
}
```

#### `progress` Stream

```python
# Published for progress tracking (compatible with existing Kurt patterns)
{
    "type": "step",
    "step": "agent_execution",
    "status": "start" | "progress" | "complete" | "error",
    "current": 5,
    "total": 50,
    "timestamp": 1704067200.123,
}
```

### DBOS Events Schema

Key-value events for workflow state (queryable via `get_live_status()`):

| Key | Type | Description |
|-----|------|-------------|
| `status` | string | running, completed, failed, cancelled |
| `started_at` | float | Unix timestamp |
| `completed_at` | float | Unix timestamp |
| `current_step` | string | Current execution phase |
| `agent_turns` | int | Number of agent turns completed |
| `tool_calls` | int | Total tool invocations |
| `tokens_in` | int | Input tokens consumed |
| `tokens_out` | int | Output tokens generated |
| `last_tool` | string | Name of last tool used |
| `last_error` | string | Last error message (if any) |
| `stop_reason` | string | Why execution stopped (completed, max_turns, guardrail) |

**Note:** Cost tracking is handled by the existing `LLMTracer` from `kurt.core.tracing`. Query costs with `tracer.stats(workflow_id=...)` after execution.

### Parser

```python
# src/kurt/workflows/agents/parser.py

import frontmatter
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Optional

class ScheduleConfig(BaseModel):
    cron: str
    timezone: str = "UTC"
    enabled: bool = True

class AgentConfig(BaseModel):
    model: str = "claude-sonnet-4-20250514"
    max_turns: int = 50
    allowed_tools: list[str] = Field(default_factory=lambda: [
        "Bash", "Read", "Write", "Edit", "Glob", "Grep"
    ])
    permission_mode: str = "bypassPermissions"  # auto, bypassPermissions

class GuardrailsConfig(BaseModel):
    max_tokens: int = 500000              # Max total tokens (in + out) per run
    max_tool_calls: int = 200             # Max tool invocations per run
    max_time: int = 3600                  # Max execution time in seconds

class InputParam(BaseModel):
    name: str
    type: str  # string, string[], number, boolean
    default: Optional[Any] = None
    description: Optional[str] = None
    required: bool = False

class ParsedWorkflow(BaseModel):
    """Parsed workflow definition."""
    name: str
    title: str
    description: Optional[str] = None
    schedule: Optional[ScheduleConfig] = None
    agent: AgentConfig = Field(default_factory=AgentConfig)
    guardrails: GuardrailsConfig = Field(default_factory=GuardrailsConfig)
    inputs: list[InputParam] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    body: str  # Markdown instructions

def parse_workflow(path: Path) -> ParsedWorkflow:
    """Parse a workflow markdown file."""
    post = frontmatter.load(path)
    return ParsedWorkflow(
        **post.metadata,
        body=post.content
    )

def validate_workflow(path: Path) -> list[str]:
    """Validate a workflow file and return any errors."""
    errors = []
    try:
        parsed = parse_workflow(path)
        if not parsed.name:
            errors.append("Missing required field: name")
        if not parsed.title:
            errors.append("Missing required field: title")
        if parsed.schedule and parsed.schedule.cron:
            try:
                from croniter import croniter
                croniter(parsed.schedule.cron)
            except Exception as e:
                errors.append(f"Invalid cron expression: {e}")
    except Exception as e:
        errors.append(f"Parse error: {e}")
    return errors
```

### Executor (DBOS + Claude Code SDK)

```python
# src/kurt/workflows/agents/executor.py

import re
import time
from datetime import datetime
from typing import Any, Optional

from dbos import DBOS
from claude_agent_sdk import query, ClaudeAgentOptions, HookMatcher

from kurt.workflows.agents.parser import ParsedWorkflow
from kurt.core.config import get_project_root


def resolve_template(body: str, inputs: dict[str, Any]) -> str:
    """Resolve template variables in workflow body."""
    now = datetime.now()
    builtins = {
        "date": now.strftime("%Y-%m-%d"),
        "datetime": now.isoformat(),
        "time": now.strftime("%H:%M"),
        "weekday": now.strftime("%A"),
        "project_root": str(get_project_root()),
    }

    all_vars = {**builtins, **inputs}

    def replace_var(match):
        var_name = match.group(1)
        value = all_vars.get(var_name, match.group(0))
        if isinstance(value, list):
            return ", ".join(str(v) for v in value)
        return str(value)

    return re.sub(r"\{\{(\w+)\}\}", replace_var, body)


@DBOS.workflow()
async def execute_agent_workflow(
    definition: ParsedWorkflow,
    inputs: dict[str, Any],
    trigger: str = "manual",
) -> dict[str, Any]:
    """
    Execute an agent workflow inside DBOS.

    All state is tracked via DBOS events/streams - no custom tables needed.
    """
    workflow_id = DBOS.workflow_id

    # Store workflow metadata in DBOS events
    DBOS.set_event("workflow_type", "agent")
    DBOS.set_event("definition_name", definition.name)
    DBOS.set_event("trigger", trigger)
    DBOS.set_event("status", "running")
    DBOS.set_event("started_at", time.time())

    DBOS.write_stream("progress", {
        "type": "workflow",
        "status": "start",
        "timestamp": time.time(),
    })

    try:
        # Resolve template variables
        prompt = resolve_template(definition.body, inputs)

        # Add workflow context
        prompt = f"""# Workflow: {definition.title}

{prompt}

---
Workflow ID: {workflow_id}
"""

        # Execute agent
        result = await agent_execution_step(
            prompt=prompt,
            model=definition.agent.model,
            max_turns=definition.agent.max_turns,
            allowed_tools=definition.agent.allowed_tools,
            permission_mode=definition.agent.permission_mode,
            max_tokens=definition.guardrails.max_tokens,
            max_tool_calls=definition.guardrails.max_tool_calls,
            max_time=definition.guardrails.max_time,
        )

        # Final state in DBOS events
        DBOS.set_event("status", "completed")
        DBOS.set_event("completed_at", time.time())
        DBOS.set_event("stop_reason", result["stop_reason"])

        DBOS.write_stream("progress", {
            "type": "workflow",
            "status": "complete",
            "timestamp": time.time(),
        })

        return {"workflow_id": workflow_id, "status": "completed", **result}

    except Exception as e:
        DBOS.set_event("status", "failed")
        DBOS.set_event("completed_at", time.time())
        DBOS.set_event("last_error", str(e))

        DBOS.write_stream("agent_events", {
            "type": "error",
            "timestamp": time.time(),
            "data": {"message": str(e), "code": "WORKFLOW_ERROR"},
        })

        raise


@DBOS.step(name="agent_execution", retries_allowed=False)
async def agent_execution_step(
    prompt: str,
    model: str,
    max_turns: int,
    allowed_tools: list[str],
    permission_mode: str = "bypassPermissions",
    # Guardrails
    max_tokens: int = 500000,
    max_tool_calls: int = 200,
    max_time: int = 3600,
) -> dict[str, Any]:
    """
    Execute Claude Code agent with event streaming and guardrails.

    Uses the Claude Agent SDK's query() function with hooks for event capture.
    """
    import asyncio

    from kurt.core.tracing import LLMTracer

    turn_count = 0
    tool_call_count = 0
    total_tokens_in = 0
    total_tokens_out = 0
    stop_reason = None
    start_time = time.time()

    # Use existing LLMTracer for token/cost tracking
    tracer = LLMTracer()

    # Hook callbacks for DBOS event streaming
    async def on_pre_tool(input_data, tool_use_id, context):
        """Capture tool call start."""
        nonlocal tool_call_count
        tool_call_count += 1

        tool_name = input_data.get("tool_name", "unknown")
        tool_input = input_data.get("tool_input", {})

        DBOS.set_event("last_tool", tool_name)
        DBOS.set_event("tool_calls", tool_call_count)

        DBOS.write_stream("agent_events", {
            "type": "tool_use",
            "timestamp": time.time(),
            "data": {
                "tool": tool_name,
                "input": _truncate_dict(tool_input, max_length=500),
            },
        })

        # Check tool call guardrail
        if tool_call_count >= max_tool_calls:
            DBOS.write_stream("agent_events", {
                "type": "guardrail_triggered",
                "timestamp": time.time(),
                "data": {"reason": f"max_tool_calls ({max_tool_calls}) reached"},
            })
            return {
                "hookSpecificOutput": {
                    "hookEventName": input_data["hook_event_name"],
                    "permissionDecision": "deny",
                    "permissionDecisionReason": f"max_tool_calls ({max_tool_calls}) reached",
                }
            }

        return {}

    async def on_post_tool(input_data, tool_use_id, context):
        """Capture tool call result."""
        tool_name = input_data.get("tool_name", "unknown")
        tool_response = input_data.get("tool_response", "")

        DBOS.write_stream("agent_events", {
            "type": "tool_result",
            "timestamp": time.time(),
            "data": {
                "tool": tool_name,
                "success": True,
                "output_preview": str(tool_response)[:500],
            },
        })
        return {}

    DBOS.write_stream("progress", {
        "type": "step",
        "step": "agent_execution",
        "status": "start",
        "total": max_turns,
        "timestamp": time.time(),
    })

    options = ClaudeAgentOptions(
        cwd=str(get_project_root()),
        allowed_tools=allowed_tools,
        permission_mode=permission_mode,
        max_turns=max_turns,
        hooks={
            "PreToolUse": [HookMatcher(hooks=[on_pre_tool])],
            "PostToolUse": [HookMatcher(hooks=[on_post_tool])],
        },
    )

    try:
        async with asyncio.timeout(max_time):
            async for msg in query(prompt=prompt, options=options):
                # Capture text output
                if hasattr(msg, "text") and msg.text:
                    DBOS.write_stream("agent_events", {
                        "type": "text",
                        "timestamp": time.time(),
                        "data": {"content": msg.text[:2000]},
                    })

                # Track turn completion and token usage
                if hasattr(msg, "stop_reason") and msg.stop_reason:
                    turn_count += 1
                    DBOS.set_event("agent_turns", turn_count)

                    DBOS.write_stream("progress", {
                        "type": "step",
                        "step": "agent_execution",
                        "status": "progress",
                        "current": turn_count,
                        "total": max_turns,
                        "timestamp": time.time(),
                    })

                # Capture usage metrics
                if hasattr(msg, "usage") and msg.usage:
                    tokens_in = msg.usage.get("input_tokens", 0)
                    tokens_out = msg.usage.get("output_tokens", 0)
                    total_tokens_in += tokens_in
                    total_tokens_out += tokens_out

                    DBOS.set_event("tokens_in", total_tokens_in)
                    DBOS.set_event("tokens_out", total_tokens_out)

                    # Record to LLMTracer
                    tracer.record(
                        prompt=f"[agent turn {turn_count}]",
                        response=msg.text[:500] if hasattr(msg, "text") and msg.text else "",
                        model=model,
                        latency_ms=int((time.time() - start_time) * 1000),
                        tokens_in=tokens_in,
                        tokens_out=tokens_out,
                        workflow_id=DBOS.workflow_id,
                        step_name="agent_execution",
                        provider="anthropic",
                    )

                    DBOS.write_stream("agent_events", {
                        "type": "turn_complete",
                        "timestamp": time.time(),
                        "data": {
                            "turn": turn_count,
                            "tokens_in": tokens_in,
                            "tokens_out": tokens_out,
                            "total_tokens": total_tokens_in + total_tokens_out,
                        },
                    })

                    # Check token guardrail
                    total_tokens = total_tokens_in + total_tokens_out
                    if total_tokens >= max_tokens:
                        stop_reason = f"max_tokens ({max_tokens}) exceeded: {total_tokens}"
                        DBOS.write_stream("agent_events", {
                            "type": "guardrail_triggered",
                            "timestamp": time.time(),
                            "data": {"reason": stop_reason},
                        })
                        break

    except asyncio.TimeoutError:
        stop_reason = f"max_time ({max_time}s) exceeded"
        DBOS.write_stream("agent_events", {
            "type": "guardrail_triggered",
            "timestamp": time.time(),
            "data": {"reason": stop_reason},
        })

    DBOS.write_stream("progress", {
        "type": "step",
        "step": "agent_execution",
        "status": "complete",
        "current": turn_count,
        "total": max_turns,
        "timestamp": time.time(),
    })

    return {
        "turns": turn_count,
        "tool_calls": tool_call_count,
        "tokens_in": total_tokens_in,
        "tokens_out": total_tokens_out,
        "duration_seconds": round(time.time() - start_time, 2),
        "stop_reason": stop_reason or "completed",
    }


def _truncate_dict(d: dict, max_length: int = 500) -> dict:
    """Truncate string values in a dict for logging."""
    result = {}
    for k, v in d.items():
        if isinstance(v, str) and len(v) > max_length:
            result[k] = v[:max_length] + "..."
        elif isinstance(v, dict):
            result[k] = _truncate_dict(v, max_length)
        else:
            result[k] = v
    return result


# --- Public API ---

def run_definition(
    definition_name: str,
    inputs: Optional[dict[str, Any]] = None,
    background: bool = True,
    trigger: str = "manual",
) -> dict[str, Any]:
    """
    Run a workflow definition by name.

    Args:
        definition_name: Name of the workflow definition
        inputs: Input parameters (will use defaults if not provided)
        background: Run in background worker (default True)
        trigger: What triggered this run (manual, scheduled, api)

    Returns:
        dict with workflow_id
    """
    from kurt.workflows.agents.registry import get_definition

    # Get definition
    definition = get_definition(definition_name)
    if not definition:
        raise ValueError(f"Workflow definition not found: {definition_name}")

    # Merge inputs with defaults
    resolved_inputs = {}
    for param in definition.inputs:
        if inputs and param.name in inputs:
            resolved_inputs[param.name] = inputs[param.name]
        elif param.default is not None:
            resolved_inputs[param.name] = param.default
        elif param.required:
            raise ValueError(f"Missing required input: {param.name}")

    # Execute via DBOS - all tracking is automatic
    if background:
        workflow_id = DBOS.start_workflow(
            execute_agent_workflow,
            definition,
            resolved_inputs,
            trigger,
        )
        return {"workflow_id": workflow_id, "background": True}
    else:
        result = execute_agent_workflow(definition, resolved_inputs, trigger)
        return {"background": False, **result}
```

### Scheduler

DBOS has native cron scheduling via `@DBOS.scheduled()` decorator. No separate scheduler library needed.

**Key insight**: Instead of loading all workflow definitions and scheduling them dynamically, we generate scheduled workflow functions at startup by scanning `.kurt/workflows/`.

```python
# src/kurt/workflows/agents/scheduler.py

"""
DBOS-native scheduling for agent workflows.

Scheduled workflows use DBOS @DBOS.scheduled decorator which provides:
- Exactly-once execution guarantees
- Automatic deduplication via idempotency keys
- Survives restarts (missed schedules can be recovered)
- No external scheduler needed
"""

import logging
from datetime import datetime
from typing import Any

from dbos import DBOS

from kurt.workflows.agents.registry import list_definitions, get_definition
from kurt.workflows.agents.executor import execute_agent_workflow

logger = logging.getLogger(__name__)


def register_scheduled_workflows():
    """
    Register scheduled workflows with DBOS at startup.

    Scans .kurt/workflows/ for definitions with schedules and
    creates @DBOS.scheduled decorated functions for each.
    """
    for definition in list_definitions():
        if definition.schedule and definition.schedule.enabled:
            _register_scheduled_workflow(definition.name, definition.schedule.cron)


def _register_scheduled_workflow(name: str, cron: str):
    """Register a single scheduled workflow with DBOS."""

    @DBOS.scheduled(cron)
    @DBOS.workflow()
    async def scheduled_agent_workflow(scheduled_time: datetime, actual_time: datetime):
        """Auto-generated scheduled workflow."""
        logger.info(f"Running scheduled workflow: {name} (scheduled: {scheduled_time})")

        definition = get_definition(name)
        if not definition:
            logger.error(f"Scheduled workflow definition not found: {name}")
            return

        # Execute the agent workflow
        result = await execute_agent_workflow(
            definition=definition,
            inputs={},
            trigger="scheduled",
        )

        logger.info(f"Scheduled workflow '{name}' completed: {result.get('status')}")
        return result

    # Register with unique name for DBOS
    scheduled_agent_workflow.__name__ = f"scheduled_{name}"
    scheduled_agent_workflow.__qualname__ = f"scheduled_{name}"

    logger.info(f"Registered scheduled workflow: {name} with cron: {cron}")
```

**Alternative: Dynamic execution without pre-registration**

If you prefer not to pre-register all workflows, you can use a single scheduled "dispatcher" that checks which workflows need to run:

```python
# Alternative approach: single dispatcher

@DBOS.scheduled('* * * * *')  # Check every minute
@DBOS.workflow()
async def workflow_scheduler_dispatcher(scheduled_time: datetime, actual_time: datetime):
    """Check and dispatch scheduled workflows."""
    from croniter import croniter

    for definition in list_definitions():
        if not definition.schedule or not definition.schedule.enabled:
            continue

        # Check if this workflow should run at scheduled_time
        cron = croniter(definition.schedule.cron, scheduled_time)
        prev_run = cron.get_prev(datetime)

        # If prev_run matches scheduled_time (within same minute), run it
        if prev_run.replace(second=0, microsecond=0) == scheduled_time.replace(second=0, microsecond=0):
            # Use DBOS child workflow for exactly-once semantics
            await DBOS.start_workflow(
                execute_agent_workflow,
                definition=definition,
                inputs={},
                trigger="scheduled",
            )
```

### Registry

Simple file-based registry - no database sync needed. Definitions are read directly from `.kurt/workflows/` on demand.

```python
# src/kurt/workflows/agents/registry.py

from pathlib import Path
from typing import Optional

from kurt.workflows.agents.parser import parse_workflow, validate_workflow, ParsedWorkflow
from kurt.core.config import get_project_root


def get_workflows_dir() -> Path:
    """Get the workflows directory."""
    return get_project_root() / ".kurt" / "workflows"


def list_definitions() -> list[ParsedWorkflow]:
    """List all workflow definitions from .kurt/workflows/."""
    workflows_dir = get_workflows_dir()
    if not workflows_dir.exists():
        return []

    definitions = []
    for path in sorted(workflows_dir.glob("*.md")):
        try:
            parsed = parse_workflow(path)
            definitions.append(parsed)
        except Exception:
            continue  # Skip invalid files in listing

    return definitions


def get_definition(name: str) -> Optional[ParsedWorkflow]:
    """Get a workflow definition by name."""
    workflows_dir = get_workflows_dir()
    if not workflows_dir.exists():
        return None

    # Try exact filename match first
    exact_path = workflows_dir / f"{name}.md"
    if exact_path.exists():
        parsed = parse_workflow(exact_path)
        if parsed.name == name:
            return parsed

    # Otherwise scan all files for matching name
    for path in workflows_dir.glob("*.md"):
        try:
            parsed = parse_workflow(path)
            if parsed.name == name:
                return parsed
        except Exception:
            continue

    return None


def validate_all() -> dict:
    """
    Validate all workflow definitions.

    Returns:
        dict with {"valid": [...], "errors": [...]}
    """
    workflows_dir = get_workflows_dir()
    if not workflows_dir.exists():
        return {"valid": [], "errors": []}

    result = {"valid": [], "errors": []}

    for path in workflows_dir.glob("*.md"):
        errors = validate_workflow(path)
        if errors:
            result["errors"].append({"file": str(path.name), "errors": errors})
        else:
            parsed = parse_workflow(path)
            result["valid"].append(parsed.name)

    return result
```

## CLI Commands

Agent workflows have their own top-level command:

```bash
# Agent workflow definition management
kurt agents list                              # List all agent workflow definitions
kurt agents show <name>                       # Show workflow details
kurt agents validate [file]                   # Validate workflow file(s)

# Manual execution
kurt agents run <name>                        # Run workflow manually
kurt agents run <name> --input topics='["AI"]'  # With inputs
kurt agents run <name> --foreground           # Run in foreground (blocking)

# Scheduling
kurt agents schedule list                     # List scheduled workflows
kurt agents schedule enable <name>            # Enable schedule
kurt agents schedule disable <name>           # Disable schedule
kurt agents schedule trigger <name>           # Trigger next run immediately

# Execution history (queries DBOS)
kurt agents history <name>                    # Show run history for a definition

# Monitoring (existing workflow commands work for agent runs too)
kurt workflows status <workflow_id>           # Show live status
kurt workflows follow <workflow_id>           # Follow live progress
kurt workflows logs <workflow_id>             # Show workflow logs
kurt workflows cancel <workflow_id>           # Cancel running workflow
```

### CLI Implementation

The `agents` command is registered as a top-level command in `src/kurt/cli/main.py`:

```python
# src/kurt/workflows/agents/cli.py

import json
import click
from pathlib import Path
from rich.console import Console
from rich.table import Table

from kurt.workflows.agents.registry import (
    list_definitions,
    get_definition,
    validate_all,
)
from kurt.workflows.agents.parser import validate_workflow
from kurt.workflows.agents.executor import run_definition

console = Console()


@click.group(name="agents")
def agents_group():
    """Manage agent-based workflow definitions."""
    pass


# Register in src/kurt/cli/main.py:
# from kurt.workflows.agents.cli import agents_group
# cli.add_command(agents_group)


@agents_group.command(name="list")
@click.option("--tag", "-t", help="Filter by tag")
@click.option("--scheduled", is_flag=True, help="Only show scheduled workflows")
def list_cmd(tag: str, scheduled: bool):
    """List all workflow definitions."""
    definitions = list_definitions()

    if tag:
        definitions = [d for d in definitions if tag in d.tags]
    if scheduled:
        definitions = [d for d in definitions if d.schedule]

    table = Table(title="Agent Workflow Definitions")
    table.add_column("Name", style="cyan")
    table.add_column("Title")
    table.add_column("Schedule")
    table.add_column("Tags")

    for d in definitions:
        schedule = d.schedule.cron if d.schedule else "-"
        if d.schedule and not d.schedule.enabled:
            schedule = f"{schedule} (disabled)"
        tags = ", ".join(d.tags) if d.tags else "-"

        table.add_row(d.name, d.title, schedule, tags)

    console.print(table)


@agents_group.command(name="show")
@click.argument("name")
def show_cmd(name: str):
    """Show workflow definition details."""
    definition = get_definition(name)
    if not definition:
        console.print(f"[red]Workflow not found: {name}[/red]")
        return

    console.print(f"[bold cyan]{definition.title}[/bold cyan]")
    console.print(f"Name: {definition.name}")

    if definition.description:
        console.print(f"\n[bold]Description:[/bold]\n{definition.description}")

    console.print(f"\n[bold]Agent Config:[/bold]")
    console.print(f"  Model: {definition.agent.model}")
    console.print(f"  Max Turns: {definition.agent.max_turns}")
    console.print(f"  Timeout: {definition.agent.timeout}s")

    if definition.schedule:
        console.print(f"\n[bold]Schedule:[/bold]")
        console.print(f"  Cron: {definition.schedule.cron}")
        console.print(f"  Timezone: {definition.schedule.timezone}")
        console.print(f"  Enabled: {definition.schedule.enabled}")

    if definition.inputs:
        console.print(f"\n[bold]Inputs:[/bold]")
        for inp in definition.inputs:
            default = f" (default: {inp.default})" if inp.default else ""
            required = " [required]" if inp.required else ""
            console.print(f"  {inp.name}: {inp.type}{default}{required}")


@agents_group.command(name="validate")
@click.argument("file", type=click.Path(exists=True), required=False)
def validate_cmd(file: str):
    """Validate workflow file(s). Validates all if no file specified."""
    if file:
        errors = validate_workflow(Path(file))
        if errors:
            console.print(f"[red]Validation failed:[/red]")
            for err in errors:
                console.print(f"  - {err}")
        else:
            console.print(f"[green]Validation passed[/green]")
    else:
        result = validate_all()
        console.print(f"Valid: {len(result['valid'])} workflows")
        for name in result['valid']:
            console.print(f"  [green]✓[/green] {name}")

        if result['errors']:
            console.print(f"\n[red]Errors:[/red]")
            for err in result['errors']:
                console.print(f"  {err['file']}:")
                for e in err['errors']:
                    console.print(f"    - {e}")


@agents_group.command(name="run")
@click.argument("name")
@click.option("--input", "-i", "inputs", multiple=True, help="Input in key=value format")
@click.option("--foreground", "-f", is_flag=True, help="Run in foreground")
def run_cmd(name: str, inputs: tuple, foreground: bool):
    """Run a workflow definition."""
    # Parse inputs
    input_dict = {}
    for inp in inputs:
        key, _, value = inp.partition("=")
        try:
            input_dict[key] = json.loads(value)
        except json.JSONDecodeError:
            input_dict[key] = value

    console.print(f"Running workflow: {name}")

    result = run_definition(
        name,
        inputs=input_dict if input_dict else None,
        background=not foreground,
        trigger="manual",
    )

    if result.get("background"):
        console.print(f"  Workflow ID: {result['workflow_id']}")
        console.print(f"\nMonitor with: [cyan]kurt workflows follow {result['workflow_id']}[/cyan]")
    else:
        console.print(f"  Status: {result.get('status')}")
        console.print(f"  Turns: {result.get('turns')}")
        console.print(f"  Tool Calls: {result.get('tool_calls')}")


@agents_group.command(name="history")
@click.argument("name")
@click.option("--limit", "-l", default=20, help="Number of runs to show")
def history_command(name: str, limit: int):
    """Show run history for a workflow (queries DBOS)."""
    from dbos import DBOS

    definition = get_definition(name)
    if not definition:
        console.print(f"[red]Workflow not found: {name}[/red]")
        return

    # Query DBOS for workflow runs matching this definition
    # DBOS stores workflow_type and definition_name as events
    runs = DBOS.get_workflows(
        workflow_name="execute_agent_workflow",
        limit=limit,
    )

    # Filter by definition name (stored as DBOS event)
    filtered_runs = [
        r for r in runs
        if DBOS.get_event(r.workflow_id, "definition_name") == name
    ]

    table = Table(title=f"Run History: {name}")
    table.add_column("Workflow ID")
    table.add_column("Status")
    table.add_column("Trigger")
    table.add_column("Started")
    table.add_column("Turns")
    table.add_column("Tokens")

    for run in filtered_runs:
        status = run.status
        status_color = {
            "SUCCESS": "green",
            "ERROR": "red",
            "PENDING": "yellow",
        }.get(status, "white")

        trigger = DBOS.get_event(run.workflow_id, "trigger") or "-"
        turns = DBOS.get_event(run.workflow_id, "agent_turns") or 0
        tokens_in = DBOS.get_event(run.workflow_id, "tokens_in") or 0
        tokens_out = DBOS.get_event(run.workflow_id, "tokens_out") or 0

        table.add_row(
            run.workflow_id[:12] + "...",
            f"[{status_color}]{status}[/{status_color}]",
            trigger,
            run.created_at.strftime("%Y-%m-%d %H:%M"),
            str(turns),
            f"{tokens_in + tokens_out:,}",
        )

    console.print(table)
```

## Monitoring Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DBOS Workflow Layer                              │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                execute_definition_workflow()                     │    │
│  │  ┌─────────────────────────────────────────────────────────┐    │    │
│  │  │              agent_execution_step()                      │    │    │
│  │  │  ┌─────────────────────────────────────────────────┐    │    │    │
│  │  │  │           Claude Code SDK Agent                  │    │    │    │
│  │  │  │                                                  │    │    │    │
│  │  │  │  receive_response() ──► Text/Tool/Usage Events  │    │    │    │
│  │  │  │  PostToolUse Hook ───► Tool Call Events         │    │    │    │
│  │  │  └─────────────────────────────────────────────────┘    │    │    │
│  │  │                         │                                │    │    │
│  │  │              ┌──────────┴──────────┐                     │    │    │
│  │  │              ▼                     ▼                     │    │    │
│  │  │     DBOS.set_event()      DBOS.write_stream()           │    │    │
│  │  │     (key-value state)     (append-only log)             │    │    │
│  │  └─────────────────────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         PostgreSQL/SQLite                                │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────────────┐  │
│  │ workflow_status │  │ workflow_events  │  │       streams          │  │
│  │  - status       │  │  - status        │  │  - agent_events        │  │
│  │  - created_at   │  │  - agent_turns   │  │  - progress            │  │
│  │  - updated_at   │  │  - tokens_in/out │  │  (append-only,         │  │
│  │                 │  │  - last_tool     │  │   offset-indexed)      │  │
│  └─────────────────┘  └──────────────────┘  └────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                              │
           ┌──────────────────┼──────────────────┐
           ▼                  ▼                  ▼
    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
    │  REST API   │    │    CLI      │    │   Web UI    │
    │             │    │             │    │             │
    │ GET /status │    │ kurt        │    │ Live panel  │
    │ GET /events │    │ workflows   │    │ with        │
    │             │    │ follow      │    │ polling     │
    └─────────────┘    └─────────────┘    └─────────────┘
```

## Agent Workflow Visualization

Agent workflows reuse the existing `kurt workflows` UI infrastructure. The same commands and views work for both code-based workflows and agent workflows - the difference is in the event stream content.

### CLI: `kurt workflows follow <workflow_id>`

Same command, enhanced view for agent workflows (detected automatically via `workflow_type` event):

**Regular workflow view (existing):**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Workflow: fetch-content                         Status: ● Running          │
│  Started: 2024-01-15 09:00:12                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  Step 3/5: Processing URLs                                                   │
│  ████████████████████░░░░░░░░░░░░░░░░░░░░  60%                              │
│                                                                              │
│  Items: 127/200 processed                                                    │
│  Errors: 2                                                                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Agent workflow view (enhanced):**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Agent Workflow: daily-research                  Status: ● Running          │
│  Started: 2024-01-15 09:00:12                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  Turn 12/50                                                                  │
│  ████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░  24%                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  Tokens                          │  Guardrails                               │
│  ├─ In:      45,231             │  ├─ Max Tokens:    500,000 (9%)           │
│  ├─ Out:     12,456             │  ├─ Max Tools:     200 (15%)              │
│  └─ Total:   57,687             │  └─ Max Time:      3600s (320s elapsed)   │
├─────────────────────────────────────────────────────────────────────────────┤
│  Tool Calls (31 total)                                                       │
│                                                                              │
│  09:00:15  ✓ Bash           kurt research search "AI agents"     2.3s       │
│  09:00:18  ✓ Read           reports/template.md                  0.1s       │
│  09:00:19  ✓ Bash           kurt signals reddit                  5.1s       │
│  09:00:25  ✓ Write          reports/research-2024-01-15.md       0.2s       │
│  09:00:26  ● Bash           kurt signals hackernews              ...        │
│                                                                              │
│  [Press 'q' to quit, 'e' to expand tool details]                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

The CLI detects `workflow_type: "agent"` in DBOS events and renders the appropriate view.

### Web UI: Workflow Detail View

Same URL pattern (`/workflows/{workflow_id}`), different rendering based on workflow type:

**Regular workflow:**
```
┌──────────────────────────────────────────────────────────────────────────────┐
│  fetch-content                                             ● Running         │
│  Started 2 min ago                                                           │
├──────────────────────────────────────────────────────────────────────────────┤
│  Step 3/5: Processing URLs                                                   │
│  Progress ████████████████████░░░░░░░░░░░░░░░░░░░░ 60%                       │
│                                                                              │
│  Items processed: 127/200                                                    │
│  Errors: 2                                                                   │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Agent workflow (enhanced view):**
```
┌──────────────────────────────────────────────────────────────────────────────┐
│  🤖 daily-research                                           ● Running       │
│  Started 5 min ago by scheduled trigger                                      │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Turn 12   │  │   57,687    │  │  31 tools   │  │   5m 20s    │         │
│  │    /50      │  │   tokens    │  │   called    │  │   elapsed   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                                              │
│  Progress ████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 24%                       │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│  Tool Activity Stream                                              [Expand ▼]│
│  ─────────────────────────────────────────────────────────────────────────── │
│                                                                              │
│  ┌─ 09:00:26 ─────────────────────────────────────────────────────────────┐ │
│  │ ● Bash (running)                                                        │ │
│  │   kurt signals hackernews --top 50                                      │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌─ 09:00:25 ─────────────────────────────────────────────────────────────┐ │
│  │ ✓ Write (0.2s)                                                          │ │
│  │   reports/research-2024-01-15.md                                        │ │
│  │   ┌────────────────────────────────────────────────────────────────┐    │ │
│  │   │ # Daily Research Report - 2024-01-15                           │    │ │
│  │   │                                                                │    │ │
│  │   │ ## Executive Summary                                           │    │ │
│  │   │ - AI agents seeing rapid adoption in enterprise...             │    │ │
│  │   └────────────────────────────────────────────────────────────────┘    │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌─ 09:00:19 ─────────────────────────────────────────────────────────────┐ │
│  │ ✓ Bash (5.1s)                                                           │ │
│  │   kurt signals reddit --subreddits programming,MachineLearning          │ │
│  │   Output: Found 47 signals matching criteria...                         │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  [Load more...]                                                              │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│  Agent Output                                                     [Expand ▼] │
│  ─────────────────────────────────────────────────────────────────────────── │
│  I've completed the research for the requested topics. Here's what I found: │
│                                                                              │
│  **AI Agents**: The field is rapidly evolving with new frameworks like...   │
│  **Developer Tools**: Recent trends show increased adoption of...           │
│                                                                              │
│  I'll now compile these findings into the daily report...                   │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Workflow List View

`kurt workflows list` and the web UI workflow list show all workflows together:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  Running Workflows                                                           │
├──────────────────────────────────────────────────────────────────────────────┤
│  Type   │ Name              │ Status    │ Progress      │ Started            │
│  ───────┼───────────────────┼───────────┼───────────────┼────────────────────│
│  🤖     │ daily-research    │ ● Running │ Turn 12/50    │ 5 min ago          │
│  📦     │ fetch-content     │ ● Running │ Step 3/5      │ 2 min ago          │
│  🤖     │ weekly-signals    │ ✓ Done    │ Completed     │ 1 hour ago         │
│  📦     │ map-urls          │ ✗ Failed  │ Step 2/3      │ 30 min ago         │
└──────────────────────────────────────────────────────────────────────────────┘
```

- 🤖 = Agent workflow (from `.kurt/workflows/*.md`)
- 📦 = Code workflow (fetch, map, signals, etc.)

### Data Structure for UI

The UI fetches from two sources:

1. **Status (DBOS events)** - polled every 1-2 seconds:
```json
{
  "status": "running",
  "agent_turns": 12,
  "tokens_in": 45231,
  "tokens_out": 12456,
  "tool_calls": 31,
  "last_tool": "Bash",
  "started_at": 1705311612.0,
  "elapsed_seconds": 320
}
```

2. **Tool stream (DBOS streams)** - paginated, newest first:
```json
{
  "events": [
    {
      "type": "tool_use",
      "timestamp": 1705311626.123,
      "data": {
        "tool": "Bash",
        "input": {"command": "kurt signals hackernews --top 50"},
        "status": "running"
      }
    },
    {
      "type": "tool_result",
      "timestamp": 1705311625.456,
      "data": {
        "tool": "Write",
        "success": true,
        "duration_ms": 200,
        "output_preview": "# Daily Research Report..."
      }
    }
  ],
  "total": 62,
  "offset": 0,
  "has_more": true
}
```

### React Component Structure

The workflow detail view automatically switches based on `workflow_type`:

```tsx
// src/kurt/web/ui/components/WorkflowDetailView.tsx

function WorkflowDetailView({ workflowId }: { workflowId: string }) {
  const { data: status } = useQuery({
    queryKey: ['workflow-status', workflowId],
    queryFn: () => fetchWorkflowStatus(workflowId),
    refetchInterval: 1000,
  });

  // Render different views based on workflow type
  if (status?.workflow_type === 'agent') {
    return <AgentWorkflowView workflowId={workflowId} status={status} />;
  }

  return <StandardWorkflowView workflowId={workflowId} status={status} />;
}


// Agent-specific view with tool stream and token metrics
function AgentWorkflowView({ workflowId, status }) {
  const { data: events, fetchNextPage } = useInfiniteQuery({
    queryKey: ['workflow-events', workflowId],
    queryFn: ({ pageParam = 0 }) => fetchWorkflowEvents(workflowId, pageParam),
    getNextPageParam: (last) => last.has_more ? last.offset + last.events.length : undefined,
  });

  return (
    <div className="agent-workflow-view">
      <StatusHeader status={status} type="agent" />
      <MetricsBar
        turns={status?.agent_turns}
        maxTurns={status?.max_turns || 50}
        tokens={status?.tokens_in + status?.tokens_out}
        maxTokens={status?.max_tokens || 500000}
        toolCalls={status?.tool_calls}
        maxToolCalls={status?.max_tool_calls || 200}
        elapsed={status?.elapsed_seconds}
        maxTime={status?.max_time || 3600}
      />
      <ToolActivityStream
        events={events?.pages.flatMap(p => p.events)}
        onLoadMore={fetchNextPage}
      />
      <AgentOutputPanel workflowId={workflowId} />
    </div>
  );
}
```

## Template Variables

Workflows support template variables using `{{variable}}` syntax:

### Built-in Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `{{date}}` | Current date (YYYY-MM-DD) | 2024-01-15 |
| `{{datetime}}` | Current datetime (ISO) | 2024-01-15T09:30:00Z |
| `{{time}}` | Current time (HH:MM) | 09:30 |
| `{{weekday}}` | Day of week | Monday |
| `{{project_root}}` | Project root path | /path/to/project |
| `{{workflow_name}}` | Workflow name | daily-research |
| `{{run_id}}` | Current run ID | 42 |

### User-defined Variables

Defined in `inputs:` frontmatter section and passed at runtime.

## Error Handling

### Failure Modes

1. **Agent timeout**: Workflow exceeds `agent.timeout` - captured in events
2. **Max turns exceeded**: Agent hits `agent.max_turns` limit - graceful stop
3. **Tool error**: Tool execution fails - logged to agent_events stream
4. **Parse error**: Invalid workflow file format - caught during sync
5. **Schedule error**: Invalid cron expression - caught during validation

## Security Considerations

1. **Tool restrictions**: `allowed_tools` whitelist in frontmatter
2. **Permission mode**: Agent runs with `bypassPermissions` in controlled environment
3. **Sandboxing**: Agent runs within Kurt's standard security sandbox
4. **Secrets**: Use environment variables, not hardcoded values
5. **Rate limiting**: Cooldown periods prevent schedule abuse

## Implementation Phases

### Phase 1: Core Infrastructure
- [ ] Workflow file parser (frontmatter + markdown)
- [ ] File-based registry (no DB needed for definitions)
- [ ] Basic CLI commands (list, show, validate)

### Phase 2: Execution with DBOS + Claude Code SDK
- [ ] DBOS workflow integration
- [ ] Claude Code SDK executor with event streaming
- [ ] Template variable resolution
- [ ] Run tracking with DBOS events and streams
- [ ] CLI run command

### Phase 3: Monitoring & Visualization
- [ ] Integration with existing `kurt workflows` commands
- [ ] Agent events stream schema
- [ ] Live status via DBOS events
- [ ] CLI follow command with tool stream
- [ ] Token/guardrail progress display

### Phase 4: Scheduling (DBOS Native)
- [ ] DBOS @scheduled decorator integration
- [ ] Cron parsing and validation
- [ ] Register scheduled workflows at startup

### Phase 5: Web UI
- [ ] API endpoints for definitions and events
- [ ] Agent workflow list panel
- [ ] Live run monitoring with tool stream
- [ ] Metrics dashboard (tokens, turns, cost)

## Dependencies

```toml
[project.dependencies]
python-frontmatter = "^1.0.0"         # Parse markdown frontmatter
croniter = "^2.0.0"                   # Cron expression parsing (used by DBOS)
claude-agent-sdk = "^0.1.0"           # Claude Code SDK (programmatic agent)
# Note: DBOS provides native cron scheduling via @DBOS.scheduled - no APScheduler needed
```

## Example Workflows

### 1. Daily Research Summary

```markdown
---
name: daily-research
title: Daily Research Summary
schedule:
  cron: "0 9 * * 1-5"
  timezone: Europe/Zurich
agent:
  max_turns: 30
inputs:
  - name: topics
    type: string[]
    default: ["AI agents", "developer tools"]
tags: [research, daily]
---

Research the following topics and create a summary report:

Topics: {{topics}}

Use `kurt research search` for each topic. Save the report to
`reports/research-{{date}}.md`.
```

### 2. Weekly Signal Digest

```markdown
---
name: weekly-signals
title: Weekly Signal Digest
schedule:
  cron: "0 10 * * 1"
agent:
  model: claude-sonnet-4-20250514
  max_turns: 50
inputs:
  - name: subreddits
    type: string[]
    default: ["programming", "MachineLearning"]
tags: [signals, weekly]
---

Compile a weekly digest of signals from Reddit and Hacker News.

1. Run `kurt signals reddit` for subreddits: {{subreddits}}
2. Run `kurt signals hackernews --top 50`
3. Summarize top signals into `reports/signals-week-{{date}}.md`
```

### 3. Content Pipeline

```markdown
---
name: content-pipeline
title: Content Ingestion Pipeline
schedule:
  cron: "0 */6 * * *"
agent:
  allowed_tools:
    - Bash
    - Read
    - Write
guardrails:
  max_time: 1800
inputs:
  - name: source_url
    type: string
    required: true
tags: [content, pipeline]
---

Fetch and process content from {{source_url}}:

1. Run `kurt content fetch {{source_url}}`
2. Generate embeddings with `kurt content embed`
3. Log completion to console
```

"""Executor for agent-based workflows using Claude Code CLI and DBOS."""

from __future__ import annotations

import json
import os
import re
import tempfile
import time
from datetime import datetime
from typing import Any, Optional

from dbos import DBOS

from kurt.config import get_config_file_path
from kurt.core import run_workflow

from .parser import ParsedWorkflow


def _create_tool_tracking_settings() -> tuple[str, str]:
    """
    Create temp settings file with PostToolUse hook for tool call tracking.

    Returns:
        (settings_file_path, tool_log_path)
    """
    # Create temp file for tool call logging
    tool_log_fd, tool_log_path = tempfile.mkstemp(suffix=".jsonl", prefix="kurt_tools_")
    os.close(tool_log_fd)

    # Create temp settings file with PostToolUse hook
    settings = {
        "hooks": {
            "PostToolUse": [
                {
                    "matcher": "*",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "kurt agents track-tool",
                            "timeout": 5,
                        }
                    ],
                }
            ]
        }
    }

    settings_fd, settings_path = tempfile.mkstemp(suffix=".json", prefix="kurt_settings_")
    with os.fdopen(settings_fd, "w") as f:
        json.dump(settings, f)

    return settings_path, tool_log_path


def _cleanup_tool_tracking(settings_path: str, tool_log_path: str) -> int:
    """
    Clean up temp files and return tool call count.

    Args:
        settings_path: Path to temp settings file
        tool_log_path: Path to temp tool log file

    Returns:
        Number of tool calls logged
    """
    tool_calls = 0
    try:
        with open(tool_log_path) as f:
            tool_calls = sum(1 for _ in f)
    except Exception:
        pass

    # Clean up temp files
    for path in [settings_path, tool_log_path]:
        try:
            os.unlink(path)
        except Exception:
            pass

    return tool_calls


def _get_project_root() -> str:
    """Get the project root directory."""
    return str(get_config_file_path().parent)


def resolve_template(body: str, inputs: dict[str, Any]) -> str:
    """
    Resolve template variables in workflow body.

    Supports {{variable}} syntax with built-in date/time variables.
    """
    now = datetime.now()
    builtins = {
        "date": now.strftime("%Y-%m-%d"),
        "datetime": now.isoformat(),
        "time": now.strftime("%H:%M"),
        "weekday": now.strftime("%A"),
        "project_root": _get_project_root(),
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
def execute_agent_workflow(
    definition_dict: dict[str, Any],
    inputs: dict[str, Any],
    trigger: str = "manual",
) -> dict[str, Any]:
    """
    Execute an agent workflow inside DBOS.

    All state is tracked via DBOS events/streams - no custom tables needed.

    Args:
        definition_dict: ParsedWorkflow as dict
        inputs: Input parameters merged with defaults
        trigger: What triggered this run (manual, scheduled, api)

    Returns:
        Dict with workflow results
    """
    definition = ParsedWorkflow.model_validate(definition_dict)
    workflow_id = DBOS.workflow_id

    # Store workflow metadata in DBOS events
    DBOS.set_event("workflow_type", "agent")
    DBOS.set_event("definition_name", definition.name)
    DBOS.set_event("trigger", trigger)
    DBOS.set_event("status", "running")
    DBOS.set_event("started_at", time.time())

    DBOS.write_stream(
        "progress",
        {
            "type": "workflow",
            "status": "start",
            "timestamp": time.time(),
        },
    )

    try:
        # Resolve template variables
        prompt = resolve_template(definition.body, inputs)

        # Add workflow context to prompt
        prompt = f"""# Workflow: {definition.title}

{prompt}

---
Workflow ID: {workflow_id}
"""

        # Execute agent
        result = agent_execution_step(
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
        DBOS.set_event("stop_reason", result.get("stop_reason", "completed"))

        DBOS.write_stream(
            "progress",
            {
                "type": "workflow",
                "status": "complete",
                "timestamp": time.time(),
            },
        )

        return {"workflow_id": workflow_id, "status": "completed", **result}

    except Exception as e:
        DBOS.set_event("status", "failed")
        DBOS.set_event("completed_at", time.time())
        DBOS.set_event("last_error", str(e))

        DBOS.write_stream(
            "agent_events",
            {
                "type": "error",
                "timestamp": time.time(),
                "data": {"message": str(e), "code": "WORKFLOW_ERROR"},
            },
        )

        raise


@DBOS.step(name="agent_execution", retries_allowed=False)
def agent_execution_step(
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
    Execute Claude Code agent via subprocess.

    Uses the `claude` CLI directly for simplicity and stability.
    Tool calls are tracked via PostToolUse hook.
    """
    import shutil
    import subprocess

    start_time = time.time()

    # Check if claude is available
    claude_path = shutil.which("claude")
    if not claude_path:
        raise RuntimeError(
            "Claude Code CLI not found. Install with: "
            "curl -fsSL https://claude.ai/install.sh | bash"
        )

    DBOS.write_stream(
        "progress",
        {
            "type": "step",
            "step": "agent_execution",
            "status": "start",
            "total": max_turns,
            "timestamp": time.time(),
        },
    )

    # Create tool tracking settings (temp files for hook-based tracking)
    settings_path, tool_log_path = _create_tool_tracking_settings()

    # Set up environment for subprocess
    env = os.environ.copy()
    env["KURT_TOOL_LOG_FILE"] = tool_log_path
    # Pass parent workflow ID so child workflows can be nested
    env["KURT_PARENT_WORKFLOW_ID"] = DBOS.workflow_id

    # Build claude command
    cmd = [
        claude_path,
        "--print",  # Print output, don't open interactive mode
        "--output-format",
        "json",  # Get structured output
        "--max-turns",
        str(max_turns),
        "--model",
        model,
        "--settings",
        settings_path,  # Use custom settings with tool tracking hook
    ]

    # Add allowed tools if specified
    if allowed_tools:
        cmd.extend(["--allowedTools", ",".join(allowed_tools)])

    # Add permission mode (acceptEdits, bypassPermissions, default, plan, etc.)
    if permission_mode:
        cmd.extend(["--permission-mode", permission_mode])

    # Add the prompt as positional argument
    cmd.append(prompt)

    DBOS.write_stream(
        "agent_events",
        {
            "type": "start",
            "timestamp": time.time(),
            "data": {"command": " ".join(cmd[:5]) + " ..."},
        },
    )

    try:
        # Run claude with timeout
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=max_time,
            cwd=_get_project_root(),
            env=env,
        )

        # Get tool call count from hook logs (tracks ALL tools, not just web)
        tool_calls = _cleanup_tool_tracking(settings_path, tool_log_path)

        # Parse JSON output if available
        output_data = {}
        if result.stdout:
            try:
                # Claude outputs JSON when --output-format json is used
                output_data = json.loads(result.stdout)
            except json.JSONDecodeError:
                # Plain text output
                output_data = {"result": result.stdout}

        # Extract metrics from output (claude JSON format)
        turns = output_data.get("num_turns", 1)
        cost = output_data.get("total_cost_usd", 0.0)

        # Usage is nested in the JSON response
        usage = output_data.get("usage", {})
        tokens_in = usage.get("input_tokens", 0) + usage.get("cache_read_input_tokens", 0)
        tokens_out = usage.get("output_tokens", 0)

        DBOS.set_event("agent_turns", turns)
        DBOS.set_event("tool_calls", tool_calls)
        DBOS.set_event("tokens_in", tokens_in)
        DBOS.set_event("tokens_out", tokens_out)
        DBOS.set_event("cost_usd", cost)

        # Log final result
        result_text = output_data.get("result", "")
        if result_text:
            DBOS.write_stream(
                "agent_events",
                {
                    "type": "result",
                    "timestamp": time.time(),
                    "data": {"content": str(result_text)[:2000]},
                },
            )

        # Determine stop reason
        is_error = output_data.get("is_error", False)
        subtype = output_data.get("subtype", "success")
        if result.returncode == 0 and not is_error:
            stop_reason = "completed"
        elif is_error:
            stop_reason = f"error: {subtype}"
        else:
            stop_reason = f"exit_code_{result.returncode}"

        # Check if there was an error in stderr
        if result.returncode != 0 and result.stderr:
            DBOS.write_stream(
                "agent_events",
                {
                    "type": "error",
                    "timestamp": time.time(),
                    "data": {"stderr": result.stderr[:1000]},
                },
            )
            if not is_error:
                stop_reason = f"error: {result.stderr[:100]}"

    except subprocess.TimeoutExpired:
        # Ensure cleanup on timeout
        tool_calls = _cleanup_tool_tracking(settings_path, tool_log_path)
        stop_reason = f"max_time ({max_time}s) exceeded"
        turns = 0
        tokens_in = 0
        tokens_out = 0
        cost = 0.0

        DBOS.write_stream(
            "agent_events",
            {
                "type": "guardrail_triggered",
                "timestamp": time.time(),
                "data": {"reason": stop_reason},
            },
        )

    except Exception:
        # Ensure cleanup on any error
        _cleanup_tool_tracking(settings_path, tool_log_path)
        raise

    DBOS.write_stream(
        "progress",
        {
            "type": "step",
            "step": "agent_execution",
            "status": "complete",
            "current": turns,
            "total": max_turns,
            "timestamp": time.time(),
        },
    )

    return {
        "turns": turns,
        "tool_calls": tool_calls,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_usd": cost,
        "duration_seconds": round(time.time() - start_time, 2),
        "stop_reason": stop_reason,
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
    from .registry import get_definition

    # Get definition
    definition = get_definition(definition_name)
    if not definition:
        raise ValueError(f"Workflow definition not found: {definition_name}")

    # Merge inputs with defaults from definition
    resolved_inputs = dict(definition.inputs)  # Start with defaults
    if inputs:
        resolved_inputs.update(inputs)  # Override with provided inputs

    # Execute via DBOS
    result = run_workflow(
        execute_agent_workflow,
        definition.model_dump(),
        resolved_inputs,
        trigger,
        background=background,
    )

    # Background mode returns workflow_id string, wrap it
    if background:
        return {"workflow_id": result, "status": "started"}
    return result

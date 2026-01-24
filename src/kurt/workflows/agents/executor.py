"""Executor for agent-based workflows using Claude Code CLI.

This module runs agent workflows (Claude Code subprocess) with observability
tracking via workflow_runs/step_logs/step_events tables (no DBOS).
"""

from __future__ import annotations

import ast
import json
import logging
import os
import re
import subprocess
import tempfile
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

from kurt.config import get_config_file_path
from kurt.db.dolt import DoltDB, check_schema_exists, init_observability_schema
from kurt.observability import WorkflowLifecycle
from kurt.observability.tracking import track_event

from .parser import ParsedWorkflow
from .registry import get_workflow_dir

logger = logging.getLogger(__name__)


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


def _get_dolt_db(project_root: Path | None = None) -> DoltDB:
    """Get or initialize Dolt database for observability."""
    if project_root is None:
        project_root = Path(_get_project_root())

    dolt_path = os.environ.get("DOLT_PATH", ".")
    path = Path(dolt_path)
    if not path.is_absolute():
        path = project_root / path

    db = DoltDB(path)
    if not db.exists():
        db.init()
        init_observability_schema(db)
    else:
        schema_status = check_schema_exists(db)
        if not all(schema_status.values()):
            init_observability_schema(db)
    return db


# Progress callback type for step events
ProgressCallback = Callable[[dict[str, Any]], None]


def _extract_tools_documentation(workflow_name: str) -> str:
    """
    Extract docstrings from DBOS workflows in tools.py.

    Returns markdown documentation of available tools.
    """
    workflow_dir = get_workflow_dir(workflow_name)
    if not workflow_dir:
        return ""

    tools_path = workflow_dir / "tools.py"
    if not tools_path.exists():
        return ""

    try:
        source = tools_path.read_text()
        tree = ast.parse(source)
    except Exception:
        return ""

    tools = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # Check for @DBOS.workflow() or @DBOS.step() decorator
            is_dbos = False
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call):
                    if isinstance(decorator.func, ast.Attribute):
                        if decorator.func.attr in ("workflow", "step"):
                            is_dbos = True
                            break
                elif isinstance(decorator, ast.Attribute):
                    if decorator.attr in ("workflow", "step"):
                        is_dbos = True
                        break

            if is_dbos:
                # Extract function signature
                args = []
                for arg in node.args.args:
                    arg_name = arg.arg
                    if arg.annotation:
                        try:
                            arg_type = ast.unparse(arg.annotation)
                            args.append(f"{arg_name}: {arg_type}")
                        except Exception:
                            args.append(arg_name)
                    else:
                        args.append(arg_name)

                sig = f"{node.name}({', '.join(args)})"

                # Extract docstring
                docstring = ast.get_docstring(node) or "No description"

                tools.append(f"- `{sig}` - {docstring.split(chr(10))[0]}")

    if not tools:
        return ""

    return "## Available Tools (from tools.py)\n\n" + "\n".join(tools) + "\n"


def _get_tools_import_path(workflow_name: str) -> Optional[str]:
    """Get the Python import path for workflow tools."""
    workflow_dir = get_workflow_dir(workflow_name)
    if not workflow_dir or not (workflow_dir / "tools.py").exists():
        return None

    # Convert path to import: workflows/competitor_tracker/tools.py -> workflows.competitor_tracker.tools
    dir_name = workflow_dir.name
    return f"workflows.{dir_name}.tools"


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


def execute_agent_workflow(
    definition_dict: dict[str, Any],
    inputs: dict[str, Any],
    trigger: str = "manual",
    run_id: str | None = None,
    db: DoltDB | None = None,
) -> dict[str, Any]:
    """
    Execute an agent workflow with observability tracking.

    All state is tracked via workflow_runs/step_logs/step_events tables.

    Args:
        definition_dict: ParsedWorkflow as dict
        inputs: Input parameters merged with defaults
        trigger: What triggered this run (manual, scheduled, api)
        run_id: Optional existing run ID (for background execution)
        db: Optional DoltDB instance (created if not provided)

    Returns:
        Dict with workflow results
    """
    definition = ParsedWorkflow.model_validate(definition_dict)

    # Initialize database and lifecycle tracking
    if db is None:
        db = _get_dolt_db()
    lifecycle = WorkflowLifecycle(db)

    # Create or resume workflow run
    if run_id is None:
        run_id = str(uuid.uuid4())
        metadata = {
            "workflow_type": "agent",
            "definition_name": definition.name,
            "trigger": trigger,
        }
        # Store parent workflow ID for nested workflow display
        parent_workflow_id = os.environ.get("KURT_PARENT_WORKFLOW_ID")
        if parent_workflow_id:
            metadata["parent_workflow_id"] = parent_workflow_id

        lifecycle.create_run(
            workflow=f"agent:{definition.name}",
            inputs=inputs,
            metadata=metadata,
            run_id=run_id,
            status="running",
        )
    else:
        lifecycle.update_status(run_id, "running")

    # Emit workflow start event
    track_event(
        run_id=run_id,
        step_id="workflow",
        status="running",
        message=f"Agent workflow {definition.name} started",
        metadata={"trigger": trigger},
        db=db,
    )

    try:
        # Resolve template variables
        prompt = resolve_template(definition.body, inputs)

        # Add tools documentation if tools.py exists
        tools_docs = _extract_tools_documentation(definition.name)
        tools_import = _get_tools_import_path(definition.name)

        tools_section = ""
        if tools_docs:
            tools_section = f"""
{tools_docs}

To call a tool, use Python:
```python
from {tools_import} import <function_name>
result = <function_name>(args)
```

"""

        # Add workflow context to prompt
        prompt = f"""# Workflow: {definition.title}

{prompt}
{tools_section}
---
Workflow ID: {run_id}
"""

        # Get workflow directory for PYTHONPATH
        workflow_dir = get_workflow_dir(definition.name)

        # Create step log for agent execution
        lifecycle.create_step_log(
            run_id=run_id,
            step_id="agent_execution",
            tool="ClaudeCLI",
            metadata={
                "model": definition.agent.model,
                "max_turns": definition.agent.max_turns,
            },
        )

        # Build progress callback
        def on_progress(event: dict[str, Any]) -> None:
            track_event(
                run_id=run_id,
                step_id="agent_execution",
                substep=event.get("substep"),
                status=event.get("status", "progress"),
                current=event.get("current"),
                total=event.get("total"),
                message=event.get("message"),
                metadata=event.get("metadata"),
                db=db,
            )

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
            workflow_dir=str(workflow_dir) if workflow_dir else None,
            run_id=run_id,
            on_progress=on_progress,
        )

        # Update step log
        lifecycle.update_step_log(
            run_id, "agent_execution",
            status="completed",
            output_count=result.get("turns", 0),
            metadata={
                "stop_reason": result.get("stop_reason"),
                "tokens_in": result.get("tokens_in"),
                "tokens_out": result.get("tokens_out"),
                "cost_usd": result.get("cost_usd"),
            },
        )

        # Complete workflow
        lifecycle.update_status(run_id, "completed")

        track_event(
            run_id=run_id,
            step_id="workflow",
            status="completed",
            message=f"Agent workflow {definition.name} completed",
            metadata={"stop_reason": result.get("stop_reason", "completed")},
            db=db,
        )

        return {"workflow_id": run_id, "status": "completed", **result}

    except Exception as e:
        # Update step log as failed
        try:
            lifecycle.update_step_log(
                run_id, "agent_execution",
                status="failed",
                error_count=1,
                errors=[{"row_idx": None, "error_type": "exception", "message": str(e)}],
            )
        except Exception:
            pass  # Step log may not exist yet

        lifecycle.update_status(run_id, "failed", error=str(e))

        track_event(
            run_id=run_id,
            step_id="workflow",
            status="failed",
            message=f"Agent workflow failed: {str(e)}",
            metadata={"error": str(e)},
            db=db,
        )

        raise


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
    # Workflow directory for custom tools
    workflow_dir: Optional[str] = None,
    # Observability
    run_id: Optional[str] = None,
    on_progress: Optional[ProgressCallback] = None,
) -> dict[str, Any]:
    """
    Execute Claude Code agent via subprocess.

    Uses the `claude` CLI directly for simplicity and stability.
    Tool calls are tracked via PostToolUse hook.

    Args:
        prompt: The prompt to send to Claude
        model: Model name (e.g., claude-sonnet-4-20250514)
        max_turns: Maximum conversation turns
        allowed_tools: List of allowed tool names
        permission_mode: Permission mode for Claude CLI
        max_tokens: Maximum token budget
        max_tool_calls: Maximum tool invocations (not enforced by CLI)
        max_time: Maximum execution time in seconds
        workflow_dir: Path to workflow directory containing tools.py
        run_id: Optional workflow run ID for nested workflow support
        on_progress: Optional callback for progress events
    """
    import shutil

    start_time = time.time()

    # Check if claude is available
    claude_path = shutil.which("claude")
    if not claude_path:
        raise RuntimeError(
            "Claude Code CLI not found. Install with: "
            "curl -fsSL https://claude.ai/install.sh | bash"
        )

    # Emit start progress event
    if on_progress:
        on_progress({
            "substep": "execution",
            "status": "running",
            "total": max_turns,
            "message": "Starting Claude Code execution",
        })

    # Create tool tracking settings (temp files for hook-based tracking)
    settings_path, tool_log_path = _create_tool_tracking_settings()

    # Set up environment for subprocess
    env = os.environ.copy()
    env["KURT_TOOL_LOG_FILE"] = tool_log_path
    # Pass parent workflow ID so child workflows can be nested
    if run_id:
        env["KURT_PARENT_WORKFLOW_ID"] = run_id

    # Add workflow directory to PYTHONPATH for custom tool imports
    # This allows: from workflows.my_workflow.tools import my_tool
    if workflow_dir:
        workflow_path = Path(workflow_dir)
        # Set KURT_WORKFLOW_DIR so agent tools can find models.py
        env["KURT_WORKFLOW_DIR"] = str(workflow_path)
        # Add parent of workflows dir (project root) to PYTHONPATH
        # so imports like `from workflows.name.tools import func` work
        workflows_parent = workflow_path.parent.parent  # workflows/ -> project root
        current_pythonpath = env.get("PYTHONPATH", "")
        if current_pythonpath:
            env["PYTHONPATH"] = f"{workflows_parent}:{current_pythonpath}"
        else:
            env["PYTHONPATH"] = str(workflows_parent)

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

    logger.debug(f"Running Claude CLI: {' '.join(cmd[:5])} ...")

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

        # Emit result progress event
        if on_progress:
            result_text = output_data.get("result", "")
            on_progress({
                "substep": "result",
                "status": "progress",
                "current": turns,
                "total": max_turns,
                "message": f"Completed {turns} turns",
                "metadata": {
                    "tokens_in": tokens_in,
                    "tokens_out": tokens_out,
                    "cost_usd": cost,
                    "result_preview": str(result_text)[:500] if result_text else None,
                },
            })

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
            if on_progress:
                on_progress({
                    "substep": "error",
                    "status": "failed",
                    "message": result.stderr[:500],
                })
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

        if on_progress:
            on_progress({
                "substep": "timeout",
                "status": "failed",
                "message": stop_reason,
            })

    except Exception:
        # Ensure cleanup on any error
        _cleanup_tool_tracking(settings_path, tool_log_path)
        raise

    # Emit completion progress event
    if on_progress:
        on_progress({
            "substep": "execution",
            "status": "completed",
            "current": turns,
            "total": max_turns,
            "message": f"Execution complete: {stop_reason}",
        })

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


# ============================================================================
# DAG Executor for DBOS-driven workflows with [steps.xxx] sections
# ============================================================================


def execute_steps_workflow(
    definition_dict: dict[str, Any],
    inputs: dict[str, Any],
    trigger: str = "manual",
    run_id: str | None = None,
    db: DoltDB | None = None,
) -> dict[str, Any]:
    """
    Execute a DAG-orchestrated workflow with observability tracking.

    Steps are executed in topological order based on their depends_on fields.
    Results from each step are passed to dependent steps via context.

    Args:
        definition_dict: ParsedWorkflow as dict
        inputs: Input parameters merged with defaults
        trigger: What triggered this run (manual, scheduled, api)
        run_id: Optional existing run ID (for background execution)
        db: Optional DoltDB instance (created if not provided)

    Returns:
        Dict with workflow results and step outputs
    """
    from graphlib import TopologicalSorter

    from .parser import ParsedWorkflow

    definition = ParsedWorkflow.model_validate(definition_dict)

    # Initialize database and lifecycle tracking
    if db is None:
        db = _get_dolt_db()
    lifecycle = WorkflowLifecycle(db)

    # Create or resume workflow run
    if run_id is None:
        run_id = str(uuid.uuid4())
        metadata = {
            "workflow_type": "steps",
            "definition_name": definition.name,
            "trigger": trigger,
            "total_steps": len(definition.steps),
        }
        # Store parent workflow ID for nested workflow display
        parent_workflow_id = os.environ.get("KURT_PARENT_WORKFLOW_ID")
        if parent_workflow_id:
            metadata["parent_workflow_id"] = parent_workflow_id

        lifecycle.create_run(
            workflow=f"steps:{definition.name}",
            inputs=inputs,
            metadata=metadata,
            run_id=run_id,
            status="running",
        )
    else:
        lifecycle.update_status(run_id, "running")

    # Emit workflow start event
    track_event(
        run_id=run_id,
        step_id="workflow",
        status="running",
        message=f"Steps workflow {definition.name} started",
        total=len(definition.steps),
        metadata={"trigger": trigger},
        db=db,
    )

    # Build context for step execution
    context = {
        "workflow_id": run_id,
        "inputs": inputs,
        "outputs": {},  # Step outputs keyed by step name
        "definition": definition_dict,
        "db": db,
        "lifecycle": lifecycle,
    }

    try:
        # Build dependency graph and get execution order
        graph = {name: set(step.depends_on) for name, step in definition.steps.items()}
        sorter = TopologicalSorter(graph)
        execution_order = list(sorter.static_order())

        track_event(
            run_id=run_id,
            step_id="workflow",
            substep="dag",
            status="progress",
            message=f"Execution order: {', '.join(execution_order)}",
            db=db,
        )

        # Execute steps in order
        for idx, step_name in enumerate(execution_order):
            step = definition.steps[step_name]

            # Create step log
            lifecycle.create_step_log(
                run_id=run_id,
                step_id=step_name,
                tool=step.type,
                metadata={"index": idx + 1, "total": len(execution_order)},
            )

            track_event(
                run_id=run_id,
                step_id=step_name,
                status="running",
                current=idx + 1,
                total=len(execution_order),
                message=f"Starting step {step_name}",
                db=db,
            )

            # Execute step based on type
            step_result = _execute_step(step_name, step, context, definition)

            # Store result in context for dependent steps
            context["outputs"][step_name] = step_result

            # Update step log
            lifecycle.update_step_log(
                run_id, step_name,
                status="completed",
                output_count=len(step_result) if isinstance(step_result, dict) else 1,
            )

            track_event(
                run_id=run_id,
                step_id=step_name,
                status="completed",
                current=idx + 1,
                total=len(execution_order),
                message=f"Completed step {step_name}",
                db=db,
            )

        # Complete workflow
        lifecycle.update_status(run_id, "completed")

        track_event(
            run_id=run_id,
            step_id="workflow",
            status="completed",
            message=f"Steps workflow {definition.name} completed",
            db=db,
        )

        return {
            "workflow_id": run_id,
            "status": "completed",
            "outputs": context["outputs"],
            "execution_order": execution_order,
        }

    except Exception as e:
        lifecycle.update_status(run_id, "failed", error=str(e))

        track_event(
            run_id=run_id,
            step_id="workflow",
            status="failed",
            message=f"Steps workflow failed: {str(e)}",
            metadata={"error": str(e)},
            db=db,
        )

        raise


def _execute_step(
    step_name: str,
    step: Any,  # StepConfig
    context: dict[str, Any],
    definition: Any,  # ParsedWorkflow
) -> dict[str, Any]:
    """
    Execute a single step based on its type.

    Args:
        step_name: Name of the step
        step: StepConfig instance
        context: Workflow context with inputs and outputs
        definition: ParsedWorkflow instance

    Returns:
        Step result dict
    """
    if step.type == "function":
        return execute_function_step(step_name, step.function, context, definition.name)
    elif step.type == "agent":
        return execute_agent_step(
            step_name,
            step.prompt,
            step.model or definition.agent.model if definition.agent else "claude-sonnet-4-20250514",
            step.max_turns or 15,
            context,
            definition.name,
        )
    elif step.type == "llm":
        return execute_llm_step(
            step_name,
            step.prompt_template,
            step.output_schema,
            context,
            definition.name,
        )
    else:
        raise ValueError(f"Unknown step type: {step.type}")


def execute_function_step(
    step_name: str,
    function_name: str,
    context: dict[str, Any],
    workflow_name: str,
) -> dict[str, Any]:
    """
    Execute a function from the workflow's tools.py.

    Args:
        step_name: Name of the step
        function_name: Name of the function in tools.py
        context: Workflow context with inputs and outputs
        workflow_name: Name of the workflow for finding tools.py

    Returns:
        Function result
    """

    workflow_dir = get_workflow_dir(workflow_name)
    if not workflow_dir:
        raise ValueError(f"Workflow directory not found: {workflow_name}")

    tools_path = workflow_dir / "tools.py"
    if not tools_path.exists():
        raise ValueError(f"tools.py not found in workflow: {workflow_name}")

    # Load the module
    from kurt.core.model_utils import _load_module_from_path

    module = _load_module_from_path(tools_path)
    if module is None:
        raise ImportError(f"Failed to load tools.py from {workflow_name}")

    # Get the function
    if not hasattr(module, function_name):
        raise ValueError(f"Function '{function_name}' not found in tools.py")

    func = getattr(module, function_name)

    # Call the function with context
    start_time = time.time()
    result = func(context)
    duration = time.time() - start_time

    # Emit progress event if db is available in context
    db = context.get("db")
    run_id = context.get("workflow_id")
    if db and run_id:
        track_event(
            run_id=run_id,
            step_id=step_name,
            substep="function",
            status="progress",
            message=f"Function {function_name} executed in {duration:.2f}s",
            metadata={
                "function": function_name,
                "duration_seconds": round(duration, 2),
            },
            db=db,
        )

    if isinstance(result, dict):
        return result
    return {"result": result}


def execute_agent_step(
    step_name: str,
    prompt: str,
    model: str,
    max_turns: int,
    context: dict[str, Any],
    workflow_name: str,
) -> dict[str, Any]:
    """
    Execute an agent step that spawns Claude Code subprocess.

    Args:
        step_name: Name of the step
        prompt: Agent prompt (can include {outputs.step_name} template vars)
        model: Model to use
        max_turns: Maximum conversation turns
        context: Workflow context with inputs and outputs
        workflow_name: Name of the workflow

    Returns:
        Agent execution result
    """
    # Resolve template variables in prompt
    resolved_prompt = resolve_template(prompt, context["inputs"])

    # Replace {outputs.step_name} with actual values
    for output_name, output_value in context["outputs"].items():
        placeholder = f"{{outputs.{output_name}}}"
        if placeholder in resolved_prompt:
            # Convert dicts to JSON for prompt insertion
            if isinstance(output_value, dict):
                resolved_prompt = resolved_prompt.replace(placeholder, json.dumps(output_value, indent=2))
            else:
                resolved_prompt = resolved_prompt.replace(placeholder, str(output_value))

    # Add workflow context
    resolved_prompt = f"""# Step: {step_name}

Workflow ID: {context['workflow_id']}

{resolved_prompt}
"""

    workflow_dir = get_workflow_dir(workflow_name)

    # Build progress callback
    db = context.get("db")
    run_id = context.get("workflow_id")

    def on_progress(event: dict[str, Any]) -> None:
        if db and run_id:
            track_event(
                run_id=run_id,
                step_id=step_name,
                substep=event.get("substep"),
                status=event.get("status", "progress"),
                current=event.get("current"),
                total=event.get("total"),
                message=event.get("message"),
                metadata=event.get("metadata"),
                db=db,
            )

    # Execute agent
    result = agent_execution_step(
        prompt=resolved_prompt,
        model=model,
        max_turns=max_turns,
        allowed_tools=["Bash", "Read", "Write", "Edit", "Glob", "Grep"],
        permission_mode="bypassPermissions",
        max_tokens=200000,
        max_tool_calls=100,
        max_time=600,
        workflow_dir=str(workflow_dir) if workflow_dir else None,
        run_id=run_id,
        on_progress=on_progress,
    )

    return result


def execute_llm_step(
    step_name: str,
    prompt_template: str,
    output_schema_name: Optional[str],
    context: dict[str, Any],
    workflow_name: str,
) -> dict[str, Any]:
    """
    Execute an LLM step for batch processing.

    Args:
        step_name: Name of the step
        prompt_template: Prompt template with {field} placeholders
        output_schema_name: Optional Pydantic model name from models.py
        context: Workflow context with inputs and outputs
        workflow_name: Name of the workflow

    Returns:
        LLM step results
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError("pandas is required for LLM steps")

    # Get input data from previous step outputs or inputs
    # Look for data in outputs or inputs
    input_data = None
    for output_name, output_value in context["outputs"].items():
        if isinstance(output_value, (list, dict)):
            if isinstance(output_value, list):
                input_data = output_value
            elif "results" in output_value:
                input_data = output_value["results"]
            elif "data" in output_value:
                input_data = output_value["data"]
            break

    if input_data is None:
        input_data = context["inputs"].get("data", [])

    if not input_data:
        return {"results": [], "total": 0, "successful": 0}

    # Resolve output schema if provided
    output_schema = None
    if output_schema_name:
        workflow_dir = get_workflow_dir(workflow_name)
        if workflow_dir:
            from kurt.core.model_utils import _load_module_from_path

            models_path = workflow_dir / "models.py"
            if models_path.exists():
                module = _load_module_from_path(models_path)
                if module and hasattr(module, output_schema_name):
                    output_schema = getattr(module, output_schema_name)

    if output_schema is None:
        from pydantic import BaseModel

        class DefaultOutput(BaseModel):
            response: str = ""

        output_schema = DefaultOutput

    # Set up LLM function
    from kurt.config import resolve_model_settings

    settings = resolve_model_settings(model_category="LLM")

    import litellm

    def llm_fn(prompt_text: str):
        response = litellm.completion(
            model=settings.model,
            messages=[{"role": "user", "content": prompt_text}],
        )
        content = response.choices[0].message.content or ""
        return output_schema(response=content)

    # Detect input columns from template
    import re as re_module

    input_columns = list(set(re_module.findall(r"\{(\w+)\}", prompt_template)))

    # Create and run LLMStep
    from kurt.core import LLMStep

    step = LLMStep(
        name=step_name,
        input_columns=input_columns,
        prompt_template=prompt_template,
        output_schema=output_schema,
        llm_fn=llm_fn,
        concurrency=3,
    )

    df = pd.DataFrame(input_data)
    result_df = step.run(df)

    results = result_df.to_dict(orient="records")
    status_col = f"{step_name}_status"
    successful = sum(1 for r in results if r.get(status_col) == "success")

    return {
        "results": results,
        "total": len(results),
        "successful": successful,
    }


# --- Background Execution ---


def _create_pending_run(
    workflow_name: str,
    definition_dict: dict[str, Any],
    inputs: dict[str, Any],
    trigger: str,
) -> str:
    """Create a pending workflow run in the database."""
    db = _get_dolt_db()
    lifecycle = WorkflowLifecycle(db)

    run_id = str(uuid.uuid4())
    metadata = {
        "workflow_type": "agent" if "agent" in workflow_name else "steps",
        "definition_name": definition_dict.get("name", "unknown"),
        "trigger": trigger,
    }

    lifecycle.create_run(
        workflow=workflow_name,
        inputs=inputs,
        metadata=metadata,
        run_id=run_id,
        status="pending",
    )

    return run_id


def _spawn_background_agent_run(
    workflow_fn: Callable,
    definition_dict: dict[str, Any],
    inputs: dict[str, Any],
    trigger: str,
) -> dict[str, Any]:
    """
    Spawn a background subprocess to run the agent workflow.

    Creates a pending run, writes payload to temp file, and spawns subprocess.
    """
    import sys

    # Determine workflow name
    is_steps = workflow_fn == execute_steps_workflow
    workflow_name = f"{'steps' if is_steps else 'agent'}:{definition_dict.get('name', 'unknown')}"

    # Create pending run
    run_id = _create_pending_run(workflow_name, definition_dict, inputs, trigger)

    # Write payload to temp file
    payload = {
        "run_id": run_id,
        "workflow_type": "steps" if is_steps else "agent",
        "definition_dict": definition_dict,
        "inputs": inputs,
        "trigger": trigger,
        "project_root": _get_project_root(),
    }

    payload_file = tempfile.NamedTemporaryFile("w", delete=False, suffix=".json")
    with payload_file as handle:
        json.dump(payload, handle)

    # Spawn subprocess
    cmd = [sys.executable, "-m", "kurt.workflows.agents.executor", "--payload", payload_file.name]
    subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=_get_project_root(),
        start_new_session=True,
    )

    return {"workflow_id": run_id, "status": "started"}


def _run_from_payload(payload_path: str) -> None:
    """Run a workflow from a payload file (called by subprocess)."""
    payload = json.loads(Path(payload_path).read_text())

    run_id = payload["run_id"]
    workflow_type = payload["workflow_type"]
    definition_dict = payload["definition_dict"]
    inputs = payload["inputs"]
    trigger = payload["trigger"]

    if workflow_type == "steps":
        execute_steps_workflow(
            definition_dict=definition_dict,
            inputs=inputs,
            trigger=trigger,
            run_id=run_id,
        )
    else:
        execute_agent_workflow(
            definition_dict=definition_dict,
            inputs=inputs,
            trigger=trigger,
            run_id=run_id,
        )


# --- Public API ---


def run_definition(
    definition_name: str,
    inputs: Optional[dict[str, Any]] = None,
    background: bool = True,
    trigger: str = "manual",
) -> dict[str, Any]:
    """
    Run a workflow definition by name.

    Automatically detects workflow type:
    - Agent-driven: Uses [agent] section, executed via Claude Code
    - Steps-driven: Uses [steps.xxx] sections, executed via DAG orchestration

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

    # Select workflow executor based on type
    if definition.is_dbos_driven:
        workflow_fn = execute_steps_workflow
    else:
        workflow_fn = execute_agent_workflow

    if background:
        # Background execution via subprocess
        return _spawn_background_agent_run(
            workflow_fn=workflow_fn,
            definition_dict=definition.model_dump(),
            inputs=resolved_inputs,
            trigger=trigger,
        )
    else:
        # Foreground execution
        return workflow_fn(
            definition_dict=definition.model_dump(),
            inputs=resolved_inputs,
            trigger=trigger,
        )


def run_from_path(
    workflow_path: Path,
    inputs: Optional[dict[str, Any]] = None,
    background: bool = True,
    trigger: str = "manual",
) -> dict[str, Any]:
    """
    Run a workflow from a file path.

    Automatically detects workflow type and file format:
    - Agent-driven (.md or .toml with [agent]): Executed via Claude Code
    - Steps-driven (.toml with [steps.xxx]): Executed via DAG orchestration

    Args:
        workflow_path: Path to workflow file (.md or .toml) or directory
        inputs: Input parameters (will use defaults if not provided)
        background: Run in background worker (default True)
        trigger: What triggered this run (manual, scheduled, api)

    Returns:
        dict with workflow_id
    """
    from .parser import parse_workflow

    # Resolve path
    workflow_path = Path(workflow_path)
    if workflow_path.is_dir():
        # Try .toml first, then .md
        workflow_file = workflow_path / "workflow.toml"
        if not workflow_file.exists():
            workflow_file = workflow_path / "workflow.md"
        if not workflow_file.exists():
            raise ValueError(f"No workflow.toml or workflow.md found in {workflow_path}")
        workflow_path = workflow_file

    if not workflow_path.exists():
        raise ValueError(f"Workflow file not found: {workflow_path}")

    # Parse the workflow
    definition = parse_workflow(workflow_path)

    # Merge inputs with defaults from definition
    resolved_inputs = dict(definition.inputs)  # Start with defaults
    if inputs:
        resolved_inputs.update(inputs)  # Override with provided inputs

    # Select workflow executor based on type
    if definition.is_dbos_driven:
        workflow_fn = execute_steps_workflow
    else:
        workflow_fn = execute_agent_workflow

    if background:
        # Background execution via subprocess
        return _spawn_background_agent_run(
            workflow_fn=workflow_fn,
            definition_dict=definition.model_dump(),
            inputs=resolved_inputs,
            trigger=trigger,
        )
    else:
        # Foreground execution
        return workflow_fn(
            definition_dict=definition.model_dump(),
            inputs=resolved_inputs,
            trigger=trigger,
        )


# --- CLI Entry Point for Background Execution ---


def _parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse command line arguments for background execution."""
    import argparse

    parser = argparse.ArgumentParser(description="Run agent workflow from payload file.")
    parser.add_argument("--payload", required=True, help="Path to JSON payload file")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Main entry point for background subprocess execution."""
    import sys

    args = _parse_args(argv or sys.argv[1:])
    try:
        _run_from_payload(args.payload)
        # Clean up payload file
        try:
            Path(args.payload).unlink()
        except Exception:
            pass
        return 0
    except Exception as e:
        logger.error(f"Background workflow failed: {e}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
"""
Async workflow executor for Kurt engine.

Executes workflow DAG with asyncio. Runs parallel steps concurrently.
Resolves step type to tool name via ToolRegistry/execute_tool.
Passes output data between steps via depends_on.
Fan-in: concatenates outputs in depends_on order.

Exit Codes:
    0: All steps succeeded
    1: One or more steps failed
    2: Workflow canceled
    3: Internal executor error
"""

from __future__ import annotations

import asyncio
import importlib.util
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from pathlib import Path
from typing import Any, Callable, Literal

from kurt.observability.tracking import track_event
from kurt.tools.core import ToolCanceledError, ToolContext, ToolError, ToolResult, execute_tool
from kurt.workflows.toml.dag import build_dag
from kurt.workflows.toml.interpolation import interpolate_step_config
from kurt.workflows.toml.parser import StepDef, WorkflowDefinition, resolve_step_type

logger = logging.getLogger(__name__)


# ============================================================================
# Custom Function Loading
# ============================================================================


def _load_user_function(tools_path: Path, function_name: str) -> Callable:
    """
    Load a user-defined function from tools.py.

    Args:
        tools_path: Path to the tools.py file
        function_name: Name of the function to load

    Returns:
        The callable function

    Raises:
        FileNotFoundError: If tools.py doesn't exist
        AttributeError: If function doesn't exist in tools.py
        ImportError: If tools.py has import errors
    """
    if not tools_path.exists():
        raise FileNotFoundError(f"tools.py not found at {tools_path}")

    spec = importlib.util.spec_from_file_location("tools", tools_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {tools_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, function_name):
        raise AttributeError(
            f"Function '{function_name}' not found in {tools_path}"
        )

    return getattr(module, function_name)


async def _execute_user_function(
    func: Callable,
    context_dict: dict[str, Any],
) -> dict[str, Any]:
    """
    Execute a user-defined function.

    The function receives a context dict with:
    - inputs: workflow input values
    - input_data: data from upstream steps
    - config: step config (if any)
    - workflow_id: the run ID

    The function should return a dict with results.

    Args:
        func: The function to execute
        context_dict: Context passed to the function

    Returns:
        Dict with function results
    """
    # Check if function is async or sync
    if asyncio.iscoroutinefunction(func):
        result = await func(context_dict)
    else:
        # Run sync function in executor to not block event loop
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, func, context_dict)

    # Normalize result to dict
    if result is None:
        return {}
    if not isinstance(result, dict):
        return {"result": result}
    return result


# Exit codes for CLI integration
class ExitCode(IntEnum):
    """Exit codes for workflow execution."""

    SUCCESS = 0  # All steps succeeded
    FAILED = 1  # One or more steps failed
    CANCELED = 2  # Workflow canceled
    INTERNAL_ERROR = 3  # Internal executor error


# Workflow status values
WorkflowRunStatus = Literal["pending", "running", "completed", "failed", "canceling", "canceled"]

# Step execution status values
StepExecStatus = Literal["pending", "running", "completed", "failed", "canceled", "skipped"]


@dataclass
class StepResult:
    """
    Result of a single step execution.

    Attributes:
        step_id: Step identifier.
        status: Execution status.
        tool_name: Name of the tool executed.
        output_data: List of output records from the tool.
        error: Error message if step failed.
        error_type: Error classification.
        started_at: ISO timestamp when step started.
        completed_at: ISO timestamp when step completed.
        duration_ms: Execution time in milliseconds.
    """

    step_id: str
    status: StepExecStatus
    tool_name: str
    output_data: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    error_type: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    duration_ms: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "step_id": self.step_id,
            "status": self.status,
            "tool_name": self.tool_name,
            "output_data": self.output_data,
            "error": self.error,
            "error_type": self.error_type,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
        }


@dataclass
class WorkflowResult:
    """
    Result of workflow execution.

    Attributes:
        run_id: Unique workflow run identifier.
        status: Final workflow status.
        step_results: Results for each step (keyed by step_id).
        error: Top-level error message if workflow failed.
        exit_code: Exit code for CLI (0=success, 1=failed, 2=canceled, 3=error).
        started_at: ISO timestamp when workflow started.
        completed_at: ISO timestamp when workflow completed.
        duration_ms: Total execution time in milliseconds.
    """

    run_id: str
    status: WorkflowRunStatus
    step_results: dict[str, StepResult] = field(default_factory=dict)
    error: str | None = None
    exit_code: int = ExitCode.SUCCESS
    started_at: str | None = None
    completed_at: str | None = None
    duration_ms: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "run_id": self.run_id,
            "status": self.status,
            "step_results": {k: v.to_dict() for k, v in self.step_results.items()},
            "error": self.error,
            "exit_code": self.exit_code,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
        }


class WorkflowExecutor:
    """
    Executes workflows asynchronously with support for parallel steps,
    cancellation, and partial failure handling.

    The executor:
    1. Builds execution plan from step dependencies
    2. Executes steps level by level
    3. Runs steps within a level in parallel
    4. Passes outputs between dependent steps (fan-in)
    5. Emits progress events for monitoring

    Usage:
        executor = WorkflowExecutor(workflow, inputs, context)
        result = await executor.run()

        # Or with cancellation support
        executor = WorkflowExecutor(workflow, inputs, context)
        task = asyncio.create_task(executor.run())
        # Later:
        await executor.cancel()
        result = await task
    """

    # Cancellation timeout in seconds
    CANCEL_TIMEOUT = 10.0

    def __init__(
        self,
        workflow: WorkflowDefinition,
        inputs: dict[str, Any],
        context: ToolContext | None = None,
        *,
        continue_on_error: bool = False,
        run_id: str | None = None,
        tools_path: Path | str | None = None,
    ) -> None:
        """
        Initialize the workflow executor.

        Args:
            workflow: Parsed workflow definition.
            inputs: Input values for the workflow (merged with defaults).
            context: Tool execution context.
            continue_on_error: If True, continue workflow on step failure.
                              Failed step's dependents receive empty input.
            run_id: Optional run ID. If not provided, generates a UUID.
            tools_path: Path to tools.py for custom function steps.
                       If None, looks for tools.py in current directory.
        """
        self.workflow = workflow
        self.inputs = inputs
        self.context = context or ToolContext()
        self.continue_on_error = continue_on_error
        self.run_id = run_id or str(uuid.uuid4())
        self.tools_path = Path(tools_path) if tools_path else Path("tools.py")

        # Execution state
        self._status: WorkflowRunStatus = "pending"
        self._step_outputs: dict[str, list[dict[str, Any]]] = {}
        self._step_results: dict[str, StepResult] = {}
        self._running_tasks: dict[str, asyncio.Task[StepResult]] = {}
        self._cancel_event = asyncio.Event()
        self._lock = asyncio.Lock()

    async def run(self) -> WorkflowResult:
        """
        Execute the workflow.

        Returns:
            WorkflowResult with status, step results, and error information.
        """
        started_at = datetime.now(timezone.utc)
        self._status = "running"

        # Emit workflow start event
        self._emit_event(
            step_id="workflow",
            status="running",
            message=f"Workflow {self.workflow.workflow.name} started",
        )

        try:
            # Build execution plan
            plan = build_dag(self.workflow.steps)

            if plan.total_steps == 0:
                # Empty workflow
                self._status = "completed"
                return self._create_result(started_at)

            # Execute level by level
            for level_idx, level in enumerate(plan.levels):
                # Check for cancellation before starting level
                if self._cancel_event.is_set():
                    await self._handle_cancellation(level)
                    return self._create_result(started_at)

                # Execute all steps in this level in parallel
                await self._execute_level(level, level_idx)

                # Check if workflow should stop due to cancellation
                if self._status == "canceling" or self._cancel_event.is_set():
                    # Handle any remaining cancellation
                    if self._status == "canceling":
                        self._status = "canceled"
                    return self._create_result(started_at)

                if self._status == "canceled":
                    return self._create_result(started_at)

                # Check for failures
                failed_steps = [
                    step_id
                    for step_id in level
                    if self._step_results.get(step_id, StepResult(step_id, "pending", "")).status
                    == "failed"
                ]

                if failed_steps and not self.continue_on_error:
                    self._status = "failed"
                    return self._create_result(started_at)

            # All levels completed
            # Check if any step failed
            any_failed = any(r.status == "failed" for r in self._step_results.values())
            self._status = "failed" if any_failed else "completed"

            return self._create_result(started_at)

        except Exception as e:
            # Internal executor error
            logger.exception("Workflow executor error")
            self._status = "failed"
            return self._create_result(started_at, error=f"Internal error: {e}")

    async def cancel(self) -> None:
        """
        Request cancellation of the workflow.

        Sets the workflow to 'canceling' state and signals running tasks to stop.
        The workflow will transition to 'canceled' after running tasks complete
        or timeout.
        """
        async with self._lock:
            if self._status in ("completed", "failed", "canceled"):
                return  # Already terminal

            self._status = "canceling"
            self._cancel_event.set()

            # Emit cancellation event
            self._emit_event(
                step_id="workflow",
                status="running",
                message="Workflow cancellation requested",
                metadata={"canceling": True},
            )

    async def _execute_level(self, level: list[str], level_idx: int) -> None:
        """Execute all steps in a level in parallel."""
        # Create tasks for all steps in the level
        tasks: dict[str, asyncio.Task[StepResult]] = {}

        for step_id in level:
            step_def = self.workflow.steps[step_id]

            # Skip step if a dependency failed and continue_on_error is False
            # (This is handled by workflow stopping, but guard anyway)
            if not self.continue_on_error:
                failed_deps = [
                    dep
                    for dep in step_def.depends_on
                    if self._step_results.get(dep, StepResult(dep, "pending", "")).status
                    == "failed"
                ]
                if failed_deps:
                    # Mark as skipped (should not reach here if continue_on_error=False)
                    self._step_results[step_id] = StepResult(
                        step_id=step_id,
                        status="skipped",
                        tool_name=step_def.type,
                        error=f"Skipped due to failed dependencies: {failed_deps}",
                    )
                    continue

            task = asyncio.create_task(self._execute_step(step_id, step_def))
            tasks[step_id] = task

            async with self._lock:
                self._running_tasks[step_id] = task

        if not tasks:
            return

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        # Process results
        any_canceled = False
        for step_id, result in zip(tasks.keys(), results):
            async with self._lock:
                self._running_tasks.pop(step_id, None)

            if isinstance(result, asyncio.CancelledError):
                any_canceled = True
                self._step_results[step_id] = StepResult(
                    step_id=step_id,
                    status="canceled",
                    tool_name=self.workflow.steps[step_id].type,
                    error="Step canceled",
                )
            elif isinstance(result, Exception):
                self._step_results[step_id] = StepResult(
                    step_id=step_id,
                    status="failed",
                    tool_name=self.workflow.steps[step_id].type,
                    error=str(result),
                    error_type=type(result).__name__,
                )
            else:
                # result is StepResult
                self._step_results[step_id] = result
                if result.status == "completed":
                    self._step_outputs[step_id] = result.output_data
                elif result.status == "canceled":
                    any_canceled = True

        # If any step was canceled and we were canceling, mark as fully canceled
        if any_canceled and self._status == "canceling":
            self._status = "canceled"

    async def _execute_step(self, step_id: str, step_def: StepDef) -> StepResult:
        """Execute a single step."""
        started_at = datetime.now(timezone.utc)
        # Resolve step type aliases (e.g., "llm" -> "batch-llm")
        tool_name = resolve_step_type(step_def.type)

        # Emit step start event
        self._emit_event(
            step_id=step_id,
            status="running",
            message=f"Step {step_id} started (tool={tool_name})",
            metadata={"tool": tool_name},
        )

        try:
            # Build input data from dependencies (fan-in)
            input_data = self._build_input_data(step_def)

            # Interpolate step config with workflow inputs
            workflow_input_names = set(self.workflow.inputs.keys())
            interpolated_config = interpolate_step_config(
                step_def.config,
                self.inputs,
                workflow_input_names=workflow_input_names,
                step_name=step_id,
            )

            # Check for cancellation before executing
            if self._cancel_event.is_set():
                raise ToolCanceledError(tool_name, reason="Workflow canceled")

            # Handle function-type steps differently
            if step_def.type == "function":
                result = await self._execute_function_step(
                    step_id, step_def, input_data, interpolated_config
                )
            else:
                # Build tool parameters
                # Tools receive: input_data (from deps) + config
                params = {
                    "input_data": input_data,
                    **interpolated_config,
                }

                # Execute tool with progress tracking
                def on_progress(event):
                    self._emit_event(
                        step_id=step_id,
                        substep=event.substep,
                        status=event.status,
                        current=event.current,
                        total=event.total,
                        message=event.message,
                        metadata=event.metadata,
                    )

                result = await execute_tool(
                    tool_name, params, self.context, on_progress=on_progress
                )

            completed_at = datetime.now(timezone.utc)
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)

            # Determine step status
            if result.success:
                status: StepExecStatus = "completed"
                error = None
                error_type = None
            else:
                status = "failed"
                error = result.errors[0].message if result.errors else "Unknown error"
                error_type = result.errors[0].error_type if result.errors else "unknown"

            # Emit step complete event
            self._emit_event(
                step_id=step_id,
                status="completed" if result.success else "failed",
                message=f"Step {step_id} {status}" + (f": {error}" if error else ""),
                metadata={
                    "output_count": len(result.data),
                    "error_count": len(result.errors),
                },
            )

            return StepResult(
                step_id=step_id,
                status=status,
                tool_name=tool_name,
                output_data=result.data,
                error=error,
                error_type=error_type,
                started_at=started_at.isoformat(),
                completed_at=completed_at.isoformat(),
                duration_ms=duration_ms,
            )

        except asyncio.CancelledError:
            # Task was canceled
            completed_at = datetime.now(timezone.utc)
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)

            self._emit_event(
                step_id=step_id,
                status="failed",
                message=f"Step {step_id} canceled",
            )

            return StepResult(
                step_id=step_id,
                status="canceled",
                tool_name=tool_name,
                error="Step canceled",
                started_at=started_at.isoformat(),
                completed_at=completed_at.isoformat(),
                duration_ms=duration_ms,
            )

        except ToolCanceledError as e:
            # Tool was canceled
            completed_at = datetime.now(timezone.utc)
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)

            self._emit_event(
                step_id=step_id,
                status="failed",
                message=f"Step {step_id} canceled: {e.reason or 'No reason'}",
            )

            return StepResult(
                step_id=step_id,
                status="canceled",
                tool_name=tool_name,
                error=str(e),
                error_type="ToolCanceledError",
                started_at=started_at.isoformat(),
                completed_at=completed_at.isoformat(),
                duration_ms=duration_ms,
            )

        except ToolError as e:
            # Tool execution error
            completed_at = datetime.now(timezone.utc)
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)

            self._emit_event(
                step_id=step_id,
                status="failed",
                message=f"Step {step_id} failed: {e.message}",
                metadata=e.details,
            )

            return StepResult(
                step_id=step_id,
                status="failed",
                tool_name=tool_name,
                error=e.message,
                error_type=type(e).__name__,
                started_at=started_at.isoformat(),
                completed_at=completed_at.isoformat(),
                duration_ms=duration_ms,
            )

        except Exception as e:
            # Unexpected error
            completed_at = datetime.now(timezone.utc)
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)

            logger.exception(f"Step {step_id} failed with unexpected error")

            self._emit_event(
                step_id=step_id,
                status="failed",
                message=f"Step {step_id} failed: {e}",
            )

            return StepResult(
                step_id=step_id,
                status="failed",
                tool_name=tool_name,
                error=str(e),
                error_type=type(e).__name__,
                started_at=started_at.isoformat(),
                completed_at=completed_at.isoformat(),
                duration_ms=duration_ms,
            )

    async def _execute_function_step(
        self,
        step_id: str,
        step_def: StepDef,
        input_data: list[dict[str, Any]],
        config: dict[str, Any],
    ) -> ToolResult:
        """
        Execute a custom function step.

        Loads the function from tools.py and executes it with context.

        Args:
            step_id: Step identifier
            step_def: Step definition (must have function field set)
            input_data: Data from upstream steps
            config: Interpolated step configuration

        Returns:
            ToolResult with function output
        """
        function_name = step_def.function
        if not function_name:
            result = ToolResult(success=False)
            result.add_error(
                error_type="config_error",
                message="Missing function name",
            )
            return result

        # Load the user function
        try:
            func = _load_user_function(self.tools_path, function_name)
        except FileNotFoundError as e:
            result = ToolResult(success=False)
            result.add_error(
                error_type="file_not_found",
                message=str(e),
            )
            return result
        except AttributeError as e:
            result = ToolResult(success=False)
            result.add_error(
                error_type="function_not_found",
                message=str(e),
            )
            return result
        except Exception as e:
            result = ToolResult(success=False)
            result.add_error(
                error_type="import_error",
                message=f"Failed to load function: {e}",
            )
            return result

        # Build context for the function
        context_dict = {
            "inputs": self.inputs,
            "input_data": input_data,
            "config": config,
            "workflow_id": self.run_id,
            "step_id": step_id,
        }

        # Execute the function
        try:
            output = await _execute_user_function(func, context_dict)

            # Emit progress event
            self._emit_event(
                step_id=step_id,
                status="completed",
                message=f"Function {function_name} completed",
                metadata={"function": function_name},
            )

            # Wrap output in list if needed (tools return list of records)
            output_data = [output] if output else []

            return ToolResult(success=True, data=output_data)

        except Exception as e:
            self._emit_event(
                step_id=step_id,
                status="failed",
                message=f"Function {function_name} failed: {e}",
                metadata={"function": function_name, "error": str(e)},
            )
            result = ToolResult(success=False)
            result.add_error(
                error_type="function_error",
                message=str(e),
            )
            return result

    def _build_input_data(self, step_def: StepDef) -> list[dict[str, Any]]:
        """
        Build input data for a step from its dependencies.

        Fan-in: Concatenate outputs from all dependencies in depends_on order.
        First step (no dependencies) gets workflow inputs as single-item list.

        If a dependency failed and continue_on_error is True, that dependency
        contributes nothing (not an empty list, just no items).
        """
        if not step_def.depends_on:
            # First step: input_data is workflow inputs as single record
            return [self.inputs] if self.inputs else []

        # Fan-in: concatenate outputs from dependencies in order
        input_data: list[dict[str, Any]] = []
        for dep in step_def.depends_on:
            dep_output = self._step_outputs.get(dep, [])
            input_data.extend(dep_output)

        return input_data

    async def _handle_cancellation(self, pending_level: list[str]) -> None:
        """Handle cancellation: cancel running tasks, skip pending steps."""
        # Cancel all running tasks
        async with self._lock:
            tasks_to_cancel = list(self._running_tasks.items())

        for step_id, task in tasks_to_cancel:
            if not task.done():
                task.cancel()

        # Wait for tasks to complete (with timeout)
        if tasks_to_cancel:
            try:
                await asyncio.wait_for(
                    asyncio.gather(
                        *[t for _, t in tasks_to_cancel], return_exceptions=True
                    ),
                    timeout=self.CANCEL_TIMEOUT,
                )
            except asyncio.TimeoutError:
                logger.warning("Cancellation timeout - some tasks may still be running")

        # Mark pending steps in current level as canceled
        for step_id in pending_level:
            if step_id not in self._step_results:
                self._step_results[step_id] = StepResult(
                    step_id=step_id,
                    status="canceled",
                    tool_name=self.workflow.steps[step_id].type,
                    error="Step skipped due to workflow cancellation",
                )

        self._status = "canceled"

        # Emit cancellation complete event
        self._emit_event(
            step_id="workflow",
            status="failed",
            message="Workflow canceled",
            metadata={"canceled_steps": pending_level},
        )

    def _create_result(
        self, started_at: datetime, error: str | None = None
    ) -> WorkflowResult:
        """Create the final WorkflowResult."""
        completed_at = datetime.now(timezone.utc)
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)

        # Determine exit code
        if self._status == "completed":
            exit_code = ExitCode.SUCCESS
        elif self._status == "canceled":
            exit_code = ExitCode.CANCELED
        elif error and "Internal error" in error:
            exit_code = ExitCode.INTERNAL_ERROR
        else:
            exit_code = ExitCode.FAILED

        # Emit workflow complete event
        self._emit_event(
            step_id="workflow",
            status="completed" if self._status == "completed" else "failed",
            message=f"Workflow {self._status}" + (f": {error}" if error else ""),
            metadata={
                "status": self._status,
                "exit_code": int(exit_code),
                "duration_ms": duration_ms,
            },
        )

        return WorkflowResult(
            run_id=self.run_id,
            status=self._status,
            step_results=self._step_results,
            error=error,
            exit_code=int(exit_code),
            started_at=started_at.isoformat(),
            completed_at=completed_at.isoformat(),
            duration_ms=duration_ms,
        )

    def _emit_event(
        self,
        step_id: str,
        status: str,
        substep: str | None = None,
        current: int | None = None,
        total: int | None = None,
        message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Emit a progress event via track_event."""
        try:
            track_event(
                run_id=self.run_id,
                step_id=step_id,
                substep=substep,
                status=status,  # type: ignore
                current=current,
                total=total,
                message=message,
                metadata=metadata,
            )
        except Exception:
            # Event tracking should not break execution
            pass


async def execute_workflow(
    workflow: WorkflowDefinition,
    inputs: dict[str, Any],
    context: ToolContext | None = None,
    *,
    continue_on_error: bool = False,
    run_id: str | None = None,
    tools_path: Path | str | None = None,
) -> WorkflowResult:
    """
    Execute a workflow with the given inputs.

    This is the main entry point for workflow execution. It:
    1. Builds an execution plan using build_dag()
    2. Executes steps level by level using asyncio.gather for parallel steps
    3. Calls execute_tool() for each step (or user function for type=function)
    4. Handles cancellation and partial failure
    5. Emits progress events via track_event()

    Args:
        workflow: Parsed workflow definition.
        inputs: Input values for the workflow. Must include all required inputs.
        context: Optional tool execution context.
        continue_on_error: If True, continue workflow on step failure.
                          Failed step's dependents receive empty input.
        run_id: Optional run ID. If not provided, generates a UUID.
        tools_path: Path to tools.py for custom function steps.
                   If None, looks for tools.py in current directory.

    Returns:
        WorkflowResult with:
        - run_id: Unique identifier for this run
        - status: Final status (completed, failed, canceled)
        - step_results: Results for each step
        - error: Error message if workflow failed
        - exit_code: CLI exit code (0=success, 1=failed, 2=canceled, 3=error)

    Example:
        from kurt.workflows.toml import parse_workflow, execute_workflow
        from kurt.tools import load_tool_context

        workflow = parse_workflow("workflows/pipeline.toml")
        context = load_tool_context()
        inputs = {"url": "https://example.com", "max_pages": 100}

        result = await execute_workflow(workflow, inputs, context)
        print(f"Status: {result.status}")
        print(f"Exit code: {result.exit_code}")
    """
    executor = WorkflowExecutor(
        workflow=workflow,
        inputs=inputs,
        context=context,
        continue_on_error=continue_on_error,
        run_id=run_id,
        tools_path=tools_path,
    )
    return await executor.run()

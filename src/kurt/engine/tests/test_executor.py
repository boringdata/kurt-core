"""
Tests for the async workflow executor.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kurt.engine.executor import (
    ExitCode,
    StepResult,
    WorkflowExecutor,
    WorkflowResult,
    execute_workflow,
)
from kurt.engine.parser import InputDef, StepDef, WorkflowDefinition, WorkflowMeta
from kurt.tools.base import ToolContext, ToolResult, ToolResultError
from kurt.tools.errors import ToolExecutionError, ToolNotFoundError


# ============================================================================
# Helper Functions
# ============================================================================


def make_workflow(
    name: str = "test_workflow",
    inputs: dict[str, InputDef] | None = None,
    steps: dict[str, StepDef] | None = None,
) -> WorkflowDefinition:
    """Create a WorkflowDefinition for testing."""
    return WorkflowDefinition(
        workflow=WorkflowMeta(name=name),
        inputs=inputs or {},
        steps=steps or {},
    )


def make_step(
    step_type: str = "map",
    depends_on: list[str] | None = None,
    config: dict[str, Any] | None = None,
    continue_on_error: bool = False,
) -> StepDef:
    """Create a StepDef for testing."""
    return StepDef(
        type=step_type,
        depends_on=depends_on or [],
        config=config or {},
        continue_on_error=continue_on_error,
    )


def make_tool_result(
    success: bool = True,
    data: list[dict[str, Any]] | None = None,
    errors: list[ToolResultError] | None = None,
) -> ToolResult:
    """Create a ToolResult for testing."""
    return ToolResult(
        success=success,
        data=data or [],
        errors=errors or [],
    )


# ============================================================================
# WorkflowResult Tests
# ============================================================================


class TestWorkflowResult:
    """Tests for WorkflowResult dataclass."""

    def test_default_values(self):
        """WorkflowResult has sensible defaults."""
        result = WorkflowResult(run_id="test-123", status="completed")

        assert result.run_id == "test-123"
        assert result.status == "completed"
        assert result.step_results == {}
        assert result.error is None
        assert result.exit_code == ExitCode.SUCCESS

    def test_to_dict(self):
        """WorkflowResult serializes to dict correctly."""
        result = WorkflowResult(
            run_id="test-123",
            status="failed",
            error="Something went wrong",
            exit_code=ExitCode.FAILED,
        )

        d = result.to_dict()

        assert d["run_id"] == "test-123"
        assert d["status"] == "failed"
        assert d["error"] == "Something went wrong"
        assert d["exit_code"] == 1


class TestStepResult:
    """Tests for StepResult dataclass."""

    def test_default_values(self):
        """StepResult has sensible defaults."""
        result = StepResult(step_id="step1", status="completed", tool_name="map")

        assert result.step_id == "step1"
        assert result.status == "completed"
        assert result.tool_name == "map"
        assert result.output_data == []
        assert result.error is None

    def test_to_dict(self):
        """StepResult serializes to dict correctly."""
        result = StepResult(
            step_id="step1",
            status="failed",
            tool_name="fetch",
            error="Timeout",
            error_type="TimeoutError",
        )

        d = result.to_dict()

        assert d["step_id"] == "step1"
        assert d["status"] == "failed"
        assert d["tool_name"] == "fetch"
        assert d["error"] == "Timeout"
        assert d["error_type"] == "TimeoutError"


# ============================================================================
# Empty Workflow Tests
# ============================================================================


class TestExecuteWorkflowEmpty:
    """Tests for empty workflows."""

    @pytest.mark.asyncio
    async def test_empty_workflow(self):
        """Empty workflow completes successfully."""
        workflow = make_workflow(steps={})

        result = await execute_workflow(workflow, {})

        assert result.status == "completed"
        assert result.exit_code == ExitCode.SUCCESS
        assert result.step_results == {}


# ============================================================================
# Single Step Tests
# ============================================================================


class TestExecuteWorkflowSingleStep:
    """Tests for single-step workflows."""

    @pytest.mark.asyncio
    async def test_single_step_success(self):
        """Single successful step."""
        workflow = make_workflow(
            steps={"step1": make_step("map")}
        )

        mock_result = make_tool_result(
            success=True, data=[{"url": "https://example.com"}]
        )

        with patch(
            "kurt.engine.executor.execute_tool", new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.return_value = mock_result

            result = await execute_workflow(workflow, {})

        assert result.status == "completed"
        assert result.exit_code == ExitCode.SUCCESS
        assert "step1" in result.step_results
        assert result.step_results["step1"].status == "completed"
        assert result.step_results["step1"].output_data == [{"url": "https://example.com"}]

    @pytest.mark.asyncio
    async def test_single_step_failure(self):
        """Single failing step."""
        workflow = make_workflow(
            steps={"step1": make_step("map")}
        )

        mock_result = make_tool_result(
            success=False,
            errors=[ToolResultError(row_idx=None, error_type="fetch_error", message="Network error")],
        )

        with patch(
            "kurt.engine.executor.execute_tool", new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.return_value = mock_result

            result = await execute_workflow(workflow, {})

        assert result.status == "failed"
        assert result.exit_code == ExitCode.FAILED
        assert result.step_results["step1"].status == "failed"
        assert result.step_results["step1"].error == "Network error"

    @pytest.mark.asyncio
    async def test_single_step_tool_exception(self):
        """Tool raises exception."""
        workflow = make_workflow(
            steps={"step1": make_step("map")}
        )

        with patch(
            "kurt.engine.executor.execute_tool", new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.side_effect = ToolExecutionError("map", "Connection refused")

            result = await execute_workflow(workflow, {})

        assert result.status == "failed"
        assert result.exit_code == ExitCode.FAILED
        assert result.step_results["step1"].status == "failed"
        assert "Connection refused" in result.step_results["step1"].error

    @pytest.mark.asyncio
    async def test_single_step_tool_not_found(self):
        """Tool not found in registry."""
        workflow = make_workflow(
            steps={"step1": make_step("nonexistent")}
        )

        with patch(
            "kurt.engine.executor.execute_tool", new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.side_effect = ToolNotFoundError("nonexistent")

            result = await execute_workflow(workflow, {})

        assert result.status == "failed"
        assert "step1" in result.step_results
        assert result.step_results["step1"].status == "failed"


# ============================================================================
# Sequential Steps Tests
# ============================================================================


class TestExecuteWorkflowSequential:
    """Tests for sequential (dependent) steps."""

    @pytest.mark.asyncio
    async def test_two_sequential_steps(self):
        """Two dependent steps execute in order."""
        workflow = make_workflow(
            steps={
                "fetch": make_step("fetch"),
                "process": make_step("llm", depends_on=["fetch"]),
            }
        )

        call_order = []

        async def mock_execute(name, params, context=None, on_progress=None):
            call_order.append(name)
            return make_tool_result(success=True, data=[{"processed": True}])

        with patch(
            "kurt.engine.executor.execute_tool", side_effect=mock_execute
        ):
            result = await execute_workflow(workflow, {})

        assert result.status == "completed"
        assert call_order == ["fetch", "llm"]

    @pytest.mark.asyncio
    async def test_data_passes_between_steps(self):
        """Output from first step is input to second step."""
        workflow = make_workflow(
            steps={
                "fetch": make_step("fetch"),
                "process": make_step("llm", depends_on=["fetch"]),
            }
        )

        captured_params = {}

        async def mock_execute(name, params, context=None, on_progress=None):
            captured_params[name] = params.copy()
            if name == "fetch":
                return make_tool_result(success=True, data=[{"url": "https://example.com"}])
            else:
                return make_tool_result(success=True, data=[{"result": "processed"}])

        with patch(
            "kurt.engine.executor.execute_tool", side_effect=mock_execute
        ):
            result = await execute_workflow(workflow, {"query": "test"})

        # First step gets workflow inputs
        assert captured_params["fetch"]["input_data"] == [{"query": "test"}]

        # Second step gets output from first step
        assert captured_params["llm"]["input_data"] == [{"url": "https://example.com"}]


# ============================================================================
# Parallel Steps Tests
# ============================================================================


class TestExecuteWorkflowParallel:
    """Tests for parallel step execution."""

    @pytest.mark.asyncio
    async def test_parallel_steps_execute_concurrently(self):
        """Steps in same level execute in parallel."""
        workflow = make_workflow(
            steps={
                "step_a": make_step("map"),
                "step_b": make_step("fetch"),
                "step_c": make_step("llm"),
            }
        )

        # Track concurrent execution
        active_tasks = 0
        max_concurrent = 0

        async def mock_execute(name, params, context=None, on_progress=None):
            nonlocal active_tasks, max_concurrent
            active_tasks += 1
            max_concurrent = max(max_concurrent, active_tasks)
            await asyncio.sleep(0.01)  # Simulate work
            active_tasks -= 1
            return make_tool_result(success=True, data=[{"step": name}])

        with patch(
            "kurt.engine.executor.execute_tool", side_effect=mock_execute
        ):
            result = await execute_workflow(workflow, {})

        assert result.status == "completed"
        # All three steps should run concurrently
        assert max_concurrent == 3

    @pytest.mark.asyncio
    async def test_diamond_pattern_execution(self):
        """Diamond pattern: fan-out then fan-in."""
        #     source
        #    /      \
        #  left    right
        #    \      /
        #     merge
        workflow = make_workflow(
            steps={
                "source": make_step("map"),
                "left": make_step("fetch", depends_on=["source"]),
                "right": make_step("llm", depends_on=["source"]),
                "merge": make_step("sql", depends_on=["left", "right"]),
            }
        )

        execution_order = []

        async def mock_execute(name, params, context=None, on_progress=None):
            execution_order.append(name)
            await asyncio.sleep(0.01)
            return make_tool_result(success=True, data=[{"from": name}])

        with patch(
            "kurt.engine.executor.execute_tool", side_effect=mock_execute
        ):
            result = await execute_workflow(workflow, {})

        assert result.status == "completed"
        # source must be first, merge must be last
        assert execution_order[0] == "map"
        assert execution_order[-1] == "sql"
        # left and right can be in any order but between source and merge
        assert set(execution_order[1:3]) == {"fetch", "llm"}


# ============================================================================
# Fan-In Tests
# ============================================================================


class TestExecuteWorkflowFanIn:
    """Tests for fan-in (multiple dependencies)."""

    @pytest.mark.asyncio
    async def test_fan_in_concatenates_outputs(self):
        """Fan-in step receives concatenated outputs in depends_on order."""
        workflow = make_workflow(
            steps={
                "source_a": make_step("map"),
                "source_b": make_step("fetch"),
                "merge": make_step("sql", depends_on=["source_a", "source_b"]),
            }
        )

        captured_params = {}

        async def mock_execute(name, params, context=None, on_progress=None):
            captured_params[name] = params.copy()
            if name == "map":
                return make_tool_result(success=True, data=[{"a": 1}, {"a": 2}])
            elif name == "fetch":
                return make_tool_result(success=True, data=[{"b": 3}])
            else:
                return make_tool_result(success=True, data=[])

        with patch(
            "kurt.engine.executor.execute_tool", side_effect=mock_execute
        ):
            result = await execute_workflow(workflow, {})

        assert result.status == "completed"
        # Fan-in: outputs concatenated in depends_on order
        assert captured_params["sql"]["input_data"] == [{"a": 1}, {"a": 2}, {"b": 3}]

    @pytest.mark.asyncio
    async def test_fan_in_empty_outputs_contribute_nothing(self):
        """Dependencies with empty output contribute nothing to fan-in."""
        workflow = make_workflow(
            steps={
                "source_a": make_step("map"),
                "source_b": make_step("fetch"),
                "merge": make_step("sql", depends_on=["source_a", "source_b"]),
            }
        )

        captured_params = {}

        async def mock_execute(name, params, context=None, on_progress=None):
            captured_params[name] = params.copy()
            if name == "map":
                return make_tool_result(success=True, data=[{"a": 1}])
            elif name == "fetch":
                return make_tool_result(success=True, data=[])  # Empty output
            else:
                return make_tool_result(success=True, data=[])

        with patch(
            "kurt.engine.executor.execute_tool", side_effect=mock_execute
        ):
            result = await execute_workflow(workflow, {})

        assert result.status == "completed"
        # Fan-in: source_b contributes nothing
        assert captured_params["sql"]["input_data"] == [{"a": 1}]


# ============================================================================
# Partial Failure Tests
# ============================================================================


class TestExecuteWorkflowPartialFailure:
    """Tests for partial failure handling."""

    @pytest.mark.asyncio
    async def test_default_stops_on_failure(self):
        """Default behavior: workflow stops on first step failure."""
        workflow = make_workflow(
            steps={
                "step1": make_step("map"),
                "step2": make_step("fetch", depends_on=["step1"]),
            }
        )

        async def mock_execute(name, params, context=None, on_progress=None):
            if name == "map":
                return make_tool_result(
                    success=False,
                    errors=[ToolResultError(None, "error", "Step 1 failed")],
                )
            return make_tool_result(success=True)

        with patch(
            "kurt.engine.executor.execute_tool", side_effect=mock_execute
        ):
            result = await execute_workflow(workflow, {})

        assert result.status == "failed"
        assert result.step_results["step1"].status == "failed"
        # Step 2 should not have run
        assert "step2" not in result.step_results or result.step_results.get("step2") is None

    @pytest.mark.asyncio
    async def test_continue_on_error_proceeds(self):
        """With continue_on_error=True, workflow continues after failure."""
        workflow = make_workflow(
            steps={
                "step1": make_step("map"),
                "step2": make_step("fetch"),  # No dependency, runs in parallel
            }
        )

        async def mock_execute(name, params, context=None, on_progress=None):
            if name == "map":
                return make_tool_result(
                    success=False,
                    errors=[ToolResultError(None, "error", "Step 1 failed")],
                )
            return make_tool_result(success=True, data=[{"result": "ok"}])

        with patch(
            "kurt.engine.executor.execute_tool", side_effect=mock_execute
        ):
            result = await execute_workflow(workflow, {}, continue_on_error=True)

        # Workflow fails overall but step2 still ran
        assert result.status == "failed"
        assert result.step_results["step1"].status == "failed"
        assert result.step_results["step2"].status == "completed"

    @pytest.mark.asyncio
    async def test_continue_on_error_dependent_gets_empty_input(self):
        """With continue_on_error, dependent of failed step gets empty input."""
        workflow = make_workflow(
            steps={
                "step1": make_step("map"),
                "step2": make_step("fetch", depends_on=["step1"]),
            }
        )

        captured_params = {}

        async def mock_execute(name, params, context=None, on_progress=None):
            captured_params[name] = params.copy()
            if name == "map":
                return make_tool_result(
                    success=False,
                    errors=[ToolResultError(None, "error", "Step 1 failed")],
                )
            return make_tool_result(success=True, data=[{"result": "ok"}])

        with patch(
            "kurt.engine.executor.execute_tool", side_effect=mock_execute
        ):
            result = await execute_workflow(workflow, {}, continue_on_error=True)

        assert result.status == "failed"
        # Step 2 should have received empty input (failed step contributes nothing)
        assert captured_params["fetch"]["input_data"] == []


# ============================================================================
# Cancellation Tests
# ============================================================================


class TestExecuteWorkflowCancellation:
    """Tests for workflow cancellation."""

    @pytest.mark.asyncio
    async def test_cancel_before_start(self):
        """Canceling before execution starts."""
        workflow = make_workflow(
            steps={"step1": make_step("map")}
        )

        executor = WorkflowExecutor(workflow, {})
        await executor.cancel()  # Cancel before run

        # Should not actually execute anything since we didn't call run()
        # But this tests the cancel method can be called safely

    @pytest.mark.asyncio
    async def test_cancel_during_execution(self):
        """Canceling during execution."""
        workflow = make_workflow(
            steps={
                "slow_step": make_step("map"),
                "after_slow": make_step("fetch", depends_on=["slow_step"]),
            }
        )

        execution_started = asyncio.Event()
        can_complete = asyncio.Event()

        async def mock_execute(name, params, context=None, on_progress=None):
            if name == "map":
                execution_started.set()
                # Wait until canceled or allowed to complete
                try:
                    await asyncio.wait_for(can_complete.wait(), timeout=10)
                except asyncio.TimeoutError:
                    pass
                # Check if we were canceled
                raise asyncio.CancelledError()
            return make_tool_result(success=True)

        with patch(
            "kurt.engine.executor.execute_tool", side_effect=mock_execute
        ):
            executor = WorkflowExecutor(workflow, {})

            # Start execution in background
            task = asyncio.create_task(executor.run())

            # Wait for execution to start
            await asyncio.wait_for(execution_started.wait(), timeout=1.0)

            # Request cancellation
            await executor.cancel()

            # Allow the mock to complete (it will raise CancelledError)
            can_complete.set()

            # Wait for result
            result = await asyncio.wait_for(task, timeout=5.0)

        assert result.status == "canceled"
        assert result.exit_code == ExitCode.CANCELED

    @pytest.mark.asyncio
    async def test_cancel_marks_pending_as_canceled(self):
        """Pending steps are marked as canceled."""
        workflow = make_workflow(
            steps={
                "step1": make_step("map"),
                "step2": make_step("fetch", depends_on=["step1"]),
                "step3": make_step("llm", depends_on=["step2"]),
            }
        )

        step1_started = asyncio.Event()
        can_complete = asyncio.Event()

        async def mock_execute(name, params, context=None, on_progress=None):
            if name == "map":
                step1_started.set()
                # Wait until canceled
                try:
                    await asyncio.wait_for(can_complete.wait(), timeout=10)
                except asyncio.TimeoutError:
                    pass
                raise asyncio.CancelledError()
            return make_tool_result(success=True)

        with patch(
            "kurt.engine.executor.execute_tool", side_effect=mock_execute
        ):
            executor = WorkflowExecutor(workflow, {})
            task = asyncio.create_task(executor.run())

            await asyncio.wait_for(step1_started.wait(), timeout=1.0)
            await executor.cancel()
            can_complete.set()

            result = await asyncio.wait_for(task, timeout=5.0)

        assert result.status == "canceled"
        # Step 1 should be canceled (was running)
        assert result.step_results["step1"].status == "canceled"


# ============================================================================
# Input Interpolation Tests
# ============================================================================


class TestExecuteWorkflowInputs:
    """Tests for input handling and interpolation."""

    @pytest.mark.asyncio
    async def test_inputs_passed_to_first_step(self):
        """Workflow inputs are passed to first step."""
        workflow = make_workflow(
            inputs={"url": InputDef(type="string", required=True)},
            steps={"step1": make_step("map")},
        )

        captured_params = {}

        async def mock_execute(name, params, context=None, on_progress=None):
            captured_params[name] = params.copy()
            return make_tool_result(success=True)

        with patch(
            "kurt.engine.executor.execute_tool", side_effect=mock_execute
        ):
            await execute_workflow(workflow, {"url": "https://example.com"})

        assert captured_params["map"]["input_data"] == [{"url": "https://example.com"}]

    @pytest.mark.asyncio
    async def test_config_interpolation(self):
        """Step config values are interpolated with inputs."""
        workflow = make_workflow(
            inputs={"model": InputDef(type="string", required=True)},
            steps={
                "step1": make_step(
                    "llm",
                    config={"model": "{{model}}", "temperature": 0.7},
                )
            },
        )

        captured_params = {}

        async def mock_execute(name, params, context=None, on_progress=None):
            captured_params[name] = params.copy()
            return make_tool_result(success=True)

        with patch(
            "kurt.engine.executor.execute_tool", side_effect=mock_execute
        ):
            await execute_workflow(workflow, {"model": "gpt-4"})

        assert captured_params["llm"]["model"] == "gpt-4"
        assert captured_params["llm"]["temperature"] == 0.7


# ============================================================================
# Progress Events Tests
# ============================================================================


class TestExecuteWorkflowEvents:
    """Tests for progress event emission."""

    @pytest.mark.asyncio
    async def test_emits_workflow_start_event(self):
        """Workflow emits start event."""
        workflow = make_workflow(
            name="test_workflow",
            steps={"step1": make_step("map")},
        )

        events = []

        def capture_event(*args, **kwargs):
            events.append(kwargs)

        with (
            patch("kurt.engine.executor.execute_tool", new_callable=AsyncMock) as mock_execute,
            patch("kurt.engine.executor.track_event", side_effect=capture_event),
        ):
            mock_execute.return_value = make_tool_result(success=True)
            await execute_workflow(workflow, {})

        # Find workflow start event
        start_events = [e for e in events if e.get("step_id") == "workflow" and e.get("status") == "running"]
        assert len(start_events) >= 1
        assert "test_workflow" in start_events[0].get("message", "")

    @pytest.mark.asyncio
    async def test_emits_step_events(self):
        """Workflow emits step start/complete events."""
        workflow = make_workflow(
            steps={"step1": make_step("map")},
        )

        events = []

        def capture_event(*args, **kwargs):
            events.append(kwargs)

        with (
            patch("kurt.engine.executor.execute_tool", new_callable=AsyncMock) as mock_execute,
            patch("kurt.engine.executor.track_event", side_effect=capture_event),
        ):
            mock_execute.return_value = make_tool_result(success=True)
            await execute_workflow(workflow, {})

        # Find step events
        step_events = [e for e in events if e.get("step_id") == "step1"]
        assert len(step_events) >= 2  # start + complete

        statuses = [e.get("status") for e in step_events]
        assert "running" in statuses
        assert "completed" in statuses


# ============================================================================
# Exit Code Tests
# ============================================================================


class TestExecuteWorkflowExitCodes:
    """Tests for exit codes."""

    @pytest.mark.asyncio
    async def test_success_exit_code(self):
        """Successful workflow has exit code 0."""
        workflow = make_workflow(steps={"step1": make_step("map")})

        with patch(
            "kurt.engine.executor.execute_tool", new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.return_value = make_tool_result(success=True)
            result = await execute_workflow(workflow, {})

        assert result.exit_code == ExitCode.SUCCESS
        assert result.exit_code == 0

    @pytest.mark.asyncio
    async def test_failed_exit_code(self):
        """Failed workflow has exit code 1."""
        workflow = make_workflow(steps={"step1": make_step("map")})

        with patch(
            "kurt.engine.executor.execute_tool", new_callable=AsyncMock
        ) as mock_execute:
            mock_execute.return_value = make_tool_result(
                success=False,
                errors=[ToolResultError(None, "error", "Failed")],
            )
            result = await execute_workflow(workflow, {})

        assert result.exit_code == ExitCode.FAILED
        assert result.exit_code == 1

    @pytest.mark.asyncio
    async def test_canceled_exit_code(self):
        """Canceled workflow has exit code 2."""
        workflow = make_workflow(
            steps={"step1": make_step("map")},
        )

        started = asyncio.Event()
        can_complete = asyncio.Event()

        async def slow_execute(*args, **kwargs):
            started.set()
            try:
                await asyncio.wait_for(can_complete.wait(), timeout=10)
            except asyncio.TimeoutError:
                pass
            raise asyncio.CancelledError()

        with patch(
            "kurt.engine.executor.execute_tool", side_effect=slow_execute
        ):
            executor = WorkflowExecutor(workflow, {})
            task = asyncio.create_task(executor.run())

            await asyncio.wait_for(started.wait(), timeout=1.0)
            await executor.cancel()
            can_complete.set()

            result = await asyncio.wait_for(task, timeout=5.0)

        assert result.exit_code == ExitCode.CANCELED
        assert result.exit_code == 2


# ============================================================================
# Run ID Tests
# ============================================================================


class TestExecuteWorkflowRunId:
    """Tests for run ID handling."""

    @pytest.mark.asyncio
    async def test_generates_run_id(self):
        """Workflow generates a run ID if not provided."""
        workflow = make_workflow(steps={})

        result = await execute_workflow(workflow, {})

        assert result.run_id is not None
        assert len(result.run_id) > 0

    @pytest.mark.asyncio
    async def test_uses_provided_run_id(self):
        """Workflow uses provided run ID."""
        workflow = make_workflow(steps={})

        result = await execute_workflow(workflow, {}, run_id="custom-run-123")

        assert result.run_id == "custom-run-123"


# ============================================================================
# Context Tests
# ============================================================================


class TestExecuteWorkflowContext:
    """Tests for tool context handling."""

    @pytest.mark.asyncio
    async def test_passes_context_to_tool(self):
        """Workflow passes context to tool execution."""
        workflow = make_workflow(steps={"step1": make_step("map")})
        context = ToolContext(settings={"custom": "value"})

        captured_context = None

        async def mock_execute(name, params, ctx=None, on_progress=None):
            nonlocal captured_context
            captured_context = ctx
            return make_tool_result(success=True)

        with patch(
            "kurt.engine.executor.execute_tool", side_effect=mock_execute
        ):
            await execute_workflow(workflow, {}, context=context)

        assert captured_context is context
        assert captured_context.settings["custom"] == "value"

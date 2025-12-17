"""Tests for run_pipeline parallel execution.

Verifies that:
1. DAG ordering is respected (dependencies execute before dependents)
2. Independent models within a level run in parallel
3. Errors are handled correctly
"""

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

from kurt.content.filtering import DocumentFilters
from kurt.core import (
    PipelineConfig,
    PipelineContext,
    WorkflowDocumentRef,
    WorkflowStepError,
)
from kurt.core.model_runner import run_pipeline
from kurt.core.registry import ModelRegistry

logger = logging.getLogger(__name__)


# ============================================================================
# Test fixtures and helpers
# ============================================================================

# Track execution order and timing
execution_log: List[Dict[str, Any]] = []


def reset_execution_log():
    """Reset execution log between tests."""
    global execution_log
    execution_log = []


def log_execution(model_name: str, action: str):
    """Log model execution with timestamp."""
    execution_log.append(
        {
            "model": model_name,
            "action": action,
            "time": time.time(),
        }
    )
    logger.info(f"[{time.time():.3f}] {model_name}: {action}")


@dataclass
class MockRow:
    """Mock row for test models."""

    id: str
    data: str


def create_mock_model(model_name: str, sleep_time: float = 0.5):
    """Create a mock model function that logs execution and sleeps."""

    def model_func(ctx, reader=None, writer=None, **kwargs):
        log_execution(model_name, "start")
        time.sleep(sleep_time)
        log_execution(model_name, "end")
        return {"rows_written": 1, "model": model_name}

    return model_func


# ============================================================================
# Tests
# ============================================================================


class TestRunPipelineParallel:
    """Test run_pipeline parallel execution."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Reset state before each test."""
        reset_execution_log()
        # Clear any test models from registry
        ModelRegistry._models = {
            k: v for k, v in ModelRegistry._models.items() if not k.startswith("test.")
        }

    @pytest.fixture
    def mock_ctx(self):
        """Create mock pipeline context."""
        return PipelineContext(
            filters=DocumentFilters(),
            workflow_id="test-parallel-workflow",
            incremental_mode="full",
        )

    def register_test_models(self, models_config: Dict[str, Dict]):
        """Register test models with specified dependencies.

        Args:
            models_config: Dict of model_name -> {
                "dependencies": list of model names this depends on,
                "sleep_time": how long the model takes to run
            }
        """
        from kurt.core.references import Reference

        for model_name, config in models_config.items():
            deps = config.get("dependencies", [])
            sleep_time = config.get("sleep_time", 0.5)

            # Build references dict
            references = {}
            for i, dep in enumerate(deps):
                ref = Reference(model_name=dep)
                references[f"dep_{i}"] = ref

            # Register the model
            ModelRegistry._models[model_name] = {
                "function": create_mock_model(model_name, sleep_time),
                "references": references,
                "table_name": model_name.replace(".", "_"),
                "description": f"Test model {model_name}",
            }

    @pytest.mark.asyncio
    async def test_sequential_ordering(self, mock_ctx):
        """Test that models with dependencies run after their dependencies."""
        # Register models: A -> B -> C (linear chain)
        self.register_test_models(
            {
                "test.model_a": {"dependencies": [], "sleep_time": 0.2},
                "test.model_b": {"dependencies": ["test.model_a"], "sleep_time": 0.2},
                "test.model_c": {"dependencies": ["test.model_b"], "sleep_time": 0.2},
            }
        )

        pipeline = PipelineConfig(
            name="test_sequential",
            models=["test.model_a", "test.model_b", "test.model_c"],
        )

        with patch("kurt.core.model_runner.DBOS") as mock_dbos:
            # Make DBOS.step() return the function directly (no-op decorator)
            mock_dbos.step.return_value = lambda fn: fn

            result = await run_pipeline(pipeline, mock_ctx)

        # Verify all models executed
        assert len(result["models_executed"]) == 3
        assert "test.model_a" in result["models_executed"]
        assert "test.model_b" in result["models_executed"]
        assert "test.model_c" in result["models_executed"]

        # Verify ordering: A finished before B started, B finished before C started
        a_end = next(
            e["time"]
            for e in execution_log
            if e["model"] == "test.model_a" and e["action"] == "end"
        )
        b_start = next(
            e["time"]
            for e in execution_log
            if e["model"] == "test.model_b" and e["action"] == "start"
        )
        b_end = next(
            e["time"]
            for e in execution_log
            if e["model"] == "test.model_b" and e["action"] == "end"
        )
        c_start = next(
            e["time"]
            for e in execution_log
            if e["model"] == "test.model_c" and e["action"] == "start"
        )

        assert a_end <= b_start, "Model B should start after A ends"
        assert b_end <= c_start, "Model C should start after B ends"

    @pytest.mark.asyncio
    async def test_parallel_execution(self, mock_ctx):
        """Test that independent models run in parallel."""
        # Register models: A and B are independent, C depends on both
        # DAG:  A ──┐
        #          ├──> C
        #       B ──┘
        self.register_test_models(
            {
                "test.model_a": {"dependencies": [], "sleep_time": 0.5},
                "test.model_b": {"dependencies": [], "sleep_time": 0.5},
                "test.model_c": {
                    "dependencies": ["test.model_a", "test.model_b"],
                    "sleep_time": 0.2,
                },
            }
        )

        pipeline = PipelineConfig(
            name="test_parallel",
            models=["test.model_a", "test.model_b", "test.model_c"],
        )

        start_time = time.time()

        with patch("kurt.core.model_runner.DBOS") as mock_dbos:
            mock_dbos.step.return_value = lambda fn: fn

            result = await run_pipeline(pipeline, mock_ctx)

        elapsed = time.time() - start_time

        # Verify all models executed
        assert len(result["models_executed"]) == 3

        # Get timing info
        a_start = next(
            e["time"]
            for e in execution_log
            if e["model"] == "test.model_a" and e["action"] == "start"
        )
        b_start = next(
            e["time"]
            for e in execution_log
            if e["model"] == "test.model_b" and e["action"] == "start"
        )

        # A and B should start within 0.1s of each other (parallel)
        start_diff = abs(b_start - a_start)
        logger.info(f"Start diff between A and B: {start_diff:.3f}s")
        assert (
            start_diff < 0.1
        ), f"A and B should start nearly simultaneously, got {start_diff:.3f}s diff"

        # Total time should be ~0.7s (max(0.5, 0.5) + 0.2), not 1.2s (0.5 + 0.5 + 0.2)
        # Allow some margin for test overhead
        logger.info(f"Total elapsed: {elapsed:.2f}s")
        assert (
            elapsed < 1.0
        ), f"Expected parallel execution (~0.7s), got {elapsed:.2f}s (sequential would be ~1.2s)"

    @pytest.mark.asyncio
    async def test_complex_dag(self, mock_ctx):
        """Test a more complex DAG with multiple levels."""
        # DAG:
        #   A ──┐
        #      ├──> D ──┐
        #   B ──┘       │
        #               ├──> F
        #   C ──────────┘
        #
        # Level 1: A, B, C (parallel)
        # Level 2: D (depends on A, B)
        # Level 3: F (depends on D, C - but C is in level 1, so F waits for D)
        self.register_test_models(
            {
                "test.model_a": {"dependencies": [], "sleep_time": 0.3},
                "test.model_b": {"dependencies": [], "sleep_time": 0.3},
                "test.model_c": {"dependencies": [], "sleep_time": 0.3},
                "test.model_d": {
                    "dependencies": ["test.model_a", "test.model_b"],
                    "sleep_time": 0.3,
                },
                "test.model_f": {
                    "dependencies": ["test.model_d", "test.model_c"],
                    "sleep_time": 0.2,
                },
            }
        )

        pipeline = PipelineConfig(
            name="test_complex",
            models=["test.model_a", "test.model_b", "test.model_c", "test.model_d", "test.model_f"],
        )

        start_time = time.time()

        with patch("kurt.core.model_runner.DBOS") as mock_dbos:
            mock_dbos.step.return_value = lambda fn: fn

            result = await run_pipeline(pipeline, mock_ctx)

        elapsed = time.time() - start_time

        # Verify all models executed
        assert len(result["models_executed"]) == 5

        # Check parallel execution in level 1 (A, B, C)
        a_start = next(
            e["time"]
            for e in execution_log
            if e["model"] == "test.model_a" and e["action"] == "start"
        )
        b_start = next(
            e["time"]
            for e in execution_log
            if e["model"] == "test.model_b" and e["action"] == "start"
        )
        c_start = next(
            e["time"]
            for e in execution_log
            if e["model"] == "test.model_c" and e["action"] == "start"
        )

        # All three should start within 0.1s of each other
        max_start = max(a_start, b_start, c_start)
        min_start = min(a_start, b_start, c_start)
        assert (max_start - min_start) < 0.1, "A, B, C should start in parallel"

        # D should start after A and B finish
        a_end = next(
            e["time"]
            for e in execution_log
            if e["model"] == "test.model_a" and e["action"] == "end"
        )
        b_end = next(
            e["time"]
            for e in execution_log
            if e["model"] == "test.model_b" and e["action"] == "end"
        )
        d_start = next(
            e["time"]
            for e in execution_log
            if e["model"] == "test.model_d" and e["action"] == "start"
        )

        assert d_start >= max(a_end, b_end), "D should start after both A and B finish"

        # Expected time: ~0.3 (level 1) + ~0.3 (level 2: D) + ~0.2 (level 3: F) = ~0.8s
        # Sequential would be: 0.3 * 5 + 0.2 = ~1.7s
        logger.info(f"Complex DAG elapsed: {elapsed:.2f}s")
        assert elapsed < 1.2, f"Expected DAG execution (~0.8s), got {elapsed:.2f}s"

    @pytest.mark.asyncio
    async def test_error_handling_stop_on_error(self, mock_ctx):
        """Test that stop_on_error stops pipeline on first error."""

        def error_model(ctx, reader=None, writer=None, **kwargs):
            log_execution("test.error_model", "start")
            raise ValueError("Intentional test error")

        self.register_test_models(
            {
                "test.model_a": {"dependencies": [], "sleep_time": 0.1},
            }
        )

        # Register error model
        ModelRegistry._models["test.error_model"] = {
            "function": error_model,
            "references": {},
            "table_name": "test_error_model",
            "description": "Error model",
        }

        # Register model that depends on error model
        self.register_test_models(
            {
                "test.model_after": {"dependencies": ["test.error_model"], "sleep_time": 0.1},
            }
        )

        pipeline = PipelineConfig(
            name="test_error",
            models=["test.model_a", "test.error_model", "test.model_after"],
            stop_on_error=True,
        )

        with patch("kurt.core.model_runner.DBOS") as mock_dbos:
            mock_dbos.step.return_value = lambda fn: fn

            result = await run_pipeline(pipeline, mock_ctx)

        # Should have error for error_model
        assert "test.error_model" in result["errors"]
        assert "Intentional test error" in result["errors"]["test.error_model"]

        # model_after should not have executed (stop_on_error=True)
        assert "test.model_after" not in result["models_executed"]

    @pytest.mark.asyncio
    async def test_error_handling_continue_on_error(self, mock_ctx):
        """Test that stop_on_error=False continues after error."""

        def error_model(ctx, reader=None, writer=None, **kwargs):
            log_execution("test.error_model", "start")
            raise ValueError("Intentional test error")

        # A and error_model are independent (same level)
        # After is in next level
        self.register_test_models(
            {
                "test.model_a": {"dependencies": [], "sleep_time": 0.1},
            }
        )

        ModelRegistry._models["test.error_model"] = {
            "function": error_model,
            "references": {},
            "table_name": "test_error_model",
            "description": "Error model",
        }

        self.register_test_models(
            {
                "test.model_after": {"dependencies": ["test.model_a"], "sleep_time": 0.1},
            }
        )

        pipeline = PipelineConfig(
            name="test_continue",
            models=["test.model_a", "test.error_model", "test.model_after"],
            stop_on_error=False,
        )

        with patch("kurt.core.model_runner.DBOS") as mock_dbos:
            mock_dbos.step.return_value = lambda fn: fn

            result = await run_pipeline(pipeline, mock_ctx)

        # Should have error for error_model
        assert "test.error_model" in result["errors"]

        # model_a should have succeeded
        assert "test.model_a" in result["models_executed"]

        # model_after should have executed (stop_on_error=False)
        assert "test.model_after" in result["models_executed"]

    @pytest.mark.asyncio
    async def test_workflow_step_error_fail_model(self, mock_ctx):
        """Test that WorkflowStepError with fail_model action stops the model."""

        def error_model(ctx, reader=None, writer=None, **kwargs):
            log_execution("test.workflow_error_model", "start")
            raise WorkflowStepError(
                step="test.workflow_error_model",
                message="Database constraint violation",
                action="fail_model",
                severity="fatal",
                documents=(WorkflowDocumentRef(entity_name="Python"),),
            )

        self.register_test_models(
            {
                "test.model_a": {"dependencies": [], "sleep_time": 0.1},
            }
        )

        ModelRegistry._models["test.workflow_error_model"] = {
            "function": error_model,
            "references": {},
            "table_name": "test_workflow_error_model",
            "description": "Workflow error model",
        }

        pipeline = PipelineConfig(
            name="test_workflow_error",
            models=["test.model_a", "test.workflow_error_model"],
            stop_on_error=True,
        )

        with patch("kurt.core.model_runner.DBOS") as mock_dbos:
            mock_dbos.step.return_value = lambda fn: fn

            result = await run_pipeline(pipeline, mock_ctx)

        # Should have error for workflow_error_model
        assert "test.workflow_error_model" in result["errors"]

        # The error should be a dict (serialized WorkflowStepError)
        error_data = result["errors"]["test.workflow_error_model"]
        assert isinstance(error_data, dict)
        assert error_data["step"] == "test.workflow_error_model"
        assert error_data["action"] == "fail_model"
        assert error_data["severity"] == "fatal"

    @pytest.mark.asyncio
    async def test_workflow_step_error_structured_in_results(self, mock_ctx):
        """Test that WorkflowStepError payload is stored in results."""

        def error_model(ctx, reader=None, writer=None, **kwargs):
            raise WorkflowStepError(
                step="test.step",
                message="Test error message",
                action="fail_model",
                severity="fatal",
                documents=(
                    WorkflowDocumentRef(document_id="doc1", section_id="sec1"),
                    WorkflowDocumentRef(document_id="doc2"),
                ),
                metadata={"llm_model": "test-model"},
            )

        ModelRegistry._models["test.structured_error"] = {
            "function": error_model,
            "references": {},
            "table_name": "test_structured_error",
            "description": "Structured error model",
        }

        pipeline = PipelineConfig(
            name="test_structured",
            models=["test.structured_error"],
        )

        with patch("kurt.core.model_runner.DBOS") as mock_dbos:
            mock_dbos.step.return_value = lambda fn: fn

            result = await run_pipeline(pipeline, mock_ctx)

        # Verify structured error in errors dict
        assert "test.structured_error" in result["errors"]
        error_payload = result["errors"]["test.structured_error"]

        assert error_payload["step"] == "test.step"
        assert error_payload["message"] == "Test error message"
        assert len(error_payload["documents"]) == 2
        assert error_payload["documents"][0]["document_id"] == "doc1"
        assert error_payload["metadata"]["llm_model"] == "test-model"

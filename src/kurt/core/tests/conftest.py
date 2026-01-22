"""
Root test fixtures for kurt.

Provides isolated database and DBOS state for integration testing.
Pattern adapted from kurt/ testing framework.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable
from unittest.mock import MagicMock

import pandas as pd
import pytest
from click.testing import CliRunner
from pydantic import BaseModel

from kurt.core.llm_step import LLMStep

# ============================================================================
# CLI Testing Fixtures
# ============================================================================


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Click CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def cli_runner_isolated(cli_runner: CliRunner):
    """Create a Click CLI runner with isolated filesystem."""
    with cli_runner.isolated_filesystem():
        yield cli_runner


def invoke_cli(runner: CliRunner, cmd, args: list[str], **kwargs):
    """
    Helper to invoke CLI command.

    Args:
        runner: Click test runner
        cmd: Click command or group
        args: Command arguments
        **kwargs: Additional arguments to runner.invoke()

    Returns:
        Click Result object
    """
    return runner.invoke(cmd, args, catch_exceptions=False, **kwargs)


def assert_cli_success(result, msg: str = None):
    """Assert CLI command succeeded (exit code 0)."""
    if result.exit_code != 0:
        error_msg = f"CLI failed (exit code {result.exit_code})"
        if msg:
            error_msg = f"{msg}: {error_msg}"
        if result.output:
            error_msg += f"\nOutput: {result.output}"
        raise AssertionError(error_msg)


def assert_cli_failure(result, expected_code: int = None, msg: str = None):
    """Assert CLI command failed."""
    if result.exit_code == 0:
        error_msg = "CLI succeeded but expected failure"
        if msg:
            error_msg = f"{msg}: {error_msg}"
        raise AssertionError(error_msg)

    if expected_code is not None and result.exit_code != expected_code:
        raise AssertionError(f"Expected exit code {expected_code}, got {result.exit_code}")


def assert_output_contains(result, text: str):
    """Assert CLI output contains text."""
    if text not in result.output:
        raise AssertionError(f"Expected '{text}' in output.\nActual: {result.output}")


def assert_json_output(result) -> dict:
    """Assert output is valid JSON and return parsed data."""
    import json

    try:
        return json.loads(result.output)
    except json.JSONDecodeError as e:
        raise AssertionError(f"Output is not valid JSON: {e}\nOutput: {result.output}")


# ============================================================================
# DBOS State Management
# ============================================================================


@pytest.fixture
def reset_dbos_state():
    """
    Reset DBOS state between tests to prevent state pollution.

    This fixture ensures each test starts with a clean DBOS state,
    preventing test interference from leftover workflows or queues.
    """

    def _reset():
        try:
            from dbos import DBOS

            if hasattr(DBOS, "_dbos_initialized"):
                DBOS._dbos_initialized = False
            if hasattr(DBOS, "_destroy"):
                try:
                    DBOS._destroy(workflow_completion_timeout_sec=0)
                except Exception:
                    pass

            # Clear DBOS global instance to allow fresh initialization
            try:
                import dbos._dbos as dbos_module

                if hasattr(dbos_module, "_dbos_global_instance"):
                    dbos_module._dbos_global_instance = None
            except Exception:
                pass
        except ImportError:
            pass

        # Also reset kurt's dbos module flag
        try:
            import kurt.core.dbos as kurt_dbos

            kurt_dbos._dbos_initialized = False
        except ImportError:
            pass

    _reset()
    yield
    _reset()


# ============================================================================
# Database Isolation
# ============================================================================


@pytest.fixture
def tmp_database(tmp_path: Path, monkeypatch, reset_dbos_state):
    """
    Create an isolated temporary SQLite database for testing.

    Sets up:
    - Temp directory with .kurt/ structure
    - Fresh SQLite database with migrations
    - Patches environment to use temp database

    Yields:
        Path: The temporary project directory
    """
    # Clear SQLModel metadata to prevent pollution from previous tests
    # This is necessary because SQLModel uses a global MetaData registry
    from sqlmodel import SQLModel

    # Store tables we want to keep (kurt core models)
    from kurt.db.models import register_all_models

    SQLModel.metadata.clear()
    register_all_models()

    # Create .kurt directory structure
    kurt_dir = tmp_path / ".kurt"
    kurt_dir.mkdir(parents=True, exist_ok=True)

    # Patch environment to not use DATABASE_URL (force SQLite)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    # Change to temp directory so SQLiteClient uses it
    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    # Initialize database
    from kurt.db import init_database

    init_database()

    yield tmp_path

    # Restore original directory
    os.chdir(original_cwd)


@pytest.fixture
def tmp_database_with_data(tmp_database: Path):
    """
    Temporary database pre-populated with sample data.

    Useful for testing queries and retrieval operations.
    """
    from kurt.db import managed_session
    from kurt.db.models import LLMTrace

    with managed_session() as session:
        # Add sample LLM traces
        session.add(
            LLMTrace(
                workflow_id="test-workflow-1",
                step_name="extract",
                model="gpt-4",
                provider="openai",
                prompt="Test prompt",
                response="Test response",
                input_tokens=100,
                output_tokens=50,
                total_tokens=150,
                cost=0.01,
                latency_ms=500,
            )
        )

    yield tmp_database


# ============================================================================
# LLM Mocking Fixtures
# ============================================================================


@pytest.fixture
def mock_llm_fn():
    """
    Factory fixture for creating mock LLM functions.

    Returns a factory that creates mock llm_fn callables
    with configurable responses.

    Usage:
        def test_something(mock_llm_fn):
            llm_fn = mock_llm_fn(MyOutputSchema, {"field": "value"})
            step = LLMStep(..., llm_fn=llm_fn)
    """

    def _create_mock(
        output_schema: type[BaseModel],
        field_values: dict[str, Any] | None = None,
    ) -> Callable[[str], BaseModel]:
        """Create a mock LLM function that returns schema instances."""

        def mock_fn(prompt: str) -> BaseModel:
            values: dict[str, Any] = {}
            for field_name, info in output_schema.model_fields.items():
                if field_values and field_name in field_values:
                    values[field_name] = field_values[field_name]
                else:
                    anno = info.annotation
                    if anno is str:
                        values[field_name] = f"mock_{field_name}"
                    elif anno is float:
                        values[field_name] = 0.85
                    elif anno is int:
                        values[field_name] = 42
                    elif hasattr(anno, "__origin__") and anno.__origin__ is list:
                        values[field_name] = []
                    else:
                        values[field_name] = None
            return output_schema(**values)

        return mock_fn

    return _create_mock


@pytest.fixture
def mock_llm_step(mock_llm_fn):
    """
    Factory fixture for creating fully mocked LLMStep instances.

    Usage:
        def test_step(mock_llm_step):
            step = mock_llm_step(
                name="test_step",
                input_columns=["text"],
                prompt_template="Process: {text}",
                output_schema=MyOutput,
            )
            result = step.run(df)
    """

    def _create_step(
        name: str,
        input_columns: list[str],
        prompt_template: str,
        output_schema: type[BaseModel],
        field_values: dict[str, Any] | None = None,
        concurrency: int = 1,
    ) -> LLMStep:
        """Create a mocked LLMStep for testing."""
        llm_fn = mock_llm_fn(output_schema, field_values)

        return LLMStep(
            name=name,
            input_columns=input_columns,
            prompt_template=prompt_template,
            output_schema=output_schema,
            llm_fn=llm_fn,
            concurrency=concurrency,
        )

    return _create_step


# ============================================================================
# Content-Aware Mocking
# ============================================================================


@pytest.fixture
def content_aware_llm_fn():
    """
    Factory for creating content-aware mock LLM functions.

    Returns different responses based on keywords in the prompt.

    Usage:
        def test_extraction(content_aware_llm_fn):
            llm_fn = content_aware_llm_fn(
                output_schema=EntityOutput,
                keyword_responses={
                    "postgresql": {"entity_type": "database"},
                    "python": {"entity_type": "language"},
                },
            )
    """

    def _create_factory(
        output_schema: type[BaseModel],
        keyword_responses: dict[str, dict[str, Any]],
        default_values: dict[str, Any] | None = None,
    ) -> Callable[[str], BaseModel]:
        """Create a content-aware mock LLM function."""

        def _get_defaults(field_name: str, info) -> Any:
            if default_values and field_name in default_values:
                return default_values[field_name]
            anno = info.annotation
            if anno is str:
                return f"mock_{field_name}"
            elif anno is float:
                return 0.85
            elif anno is int:
                return 42
            elif hasattr(anno, "__origin__") and anno.__origin__ is list:
                return []
            return None

        def mock_fn(prompt: str) -> BaseModel:
            prompt_lower = prompt.lower()

            # Check for keyword matches
            for keyword, values in keyword_responses.items():
                if keyword.lower() in prompt_lower:
                    merged = {}
                    for field_name, info in output_schema.model_fields.items():
                        if field_name in values:
                            merged[field_name] = values[field_name]
                        else:
                            merged[field_name] = _get_defaults(field_name, info)
                    return output_schema(**merged)

            # Default response
            values = {}
            for field_name, info in output_schema.model_fields.items():
                values[field_name] = _get_defaults(field_name, info)
            return output_schema(**values)

        return mock_fn

    return _create_factory


# ============================================================================
# Hook Testing
# ============================================================================


class RecordingHooks:
    """
    Test hooks that record all callback invocations.

    Useful for verifying hook behavior in tests.
    """

    def __init__(self):
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def on_start(self, *, step_name: str, total: int, concurrency: int) -> None:
        self.calls.append(
            ("on_start", {"step_name": step_name, "total": total, "concurrency": concurrency})
        )

    def on_row_success(
        self,
        *,
        step_name: str,
        idx: int,
        total: int,
        latency_ms: int,
        prompt: str,
        tokens_in: int,
        tokens_out: int,
        cost: float,
        result: dict[str, Any],
    ) -> None:
        self.calls.append(
            (
                "on_row_success",
                {
                    "step_name": step_name,
                    "idx": idx,
                    "total": total,
                    "latency_ms": latency_ms,
                    "prompt": prompt,
                    "tokens_in": tokens_in,
                    "tokens_out": tokens_out,
                    "cost": cost,
                    "result": result,
                },
            )
        )

    def on_row_error(
        self,
        *,
        step_name: str,
        idx: int,
        total: int,
        latency_ms: int,
        prompt: str,
        tokens_in: int,
        tokens_out: int,
        cost: float,
        error: Exception,
    ) -> None:
        self.calls.append(
            (
                "on_row_error",
                {
                    "step_name": step_name,
                    "idx": idx,
                    "total": total,
                    "latency_ms": latency_ms,
                    "prompt": prompt,
                    "tokens_in": tokens_in,
                    "tokens_out": tokens_out,
                    "cost": cost,
                    "error": error,
                },
            )
        )

    def on_result(
        self,
        *,
        step_name: str,
        idx: int,
        total: int,
        status: str,
        error: str | None,
    ) -> None:
        self.calls.append(
            (
                "on_result",
                {
                    "step_name": step_name,
                    "idx": idx,
                    "total": total,
                    "status": status,
                    "error": error,
                },
            )
        )

    def on_end(
        self,
        *,
        step_name: str,
        successful: int,
        total: int,
        errors: list[str],
    ) -> None:
        self.calls.append(
            (
                "on_end",
                {
                    "step_name": step_name,
                    "successful": successful,
                    "total": total,
                    "errors": errors,
                },
            )
        )

    def get_calls(self, event_type: str) -> list[dict[str, Any]]:
        """Get all calls of a specific event type."""
        return [data for name, data in self.calls if name == event_type]


@pytest.fixture
def recording_hooks():
    """Fixture that provides a RecordingHooks instance."""
    return RecordingHooks()


# ============================================================================
# DataFrame Fixtures
# ============================================================================


@pytest.fixture
def sample_df():
    """Simple sample DataFrame for testing."""
    return pd.DataFrame(
        {
            "id": [1, 2, 3],
            "text": ["Hello world", "Test content", "More data"],
            "category": ["A", "B", "A"],
        }
    )


@pytest.fixture
def large_df():
    """Larger DataFrame for concurrency testing."""
    return pd.DataFrame(
        {
            "id": range(100),
            "text": [f"Document {i} content" for i in range(100)],
        }
    )


# ============================================================================
# DBOS Integration Fixtures
# ============================================================================


class MockHandle:
    """Mock handle that returns results synchronously."""

    def __init__(self, result):
        self._result = result

    def get_result(self):
        return self._result


class MockQueue:
    """Mock queue that executes functions synchronously."""

    def __init__(self, name: str = "", *args, **kwargs):
        self.name = name

    def enqueue(self, fn, *args, **kwargs):
        # Execute the function synchronously and return a mock handle
        result = fn(*args, **kwargs)
        return MockHandle(result)


class MockSetEnqueueOptions:
    """Mock context manager for SetEnqueueOptions."""

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


@pytest.fixture
def mock_dbos():
    """
    Mock DBOS for tests that need synchronous execution without real DBOS.

    Patches DBOS decorators and Queue to execute synchronously.
    Tests that need this must explicitly request it.
    """
    import sys

    # Patch DBOS.step decorator to be a no-op
    def mock_step_decorator(**kwargs):
        def decorator(fn):
            return fn

        return decorator

    mock_dbos_cls = MagicMock()
    mock_dbos_cls.step = mock_step_decorator
    mock_dbos_cls.workflow = mock_step_decorator
    mock_dbos_cls.workflow_id = "test-workflow-id"

    # Force import of modules
    from kurt.core import embedding_step as _e  # noqa: F401
    from kurt.core import llm_step as _l  # noqa: F401

    llm_step_module = sys.modules["kurt.core.llm_step"]
    embedding_step_module = sys.modules["kurt.core.embedding_step"]

    # Store originals
    originals = {
        "llm_queue": llm_step_module.Queue,
        "llm_set_enqueue": llm_step_module.SetEnqueueOptions,
        "llm_dbos": llm_step_module.DBOS,
        "emb_queue": embedding_step_module.Queue,
        "emb_dbos": embedding_step_module.DBOS,
    }

    # Patch llm_step
    llm_step_module.Queue = MockQueue
    llm_step_module.SetEnqueueOptions = MockSetEnqueueOptions
    llm_step_module.DBOS = mock_dbos_cls

    # Patch embedding_step
    embedding_step_module.Queue = MockQueue
    embedding_step_module.DBOS = mock_dbos_cls

    try:
        yield mock_dbos_cls
    finally:
        llm_step_module.Queue = originals["llm_queue"]
        llm_step_module.SetEnqueueOptions = originals["llm_set_enqueue"]
        llm_step_module.DBOS = originals["llm_dbos"]
        embedding_step_module.Queue = originals["emb_queue"]
        embedding_step_module.DBOS = originals["emb_dbos"]


@pytest.fixture
def dbos_launched(tmp_database, reset_dbos_state):
    """
    Fixture that initializes and launches DBOS for integration tests.

    Use this when testing actual DBOS queue behavior.
    DBOS creates its own tables (workflow_events, streams, etc.) in the database.
    """
    from dbos import DBOS

    from kurt.core.dbos import init_dbos

    # Initialize DBOS with proper config (uses tmp_database path)
    init_dbos()

    yield DBOS

    # Cleanup handled by reset_dbos_state
